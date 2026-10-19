# SafeShe API Master Contract

**Version:** 1.1.0
**Phase:** 2.5 API Contract Refinement (FINAL FREEZE)
**Status:** Frozen single source of truth for Frontend, Backend, ML, and LLM development.

---

## 1. Project Communication Architecture

The SafeShe platform operates on a strict decoupled Agentic AI Architecture. The frontend is a "dumb" presentation layer that never directly handles complex external API integrations.

**CRITICAL RULE:** The frontend MUST NEVER communicate directly with external systems (MongoDB, ML Models, OpenWeather, Map Providers, etc.). It communicates strictly via the SafeShe Backend APIs.

---

## 2. Standard Backend vs AI Backend

The backend is explicitly divided into two distinct processing paradigms to maintain separation of concerns:

### Standard Backend Services (Traditional CRUD)
These modules handle standard business logic and database persistence without invoking the AI orchestrator.
- Authentication
- Community CRUD
- Profile
- Settings

### AI Agent Controlled Services
These modules are strictly orchestrated by the **Journey Intelligence Coordinator (JIC)**. The JIC dynamically calls providers, aggregates data, and leverages ML/LLM models before returning a response.
- Dashboard
- Journey
- Live Monitor
- Emergency
- AI Assistant

---

## 3. Journey Intelligence Coordinator Responsibilities

The **Journey Intelligence Coordinator (AI Agent)** is the true orchestrator of the SafeShe platform. The frontend never decides which provider to call; it only sends a request to the backend. 

The AI Agent is responsible for:
- **Understanding requests:** Parsing user intents (e.g., from the Assistant or Journey inputs).
- **Selecting providers:** Dynamically deciding which external APIs (Weather, Routing, Location) are needed for the context.
- **Orchestrating external systems:** Executing provider calls in the correct sequence.
- **Aggregating context:** Combining disparate data (weather forecasts, map data, community hazards).
- **Feature extraction:** Normalizing aggregated data into tensors for ML inference.
- **Calling the ML model:** Securing raw heuristic safety scores.
- **Calling the LLM:** Generating human-readable, contextual insights based on the ML score and raw data.
- **Producing final frontend DTOs:** Constructing the unified, singular response object expected by the frontend.

---

## 4. Application Modules

| Module | Purpose | Owner | Current Status | Future Status |
|---|---|---|---|---|
| **Authentication** | Secure entry, JWT generation | Auth Service | Mostly Implemented (Login mocked) | Full JWT/Refresh/SSO |
| **Dashboard** | Home view, aggregated safety metrics | Journey Intelligence Coordinator | Planned | Implemented |
| **Journey** | Neural routing, safety scoring | Journey Intelligence Coordinator | Implemented (w/ mock ML/LLM) | Full ML/LLM integration |
| **Live Monitor** | Active trip telemetry & WebSockets | Journey Intelligence Coordinator | Implemented (Polled backend) | Realtime Pub/Sub |
| **Community** | Crowdsourced hazard reporting | Community Service | Implemented | Validated via LLM |
| **Emergency** | SOS triggers, live tracking | Journey Intelligence Coordinator | Partially Implemented | Full SMS dispatch |
| **AI Assistant** | Interactive safety querying | Journey Intelligence Coordinator | Planned | Implemented |
| **Profile** | User management & preferences | Profile Service | Planned | Implemented |
| **Settings** | App config, emergency contacts | Settings Service | Planned | Implemented |

---

## 5. Endpoint Ownership Matrix

| Module | Owner | AI Agent | Providers | ML | LLM |
|---|---|---|---|---|---|
| **Authentication** | Auth Service | NO | NO | NO | NO |
| **Dashboard** | Journey Intelligence Coordinator | YES | Weather, Community | NO | YES |
| **Journey** | Journey Intelligence Coordinator | YES | Routing, Weather, Location, Community | YES | YES |
| **Live Monitor** | Journey Intelligence Coordinator | YES | Location, Weather, Community | YES | YES |
| **Community** | Community Service | NO | Community (DB) | NO | NO |
| **Emergency** | Journey Intelligence Coordinator | YES | Location, Notification, Community | NO | YES |
| **AI Assistant** | Journey Intelligence Coordinator | YES | All Providers Available | Optional | YES |
| **Profile** | Profile Service | NO | NO | NO | NO |
| **Settings** | Settings Service | NO | NO | NO | NO |

---

## 6. REST API Contract

### Authentication APIs
**Endpoint:** `POST /api/v1/auth/login`
- **Purpose:** Authenticate user and return JWT tokens.
- **Authentication Required:** NO
- **Owner:** Auth Service
- **Status:** Existing (Mocked in Frontend)
- **Request Flow:** Frontend -> Auth Service -> NO AI Agent -> DB -> AuthResponse
- **Request DTO:** `LoginRequest`
- **Response DTO:** `AuthResponse`

