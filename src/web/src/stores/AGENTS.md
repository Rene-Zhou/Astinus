# STORES - State Management

**Scope:** Zustand stores for frontend state

## OVERVIEW

Zustand stores for global state (game, settings, chat). Immer for immutable updates.

## STRUCTURE

```
stores/
├── gameStore.ts       # Game state, turns, phase
├── settingsStore.ts   # User settings, preferences
├── chatStore.ts       # Chat history, messages
└── (other stores)
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Game state | `gameStore.ts` |
| Settings | `settingsStore.ts` |
| Chat history | `chatStore.ts` |

## PATTERNS

- **Zustand**: `create<StoreState>((set) => ({...}))`
- **Immer**: `set(produce((state) => {...}))` for nested updates
- **Types**: All stores fully typed with TypeScript

## NOTES

- Stores sync with backend via API/WebSocket
- Single source of truth for each domain
