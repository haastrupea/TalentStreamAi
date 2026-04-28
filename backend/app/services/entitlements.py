from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class PlanLimits:
    monthly_llm_token_budget: int
    monthly_application_limit: int
    monthly_base_resume_limit: int


@dataclass(frozen=True)
class ResolvedPlan:
    plan_key: str
    raw_value: str
    claim_path: str
    limits: PlanLimits


def _plan_limits_map() -> dict[str, PlanLimits]:
    return {
        "free": PlanLimits(
            monthly_llm_token_budget=max(0, settings.free_monthly_llm_token_budget),
            monthly_application_limit=max(0, settings.free_monthly_application_limit),
            monthly_base_resume_limit=max(0, settings.free_monthly_base_resume_limit),
        ),
        "starter": PlanLimits(
            monthly_llm_token_budget=max(0, settings.starter_monthly_llm_token_budget),
            monthly_application_limit=max(0, settings.starter_monthly_application_limit),
            monthly_base_resume_limit=max(0, settings.starter_monthly_base_resume_limit),
        ),
        "pro": PlanLimits(
            monthly_llm_token_budget=max(0, settings.pro_monthly_llm_token_budget),
            monthly_application_limit=max(0, settings.pro_monthly_application_limit),
            monthly_base_resume_limit=max(0, settings.pro_monthly_base_resume_limit),
        ),
    }


def _extract_from_claim_path(claims: dict[str, Any], path: str) -> str:
    cur: Any = claims
    for part in path.split("."):
        key = part.strip()
        if not key:
            continue
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    if cur is None:
        return ""
    return str(cur).strip()

def parse_claim_plan(raw_plan: str):
    identifier, plan = raw_plan.split(":", 1)
    if (identifier or '').lower() == 'u':
        return plan.lower()
    return 'free'

def resolve_user_plan(claims: dict[str, Any]) -> ResolvedPlan:
    limits_map = _plan_limits_map()
    default_plan = settings.plan_default if settings.plan_default in limits_map else "free"
    claim_path = (settings.plan_claim_path or "").strip() or "pla"
    raw_plan = _extract_from_claim_path(claims, claim_path).lower()
    resolved = parse_claim_plan(raw_plan)
    if resolved not in limits_map:
        resolved = default_plan
    return ResolvedPlan(
        plan_key=resolved,
        raw_value=raw_plan,
        claim_path=claim_path,
        limits=limits_map[resolved],
    )
