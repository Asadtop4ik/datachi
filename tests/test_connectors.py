"""Faza 6 darvozasi: demo va erpnext konnektorlari bir interfeysni (Connector) bajaradi."""

from __future__ import annotations

import pytest

from src.connectors.base import Connector, SchemaInfo
from src.connectors.demo import ALLOWED_TABLES, DemoConnector
from src.connectors.erpnext import DOCTYPE_BY_TABLE, ERPNextConnector
from src.db import get_biz_readonly_engine
from tests.conftest import skip_if_db_down


def test_both_implement_interface() -> None:
    demo = DemoConnector()
    erp = ERPNextConnector()
    assert isinstance(demo, Connector)
    assert isinstance(erp, Connector)
    for conn in (demo, erp):
        assert callable(conn.list_tables)
        assert callable(conn.get_schema)
        assert callable(conn.run_sql)


def test_demo_list_tables() -> None:
    assert DemoConnector().list_tables() == list(ALLOWED_TABLES)


def test_demo_get_schema() -> None:
    skip_if_db_down(get_biz_readonly_engine())
    info = DemoConnector().get_schema("customers")
    assert isinstance(info, SchemaInfo)
    names = {c["name"] for c in info.columns}
    assert {"id", "name", "city", "segment"}.issubset(names)
    assert len(info.sample_rows) > 0


def test_demo_get_schema_rejects_unknown_table() -> None:
    with pytest.raises(ValueError):
        DemoConnector().get_schema("secrets")


def test_demo_run_sql() -> None:
    skip_if_db_down(get_biz_readonly_engine())
    res = DemoConnector().run_sql("SELECT count(*) AS n FROM items")
    assert res.rows[0]["n"] > 0


def test_erpnext_list_tables_maps_doctypes() -> None:
    assert ERPNextConnector().list_tables() == list(DOCTYPE_BY_TABLE.keys())


def test_erpnext_not_live_without_creds() -> None:
    erp = ERPNextConnector()
    assert erp.is_live is False
    with pytest.raises(RuntimeError):
        erp.get_schema("customers")


def test_erpnext_run_sql_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        ERPNextConnector().run_sql("SELECT 1")


def test_erpnext_auth_header_format() -> None:
    erp = ERPNextConnector(base_url="https://erp.example", api_key="k", api_secret="s")
    assert erp.is_live is True
    assert erp._headers()["Authorization"] == "token k:s"
