from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.db import create_document, get_document
from app.services.guardrails import enforce_job_description_like, enforce_prompt_injection_guard
from app.services.text_guardrails import normalize_user_text

router = APIRouter()


class JobDescriptionCreateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500_000)
    source_url: str | None = None


@router.post("/job-descriptions")
def create_job_description(
    payload: JobDescriptionCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    text = normalize_user_text(payload.text)
    if not text:
        raise HTTPException(status_code=400, detail="Empty job description")
    enforce_prompt_injection_guard(text=text, field_name="job_description")
    enforce_job_description_like(text=text, field_name="job_description")

    doc = create_document(
        kind="job_description",
        owner_user_id=user.user_id,
        text=text,
        filename=None,
        content_type="text/plain",
        meta={"source_url": payload.source_url} if payload.source_url else {},
    )
    return {"job_description_id": doc.id}


@router.get("/job-descriptions/{job_description_id}")
def get_job_description(
    job_description_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str | None]:
    doc = get_document(doc_id=job_description_id, owner_user_id=user.user_id)
    if not doc or doc.kind != "job_description":
        raise HTTPException(status_code=404, detail="Job description not found")
    return {
        "job_description_id": doc.id,
        "created_at": doc.created_at,
    }
