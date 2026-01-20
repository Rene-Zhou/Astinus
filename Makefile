# Astinus Development Makefile

.PHONY: help install install-backend install-web test test-backend test-web lint lint-backend lint-web format format-backend format-web type-check type-check-backend type-check-web check clean run-backend run-web run-dev stop-dev dev-logs build build-backend build-web

help:
	@echo "Astinus Development Commands:"
	@echo ""
	@echo "  Installation:"
	@echo "    make install         - Install all dependencies (backend + web)"
	@echo "    make install-backend - Install backend dependencies (npm)"
	@echo "    make install-web     - Install frontend dependencies (npm)"
	@echo ""
	@echo "  Testing:"
	@echo "    make test            - Run all tests"
	@echo "    make test-backend    - Run backend tests (vitest)"
	@echo "    make test-web        - Run frontend tests (vitest)"
	@echo ""
	@echo "  Linting:"
	@echo "    make lint            - Run all linters"
	@echo "    make lint-backend    - Run backend linter (eslint)"
	@echo "    make lint-web        - Run frontend linter (eslint)"
	@echo ""
	@echo "  Formatting:"
	@echo "    make format          - Format all code"
	@echo "    make format-backend  - Format backend code (prettier)"
	@echo "    make format-web      - Format frontend code"
	@echo ""
	@echo "  Type Checking:"
	@echo "    make type-check      - Run all type checkers"
	@echo "    make type-check-backend - Run backend type checker (tsc)"
	@echo "    make type-check-web  - Run frontend type checker (tsc)"
	@echo ""
	@echo "  Build:"
	@echo "    make build           - Build all (backend + web)"
	@echo "    make build-backend   - Build backend (tsc)"
	@echo "    make build-web       - Build frontend (vite)"
	@echo ""
	@echo "  Development:"
	@echo "    make run-backend     - Run backend server (tsx watch)"
	@echo "    make run-web         - Run frontend server (vite dev)"
	@echo "    make run-dev         - Run both servers using PM2"
	@echo "    make stop-dev        - Stop all PM2 processes"
	@echo "    make dev-logs        - View PM2 logs"
	@echo ""
	@echo "  Other:"
	@echo "    make check           - Run all checks (lint + type-check + test)"
	@echo "    make clean           - Clean build artifacts and cache"

# Installation
install: install-backend install-web

install-backend:
	cd src/backend && npm install

install-web:
	cd src/web && npm install

# Testing
test: test-backend test-web

test-backend:
	cd src/backend && npm test

test-web:
	cd src/web && npm test

# Linting
lint: lint-backend lint-web

lint-backend:
	cd src/backend && npm run lint

lint-web:
	cd src/web && npm run lint

# Formatting
format: format-backend format-web

format-backend:
	cd src/backend && npm run format

format-web:
	cd src/web && npm run format 2>/dev/null || echo "No format script in web"

# Type Checking
type-check: type-check-backend type-check-web

type-check-backend:
	cd src/backend && npm run typecheck

type-check-web:
	cd src/web && npx tsc -b --noEmit

# Build
build: build-backend build-web

build-backend:
	cd src/backend && npm run build

build-web:
	cd src/web && npm run build

# Full check
check: lint type-check test
	@echo "All checks passed!"

# Clean
clean:
	rm -rf src/backend/dist src/backend/node_modules
	rm -rf src/web/dist src/web/node_modules
	rm -rf logs/*.log
	@echo "Cleaned build artifacts and cache"

# Development servers
run-backend:
	cd src/backend && npm run dev

run-web:
	cd src/web && npm run dev

run-dev:
	pm2 start pm2.config.js

stop-dev:
	pm2 stop all

dev-logs:
	pm2 logs
