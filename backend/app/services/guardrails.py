from __future__ import annotations

import structlog
from fastapi import HTTPException

from app.core import metrics
from app.core.config import settings
from app.services.document_checks import check_job_description_like, check_resume_like
from app.services.input_safety import check_prompt_injection

log = structlog.get_logger(__name__)


def _mode(value: str) -> str:
    v = (value or "").strip().lower()
    if v in {"warn", "block"}:
        return v
    return "warn"


def enforce_prompt_injection_guard(*, text: str, field_name: str) -> None:
    result = check_prompt_injection(text)
    if not result.matched_rules:
        return
    log.warning(
        "prompt_injection_signal",
        field=field_name,
        risk_score=result.risk_score,
        matched_rules=result.matched_rules,
    )
    if _mode(settings.input_injection_mode) == "block" and result.suspicious:
        metrics.limit_rejections.labels("prompt_injection").inc()
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PROMPT_INJECTION_SUSPECTED",
                "message": f"Input flagged as suspicious in {field_name}.",
                "field": field_name,
                "signals": result.matched_rules,
            },
        )


def enforce_resume_like(*, text: str, field_name: str = "resume_text") -> None:
    result = check_resume_like(text)
    if result.score >= settings.resume_validation_min_score:
        return
    if _mode(settings.expected_input_mode) == "warn":
        log.warning(
            "resume_text_unlikely",
            field=field_name,
            score=round(result.score, 4),
            reasons=result.reasons,
        )
        return
    metrics.limit_rejections.labels("resume_unlikely").inc()
    raise HTTPException(
        status_code=400,
        detail={
            "code": "DOCUMENT_NOT_RESUME_LIKE",
            "message": "The uploaded content does not look like a resume/CV.",
            "field": field_name,
            "score": round(result.score, 4),
            "signals": result.reasons,
        },
    )


def enforce_job_description_like(*, text: str, field_name: str = "job_description") -> None:
    result = check_job_description_like(text)
    if result.score >= settings.job_description_validation_min_score:
        return
    if _mode(settings.expected_input_mode) == "warn":
        log.warning(
            "job_description_unlikely",
            field=field_name,
            score=round(result.score, 4),
            reasons=result.reasons,
        )
        return
    metrics.limit_rejections.labels("job_description_unlikely").inc()
    raise HTTPException(
        status_code=400,
        detail={
            "code": "JOB_DESCRIPTION_UNLIKELY",
            "message": "The submitted text does not look like a job description.",
            "field": field_name,
            "score": round(result.score, 4),
            "signals": result.reasons,
        },
    )
