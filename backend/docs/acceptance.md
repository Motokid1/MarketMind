# Acceptance record

Verified on 11 October 2026 in the local educational environment. This record does not grant data rights or constitute product-owner/reviewer/release approval. Original specifications were not modified.

## Executed evidence

- Official tools/list discovery succeeded on both specified NSE endpoints with official Python SDK 1.26. The metadata-only manifest records 36 actual methods and their schemas/hashes. Nineteen capability bindings were reviewed against those exact schemas. Unknown methods remain disabled.
- Backend: 69 automated tests pass under Python 3.12 inside the Linux Compose image; native Windows tests also passed. Ruff passes. Tests cover pure analytics, registry contracts, FastAPI identity/ownership, reviewer sharing, retention, bounded graph execution, cache latency and a Streamable HTTP MCP server/SDK round trip. CI defaults to synthetic fixtures.
- Frontend: strict TypeScript and Vite production build pass; two formatting tests pass. Four Playwright journeys pass against the PostgreSQL Compose stack: researcher and administrator on desktop and mobile. Screenshots are under docs/evidence. Research journeys exercise aligned charts, sourced export and invalid portfolio weights.
- Live opt-in smoke: six bounded checks pass for symbol lookup, OHLCV, breadth, quote, index and equity listing. See live-smoke.json. No source prices were saved to this evidence file. Separate response-shape probes verified SME/bond listing contracts and documented current-mover errors.
- Docker Compose builds and starts PostgreSQL 16, FastAPI and nginx/React on loopback. Database and backend health checks pass. Schema reaches migration 0002. Native SQLite upgrade/downgrade/upgrade was rehearsed.
- PostgreSQL backup restored into separate marketmind_restore_check. Both original and restore have migration 0002 and two research runs at the checkpoint. The original database was preserved.
- Final live-mode Compose HTTP smoke: frontend 200, research creation 201 and export 200. Source calls timed out and produced an explicitly degraded report with zero quantitative claims. See container-smoke.json. This proves outage behavior, not a successful live container briefing. Native live smoke remains independently successful.

## Acceptance criteria

| Criterion | Verified behavior | Evidence |
|---|---|---|
| AT-001 | Actual schema manifest; unknown methods disabled; reviewed hashes checked | test_discovered_contracts.py, test_registry.py, manifest |
| AT-002 | Delayed badges and source/received timestamps; IST formatting | test_AT002_delayed_quote, frontend format test and browser journeys |
| AT-003 | Missing price remains null; no invented value/date | test_AT003_missing_quote, bare-price adapter test |
| AT-004 | Independent fixture gives 8% return and -25% drawdown | test_AT004_independent_return_and_drawdown |
| AT-005 | Inner-join trading sessions; original/aligned sample counts and missing dates | test_AT005_alignment, browser comparison journey |
| AT-006 | Closed source labeled latest-known session, not live | test_AT006_closed_session, browser journey, live closed quote/index |
| AT-007 | Cross-user run and export denied; admin controls return 403 | test_AT007_owner_isolation_and_rbac, role tests |
| AT-008 | Timeout retry bounded; full outage produces degraded report with no numeric claims | test_AT008_bounded_timeout, test_fully_unavailable_is_explicit_degraded |
| AT-009 | Embedded tool instruction ignored; writer consumes only normalized facts | test_AT009_injection_is_data_and_AT010_export |
| AT-010 | HTML export contains trace, source/date metadata, formulas, caveats and disclaimer | combined export test, downloaded file in browser journey |
| AT-011 | Input-schema change disables method and emits registry alert | test_registry_requires_review_and_pins_schemas |
| AT-012 | Invalid fractional weights rejected; no silent normalization | test_AT012_weights_api, browser portfolio validation |

## Task and requirement traceability

| Task | FR IDs | API / storage / verification |
|---|---|---|
| T01 | FR-019 | Vite/FastAPI shell, pinned dependency locks, Compose, CI, production build |
| T02 | FR-001,020 | auth/register/login/me, ownership and role checks; migration 0001; identity/role tests |
| T03 | FR-002,003 | tools/list sync and hash-reviewed registry; metadata manifest; registry/schema tests |
| T04 | FR-015,016,017 | normalized gateway, bounded retries/cache/circuit breakers; invocation/observation tables; resilience tests |
| T05 | FR-004,006,010,019 | overview, search, quote/history/range; dashboard/explorer/detail views; timestamp/closed/missing tests and screenshots |
| T06 | FR-005,007,008,009 | decimal metrics, history chunks and comparison API; independent fixtures, alignment and volume baseline tests |
| T07 | FR-011,016,017 | LangGraph intent/universe/planning/concurrent workers/calculation/evidence/writer/compliance/publisher; injection and call-budget tests |
| T08 | FR-013,014,016 | owned run history, reviewer sharing/annotations, derived HTML exports; report/metric tables; export and access tests |
| T09 | FR-008,012 | comparison and hypothetical portfolio; exact weight validation; independent calculation and browser tests |
| T10 | FR-003,015,018 | administrator observability, schema review, user permissions and retention; migration 0002; admin browser and retention tests |
| T11 | FR-001,016,017,019,020 | offline/live separation, desktop/mobile E2E, security tests, fixture latency check, Linux Compose and restore rehearsal |

## Remaining gates and known limits

G1 discovery is verified. All twelve TEST-001 criteria above have executed local evidence. Broader release approval is **not marked complete**: G0 external data-rights approval, specification/product-owner review and G3 organizational deployment approval remain external gates. This is a locally executable research prototype, not a licensed production deployment.

NSE current gainers/losers returned error objects in the live probe, so those panels degrade explicitly. Historical bare-price and 52-week summary responses lacked adequate source-as-of evidence; those numeric outputs remain unavailable. B04/B05/B06/B09 input bindings are mapped, while unverified direct-response shapes fail closed; the application implements returns, volume and comparison from validated OHLCV. Full live output-contract coverage of every applicable method remains pending, and is not inferred from schema-only tests.

NSE retrieval also timed out from the live Docker runtime on the final checkpoint. The app stays available and marks the report degraded. A successful live-container briefing remains unverified; do not mark complete end-to-end live acceptance or release approval on the strength of the synthetic container tests.

Long histories can exceed the interactive twelve-call budget; only received eligible sessions are calculated and partial coverage is disclosed. Initial manifests may change: rediscovery can require renewed review. Raw source data is intentionally not archived; saved derived records and hashes are inspectable, while refreshed source reproduction is a new run. Historical prices remain unadjusted and must not be interpreted as actual economic loss around corporate actions.

The writer is deterministic; an external LLM integration is not required or claimed. WCAG-conscious keyboard labels and responsive journeys are tested, but no formal accessibility certification is asserted. Cached fixture latency is tested against the eight-second target; no production load/SLA claim is made. Production TLS, volume encryption, distributed throttling and comprehensive output-contract coverage require further release work.
