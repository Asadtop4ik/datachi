# Synthetic data is seeded deterministically around a configurable anchor date

`seed/seed_demo_biz.py` uses a fixed RNG seed and generates ~18 months of sales invoices ending at a
configurable `ANCHOR_DATE` (default: the date the seed is run). All "recent"/"last month" date logic
in the demo and tests is computed relative to this anchor, never to a hardcoded calendar date.

This exists because golden-question tests like "last month's top products in Toshkent" must resolve
deterministically, yet the live pitch demo must still show data that looks current on demo day. A
fixed seed gives reproducible rows; the anchor decouples "what counts as recent" from wall-clock time,
so tests inject a frozen anchor while the demo defaults the anchor to today. Without this, either the
demo shows stale data or the date-sensitive golden tests flake as the calendar moves.
