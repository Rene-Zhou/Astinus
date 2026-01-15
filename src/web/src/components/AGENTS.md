# COMPONENTS - React UI

**Scope:** Frontend React components

## OVERVIEW

React + TailwindCSS ecosystem. Priority on mobile-first responsive design. All UI text managed via i18n bundles. Touch-friendly interactions with bottom-sliding panels for mobile.

## STRUCTURE

```
components/
├── ChatBox/           # Narrative flow, streaming text, typewriter effects
├── DiceRoller/        # 3D/Visual dice, roll submission, result display
├── Layout/            # Responsive app shell, sidebars, mobile navigation
├── Settings/          # Configuration panels, theme toggles
├── StatBlock/         # Dynamic character stats, attributes, health bars
└── common/            # Atomic UI components (Button, Input, Modal, etc.)
```

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Narrative/Chat | `ChatBox/` |
| Dice Mechanics | `DiceRoller/` |
| Global Layout | `Layout/` |
| Settings/Config | `Settings/` |
| Character UI | `StatBlock/` |
| Base Components| `common/` |

## CONVENTIONS

- **Mobile-First**: Design for touch (44px min targets), bottom panels
- **i18n Mandatory**: Zero hardcoded strings. Use `useTranslation()`
- **Tailwind-Only**: Use utility classes. NO custom CSS or inline styles
- **Responsive**: 3-column layout (desktop) -> bottom-panel view (mobile)
- **Typing**: Strict TypeScript interfaces for all component props
- **Accessibility**: ARIA labels, semantic HTML, keyboard support

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| NO hardcoded strings | Localization failure; breaks i18n support |
| NO inline styles | Prevents theme overrides; hard to maintain |
| NO fixed dimensions | Breaks layout on diverse screen sizes |
| NO hover-dependence | Blocks functionality on touch-only mobile devices |
| NO complex state | Keep components stateless; use Zustand stores |
