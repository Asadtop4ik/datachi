# Schema delivered to the agent via a static prompt map, not pure tool introspection

The agent receives a hand-written compact schema map (tables, columns, types, FKs, UZS hints) baked into its system prompt. `list_tables`/`get_schema` tools are kept only for fetching live sample rows, not for the agent to discover structure.

BUILD_PLAN.md describes pure tool introspection (agent calls `list_tables` then `get_schema` before querying). We deliberately deviate: for a pitch demo on a fixed synthetic schema, prompt-injected schema is deterministic, cheaper (fewer LLM round-trips), faster, and makes golden-question tests stable. Trade-off: the prompt map must be kept in sync with `seed/seed_demo_biz.py` by hand. Acceptable because the seed schema is small and frozen for the demo.
