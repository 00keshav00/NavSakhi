# API Endpoints Audit

## 1. Journeys API (`app/api/v1/journeys.py`)
- **Prefix:** `/api/v1/journeys`
- **Endpoints:**
  - `POST /`
    - **Purpose:** Create a new journey and initialize the AI planning phase.
    - **Request Model:** `JourneyCreate` (source, destination, transport_mode)
    - **Response Model:** `StandardResponse[JourneyResponse]`
    - **Status:** **Broken.** Triggers the `JourneyToolManager` NameError in Coordinator.
  - `POST /{journey_id}/start`
    - **Purpose:** Transition journey state to ACTIVE and start background monitoring loop.
    - **Status:** Integrated.
  - `POST /{journey_id}/cancel`
    - **Purpose:** Transition journey state to CANCELLED.
    - **Status:** Integrated.

## 2. Community API (`app/api/v1/community.py`)
- **Prefix:** `/api/v1/community`
- **Endpoints:**
  - `POST /`
    - **Purpose:** Create a new community hazard report.
    - **Request Model:** `CommunityReportCreate`
    - **Response Model:** `StandardResponse[CommunityReportResponse]`
    - **Status:** **Working.** Saves to MongoDB.
  - `GET /nearby`
    - **Purpose:** Fetch community reports within a geospatial radius.
    - **Query Params:** `lon` (float), `lat` (float), `radius` (float)
    - **Status:** **Working.** Uses `$near` operator.

## 3. Emergency API (`app/api/v1/emergency.py`)
- **Prefix:** `/api/v1/emergency`
- **Endpoints:**
  - `POST /sos`
    - **Purpose:** Trigger an emergency SOS event. Generates a session ID and dispatches notifications.
    - **Request Model:** `SOSTrigger`
    - **Response Model:** `StandardResponse[SOSResponse]`
    - **Status:** Partially Working. Triggers WebSocket session generation, but physical SMS dispatch is stubbed.

## 4. WebSockets API
- **Journey Monitor:** `ws://localhost:8000/api/v1/ws/journey/{journey_id}`
  - **Purpose:** Pushes live AI Agent safety alerts to the frontend map UI.
  - **Status:** **Working.**
- **Emergency Broadcast:** `ws://localhost:8000/api/v1/ws/emergency/{session_id}`
  - **Purpose:** Continously broadcast user's live location during an SOS event.
  - **Status:** **Working.**

## 5. Users API (`app/api/v1/users.py`)
- **Prefix:** `/api/v1/users`
- **Endpoints:**
  - `POST /` (Register)
  - `GET /me` (Get Current User)
- **Status:** Schema and Repositories working, but Frontend completely bypasses this logic by hardcoding `x-user-id` headers.

## 6. Chat API (`app/api/v1/chat.py`)
- **Prefix:** `/api/v1/chat`
- **Endpoints:**
  - `POST /{session_id}/messages`
- **Status:** Not integrated into Frontend.

## 7. Debug API (`app/api/v1/debug.py`)
- **Prefix:** `/api/v1/debug`
- **Endpoints:** Various raw provider tests (Routing, Location, ML).
- **Status:** Used internally for validation.
