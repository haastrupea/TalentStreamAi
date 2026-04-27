from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionCheckResult:
    risk_score: int
    matched_rules: list[str]

    @property
    def suspicious(self) -> bool:
        return self.risk_score >= 3


_RULES: list[tuple[str, re.Pattern[str], int]] = [
    ("ignore_instruction", re.compile(r"\b(ignore|bypass|disregard)\b.{0,30}\b(instruction|system|previous|above)\b", re.I), 2),
    ("role_override", re.compile(r"\b(you are now|act as|pretend to be)\b", re.I), 1),
    ("system_tag", re.compile(r"(?:^|\n)\s*(###\s*system|<\s*/?\s*system\s*>|<\s*/?\s*assistant\s*>)", re.I), 2),
    ("jailbreak_terms", re.compile(r"\b(jailbreak|prompt injection|developer message|system prompt)\b", re.I), 2),
    ("tool_leakage", re.compile(r"\b(exfiltrate|leak|reveal)\b.{0,50}\b(prompt|secret|token)\b", re.I), 2),
    ("delimiter_flood", re.compile(r"([`#<>{}\[\]])\1{7,}"), 1),
]


def check_prompt_injection(text: str) -> InjectionCheckResult:
    body = str(text or "")
    score = 0
    hits: list[str] = []
    for name, pattern, weight in _RULES:
        if pattern.search(body):
            hits.append(name)
            score += weight
    unique_ratio = 0.0
    stripped = re.sub(r"\s+", "", body)
    if stripped:
        unique_ratio = len(set(stripped)) / max(1, len(stripped))
    if len(body) > 600 and unique_ratio < 0.12:
        hits.append("low_entropy_repetition")
        score += 2
    return InjectionCheckResult(risk_score=score, matched_rules=hits)
