"""Analyst Agent (Pydantic AI + Gemini). Toollar: list_tables, get_schema, run_sql, make_chart.

Qarorlar (BUILD_PLAN §8):
  - Stateless: har run faqat joriy xabarni oladi (tarix LLM'ga uzatilmaydi).
  - SQL + qatorlar deps (RunContext) orqali yoziladi; API run tugagach deps'dan o'qiydi.
  - run_sql LLM'ga faqat birinchi ~50 qator beradi; deps'da to'liq (<=LIMIT) qoladi.
  - Strukturali chiqish: {text, chart_title, vega_spec}. Grafik make_chart'da server tekshiradi.
  - Tool-call cap = 6; oshsa muloyim xato (crash emas).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

from src.agent.cache import DemoCache
from src.agent.charts import build_chart
from src.agent.prompts import SYSTEM_PROMPT
from src.config import get_settings
from src.connectors.base import Connector
from src.connectors.demo import DemoConnector
from src.safe_sql import LLM_ROW_CAP, SafeSqlError

try:  # pydantic-ai versiyasiga chidamli: HTTP xato turi bo'lmasligi mumkin
    from pydantic_ai.exceptions import ModelHTTPError as _ModelHTTPError
except ImportError:  # pragma: no cover
    _ModelHTTPError = None  # type: ignore[assignment, misc]

TOOL_CALL_CAP = 6

# Demo barqarorligi: live LLM transient xatosida (kvota/tarmoq) qayta urinish.
MAX_ATTEMPTS = 3
BACKOFF_BASE = 0.6  # sekund; urinishlar orasi backoff_base * 2**(attempt-1)

# str(exc) ichida shu belgilar -> transient (qayta urinishga arziydi).
_TRANSIENT_MARKERS = (
    "429",
    "resource_exhausted",
    "rate limit",
    "rate-limit",
    "ratelimit",
    "timeout",
    "timed out",
    "temporarily",
    "unavailable",
    "overloaded",
    "connection",
    "502",
    "503",
    "504",
)
_TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

_POLITE_ERROR = (
    "Kechirasiz, so'rovni bajarib bo'lmadi. Iltimos, savolni soddalashtirib qayta urinib ko'ring. "
    "(Извините, не удалось выполнить запрос. / Sorry, the request could not be completed.)"
)


@dataclass
class AnalysisDeps:
    """Run davomida to'planadigan holat. Tool'lar yozadi, API o'qiydi."""

    connector: Connector
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    chart_title: str = ""
    vega_spec: dict[str, Any] | None = None


class AnalysisResult(BaseModel):
    """Agentning strukturali chiqishi (BUILD_PLAN §8.11)."""

    text: str = Field(description="Narration in the user's language, max 3 sentences.")
    chart_title: str = Field(default="", description="Short chart title in user's language.")
    vega_spec: dict[str, Any] | None = Field(
        default=None, description="Vega-Lite spec passed to make_chart, or null."
    )


@dataclass
class Outcome:
    """API/UI uchun yakuniy natija (deps + output birlashtirilgan)."""

    text: str
    chart_title: str
    vega_spec: dict[str, Any] | None
    sql: str | None
    columns: list[str]
    rows: list[dict[str, Any]]
    error_detail: str | None = None


