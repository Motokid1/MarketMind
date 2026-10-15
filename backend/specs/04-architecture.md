# Architecture (ARCH-001)
React+Vite -> FastAPI -> LangGraph supervisor -> tool gateway (NSE MCP Bhavcopy + CM Market) -> normalization -> deterministic analytics -> evidence validator -> report.
PostgreSQL persists users, runs, registry, invocation metadata, calculation records and report metadata. Redis optional for cache; development may use memory TTL cache.
Graph nodes: intent parser, plan validator, market worker, history worker, universe worker, calculation worker, evidence validator, writer, report publisher.
Calls can parallelize when independent; cap fanout and max calls; disallow arbitrary server URLs, shell/SQL/broker calls. Logs include correlation IDs but no credentials or indiscriminate raw data dumps.
Cloud or private deployment must clear G0 policy review. Default demonstration uses local Docker Compose.
ADR-001: separate deterministic arithmetic from LLM writing.
ADR-002: adapter layer abstracts changing NSE tool names.
ADR-003: fail closed on missing source evidence and stale current data.
