SHELL := /bin/bash

.PHONY: install dev test lint format migrate seed-mock docker-build docker-run

install:
	poetry install

dev:
	poetry run uvicorn meridian.main:app --reload --host 0.0.0.0 --port 8000

test:
	poetry run pytest

lint:
	poetry run ruff check .
	poetry run black --check .
	poetry run mypy meridian

format:
	poetry run black .
	poetry run ruff format .

migrate:
	poetry run alembic upgrade head

seed-mock:
	poetry run meridian-cli seed-mock

docker-build:
	docker build -t meridian-signal-service:local .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env meridian-signal-service:local
