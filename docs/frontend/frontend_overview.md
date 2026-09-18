# Frontend Architecture & File Index

This document maps the primary frontend pages and React components.

## Application Pages (`frontend/src/app/`)

### `(workspace)/journey/page.tsx`
- **Purpose:** The main interface for route planning and live navigation.
- **State:** Tracks source, destination, active transport mode, and live agent alerts.
- **Hooks:** Uses `usePlanJourney` (React Query) to fetch routes.
- **Components:** Renders `SafeMap`.
- **Backend APIs:** Calls `/api/v1/journeys/` and connects to `ws://.../ws/journey/{id}`.

### `(workspace)/community/page.tsx`
- **Purpose:** Displays the crowdsourced hazard map.
- **State:** Tracks map viewport and nearby pins.
- **Components:** Renders `SafeMap` and `ReportForm`.
- **Backend APIs:** Calls `/api/v1/community/nearby`.

### `(workspace)/emergency/page.tsx`
- **Purpose:** The SOS activation screen.
- **State:** Tracks SOS countdown and active session ID.
- **Backend APIs:** Calls `/api/v1/emergency/sos` and connects to `ws://.../ws/emergency/{id}`.

## Core Components (`frontend/src/components/`)

### `map/SafeMap.tsx`
- **Purpose:** The central MapLibre wrapper component.
- **Props:** Accepts `routeData` (GeoJSON), `communityPins` (Array), and `userLocation`.
- **Dependencies:** `react-map-gl`, `maplibre-gl`.
- **Status:** **Working.** Handles dynamic repainting of GeoJSON routes based on AI Agent responses.
