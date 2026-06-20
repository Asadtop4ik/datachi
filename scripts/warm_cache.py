"""Demo keshini oldindan to'ldiradi (pitch barqarorligi).

KVOTA BORLIGIDA pitchdan OLDIN bir marta ishlat:
    uv run python scripts/warm_cache.py

Har demo savolni live LLM bilan bajaradi va javobni `demo_cache.json` ga yozadi.
Pitch vaqtida kvota/tarmoq qoqilsa, API shu keshdan javob beradi -> demo yiqilmaydi.

Talab: DB ko'tarilgan, .env da GOOGLE_API_KEY bor, kvota tugamagan.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.analyst import get_demo_cache, run_analysis  # noqa: E402
from src.agent.prompts import SAMPLE_PROMPTS  # noqa: E402


def main() -> int:
    cache = get_demo_cache()
    ok = 0
    failed: list[str] = []
    for q in SAMPLE_PROMPTS:
        outcome = run_analysis(q, cache=cache)
        # Yangi muvaffaqiyatli live run: error_detail None va SQL bor (keshga yozildi).
        # Aks holda live yiqilgan (kvota/tarmoq) -> error_detail to'lgan.
        if outcome.error_detail is None and outcome.sql:
            ok += 1
            print(f"  OK   {q}")
        else:
            failed.append(q)
            print(f"  FAIL {q}  ({outcome.error_detail or 'no sql'})")

    print(f"\nKeshlandi: {ok}/{len(SAMPLE_PROMPTS)} -> {cache.path}")
    if failed:
        print("Yiqilgan savollar (kvota/tarmoq?):")
        for q in failed:
            print(f"  - {q}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