def build_agent(model: Any | None = None) -> Agent[AnalysisDeps, AnalysisResult]:
    """Toollari ro'yxatdan o'tgan agent quradi. model=None -> .env dagi LLM_MODEL."""
    model = model or get_settings().llm_model
    agent: Agent[AnalysisDeps, AnalysisResult] = Agent(
        model,
        deps_type=AnalysisDeps,
        output_type=AnalysisResult,
        system_prompt=SYSTEM_PROMPT,
        retries=1,  # yomon SQL'da 1 marta retry (BUILD_PLAN §8.8)
        defer_model_check=True,  # konstruksiyada kalit talab qilinmasin
    )

    @agent.tool
    def list_tables(ctx: RunContext[AnalysisDeps]) -> list[str]:
        """List the available business tables."""
        return ctx.deps.connector.list_tables()

    @agent.tool
    def get_schema(ctx: RunContext[AnalysisDeps], table: str) -> dict[str, Any]:
        """Columns and a few live sample rows for one table."""
        info = ctx.deps.connector.get_schema(table)
        return {
            "table": info.table,
            "columns": info.columns,
            "sample_rows": info.sample_rows,
        }

    @agent.tool
    def run_sql(ctx: RunContext[AnalysisDeps], sql: str) -> dict[str, Any]:
        """Execute one read-only SELECT and return rows (auto-validated, auto-limited)."""
        try:
            res = ctx.deps.connector.run_sql(sql)
        except SafeSqlError as exc:
            # Validatsiya xatosi -> LLM xabarni o'qib, SQL'ni tuzatib qayta urinadi.
            return {"error": f"Invalid SQL: {exc}"}
        ctx.deps.sql = res.sql
        ctx.deps.columns = res.columns
        ctx.deps.rows = res.rows
        return {
            "sql": res.sql,
            "columns": res.columns,
            "row_count": res.row_count,
            "rows": res.rows[:LLM_ROW_CAP],  # LLM'ga faqat birinchi ~50 qator
        }

    @agent.tool
    def make_chart(
        ctx: RunContext[AnalysisDeps], title: str, vega_spec: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate a Vega-Lite spec server-side and store the safe version (with fallback)."""
        spec = build_chart(title, vega_spec, ctx.deps.rows, ctx.deps.columns)
        ctx.deps.chart_title = title
        ctx.deps.vega_spec = spec
        return {"ok": spec is not None, "used_fallback": spec is not None and spec != vega_spec}

    return agent


# Ishlab chiqarish uchun yagona agent (live model). Testlar agent.override bilan almashtiradi.
analyst_agent = build_agent()


@lru_cache(maxsize=1)
def get_demo_cache() -> DemoCache:
    """API/warm-up uchun yagona disk kesh (lazy: birinchi chaqiruvda yuklanadi)."""
    return DemoCache()


def _is_transient(exc: Exception) -> bool:
    """Xato qayta urinishga arziydimi (kvota/tarmoq/server) — doimiy xatodan farqlash."""
    if _ModelHTTPError is not None and isinstance(exc, _ModelHTTPError):
        if getattr(exc, "status_code", None) in _TRANSIENT_STATUS:
            return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def _finalize(result: Any, deps: AnalysisDeps) -> Outcome:
    """Agent natijasini Outcome'ga aylantiradi (server spec ustun, aks holda fallback)."""
    out = result.output
    spec = deps.vega_spec
    if spec is None:
        spec = build_chart(out.chart_title or "", out.vega_spec, deps.rows, deps.columns)
    return Outcome(
        text=out.text,
        chart_title=out.chart_title or deps.chart_title,
        vega_spec=spec,
        sql=deps.sql,
        columns=deps.columns,
        rows=deps.rows,
    )


def _outcome_from_cache(cached: dict[str, Any], detail: str | None) -> Outcome:
    """Keshlangan javobni Outcome'ga; error_detail'ga 'keshdan' izohi (demo toza ko'rinadi)."""
    note = "served from cache (live LLM unavailable)"
    if detail:
        note += f": {detail}"
    return Outcome(
        text=cached.get("text", ""),
        chart_title=cached.get("chart_title", "") or "",
        vega_spec=cached.get("vega_spec"),
        sql=cached.get("sql"),
        columns=cached.get("columns") or [],
        rows=cached.get("rows") or [],
        error_detail=note,
    )


def run_analysis(
    message: str,
    *,
    connector: Connector | None = None,
    agent: Agent[AnalysisDeps, AnalysisResult] | None = None,
    require_key: bool = True,
    cache: DemoCache | None = None,
    max_attempts: int = MAX_ATTEMPTS,
    backoff_base: float = BACKOFF_BASE,
    sleep: Callable[[float], None] = time.sleep,
) -> Outcome:
    """Bitta savolni bajaradi. Xato bo'lsa muloyim matn qaytaradi (crash EMAS).

    Demo barqarorligi (cache berilganda):
      - muvaffaqiyatda javob keshga yoziladi;
      - transient xatoda (kvota/tarmoq) backoff bilan max_attempts marta qayta urinadi;
      - hamma urinish yiqilsa va kesh bo'lsa -> keshlangan javob (demo davom etadi).
    """
    if require_key:
        get_settings().require_google_api_key()
    connector = connector or DemoConnector()
    agent = agent or analyst_agent

    deps = AnalysisDeps(connector=connector)
    last_detail: str | None = None
    for attempt in range(1, max_attempts + 1):
        deps = AnalysisDeps(connector=connector)
        try:
            result = agent.run_sync(
                message,
                deps=deps,
                usage_limits=UsageLimits(tool_calls_limit=TOOL_CALL_CAP),
            )
        except UsageLimitExceeded as exc:
            last_detail = f"tool-call cap exceeded: {exc}"
            break  # cap doimiy -> qayta urinish foyda bermaydi
        except Exception as exc:  # noqa: BLE001 — demo'da xom stack-trace ko'rsatilmaydi
            last_detail = f"{type(exc).__name__}: {exc}"
            if _is_transient(exc) and attempt < max_attempts:
                sleep(backoff_base * (2 ** (attempt - 1)))
                continue
            break
        else:
            outcome = _finalize(result, deps)
            if cache is not None:
                cache.set(message, asdict(outcome))
            return outcome

    # Hamma urinish yiqildi -> kesh fallback yoki muloyim xato.
    if cache is not None:
        cached = cache.get(message)
        if cached is not None:
            return _outcome_from_cache(cached, last_detail)
    return Outcome(
        text=_POLITE_ERROR,
        chart_title="",
        vega_spec=None,
        sql=deps.sql,
        columns=deps.columns,
        rows=deps.rows,
        error_detail=last_detail,
    )
