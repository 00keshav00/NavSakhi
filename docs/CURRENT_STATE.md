# SafeShe: Current State & Architectural Audit
**Generated:** Phase 1 of Codebase Audit

---

## 1. Executive Summary

**Project Purpose:** SafeShe is a personal safety and intelligent journey orchestration platform designed to route users securely, monitor them dynamically via AI, and trigger emergency responses when necessary.

**Current Status:** Development is halted. The project sits in a structurally complete but partially integrated state, functioning largely through simulated layers (stubs/mocked providers) rather than production-ready AI or third-party connections.

**Architecture Style:** Decoupled Microservice-like Monolith. Frontend (Next.js), Backend (FastAPI), Intelligence Layer (Agentic AI), and Provider Layer (External Interfaces) operate independently, communicating via APIs, WebSockets, and defined schema interfaces.

**Technology Stack:**
- **Frontend:** React, Next.js 16.2.12 (Turbopack), Tailwind CSS, Framer Motion, MapLibre GL JS.
- **Backend:** Python, FastAPI, Uvicorn, Pydantic, Motor (Async MongoDB).
- **Intelligence/Agent:** Custom Coordinator pattern, asynchronous task delegation, pipeline architecture.
- **Data Store:** MongoDB (NoSQL).

**Overall Completion:** ~70%. Core plumbing is laid, but the "brains" (ML/LLM) and physical external triggers (Twilio SMS) are stubs.

**Current Readiness:** Not ready for production. Development environments can run, but core features rely on placeholder data, and there is a fatal runtime crash preventing the backend from initializing properly.

---

## 2. Repository Overview

```text
SafeShe/
├── app/                        # FastAPI Backend Application
│   ├── agents/                 # Multi-agent collaboration frameworks
│   ├── api/                    # API v1 Routers (HTTP & WebSockets)
│   ├── config/                 # Environment & Logging configuration
│   ├── db/                     # MongoDB connection & init logic
│   ├── intelligence/           # The Core AI Agent (Journey Coordinator)
│   ├── ml/                     # Machine Learning boundaries & stubs
│   ├── models/                 # Pydantic core data models
│   ├── providers/              # Abstraction layer for external services
│   ├── repositories/           # Database CRUD abstraction
│   ├── schemas/                # Request/Response validation schemas
│   ├── services/               # Business logic
│   └── tools/                  # Tool Manager & Executable Agent Tools
├── frontend/                   # Next.js Application
│   ├── src/
│   │   ├── api/                # Axios Client & Services mapped to Backend
│   │   ├── app/                # Next.js App Router Pages
│   │   ├── components/         # Reusable React components (UI, Map)
│   │   ├── hooks/              # Custom React Query hooks
│   │   ├── lib/                # Utilities
│   │   └── store/              # State management
├── tests/                      # Testing directory (Currently empty/unverified)
└── requirements.txt            # Python dependencies
```

**Purpose of Major Folders:**
- `app/intelligence/`: Acts as the autonomous brain. It orchestrates routing, weather, community reports, and ML to make decisions.
- `app/providers/`: Prevents tight coupling. The Agent talks to a `WeatherProvider`, not OpenWeather API directly.
- `app/tools/`: The strict sandbox where the Agent executes actions.
- `frontend/src/api/`: Replicates the backend service structure identically on the client side.

---

## 3. High Level Architecture

The system operates across distinct boundaries:

1. **Frontend:** User interface, state management, and MapLibre map rendering. Communicates strictly via HTTP REST and WebSockets.
2. **Backend (Services & API):** Standard CRUD operations and session management. Passes complex tasks (like planning) to the Intelligence Layer.
3. **Journey Intelligence Layer:** The AI Agent coordinator. It plans, monitors, and reroutes.
4. **Provider Layer:** The translation layer. Converts external system data (OSRM, OpenWeather, Dummy ML) into internal formats.
5. **Database Layer:** MongoDB async driver storing users, journeys, and community reports.
6. **AI/ML Layer:** Stubbed implementation. The Coordinator delegates mathematically computing safety to the ML Layer, and explaining decisions to the LLM Layer.

**Interaction Flow:**
Frontend → REST API → Service Layer → Intelligence Coordinator → Tool Manager → Providers/ML/LLM → Return Path.

