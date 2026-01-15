# Astinus Development Makefile

.PHONY: help install install-web test test-web lint lint-web format format-web check clean run-backend run-web run-dev stop-dev dev-logs

help:
	@echo "Astinus Development Commands:"
	@echo "  make install      - Install backend dependencies using uv"
	@echo "  make install-web  - Install frontend dependencies (cd src/web && npm install)"
	@echo "  make test         - Run backend tests (pytest)"
	@echo "  make test-web     - Run frontend tests (cd src/web && npm test)"
	@echo "  make lint         - Run backend linter (ruff)"
	@echo "  make lint-web     - Run frontend linter (eslint)"
	@echo "  make format       - Format backend code (ruff)"
	@echo "  make format-web   - Format frontend code"
	@echo "  make type-check   - Run backend type checker (mypy)"
	@echo "  make check        - Run all checks (lint + type-check + test)"
	@echo "  make clean        - Clean build artifacts and cache"
	@echo "  make run-backend  - Run backend server (uvicorn)"
	@echo "  make run-web      - Run frontend server (Vite dev)"
	@echo "  make run-dev     - Run both servers using PM2 (recommended)"
	@echo "  make stop-dev    - Stop all PM2 processes"
	@echo "  make dev-logs     - View PM2 logs"

install:
	uv sync

install-web:
	cd src/web && npm install

test:
	uv run pytest

test-web:
	cd src/web && npm test

lint:
	uv run ruff check src/ tests/

lint-web:
	cd src/web && npm run lint

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

format-web:
	cd src/web && npm run format

type-check:
	uv run mypy src/

check: lint lint-web test type-check test-web
	@echo "All checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	rm -rf src/web/dist src/web/node_modules .vite
	@echo "Cleaned build artifacts and cache"

run-backend:
	uv run uvicorn src.backend.main:app --reload

run-web:
	cd src/web && npm run dev

run-dev:
	pm2 start pm2.config.js

stop-dev:
	pm2 stop all

dev-logs:
	pm2 logs
