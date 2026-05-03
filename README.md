# Meridian Signal Service

Meridian Signal Service is a Python FastAPI microservice that provides the data and intelligence backbone for Meridian Signals® and Meridian Data®. It exposes authenticated APIs for listings, market reports, signals, comps, and asynchronous report generation.

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
