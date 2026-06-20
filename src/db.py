"""DB enginelari: app (metadata), biz (seed yozish), biz-readonly (agent o'qishi).

Agent biznes bazasiga FAQAT readonly engine orqali ulanadi (CLAUDE.md invarianti).
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import get_settings


@lru_cache
def get_app_engine() -> Engine:
    """App metadata bazasi (conversations, messages, saved_charts)."""
    return create_engine(get_settings().database_url_app, pool_pre_ping=True, future=True)


@lru_cache
def get_biz_engine() -> Engine:
    """Biznes bazasi, analytics roli — FAQAT seed yozishi uchun (read-write)."""
    return create_engine(get_settings().database_url_biz, pool_pre_ping=True, future=True)


@lru_cache
def get_biz_readonly_engine() -> Engine:
    """Biznes bazasi, readonly_user — agent SHU bilan o'qiydi."""
    return create_engine(get_settings().database_url_biz_readonly, pool_pre_ping=True, future=True)
