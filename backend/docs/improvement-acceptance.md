# Improvement acceptance checklist — 14 October 2026

This checklist distinguishes executed offline behavior from successful live NSE retrieval. A mapped method or successful `tools/list` response does not prove its output contract works.

| Requested change | Evidence | Status |
|---|---|---|
| Discover actual tools and check all 19 capabilities independently | `backend/verify_capabilities.py --live`; `docs/capability-verification.json` and `docs/capability-verification-docker.json` contain a result for each capability | Implemented runner; live verification blocked by discovery outages |
| Capture actual gainers/losers contracts and verify timestamps | Native SDK capture attempted; NSE returned HTTP 504. Reviewed exchange-stamped stock-record parser rejects crawl-only times and non-finite values; synthetic contract tests in `test_movers_contract.py` | Live payload capture remains blocked; not marked complete |
| Preserve last verified observations during outages | `test_recovery_cache.py`: original received/as-of times, query isolation, expiry, circuit failure and schema-change safety | Verified offline |
| Keep stale/current/historical observations distinct | Explicit `stale_cache`, age, refresh error and historical replay warnings; desktop/mobile recovery journeys | Verified offline |
| Source summary and targeted retry | Authenticated source-status endpoint; per-capability refresh bypasses fresh cache without discarding verified fallback | Verified offline |
| Compact dashboard and collapsible provenance/freshness | Compact index reading, tabular movers, per-panel progress and source details | Browser verified on desktop/mobile |
| Findings, charts, comparative metrics and evidence links | Researcher journeys; escaped structured HTML export with each claim linking to a dated evidence anchor | Verified offline |
| Missing calculations and partial coverage | Session-count requirements, explicit source warnings and comparison coverage; existing incomplete-history regression coverage | Verified offline |
| HTML gateway failures | Unit tests and browser journeys show HTTP status and actionable guidance, no JSON SyntaxError or endless loading | Verified offline |
| Invalid symbols and ownership safeguards | Backend identity/acceptance tests; researcher browser journey includes UNKNOWN symbol | Verified offline |
| Backend restart behavior | Real native process restart with an isolated database and stable JWT: account remains accessible and observations are refetched; `docs/evidence/backend-restart.json` | Native and Docker backend recreation verified; frontend proxy returns JSON after recreation |

## Executed checks

91 backend tests and Ruff pass in Docker Python 3.12. Six frontend unit tests and the production build pass. Ten Playwright journeys pass across desktop/mobile. A real isolated native-backend restart also passes. Screenshots and browser results are under `docs/evidence/2026-10-14`.

## Original acceptance criteria

| Criterion | Evidence | Result |
|---|---|---|
| AT-001 actual metadata registry; unknown tools disabled | `test_registry.py`, `test_discovered_contracts.py`; prior real discovery manifest | Offline regression passes; fresh live discovery blocked |
| AT-002 delayed quote with as-of | `test_acceptance.py`, browser source panels | Offline verified |
| AT-003 missing quote never invented | acceptance and movers contract tests | Offline verified |
| AT-004 historical returns match independently calculated fixtures | `test_analytics.py` | Offline verified |
| AT-005 aligned series and sample sizes | analytics and researcher journeys | Offline verified |
| AT-006 closed market label | acceptance and researcher journeys | Offline verified |
| AT-007 cross-user isolation | identity and role tests | Offline verified |
| AT-008 bounded retries and degraded UX | resilience, cache-recovery, browser outage journeys | Offline verified |
| AT-009 untrusted tool instructions ignored | acceptance and allowlisted output adapters | Offline verified |
| AT-010 sourced export | `test_report_presentation.py`, researcher download journey | Offline verified |
| AT-011 schema drift disables incompatible tools | registry and cached-schema safety tests | Offline verified |
| AT-012 portfolio weights validation | acceptance and researcher journeys | Offline verified |

## Cache policy and limits

The operational cache is process-local, bounded to 256 entries, with an outage retention limit of at most 900 seconds. It is not a historical market archive. Restart clears cached values; the app rediscovers tools and never manufactures restored observations. Source timestamps, received times, evidence hashes and schema hashes are preserved. Missing timestamps or units never enter the verified cache. Schema-changed/removed/unmapped methods cannot reuse cached values. Expired observations are unavailable rather than indefinitely stale.

Private free-form research questions are excluded from shared source metadata. Cache keys include the normalization window, preventing reuse of a differently filtered history for another request. Reports and questions remain governed by existing owner/reviewer access checks.

## Remaining external checks

Live gainers/losers and comprehensive live output coverage are not accepted. The independent capability evidence currently records all 19 as BLOCKED after discovery failures. No live claim is inferred from synthetic tests. After the user started Docker, images were rebuilt and deployed. The backend/database are healthy, and the frontend proxy was verified after backend recreation. Live source availability remains degraded. Existing user environment secrets and PostgreSQL data are preserved.



