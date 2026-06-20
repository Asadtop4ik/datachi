# DEMO_SCRIPT — pitch (5 savol)

Demo `demo_biz` sintetik savdo bazasida ishlaydi. Har savol uchun agent: tilni aniqlaydi →
xavfsiz `SELECT` yozadi → grafik + 3 jumlagacha izoh qaytaradi. "SQL ko'rsatish" expander'ida
xavfsizlikni ko'rsating (faqat SELECT, LIMIT bilan).

## Ssenariy

1. **UZ — top mahsulotlar (bar).**
   > Oxirgi oyda Toshkentda eng ko'p sotilgan mahsulotlar?

   _Ko'rsatish:_ bar grafik + SQL (join `sales_invoice_items` → `items`, `posting_date` filtri).

2. **UZ — shahar bo'yicha tushum (bar).**
   > Shahar bo'yicha umumiy tushum qancha?

   _Ko'rsatish:_ 5 shahar bo'yicha tushum; Toshkent yetakchi.

3. **UZ — oylik trend (line).**
   > Oylik savdo trendini ko'rsat

   _Ko'rsatish:_ vaqt bo'yicha chiziqli grafik (~18 oy).

4. **RU — o'rtacha chek (til almashishi).**
   > Какой средний чек?

   _Ko'rsatish:_ javob **rus tilida** — til avtomatik aniqlanadi.

5. **UZ/RU — top mijozlar (bar).**
   > Tushum bo'yicha eng yaxshi 10 mijoz

   _Ko'rsatish:_ top-10 mijoz, `LIMIT` AST darajasida majburlangan.

## Xavfsizlik momenti (pitchda alohida ayting)

- LLM xom SQL'ni to'g'ridan DB'ga YUBORMAYDI — hamma so'rov `safe_sql` orqali (sqlglot AST:
  bitta SELECT, DML/DDL blok, majburiy LIMIT, 15s timeout), va biznes bazaga FAQAT read-only rol
  ulanadi. Komment-inyeksiya AST generatsiyada o'ladi.
- Buzuq grafik bo'lmaydi: spec server'da tekshiriladi, kerak bo'lsa xavfsiz fallback.

## Zaxira savollar

- Segmentlar bo'yicha tushum ulushi (pie/arc).
- "Best selling items by quantity" (EN).
- Status bo'yicha hisob-fakturalar soni.
