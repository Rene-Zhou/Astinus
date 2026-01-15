# STORES - State Management

**Scope:** Zustand stores for frontend global state

## OVERVIEW

Centralized state management using Zustand with Immer for immutable updates. Stores are fully typed and act as the single source of truth (SSOT) for game, settings, and UI domains. Syncs with backend via REST API and WebSocket.

## STRUCTURE

```
stores/
├── gameStore.ts       # Main game state: session, messages, dice, turns
├── settingsStore.ts   # AI configuration: providers, models, agent params
├── uiStore.ts         # Layout/View state: theme, sidebar, mobile panels
└── connectionStore.ts # WebSocket connectivity and error handling
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Game Session & Turns | `gameStore.ts` |
| AI Model Settings | `settingsStore.ts` |
| UI/Theme Preferences | `uiStore.ts` |
| WS Reconnection Logic | `connectionStore.ts` |
| Narrative History | `gameStore.ts` |

## PATTERNS

- **Zustand + Immer**: Use `immer` middleware for deep state updates
- **Action Pattern**: Actions bundled within stores for encapsulation
- **Backend Sync**: REST for static data, WebSocket for streaming/phases
- **Type Safety**: Interface-driven development using shared API types

## GAME PHASE SYNC

`GamePhase` from backend directly controls UI interactivity:
- `narrating`: Blocks player input; enables typewriter streaming
- `dice_check`: Forces dice tray overlay; blocks input/navigation
- `waiting_input`: Enables main player input area
- `processing`: Displays active Agent status/spinner

## CONVENTIONS & ANTI-PATTERNS

- **NO direct mutation**: Always wrap updates in Immer `set()`
- **NO state outside stores**: Shared data must reside in a Store, not local state
- **NO direct API calls**: Use `apiClient` or `wsClient` within store actions
- **Manual Type Sync**: Ensure interfaces match `src/web/src/api/types.ts`
