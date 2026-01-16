# WEB - Frontend (React 19)

**Generated:** 2026-01-16
**Branch:** main
**Stack:** React 19 + Vite + TailwindCSS + Zustand (with Immer)

## OVERVIEW

Modern, responsive web interface for the Astinus TTRPG engine. Features real-time streaming narrative, interactive dice rolling, and character management. Optimized for both desktop (3-column layout) and mobile (bottom-panel interaction).

## STRUCTURE

```
src/web/src/
├── api/             # REST & WebSocket clients, Shared Types
├── components/      # UI components (See components/AGENTS.md)
├── hooks/           # Custom React hooks (logic reuse)
├── locales/         # i18n JSON bundles (cn/en)
├── pages/           # Route-level components (Game, Settings, etc.)
├── stores/          # Zustand stores with Immer (See stores/AGENTS.md)
├── utils/           # Pure helper functions (Dice logic, i18n)
└── main.tsx         # Entry point
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **App Entry** | `src/main.tsx` | Vite entry point |
| **Game UI** | `src/pages/GamePage.tsx` | Main gameplay interface |
| **API Client** | `src/api/client.ts` | Axios/Fetch wrapper |
| **Real-time** | `src/api/websocket.ts` | Game event streaming |
| **State** | `src/stores/` | Zustand + Immer management |
| **Styling** | `index.css` | Global Tailwind directives |

## CONVENTIONS

- **Styling**: **TAILWIND ONLY**. Use utility classes exclusively. Strictly **NO inline styles** or custom CSS files (except root `index.css`).
- **i18n**: Mandatory use of `useTranslation` hook for all UI text. Support `LocalizedString` objects for dynamic content.
- **State**: Centralized Zustand stores with `immer` middleware for deep state updates.
- **Strict Typing**: TypeScript is enforced across the board. Prop interfaces are required.
- **Linting**: Strict `noUnusedLocals` and `noUnusedParameters` checks enabled in `tsconfig.app.json`.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **NO src/frontend** | Deprecated TUI directory. Use `src/web` for all UI work. |
| **NO Hardcoded Strings** | Breaks i18n support. Always use translation keys. |
| **NO Inline Styles** | Prevents theme consistency and makes maintenance difficult. |
| **NO Direct State Mutation** | Breaks Zustand/React reactivity. Always use Immer `set`. |
| **NO Prop Drilling** | Use Zustand stores for shared application state. |

## COMMANDS

```bash
npm run dev          # Start Vite dev server locally
pm2 start pm2.config.js  # Orchestrate both Backend and Frontend
npm run build        # Production build (TSC + Vite)
npm run lint         # Run ESLint validation
```
