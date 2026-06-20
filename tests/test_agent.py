"""Faza 3 darvozasi: agent VALID SELECT + valid Vega-Lite spec qaytaradi (jonli kalitsiz).

FunctionModel bilan tool-chaqiruv mantig'ini boshqaramiz (BUILD_PLAN §16). run_sql jonli
demo_biz'da bajariladi (DB kerak; yo'q bo'lsa skip). Jonli LLM smoke testi RUN_LIVE_LLM=1 bilan.
"""

from __future__ import annotations

import os

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.agent.analyst import build_agent, run_analysis
from src.agent.charts import ALLOWED_MARKS
from src.connectors.demo import DemoConnector
from src.db import get_biz_readonly_engine
from src.safe_sql import validate_sql
from tests.conftest import skip_if_db_down

GOLDEN = [
    (
        "Shahar bo'yicha mijozlar soni",
        "SELECT city, count(*) AS n FROM customers GROUP BY city ORDER BY n DESC",
        {"mark": "bar", "encoding": {"x": {"field": "city"}, "y": {"field": "n"}}},
        "bar",
    ),
    (
        "Top 10 mahsulot tushum bo'yicha",
        "SELECT i.name, SUM(sii.amount_uzs) AS revenue "
        "FROM sales_invoice_items sii JOIN items i ON i.id = sii.item_id "
        "GROUP BY i.name ORDER BY revenue DESC LIMIT 10",
        {"mark": "bar", "encoding": {"x": {"field": "name"}, "y": {"field": "revenue"}}},
        "bar",
    ),
    (
        "Oylik savdo trendi",
        "SELECT date_trunc('month', posting_date) AS month, SUM(total_uzs) AS revenue "
        "FROM sales_invoices GROUP BY 1 ORDER BY 1",
        {"mark": "line", "encoding": {"x": {"field": "month"}, "y": {"field": "revenue"}}},
        "line",
    ),
]


def _count_returns(messages: list) -> int:
    return sum(
        1 for m in messages for p in getattr(m, "parts", []) if isinstance(p, ToolReturnPart)
    )


def _scripted_model(sql: str, spec: dict) -> FunctionModel:
    """run_sql -> make_chart -> final_result ketma-ketligini ijro etadi."""

    def func(messages: list, info: AgentInfo) -> ModelResponse:
        n = _count_returns(messages)
        if n == 0:
            return ModelResponse(parts=[ToolCallPart("run_sql", {"sql": sql})])
        if n == 1:
            return ModelResponse(
                parts=[ToolCallPart("make_chart", {"title": "Demo", "vega_spec": spec})]
            )
        out_tool = info.output_tools[0].name
        return ModelResponse(
            parts=[
                ToolCallPart(
                    out_tool,
                    {"text": "Natija tayyor.", "chart_title": "Demo", "vega_spec": None},
                )
            ]
        )

    return FunctionModel(func)


@pytest.mark.parametrize("question,sql,spec,expected_mark", GOLDEN)
def test_golden_question_valid_sql_and_chart(
    question: str, sql: str, spec: dict, expected_mark: str
) -> None:
    skip_if_db_down(get_biz_readonly_engine())
    agent = build_agent(model=_scripted_model(sql, spec))
    outcome = run_analysis(question, connector=DemoConnector(), agent=agent, require_key=False)
    assert outcome.error_detail is None
    assert outcome.text
    assert outcome.sql is not None
    validate_sql(outcome.sql)  # bajarilgan SQL haqiqatan ham yaroqli SELECT
    assert outcome.rows, "natija qatorlari bo'sh"
    assert outcome.vega_spec is not None
    assert outcome.vega_spec["mark"] == expected_mark
    assert outcome.vega_spec["mark"] in ALLOWED_MARKS


def test_tool_call_cap_returns_polite_error() -> None:
    def runaway(messages: list, info: AgentInfo) -> ModelResponse:
        # Hech qachon tugatmaydi -> cap'ga uriladi.
        return ModelResponse(parts=[ToolCallPart("list_tables", {})])

    agent = build_agent(model=FunctionModel(runaway))
    outcome = run_analysis("cheksiz", connector=DemoConnector(), agent=agent, require_key=False)
    assert outcome.vega_spec is None
    assert outcome.error_detail is not None
    assert "cap" in outcome.error_detail.lower()
    assert outcome.text  # muloyim matn, crash emas


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM") != "1",
    reason="jonli LLM smoke faqat RUN_LIVE_LLM=1 bilan (ixtiyoriy, BUILD_PLAN §16)",
)
def test_live_smoke() -> None:
    skip_if_db_down(get_biz_readonly_engine())
    outcome = run_analysis("Shahar bo'yicha umumiy tushum qancha?")
    assert outcome.text
    if outcome.sql:
        validate_sql(outcome.sql)
