# SafeShe Frontend-Backend Mapping

This document provides a strict mapping of how the frontend UI surfaces directly map to the backend API contracts.

## High-Level Mapping

| Frontend View / Component | API Service Layer | Target FastAPI Route | Method |
|---------------------------|-------------------|----------------------|--------|
| `login/page.tsx` | `authService.login` | `/api/v1/auth/login` | POST |
| `login/page.tsx` | `authService.register` | `/api/v1/auth/register` | POST |
| `home/page.tsx` | `dashboardService.getDashboardStats` | `/api/v1/dashboard/metrics` | GET |
| `journey/page.tsx` | `journeyService.planJourney` | `/api/v1/journeys/` | POST |
| `journey/page.tsx` | `journeyService.startJourney` | `/api/v1/journeys/{id}/start` | POST |
| `journey/page.tsx` | `journeyService.cancelJourney` | `/api/v1/journeys/{id}/cancel` | POST |
| `live/page.tsx` | `liveMonitorService.getTelemetry` | `/api/v1/live/{id}` | GET |
| `live/page.tsx` | `journeyService.connectToJourneyWebSocket` | `ws://.../api/v1/ws/journey/{id}` | WS |
| `assistant/page.tsx` | `assistantService.sendMessage` | `/api/v1/assistant/chat` | POST |
| `community/page.tsx` | `communityService.fetchReports` | `/api/v1/community/` | GET |
| `community/page.tsx` | `communityService.submitReport` | `/api/v1/community/` | POST |
| `emergency/page.tsx` | `emergencyService.triggerSOS` | `/api/v1/emergency/sos` | POST |
| `emergency/page.tsx` | `emergencyService.cancelSOS` | `/api/v1/emergency/cancel` | POST |
| `profile/page.tsx` | `profileService.getProfile` | `/api/v1/profile/` | GET |
| `settings/page.tsx` | `settingsService.getSettings` | `/api/v1/settings/` | GET |
| `settings/page.tsx` | `healthService.checkHealth` | `/api/v1/health` | GET |

## Architectural Boundaries

The frontend strictly enforces the API Contract defined in `SAFE_SHE_API_CONTRACTS.md`.

1. **No direct database access**: The frontend never connects to MongoDB or Redis directly. It relies purely on the standard HTTP responses provided by `apiClient`.
2. **No arbitrary background workers**: All background polling (like live telemetry updates) is bound to the React component lifecycle using `react-query`'s `refetchInterval`. If a component unmounts, the polling stops to save client bandwidth.
3. **Mock Fallbacks**: The frontend contains several temporary fallback mechanisms, such as defaulting to Bangalore coordinates if Geolocation fails, or using `j_mock_active` in the live view if no journey is supplied. These represent edges where the backend logic must securely sanitize the inputs.
