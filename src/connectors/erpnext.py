"""ERPNext (Frappe REST) konnektori — STUB (Faza 6).

Jonli ERPNext instance + token bo'lganda ulanadi: GET /api/resource/<DocType>,
sarlavha `Authorization: token <key>:<secret>`. Demo uchun SHART EMAS (sintetik bazada ishlaydi).
Interfeysga moslik uchun mavjud; jonli ulanishsiz so'rovlar muloyim RuntimeError beradi.
"""

from __future__ import annotations

from typing import Any

import requests

from src.connectors.base import Connector, SchemaInfo
from src.safe_sql import SqlResult

# ERPNext DocType -> demo_biz jadval nomi (kelajakdagi mapping uchun namuna).
DOCTYPE_BY_TABLE = {
    "customers": "Customer",
    "items": "Item",
    "sales_invoices": "Sales Invoice",
    "sales_invoice_items": "Sales Invoice Item",
}


class ERPNextConnector(Connector):
    name = "erpnext"

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        api_secret: str = "",
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    @property
    def is_live(self) -> bool:
        return bool(self.base_url and self.api_key and self.api_secret)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"token {self.api_key}:{self.api_secret}"}

    def _require_live(self) -> None:
        if not self.is_live:
            raise RuntimeError(
                "ERPNext konnektori jonli instance + token talab qiladi "
                "(base_url, api_key, api_secret). Demo sintetik bazada ishlaydi."
            )

    def list_tables(self) -> list[str]:
        return list(DOCTYPE_BY_TABLE.keys())

    def get_schema(self, table: str) -> SchemaInfo:
        self._require_live()
        doctype = DOCTYPE_BY_TABLE.get(table)
        if doctype is None:
            raise ValueError(f"Noma'lum jadval: {table!r}")
        # Jonli: GET /api/resource/<DocType>?limit_page_length=5
        url = f"{self.base_url}/api/resource/{doctype.replace(' ', '%20')}"
        resp = requests.get(
            url,
            headers=self._headers(),
            params={"limit_page_length": 5},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json().get("data", [])
        columns = [{"name": k, "type": "unknown"} for k in (data[0].keys() if data else [])]
        return SchemaInfo(table=table, columns=columns, sample_rows=data)

    def run_sql(self, sql: str) -> SqlResult:  # noqa: ARG002
        # Frappe REST xom SQL'ni ochib bermaydi; jonli integratsiya report/query API
        # orqali bo'ladi — bu demo doirasidan tashqarida.
        raise NotImplementedError(
            "ERPNext konnektori xom SQL bajarmaydi (Frappe REST). Demo demo_biz'da ishlaydi."
        )
