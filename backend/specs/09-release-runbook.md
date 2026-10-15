# Release and operational runbook (OPS-001)
Development: Python 3.12+, Node 22+, Docker Desktop optional, PostgreSQL 16+, optional Redis.
`docker compose up --build` in implementation repository once files exist; never mistake this specification-only pack for a running implementation.
Private release gates: compliance approval; schema discovery pass; test suite pass; admin allowlist; secret scan; auth isolation; market closed/stale UX; smoke tests with fixed quotas; restore test.
Operational monitors: upstream availability, tool fail rate, tool latency, cache ages, stuck runs, hallucinated-number assertion, rate-limit events and LLM cost.
Rollback: stop new runs, revert app image and migration only when reversible; preserve completed run records.
Retention: minimal rights-compliant market-data caches; configure deletion for reports and user data.
