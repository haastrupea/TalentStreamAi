"""Pydantic models aligned with the Next.js `src/lib/types.ts` (camelCase JSON)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.core.db import ApplicationRecord, StoredDocument, UserProfile


def _cc() -> ConfigDict:
    return ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class ProfileOut(BaseModel):
    model_config = _cc()
    id: str
    full_name: str
    email: str
    headline: str | None = None
    base_resume_id: str | None = None
    created_at: str


class ProfilePatchIn(BaseModel):
    model_config = _cc()
    base_resume_id: str


class ResumeOut(BaseModel):
    model_config = _cc()
    id: str
    title: str
    content: str
    application_id: str | None = None
    is_base: bool | None = None
    created_at: str


class DashboardStatsOut(BaseModel):
    model_config = _cc()
    applications: int
    interviews: int
    average_match_score: float
    resumes_generated: int


class PlanLimitsOut(BaseModel):
    model_config = _cc()
    monthly_llm_token_budget: int
    monthly_application_limit: int
    monthly_base_resume_limit: int


class LimitUsageOut(BaseModel):
    model_config = _cc()
    llm_prompt_tokens: int
    llm_completion_tokens: int
    total_llm_tokens: int
    applications_created: int
    base_resume_uploads: int


class EntitlementsOut(BaseModel):
    model_config = _cc()
    plan: str
    period: str
    limits: PlanLimitsOut
    usage: LimitUsageOut


class GapItemOut(BaseModel):
    model_config = _cc()
    skill: str
    severity: str
    note: str | None = None


class ApplicationOut(BaseModel):
    model_config = _cc()
    id: str
    company: str
    position: str
    job_url: str | None = None
    job_description: str
    match_score: int
    status: str
    resume_id: str | None = None
    cover_letter: str | None = None
    gaps: list[GapItemOut] | None = None
    created_at: str


class MatchAnalysisOut(BaseModel):
    model_config = _cc()
    original_score: float
    tailored_score: float
    improvement: float
    what_we_improved: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    remaining_deficits: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DraftEmailOut(BaseModel):
    model_config = _cc()
    subject: str
    body: str


class TailorRequestIn(BaseModel):
    model_config = _cc()
    base_resume_id: str
    job_url: str | None = None
    job_description: str | None = None

    @model_validator(mode="after")
    def require_job(self) -> TailorRequestIn:
        url = (self.job_url or "").strip()
        desc = (self.job_description or "").strip()
        if not url and len(desc) < 40:
            raise ValueError("Provide a jobUrl or at least 40 characters of jobDescription")
        if url and not url.lower().startswith(("http://", "https://")):
            raise ValueError("jobUrl must be an http(s) URL")
        return self


class TailorResponseOut(BaseModel):
    model_config = _cc()
    application_id: str
    match_score: int
    resume: ResumeOut
    cover_letter: str
    draft_email: DraftEmailOut
    gaps: list[GapItemOut]
    analysis: MatchAnalysisOut


def _gap_items(raw: list[Any]) -> list[GapItemOut]:
    out: list[GapItemOut] = []
    for g in raw or []:
        if isinstance(g, dict):
            out.append(
                GapItemOut(
                    skill=str(g.get("skill", "")),
                    severity=str(g.get("severity", "")),
                    note=g.get("note"),
                )
            )
    return out


def map_profile(user_id: str, profile: UserProfile | None, claims: dict[str, Any]) -> ProfileOut:
    email = (profile and profile.email) or str(claims.get("email") or "")
    name = (profile and profile.full_name) or str(claims.get("name") or "")
    cr = (profile and profile.created_at) or ""
    return ProfileOut(
        id=user_id,
        full_name=name,
        email=email,
        headline=(profile and profile.headline) or None,
        base_resume_id=(profile and profile.base_resume_id) or None,
        created_at=cr,
    )


def map_resume(
    doc: StoredDocument, *, is_base: bool, application_id: str | None
) -> ResumeOut:
    title = str(doc.meta.get("title") or doc.filename or "")
    is_b = bool(doc.meta.get("is_base")) or is_base
    return ResumeOut(
        id=doc.id,
        title=title[:500],
        content=doc.text,
        application_id=doc.meta.get("application_id") or application_id,
        is_base=is_b,
        created_at=doc.created_at,
    )


def map_application(
    a: ApplicationRecord, *, list_view: bool = False
) -> ApplicationOut:
    met = a.meta or {}
    gaps = _gap_items(met.get("gaps", []))
    jdesc = a.job_description
    if list_view and len(jdesc) > 2000:
        jdesc = jdesc[:2000] + "…"
    return ApplicationOut(
        id=a.id,
        company=str(a.company or ""),
        position=str(a.position or ""),
        job_url=a.job_url,
        job_description=jdesc,
        match_score=int(round(a.match_score)),
        status=a.status,
        resume_id=a.resume_id,
        cover_letter=a.cover_letter,
        gaps=gaps,
        created_at=a.created_at,
    )


def map_match_analysis(m: dict[str, Any]) -> MatchAnalysisOut:
    return MatchAnalysisOut(
        original_score=float(
            m.get("originalScore", m.get("original_score", 0)) or 0
        ),
        tailored_score=float(
            m.get("tailoredScore", m.get("tailored_score", 0)) or 0
        ),
        improvement=float(m.get("improvement", 0) or 0),
        what_we_improved=list(
            m.get("whatWeImproved") or m.get("what_we_improved") or []
        ),
        strengths=list(m.get("strengths") or []),
        remaining_deficits=list(
            m.get("remainingDeficits") or m.get("remaining_deficits") or []
        ),
        matched_keywords=list(
            m.get("matchedKeywords") or m.get("matched_keywords") or []
        ),
        missing_keywords=list(
            m.get("missingKeywords") or m.get("missing_keywords") or []
        ),
        suggestions=list(m.get("suggestions") or []),
    )
