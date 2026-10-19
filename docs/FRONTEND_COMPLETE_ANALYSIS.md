# SafeShe Frontend Complete Analysis

This document provides a complete file-by-file audit of the frontend source code.

------------------------------------------------
# File
frontend/src/store/authStore.ts
------------------------------------------------
Purpose
Global state management for user authentication sessions and JWT token storage.
------------------------------------------------
File Type
Store (Zustand)
------------------------------------------------
Imports
Internal Imports: `User` (from `../types/auth`)
External Libraries: `create` (zustand), `persist` (zustand/middleware)
------------------------------------------------
Exports
`useAuthStore`
------------------------------------------------
State
- `user`: User | null (Initial: null). Purpose: Stores the authenticated user profile.
- `accessToken`: string | null (Initial: null). Purpose: Stores the JWT used for API requests.
- `isAuthenticated`: boolean (Initial: false). Purpose: Boolean flag indicating if a valid session exists.
------------------------------------------------
Hooks Used
N/A
------------------------------------------------
Stores
Store Name: `safeshe-auth-storage`
Write Actions:
- `login(user, token)`: Sets user, token, and isAuthenticated to true.
- `logout()`: Clears all state to null/false.
------------------------------------------------
Business Logic
Utilizes Zustand's `persist` middleware to automatically synchronize the auth state into the browser's `localStorage` under the key `safeshe-auth-storage`. This allows the session to survive browser reloads.
------------------------------------------------
Used By
`middleware.ts`, `api/client.ts`, `hooks/useLogin.ts`, `components/layout/Sidebar.tsx`

------------------------------------------------
# File
frontend/src/store/emergencyStore.ts
------------------------------------------------
Purpose
Global state management for the Emergency SOS trigger to ensure it persists across different routes (Dashboard vs Journey Map).
------------------------------------------------
File Type
Store (Zustand)
------------------------------------------------
Imports
External Libraries: `create` (zustand)
------------------------------------------------
Exports
`useEmergencyStore`
------------------------------------------------
State
- `isSOSActive`: boolean (Initial: false). Purpose: Tracks if the emergency broadcast is actively running.
------------------------------------------------
Stores
Write Actions:
- `triggerSOS()`: Sets `isSOSActive` to true.
- `cancelSOS()`: Sets `isSOSActive` to false.
------------------------------------------------
Used By
`hooks/useEmergency.ts`, `components/agent/AgentPanel.tsx`, `app/(workspace)/emergency/page.tsx`

------------------------------------------------
# File
frontend/src/api/client.ts
------------------------------------------------
Purpose
Configures the base Axios HTTP client for all backend communication, including global timeout rules and JWT injection.
------------------------------------------------
File Type
API Configuration
------------------------------------------------
Imports
External Libraries: `axios`
------------------------------------------------
Exports
`apiClient`, `StandardResponse` (Interface)
------------------------------------------------
API Calls
N/A (This configures the client used by other services).
------------------------------------------------
Business Logic
1. Creates an Axios instance (`apiClient`) with a `baseURL` mapping to `NEXT_PUBLIC_API_URL` or `localhost:8000`.
2. Registers a **Request Interceptor**: intercepts every outgoing HTTP request, reads `safeshe-auth-storage` directly from `localStorage` to avoid circular dependencies with Zustand, and injects the `Bearer` token into the `Authorization` header. It also implements a fallback dummy user-id if no token is found (for Phase 1 development).
3. Registers a **Response Interceptor**: catches all API errors globally. If a `401 Unauthorized` is detected, it logs a warning (planned for future token refresh logic).
------------------------------------------------
Used By
Every file in `frontend/src/api/services/*.ts`

