# Database Architecture & Status

**Location:** `app/db/` and `app/models/`
**Driver:** Motor (Async PyMongo)

## 1. Connection & Initialization
- **File:** `app/db/connection.py` and `app/db/init_db.py`
- **Method:** `AsyncIOMotorClient` using `MONGO_URI` from settings.
- **Indexes:** Created automatically on startup via `initialize_database()`.

## 2. Collections & Models

### `users` Collection
- **Model:** `app.models.user.User`
- **Indexes:** `email` (ASCENDING, Unique)
- **Relationships:** Referenced by `user_id` in Journeys and Reports.
- **Status:** **Working.** User creation is supported, though authentication is bypassed (hardcoded `123456789012345678901234`).

### `journeys` Collection
- **Model:** `app.models.journey.Journey`
- **Indexes:** 
  - `user_id` (ASCENDING)
  - `status` (ASCENDING)
  - `created_at` (DESCENDING)
- **Relationships:** Belongs to a User. Contains embedded `JourneyPlan` and `JourneyState`.
- **Status:** **Working.** Journeys are successfully persisted and their states updated during the active monitoring loop.

### `community_reports` Collection
- **Model:** `app.models.community.CommunityReport`
- **Indexes:**
  - `location` (GEOSPHERE) - Critical for `$near` spatial queries.
  - `created_at` (DESCENDING)
  - `is_active` (ASCENDING)
- **Status:** **Working.** Geospatial queries (`$near`) successfully return reports within a given radius.

### `chat_sessions` Collection
- **Model:** `app.models.chat.ChatSession`
- **Indexes:**
  - `user_id` (ASCENDING)
  - `updated_at` (DESCENDING)
- **Status:** Schema defined and indexed. Endpoints exist. Not integrated into frontend UI.

## 3. Repositories
Located in `app/repositories/`.
All repositories inherit from `BaseRepository` (`app/repositories/base.py`), which abstracts:
- `create()`
- `get_by_id()`
- `get_all()`
- `update()`
- `delete()`

**Current Implementation Status:** The generic repository pattern is successfully implemented and avoids repetitive MongoDB raw queries across the backend.
