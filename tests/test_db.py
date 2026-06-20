"""Faza 1 darvozasi: app jadvallari mavjud, biz seed to'lgan, readonly rol yoza olmaydi.

Bu testlar jonli DB talab qiladi (docker compose up -d postgres + alembic upgrade + seed).
DB yo'q bo'lsa skip.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import inspect, text

from src.db import get_app_engine, get_biz_engine, get_biz_readonly_engine
from tests.conftest import skip_if_db_down

APP_TABLES = {"conversations", "messages", "saved_charts"}
BIZ_TABLES = ["customers", "items", "sales_invoices", "sales_invoice_items"]


def test_app_tables_exist() -> None:
    engine = get_app_engine()
    skip_if_db_down(engine)
    names = set(inspect(engine).get_table_names())
    assert APP_TABLES.issubset(names), f"yetishmayotgan jadvallar: {APP_TABLES - names}"


def test_biz_tables_seeded() -> None:
    engine = get_biz_engine()
    skip_if_db_down(engine)
    with engine.connect() as conn:
        for table in BIZ_TABLES:
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            assert count > 0, f"{table} bo'sh"


def test_readonly_cannot_insert() -> None:
    engine = get_biz_readonly_engine()
    skip_if_db_down(engine)
    with engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "INSERT INTO customers (id, name, city, segment) "
                    "VALUES (999999, 'X', 'Toshkent', 'SMB')"
                )
            )
            conn.commit()
        except sa.exc.DBAPIError:
            return  # kutilgan: ruxsat yo'q
        raise AssertionError("readonly_user INSERT qila oldi — bu XAVFSIZLIK buzilishi!")
