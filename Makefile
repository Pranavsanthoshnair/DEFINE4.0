# Makefile — Veylo PR 002
# Owner: Member 4
# Usage: make <target>

.PHONY: up down logs migrate seed test lint fmt backup help

COMPOSE = docker compose
PROJECT = pr002

## Start all services in the background
up:
	$(COMPOSE) up -d
	@echo "Services started. Run 'make logs' to follow output."

## Stop all services (keep volumes)
down:
	$(COMPOSE) down

## Stop all services and remove volumes (DESTRUCTIVE)
destroy:
	$(COMPOSE) down -v

## Follow logs for all services (Ctrl+C to stop)
logs:
	$(COMPOSE) logs -f

## Follow logs for a specific service: make logs-api
logs-%:
	$(COMPOSE) logs -f $*

## Run Alembic migrations inside the api container
migrate:
	$(COMPOSE) exec api alembic -c backend/alembic.ini upgrade head

## Seed the database (presets, admin user)
seed:
	$(COMPOSE) exec api python -m app.db.seed

## Run all tests (Python + frontend)
test: test-py test-web

## Run Python tests (ruff + pytest)
test-py:
	$(COMPOSE) exec api bash -c "ruff check . && pytest -x -q"

## Run frontend tests (ESLint + tsc + Vitest)
test-web:
	cd frontend && npm run lint && npx tsc --noEmit && npx vitest run

## Run linters only (no tests)
lint:
	$(COMPOSE) exec api ruff check .
	cd frontend && npm run lint

## Auto-format code
fmt:
	$(COMPOSE) exec api ruff format .

## Run the database backup script (requires .env to be sourced)
backup:
	bash infra/backup/pg_backup.sh

## Rebuild and restart a single service: make rebuild-api
rebuild-%:
	$(COMPOSE) build $*
	$(COMPOSE) up -d --no-deps $*

## Pull latest images and redeploy (production)
deploy:
	bash infra/deploy/deploy.sh

## Show this help
help:
	@grep -E '^## ' Makefile | sed 's/## //'
