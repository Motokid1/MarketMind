# API and storage spec (API-001 / DATA-001)
Base `/api/v1`; JSON. Routes: POST auth/login; GET market/overview; GET instruments/search; GET instruments/{symbol}/quote; GET instruments/{symbol}/history; POST research/runs; GET research/runs/{id}; POST research/comparisons; POST portfolio/simulate; GET reports/{id}/export; GET admin/mcp/capabilities; GET /health/live and /health/ready.
Error shape: `{request_id, error_code, message, retryable, details?}`. Authenticated object lookup must scope by server-derived owner identity.
Tables: users, research_runs, tool_registry, tool_invocations, market_observations (rights-compliant minimal persisted), calculated_metrics, reports, audit_events.
Dates ISO-8601 Asia/Kolkata for display; UTC-aware internal timestamps; amounts in INR; preserve decimal precision; nullable missing metrics.
No historical market data archive or redistribution unless data policy allows it.
