# LangGraph workflow (AGENTS-001)
Input -> resolve symbols/intent -> validate plan -> concurrent allowed data-retrieval workers -> normalize data -> deterministic calculation -> evidence checker -> narrative writer -> final compliance check -> report.
State keys: run_id, owner, intent, params, plan, tools_called, observations, metrics, evidence_ids, warnings, status, final.
Assertions: every number in final has evidence_id + verified units/time; no external tools except allowlist; no buy/sell instruction; no invented reasons for movement.
Recovery: retry transient network errors within bounds; missing data -> partial report flagged; stale quote -> historical-only mode; ambiguous symbol -> explicit ambiguity response; tools/schema changed -> registry unhealthy and method disabled.
LLM is not the calculator and cannot choose raw tools without typed validation.
