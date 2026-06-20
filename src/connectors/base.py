"""Connector interfeysi (CONTEXT.md): biznes datasetini Analyst Agent'ga ochuvchi chegara.

Demo sintetik konnektor (demo.py) va jonli ERPNext konnektori (erpnext.py) shu interfeysni
bajaradi. Agent FAQAT shu chegara orqali ma'lumotga tegadi.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.safe_sql import SqlResult


@dataclass
class SchemaInfo:
    table: str
    columns: list[dict[str, str]]  # [{"name": ..., "type": ...}]
    sample_rows: list[dict[str, Any]] = field(default_factory=list)


class Connector(ABC):
    """Biznes dataset chegarasi."""

    name: str = "base"

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Mavjud jadval (yoki doctype) nomlari."""

    @abstractmethod
    def get_schema(self, table: str) -> SchemaInfo:
        """Ustunlar + bir nechta jonli namuna qator."""

    @abstractmethod
    def run_sql(self, sql: str) -> SqlResult:
        """Xavfsiz, read-only so'rovni bajaradi va natijani qaytaradi."""
