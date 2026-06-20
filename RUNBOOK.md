# RUNBOOK — Datachi AI Analytics (demo)

Lokal demo'ni ishga tushirish va qo'lda tekshirish bo'yicha qadamlar.

## 1. Bir martalik tayyorgarlik (INSON)

1. Docker ishlayotganini tekshiring (`colima start` yoki Docker Desktop).
2. `.env` faylida `GOOGLE_API_KEY` to'ldirilganini tekshiring (Google AI Studio bepul key).
   Qolgan qiymatlarga TEGMANG — ular docker-compose'ga mos.

## 2. Ishga tushirish

```bash
# 1) Postgres (db-init/init.sql avtomatik: demo_biz + readonly_user)
docker compose up -d postgres

# 2) Bog'liqliklar
uv sync

# 3) App DB migratsiyasi (FAQAT app DB)
uv run alembic upgrade head

# 4) Sintetik biznes ma'lumotini seed qilish
uv run python seed/seed_demo_biz.py

# 5) (TAVSIYA) Demo keshini oldindan to'ldirish — pitch barqarorligi uchun
#    Kvota borligida BIR marta. Kvota/tarmoq pitchda qoqilsa, API shu keshdan javob beradi.
uv run python scripts/warm_cache.py

# 6) API (alohida terminal)
uv run uvicorn src.api.main:app --reload

# 7) UI (alohida terminal)
uv run streamlit run src/ui/app.py
```

UI brauzerda ochiladi (odatda http://localhost:8501). API: http://localhost:8000/health → `{"status":"ok"}`.

## Demo barqarorligi (kesh)

Live LLM kvota/tarmoq qoqilsa demo yiqilmasligi uchun ikki himoya bor:

- **Retry+backoff:** transient xato (429 kvota / tarmoq / 5xx) da agent 3 marta qayta urinadi.
- **Javob keshi:** muvaffaqiyatli javoblar `demo_cache.json` ga yoziladi. Keyin live yiqilsa,
  o'sha savolga keshlangan javob (matn + grafik + SQL) qaytadi. Pitchdan oldin
  `scripts/warm_cache.py` bilan 6 demo savolni keshlang — kvota tugasa ham demo to'liq ishlaydi.
  Kesh javobi UI'da odatdagidek ko'rinadi; "Tafsilot (texnik)" da "served from cache" belgisi turadi.

## 3. Qo'lda demo cheklist

- [ ] `GET /health` → `{"status":"ok"}`.
- [ ] UI ochiladi, sidebar'da namuna savol tugmalari ko'rinadi.
- [ ] "Oxirgi oyda Toshkentda eng ko'p sotilgan mahsulotlar?" → matn + bar grafik + "SQL ko'rsatish".
- [ ] "Shahar bo'yicha umumiy tushum qancha?" → shaharlar bo'yicha bar.
- [ ] "Oylik savdo trendini ko'rsat" → line grafik.
- [ ] Rus tilida savol ("Какой средний чек?") → javob rus tilida.
- [ ] "SQL ko'rsatish" expander ichidagi SQL — faqat `SELECT`, `LIMIT` bilan.
- [ ] Buzuq/imkonsiz savol → muloyim xato matni, crash yo'q, xom stack-trace yo'q.

## 4. Tez-tez uchraydigan muammolar

- **API'ga ulanmadi (UI'da):** backend ishga tushganmi? `uv run uvicorn src.api.main:app --reload`.
- **`GOOGLE_API_KEY .env da bo'sh`:** `.env` ga kalit qo'ying.
- **DB ulanmadi:** `docker compose up -d postgres` va `docker compose ps` (healthy?).
- **Bo'sh natija / sana noto'g'ri:** seed'ni qayta ishga tushiring (anchor = bugungi kun).
- **Gemini kvota (429) / "served from cache":** free-tier kvota tugagan. Agar savol oldin
  keshlangan bo'lsa — javob keshdan keladi (demo davom etadi). Aks holda kvota tiklanishini
  kuting yoki pitchdan oldin `scripts/warm_cache.py` ni ishga tushiring.
