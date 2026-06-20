# Datachi — AI Analytics MVP

Natural-language analytics over a synthetic, **ERPNext-shaped** sales database. A manager asks a
question in chat (UZ / RU / EN); the **Analyst Agent** writes safe, read-only SQL, runs it, and
answers with a chart and a short narration. The demo runs **only on synthetic data**.

> Pitch demo. Real customer databases come after the pitch (see the privacy note below).

## Architecture

```
Streamlit UI  ──HTTP──►  FastAPI /chat  ──►  Pydantic AI agent (Gemini 2.5 Flash)
                                               tools: list_tables, get_schema, run_sql, make_chart
                                                        │
                                                        ▼
                                               safe_sql  (sqlglot AST validate + read-only exec)
                                                        │
                                                        ▼
                              Postgres: app (metadata) + demo_biz (synthetic, read-only role)
```

## Safety (the core claim)

- **Two-layer defense (ADR-0002):** every query passes `src/safe_sql.py` — a `sqlglot` AST
  validator (single statement, SELECT root, no DML/DDL, LIMIT injected at AST level, comments
  dropped, 15s timeout) — **behind** a read-only Postgres role (`readonly_user`). The LLM never
  sends raw SQL straight to the DB.
- **Charts validated server-side (ADR-0003):** the LLM proposes a Vega-Lite spec; the server
  checks it and falls back safely so the demo never renders a broken chart.
- **Schema in the prompt (ADR-0001):** a static schema map is baked into the system prompt;
  introspection tools exist only for live sample rows.
- **Deterministic seed (ADR-0004):** fixed RNG + configurable `ANCHOR_DATE`; "last month" is
  relative to the anchor, not the wall clock.

## Stack

Python (uv) · FastAPI · Pydantic AI (`google-gla:gemini-2.5-flash`) · PostgreSQL 16 ·
SQLAlchemy 2 · Alembic · Streamlit · Vega-Lite · pytest · ruff. (No React.)

## Quick start

The human fills only `GOOGLE_API_KEY` in `.env` (from [Google AI Studio](https://aistudio.google.com/apikey)).
Everything else is preconfigured. Full steps + manual demo checklist: [RUNBOOK.md](RUNBOOK.md).

```bash
docker compose up -d postgres            # db-init/init.sql -> demo_biz + readonly_user
uv sync
uv run alembic upgrade head              # app DB only
uv run python seed/seed_demo_biz.py      # synthetic biz data
uv run uvicorn src.api.main:app --reload # API  :8000
uv run streamlit run src/ui/app.py       # UI   :8501
```

Pitch questions to demo: [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

## Commands

| | |
|---|---|
| Install | `uv sync` |
| DB up | `docker compose up -d postgres` |
| Migrate | `uv run alembic upgrade head` |
| Seed | `uv run python seed/seed_demo_biz.py` |
| API | `uv run uvicorn src.api.main:app --reload` |
| UI | `uv run streamlit run src/ui/app.py` |
| Test | `uv run pytest` |
| Lint | `uv run ruff check . && uv run ruff format .` |

Tests run without a live LLM key (Pydantic AI `FunctionModel` drives tool calls). They need
Postgres up; DB-dependent tests skip cleanly if it is not. An optional live smoke test runs with
`RUN_LIVE_LLM=1`.

## Connectors

`src/connectors/` defines a `Connector` boundary. `demo.py` (synthetic `demo_biz`) is used by the
demo; `erpnext.py` is a Frappe REST stub implementing the same interface for a live ERPNext
instance after the pitch (`Authorization: token key:secret`).

## Project docs

- [BUILD_PLAN.md](BUILD_PLAN.md) — phased build plan and locked decisions (§8).
- [CONTEXT.md](CONTEXT.md) — domain language (ubiquitous vocabulary).
- [docs/adr/](docs/adr/) — architecture decision records.

## Privacy

The free Gemini tier may use submitted data for training. The demo therefore uses **synthetic
data only**. Do not point it at a real customer database on the free tier.
