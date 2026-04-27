from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.config import settings


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_conn() -> sqlite3.Connection:
    _ensure_parent_dir(settings.sqlite_path)
    conn = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={int(settings.sqlite_busy_timeout_ms)}")
    conn.execute("PRAGMA foreign_keys=ON")
    if settings.sqlite_enable_wal:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY,
              kind TEXT NOT NULL,
              owner_user_id TEXT NOT NULL,
              filename TEXT,
              content_type TEXT,
              file_path TEXT,
              text TEXT NOT NULL,
              created_at TEXT NOT NULL,
              meta_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_kind ON documents(kind)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
              user_id TEXT PRIMARY KEY,
              email TEXT,
              full_name TEXT,
              headline TEXT,
              base_resume_id TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_records (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              company TEXT,
              position TEXT,
              job_url TEXT,
              job_description TEXT NOT NULL,
              match_score REAL NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'draft',
              base_resume_id TEXT,
              resume_id TEXT,
              cover_letter TEXT,
              meta_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_monthly (
              user_id TEXT NOT NULL,
              period_yyyymm TEXT NOT NULL,
              llm_prompt_tokens INTEGER NOT NULL DEFAULT 0,
              llm_completion_tokens INTEGER NOT NULL DEFAULT 0,
              base_resume_uploads INTEGER NOT NULL DEFAULT 0,
              applications_created INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (user_id, period_yyyymm)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_app_records_user ON application_records(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_app_records_created ON application_records(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_monthly(period_yyyymm)")
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=True)
class StoredDocument:
    id: str
    kind: str
    owner_user_id: str
    filename: str | None
    content_type: str | None
    file_path: str | None
    text: str
    created_at: str
    meta: dict[str, Any]


def create_document(
    *,
    kind: str,
    owner_user_id: str,
    text: str,
    filename: str | None = None,
    content_type: str | None = None,
    file_path: str | None = None,
    meta: dict[str, Any] | None = None,
) -> StoredDocument:
    doc_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    meta_json = json.dumps(meta or {}, ensure_ascii=True)

    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO documents (
              id, kind, owner_user_id, filename, content_type, file_path, text, created_at, meta_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, kind, owner_user_id, filename, content_type, file_path, text, created_at, meta_json),
        )
        conn.commit()
    finally:
        conn.close()

    return StoredDocument(
        id=doc_id,
        kind=kind,
        owner_user_id=owner_user_id,
        filename=filename,
        content_type=content_type,
        file_path=file_path,
        text=text,
        created_at=created_at,
        meta=meta or {},
    )


def get_document(*, doc_id: str, owner_user_id: str) -> StoredDocument | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ? AND owner_user_id = ? LIMIT 1",
            (doc_id, owner_user_id),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
    return StoredDocument(
        id=row["id"],
        kind=row["kind"],
        owner_user_id=row["owner_user_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        file_path=row["file_path"],
        text=row["text"],
        created_at=row["created_at"],
        meta=meta,
    )


def list_documents(
    *, owner_user_id: str, kind: str | None = None, limit: int = 200
) -> list[StoredDocument]:
    """List documents for a user, newest first."""
    conn = get_conn()
    try:
        if kind:
            rows = conn.execute(
                """
                SELECT * FROM documents
                WHERE owner_user_id = ? AND kind = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_user_id, kind, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM documents
                WHERE owner_user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (owner_user_id, limit),
            ).fetchall()
    finally:
        conn.close()

    out: list[StoredDocument] = []
    for row in rows:
        meta = json.loads(row["meta_json"]) if row["meta_json"] else {}
        out.append(
            StoredDocument(
                id=row["id"],
                kind=row["kind"],
                owner_user_id=row["owner_user_id"],
                filename=row["filename"],
                content_type=row["content_type"],
                file_path=row["file_path"],
                text=row["text"],
                created_at=row["created_at"],
                meta=meta,
            )
        )
    return out


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    email: str | None
    full_name: str | None
    headline: str | None
    base_resume_id: str | None
    created_at: str
    updated_at: str


def get_user_profile(*, user_id: str) -> UserProfile | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return UserProfile(
        user_id=row["user_id"],
        email=row["email"],
        full_name=row["full_name"],
        headline=row["headline"],
        base_resume_id=row["base_resume_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def upsert_user_profile(
    *,
    user_id: str,
    email: str | None = None,
    full_name: str | None = None,
    headline: str | None = None,
    base_resume_id: str | None = None,
) -> UserProfile:
    now = datetime.now(UTC).isoformat()
    existing = get_user_profile(user_id=user_id)
    conn = get_conn()
    try:
        if existing is None:
            conn.execute(
                """
                INSERT INTO user_profiles
                  (user_id, email, full_name, headline, base_resume_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email, full_name, headline, base_resume_id, now, now),
            )
        else:
            conn.execute(
                """
                UPDATE user_profiles
                SET email = COALESCE(?, email),
                    full_name = COALESCE(?, full_name),
                    headline = COALESCE(?, headline),
                    base_resume_id = COALESCE(?, base_resume_id),
                    updated_at = ?
                WHERE user_id = ?
                """,
                (email, full_name, headline, base_resume_id, now, user_id),
            )
        conn.commit()
    finally:
        conn.close()
    p = get_user_profile(user_id=user_id)
    assert p is not None
    return p


@dataclass(frozen=True)
class ApplicationRecord:
    id: str
    user_id: str
    company: str | None
    position: str | None
    job_url: str | None
    job_description: str
    match_score: float
    status: str
    base_resume_id: str | None
    resume_id: str | None
    cover_letter: str | None
    meta: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class UsageSnapshot:
    user_id: str
    period_yyyymm: str
    llm_prompt_tokens: int
    llm_completion_tokens: int
    base_resume_uploads: int
    applications_created: int

    @property
    def total_llm_tokens(self) -> int:
        return self.llm_prompt_tokens + self.llm_completion_tokens


def current_period_yyyymm() -> str:
    now = datetime.now(UTC)
    return f"{now.year:04d}{now.month:02d}"


def create_application(
    *,
    user_id: str,
    company: str | None,
    position: str | None,
    job_url: str | None,
    job_description: str,
    match_score: float,
    status: str,
    base_resume_id: str | None,
    resume_id: str | None,
    cover_letter: str | None,
    meta: dict[str, Any] | None = None,
) -> ApplicationRecord:
    app_id = str(uuid4())
    created_at = datetime.now(UTC).isoformat()
    meta_json = json.dumps(meta or {}, ensure_ascii=True)
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO application_records (
                id, user_id, company, position, job_url, job_description,
                match_score, status, base_resume_id, resume_id, cover_letter, meta_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                app_id,
                user_id,
                company,
                position,
                job_url,
                job_description,
                match_score,
                status,
                base_resume_id,
                resume_id,
                cover_letter,
                meta_json,
                created_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    r = get_application(app_id=app_id, user_id=user_id)
    assert r is not None
    return r


def get_application(*, app_id: str, user_id: str) -> ApplicationRecord | None:
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT * FROM application_records
            WHERE id = ? AND user_id = ? LIMIT 1
            """,
            (app_id, user_id),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return _row_to_application(row)


def list_applications(
    *, user_id: str, limit: int = 100
) -> list[ApplicationRecord]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM application_records
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_application(r) for r in rows]


def _row_to_application(row: sqlite3.Row) -> ApplicationRecord:
    raw = row["meta_json"] or "{}"
    meta: dict[str, Any] = json.loads(raw) if raw else {}
    return ApplicationRecord(
        id=row["id"],
        user_id=row["user_id"],
        company=row["company"],
        position=row["position"],
        job_url=row["job_url"],
        job_description=row["job_description"],
        match_score=float(row["match_score"] or 0),
        status=row["status"] or "draft",
        base_resume_id=row["base_resume_id"],
        resume_id=row["resume_id"],
        cover_letter=row["cover_letter"],
        meta=meta,
        created_at=row["created_at"],
    )


def update_document_meta(
    *, doc_id: str, owner_user_id: str, meta_patch: dict[str, Any]
) -> StoredDocument | None:
    """Merge meta_patch into the document's meta JSON."""
    doc = get_document(doc_id=doc_id, owner_user_id=owner_user_id)
    if not doc:
        return None
    merged = {**doc.meta, **meta_patch}
    meta_json = json.dumps(merged, ensure_ascii=True)
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE documents SET meta_json = ? WHERE id = ? AND owner_user_id = ?",
            (meta_json, doc_id, owner_user_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_document(doc_id=doc_id, owner_user_id=owner_user_id)


def dashboard_aggregates(*, user_id: str) -> dict[str, int | float]:
    """Pre-computed dashboard numbers for a user (SQLite; swap for warehouse in prod)."""
    conn = get_conn()
    try:
        n_apps = conn.execute(
            "SELECT COUNT(*) AS c FROM application_records WHERE user_id = ?",
            (user_id,),
        ).fetchone()["c"]
        n_interview = conn.execute(
            "SELECT COUNT(*) AS c FROM application_records WHERE user_id = ? AND status = 'interview'",
            (user_id,),
        ).fetchone()["c"]
        score_row = conn.execute(
            """
            SELECT AVG(match_score) AS a FROM application_records
            WHERE user_id = ? AND match_score > 0
            """,
            (user_id,),
        ).fetchone()
        avg = score_row["a"] if score_row and score_row["a"] is not None else 0.0
        n_tailored = conn.execute(
            "SELECT COUNT(*) AS c FROM documents WHERE owner_user_id = ? AND kind = 'resume'",
            (user_id,),
        ).fetchone()["c"]
    finally:
        conn.close()
    return {
        "applications": int(n_apps),
        "interviews": int(n_interview),
        "average_match_score": float(avg) if avg else 0.0,
        "resumes_generated": int(n_tailored),
    }


def get_usage_snapshot(*, user_id: str, period_yyyymm: str | None = None) -> UsageSnapshot:
    period = period_yyyymm or current_period_yyyymm()
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT user_id, period_yyyymm, llm_prompt_tokens, llm_completion_tokens,
                   base_resume_uploads, applications_created
            FROM usage_monthly
            WHERE user_id = ? AND period_yyyymm = ?
            LIMIT 1
            """,
            (user_id, period),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return UsageSnapshot(
            user_id=user_id,
            period_yyyymm=period,
            llm_prompt_tokens=0,
            llm_completion_tokens=0,
            base_resume_uploads=0,
            applications_created=0,
        )
    return UsageSnapshot(
        user_id=row["user_id"],
        period_yyyymm=row["period_yyyymm"],
        llm_prompt_tokens=int(row["llm_prompt_tokens"] or 0),
        llm_completion_tokens=int(row["llm_completion_tokens"] or 0),
        base_resume_uploads=int(row["base_resume_uploads"] or 0),
        applications_created=int(row["applications_created"] or 0),
    )


def bump_usage(
    *,
    user_id: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    base_resume_uploads: int = 0,
    applications_created: int = 0,
    period_yyyymm: str | None = None,
) -> UsageSnapshot:
    period = period_yyyymm or current_period_yyyymm()
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO usage_monthly (
                user_id, period_yyyymm, llm_prompt_tokens, llm_completion_tokens,
                base_resume_uploads, applications_created, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, period_yyyymm) DO UPDATE SET
                llm_prompt_tokens = llm_prompt_tokens + excluded.llm_prompt_tokens,
                llm_completion_tokens = llm_completion_tokens + excluded.llm_completion_tokens,
                base_resume_uploads = base_resume_uploads + excluded.base_resume_uploads,
                applications_created = applications_created + excluded.applications_created,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                period,
                max(0, int(prompt_tokens)),
                max(0, int(completion_tokens)),
                max(0, int(base_resume_uploads)),
                max(0, int(applications_created)),
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_usage_snapshot(user_id=user_id, period_yyyymm=period)
