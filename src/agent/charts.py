"""Grafik validatsiya + xavfsiz fallback (ADR-0003).

LLM Vega-Lite spec beradi; server tekshiradi va kerak bo'lsa fallback qiladi.
Demo HECH QACHON buzuq grafik chiqarmasin. Bu modul LLM'siz testlanadi.
"""

from __future__ import annotations

from typing import Any

ALLOWED_MARKS = {"bar", "line", "arc", "point"}
VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"


def _mark_type(mark: Any) -> str | None:
    if isinstance(mark, str):
        return mark
    if isinstance(mark, dict):
        t = mark.get("type")
        return t if isinstance(t, str) else None
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _coerce_llm_spec(vega_spec: Any, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """LLM spec'ni tekshiradi. Yaroqli bo'lsa data in'ektsiya qilib qaytaradi, aks holda None."""
    if not isinstance(vega_spec, dict):
        return None
    mark = vega_spec.get("mark")
    mtype = _mark_type(mark)
    if mtype is None or mtype not in ALLOWED_MARKS:
        return None
    encoding = vega_spec.get("encoding")
    if not isinstance(encoding, dict) or not encoding:
        return None
    if not rows:
        return None

    spec: dict[str, Any] = {
        "$schema": VEGA_SCHEMA,
        "mark": mark,
        "encoding": encoding,
        "data": {"values": rows},  # server haqiqiy qatorlarni in'ektsiya qiladi
    }
    if isinstance(vega_spec.get("transform"), list):
        spec["transform"] = vega_spec["transform"]
    return spec


def _fallback_spec(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any] | None:
    """Birinchi 2 ustun bo'yicha bar (2-ustun raqamli bo'lsa). Aks holda None -> jadval."""
    if not rows or len(columns) < 2:
        return None
    x_col, y_col = columns[0], columns[1]
    if not _is_number(rows[0].get(y_col)):
        return None
    return {
        "$schema": VEGA_SCHEMA,
        "mark": "bar",
        "encoding": {
            "x": {"field": x_col, "type": "nominal", "sort": "-y"},
            "y": {"field": y_col, "type": "quantitative"},
            "tooltip": [
                {"field": x_col, "type": "nominal"},
                {"field": y_col, "type": "quantitative", "format": ",.0f"},
            ],
        },
        "data": {"values": rows},
    }


def build_chart(
    title: str,
    vega_spec: Any,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> dict[str, Any] | None:
    """Yakuniy, render qilinadigan Vega-Lite spec qaytaradi (yoki None -> faqat jadval)."""
    spec = _coerce_llm_spec(vega_spec, rows)
    if spec is None:
        spec = _fallback_spec(rows, columns)
    if spec is not None and title:
        spec["title"] = title
    return spec
