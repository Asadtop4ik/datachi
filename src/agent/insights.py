"""Natija qatorlaridan deterministik KPI/insightlar (taqqoslash, ulush %, trend ±%).

Maqsad: xom raqam o'rniga manager-darajadagi xulosa. LLM'ga BOG'LIQ EMAS — qatorlardan
sof hisoblanadi, shu sabab testli va keshlangan/fallback javobda ham ishlaydi.

Chiqish: list[dict] (JSON-safe) -> {"label", "value", "delta"|None}. UI st.metric kartalar.
"""

from __future__ import annotations

import re
from typing import Any

# Vaqt o'qini bildiruvchi ustun nomlari (trend hisoblash uchun).
_TIME_WORDS = (
    "month",
    "date",
    "day",
    "year",
    "week",
    "quarter",
    "period",
    "posting_date",
    "oy",
    "sana",
    "kun",
    "yil",
    "hafta",
    "chorak",
)
# O'rtacha o'lchov (sum/share ma'nosiz) bildiruvchi belgilar.
_AVG_WORDS = ("avg", "mean", "average", "o'rtacha", "ortacha", "средн", "sredn3")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _fmt(x: Any) -> str:
    """Katta sonlarni ixchamlaydi: 12.3 mlrd / 4.5 mln / 7.8 ming / 186."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return str(x)
    a = abs(x)
    if a >= 1e9:
        return f"{x / 1e9:.1f} mlrd"
    if a >= 1e6:
        return f"{x / 1e6:.1f} mln"
    if a >= 1e3:
        return f"{x / 1e3:.1f} ming"
    if x == int(x):
        return str(int(x))
    return f"{x:.1f}"


def _pretty(col: str) -> str:
    return col.replace("_", " ").strip().capitalize()


def _metric(label: str, value: str, delta: str | None = None) -> dict[str, Any]:
    return {"label": label, "value": value, "delta": delta}


def _numeric_cols(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    out = []
    for c in columns:
        vals = [r.get(c) for r in rows if r.get(c) is not None]
        if vals and all(_is_number(v) for v in vals):
            out.append(c)
    return out


def _is_temporal(col: str, rows: list[dict[str, Any]]) -> bool:
    if any(w in col.lower() for w in _TIME_WORDS):
        return True
    vals = [r.get(col) for r in rows if r.get(col) is not None][:5]
    return bool(vals) and all(isinstance(v, str) and _ISO_DATE.match(v) for v in vals)


def derive_insights(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    """Qatorlardan KPI kartalar ro'yxati. Hisoblab bo'lmasa bo'sh ro'yxat."""
    if not rows or not columns:
        return []
    nums = _numeric_cols(rows, columns)
    if not nums:
        return []
    measure = nums[-1]  # odatda agregat (oxirgi sonli ustun)
    dim = next((c for c in columns if c not in nums), None)
    values = [r[measure] for r in rows if _is_number(r.get(measure))]
    if not values:
        return []

    # Bitta qator -> shunchaki qiymat (masalan o'rtacha chek).
    if len(rows) == 1:
        return [_metric(_pretty(measure), _fmt(values[0]))]

    is_avg = any(k in measure.lower() for k in _AVG_WORDS)
    total = sum(values)

    # Vaqt qatori -> trend (oxirgi davr avvalgiga nisbatan ±%).
    if dim and _is_temporal(dim, rows):
        metrics: list[dict[str, Any]] = []
        if not is_avg:
            metrics.append(_metric("Jami", _fmt(total)))
        last = values[-1]
        prev = values[-2] if len(values) >= 2 else None
        delta = None
        if prev not in (None, 0):
            pct = (last - prev) / abs(prev) * 100
            delta = f"{pct:+.0f}%"
        metrics.append(_metric("Oxirgi davr", _fmt(last), delta))
        metrics.append(_metric("Eng yuqori", _fmt(max(values))))
        return metrics

    # Kategoriyali -> jami + yetakchi + ulush %.
    top_idx = max(
        range(len(rows)),
        key=lambda i: rows[i][measure] if _is_number(rows[i].get(measure)) else float("-inf"),
    )
    top_val = rows[top_idx][measure]
    top_label = str(rows[top_idx].get(dim, "")).strip() if dim else ""

    if is_avg:
        return [
            _metric(f"Eng yuqori{f': {top_label}' if top_label else ''}", _fmt(top_val)),
            _metric("O'rtacha", _fmt(sum(values) / len(values))),
        ]

    metrics = [_metric("Jami", _fmt(total))]
    metrics.append(_metric(f"Yetakchi{f': {top_label}' if top_label else ''}", _fmt(top_val)))
    if total:
        metrics.append(_metric("Yetakchi ulush", f"{top_val / total * 100:.0f}%"))
    return metrics
