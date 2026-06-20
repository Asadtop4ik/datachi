"""Umumiy test yordamchilari. DB yetib bo'lmasa testlar skip qilinadi (hard-fail emas)."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def skip_if_db_down(engine: Engine) -> None:
    import pytest

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"DB ulanib bo'lmadi (docker compose up -d postgres?): {exc}")
