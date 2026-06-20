"""Konfiguratsiya: .env o'qiydi. DB URL'lari env'dan (default'lar docker-compose'ga mos).

Qoida (CLAUDE.md): INSON faqat GOOGLE_API_KEY ni qo'yadi. Agar bo'sh bo'lsa — O'YLAB TOPMA,
balandovoz RuntimeError. Kalit FAQAT agent yaratilganda talab qilinadi (import vaqtida emas),
shunda safe_sql/db testlari kalitsiz ham ishlaydi.
"""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"

# Default'lar docker-compose.yml dagi qiymatlarga MOS keladi.
_DEFAULTS = {
    "DATABASE_URL_APP": "postgresql+psycopg://analytics:analytics_dev_pw@localhost:5432/app",
    "DATABASE_URL_BIZ": "postgresql+psycopg://analytics:analytics_dev_pw@localhost:5432/demo_biz",
    "DATABASE_URL_BIZ_READONLY": (
        "postgresql+psycopg://readonly_user:readonly_pw@localhost:5432/demo_biz"
    ),
    "LLM_MODEL": "google-gla:gemini-2.5-flash",
    "API_URL": "http://localhost:8000",
}


def _ensure_env_file() -> None:
    """Agar .env yo'q bo'lsa, .env.example dan nusxa qiladi (Faza 0 talabi)."""
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        shutil.copyfile(ENV_EXAMPLE_PATH, ENV_PATH)


_ensure_env_file()
load_dotenv(ENV_PATH)


class Settings:
    """Yagona sozlamalar konteyneri."""

    def __init__(self) -> None:
        self.database_url_app = os.getenv("DATABASE_URL_APP", _DEFAULTS["DATABASE_URL_APP"])
        self.database_url_biz = os.getenv("DATABASE_URL_BIZ", _DEFAULTS["DATABASE_URL_BIZ"])
        self.database_url_biz_readonly = os.getenv(
            "DATABASE_URL_BIZ_READONLY", _DEFAULTS["DATABASE_URL_BIZ_READONLY"]
        )
        self.llm_model = os.getenv("LLM_MODEL", _DEFAULTS["LLM_MODEL"])
        self.api_url = os.getenv("API_URL", _DEFAULTS["API_URL"])
        self.anchor_date = os.getenv("ANCHOR_DATE", "").strip() or None
        self._google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()

    @property
    def google_api_key(self) -> str:
        return self._google_api_key

    @property
    def has_google_api_key(self) -> bool:
        return bool(self._google_api_key)

    def require_google_api_key(self) -> str:
        if not self._google_api_key:
            raise RuntimeError("GOOGLE_API_KEY .env da bo'sh — inson qo'yishi kerak")
        return self._google_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
