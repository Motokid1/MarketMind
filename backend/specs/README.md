# MarketMind AI — spec-driven implementation pack

**Status:** design only; not implemented. Educational/informational/private prototype. NSE official MCP data must not be used for commercial deployment, trading, or individualized advice.

## Order of execution
1. Read 00-charter.md and 01-business-requirements.md.
2. Validate NSE public terms and execute 03-mcp-contract.md discovery gate.
3. Implement 04-architecture.md / 05-api-data-contract.md in small vertical slices.
4. Implement 06-agent-workflows.md with deterministic analytics.
5. Implement tests from 07-acceptance-tests.md before marking feature done.
6. Execute 08-delivery-plan.md and 09-release-runbook.md.

**Rule:** never invent NSE tool methods or parameters. Discover through tools/list, pin schema snapshots, and fail safely if the capabilities differ.
