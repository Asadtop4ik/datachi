"""Grafik validatsiya + fallback + avto-tanlov (ADR-0003) — LLM'siz, sof birlik testlari."""

from __future__ import annotations

from typing import Any

from src.agent.charts import ALLOWED_MARKS, build_chart, choose_mark

ROWS = [{"city": "Toshkent", "n": 200}, {"city": "Samarqand", "n": 100}]
COLS = ["city", "n"]
TIME_ROWS = [{"month": "2026-01-01", "revenue": 100}, {"month": "2026-02-01", "revenue": 140}]
TIME_COLS = ["month", "revenue"]
SHARE_ROWS = [{"segment": "Enterprise", "rev": 60}, {"segment": "SMB", "rev": 40}]
SHARE_COLS = ["segment", "rev"]


def _mark(spec: dict[str, Any]) -> str:
    m = spec["mark"]
    return m["type"] if isinstance(m, dict) else m


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


# --- Avto-tanlov (choose_mark + fallback) ---


def test_choose_mark_time_series_line() -> None:
    assert choose_mark(TIME_ROWS, TIME_COLS) == "line"


def test_choose_mark_share_question_arc() -> None:
    assert choose_mark(SHARE_ROWS, SHARE_COLS, "Segmentlar ulushi qancha?") == "arc"


def test_choose_mark_default_bar() -> None:
    # Kategoriyali, ulush so'zi yo'q -> taqqoslash -> bar.
    assert choose_mark(ROWS, COLS, "Shahar bo'yicha mijozlar?") == "bar"


def test_choose_mark_share_too_many_slices_falls_back_to_bar() -> None:
    rows = [{"c": str(i), "v": i + 1} for i in range(12)]
    assert choose_mark(rows, ["c", "v"], "ulush") == "bar"


def test_fallback_auto_selects_line_for_temporal() -> None:
    spec = build_chart("Trend", "bad-spec", TIME_ROWS, TIME_COLS)
    assert spec is not None
    assert _mark(spec) == "line"


def test_fallback_auto_selects_arc_for_share() -> None:
    spec = build_chart("Ulush", "bad-spec", SHARE_ROWS, SHARE_COLS, question="segmentlar ulushi")
    assert spec is not None
    assert _mark(spec) == "arc"
    assert spec["encoding"]["theta"]["field"] == "rev"


def test_valid_llm_spec_overrides_auto_selection() -> None:
    # LLM aniq spec bersa, avto-tanlov ARALASHMAYDI (ADR-0003).
    spec = build_chart(
        "t",
        {"mark": "bar", "encoding": {"x": {"field": "month"}, "y": {"field": "revenue"}}},
        TIME_ROWS,
        TIME_COLS,
        question="trend",
    )
    assert spec["mark"] == "bar"
