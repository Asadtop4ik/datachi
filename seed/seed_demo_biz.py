"""Sintetik, ERPNext-shaklidagi savdo ma'lumotini demo_biz bazasiga yozadi.

Determinizm (ADR-0004): qat'iy RNG urug'i + ANCHOR_DATE. ~18 oylik diapazon anchor'da tugaydi.
"Oxirgi oy" mantiq anchor'ga nisbiy, kalendarga emas. Testlar qotirilgan anchor uzatadi;
demo bugungi kunni oladi (default).

Jadvallar (CONTEXT.md domen tili):
  customers(id, name, city, segment)
  items(id, name, category, unit_price_uzs)
  sales_invoices(id, customer_id, posting_date, status, total_uzs)
  sales_invoice_items(id, invoice_id, item_id, qty, amount_uzs)

Ishga tushirish: uv run python seed/seed_demo_biz.py
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

# seed/ paket emas — root'ni sys.path ga qo'shamiz, shunda `src` import bo'ladi.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import (  # noqa: E402
    BigInteger,
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    insert,
)
from sqlalchemy.engine import Engine  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.db import get_biz_engine  # noqa: E402

RNG_SEED = 42
N_CUSTOMERS = 500
N_ITEMS = 80
N_INVOICES = 20_000
MONTHS_SPAN = 18
DAYS_SPAN = MONTHS_SPAN * 30

CITIES = ["Toshkent", "Samarqand", "Buxoro", "Andijon", "Namangan"]
CITY_WEIGHTS = [0.40, 0.20, 0.15, 0.13, 0.12]  # Toshkent eng katta ulush
SEGMENTS = ["Enterprise", "SMB", "Retail", "Government", "Wholesale"]
STATUSES = ["Paid", "Unpaid", "Overdue"]
STATUS_WEIGHTS = [0.70, 0.20, 0.10]
CATEGORIES = ["Electronics", "Furniture", "Stationery", "Appliances", "Tools", "Groceries"]

_COMPANY_HEAD = [
    "Oltin",
    "Zamon",
    "Yangi",
    "Buyuk",
    "Sharq",
    "Markaz",
    "Hilol",
    "Baraka",
    "Nur",
    "Asl",
    "Mega",
    "Universal",
    "Premium",
    "Optima",
    "Global",
    "Ipak",
]
_COMPANY_TAIL = ["Savdo", "Trade", "Group", "Servis", "Market", "Logistic", "Invest"]
_COMPANY_SUFFIX = ["MChJ", "AJ", "QK", "LLC"]

_ITEM_ADJ = ["Pro", "Max", "Lite", "Plus", "Eco", "Smart", "Classic", "Ultra", "Mini", "Standard"]
_ITEM_NOUN = {
    "Electronics": ["Telefon", "Noutbuk", "Monitor", "Quloqchin", "Planshet"],
    "Furniture": ["Stol", "Stul", "Shkaf", "Divan", "Polka"],
    "Stationery": ["Daftar", "Ruchka", "Papka", "Marker", "Qog'oz"],
    "Appliances": ["Muzlatgich", "Konditsioner", "Pech", "Changyutgich", "Mikser"],
    "Tools": ["Drel", "Bolg'a", "Otvertka", "Arra", "Kalit"],
    "Groceries": ["Choy", "Shakar", "Guruch", "Yog'", "Un"],
}

metadata = MetaData()

customers = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("city", String(40), nullable=False),
    Column("segment", String(40), nullable=False),
)

items = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(120), nullable=False),
    Column("category", String(40), nullable=False),
    Column("unit_price_uzs", BigInteger, nullable=False),
)

sales_invoices = Table(
    "sales_invoices",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False, index=True),
    Column("posting_date", Date, nullable=False, index=True),
    Column("status", String(20), nullable=False),
    Column("total_uzs", BigInteger, nullable=False),
)

sales_invoice_items = Table(
    "sales_invoice_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("invoice_id", Integer, ForeignKey("sales_invoices.id"), nullable=False, index=True),
    Column("item_id", Integer, ForeignKey("items.id"), nullable=False, index=True),
    Column("qty", Integer, nullable=False),
    Column("amount_uzs", BigInteger, nullable=False),
)


def _company_name(rng: random.Random) -> str:
    return f"{rng.choice(_COMPANY_HEAD)} {rng.choice(_COMPANY_TAIL)} {rng.choice(_COMPANY_SUFFIX)}"


def _item_name(rng: random.Random, category: str) -> str:
    return f"{rng.choice(_ITEM_NOUN[category])} {rng.choice(_ITEM_ADJ)}"


def _build_rows(anchor: date) -> dict[str, list[dict]]:
    rng = random.Random(RNG_SEED)
    start = anchor - timedelta(days=DAYS_SPAN)

    customer_rows = [
        {
            "id": i,
            "name": _company_name(rng),
            "city": rng.choices(CITIES, weights=CITY_WEIGHTS, k=1)[0],
            "segment": rng.choice(SEGMENTS),
        }
        for i in range(1, N_CUSTOMERS + 1)
    ]

    item_rows = []
    for i in range(1, N_ITEMS + 1):
        category = rng.choice(CATEGORIES)
        item_rows.append(
            {
                "id": i,
                "name": _item_name(rng, category),
                "category": category,
                # 20 000 .. 8 000 000 UZS, mingga yaxlitlangan
                "unit_price_uzs": rng.randint(20, 8000) * 1000,
            }
        )

    price_by_item = {r["id"]: r["unit_price_uzs"] for r in item_rows}

    invoice_rows: list[dict] = []
    invoice_item_rows: list[dict] = []
    line_id = 0
    for inv_id in range(1, N_INVOICES + 1):
        # Engil o'sish trendi: keyingi sanalar biroz ko'proq ehtimol.
        bias = rng.random() ** 0.85
        day_offset = int(bias * DAYS_SPAN)
        posting = start + timedelta(days=day_offset)
        customer_id = rng.randint(1, N_CUSTOMERS)
        total = 0
        n_lines = rng.randint(1, 4)
        chosen = rng.sample(range(1, N_ITEMS + 1), k=n_lines)
        for item_id in chosen:
            line_id += 1
            qty = rng.randint(1, 20)
            amount = qty * price_by_item[item_id]
            total += amount
            invoice_item_rows.append(
                {
                    "id": line_id,
                    "invoice_id": inv_id,
                    "item_id": item_id,
                    "qty": qty,
                    "amount_uzs": amount,
                }
            )
        invoice_rows.append(
            {
                "id": inv_id,
                "customer_id": customer_id,
                "posting_date": posting,
                "status": rng.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0],
                "total_uzs": total,
            }
        )

    return {
        "customers": customer_rows,
        "items": item_rows,
        "sales_invoices": invoice_rows,
        "sales_invoice_items": invoice_item_rows,
    }


def _bulk_insert(engine: Engine, table: Table, rows: list[dict], chunk: int = 5000) -> None:
    with engine.begin() as conn:
        for i in range(0, len(rows), chunk):
            conn.execute(insert(table), rows[i : i + chunk])


def seed(anchor: date | None = None, engine: Engine | None = None) -> dict[str, int]:
    """demo_biz ni qaytadan yaratadi va to'ldiradi. Qaytaradi: jadval -> qator soni."""
    settings = get_settings()
    if anchor is None:
        if settings.anchor_date:
            anchor = date.fromisoformat(settings.anchor_date)
        else:
            # Bugungi kun. ADR-0004: demo anchor'i = seed ishlagan kun.
            anchor = date.today()  # noqa: DTZ011
    engine = engine or get_biz_engine()

    data = _build_rows(anchor)

    # Toza qayta seed: barcha jadvallarni qaytadan yaratamiz.
    metadata.drop_all(engine)
    metadata.create_all(engine)

    counts: dict[str, int] = {}
    for table in (customers, items, sales_invoices, sales_invoice_items):
        rows = data[table.name]
        _bulk_insert(engine, table, rows)
        counts[table.name] = len(rows)
    return counts


if __name__ == "__main__":
    result = seed()
    print("Seed tugadi. Qatorlar:")
    for name, n in result.items():
        print(f"  {name:24s} {n:>8d}")
