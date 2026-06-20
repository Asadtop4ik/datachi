# safe_sql validates via sqlglot AST, behind a read-only Postgres role (defense in depth)

LLM-generated SQL never reaches the business DB unchecked. Two independent layers guard it:

1. **Read-only Postgres role** (primary): the agent connects to `demo_biz` with a role that has no INSERT/UPDATE/DELETE/DDL grants. Even a validator bypass cannot mutate data.
2. **`sqlglot` AST validator** (secondary): SQL is parsed to an AST and rejected unless it is exactly one statement with a `SELECT` root and no DML/DDL nodes. A mandatory `LIMIT` is injected at the AST level (not string concatenation), and a `statement_timeout` is set on execution. Parsing to an AST drops comments, so comment-based injection dies.

We chose `sqlglot` over regex/keyword blacklists (fragile against `/**/`, casing, encoded payloads — weak answer to "how do you keep it safe?" in the pitch) and over `sqlparse` (token-level, not a full AST, forces hand-handling of CTE/subquery edge cases). The new dependency is justified because this validator is the product's core safety claim.
