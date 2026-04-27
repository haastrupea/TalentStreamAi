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


def _plan_aliases() -> dict[str, str]:
    out: dict[str, str] = {}
    raw = (settings.plan_alias_map or "").strip()
    if not raw:
        return out
    for chunk in raw.split(","):
        if ":" not in chunk:
            continue
        source, target = chunk.split(":", 1)
        source = source.strip().lower()
        target = target.strip().lower()
        if source and target:
            out[source] = target
    return out


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


def resolve_user_plan(claims: dict[str, Any]) -> ResolvedPlan:
    limits_map = _plan_limits_map()
    default_plan = settings.plan_default if settings.plan_default in limits_map else "free"
    claim_path = (settings.plan_claim_path or "").strip() or "public_metadata.plan"
    raw = _extract_from_claim_path(claims, claim_path).lower()
    aliases = _plan_aliases()
    resolved = aliases.get(raw, raw)
    if resolved not in limits_map:
        resolved = default_plan
    return ResolvedPlan(
        plan_key=resolved,
        raw_value=raw,
        claim_path=claim_path,
        limits=limits_map[resolved],
    )
