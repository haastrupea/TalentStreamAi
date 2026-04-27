"""Prometheus metrics (exposed at /api/v1/metrics when enabled)."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, generate_latest, REGISTRY

# HTTP
http_requests = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("method", "path_template", "status"),
)
http_request_latency = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ("method", "path_template"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# LLM
llm_calls = Counter(
    "llm_invocations_total",
    "LLM API calls",
    ("model", "outcome"),
)
llm_tokens = Counter(
    "llm_tokens_total",
    "Token usage (when reported by the provider)",
    ("model", "token_type"),
)
llm_latency = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration",
    ("model",),
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

# Domain
tailor_runs = Counter("tailor_runs_total", "Resume tailor runs", ("outcome",))
limit_rejections = Counter(
    "limit_rejections_total",
    "Requests rejected by quota/validation guardrails",
    ("reason",),
)


def metrics_payload() -> bytes:
    return generate_latest(REGISTRY)
