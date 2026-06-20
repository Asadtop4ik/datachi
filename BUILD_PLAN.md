# AI Analytics MVP — Build Plan (Claude Code)

> **Maqsad:** Pitch demo. Manager chatda savol yozadi ("o'tgan oy Toshkentda eng ko'p sotilgan
> mahsulotlar?") → AI agent xavfsiz SQL yozadi → natijani grafik + izoh qilib qaytaradi.
> Demo **sintetik, ERPNext-shaklidagi** ma'lumotda ishlaydi. Real mijoz bazasi PITCHDAN KEYIN.

> **Bu hujjat Claude Code uchun.** Fazalarni KETMA-KET bajar. Har fazada acceptance testlari
> YASHIL bo'lmaguncha keyingisiga O'TMA. Har faza oxirida `git commit` qil. Agar bir faza 2 marta
> ketma-ket muvaffaqiyatsiz bo'lsa — TO'XTA va nima bloklayotganini `BLOCKERS.md` ga yoz.

---

## 0. Qattiq qoidalar (hech qachon buzma)

- **`.env` ni o'zing yarat.** `.env.example` ni `.env` ga nusxa qil. DB URL'lari u yerda allaqachon
  to'g'ri (docker-compose'ga mos) — o'zing sozla, hech narso so'rama. INSON faqat `GOOGLE_API_KEY` ni
  qo'yadi. Agar `.env` da `GOOGLE_API_KEY` bo'sh bo'lsa — uni O'YLAB TOPMA, balandovoz xato ber
  (`raise RuntimeError("GOOGLE_API_KEY .env da bo'sh — inson qo'yishi kerak")`).
- **LLM hech qachon xom SQL'ni to'g'ridan-to'g'ri DB'ga yubormaydi.** Hamma SQL `safe_sql` qatlamidan
  o'tadi: faqat `SELECT`, DDL/DML bloklangan, majburiy `LIMIT`, timeout.
- **Biznes bazasiga faqat read-only rol** ulanadi. App metadata bazasi alohida.
- **Real tashqi servislarni demo uchun talab qilma.** ERPNext'ning haqiqiy API'si Faza 6'da, stub
  ko'rinishida (jonli instance kerak). Demo sintetik bazada ishlaydi.
- Har modul uchun test yoz. Test yo'q kod = tugallanmagan faza.
- Python: `uv` bilan boshqar. Til: backend Python, UI Streamlit. Frontendga React ISHLATMA (MVP).

---

## 1. Maqsadli arxitektura (MVP, minimal)

```
Streamlit UI (chat + grafik + jadval + SQL ko'rsatish)
        │  HTTP
        ▼
FastAPI  ──►  Pydantic AI agent (Gemini 2.5 Flash)
                  tools: list_tables, get_schema, run_sql, make_chart
                          │
                          ▼
                  safe_sql qatlami (validator + executor, read-only)
                          │
                          ▼
        Postgres (bitta instance, ikki DB):
          - app        : metadata (conversations, messages, saved_charts)
          - demo_biz   : sintetik ERPNext-shaklidagi savdo ma'lumoti (read-only rol o'qiydi)
```

Spec'dagi Cube, MotherDuck, dlt, Prefect, R2, Valkey, Clerk — **MVP'da YO'Q**. Keyin qo'shiladi.

---

## 2. Stack (qat'iy)

| Qatlam | Tanlov |
|---|---|
| API | FastAPI |
| Agent | Pydantic AI, model: `google-gla:gemini-2.5-flash` (almashtiriladigan) |
| LLM | Gemini (Google AI Studio bepul key) — `GOOGLE_API_KEY` |
| App DB | PostgreSQL 16 (docker) |
| Biznes DB | PostgreSQL (xuddi shu instance, alohida `demo_biz` DB) |
| Migratsiya | Alembic |
| ORM | SQLAlchemy 2.x |
| UI | Streamlit |
| Grafik | Vega-Lite (LLM JSON spec chiqaradi → `st.vega_lite_chart`) |
| Paket | uv |
| Test | pytest |
| Lint/format | ruff |

`uv add fastapi uvicorn pydantic-ai sqlalchemy "psycopg[binary]" alembic streamlit requests python-dotenv`
`uv add --dev pytest ruff httpx`

---

## 3. Repo tuzilishi (yaratiladigan)

```
ai-analytics-mvp/
├── docker-compose.yml          # postgres
├── .env.example                # kerakli kalitlar ro'yxati
├── pyproject.toml
├── alembic/                    # app DB migratsiyalari
├── seed/
│   └── seed_demo_biz.py        # sintetik ERPNext-shaklidagi ma'lumot generatori
├── src/
│   ├── config.py               # .env o'qish, kalit yo'q bo'lsa balandovoz xato
│   ├── db.py                   # app + biznes DB enginelari
│   ├── safe_sql.py             # SQL validator + read-only executor
│   ├── agent/
│   │   ├── analyst.py          # Pydantic AI agent + toollar
│   │   └── prompts.py          # system prompt (RU/UZ/EN)
│   ├── connectors/
│   │   ├── base.py             # Connector interfeysi
│   │   ├── demo.py             # sintetik demo_biz konnektori
│   │   └── erpnext.py          # Faza 6: Frappe REST stub (jonli instance kerak)
│   ├── api/
│   │   └── main.py             # FastAPI: /health, /chat
│   └── ui/
│       └── app.py              # Streamlit
└── tests/
    ├── test_safe_sql.py
    ├── test_agent.py
    ├── test_api.py
    └── test_connectors.py
```

---

## 4. Sintetik biznes ma'lumoti (ERPNext-shaklida)

`seed/seed_demo_biz.py` quyidagilarni `demo_biz` DB'ga yozadi (ERPNext nomlash uslubida, real
ERPNext'ga o'tish oson bo'lishi uchun):

- `customers` (id, name, city, segment) — shaharlar: Toshkent, Samarqand, Buxoro, Andijon, Namangan
- `items` (id, name, category, unit_price_uzs)
- `sales_invoices` (id, customer_id, posting_date, status, total_uzs) — ~18 oylik diapazon
- `sales_invoice_items` (id, invoice_id, item_id, qty, amount_uzs)

Hajm: ~500 mijoz, ~80 mahsulot, ~20 000 hisob-faktura. Valyuta UZS. Bu savollar ishlashi shart:
"oxirgi oy Toshkentda top mahsulotlar", "shahar bo'yicha tushum", "oylik savdo trendi",
"tushum bo'yicha top 10 mijoz", "o'rtacha chek".

---

## 5. FAZALAR (ketma-ket, har birida acceptance darvozasi)

### Faza 0 — Skelet
- Repo, `pyproject.toml`, `uv sync`, ruff.
- `docker-compose.yml` (postgres 16, ikki DB: `app`, `demo_biz`).
- `src/config.py`: `.env` o'qiydi. DB URL'lari `.env` dan keladi (default'lar docker-compose'ga mos).
  FAQAT `GOOGLE_API_KEY` bo'sh bo'lsa balandovoz xato. Boshlanishida agent `.env.example` ni `.env` ga
  nusxa qiladi (agar `.env` yo'q bo'lsa).
- FastAPI `GET /health` → `{"status":"ok"}`.
- **Darvoza:** `docker compose up -d` ko'tariladi; `pytest tests/test_api.py::test_health` yashil.

### Faza 1 — Ma'lumotlar bazasi
- Alembic migratsiya: app DB jadvallari (`conversations`, `messages`, `saved_charts`).
- `seed/seed_demo_biz.py` → `demo_biz` to'ldiriladi.
- `demo_biz` uchun **read-only Postgres rol** yaratiladi; agent shu rol bilan ulanadi.
- **Darvoza:** seed ishlaydi, har jadval `count(*) > 0`; read-only rol `INSERT` qila olmaydi
  (test buni tasdiqlaydi); `alembic upgrade head` xatosiz.

### Faza 2 — Xavfsiz SQL qatlami
- `src/safe_sql.py`: `validate_sql(sql)` — faqat bitta `SELECT` statement, `;` bilan ko'p
  statement bloklangan, DDL/DML (`INSERT/UPDATE/DELETE/DROP/ALTER/...`) bloklangan, kommentlar
  tozalangan. `run_sql(sql)` — read-only ulanish, `LIMIT` majburlanadi (yo'q bo'lsa qo'shiladi),
  statement timeout (masalan 15s).
- **Darvoza:** `tests/test_safe_sql.py` — quyidagilar bloklanadi: `DROP TABLE`, `; DELETE`,
  `UPDATE`, kommentdagi inyeksiya; ruxsat etiladi: oddiy `SELECT`. Hammasi yashil.

### Faza 3 — AI agent (Pydantic AI + Gemini)
- `src/agent/analyst.py`: Pydantic AI agent, model `google-gla:gemini-2.5-flash`.
  Toollar:
  - `list_tables()` → demo_biz jadvallari
  - `get_schema(table)` → ustunlar + 5 namuna qator
  - `run_sql(sql)` → safe_sql orqali natija
  - `make_chart(title, vega_spec)` → spec'ni qaytaradi/saqlaydi
- System prompt: foydalanuvchi tilini aniqlash (RU/UZ/EN), faqat semantik/jadval nomlaridan
  foydalanish, natijani grafik shakliga moslab Vega-Lite chiqarish, 3 jumladan qisqa izoh.
- `max tool calls` cheklangan (masalan 6).
- **Darvoza:** `tests/test_agent.py` — 3 ta "golden" savol uchun agent VALID `SELECT` va valid
  Vega-Lite spec qaytaradi. *CI'da jonli kalit yo'q bo'lsa, LLM'ni stub model bilan almashtir va
  tool-chaqiruv mantig'ini test qil; jonli kalit bo'lsa, jonli smoke test ham ishlasin.*

### Faza 4 — API
- `POST /chat` `{conversation_id?, message}` → agentni chaqiradi, `{text, sql, rows, vega_spec,
  chart_title}` qaytaradi. Suhbat tarixi app DB'ga yoziladi.
- (Ixtiyoriy) SSE stream; MVP uchun oddiy JSON ham yetadi.
- **Darvoza:** `tests/test_api.py` — `/chat` namuna savolga to'liq javob qaytaradi (LLM mock bilan
  integration test). Yashil.

### Faza 5 — Streamlit UI
- `src/ui/app.py`: chat oynasi, xabar yuborish, javob matni, `st.vega_lite_chart(spec)`,
  yig'iladigan "SQL ko'rsatish" va natija jadvali, 4-5 ta namuna prompt tugmasi (RU/UZ).
- API'ga `requests` orqali ulanadi.
- **Darvoza:** `streamlit run src/ui/app.py` xatosiz ko'tariladi (import smoke test);
  `RUNBOOK.md` da qo'lda demo cheklist.

### Faza 6 — ERPNext konnektori + sayqal
- `src/connectors/base.py` interfeysi; `demo.py` (sintetik) va `erpnext.py` (Frappe REST stub:
  `GET /api/resource/...`, `Authorization: token key:secret`) bir interfeysni bajaradi. ERPNext
  jonli instance + token bo'lganda ulanadi — bu qadam SUPERVISED, demo uchun shart emas.
- README + RUNBOOK + DEMO_SCRIPT (pitchda ko'rsatiladigan 5 savol).
- i18n: UZ/RU/EN prompt namunalari.
- **Darvoza:** `tests/test_connectors.py` — ikkala konnektor interfeysga mos; README'da ishga
  tushirish qadamlari bor.

---

## 6. Ishga tushirishdan oldin INSON qiladigan narsalar (bir marta)

Agentni ishga tushirishdan oldin SIZ tayyorlaysiz (agent bularni o'ylab topa olmaydi):

1. Claude Code o'rnatilgan, repo ichida.
2. Docker ishlamoqda: `docker compose up -d postgres` (URL'lar qat'iy, o'zgartirish shart emas).
3. `.env` faylida FAQAT bitta narsa — `GOOGLE_API_KEY` ni qo'yasiz (Google AI Studio bepul key).
   Qolgan hamma narsani (DB URL'lari, `.env` ni `.env.example` dan yasash) agent o'zi qiladi.
4. `uv sync` (yoki agent o'zi bajaradi).

> **Maxfiylik eslatmasi:** Gemini bepul tier ma'lumotni Google trening uchun ishlatishi mumkin.
> Shu sabab demo FAQAT sintetik ma'lumotda. Real mijoz bazasini bepul tierda ishlatmang.

---

## 7. Avtonom ishlatish (tunги ish)

1. `git init`, birinchi commit.
2. Claude Code'ga shu hujjatni ko'rsat va ayt: **"BUILD_PLAN.md ni o'qi. Fazalarni 0 dan 6 gacha
   ketma-ket bajar. Har faza acceptance darvozasi yashil bo'lmaguncha keyingisiga o'tma. Har faza
   oxirida `git commit` qil. Bir faza 2 marta yiqilsa, BLOCKERS.md ga yoz va to'xta."**
3. Avtonom tun uchun headless: tekshirilgan ish bo'lsa `--dangerously-skip-permissions`. Yangi repo
   bo'lgani uchun zarar doirasi past. Iloji bo'lsa dev-container/sandboxda ishlat.
4. Har faza commit bo'lgani uchun ertalab `git log` bilan ko'rasiz; yomon fazani `git revert` yoki
   checkpoint bilan ortga qaytarasiz.
5. Ertalab: `BLOCKERS.md` o'qing, qo'lda demo qiling (RUNBOOK), kamchiliklarni nuqtali topshiriqlar
   bilan tuzating ("Faza 5 dagi grafik UZS formatlanmayapti, ming ajratgich qo'sh").

> **Tavsiya:** bitta 6-soatlik "hammasini qur" goal o'rniga, fazalar bo'yicha test-bilan-loop —
> shu token va vaqtni eng foydali sarflaydi va ertalab bo'sh qobiq emas, ishlaydigan demo topasiz.

---

## 8. Hal qilingan qarorlar (grilling natijasi — BUILD shularga AMAL QILADI)

> Bu bo'lim grilling sessiyasida qotirildi. Yuqoridagi fazalar matni bilan ziddiyat bo'lsa — **bu
> bo'lim ustun**. Batafsil sabablar `docs/adr/` da. Domen tili `CONTEXT.md` da.

### Arxitektura / xavfsizlik
1. **Sxema agentga prompt orqali beriladi** (ADR-0001). Tizim prompt'ida qo'lda yozilgan ixcham
   sxema xaritasi (jadvallar, ustunlar, tip, FK, UZS izohi) bo'ladi. `list_tables`/`get_schema`
   toollari FAQAT jonli namuna qator uchun qoladi — agent struktura bilish uchun ularga tayanmaydi.
   Sxema xaritasi `seed_demo_biz.py` bilan qo'lda sinxron tutiladi.
2. **`safe_sql` = ikki qatlamli mudofaa** (ADR-0002). (a) Postgres **read-only rol** (`readonly_user`,
   `db-init/init.sql`) — asosiy himoya. (b) **`sqlglot` AST validator** — ikkinchi qatlam:
   `sqlparse({sql})` → aniq bitta statement, ildiz `SELECT`, DML/DDL node yo'q. `LIMIT` AST darajasida
   qo'shiladi (string concat EMAS). `statement_timeout` (15s) o'rnatiladi. Komment AST'da yo'qoladi
   → inyeksiya o'ladi. `uv add sqlglot`. Regex qora ro'yxat ISHLATMA.
3. **Grafik: LLM spec + server validatsiya + fallback** (ADR-0003). `make_chart` Vega-Lite spec'ni
   tekshiradi: `mark`+`encoding` bor, `mark ∈ {bar,line,arc,point}`, `data.values` natija qatorlariga
   mos. Buzuq bo'lsa → xavfsiz fallback (jadval yoki birinchi 2 ustun bo'yicha bar). Demo hech qachon
   sinmasin.
4. **Seed determinizm + anchor sana** (ADR-0004). `seed_demo_biz.py` qat'iy RNG urug'i, ~18 oy,
   `ANCHOR_DATE` (default: seed ishlagan kun) atrofida. "Oxirgi oy" mantiq anchor'ga nisbiy, kalendarga
   EMAS. Testlar qotirilgan anchor uzatadi; demo bugungi kunni oladi.

### Agent / API xulqi
5. **Stateless suhbat.** `/chat` har chaqiruvda agentga FAQAT joriy xabarni beradi. Tarix `messages`
   jadvaliga yoziladi (ko'rsatish uchun), LLM'ga UZATILMAYDI. Multi-turn follow-up MVP'da yo'q.
6. **Til.** LLM xabardan RU/UZ/EN ni o'zi aniqlaydi va shu tilda javob beradi. Alohida kutubxona yo'q.
7. **Tool-call cheklovi = 6.** Oshib ketsa → muloyim xato matni, crash EMAS.
8. **Xato UX.** Tool/SQL xatosi ushlanadi; yomon SQL'da 1 marta retry; bo'lmasa muloyim matn + xom
   xato faqat yig'iladigan "tafsilot" ichida. Demo'da xom stack-trace KO'RSATILMAYDI.
9. **SQL + qatorlarni olish.** Bajarilgan SQL va natija qatorlari Pydantic AI **deps** (`RunContext`)
   orqali yoziladi; API run tugagach deps'dan o'qiydi.
10. **LLM'ga qator hajmi.** `run_sql` LLM'ga narrativ uchun faqat birinchi ~50 qatorni qaytaradi;
    UI'ga to'liq (LIMIT ≤1000) qatorlar boradi.
11. **Agent strukturali chiqishi.** Pydantic natija modeli `{text, chart_title, vega_spec}`; `sql`+`rows`
    deps orqali (4-bandga qarama-qarshi emas).
12. **`/chat` javobi:** `{conversation_id, text, sql, rows, vega_spec, chart_title}`.

### Konfiguratsiya / infratuzilma
13. **Bitta Postgres instance, ikki DB** (`app`, `demo_biz`) — `db-init/init.sql` ko'taradi (read-only
    rol shu yerda). Alembic FAQAT `app` DB uchun. **MUHIM tuzatish:** `init.sql` `db-init/` ichida
    bo'lishi shart (docker-compose mount `./db-init`). Ildizda QOLDIRMA.
14. **Model va URL env'dan.** `LLM_MODEL` (default `google-gla:gemini-2.5-flash`), `API_URL`
    (default `http://localhost:8000`). INSON faqat `GOOGLE_API_KEY` qo'yadi.
15. **`saved_charts`** jadvali sxemada bor, lekin MVP'da avto-saqlash YO'Q. Pitch'dan keyin ixtiyoriy.

### Test strategiyasi
16. **Agent testi jonli kalitsiz** — Pydantic AI `TestModel`/`FunctionModel` bilan tool-chaqiruv
    mantig'i. Jonli `GOOGLE_API_KEY` bo'lsa → ixtiyoriy smoke test; bo'lmasa skip (xato EMAS).
