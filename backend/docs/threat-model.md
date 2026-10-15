# Security boundaries

Identity: PBKDF2-SHA256 with individual random salts and 600,000 rounds; signed short-lived JWTs with explicit algorithm, issuer, audience and required expiry; each API request reloads an active user from the database. JWT role data is not trusted. Administrator accounts additionally require an environment allowlist. Login and run submissions have bounded local protection; a multi-process external deployment needs a shared limiter.

Ownership: server-side user ID scopes run reads. Report reads/export permit the owner or an explicitly shared reviewer. Administrative role does not bypass report ownership. Passwords and tokens are not logged or included in exports. Reviewer comments are bounded text and React escapes display output.

External tools: only the two exact NSE HTTPS endpoints are configured. Research input cannot select a URL, method, SQL, shell, broker or schema. MCP HTTP calls do not follow redirects. Names and schemas originate from tools/list and require hash-matched mappings. Schema changes disable the method. Incoming payloads are bounded and normalized; tool instructions/descriptions never execute as application instructions.

Reports: quantitative claims come from verified observations or deterministic metrics. Missing units/as-of time drops the source value. Stale quotes cannot enter current-movement claims. Export escapes JSON into an inert HTML document with a restrictive CSP and includes trace IDs, timestamps and limitations. A report is a private derived artifact rather than a raw data download.

Local runtime: non-root backend container; database network is internal; HTTP ports bind to loopback. Secrets are generated into ignored .env only for the running local environment, and are excluded from the deliverable archive. Production TLS, at-rest encryption, centralized secret management, cross-process throttling and an organizational privacy review remain release controls, not claims established by a local demo.
