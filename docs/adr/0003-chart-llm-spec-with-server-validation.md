# Charts: LLM emits a Vega-Lite spec, the server validates it and falls back safely

The Analyst Agent's `make_chart` tool receives a Vega-Lite spec from the LLM, but the spec is never trusted blindly. `make_chart` validates it server-side: required keys (`mark`, `encoding`) present, `mark` in a whitelist (`bar`, `line`, `arc`, `point`), and `data.values` consistent with the actual result rows. On any failure it returns a safe fallback (a plain table, or a default bar chart over the first two columns) instead of a broken spec.

We chose this over (a) passing the raw LLM spec straight to the UI — one malformed spec breaks the chart live during the pitch — and over (b) having the LLM emit only a structured chart intent that the server renders into a fixed template — safest, but too rigid for the variety of demo questions. Validation-plus-fallback keeps the LLM's flexibility while guaranteeing the demo never renders a broken chart.
