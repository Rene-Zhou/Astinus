# STORES - State Management

**Generated:** 2026-01-20
**Scope:** Global state management for the Astinus frontend.

## OVERVIEW

Astinus uses **Zustand** combined with the **Immer** middleware to manage application state. This combination provides a simple, boilerplate-free state management solution while ensuring immutability through a "mutable-like" syntax.

### Key Files
- `gameStore.ts`: Manages session data, messages, dice results, and game phases.
- `settingsStore.ts`: Handles AI provider configurations, agent parameters, and i18n settings.
- `uiStore.ts`: Manages layout states, theme preferences, and mobile view transitions.
- `connectionStore.ts`: Tracks WebSocket status and reconnection attempts.

## CONVENTIONS

- **Immer usage for mutable syntax**: Always use the `set((state) => { state.field = value })` pattern. Immer allows you to write code that looks like direct mutation, which it then translates into immutable updates.
- **Selector Pattern**: Always use selectors when consuming state in components (e.g., `useGameStore(state => state.messages)`) to prevent unnecessary re-renders.
- **Action Encapsulation**: Define all state-modifying logic (actions) within the store itself.
- **Async Handling**: Store actions should handle API calls and loading states (e.g., `isLoading`, `error`) to keep components clean.
- **Manual Type Sync**: State interfaces must be manually synchronized with `src/web/src/api/types.ts`.

## ANTI-PATTERNS

- **No direct mutations outside actions**: Never attempt to modify the state object directly from a component. Always call a defined action.
- **No nested `useState` for shared data**: If data is needed by more than one component or needs to persist across routes, it belongs in a Zustand store.
- **No direct API calls in components**: Data fetching logic that affects global state should reside in store actions, using `apiClient` or `wsClient`.
- **Avoid Big Stores**: Keep stores focused on specific domains (Game, Settings, UI) to maintain maintainability.

---
*Note: This file is for AI agents. Ensure any changes to store logic adhere to these principles.*
