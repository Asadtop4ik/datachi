# CLAUDE.md

Bu repo: AI Analytics MVP (pitch demo). To'liq reja: `BUILD_PLAN.md`. Uni o'qi va unga amal qil.

## Eng muhim qoidalar
- `.env` ni `.env.example` dan o'zing yarat. DB URL'lari u yerda to'g'ri (docker-compose'ga mos) —
  o'zing sozla. INSON faqat `GOOGLE_API_KEY` ni qo'yadi. U bo'sh bo'lsa — O'YLAB TOPMA, `RuntimeError`.
- LLM xom SQL'ni to'g'ridan-to'g'ri DB'ga YUBORMAYDI — hamma SQL `src/safe_sql.py` orqali o'tadi
  (faqat SELECT, DDL/DML bloklangan, majburiy LIMIT, timeout).
- Biznes bazasiga FAQAT read-only rol ulanadi.
- Real tashqi servis (ERPNext jonli API) demo uchun TALAB QILINMAYDI. Demo sintetik bazada.
- Har modul testli bo'lsin. Test yo'q = faza tugamagan.

## Stack
Python (uv), FastAPI, Pydantic AI (`google-gla:gemini-2.5-flash`), PostgreSQL, SQLAlchemy 2,
Alembic, Streamlit, Vega-Lite, pytest, ruff. **React ISHLATMA.**

## Buyruqlar
- O'rnatish: `uv sync`
- DB ko'tarish: `docker compose up -d postgres`
- Migratsiya: `uv run alembic upgrade head`
- Seed: `uv run python seed/seed_demo_biz.py`
- API: `uv run uvicorn src.api.main:app --reload`
- UI: `uv run streamlit run src/ui/app.py`
- Test: `uv run pytest`
- Lint: `uv run ruff check . && uv run ruff format .`

## Ish tartibi
Fazalarni `BUILD_PLAN.md` bo'yicha KETMA-KET bajar. Har faza acceptance darvozasi (testlar) yashil
bo'lmaguncha keyingisiga O'TMA. Har faza oxirida `git commit -m "phase N: ..."`. Bir faza 2 marta
yiqilsa — `BLOCKERS.md` ga yoz va TO'XTA.
