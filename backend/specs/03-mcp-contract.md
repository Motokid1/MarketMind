# MCP integration specification (MCP-001)
Endpoints (HTTPS Streamable HTTP):
- Bhavcopy: https://mcp.nseindia.in/bhavcopy/cm/mcp
- CM Market: https://mcp.nseindia.in/cmmkt/mcp
No auth configured per NSE public overview; never embed secrets if this changes.
### Discovery gate
Use official MCP Python SDK. Initialize clients and call `list_tools()` on each endpoint. Persist only method metadata, inputSchema and schema hash in `specs/generated/nse-tool-manifest.json`. Compare discovered names and descriptions against capability registry; manual review mismatches. Do not assume documented capability phrases are callable tool names. Do not ship static guessed method names.
### Official capability categories
Bhavcopy: stock history OHLCV; breadth; last price on date; symbol search; performance/returns; volume trends; bulk quotes; gainers/losers by date; multi-stock compare; 52-week high/low.
CM Market: current top gainers; index data; SME listings; single quotes; current losers; all equities; bond listings; freshness status.
### Adapter output contract
`{service, method, instrument, value, units, currency, source_as_of, received_at, data_delay_label, evidence_id, missing_fields, raw_ref, status}`
Enforce schema validation, hostname allowlist, bounded timeouts/retries, jitter, circuit breakers, configurable TTL, max response size, input/output escaping, transparent errors. Delay is typically 1-3 min for CM market; never promise current ticks.
