"""Grafik validatsiya + fallback (ADR-0003) — LLM'siz, sof birlik testlari."""

from __future__ import annotations

from src.agent.charts import ALLOWED_MARKS, build_chart

ROWS = [{"city": "Toshkent", "n": 200}, {"city": "Samarqand", "n": 100}]
COLS = ["city", "n"]


def test_valid_llm_spec_passes_and_injects_data() -> None:
    spec = build_chart(
        "By city",
        {"mark": "bar", "encoding": {"x": {"field": "city"}, "y": {"field": "n"}}},
        ROWS,
        COLS,
    )
    assert spec is not None
    assert spec["mark"] == "bar"
    assert spec["data"]["values"] == ROWS  # server haqiqiy qatorlarni in'ektsiya qildi
    assert spec["title"] == "By city"


def test_bad_mark_falls_back_to_bar() -> None:
    spec = build_chart("x", {"mark": "treemap", "encoding": {"x": {"field": "city"}}}, ROWS, COLS)
    assert spec is not None
    assert spec["mark"] == "bar"  # fallback


def test_non_dict_spec_falls_back() -> None:
    spec = build_chart("x", "not-a-spec", ROWS, COLS)
    assert spec is not None
    assert spec["mark"] == "bar"


def test_missing_encoding_falls_back() -> None:
    spec = build_chart("x", {"mark": "bar"}, ROWS, COLS)
    assert spec is not None
    assert spec["mark"] == "bar"


def test_no_rows_returns_none() -> None:
    assert build_chart("x", {"mark": "bar", "encoding": {"x": {}}}, [], COLS) is None


def test_single_column_returns_none() -> None:
    rows = [{"only": 1}, {"only": 2}]
    assert build_chart("x", "bad", rows, ["only"]) is None


def test_allowed_marks_pass_through() -> None:
    for mark in ALLOWED_MARKS:
        spec = build_chart("t", {"mark": mark, "encoding": {"x": {"field": "city"}}}, ROWS, COLS)
        assert spec is not None
        assert spec["mark"] == mark
