"""Demo kesh + retry darvozasi: pitch barqarorligi (live LLM yiqilsa demo davom etadi).

Jonli LLM/DB SHART EMAS — FunctionModel bilan muvaffaqiyat/xato/transient stsenariylari.
"""

from __future__ import annotations

import json

from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.agent.analyst import run_analysis
from src.agent.cache import DemoCache, normalize_key
from src.connectors.demo import DemoConnector

# ---- yordamchi modellar -------------------------------------------------------


def _direct_output(text: str = "natija") -> FunctionModel:
    """run_sql'siz to'g'ridan strukturali chiqish (DB kerak emas)."""

    def func(messages: list, info: AgentInfo) -> ModelResponse:
        out_tool = info.output_tools[0].name
        return ModelResponse(
            parts=[ToolCallPart(out_tool, {"text": text, "chart_title": "", "vega_spec": None})]
        )

    return FunctionModel(func)


def _always_raises(msg: str = "boom") -> FunctionModel:
    def func(messages: list, info: AgentInfo) -> ModelResponse:
        raise RuntimeError(msg)

    return FunctionModel(func)


def _raises_then_ok(fail_times: int, text: str = "ok") -> FunctionModel:
    state = {"n": 0}

    def func(messages: list, info: AgentInfo) -> ModelResponse:
        state["n"] += 1
        if state["n"] <= fail_times:
            raise RuntimeError("429 RESOURCE_EXHAUSTED rate limit")
        out_tool = info.output_tools[0].name
        return ModelResponse(
            parts=[ToolCallPart(out_tool, {"text": text, "chart_title": "", "vega_spec": None})]
        )

    return FunctionModel(func)


# ---- normalize_key ------------------------------------------------------------


def test_normalize_key_case_space_punct() -> None:
    assert normalize_key("  Shahar BO'YICHA   tushum?  ") == "shahar bo'yicha tushum"
    assert normalize_key("Some Q") == normalize_key("some q?") == "some q"


# ---- DemoCache ----------------------------------------------------------------


def test_cache_set_get_roundtrip(tmp_path) -> None:
    cache = DemoCache(tmp_path / "c.json")
    cache.set("Savol?", {"text": "javob", "sql": "SELECT 1", "rows": [{"n": 1}]})
    got = cache.get("  savol ")  # normalizatsiya bir xil kalitga keltiradi
    assert got is not None
    assert got["text"] == "javob"
    assert got["sql"] == "SELECT 1"
    # error_detail SAQLANMAYDI (toza javob keshlanadi)
    assert "error_detail" not in got


def test_cache_persists_to_disk(tmp_path) -> None:
    path = tmp_path / "c.json"
    DemoCache(path).set("Q", {"text": "t"})
    # yangi instans diskdan o'qiydi
    assert DemoCache(path).get("q")["text"] == "t"
    # fayl haqiqatan ham JSON
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "q" in raw


def test_cache_corrupt_file_is_empty(tmp_path) -> None:
    path = tmp_path / "c.json"
    path.write_text("{ not json", encoding="utf-8")
    cache = DemoCache(path)  # xato tashlamaydi
    assert len(cache) == 0


# ---- run_analysis: muvaffaqiyatda keshga yozadi -------------------------------


def test_success_stores_in_cache(tmp_path) -> None:
    from src.agent.analyst import build_agent

    cache = DemoCache(tmp_path / "c.json")
    agent = build_agent(model=_direct_output("natija tayyor"))
    out = run_analysis(
        "Test savol", connector=DemoConnector(), agent=agent, require_key=False, cache=cache
    )
    assert out.error_detail is None
    assert out.text == "natija tayyor"
    # keshga yozildi va diskda turibdi
    assert "test savol" in cache
    assert DemoCache(tmp_path / "c.json").get("test savol")["text"] == "natija tayyor"


# ---- run_analysis: live yiqilsa keshdan qaytaradi -----------------------------


def test_failure_falls_back_to_cache(tmp_path) -> None:
    from src.agent.analyst import build_agent

    cache = DemoCache(tmp_path / "c.json")
    cache.set("Shahar bo'yicha tushum", {"text": "keshlangan javob", "sql": "SELECT 1", "rows": []})

    agent = build_agent(model=_always_raises())
    out = run_analysis(
        "shahar bo'yicha tushum?",  # registr/tinish farqli -> bir xil kalit
        connector=DemoConnector(),
        agent=agent,
        require_key=False,
        cache=cache,
        max_attempts=1,
    )
    assert out.text == "keshlangan javob"
    assert out.sql == "SELECT 1"
    assert out.error_detail is not None
    assert out.error_detail.startswith("served from cache")


def test_failure_without_cache_returns_polite_error() -> None:
    from src.agent.analyst import _POLITE_ERROR, build_agent

    agent = build_agent(model=_always_raises("nondb"))
    out = run_analysis(
        "savol", connector=DemoConnector(), agent=agent, require_key=False, max_attempts=1
    )
    assert out.text == _POLITE_ERROR
    assert out.vega_spec is None
    assert out.error_detail is not None


# ---- run_analysis: transient xatoda retry+backoff -----------------------------


def test_transient_retries_then_succeeds() -> None:
    from src.agent.analyst import build_agent

    sleeps: list[float] = []
    agent = build_agent(model=_raises_then_ok(fail_times=2, text="oxiri ishladi"))
    out = run_analysis(
        "savol",
        connector=DemoConnector(),
        agent=agent,
        require_key=False,
        max_attempts=3,
        backoff_base=0.0,
        sleep=sleeps.append,
    )
    assert out.error_detail is None
    assert out.text == "oxiri ishladi"
    assert len(sleeps) == 2  # 2 transient xato -> 2 backoff, 3-urinish muvaffaqiyat


def test_transient_exhausts_attempts() -> None:
    from src.agent.analyst import _POLITE_ERROR, build_agent

    sleeps: list[float] = []
    agent = build_agent(model=_always_raises("503 unavailable"))
    out = run_analysis(
        "savol",
        connector=DemoConnector(),
        agent=agent,
        require_key=False,
        max_attempts=2,
        backoff_base=0.0,
        sleep=sleeps.append,
    )
    assert out.text == _POLITE_ERROR
    assert len(sleeps) == 1  # 2 urinish -> faqat 1 marta backoff (oxirgidan keyin kutmaydi)
