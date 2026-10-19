# SafeShe API Implementation

This document covers the structure and flow of the FastAPI routes in `app/api/v1/`.

## Architecture Overview
The API layer relies on FastAPI's Dependency Injection (`Depends`).
- **Flow**: `Router` -> `Depends(Service)` -> `Depends(Repository)` -> `Depends(Database)`
- **DTOs**: Data Transfer Objects are validated by Pydantic models in `app/schemas/`.

## Endpoint Map

### 1. Users & Authentication
- **Router**: `users.py`
- **Service**: `UserService`
- **Repository**: `UserRepository`
- **Endpoints**:
  - `POST /register`: Accepts `UserCreate` schema, hashes password, inserts to DB.
  - `POST /login`: Accepts OAuth2 or JSON credentials, returns JWT token.

### 2. Journeys & Routing
- **Router**: `journeys.py`
- **Service**: `JourneyService`
- **Coordinator**: `JourneyIntelligenceCoordinator` (Combines ML, Routing, Weather, and DB logic)
- **Endpoints**:
  - `POST /`: Plans a journey. Takes `source`, `destination`, `preferences`. Returns a `JourneyPlan` with multiple `CandidateRoute`s.
  - `POST /{id}/start`: Transitions journey state from `PLANNED` to `ACTIVE`.
  - `POST /{id}/cancel`: Transitions journey state to `CANCELLED`.
  - `GET /{id}/monitor`: HTTP fallback for telemetry.

### 3. Community (Crowdsourcing)
- **Router**: `community.py`
- **Service**: `CommunityService`
- **Endpoints**:
  - `GET /`: Fetches local anomaly reports based on a `radius` and `lat/lng`. Returns `CommunityReportResponse`.
  - `POST /`: Submits a new `CommunityReport`. Requires Auth token. Validation (`422`) enforced by Pydantic if location geometry is malformed.

### 4. Emergency & SOS
- **Router**: `emergency.py`
- **Service**: `EmergencyService`
- **Endpoints**:
  - `POST /sos`: High priority. Immediately flags `isSOSActive = True` on the user, transitions active journeys to `FAILED/EMERGENCY`, and triggers dispatch mechanisms.
  - `POST /cancel`: Stand-down sequence. Requires secondary validation (e.g., PIN) in production.

### 5. AI Assistant Chat
- **Router**: `chat.py`
- **Service**: `ChatService`
- **Endpoints**:
  - `POST /`: Accepts a natural language string. Returns an LLM-generated string response containing safety advice or routing context.

## Validation & Exceptions
- **Pydantic Validation**: Automatically returns `422 Unprocessable Entity` if request schemas (DTOs) do not match the expected typing (e.g. sending a string instead of a float array for coordinates).
- **Custom Exceptions**: Defined in `app/api/exceptions.py`. Includes `401 Unauthorized` for token issues and `404 Not Found` for missing ObjectIds.
- **Global Handlers**: Handled in `app/api/handlers.py` to standardize JSON error payloads.
