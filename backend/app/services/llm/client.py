from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from app.core.config import settings
from app.core import metrics
from app.core.db import bump_usage
from app.core.request_context import get_context_user_id
from app.services.llm.json_parsing import parse_json_object
from app.services.llm.safety import llm_output_safety_flags
from app.services.observability.langfuse_tracing import (
    chat_completions_span,
    generation_mark_error,
    generation_mark_success,
)

logger = logging.getLogger(__name__)
slog = structlog.get_logger(__name__)

_http_clients_by_loop: dict[asyncio.AbstractEventLoop, httpx.AsyncClient] = {}


def _http_client() -> httpx.AsyncClient:
    loop = asyncio.get_running_loop()
    client = _http_clients_by_loop.get(loop)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(timeout=httpx.Timeout(settings.llm_timeout_seconds))
        _http_clients_by_loop[loop] = client
    return client


async def close_llm_http_clients() -> None:
    clients = list(_http_clients_by_loop.values())
    _http_clients_by_loop.clear()
    for client in clients:
        if not client.is_closed:
            await client.aclose()


@dataclass(frozen=True)
class LlmMessage:
    role: str
    content: str


class LlmError(RuntimeError):
    pass


class LlmClient:
    def __init__(self) -> None:
        self._base_url = settings.llm_base_url.rstrip("/")
        self._api_key = settings.chat_completions_api_key
        self._model = settings.llm_model

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise LlmError(
                "OPENROUTER_API_KEY or OPENAI_API_KEY is required when AGENT_MODE=llm"
            )
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_referer:
            headers["HTTP-Referer"] = settings.openrouter_referer
        if settings.openrouter_title:
            headers["X-Title"] = settings.openrouter_title
        return headers

    async def chat_json(self, *, messages: list[LlmMessage]) -> dict[str, Any]:
        url = f"{self._base_url}/v1/chat/completions"
        msg_dicts = [m.__dict__ for m in messages]
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": msg_dicts,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "response_format": {"type": "json_object"},
        }

        def _is_retryable_http_status(exc: httpx.HTTPStatusError) -> bool:
            status = exc.response.status_code if exc.response else None
            if status is None:
                return True
            return status == 429 or 500 <= status <= 599 or status == 408

        def _is_retryable_exc(exc: Exception) -> bool:
            if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
                return True
            if isinstance(exc, httpx.HTTPStatusError):
                return _is_retryable_http_status(exc)
            return False

        with chat_completions_span(
            messages=msg_dicts,
            model=self._model,
            base_url=self._base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        ) as gen:
            t0 = time.perf_counter()
            data: dict[str, Any] | None = None
            try:
                async for attempt in AsyncRetrying(
                    reraise=True,
                    stop=stop_after_attempt(3),
                    wait=wait_exponential_jitter(initial=0.5, max=4.0),
                    retry=retry_if_exception(_is_retryable_exc),
                ):
                    with attempt:
                        resp = await _http_client().post(
                            url, headers=self._headers(), json=payload
                        )
                        try:
                            resp.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            body = (resp.text or "")[:500]
                            logger.warning("LLM HTTP error %s: %s", resp.status_code, body)
                            metrics.llm_calls.labels(self._model, "http_error").inc()
                            generation_mark_error(gen, exc)
                            raise
                        data = resp.json()
            except Exception as e:
                if not isinstance(e, httpx.HTTPStatusError):
                    generation_mark_error(gen, e)
                raise
            if data is None:
                ne = LlmError("No response from LLM")
                generation_mark_error(gen, ne)
                raise ne

            elapsed = time.perf_counter() - t0
            metrics.llm_latency.labels(self._model).observe(elapsed)
            metrics.llm_calls.labels(self._model, "success").inc()

            usage = data.get("usage") or {}
            pt = int(usage.get("prompt_tokens") or 0)
            ct = int(usage.get("completion_tokens") or 0)
            if pt:
                metrics.llm_tokens.labels(self._model, "prompt").inc(pt)
            if ct:
                metrics.llm_tokens.labels(self._model, "completion").inc(ct)
            if pt or ct:
                slog.info(
                    "llm_token_usage",
                    model=self._model,
                    prompt_tokens=pt,
                    completion_tokens=ct,
                    duration_ms=round(elapsed * 1000, 2),
                )
                uid = get_context_user_id()
                if uid:
                    bump_usage(
                        user_id=uid,
                        prompt_tokens=pt,
                        completion_tokens=ct,
                    )

            try:
                text = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as e:
                metrics.llm_calls.labels(self._model, "malformed").inc()
                generation_mark_error(gen, e)
                raise LlmError("Malformed LLM response") from e

            flags = llm_output_safety_flags(text)
            if flags:
                slog.warning(
                    "llm_output_safety_flags",
                    model=self._model,
                    flags=flags,
                )

            try:
                out = parse_json_object(text)
            except Exception as e:
                metrics.llm_calls.labels(self._model, "json_parse").inc()
                logger.warning("Failed to parse JSON from LLM output", exc_info=e)
                generation_mark_error(gen, e)
                raise LlmError("LLM did not return valid JSON") from e

            generation_mark_success(
                gen,
                assistant_text=text,
                prompt_tokens=pt,
                completion_tokens=ct,
            )
            return out
