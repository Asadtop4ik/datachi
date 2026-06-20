# HANDOFF — ish holati va davom ettirish

> Bu fayl mashinalar orasida davom ettirish uchun. Claude Code sessiyasi (`~/.claude/projects/.../*.jsonl`)
> **lokal** — gitga ketmaydi, laptopga ko'chmaydi. Davom ettirish = `git pull` + shu faylni o'qish.

## Loyiha holati: MVP TUGAGAN + post-MVP yaxshilanishlar

MVP (Faza 0→6) to'liq qurilgan va testli. Undan keyin 3 ta yaxshilanish qo'shildi.

## Bu sessiyada qilingan ishlar

1. **Demo barqarorligi (resilience)** — `80d586d`
   - `src/agent/cache.py` — disk-backed JSON kesh (savol normallashtirish bilan).
   - `run_analysis`: transient xatoda (kvota 429 / tarmoq / 5xx) backoff bilan 3 marta retry;
     hammasi yiqilsa keshlangan javob qaytadi → pitch yiqilmaydi.
   - `scripts/warm_cache.py` — kvota borida keshni oldindan to'ldiradi.
   - `demo_cache.json` gitignore (runtime artefakt). Test keshi tmp'ga izolyatsiya (conftest).

2. **Insight sifati (KPI kartalar)** — `c8319f7`
   - `src/agent/insights.py` — `derive_insights(rows, columns)` deterministik KPI (LLM'siz):
     kategoriyali → Jami · Yetakchi · Yetakchi ulush %; vaqt qatori → Jami · Oxirgi davr ±% · Eng yuqori.
   - `Outcome.metrics` → `/chat` javobi → kesh → Streamlit `st.metric` kartalar.

3. **Grafik avto-tanlov + chart saqlash** — `ddd4eb7`
   - `charts.choose_mark(rows, cols, question)` — fallback grafik turi: vaqt→line, ulush(≤8 kat.)→arc/pie,
     aks→bar. LLM o'z yaroqli spec'ini bersa o'sha ustun (ADR-0003). `question` `AnalysisDeps` orqali oqadi.
   - Chart saqlash: `POST/GET/DELETE /charts` (`SavedChart` modeli) + Streamlit "💾 Saqlash" tugma +
     "📌 Saqlangan grafiklar" tab (ko'rish/o'chirish).

**Testlar:** 76 passed, 1 skipped. Ruff toza.

## Laptopda davom ettirish

```bash
git clone git@github.com:Asadtop4ik/datachi.git   # yoki: git pull
cd datachi
uv sync
# .env ni .env.example dan yarat, GOOGLE_API_KEY ni qo'y (faqat shu qo'lda qo'yiladi)
docker compose up -d postgres
uv run alembic upgrade head
uv run python seed/seed_demo_biz.py
# (ixtiyoriy, kvota borida) demo keshini isit:
uv run python scripts/warm_cache.py
# Ishga tushirish (2 terminal):
uv run uvicorn src.api.main:app --reload
uv run streamlit run src/ui/app.py
# Test:
uv run pytest
```

## Keyingi nomzod yaxshilanishlar (hali boshlanmagan)

- Follow-up savollar — stateless invariant bilan ziddiyatli (BUILD_PLAN §8.5/8.12), ehtiyot bo'l.
- Export (CSV/PNG) saqlangan grafiklardan.
- Dashboard ko'rinish — bir nechta saqlangan grafikni bitta gridda.

## Eslatma — sessiya ko'chmaydi
Claude Code suhbat tarixi shu Mac'da `~/.claude/projects/-Users-macmini1-Desktop-datachi/` ichida.
Laptopda yangi sessiya bo'ladi; kontekst = git tarixi + BUILD_PLAN.md + CLAUDE.md + shu HANDOFF.md.
Cross-machine sessiya sinxron yo'q.
