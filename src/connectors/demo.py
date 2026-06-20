"""Sintetik demo_biz konnektori. Postgres read-only rol orqali o'qiydi.

Jadval nomlari qattiq allowlist'da — get_schema'da nom inyeksiyasiga yo'l qo'yilmaydi.
"""

from __future__ import annotations

from sqlalchemy import text

from src.connectors.base import Connector, SchemaInfo
from src.db import get_biz_readonly_engine
from src.safe_sql import SqlResult, run_sql

# demo_biz jadvallari (seed bilan mos).
ALLOWED_TABLES = ["customers", "items", "sales_invoices", "sales_invoice_items"]


class DemoConnector(Connector):
    name = "demo"

    def list_tables(self) -> list[str]:
        return list(ALLOWED_TABLES)

    def get_schema(self, table: str) -> SchemaInfo:
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Noma'lum jadval: {table!r}")
        engine = get_biz_readonly_engine()
        with engine.connect() as conn:
            col_rows = conn.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :t "
                    "ORDER BY ordinal_position"
                ),
                {"t": table},
            ).all()
        columns = [{"name": r[0], "type": r[1]} for r in col_rows]
        # Namuna qatorlar safe_sql orqali (table allowlist'da, xavfsiz).
        sample = run_sql(f"SELECT * FROM {table} LIMIT 5")
        return SchemaInfo(table=table, columns=columns, sample_rows=sample.rows)

    def run_sql(self, sql: str) -> SqlResult:
        return run_sql(sql)
