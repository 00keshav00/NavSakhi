# SafeShe Component Tree

This document outlines the hierarchy and relationship of all React components within `frontend/src/components`.

## Tree Structure

```text
frontend/src/components/
├── theme-provider.tsx (Provider for Next-Themes)
├── providers/
│   └── query-provider.tsx (Provider for React Query)
├── layout/
│   └── Sidebar.tsx (Primary Global Navigation)
├── map/
│   └── SafeMap.tsx (Core Mapbox/MapLibre renderer)
├── agent/
│   ├── AgentPanel.tsx (Full-page chat interface)
│   └── FloatingAssistant.tsx (Global floating chat widget)
├── journey/
│   ├── JourneyForm.tsx (Routing input controls)
│   └── LiveStatusPanel.tsx (HUD for active journeys)
├── cards/
│   └── MetricCard.tsx (Reusable stat display)
└── ui/ (Shadcn/Radix Primitives)
    ├── badge.tsx
    ├── button.tsx
    ├── card.tsx
    ├── dialog.tsx
    ├── input.tsx
    ├── progress.tsx
    ├── scroll-area.tsx
    ├── select.tsx
    ├── separator.tsx
    ├── skeleton.tsx
    ├── switch.tsx
    └── textarea.tsx
```

## Composition Logic

The application uses a strict component composition hierarchy:

### 1. Primitives Layer (`components/ui/`)
At the lowest level, all user interface elements rely on the Shadcn/Radix primitives defined in the `ui` folder. These components are completely stateless and exist solely to provide accessible, styled building blocks. They depend heavily on `class-variance-authority` and `lib/utils.ts` for Tailwind CSS class merging.

### 2. Specialized Layer (`components/cards/`, `components/journey/`)
These are mid-level components. For example, `MetricCard` composes the primitive `Card` to create a domain-specific visual element used in the Dashboard.

### 3. Feature Layer (`components/agent/`, `components/map/`)
These are high-level, domain-heavy components.
- `SafeMap.tsx` connects directly to external APIs (Mapbox) and uses HTML5 Geolocation. It is embedded into page-level views.
- `AgentPanel.tsx` encapsulates React Query hooks (`useAssistant`) and manages its own complex internal state (chat history).

### 4. Global Layer (`components/layout/`, `components/providers/`)
These components sit at the very top of the React tree.
- `query-provider` and `theme-provider` wrap the root `layout.tsx`.
- `Sidebar.tsx` and `FloatingAssistant.tsx` sit in the `(workspace)/layout.tsx`, meaning they are persistently mounted and never unmount during workspace navigation, ensuring global state (like active chat threads or the SOS trigger) remains intact.