---

## 4. Architecture Comparison

### Original Intended Architecture
A fully autonomous, multi-agent AI system that continuously monitors a user's journey, computes real-time safety scores using deployed XGBoost models, streams environmental data via OpenWeather/Google APIs, and converses with the user via LLM regarding alternative safe routes.

### Current Implemented Architecture
- **Matches:** The decoupled folder structure, strict Provider layer isolation, MapLibre rendering, and Database Schema structure.
- **Partially Implemented:** The AI Agent (runs synchronously/asynchronously but relies heavily on predefined rule-sets rather than real LLM decision-making). Live monitoring WebSocket loops exist but simulate environmental triggers.
- **Broken:** The backend fails to start due to a `NameError` in the Coordinator (missing/renamed `JourneyToolManager` import).
- **Placeholder:** The ML Model (returns random/heuristic numbers based on inputs), LLM (returns hardcoded explanation strings), Weather API (returns randomized dummy weather), Emergency SMS (console logs instead of sending SMS).
- **Missing:** Full multi-agent conversation history, proper authentication tokens (currently mocked with hardcoded `x-user-id`), tests.

---

## 5. Complete Request Flow

### Journey Planning Flow
1. **Frontend:** User inputs destination → `usePlanJourney` hook called.
2. **Axios Service:** `journeyService.planJourney()` sends `POST /api/v1/journeys/`.
3. **API Router:** `app.api.v1.journeys.create_journey()` receives request.
4. **Service:** `JourneyService.create_journey()` saves to DB, then calls `initialize_journey()`.
5. **Coordinator:** `JourneyService` calls `JourneyIntelligenceCoordinator.plan_journey(context)`.
6. **Providers (via Coordinator):** Coordinator queries `RoutingProvider`, `WeatherProvider`, `CommunityProvider`.
7. **ML Layer:** Coordinator delegates candidates to `EvaluationPipeline`, which calls `SafetyPredictionTool` (ML Stub).
8. **LLM Layer:** Ranked route is passed to `AIPipelineProvider` (LLM Stub) for explanation.
9. **Response:** Route and explanation return down the stack to the UI map.

### Emergency SOS Flow
1. **Frontend:** User clicks SOS → `emergencyService.triggerSOS()` called.
2. **API Router:** `POST /api/v1/emergency/sos`.
3. **Service:** `EmergencyService.trigger_sos()` creates a session.
4. **External System (Simulated):** Service calls `NotificationProvider` to send SMS (stubbed).
5. **WebSocket:** Frontend opens `ws://localhost:8000/api/v1/ws/emergency/{id}`.
6. **Broadcast:** Frontend streams location; backend `EmergencyConnectionManager` broadcasts it to connected observers.

---

## 6. Current AI Agent

**Journey Intelligence Coordinator (`app/intelligence/journey/coordinator.py`)**
- **Purpose:** Central brain orchestrating the journey lifecycle.
- **Responsibilities:** Gathering context, generating route candidates, evaluating safety, monitoring live journeys, handling events.
- **Inputs:** `JourneyContext` (Location, Timestamp, Mode).
- **Outputs:** `JourneyPlan`, Alerts, Reroute decisions.
- **Current Orchestration:**
  - Evaluates routes via an `EvaluationPipeline`.
  - Monitors active journeys via an asynchronous `_active_monitor_loop` (invoked by `JourneyService`).
- **Current Limitations:** The active monitor loop fakes environmental events on a 5-second tick timer.
- **Future Extension Points:** The `tool_manager` property is designed to allow the Agent to dynamically choose tools (search web, call police, etc.), but currently, tools are called imperatively.

---

## 7. Provider Layer

| Provider | Purpose | Concrete Implementation | Status |
|----------|---------|-------------------------|--------|
| **Routing** | Get paths between A & B | `app/providers/routing/` | Placeholder/Mocked |
| **Location** | Geocoding | `app/providers/location/` | Placeholder/Mocked |
| **Weather** | Live environmental data | `app/providers/weather/` | Placeholder/Mocked |
| **Community** | Access DB hazard pins | `app/providers/reports/` | **Working** (Queries DB) |
| **LLM** | Explain decisions | `app/providers/ai/provider.py` | Placeholder (Returns static strings) |

