"""Demo javob keshi — pitch ishonchliligi uchun (BUILD_PLAN: demo barqarorligi).

Maqsad: live pitchda Gemini kvotasi yoki tarmoq qoqilsa ham demo savollari ishlasin.
  - Muvaffaqiyatli javob diskka yoziladi (warm cache).
  - Keyin live yiqilsa (kvota/tarmoq), keshlangan javob qaytariladi — demo davom etadi.
  - Kesh kaliti = normallashtirilgan savol matni (registr/bo'sh joy/tinish belgisiga chidamli).

Bu modul `analyst`ga BOG'LANMAYDI (aylanma import yo'q): faqat oddiy dict saqlaydi.
Saqlangan payload — Outcome maydonlari (text, chart_title, vega_spec, sql, columns, rows).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Loyiha root'idagi kesh fayli. Commit qilinadi -> toza klonda ham demo ishlaydi.
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[2] / "demo_cache.json"

_WHITESPACE = re.compile(r"\s+")
# Oxiridagi tinish/savol belgilari (lotin + kirill + arab savol belgisi).
_TRAILING_PUNCT = "?!.,;:؟ "

# Keshda saqlanadigan maydonlar (error_detail SAQLANMAYDI — toza javob keshlanadi).
_FIELDS = ("text", "chart_title", "vega_spec", "sql", "columns", "rows")


def normalize_key(question: str) -> str:
    """Savol -> kesh kaliti: trim + lower + bo'sh joy siqish + oxirgi tinish olib tashlash."""
    q = _WHITESPACE.sub(" ", question.strip().lower())
    return q.rstrip(_TRAILING_PUNCT)


class DemoCache:
    """Savol -> javob dict keshi, diskka JSON sifatida saqlanadi."""

    def __init__(self, path: Path | None = None, *, autoload: bool = True) -> None:
        self.path = Path(path) if path is not None else DEFAULT_CACHE_PATH
        self._data: dict[str, dict[str, Any]] = {}
        if autoload:
            self.load()

    def load(self) -> None:
        """Diskdan o'qiydi. Fayl yo'q/buzuq bo'lsa bo'sh kesh (xato tashlamaydi)."""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data = {k: v for k, v in raw.items() if isinstance(v, dict)}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self._data = {}

    def save(self) -> None:
        """Keshni diskka yozadi (atomik: vaqtinchalik faylga yozib, almashtiradi)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def get(self, question: str) -> dict[str, Any] | None:
        """Keshlangan payload (Outcome maydonlari) yoki None."""
        return self._data.get(normalize_key(question))

    def set(self, question: str, payload: dict[str, Any], *, persist: bool = True) -> None:
        """Faqat kerakli maydonlarni saqlaydi. persist=True -> darhol diskka yozadi."""
        self._data[normalize_key(question)] = {k: payload.get(k) for k in _FIELDS}
        if persist:
            self.save()

    def __contains__(self, question: str) -> bool:
        return normalize_key(question) in self._data

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list[str]:
        return list(self._data.keys())
