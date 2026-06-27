# Meridian Signal Service

![CI](https://github.com/khamanihendrix1-sys/meridian-signal-service/actions/workflows/ci.yml/badge.svg)

Meridian Signal Service is a Python FastAPI microservice that provides the data and intelligence backbone for Meridian Signals® and Meridian Data®. It exposes authenticated APIs for listings, market reports, signals, comps, and asynchronous report generation.

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

## Getting Started

### Requirements
- Python 3.12
- Docker & Docker Compose (for local development)

### Local development

1. Copy `.env.example` to `.env`
2. Start the local stack:
   ```bash
   docker-compose up --build
   ```
3. Run the API server locally:
   ```bash
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