*Unable to verify specific OpenWeather or Google API integration from current code, as the providers return static/simulated dataclasses.*

---

## 8. External Systems

- **MongoDB:** Integrated natively via Motor async driver. **Working.**
- **MapLibre (Frontend):** Integrated via `react-map-gl`/`maplibre-gl`. **Working.**
- **WebSockets:** FastAPI WebSockets implemented for Journey Alerts and Emergency Tracking. **Working.**
- **ML / XGBoost:** Isolated in `app/ml/models.py`. **Placeholder.** (Ready for `.predict()`).
- **SMS / Twilio:** Isolated in `NotificationProvider`. **Placeholder.**

---

## 9. Database

- **Driver:** Motor (Async PyMongo).
- **Initialization:** `app/db/init_db.py` creates collections and indexes on startup.
- **Collections:**
  - `users`: Indexed uniquely by `email`.
  - `journeys`: Indexed by `user_id`, `status`, `created_at`.
  - `community_reports`: 2dsphere index on `location` for geospatial querying.
  - `chat_sessions`: Indexed by `user_id`.
- **Status:** **Working.** CRUD operations heavily abstracted through `BaseRepository`.

---

## 10. Frontend

- **Pages:** Home, Journey, Community, Profile, Emergency.
- **Map Component:** `SafeShe Map` integrates MapLibre, renders routes as GeoJSON lines, plots community pins.
- **State:** Mostly managed locally via React `useState` and remotely via React Query `useMutation`/`useQuery`.
- **Integration Status:** Frontend API paths successfully match the backend `/api/v1/` routes. The UI successfully catches Network Errors gracefully when the backend is offline.

---

## 11. Backend

- **Configuration:** Managed via Pydantic `BaseSettings` (`app/config/settings.py`).
- **Routers:** Properly scoped and mounted in `main.py` under `/api/v1`.
- **Dependencies:** DI extensively used (`get_journey_service`, `get_current_user_id`).
- **Integration Status:** **Currently Broken** at runtime.

---

## 12. Testing
- **Status:** Missing. The `tests/` directory exists but no verifiable test suites are present for the core logic.

---

## 13. Integration Status (Feature-by-Feature)

- **Journey Planning:** Placeholder (relies on mock routing & ML).
- **Community Maps:** **Working** (Read/Write to MongoDB Geospatial index).
- **Weather:** Placeholder.
- **Emergency SOS:** Partially Working (WebSockets operational, SMS missing).
- **Live Tracking:** Partially Working (Simulated loop).
- **Authentication:** Placeholder (Hardcoded `x-user-id` everywhere).

---

## 14. Known Issues (Observed from Code)

1. **Fatal Runtime Crash:** `app/intelligence/journey/coordinator.py` references `JourneyToolManager` on line 46, which throws a `NameError` on backend startup because the class was refactored/renamed to `ToolManager`, breaking Uvicorn initialization.
2. **Authentication Bypass:** All frontend API calls hardcode `"x-user-id": "123456789012345678901234"`. Real JWT verification is not implemented.
3. **Missing Routing Engine:** `RoutingProvider` does not actually query OSRM or Google Maps; it generates static coordinate arrays.

---

## 15. Technical Debt

- **Placeholder Implementations:** Nearly the entire `app/providers/` directory consists of stubs.
- **Architectural Drift:** The Multi-Agent Collaboration framework (`app/agents/collaboration/`) exists but is entirely disconnected from the actual `JourneyIntelligenceCoordinator`, representing unused files/architectural drift.
- **Duplicate Logic:** The `JourneyContext` is defined/handled in both standard services and intelligence models, causing potential synchronization issues.

---

## 16. Project Readiness

- **Current Completion:** ~70% of structural scaffolding. ~10% of external integrations.
- **Major Blockers:** The `JourneyToolManager` NameError must be fixed before the backend can start. Real ML/LLM models must be loaded to replace the placeholders.
- **Recommended Future Work:** 
  1. Fix backend startup crash.
  2. Implement real JWT authentication.
  3. Integrate real OSRM/Routing APIs inside the `RoutingProvider`.
  4. Inject the compiled ML `.pkl` model into `SafetyPredictionTool`.
