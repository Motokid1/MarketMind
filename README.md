# MarketMind AI

An educational NSE research workspace with source-attributed market observations, historical comparisons, hypothetical portfolio analysis and reproducible reports. Trading, brokerage integration and personalised investment advice are excluded.

## Repository layout

```text
marketmind/
  frontend/             React + TypeScript + Vite
    src/                UI and API client
    tests/              Unit and desktop/mobile browser tests
    node_modules/       Installed locally; ignored by Git
    Dockerfile
    nginx.conf
  backend/              FastAPI + LangGraph + official MCP SDK
    app/                Authentication, API, analytics, source gateway and reports
    migrations/         Alembic database migrations
    tests/              Offline automated tests
    specs/              Original requirements and reviewed NSE mappings
    docs/               Architecture, operations and acceptance evidence
    venv/               Local Python environment; ignored by Git
    Dockerfile
    requirements.lock
  .github/              Automated verification workflows
  compose.yaml          PostgreSQL, backend and frontend services
  .env                  Local configuration; ignored by Git
  .env.example          Configuration template
  .gitignore
  .dockerignore
  README.md
```

The specification files and reviewed tool mappings are runtime/test dependencies. Supporting Docker and CI files are retained so cleanup does not remove deployment or verification capabilities.

## Stack and behaviour

React, TypeScript, Vite and Recharts provide the UI. FastAPI supplies authenticated APIs with owner/reviewer access checks. LangGraph coordinates bounded research workflows; calculations use decimal arithmetic and aligned trading sessions. PostgreSQL is used in Docker, with SQLite as the native-development default.

NSE methods are discovered using the official MCP SDK and pinned to reviewed schemas. Unknown or incompatible methods remain disabled. The dashboard distinguishes current observations, historical replay, missing evidence, empty results and retained stale values. Its bounded operational cache retains verified observations for at most 15 minutes during an outage and clears on restart. Reports link quantitative findings to dated evidence. No external LLM key is required.

## Run with Docker (recommended)

Start Docker Desktop with its Linux engine, then use PowerShell:

```powershell
Set-Location "D:\Projects - AI\marketmind"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose ps
```

For a new installation, replace the secret placeholders in `.env` before starting. Set independent `POSTGRES_PASSWORD` and `JWT_SECRET` values, your registration email in `ADMIN_EMAILS` if administrator access is required, and `MCP_MODE=live` or `mock`. Preserve the original password when using an existing PostgreSQL volume. Existing configuration and database data were preserved during cleanup.

Defaults: frontend http://localhost:5173, API documentation http://localhost:8000/docs. Register an account and acknowledge educational use. There are no seeded credentials. Docker runs migrations automatically.

```powershell
Invoke-RestMethod "http://localhost:8000/health/ready"
docker compose logs --tail=100 backend
docker compose down   # Stops services; retains database volume
```

## Native development

Docker uses Python 3.12; the installed local `backend/venv` uses this machine's Python 3.11. Node.js 22+ is required. Stop Docker services first if using the same ports.

Backend terminal:

```powershell
Set-Location "D:\Projects - AI\marketmind\backend"
# Recreate if needed: py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.lock
$env:MCP_MODE = "mock"
$env:JWT_SECRET = "replace-with-a-long-stable-local-secret"
$env:ADMIN_EMAILS = "your-email@example.com"
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
Set-Location "D:\Projects - AI\marketmind\frontend"
npm ci
npm run dev
```

Mock mode uses explicitly labeled synthetic symbols such as ALPHA and BETA. Live mode depends on NSE availability; successful tool discovery alone does not establish successful data retrieval.

## Verification

From the project root:

```powershell
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python -m ruff check app tests verify_capabilities.py
docker compose exec -T backend python verify_capabilities.py --live --output /srv/backend/capability-verification.json
docker compose cp backend:/srv/backend/capability-verification.json .\backend\docs\capability-verification-docker.json
```

Native backend checks, from `backend`:

```powershell
.\venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\venv\Scripts\python.exe -m ruff check --no-cache app tests verify_capabilities.py
```

Frontend checks, from `frontend`:

```powershell
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests require a running migrated backend in `MCP_MODE=mock` with `ADMIN_EMAILS=admin@example.test`; they must not run against live NSE data. Generated builds, environments, test output and caches are ignored by Git.

Latest feature verification: 91 backend tests, six frontend unit tests, ten browser journeys, lint, production build and restart checks passed. Live NSE checks remained blocked by upstream discovery outages; full live acceptance is not marked complete. See [the acceptance checklist](backend/docs/improvement-acceptance.md), [operations guide](backend/docs/runbook.md) and [original specifications](backend/specs/README.md).
