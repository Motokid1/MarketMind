# Acceptance tests (TEST-001)
- AT-001 tools/list -> tool registry matches actual schemas; unknown methods disabled.
- AT-002 current quote delayed -> as-of and delayed badge shown.
- AT-003 missing quote -> no invented price/return.
- AT-004 historical return -> matches independently computed fixture.
- AT-005 two stock history series -> aligned by trading sessions, sample sizes shown.
- AT-006 closed market -> latest known session labeled rather than “live”.
- AT-007 cross-user research read -> denied.
- AT-008 upstream timeout -> bounded retry and degraded UX.
- AT-009 prompt injection in tool data -> ignored as instructions.
- AT-010 exported report -> trace IDs, sources, dates, caveats and disclaimer.
- AT-011 breaking inputSchema change -> incompatible tool disabled + alert.
- AT-012 invalid portfolio weights -> validation error or explicit normalization approval.
CI tests must use mock MCP servers by default; live tests explicit opt-in only.
