"""Xavfsiz SQL qatlami (ADR-0002): sqlglot AST validatsiya + read-only executor.

Ikki qatlamli mudofaa:
  1) Postgres read-only rol (readonly_user) — asosiy himoya (db-init/init.sql).
  2) sqlglot AST validator — ikkinchi qatlam (shu fayl).

Qoidalar:
  - Aniq BITTA statement (';' bilan ko'p statement bloklangan).
  - Ildiz SELECT (yoki UNION / WIT...SELECT / subquery). DML/DDL node yo'q.
  - LIMIT AST darajasida majburlanadi (string concat EMAS), MAX_LIMIT ga clamp.
  - statement_timeout (15s) bajarishda o'rnatiladi.
  - Komment AST'dan generatsiyada tushib qoladi -> komment-inyeksiya o'ladi.
Regex qora ro'yxat ISHLATILMAYDI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import sqlglot
from sqlalchemy import text
from sqlglot import exp
from sqlglot.errors import ParseError, TokenError

from src.db import get_biz_readonly_engine

DIALECT = "postgres"
MAX_LIMIT = 1000
STATEMENT_TIMEOUT_MS = 15_000
LLM_ROW_CAP = 50  # LLM narrativi uchun faqat birinchi ~50 qator (BUILD_PLAN §8.10)

# DML/DDL va boshqa xavfli node turlari (versiyaga chidamli — hasattr bilan).
_FORBIDDEN_NAMES = [
    "Insert",
    "Update",
    "Delete",
    "Merge",
    "Drop",
    "Create",
    "Alter",
    "TruncateTable",
    "Command",
    "Set",
    "SetItem",
    "Use",
    "Copy",
    "Grant",
    "Revoke",
    "Pragma",
    "Call",
    "AlterTable",
    "Into",
]
_FORBIDDEN = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

# Ildizda ruxsat etilgan ifoda turlari.
_ALLOWED_ROOTS = tuple(
    getattr(exp, n)
    for n in ["Select", "Union", "Intersect", "Except", "SetOperation", "Subquery"]
    if hasattr(exp, n)
)


class SafeSqlError(ValueError):
    """SQL validatsiyadan o'tmadi."""


@dataclass
class SqlResult:
    sql: str  # bajarilgan yakuniy SQL (LIMIT bilan)
    columns: list[str]
    rows: list[dict[str, Any]]  # JSON-xavfsiz qiymatlar (<= LIMIT)
    row_count: int


def _parse_single(sql: str) -> exp.Expression:
    if not sql or not sql.strip():
        raise SafeSqlError("Bo'sh SQL.")
    try:
        statements = sqlglot.parse(sql, read=DIALECT)
    except (ParseError, TokenError) as exc:
        raise SafeSqlError(f"SQL parse bo'lmadi: {exc}") from exc
    statements = [s for s in statements if s is not None]
    if len(statements) == 0:
        raise SafeSqlError("Statement topilmadi.")
    if len(statements) > 1:
        raise SafeSqlError("Faqat bitta SELECT statement ruxsat etiladi (';' bloklangan).")
    return statements[0]


def _ensure_select_only(statement: exp.Expression) -> None:
    if not isinstance(statement, _ALLOWED_ROOTS):
        raise SafeSqlError(f"Faqat SELECT ruxsat etiladi, topildi: {type(statement).__name__}.")
    # SELECT ... INTO (jadval yaratadi) bloklash.
    if isinstance(statement, exp.Select) and statement.args.get("into") is not None:
        raise SafeSqlError("SELECT ... INTO ruxsat etilmaydi.")
    # Daraxtning istalgan joyida DML/DDL node bo'lsa — rad.
    for node in statement.walk():
        if isinstance(node, _FORBIDDEN):
            raise SafeSqlError(f"Ruxsat etilmagan operatsiya: {type(node).__name__}.")


def _enforce_limit(statement: exp.Expression) -> exp.Expression:
    """LIMIT'ni AST darajasida majburlaydi va MAX_LIMIT ga clamp qiladi."""
    limit = statement.args.get("limit")
    if limit is None:
        return statement.limit(MAX_LIMIT)
    # Mavjud LIMIT'ni clamp qilamiz (raqam bo'lsa).
    expr = limit.expression if isinstance(limit, exp.Limit) else None
    try:
        current = int(expr.name) if expr is not None else None
    except (ValueError, AttributeError):
        current = None
    if current is None or current > MAX_LIMIT:
        return statement.limit(MAX_LIMIT)
    return statement


def validate_sql(sql: str) -> str:
    """Validatsiya qiladi va LIMIT bilan, kommentsiz, xavfsiz SQL string qaytaradi."""
    statement = _parse_single(sql)
    _ensure_select_only(statement)
    statement = _enforce_limit(statement)
    # comments=False -> komment-inyeksiya generatsiyada yo'qoladi.
    return statement.sql(dialect=DIALECT, comments=False)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        f = float(value)
        return int(f) if f.is_integer() else f
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def run_sql(sql: str) -> SqlResult:
    """SQL'ni validatsiya qilib, read-only ulanishda timeout bilan bajaradi."""
    safe = validate_sql(sql)
    engine = get_biz_readonly_engine()
    with engine.connect() as conn:
        conn.execute(text(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}"))
        result = conn.execute(text(safe))
        columns = list(result.keys())
        rows = [{k: _jsonable(v) for k, v in row._mapping.items()} for row in result]
    return SqlResult(sql=safe, columns=columns, rows=rows, row_count=len(rows))
