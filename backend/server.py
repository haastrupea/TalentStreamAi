"""Run the API locally with Uvicorn: ``python server.py`` or ``uv run python server.py``."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    from app.core.config import settings

    host = (settings.api_host or os.environ.get("API_HOST") or "0.0.0.0").strip()
    port = settings.api_port or int(os.environ.get("API_PORT", "8000"))
    reload = os.environ.get("UVICORN_RELOAD", "").lower() in ("1", "true", "yes")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
