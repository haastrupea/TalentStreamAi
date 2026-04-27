from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentCheckResult:
    score: float
    reasons: list[str]


_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+?\d[\d\-\s().]{7,}\d)")
_DATE_RANGE = re.compile(r"(19|20)\d{2}\s*(?:-|to|–)\s*(19|20)\d{2}|(19|20)\d{2}\s*-\s*(present|current)", re.I)


def check_resume_like(text: str) -> DocumentCheckResult:
    body = str(text or "")
    lowered = body.lower()
    reasons: list[str] = []
    score = 0.0
    if len(body) >= 350:
        score += 0.2
        reasons.append("length")
    if _EMAIL.search(body):
        score += 0.2
        reasons.append("email")
    if _PHONE.search(body):
        score += 0.15
        reasons.append("phone")
    if _DATE_RANGE.search(body):
        score += 0.2
        reasons.append("date_ranges")
    section_hits = sum(
        1
        for key in ("experience", "education", "skills", "projects", "summary")
        if key in lowered
    )
    if section_hits >= 2:
        score += 0.2
        reasons.append("sections")
    if re.search(r"\b(engineer|developer|manager|analyst|intern)\b", lowered):
        score += 0.1
        reasons.append("job_titles")
    return DocumentCheckResult(score=min(1.0, score), reasons=reasons)


def check_job_description_like(text: str) -> DocumentCheckResult:
    body = str(text or "")
    lowered = body.lower()
    reasons: list[str] = []
    score = 0.0
    if len(body) >= 300:
        score += 0.25
        reasons.append("length")
    section_hits = sum(
        1
        for key in (
            "responsibilities",
            "requirements",
            "qualifications",
            "about the role",
            "what you'll do",
            "benefits",
        )
        if key in lowered
    )
    if section_hits >= 2:
        score += 0.35
        reasons.append("job_sections")
    if re.search(r"\b(we are looking for|you will|must have|preferred|required)\b", lowered):
        score += 0.2
        reasons.append("hiring_language")
    if re.search(r"\b(annual salary|compensation|remote|hybrid|full[- ]time)\b", lowered):
        score += 0.1
        reasons.append("employment_terms")
    if _EMAIL.search(body) and _PHONE.search(body):
        score -= 0.1
        reasons.append("resume_signals_present")
    return DocumentCheckResult(score=max(0.0, min(1.0, score)), reasons=reasons)
