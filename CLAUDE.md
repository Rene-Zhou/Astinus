# Project Development Standards

## Reference documentation

- docs/GUIDE.md
- docs/ARCHITECTURE.md
- docs/PROGRESS.md
- docs/WEB_FRONTEND_PLAN.md
- docs/SETTINGS_SYSTEM_PLAN.md
- docs/API_TYPES.ts

## Python Package Management

- **Use uv to manage project dependencies**
  - Use `uv add <package>` to add dependencies
  - Use `uv sync` to synchronize dependencies
  - Use `uv run <command>` to run project commands

## API and Interface Usage

- **Use Context7 to ensure API correctness**
  - When using third-party libraries, query the latest documentation and interfaces through Context7
  - Ensure the correct version of the library and recommended best practices are used

## Branch Management Strategy

- **Feature Development Process**
  - Before developing a new feature, create a new feature branch from the main branch
  - Branch naming convention: `feature/<feature-name>` or `fix/<bug-name>`
  - After development is complete, merge back into the main branch via a Pull Request and update progress in docs/PROGRESS.md

## Development Principles

- **Test-Driven Development (TDD)**
  - Write test cases first, then implement the functionality
  - Ensure all new features have corresponding test coverage
  - Run tests to ensure code quality

- **Frontend-Backend Separation**
  - Separate frontend and backend code to improve maintainability and scalability
  - Use RESTful APIs for frontend-backend communication

## Web Frontend Development

- **Use npm to manage frontend dependencies**
  - Frontend code is located in `src/web/`
  - Use `npm install` to install dependencies
  - Use `npm run dev` to start development server
  - Use `npm run build` to build for production

- **Frontend Tech Stack**
  - React 18 + TypeScript
  - Vite (build tool)
  - TailwindCSS (styling)
  - Zustand (state management)
  - React Router v6 (routing)

- **API Types Reference**
  - See `docs/API_TYPES.ts` for all API type definitions
  - See `docs/WEB_FRONTEND_PLAN.md` for detailed API documentation

## Project Information

- Project Type: AI-driven narrative TTRPG
- Python Version: >=3.14
- Main Dependencies:
  - Backend: LangChain (AI framework), FastAPI (API framework), SQLite, ChromaDB
  - Frontend: React, Vite, TailwindCSS, Zustand
  - Deprecated: Textual (TUI frontend - see `src/frontend/`)

## Project Prototype

This project is a refactoring of the **weave** project in `~/dev/cli-ttrpg`
