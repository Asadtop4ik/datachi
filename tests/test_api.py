"""Faza 0 darvozasi: /health. Faza 4 darvozasi: /chat to'liq javob (LLM mock bilan integration)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import text

from src.agent.analyst import analyst_agent
from src.api.main import app
from src.db import get_app_engine, get_biz_readonly_engine
from src.safe_sql import validate_sql
from tests.conftest import skip_if_db_down

GOLDEN_SQL = "SELECT city, count(*) AS n FROM customers GROUP BY city ORDER BY n DESC"
GOLDEN_SPEC = {"mark": "bar", "encoding": {"x": {"field": "city"}, "y": {"field": "n"}}}


def _scripted(messages: list, info: AgentInfo) -> ModelResponse:
    n = sum(1 for m in messages for p in getattr(m, "parts", []) if isinstance(p, ToolReturnPart))
    if n == 0:
        return ModelResponse(parts=[ToolCallPart("run_sql", {"sql": GOLDEN_SQL})])
    if n == 1:
        return ModelResponse(
            parts=[
                ToolCallPart("make_chart", {"title": "Shahar bo'yicha", "vega_spec": GOLDEN_SPEC})
            ]
        )
    out_tool = info.output_tools[0].name
    return ModelResponse(
        parts=[
            ToolCallPart(
                out_tool,
                {
                    "text": "Toshkent eng ko'p mijozga ega.",
                    "chart_title": "Shahar bo'yicha",
                    "vega_spec": None,
                },
            )
        ]
    )


def test_health() -> None:
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_full_response() -> None:
    skip_if_db_down(get_app_engine())
    skip_if_db_down(get_biz_readonly_engine())
    client = TestClient(app)
    with analyst_agent.override(model=FunctionModel(_scripted)):
        resp = client.post("/chat", json={"message": "Shahar bo'yicha mijozlar?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"] > 0
    assert body["text"]
    assert body["sql"] is not None
    validate_sql(body["sql"])
    assert len(body["rows"]) > 0
    assert body["vega_spec"]["mark"] == "bar"
    assert body["chart_title"]
    assert body["error_detail"] is None

    # Tarix app DB'ga yozildi: user + assistant = 2 ta xabar.
    with get_app_engine().connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM messages WHERE conversation_id = :c"),
            {"c": body["conversation_id"]},
        ).scalar_one()
    assert count == 2


def test_chat_empty_message_rejected() -> None:
    client = TestClient(app)
    resp = client.post("/chat", json={"message": "   "})
    assert resp.status_code in (400, 422)


def test_chat_unknown_conversation_404() -> None:
    skip_if_db_down(get_app_engine())
    client = TestClient(app)
    with analyst_agent.override(model=FunctionModel(_scripted)):
        resp = client.post("/chat", json={"message": "test", "conversation_id": 999_999_999})
    assert resp.status_code == 404
