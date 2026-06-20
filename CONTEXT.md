# Datachi — AI Analytics

Natural-language analytics over a synthetic, ERPNext-shaped sales database: a manager asks a
question in chat, the agent writes safe read-only SQL, and answers with a chart and a short
explanation. The demo runs only on synthetic data.

## Business domain (demo_biz)

**Customer**:
A person or organization that buys; has a city and a segment.
_Avoid_: Client, buyer, account

**Item**:
A product offered for sale, with a category and a unit price in UZS.
_Avoid_: Product, SKU, good

**Sales Invoice**:
A dated record of a sale to one Customer, with a status and a UZS total.
_Avoid_: Order, bill, sale, receipt, transaction

**Sales Invoice Item**:
A single line of a Sales Invoice: one Item, a quantity, and a UZS amount.
_Avoid_: Line item, order line, detail

**City**:
The Uzbek city a Customer belongs to (Toshkent, Samarqand, Buxoro, Andijon, Namangan).

**Segment**:
A business classification of a Customer used to group revenue.

## Product

**Analyst Agent**:
The LLM agent that turns one question into safe SQL, a result set, a chart, and a short
narration in the user's language.
_Avoid_: Bot, assistant, AI

**Safe SQL gateway**:
The mandatory checkpoint every query passes through before touching the business database:
read-only, SELECT-only, single statement, forced LIMIT, timeout.
_Avoid_: SQL runner, executor, validator (it is both)

**Connector**:
The boundary that exposes a business dataset to the Analyst Agent. The demo uses a synthetic
connector; a live ERPNext connector implements the same boundary after the pitch.
_Avoid_: Adapter, driver, integration

**Demo Business DB / demo_biz**:
The synthetic, read-only sales database the Analyst Agent queries. Distinct from the app
database, which holds conversations and saved charts.
_Avoid_: Business DB, prod DB, client DB
