from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.db import UsageSnapshot
from app.services.entitlements import PlanLimits


@dataclass(frozen=True)
class EntitlementsUsage:
    period_yyyymm: str
    plan: str
    limits: PlanLimits
    usage: UsageSnapshot


def estimate_tailor_tokens(*, resume_text: str, job_description_text: str, llm_max_tokens: int) -> int:
    input_estimate = max(1, int((len(resume_text) + len(job_description_text)) / 4))
    # analyze + resume + cover letter + gmail steps
    completion_ceiling = max(0, int(llm_max_tokens)) * 4
    return input_estimate + completion_ceiling


def limit_detail(*, code: str, message: str, plan: str, period_yyyymm: str, limit: int, used: int) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "plan": plan,
        "period": period_yyyymm,
        "limit": int(limit),
        "used": int(used),
    }
