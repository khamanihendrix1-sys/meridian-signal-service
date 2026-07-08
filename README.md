# Meridian Signal Service

![CI](https://github.com/khamanihendrix1-sys/meridian-signal-service/actions/workflows/ci.yml/badge.svg)

Meridian Signal Service is a Python FastAPI microservice that provides the data and intelligence backbone for Meridian Signals® and Meridian Data®. It exposes authenticated APIs for listings, market reports, signals, comps, and asynchronous report generation.

## Market report capabilities

The `/v1/market-reports` router includes snapshot retrieval plus extended report generation endpoints for:

- comparable properties (`GET /v1/market-reports/comps`)
- investment opportunity signals (`POST /v1/market-reports/investment-signals`)
- neighborhood comparisons (`GET /v1/market-reports/compare`)
- PDF exports (`GET /v1/market-reports/{report_id}/export?format=pdf`)
- forecasts (`GET /v1/market-reports/forecast`)
- heat index scoring (`GET /v1/market-reports/heat-index`)
- seasonal analysis (`GET /v1/market-reports/seasonal`)
- demographic correlation (`GET /v1/market-reports/demographics`)
- scheduled email digests (`POST /v1/market-reports/schedules`)
- custom dashboards (`POST /v1/market-reports/custom`)

## Production deployment

This service should be deployed to a container host (not Vercel). The recommended default is **Fly.io** because this repository already includes a production `Dockerfile` and `deploy/fly.toml` config.

### Fly.io quick start

1. Install and authenticate Fly CLI:
   ```bash
   fly auth login
   ```
2. Create/select the Fly app (if not already created):
   ```bash
   fly launch --no-deploy --config deploy/fly.toml
   ```
3. Set required secrets:
   ```bash
   fly secrets set --app meridian-signal-service DATABASE_URL=...
   fly secrets set --app meridian-signal-service REDIS_URL=...
   fly secrets set --app meridian-signal-service JWT_SIGNING_KEY=...
   ```
   - `DATABASE_URL`: full Postgres connection string including scheme, user, password, host, port, and database name
   - `REDIS_URL`: full Redis connection string (`redis://host:6379/0`)
   - `JWT_SIGNING_KEY`: strong random signing key for JWT tokens
4. Deploy:
   ```bash
   fly deploy --config deploy/fly.toml
   ```

The service exposes `/healthz` for health checks (implemented in `meridian/api/routers/health.py`) and listens on internal port `8000`. In the current implementation, `/healthz` returns a minimal `{"status":"ok"}` response.

## Deployments

This repository includes an automated GitHub Actions workflow (`.github/workflows/deploy-fly.yml`) that handles both preview and production deployments to [Fly.io](https://fly.io).

### Preview deployments (pull requests)

Every pull request automatically:
1. Creates (or reuses) an ephemeral Fly app named `meridian-signal-pr-<PR_NUMBER>`.
2. Deploys the branch to that app in the `iad` region.
3. Posts a comment on the PR with the preview URL: `https://meridian-signal-pr-<PR_NUMBER>.fly.dev`.

When the pull request is **closed or merged**, the preview app is automatically destroyed.

### Production deployment (main / master)

Any push to the `main` or `master` branch deploys to the production app `meridian-signal-service`.

### Required secret

Add the following secret to your repository (**Settings → Secrets and variables → Actions → New repository secret**):

| Secret | Description |
|---|---|
| `FLY_API_TOKEN` | A Fly.io API token with permission to create, deploy, and destroy apps. Generate with `fly auth token`. |

### Assumptions

- The service listens on **port 8000** (as configured in `fly.toml` and the `Dockerfile`). If you change the listen port, update `internal_port` in `fly.toml` to match.
- The production Fly app (`meridian-signal-service`) must already exist in your Fly.io account before the first production deploy. Create it once with:
  ```bash
  fly apps create meridian-signal-service
  ```
- Preview apps are created automatically on first PR deployment; no manual setup is required.
- Fly region is set to `iad` (Washington D.C.). Change `FLY_REGION` in the workflow `env` block to use a different region.

### GitHub Environments (optional but recommended)

Create two environments in **Settings → Environments**:
- `preview` — no approval required.
- `production` — require manual approval before deploy.

## Getting Started

### Requirements
- Python 3.12
- Docker & Docker Compose (for local development)

### Local development

1. Copy `.env.example` to `.env`
2. Start the local stack (Postgres, Redis, API, Celery worker, scheduler):
   ```bash
   docker-compose up --build
   ```
3. Run the API server locally:
   ```bash
   # If running outside Docker, update DATABASE_URL/REDIS_URL in .env to localhost hosts.
   poetry install
   poetry run meridian-api
   ```

### Available commands

- `meridian-api` — start the FastAPI service
- `meridian-worker` — start Celery worker
- `meridian-scheduler` — start APScheduler scheduler
- `meridian-cli` — utility command-line tool

## Project layout

- `meridian/` — application package
- `config/` — runtime configuration manifests
- `deploy/` — deployment manifests for Fly.io and AWS ECS
- `alembic/` — database migrations
- `tests/` — unit, integration, and e2e tests

## Contributing

This repository uses strict typing, structured logging, and OpenAPI-driven API design. All new features must include tests and an Alembic migration if they add persistence.