### Journey APIs
**Endpoint:** `POST /api/v1/journeys/`
- **Purpose:** Generate a safety-evaluated route plan between two coordinates.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Status:** Existing (Fails currently due to `JourneyToolManager` NameError)
- **Request Flow:** Frontend -> Backend Route -> YES AI Agent -> Routing/Weather/Location/Community Providers -> Feature Extraction -> ML -> LLM -> JourneyPlanResponse
- **Request DTO:** `JourneyCreateRequest`
- **Response DTO:** `JourneyPlanResponse`

**Endpoint:** `POST /api/v1/journeys/{journey_id}/start`
- **Purpose:** Transition journey to ACTIVE and spawn live monitoring task.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Status:** Existing
- **Request Flow:** Frontend -> Backend Route -> YES AI Agent -> WebSocket/Telemetry Engine -> JourneyStateUpdateResponse
- **Request DTO:** None
- **Response DTO:** `JourneyStateUpdateResponse`

**Endpoint:** `POST /api/v1/journeys/{journey_id}/cancel`
- **Purpose:** Halt active monitoring.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Status:** Existing
- **Request Flow:** Frontend -> Backend Route -> NO AI Agent -> DB Update -> JourneyStateUpdateResponse
- **Request DTO:** None
- **Response DTO:** `JourneyStateUpdateResponse`

### Community APIs
**Endpoint:** `POST /api/v1/community/`
- **Purpose:** Submit a new local hazard report.
- **Authentication Required:** YES
- **Owner:** Community Service
- **Status:** Existing
- **Request Flow:** Frontend -> Community Service -> NO AI Agent -> DB Insertion -> CommunityReportResponse
- **Request DTO:** `CommunityReportCreate`
- **Response DTO:** `CommunityReportResponse`

**Endpoint:** `GET /api/v1/community/nearby`
- **Purpose:** Fetch geospatial hazard reports within a radius.
- **Authentication Required:** YES
- **Owner:** Community Service
- **Status:** Existing
- **Request Flow:** Frontend -> Community Service -> NO AI Agent -> DB `$near` Query -> CommunityReportListResponse
- **Request DTO:** Query Params (`lon`, `lat`, `radius`)
- **Response DTO:** `CommunityReportListResponse`

### Emergency APIs
**Endpoint:** `POST /api/v1/emergency/sos`
- **Purpose:** Trigger immediate SOS dispatch sequence.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Status:** Existing
- **Request Flow:** Frontend -> Emergency API -> Emergency Service -> YES AI Agent -> Notification/Location/Community Providers -> LLM (Future) -> SOSResponse
- **Request DTO:** `SOSTriggerRequest`
- **Response DTO:** `SOSResponse`

### AI Assistant APIs (Planned)
**Endpoint:** `POST /api/v1/assistant/query`
- **Purpose:** Freeform conversational safety queries.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Request Flow:** Frontend -> Assistant API -> YES AI Agent -> Intent Engine -> Dynamic Provider Selection -> LLM -> AssistantResponse
- **Request DTO:** `AssistantQueryRequest`
- **Response DTO:** `AssistantResponse`

### Dashboard APIs (Planned)
**Endpoint:** `GET /api/v1/dashboard/overview`
- **Purpose:** Retrieve the aggregated holistic state for the Dashboard view.
- **Authentication Required:** YES
- **Owner:** Journey Intelligence Coordinator
- **Request Flow:** Frontend -> Dashboard API -> YES AI Agent -> Weather/Community/User Providers -> LLM Synthesis -> DashboardOverviewResponse
- **Request DTO:** None
- **Response DTO:** `DashboardOverviewResponse`

---

## 7. Request DTO Definitions

```typescript
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface JourneyCreateRequest {
  source: string; 
  destination: string;
  transport_mode: "walking" | "driving" | "transit";
}

export interface CommunityReportCreate {
  type: string; 
  location: [number, number];
  description?: string;
}

export interface SOSTriggerRequest {
  current_location: string;
  journey_id?: string;
}

export interface AssistantQueryRequest {
  message: string;
  context?: any;
}
```

---

## 8. Response DTO Definitions

```typescript
export interface StandardResponse<T> {
  status: "success" | "error";
  data: T;
  message?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email: string;
    role: string;
  };
}

export interface JourneyPlanResponse {
  journey_id: string;
  session_info: {
    created_at: string;
    status: string;
  };
  journey_information: {
    source: string;
    destination: string;
    distance: number;
    estimated_duration: number;
  };
  route_options: Array<any>; // Array of available GeoJSON lines
  recommended_route: any; // The chosen GeoJSON LineString
  weather_summary: {
    condition: string;
    temperature: number;
    hazards: string[];
  };
  community_summary: {
    reports_along_route: number;
    severity_level: string;
  };
  alerts: string[];
  safety_score: number; // 0.0 - 1.0 (Generated by ML)
  ai_recommendation: string; // Populated by LLM
}

export interface CommunityReportResponse {
  id: string;
  type: string;
  location: [number, number];
  created_at: string;
}

export interface SOSResponse {
  session_id: string;
  status: string;
}

export interface AssistantResponse {
  reply: string;
  action_suggested?: string;
  data_payload?: any;
}

export interface DashboardOverviewResponse {
  active_alerts: number;
  local_weather: any;
  nearby_hazards: any[];
  ai_status: string;
  user_metrics: any;
  safety_score: number;
}
```