------------------------------------------------
# File
frontend/src/components/map/SafeMap.tsx
------------------------------------------------
Purpose
The core Mapbox / MapLibre GL component responsible for rendering route geometry, user location, and community incident reports on an interactive map layer.
------------------------------------------------
File Type
Client Component
------------------------------------------------
Imports
Internal Imports: `CommunityReportResponse` (from `@/api/services/communityService`)
External Libraries: `useState`, `useEffect` (React), `Map`, `Marker`, `NavigationControl`, `Source`, `Layer` (react-map-gl/maplibre), `maplibre-gl/dist/maplibre-gl.css`, `MapPin`, `Navigation`, `AlertTriangle` (lucide-react)
------------------------------------------------
Exports
`default function SafeMap`
------------------------------------------------
Props
- `source`: Location | null (Optional) - Starting point.
- `destination`: Location | null (Optional) - Ending point.
- `routeGeometry`: any | null (Optional) - GeoJSON of the active route path.
- `reports`: CommunityReportResponse[] | null (Optional) - Array of community incident reports to plot.
- `onLocationDetected`: function (Optional) - Callback triggered when browser GPS locks.
------------------------------------------------
State
- `viewState`: Object (Initial: Bangalore coords, zoom 12). Purpose: Tracks map viewport pan/zoom.
- `userLocation`: Object | null (Initial: null). Purpose: Stores the browser's live GPS coordinates.
------------------------------------------------
Effects
- `useEffect` (deps: []): Requests HTML5 Geolocation API on mount. If granted, updates `userLocation`, triggers `onLocationDetected`, and pans the camera to the user. Fallback to Bangalore on denial.
------------------------------------------------
Render Flow
Mount -> Request Geolocation -> Pan to Location -> Render OSM Tiles -> Plot User Marker -> Plot Destination Marker -> Plot route path via GeoJSON Source/Layer -> Plot `reports` array as AlertTriangle Markers.
------------------------------------------------
Used By
`app/(workspace)/live/page.tsx`, `app/(workspace)/journey/page.tsx`

------------------------------------------------
# File
frontend/src/app/(workspace)/live/page.tsx
------------------------------------------------
Purpose
The "Live Monitor" dashboard page. Integrates the `SafeMap`, progress indicators, live telemetry polling, and the AI Action Feed timeline during an active journey.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Imports
Internal Imports: `Button`, `ScrollArea`, `SafeMap`, `useLiveMonitor`
External Libraries: `framer-motion`, `lucide-react`, `next/link`, `react`
------------------------------------------------
Exports
`default function LiveMonitorPage`
------------------------------------------------
State
- `journeyId`: string (Initial: "j_mock_active"). Purpose: Temporary mocked ID to force UI load during Phase 5 validation.
------------------------------------------------
Hooks Used
`useState`, `useEffect`, `useLiveMonitor` (Custom hook calling React Query).
------------------------------------------------
Effects
- `useEffect` (deps: `[data?.agent_timeline]`): Automatically scrolls the `agent-timeline-scroll` div to the bottom whenever a new AI event is appended to the timeline.
------------------------------------------------
API Calls
Handled implicitly by `useLiveMonitor`.
------------------------------------------------
Business Logic
1. Invokes `useLiveMonitor` to begin polling the backend for telemetry.
2. If loading, renders `LiveMonitorSkeleton`.
3. If errored/no data, renders a fallback prompt to plan a journey.
4. If successful, splits the view into a Left Panel (AI Sidebar) and Right Panel (Map + HUD).
5. The Left Panel displays dynamic Safety Score trends, AI recommendations (via Framer Motion AnimatePresence), and a scrolling Action Feed.
6. The Right Panel renders `SafeMap` and overlays a progress bar and environment pills (Weather, Lighting, Crowd Density).
------------------------------------------------
Child Components
`LiveMonitorSkeleton`, `EnvironmentPill`, `SafeMap`, `ScrollArea`, `Button`
------------------------------------------------
Used By
Next.js App Router (`/live`)
------------------------------------------------
Potential Bugs
Hardcoded `j_mock_active` string limits dynamic journey tracking.

