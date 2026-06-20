"""Insight darvozasi: qatorlardan deterministik KPI (jami, ulush %, trend ±%). DB/LLM kerak emas."""

from __future__ import annotations

from src.agent.insights import _fmt, derive_insights


def test_fmt_abbreviations() -> None:
    assert _fmt(186) == "186"
    assert _fmt(7800) == "7.8 ming"
    assert _fmt(4_500_000) == "4.5 mln"
    assert _fmt(12_300_000_000) == "12.3 mlrd"


def test_categorical_total_leader_share() -> None:
    rows = [{"city": "A", "n": 75}, {"city": "B", "n": 25}]
    metrics = derive_insights(rows, ["city", "n"])
    labels = {m["label"]: m for m in metrics}
    assert labels["Jami"]["value"] == "100"
    assert labels["Yetakchi: A"]["value"] == "75"
    assert labels["Yetakchi ulush"]["value"] == "75%"


def test_time_series_trend_delta() -> None:
    rows = [
        {"month": "2026-01-01", "revenue": 100},
        {"month": "2026-02-01", "revenue": 112},
    ]
    metrics = derive_insights(rows, ["month", "revenue"])
    labels = {m["label"]: m for m in metrics}
    assert labels["Jami"]["value"] == "212"
    assert labels["Oxirgi davr"]["delta"] == "+12%"
    assert "Eng yuqori" in labels


def test_time_series_negative_trend() -> None:
    rows = [
        {"month": "2026-01-01", "revenue": 200},
        {"month": "2026-02-01", "revenue": 150},
    ]
    metrics = derive_insights(rows, ["month", "revenue"])
    last = next(m for m in metrics if m["label"] == "Oxirgi davr")
    assert last["delta"] == "-25%"


def test_single_value() -> None:
    metrics = derive_insights([{"avg": 4_500_000}], ["avg"])
    assert len(metrics) == 1
    assert metrics[0]["value"] == "4.5 mln"


def test_average_across_categories_no_total() -> None:
    rows = [{"city": "A", "avg_check": 100}, {"city": "B", "avg_check": 200}]
    metrics = derive_insights(rows, ["city", "avg_check"])
    labels = {m["label"]: m for m in metrics}
    assert "Jami" not in labels  # o'rtacha yig'indisi ma'nosiz
    assert labels["Eng yuqori: B"]["value"] == "200"
    assert labels["O'rtacha"]["value"] == "150"


def test_empty_and_non_numeric_return_no_metrics() -> None:
    assert derive_insights([], []) == []
    assert derive_insights([], ["a"]) == []
    assert derive_insights([{"city": "A"}, {"city": "B"}], ["city"]) == []
