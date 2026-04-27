"""Shared upload + text extraction for resume documents."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.auth import AuthenticatedUser
from app.core.config import settings
from app.core.db import StoredDocument, create_document, upsert_user_profile
from app.services.guardrails import enforce_prompt_injection_guard, enforce_resume_like
from app.services.text_guardrails import normalize_user_text
from app.services.uploads import delete_saved_upload, extract_text, save_upload, validate_upload

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    document: StoredDocument
    byte_size: int


async def ingest_uploaded_resume(
    *,
    file: UploadFile,
    user: AuthenticatedUser,
    set_as_base: bool,
) -> IngestResult:
    """Parse upload, persist as a resume document, optionally mark as the user's base resume."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)
    raw = b"".join(chunks)

    def _process() -> tuple[Any, str, str]:
        detected_type = validate_upload(
            filename=file.filename or "", content_type=file.content_type, data=raw
        )
        extracted = extract_text(detected_type=detected_type, data=raw)
        extracted = normalize_user_text(extracted)
        if not extracted:
            return None, detected_type, ""
        saved = save_upload(
            detected_type=detected_type,
            owner_user_id=user.user_id,
            content_type=file.content_type,
            data=raw,
        )
        return saved, detected_type, extracted

    saved, detected_type, extracted = await run_in_threadpool(_process)
    if not extracted:
        raise HTTPException(status_code=400, detail="Could not extract text from resume")
    enforce_prompt_injection_guard(text=extracted, field_name="resume_upload")
    enforce_resume_like(text=extracted, field_name="resume_upload")

    title = (file.filename or "").rsplit("/")[-1][:200]
    meta: dict[str, Any] = {
        "bytes": len(raw),
        "detected_type": detected_type,
        "title": title,
        "is_base": set_as_base,
    }
    try:
        doc = await run_in_threadpool(
            create_document,
            kind="resume",
            owner_user_id=user.user_id,
            text=extracted,
            filename=file.filename,
            content_type=file.content_type,
            file_path=saved.path if saved else None,
            meta=meta,
        )
    except Exception:
        try:
            await run_in_threadpool(delete_saved_upload, saved.path if saved else None)
        except Exception:
            logger.exception("Failed to clean up uploaded resume after DB insert failure")
        raise

    if set_as_base:
        email = str(user.claims.get("email") or "") or None
        full_name = str(
            user.claims.get("name")
            or user.claims.get("given_name")
            or ""
        )
        await run_in_threadpool(
            upsert_user_profile,
            user_id=user.user_id,
            email=email,
            full_name=full_name,
            headline=None,
            base_resume_id=doc.id,
        )
    return IngestResult(document=doc, byte_size=len(raw))