------------------------------------------------
# File
frontend/src/components/ui/badge.tsx
------------------------------------------------
Purpose
Provides a standardized badge primitive for displaying status labels or small text chips.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `class-variance-authority`, `lib/utils`
------------------------------------------------
Exports
`Badge`, `badgeVariants`
------------------------------------------------
Business Logic
Utilizes `class-variance-authority` (cva) to map variant props (default, secondary, destructive, outline) to Tailwind CSS utility classes.
------------------------------------------------
Dependencies
`class-variance-authority`
------------------------------------------------
Used By
Various pages and components.

------------------------------------------------
# File
frontend/src/components/ui/button.tsx
------------------------------------------------
Purpose
Standardized button primitive with variant and size mappings.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-slot`, `class-variance-authority`, `lib/utils`
------------------------------------------------
Exports
`Button`, `buttonVariants`
------------------------------------------------
Business Logic
Implements Radix UI's Slot pattern for `asChild` composition, allowing buttons to act as Next.js Links without breaking HTML semantics.
------------------------------------------------
Dependencies
`@radix-ui/react-slot`, `class-variance-authority`
------------------------------------------------
Used By
Globally across all forms, CTAs, and interactive elements.

------------------------------------------------
# File
frontend/src/components/ui/card.tsx
------------------------------------------------
Purpose
Provides composite structural elements (Card, CardHeader, CardTitle, CardContent) to build boxed UI panels.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `lib/utils`
------------------------------------------------
Exports
`Card`, `CardHeader`, `CardFooter`, `CardTitle`, `CardDescription`, `CardContent`
------------------------------------------------
Business Logic
Simple wrapper components applying standard Tailwind border, radius, and background classes (e.g., `bg-card`, `text-card-foreground`).
------------------------------------------------
Used By
`DashboardView`, `LiveStatusPanel`, `MetricCard`

------------------------------------------------
# File
frontend/src/components/ui/dialog.tsx
------------------------------------------------
Purpose
Accessible modal dialog primitive based on Radix UI.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-dialog`, `lucide-react`, `lib/utils`
------------------------------------------------
Exports
`Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, etc.
------------------------------------------------
Business Logic
Provides accessible focus-trapping, escape-key closing, and portal-rendering for modals.
------------------------------------------------
Used By
`ReportAnomalyModal`, `JourneyPage` (Route Details)

------------------------------------------------
# File
frontend/src/components/ui/input.tsx
------------------------------------------------
Purpose
Standardized HTML input field.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `lib/utils`
------------------------------------------------
Exports
`Input`
------------------------------------------------
Business Logic
Wraps `input` with consistent Tailwind focus rings (`focus-visible:ring-primary`), background styling, and disabled states.
------------------------------------------------
Used By
`JourneyPage`, `JourneyForm`

------------------------------------------------
# File
frontend/src/components/ui/progress.tsx
------------------------------------------------
Purpose
Accessible progress bar primitive.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-progress`, `lib/utils`
------------------------------------------------
Exports
`Progress`
------------------------------------------------
Business Logic
Maps a `value` (0-100) to an internal transform translation (`translateX`) using Radix UI.
------------------------------------------------
Used By
`JourneyMonitor`, `Dashboard`

------------------------------------------------
# File
frontend/src/components/ui/scroll-area.tsx
------------------------------------------------
Purpose
Custom scrollbar primitive masking default browser scrollbars with a sleek, animated thumb.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-scroll-area`, `lib/utils`
------------------------------------------------
Exports
`ScrollArea`, `ScrollBar`
------------------------------------------------
Business Logic
Uses Radix UI to overlay a custom absolute-positioned scrollbar thumb.
------------------------------------------------
Used By
`Sidebar`, `JourneyPage`

------------------------------------------------
# File
frontend/src/components/ui/select.tsx
------------------------------------------------
Purpose
Accessible dropdown select primitive.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-select`, `lucide-react`, `lib/utils`
------------------------------------------------
Exports
`Select`, `SelectGroup`, `SelectValue`, `SelectTrigger`, `SelectContent`, `SelectItem`
------------------------------------------------
Business Logic
Manages complex z-indexing and viewport collision detection for dropdown menus.
------------------------------------------------
Used By
`SettingsPage`, `CommunityView`

