# Product specification (PRD-001)
Routes: /login, /dashboard, /research, /instruments, /instruments/:symbol, /compare, /portfolio, /reports, /admin/mcp.
Research page: query input, source selector, symbols, lookback, tool-used drawer, dated evidence table, chart outputs, report export and explicit degraded state.
Dashboard: index overview, top movers, breadth, freshness, research CTA.
Instrument explorer: search and equity/SME/bond filters.
Comparison: max 5 supported symbols, aligned data range, numeric metrics and sample sizes.
Portfolio: hypothetical amounts/weights; explain formulas; validation and privacy.
Design: responsive light theme, muted navy/teal, WCAG-conscious contrast, keyboard support; every data card displays time and source.
States: first-load, empty, invalid symbol, market closed, quote stale, source failed, report partly available.
