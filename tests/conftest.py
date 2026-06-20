"""Umumiy test yordamchilari. DB yetib bo'lmasa testlar skip qilinadi (hard-fail emas)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine


@pytest.fixture(autouse=True)
def _isolate_demo_cache(tmp_path_factory, monkeypatch):
    """Demo keshini tmp faylga yo'naltiradi — production demo_cache.json ifloslanmasin."""
    from src.agent import analyst
    from src.agent import cache as cache_mod

    path = tmp_path_factory.mktemp("democache") / "demo_cache.json"
    monkeypatch.setattr(cache_mod, "DEFAULT_CACHE_PATH", path)
    analyst.get_demo_cache.cache_clear()
    yield
    analyst.get_demo_cache.cache_clear()


def skip_if_db_down(engine: Engine) -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"DB ulanib bo'lmadi (docker compose up -d postgres?): {exc}")
