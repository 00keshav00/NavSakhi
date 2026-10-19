# Backend Architecture & File Index

This document maps the primary backend service layer.

## `app/services/`
The service layer contains all core business logic and database interactions.

### `journey_service.py`
- **Class:** `JourneyService`
- **Purpose:** Manages the CRUD and lifecycle of a user's journey.
- **Functions:**
  - `create_journey()`: Inserts journey to DB and triggers `initialize_journey`.
  - `initialize_journey()`: Invokes the `JourneyIntelligenceCoordinator` to plan the route.
  - `start_journey()`: Transitions state to ACTIVE and spawns `_active_monitor_loop` as an asyncio background task.
  - `cancel_journey()`: Halts monitoring.

### `community_service.py`
- **Class:** `CommunityService`
- **Purpose:** Handles hazard reports.
- **Functions:**
  - `create_report()`: Inserts report to MongoDB.
  - `get_nearby_reports()`: Executes `$near` geospatial query on MongoDB.

### `emergency_service.py`
- **Class:** `EmergencyService`
- **Purpose:** Handles SOS triggers.
- **Functions:**
  - `trigger_sos()`: Creates an emergency session ID and initiates notifications.

## `app/ml/models.py`
- **Class:** `XGBoostSafetyModel`
- **Purpose:** Placeholder ML implementation. Contains `predict()` function that accepts 4 features (time, weather, crowd, police) and returns a heuristic safety score. Marked with `[ML MODEL BOUNDARY]`.
