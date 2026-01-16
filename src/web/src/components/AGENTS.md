# COMPONENTS - React UI

**Generated:** 2026-01-16
**Branch:** main
**Stack:** React 19 (Functional) + TailwindCSS + i18next

## OVERVIEW

This directory houses the modular UI components for the Astinus web interface. Components are organized by feature-specific folders or as shared primitives in the `common/` directory. All components are built with React 19, emphasizing a premium, responsive, and accessible TTRPG experience.

## STRUCTURE

```
src/web/src/components/
├── ChatBox/           # Narrative flow & streaming typewriter effects
├── DiceRoller/        # Visual dice rolling & result submission
├── Layout/            # Responsive shell & navigation components
├── Settings/          # Configuration cards & modal editors
├── StatBlock/         # Dynamic character attribute displays
└── common/            # Shared primitives (Button, Card, Input, etc.)
```

## CONVENTIONS

- **React 19 Hooks**: Use functional components and modern hooks (e.g., `useMemo`, `useCallback`) to ensure optimal performance.
- **Strict Props**: Define explicit TypeScript interfaces for all component props to ensure type safety.
- **Tailwind CSS ONLY**: Use utility classes exclusively for styling. Custom CSS files or `<style>` blocks are strictly prohibited.
- **i18n Integration**: Mandatory use of the `useTranslation` hook for ALL user-facing text content.
- **Mobile-First**: Prioritize touch-friendly interactions (min 44px targets) and responsive layouts for all UI elements.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **No Inline Styles** | Prevents consistent theming and complicates maintenance. |
| **No Hardcoded Text** | Blocks localization; all text must reside in i18n bundles. |
| **No Logic in Components** | Components should remain "dumb" presenters; use hooks or stores for logic. |
| **No Complex State** | Keep components stateless where possible to improve reusability and testing. |
| **No Prop Drilling** | Leverage Zustand stores or Context for deeply nested state requirements. |
