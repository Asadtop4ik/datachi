"""Grafik validatsiya + xavfsiz fallback (ADR-0003).

LLM Vega-Lite spec beradi; server tekshiradi va kerak bo'lsa fallback qiladi.
Demo HECH QACHON buzuq grafik chiqarmasin. Bu modul LLM'siz testlanadi.
"""

from __future__ import annotations

from typing import Any

from src.agent.insights import _is_temporal

ALLOWED_MARKS = {"bar", "line", "arc", "point"}
VEGA_SCHEMA = "https://vega.github.io/schema/vega-lite/v5.json"

# Savolda "ulush/share" niyati -> pie (arc) mos keladi.
_SHARE_WORDS = ("ulush", "share", "доля", "foiz", "процент", "percent", "%")
MAX_PIE_SLICES = 8  # ko'p bo'lakli pie o'qib bo'lmaydi -> bar'ga qaytamiz


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


def _looks_share(question: str) -> bool:
    return any(w in question.lower() for w in _SHARE_WORDS)


def choose_mark(
    rows: list[dict[str, Any]],
    columns: list[str],
    question: str = "",
) -> str:
    """Ma'lumot shakli + savol niyatidan grafik turini tanlaydi (line/arc/bar).

    Avto-tanlov: vaqt o'qi -> line (trend); ulush savoli + kam kategoriya -> arc (pie);
    aks holda -> bar (taqqoslash). Faqat fallback'da ishlaydi (LLM o'z spec'ini bersa, o'sha ustun).
    """
    if not rows or len(columns) < 2:
        return "bar"
    dim, measure = columns[0], columns[1]
    if not _is_number(rows[0].get(measure)):
        return "bar"
    if _is_temporal(dim, rows):
        return "line"
    if _looks_share(question) and 2 <= len(rows) <= MAX_PIE_SLICES:
        return "arc"
    return "bar"


def _tooltip(x_col: str, y_col: str) -> list[dict[str, Any]]:
    return [
        {"field": x_col, "type": "nominal"},
        {"field": y_col, "type": "quantitative", "format": ",.0f"},
    ]


def _spec_for(mark: str, rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    """Tanlangan mark uchun xavfsiz, ma'lumot in'ektsiyalangan Vega-Lite spec quradi."""
    x_col, y_col = columns[0], columns[1]
    base = {"$schema": VEGA_SCHEMA, "data": {"values": rows}}
    if mark == "line":
        return {
            **base,
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": x_col, "type": "temporal"},
                "y": {"field": y_col, "type": "quantitative"},
                "tooltip": _tooltip(x_col, y_col),
            },
        }
    if mark == "arc":
        return {
            **base,
            "mark": {"type": "arc"},
            "encoding": {
                "theta": {"field": y_col, "type": "quantitative"},
                "color": {"field": x_col, "type": "nominal"},
                "tooltip": _tooltip(x_col, y_col),
            },
        }
    return {
        **base,
        "mark": "bar",
        "encoding": {
            "x": {"field": x_col, "type": "nominal", "sort": "-y"},
            "y": {"field": y_col, "type": "quantitative"},
            "tooltip": _tooltip(x_col, y_col),
        },
    }


def _fallback_spec(
    rows: list[dict[str, Any]],
    columns: list[str],
    question: str = "",
) -> dict[str, Any] | None:
    """Avto-tanlangan mark bo'yicha spec (2-ustun raqamli bo'lsa). Aks holda None -> jadval."""
    if not rows or len(columns) < 2:
        return None
    if not _is_number(rows[0].get(columns[1])):
        return None
    return _spec_for(choose_mark(rows, columns, question), rows, columns)


def build_chart(
    title: str,
    vega_spec: Any,
    rows: list[dict[str, Any]],
    columns: list[str],
    question: str = "",
) -> dict[str, Any] | None:
    """Yakuniy, render qilinadigan Vega-Lite spec qaytaradi (yoki None -> faqat jadval).

    LLM spec yaroqli bo'lsa o'sha (ADR-0003); aks holda `question`+ma'lumot shakliga qarab
    avto-tanlangan fallback (trend->line, ulush->pie, taqqoslash->bar).
    """
    spec = _coerce_llm_spec(vega_spec, rows)
    if spec is None:
        spec = _fallback_spec(rows, columns, question)
    if spec is not None and title:
        spec["title"] = title
    return spec
