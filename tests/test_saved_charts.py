"""Chart saqlash darvozasi: POST/GET/DELETE /charts (app DB kerak, LLM kerak emas)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import app
from src.db import get_app_engine
from tests.conftest import skip_if_db_down

SPEC = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "bar",
    "encoding": {"x": {"field": "city"}, "y": {"field": "n"}},
    "data": {"values": [{"city": "Toshkent", "n": 200}]},
}


def test_save_list_delete_chart() -> None:
    skip_if_db_down(get_app_engine())
    client = TestClient(app)

    resp = client.post(
        "/charts", json={"title": "Test grafik", "vega_spec": SPEC, "sql": "SELECT 1"}
    )
    assert resp.status_code == 201
    body = resp.json()
    chart_id = body["id"]
    assert body["title"] == "Test grafik"
    assert body["vega_spec"] == SPEC
    assert body["created_at"]

    try:
        listed = client.get("/charts").json()
        got = next((c for c in listed if c["id"] == chart_id), None)
        assert got is not None
        assert got["title"] == "Test grafik"
        assert got["sql"] == "SELECT 1"
    finally:
        deleted = client.delete(f"/charts/{chart_id}")
        assert deleted.status_code == 204

    listed_after = client.get("/charts").json()
    assert all(c["id"] != chart_id for c in listed_after)


def test_delete_missing_chart_404() -> None:
    skip_if_db_down(get_app_engine())
    client = TestClient(app)
    assert client.delete("/charts/999999999").status_code == 404


def test_save_chart_unknown_conversation_404() -> None:
    skip_if_db_down(get_app_engine())
    client = TestClient(app)
    resp = client.post(
        "/charts",
        json={"title": "x", "vega_spec": SPEC, "conversation_id": 999_999_999},
    )
    assert resp.status_code == 404


def test_save_chart_empty_title_rejected() -> None:
    client = TestClient(app)
    resp = client.post("/charts", json={"title": "", "vega_spec": SPEC})
    assert resp.status_code == 422
