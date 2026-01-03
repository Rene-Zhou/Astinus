# Astinus Development Makefile

.PHONY: help install test lint format check clean run-backend run-frontend

help:
	@echo "Astinus Development Commands:"
	@echo "  make install    - Install dependencies using uv"
	@echo "  make test       - Run all tests with coverage"
	@echo "  make lint       - Run ruff linter"
	@echo "  make format     - Format code with ruff"
	@echo "  make check      - Run all checks (lint + type check + test)"
	@echo "  make clean      - Clean build artifacts and cache"
	@echo "  make run-backend  - Run backend server (TODO)"
	@echo "  make run-frontend - Run TUI frontend (TODO)"

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

type-check:
	uv run mypy src/

check: lint type-check test
	@echo "All checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov/
	@echo "Cleaned build artifacts and cache"

run-backend:
	@echo "Backend server not yet implemented"
	@echo "TODO: uv run uvicorn src.backend.main:app --reload"

run-frontend:
	@echo "Frontend TUI not yet implemented"
	@echo "TODO: uv run python -m src.frontend.app"
