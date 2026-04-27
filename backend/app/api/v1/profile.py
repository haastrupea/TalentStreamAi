from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.schemas.frontend import (
    EntitlementsOut,
    LimitUsageOut,
    PlanLimitsOut,
    ProfileOut,
    ProfilePatchIn,
    ResumeOut,
    map_profile,
    map_resume,
)
from app.core import metrics
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.db import bump_usage, get_document, get_usage_snapshot, get_user_profile, upsert_user_profile
from app.services.entitlements import resolve_user_plan
from app.services.usage_limits import limit_detail
from app.services.ingest_resume import ingest_uploaded_resume

router = APIRouter()
log = structlog.get_logger(__name__)


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: AuthenticatedUser = Depends(get_current_user)) -> ProfileOut:
    p = get_user_profile(user_id=user.user_id)
    return map_profile(user.user_id, p, user.claims)


@router.get("/entitlements", response_model=EntitlementsOut)
def get_entitlements(user: AuthenticatedUser = Depends(get_current_user)) -> EntitlementsOut:
    plan = resolve_user_plan(user.claims)
    usage = get_usage_snapshot(user_id=user.user_id)
    return EntitlementsOut(
        plan=plan.plan_key,
        period=usage.period_yyyymm,
        limits=PlanLimitsOut(
            monthly_llm_token_budget=plan.limits.monthly_llm_token_budget,
            monthly_application_limit=plan.limits.monthly_application_limit,
            monthly_base_resume_limit=plan.limits.monthly_base_resume_limit,
        ),
        usage=LimitUsageOut(
            llm_prompt_tokens=usage.llm_prompt_tokens,
            llm_completion_tokens=usage.llm_completion_tokens,
            total_llm_tokens=usage.total_llm_tokens,
            applications_created=usage.applications_created,
            base_resume_uploads=usage.base_resume_uploads,
        ),
    )


@router.patch("/profile", response_model=ProfileOut)
def patch_profile(
    body: ProfilePatchIn,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ProfileOut:
    doc = get_document(doc_id=body.base_resume_id, owner_user_id=user.user_id)
    if not doc or doc.kind != "resume":
        raise HTTPException(status_code=404, detail="Resume not found")
    claims = user.claims
    existing = get_user_profile(user_id=user.user_id)
    if existing is None:
        upsert_user_profile(
            user_id=user.user_id,
            email=str(claims.get("email") or ""),
            full_name=str(claims.get("name") or ""),
            headline=None,
            base_resume_id=body.base_resume_id,
        )
    else:
        upsert_user_profile(
            user_id=user.user_id,
            base_resume_id=body.base_resume_id,
        )
    p = get_user_profile(user_id=user.user_id)
    return map_profile(user.user_id, p, user.claims)


@router.post("/profile/base-resume", response_model=ResumeOut)
async def upload_base_resume(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ResumeOut:
    plan = resolve_user_plan(user.claims)
    usage = get_usage_snapshot(user_id=user.user_id)
    if usage.base_resume_uploads >= plan.limits.monthly_base_resume_limit:
        metrics.limit_rejections.labels("base_resume_uploads").inc()
        raise HTTPException(
            status_code=403,
            detail=limit_detail(
                code="LIMIT_BASE_RESUMES",
                message="Base resume upload limit reached for this plan.",
                plan=plan.plan_key,
                period_yyyymm=usage.period_yyyymm,
                limit=plan.limits.monthly_base_resume_limit,
                used=usage.base_resume_uploads,
            ),
        )
    try:
        res = await ingest_uploaded_resume(
            file=file, user=user, set_as_base=True
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception("base_resume_upload_failed")
        raise HTTPException(status_code=500, detail="Failed to store resume") from e
    await run_in_threadpool(bump_usage, user_id=user.user_id, base_resume_uploads=1)
    p = get_user_profile(user_id=user.user_id)
    is_base = bool(p and p.base_resume_id == res.document.id)
    return map_resume(
        res.document, is_base=is_base, application_id=None
    )
