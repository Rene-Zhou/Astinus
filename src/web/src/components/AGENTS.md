# COMPONENTS - React UI

**Scope:** Frontend React components

## OVERVIEW

React components with TailwindCSS styling. All text via i18n (never hardcode). Mobile-first responsive design.

## STRUCTURE

```
components/
├── ChatBox/           # Narrative display, streaming text
├── DiceRoller/        # Visual dice, roll submission
├── Layout/            # App shell, responsive layout
├── Settings/          # Settings panels
├── StatBlock/         # Character stats display
└── common/            # Shared UI (Button, Input, etc.)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Chat/narrative | `ChatBox/` |
| Dice UI | `DiceRoller/` |
| Main layout | `Layout/` |
| Settings UI | `Settings/` |
| Shared UI | `common/` |

## CONVENTIONS

- **NO hardcoded text**: Use `useTranslation()` from `react-i18next`
- **TailwindCSS**: All styling via utility classes
- **Mobile-first**: Touch-friendly, bottom panels
- **Components**: Functional, TypeScript, prop types

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| NO hardcoded strings | All text via i18n |
| NO inline styles | Use Tailwind classes |
