# Business requirements (BRD-001)
**UC-001 Morning briefing:** User selects index, date, lookback, securities; planner resolves symbols; gets market/index/movers/breadth; history agent retrieves comparable OHLCV; analytics node computes figures; evidence validator verifies each claim; user receives saved source-attributed report.
**UC-002 Equity comparison:** Align trade dates, calculate comparable returns/drawdowns; show missing data.
**UC-003 Volume anomalies:** Calculate explicit rolling-baseline ratio; never claim the cause without evidence.
**UC-004 Instrument explorer:** Equity, SME, bond lists with segment labels.
**UC-005 Hypothetical portfolio:** Weights and historical risk only; no brokerage or advice.
**UC-006 Reproducibility:** Store run, params, schema hash, evidence and calculation version.
**UC-007 Historical market replay:** Historical gainers/losers/breadth and closing quotes.
**UC-008 Tool observability:** Registry, availability, latency and errors.
KPIs: complete capability mapping, 100% auditable quantitative values, 100% visible source timestamps, unauthorized-read prevention.
