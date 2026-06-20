"""Faza 2 darvozasi: validate_sql DML/DDL/multi-statement/komment-inyeksiyani bloklaydi,
oddiy SELECT'ga ruxsat beradi, LIMIT majburlaydi. run_sql read-only DB'da ishlaydi.
"""

from __future__ import annotations

import pytest

from src.db import get_biz_readonly_engine
from src.safe_sql import MAX_LIMIT, SafeSqlError, run_sql, validate_sql
from tests.conftest import skip_if_db_down

BLOCKED = [
    "DROP TABLE customers",
    "SELECT 1; DELETE FROM customers",
    "UPDATE customers SET city = 'X'",
    "DELETE FROM customers",
    "INSERT INTO customers (id) VALUES (1)",
    "TRUNCATE TABLE customers",
    "ALTER TABLE customers ADD COLUMN x int",
    "SELECT * FROM customers; DROP TABLE customers",
    "SELECT * INTO new_t FROM customers",
    "",
    "   ",
]


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked_statements(sql: str) -> None:
    with pytest.raises(SafeSqlError):
        validate_sql(sql)


def test_simple_select_allowed() -> None:
    out = validate_sql("SELECT name, city FROM customers")
    assert "SELECT" in out.upper()


def test_limit_injected_when_missing() -> None:
    out = validate_sql("SELECT * FROM customers")
    assert f"LIMIT {MAX_LIMIT}" in out.upper()


def test_limit_clamped_when_too_large() -> None:
    out = validate_sql("SELECT * FROM customers LIMIT 999999")
    assert "999999" not in out
    assert f"LIMIT {MAX_LIMIT}" in out.upper()


def test_small_limit_kept() -> None:
    out = validate_sql("SELECT * FROM customers LIMIT 10")
    assert "LIMIT 10" in out.upper()


def test_line_comment_injection_dies() -> None:
    out = validate_sql("SELECT id FROM customers -- ; DROP TABLE customers")
    assert "DROP" not in out.upper()


def test_block_comment_injection_dies() -> None:
    out = validate_sql("SELECT id /* ; DROP TABLE customers */ FROM customers")
    assert "DROP" not in out.upper()


def test_cte_with_dml_blocked() -> None:
    with pytest.raises(SafeSqlError):
        validate_sql("WITH x AS (DELETE FROM customers RETURNING id) SELECT * FROM x")


def test_run_sql_rejects_dml_before_db() -> None:
    with pytest.raises(SafeSqlError):
        run_sql("DELETE FROM customers")


def test_run_sql_returns_rows() -> None:
    skip_if_db_down(get_biz_readonly_engine())
    res = run_sql("SELECT city, count(*) AS n FROM customers GROUP BY city ORDER BY n DESC")
    assert res.row_count > 0
    assert "city" in res.columns
    assert len(res.rows) <= MAX_LIMIT
    assert f"LIMIT {MAX_LIMIT}" in res.sql.upper()