------------------------------------------------
# File
frontend/src/components/ui/separator.tsx
------------------------------------------------
Purpose
Visual divider primitive (hr).
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-separator`, `lib/utils`
------------------------------------------------
Exports
`Separator`
------------------------------------------------
Business Logic
Applies `bg-border` to either horizontal or vertical orientations.
------------------------------------------------
Used By
`Sidebar`, `JourneyForm`

------------------------------------------------
# File
frontend/src/components/ui/skeleton.tsx
------------------------------------------------
Purpose
Loading state placeholder primitive.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `lib/utils`
------------------------------------------------
Exports
`Skeleton`
------------------------------------------------
Business Logic
Applies `animate-pulse` and `bg-muted` to block elements.
------------------------------------------------
Used By
`LiveMonitorSkeleton`, `Dashboard`

------------------------------------------------
# File
frontend/src/components/ui/switch.tsx
------------------------------------------------
Purpose
Accessible boolean toggle primitive.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `@radix-ui/react-switch`, `lib/utils`
------------------------------------------------
Exports
`Switch`
------------------------------------------------
Business Logic
Translates a thumb circle along the X-axis based on boolean state.
------------------------------------------------
Used By
`JourneyForm`, `SettingsPage`

------------------------------------------------
# File
frontend/src/components/ui/textarea.tsx
------------------------------------------------
Purpose
Standardized multi-line input field.
------------------------------------------------
File Type
Client Component / UI Primitive
------------------------------------------------
Imports
External Libraries: `react`, `lib/utils`
------------------------------------------------
Exports
`Textarea`
------------------------------------------------
Business Logic
Similar to `Input`, providing focus rings and disabled states for `<textarea>`.
------------------------------------------------
Used By
`CommunityView` (Incident Description)

------------------------------------------------
# File
frontend/package.json
------------------------------------------------
Purpose
Defines all Node.js project dependencies, scripts, and build tools.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Contains core dependencies: Next.js 15, React 19, Tailwind CSS, Zustand, React Query, Mapbox-GL (maplibre-gl), Framer Motion, Axios.
------------------------------------------------
Used By
Node package manager (npm).

------------------------------------------------
# File
frontend/next.config.ts
------------------------------------------------
Purpose
Next.js server and build configuration.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Configures strict mode and standard compiler settings for the Next.js build pipeline.
------------------------------------------------
Used By
Next.js compiler.

------------------------------------------------
# File
frontend/tsconfig.json
------------------------------------------------
Purpose
TypeScript compiler configuration.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Defines JSX handling (`preserve`), absolute import paths (`@/*`), and strict type checking rules.
------------------------------------------------
Used By
TypeScript compiler (tsc).

------------------------------------------------
# File
frontend/components.json
------------------------------------------------
Purpose
Configuration for the Shadcn UI CLI.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Maps utility files (`lib/utils.ts`) and CSS variables, allowing seamless addition of new UI components via `npx shadcn-ui`.
------------------------------------------------
Used By
Shadcn CLI.

------------------------------------------------
# File
frontend/postcss.config.mjs
------------------------------------------------
Purpose
Configures PostCSS transformations.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Includes plugins for `tailwindcss` and `autoprefixer`.
------------------------------------------------
Used By
PostCSS build pipeline.

------------------------------------------------
# File
frontend/eslint.config.mjs
------------------------------------------------
Purpose
Defines standard linting rules.
------------------------------------------------
File Type
Config
------------------------------------------------
Business Logic
Extends Next.js core web vitals and React recommended configurations.
------------------------------------------------
Used By
ESLint.

------------------------------------------------
# File
frontend/src/middleware.ts
------------------------------------------------
Purpose
Next.js Edge Middleware for route protection and session validation.
------------------------------------------------
File Type
Middleware
------------------------------------------------
Business Logic
Intercepts every request. Reads the `safeshe_token` from cookies. 
If no token is found and the user requests a workspace route (e.g., `/home`), they are redirected to `/login`.
If a token is found and the user requests `/login` or `/`, they are redirected to `/home`.
------------------------------------------------
Used By
Next.js Edge runtime.

------------------------------------------------
# File
frontend/src/lib/utils.ts
------------------------------------------------
Purpose
Provides standard utility functions across the application.
------------------------------------------------
File Type
Utility
------------------------------------------------
Business Logic
Contains `cn()` function which merges Tailwind CSS classes using `clsx` and `tailwind-merge`, avoiding conflicting utility classes.
------------------------------------------------
Used By
Almost every UI component in the application.

------------------------------------------------
# File
frontend/src/components/providers/query-provider.tsx
------------------------------------------------
Purpose
Wraps the application in a React Query client context.
------------------------------------------------
File Type
Client Component / Provider
------------------------------------------------
Business Logic
Initializes a new `QueryClient` instance and provides it to the React tree via `QueryClientProvider`, enabling global data fetching, caching, and polling (e.g. `useLiveMonitor`).
------------------------------------------------
Used By
`app/layout.tsx`

------------------------------------------------
# File
frontend/src/components/theme-provider.tsx
------------------------------------------------
Purpose
Provides dynamic Light/Dark mode toggling.
------------------------------------------------
File Type
Client Component / Provider
------------------------------------------------
Business Logic
Uses `next-themes` to inject the `dark` class into the `<html>` element based on user preference or system default.
------------------------------------------------
Used By
`app/layout.tsx`

------------------------------------------------
# File
frontend/src/api/services/assistantService.ts
------------------------------------------------
Purpose
Handles interactions with the conversational AI Assistant endpoints.
------------------------------------------------
File Type
API Service
------------------------------------------------
Imports
Internal Imports: `apiClient`, `StandardResponse`
------------------------------------------------
Business Logic
Provides the `sendMessage` function that posts to `/api/v1/assistant/chat`, and a context initializer `initializeContext`.
------------------------------------------------
Used By
`useAssistant.ts`

------------------------------------------------
# File
frontend/src/api/services/authService.ts
------------------------------------------------
Purpose
Handles user authentication endpoints (login, register).
------------------------------------------------
File Type
API Service
------------------------------------------------
Imports
Internal Imports: `apiClient`, `StandardResponse`
------------------------------------------------
Business Logic
Provides `login` and `register` functions calling `/api/v1/auth/`. Parses the JWT and saves it to Zustand's authStore upon success.
------------------------------------------------
Used By
`useLogin.ts`

------------------------------------------------
# File
frontend/src/api/services/communityService.ts
------------------------------------------------
Purpose
Handles community incident reporting and anomaly fetching.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes methods like `fetchReports()`, `submitReport()`, and `upvoteReport()`.
------------------------------------------------
Used By
`useCommunity.ts`

------------------------------------------------
# File
frontend/src/api/services/dashboardService.ts
------------------------------------------------
Purpose
Fetches unified dashboard analytics and user activity feeds.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `getDashboardStats()` calling `/api/v1/dashboard/metrics`.
------------------------------------------------
Used By
`useDashboard.ts`

------------------------------------------------
# File
frontend/src/api/services/emergencyService.ts
------------------------------------------------
Purpose
Handles dispatching high-priority SOS alerts to the backend.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `triggerSOS()` and `cancelSOS()`. Connects directly to the backend's emergency dispatch subsystem.
------------------------------------------------
Used By
`useEmergency.ts`

------------------------------------------------
# File
frontend/src/api/services/healthService.ts
------------------------------------------------
Purpose
Provides basic API connectivity checks.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `checkHealth()` to ping `/api/v1/health`.
------------------------------------------------
Used By
`useHealth.ts`

------------------------------------------------
# File
frontend/src/api/services/liveMonitorService.ts
------------------------------------------------
Purpose
Fetches live telemetry for active journeys.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `getTelemetry(journeyId)`. This is typically polled via React Query in `useLiveMonitor`.
------------------------------------------------
Used By
`useLiveMonitor.ts`

------------------------------------------------
# File
frontend/src/api/services/profileService.ts
------------------------------------------------
Purpose
Handles reading and updating user profile data.
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `getProfile()` and `updateProfile()`.
------------------------------------------------
Used By
`useProfile.ts`

------------------------------------------------
# File
frontend/src/api/services/settingsService.ts
------------------------------------------------
Purpose
Handles reading and updating user application settings (e.g., privacy, notifications).
------------------------------------------------
File Type
API Service
------------------------------------------------
Business Logic
Exposes `getSettings()` and `updateSettings()`.
------------------------------------------------
Used By
`useSettings.ts`

------------------------------------------------
# File
frontend/src/types/assistant.ts
------------------------------------------------
Purpose
Type definitions for Assistant payload structures.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `AssistantMessage`, `ChatContext`.

------------------------------------------------
# File
frontend/src/types/auth.ts
------------------------------------------------
Purpose
Type definitions for Authentication models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `User`, `LoginCredentials`, `AuthResponse`.

------------------------------------------------
# File
frontend/src/types/community.ts
------------------------------------------------
Purpose
Type definitions for Community Incident models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `IncidentReport`, `ReportSeverity`, `VerificationStatus`.

------------------------------------------------
# File
frontend/src/types/dashboard.ts
------------------------------------------------
Purpose
Type definitions for Dashboard Analytics models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `DashboardMetrics`, `ActivityFeedItem`.

------------------------------------------------
# File
frontend/src/types/emergency.ts
------------------------------------------------
Purpose
Type definitions for Emergency SOS models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `SOSPayload`, `EmergencyContact`.

------------------------------------------------
# File
frontend/src/types/liveMonitor.ts
------------------------------------------------
Purpose
Type definitions for Live Telemetry models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `TelemetryUpdate`, `LiveAgentAction`.

------------------------------------------------
# File
frontend/src/types/profile.ts
------------------------------------------------
Purpose
Type definitions for User Profile models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `UserProfile`, `ProfileUpdatePayload`.

------------------------------------------------
# File
frontend/src/types/settings.ts
------------------------------------------------
Purpose
Type definitions for Application Settings models.
------------------------------------------------
File Type
Type Definition
------------------------------------------------
Business Logic
Interfaces: `UserSettings`, `PrivacyPreferences`.

------------------------------------------------
# File
frontend/src/hooks/useAssistant.ts
------------------------------------------------
Purpose
Provides React Query state management for sending and receiving Assistant chat messages.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Wraps `assistantService.sendMessage`. Manages optimistic UI updates for chat history.
------------------------------------------------
Used By
`app/(workspace)/assistant/page.tsx`, `components/agent/FloatingAssistant.tsx`

------------------------------------------------
# File
frontend/src/hooks/useCommunity.ts
------------------------------------------------
Purpose
Fetches community anomaly reports using React Query.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Wraps `communityService.fetchReports` with auto-refetching intervals (e.g. 60s) for live map updates.
------------------------------------------------
Used By
`app/(workspace)/community/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useDashboard.ts
------------------------------------------------
Purpose
Fetches unified dashboard analytics metrics.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Wraps `dashboardService.getDashboardStats()`. Caches the dashboard view.
------------------------------------------------
Used By
`app/(workspace)/home/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useEmergency.ts
------------------------------------------------
Purpose
Handles API state for SOS triggering and interfaces with the Zustand `emergencyStore`.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
When `triggerSOS` is called, it fires the API via `emergencyService` and simultaneously toggles the global Zustand state `isSOSActive = true`.
------------------------------------------------
Used By
`app/(workspace)/emergency/page.tsx`, `Sidebar.tsx`

------------------------------------------------
# File
frontend/src/hooks/useHealth.ts
------------------------------------------------
Purpose
Simple polling hook to check backend connectivity.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Polls `/api/v1/health` to render system status indicators in the Settings panel.
------------------------------------------------
Used By
`app/(workspace)/settings/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useLiveMonitor.ts
------------------------------------------------
Purpose
Polls the backend for live telemetry updates and AI Agent Timeline actions during an active journey.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Uses `react-query` with a `refetchInterval` of 2000ms to constantly fetch `/api/v1/live/{journeyId}`. Returns structured telemetry for mapping.
------------------------------------------------
Used By
`app/(workspace)/live/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useLogin.ts
------------------------------------------------
Purpose
Handles authentication form state and token persistence.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
Posts to `authService.login`. On success, writes the JWT to `useAuthStore` and redirects to `/home`.
------------------------------------------------
Used By
`app/login/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useProfile.ts
------------------------------------------------
Purpose
Fetches and mutates user profile details.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
React Query bindings for profile CRUD operations.
------------------------------------------------
Used By
`app/(workspace)/profile/page.tsx`

------------------------------------------------
# File
frontend/src/hooks/useSettings.ts
------------------------------------------------
Purpose
Fetches user application preferences.
------------------------------------------------
File Type
Custom Hook
------------------------------------------------
Business Logic
React Query bindings for updating notification and privacy toggles.
------------------------------------------------
Used By
`app/(workspace)/settings/page.tsx`

------------------------------------------------
# File
frontend/src/components/agent/AgentPanel.tsx
------------------------------------------------
Purpose
Renders a persistent chat interface for the SafeShe Intelligent Agent.
------------------------------------------------
File Type
Client Component
------------------------------------------------
Business Logic
Maintains a local `messages` state arrays. Interacts with `useAssistant` to stream responses. Used within the dedicated Assistant workspace page.
------------------------------------------------
Used By
`app/(workspace)/assistant/page.tsx`

------------------------------------------------
# File
frontend/src/components/agent/FloatingAssistant.tsx
------------------------------------------------
Purpose
Provides a globally accessible "Chat Head" floating widget for immediate AI queries.
------------------------------------------------
File Type
Client Component
------------------------------------------------
Business Logic
Uses `framer-motion` for drag and drop capabilities (`drag="y"`, `dragConstraints`). Opens a mini-chat window that overlays on top of any workspace route.
------------------------------------------------
Used By
`app/(workspace)/layout.tsx`

------------------------------------------------
# File
frontend/src/components/cards/MetricCard.tsx
------------------------------------------------
Purpose
Reusable UI block for displaying a single numerical statistic (e.g., "Journeys Completed: 12").
------------------------------------------------
File Type
Client Component
------------------------------------------------
Business Logic
Takes `title`, `value`, `icon`, and `trend` props to render a glassmorphism card.
------------------------------------------------
Used By
`app/(workspace)/home/page.tsx`

------------------------------------------------
# File
frontend/src/components/journey/LiveStatusPanel.tsx
------------------------------------------------
Purpose
Provides an alternative, compact view of telemetry data.
------------------------------------------------
File Type
Client Component
------------------------------------------------
Business Logic
Displays speed, ETA, and progress metrics for the currently active route.
------------------------------------------------
Used By
Not actively used in the main `/live` route (which implements its own HUD).

------------------------------------------------
# File
frontend/src/components/layout/Sidebar.tsx
------------------------------------------------
Purpose
The primary navigation menu for the workspace environment.
------------------------------------------------
File Type
Client Component
------------------------------------------------
Business Logic
Implements an interactive resizable sidebar using `framer-motion` and mouse events (`onMouseMove`, `onMouseUp`). Persists width to `localStorage`. Renders primary nav items (Dashboard, Journey, Live, Community) and a highlighted red SOS button.
------------------------------------------------
Used By
Used By
`app/(workspace)/layout.tsx`

------------------------------------------------
# File
frontend/src/app/layout.tsx
------------------------------------------------
Purpose
Root layout component for the entire Next.js application.
------------------------------------------------
File Type
Server Component / Layout
------------------------------------------------
Business Logic
Injects global CSS, configures `next/font/google` (Inter and Plus Jakarta Sans), and wraps children with `ThemeProvider` (for Dark Mode) and `ReactQueryProvider`.
------------------------------------------------
Used By
Next.js App Router root.

------------------------------------------------
# File
frontend/src/app/page.tsx
------------------------------------------------
Purpose
Public landing page for the application.
------------------------------------------------
File Type
Server Component / Page
------------------------------------------------
Business Logic
Displays a premium, animated hero section marketing SafeShe. Contains a dynamic mesh gradient background, "Open Workspace" CTA to `/home`, and static feature cards highlighting Telemetry, Routing, and SOS features. Does not require authentication.
------------------------------------------------
Used By
Next.js App Router (`/`)

------------------------------------------------
# File
frontend/src/app/login/page.tsx
------------------------------------------------
Purpose
Authentication UI page.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Provides a form taking email and password. Invokes `useLogin` hook. Renders loading states and error toasts. If successful, redirects user. Uses Framer Motion for entrance animations.
------------------------------------------------
Used By
Next.js App Router (`/login`)

------------------------------------------------
# File
frontend/src/app/(workspace)/layout.tsx
------------------------------------------------
Purpose
Shared layout for all authenticated workspace routes.
------------------------------------------------
File Type
Server Component / Layout
------------------------------------------------
Business Logic
Wraps its children in an `h-screen overflow-hidden` container alongside the `Sidebar` and `FloatingAssistant` chat widget, ensuring these components remain mounted across workspace navigation.
------------------------------------------------
Used By
Next.js App Router (`/home`, `/journey`, `/live`, etc.)

------------------------------------------------
# File
frontend/src/app/(workspace)/home/page.tsx
------------------------------------------------
Purpose
Primary dashboard page summarizing recent activity and telemetry.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Fetches metrics via `useDashboard`. Uses `recharts` to render a timeline chart of safety scores over time. Displays quick-action buttons (Plan Journey, SOS) and recent activity logs.
------------------------------------------------
Used By
Next.js App Router (`/home`)

------------------------------------------------
# File
frontend/src/app/(workspace)/assistant/page.tsx
------------------------------------------------
Purpose
Dedicated conversational AI interface.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Renders the full-page version of the `AgentPanel`, allowing users to chat with the system to request incident summaries or context about their current routes.
------------------------------------------------
Used By
Next.js App Router (`/assistant`)

------------------------------------------------
# File
frontend/src/app/(workspace)/community/page.tsx
------------------------------------------------
Purpose
Map and list view of crowd-sourced anomaly reports.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Uses `useCommunity` to fetch reports. Displays them on a `SafeMap`. Also provides a UI to submit new anomaly reports via a modal dialog, including selecting categories (Harassment, Lighting, Accident).
------------------------------------------------
Used By
Next.js App Router (`/community`)

------------------------------------------------
# File
frontend/src/app/(workspace)/emergency/page.tsx
------------------------------------------------
Purpose
High-priority distress center.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Renders a massive red SOS button. When triggered via `useEmergency`, begins a visual countdown, activates loud UI flashing (`animate-pulse`), and immediately requests geolocation to broadcast coordinates to emergency services and contacts.
------------------------------------------------
Used By
Next.js App Router (`/emergency`)

------------------------------------------------
# File
frontend/src/app/(workspace)/profile/page.tsx
------------------------------------------------
Purpose
User profile management.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Forms to update personal information and manage emergency contacts. Connects to `useProfile`.
------------------------------------------------
Used By
Next.js App Router (`/profile`)

------------------------------------------------
# File
frontend/src/app/(workspace)/settings/page.tsx
------------------------------------------------
Purpose
Application settings and system health view.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Toggles for data sharing, location tracking, and notifications. Includes a "System Diagnostics" section powered by `useHealth` to verify backend connectivity (green/red indicators).
------------------------------------------------
Used By
Next.js App Router (`/settings`)

------------------------------------------------
# File
frontend/src/app/(workspace)/activity/page.tsx
------------------------------------------------
Purpose
Historical log of past journeys and routes taken.
------------------------------------------------
File Type
Client Component / Page
------------------------------------------------
Business Logic
Lists past journeys with associated dates, average safety scores, and routes. Primarily a read-only data grid/list.
------------------------------------------------
Used By
Next.js App Router (`/activity`)