---

## 9. Frontend Mapping

| Frontend Page | Custom Hook | API Service | REST Endpoint |
|---|---|---|---|
| **Login** | `useLogin()` | `authService` | `POST /api/v1/auth/login` |
| **Journey** | `useJourney()` | `journeyService` | `POST /api/v1/journeys/` |
| **Community** | `useCommunity()` | `communityService` | `GET /api/v1/community/nearby` |
| **Emergency** | `useEmergency()` | `emergencyService` | `POST /api/v1/emergency/sos` |
| **Dashboard** | `useDashboard()` | `dashboardService` | `GET /api/v1/dashboard/overview` |
| **Assistant** | `useAssistant()` | `assistantService` | `POST /api/v1/assistant/query` |

---

## 10. Provider Usage

**Journey AI Flow (`POST /journeys/`)**
1. `Routing Provider` 
2. `Weather Provider` 
3. `Location Provider` 
4. `Reports Provider` 
5. `Feature Extraction` 
6. `ML Provider` 
7. `LLM Provider` 

**Emergency AI Flow (`POST /emergency/sos`)**
1. `Location Provider` 
2. `Reports Provider` (Community Intelligence)
3. `Notification Provider` 
4. `LLM Provider` (Future text synthesis)

**Dashboard AI Flow (`GET /dashboard/overview`)**
1. `Weather Provider`
2. `Reports Provider`
3. `LLM Provider` (Synthesizes summary of local status)

**Assistant AI Flow (`POST /assistant/query`)**
1. `Intent Detection`
2. `Required Providers` (Dynamic based on intent)
3. `ML Provider` (Optional)
4. `LLM Provider`

---

## 11. WebSocket Contracts

### Journey Live Monitor
- **Endpoint:** `ws://api/v1/ws/journey/{journey_id}`
- **Direction:** Backend -> Frontend (Push)
- **Payload:** `{ status: string, safety_score: number, alerts: [string] }`

### Emergency Broadcast
- **Endpoint:** `ws://api/v1/ws/emergency/{session_id}`
- **Direction:** Bi-Directional
- **Payload:** Frontend -> `{ event: "location_update", lat: X, lon: Y }`. Backend -> `{ status: "police_dispatched", eta: "5m" }`

---

## 12. Authentication Contract

- **JWT Handling:** Handled strictly via HTTP `Authorization: Bearer <access_token>` headers injected by the Axios Interceptor (`src/api/client.ts`).
- **Storage:** Managed via Zustand `persist` (saved to localStorage).
- **Protected Routes:** Enforced via Next.js `middleware.ts`.
- **401 Handling:** Axios interceptor catches 401s, clearing AuthStore and redirecting.

---

## 13. External Systems Integrations

| External System | Purpose | Backend Provider | AI Agent Uses? | Frontend Direct Access? |
|---|---|---|---|---|
| **OSRM** | Map routing & distances | `RoutingProvider` | YES | NO |
| **OpenWeather** | Live weather context | `WeatherProvider` | YES | NO |
| **Nominatim** | Geocoding | `LocationProvider` | YES | NO |
| **MongoDB** | Persistence & Geospatial queries | `Motor / Repositories` | YES | NO |
| **ML Model** | Safety score prediction | `MLProvider / Tools` | YES | NO |
| **LLM** | Explanations & Natural language | `LLMProvider` | YES | NO |
| **Twilio (Planned)** | SMS Dispatch | `CommunicationsProvider`| YES | NO |

---

## 14. Realtime Events

| Event | Trigger | Frequency | Backend Owner | Frontend Consumer |
|---|---|---|---|---|
| **Journey Monitor** | `POST /start` | Every 5 seconds | `JourneyIntelligenceCoordinator` | `SafeMap` Component via WS |
| **Emergency Stream** | `POST /sos` | Continuous | `JourneyIntelligenceCoordinator` | Backend receives WS data |

---

## 15. Complete System Architecture Diagram

```mermaid
graph TD
    USER([USER]) --> |Interacts| FRONT[Frontend React Client]
    FRONT -->|REST / WebSocket| BACKEND[SafeShe FastAPI Backend]
    
    subgraph SafeShe Backend Core
        BACKEND --> STD[Standard Services: Auth, Community, Profile, Settings]
        BACKEND --> JIC[Journey Intelligence Coordinator]
    end
    
    subgraph Provider Layer (Orchestrated by JIC)
        JIC --> RP[Routing Provider / OSRM]
        JIC --> WP[Weather Provider / OpenWeather]
        JIC --> LP[Location Provider / Nominatim]
        JIC --> CP[Reports Provider / MongoDB]
    end
    
    subgraph Modeling Layer (Orchestrated by JIC)
        JIC --> FE[Feature Extraction]
        FE --> ML[ML Model / XGBoost]
        ML --> LLM[LLM / OpenAI]
    end
    
    LLM --> |Analyzed Output| JIC
    STD --> |Standard CRUD| FRONT
    JIC --> |Unified DTO Response| FRONT
```
