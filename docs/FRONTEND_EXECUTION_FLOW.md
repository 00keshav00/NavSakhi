# SafeShe Frontend Execution Flow

This document outlines the sequential execution flow of the application lifecycle from a user's perspective.

## 1. Application Initialization Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Middleware
    participant ReactContext
    participant AuthStore
    
    User->>Browser: Opens safeshe.app
    Browser->>Middleware: GET /
    Middleware-->>Browser: 200 OK (Public Route)
    Browser->>ReactContext: Mount <RootLayout>
    ReactContext->>ReactContext: Initialize ThemeProvider (Dark Mode check)
    ReactContext->>ReactContext: Initialize ReactQueryProvider
    ReactContext->>Browser: Render Landing Page UI
```

## 2. Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant AuthService
    participant Backend
    participant AuthStore
    
    User->>Browser: Clicks "Open Workspace"
    Browser->>Browser: Navigate to /login
    User->>Browser: Enters credentials & submits
    Browser->>AuthService: authService.login(email, pass)
    AuthService->>Backend: POST /api/v1/auth/login
    Backend-->>AuthService: 200 OK + { token, user }
    AuthService->>AuthStore: login(user, token)
    AuthStore->>AuthStore: Persist to localStorage
    Browser->>Browser: Redirect to /home
```

## 3. Core Journey Planner Flow

```mermaid
sequenceDiagram
    participant User
    participant JourneyPage
    participant MapComponent
    participant JourneyService
    participant Backend
    
    User->>JourneyPage: Opens /journey
    JourneyPage->>MapComponent: Mount <SafeMap>
    MapComponent->>MapComponent: Request Geolocation (HTML5)
    MapComponent-->>JourneyPage: onLocationDetected(lat, lng)
    User->>JourneyPage: Inputs destination & preferences
    User->>JourneyPage: Clicks "Ask Agent to Plan Route"
    JourneyPage->>JourneyService: planJourney()
    JourneyService->>Backend: POST /api/v1/journeys/
    Backend-->>JourneyService: 200 OK + Route Options
    JourneyPage->>JourneyPage: Update UI State (Show Results)
    JourneyPage->>MapComponent: Render GeoJSON geometry
```

## 4. Live Telemetry & SOS Flow

```mermaid
sequenceDiagram
    participant User
    participant LiveMonitor
    participant Backend (HTTP)
    participant Backend (WS)
    participant EmergencyStore
    
    User->>LiveMonitor: Clicks "Start Live Monitor"
    LiveMonitor->>Backend (HTTP): POST /api/v1/journeys/{id}/start
    LiveMonitor->>Backend (WS): Open WebSocket connection
    
    loop Every 2 seconds
        LiveMonitor->>Backend (HTTP): GET /api/v1/live/{id}
        Backend (HTTP)-->>LiveMonitor: Return Telemetry JSON
        LiveMonitor->>LiveMonitor: Update HUD & Map
    end
    
    Backend (WS)-->>LiveMonitor: Push AgentAlert ("High Risk Detected")
    LiveMonitor->>LiveMonitor: Render Framer Motion Alert Panel
    
    User->>LiveMonitor: Clicks SOS Button (or Navigates to /emergency)
    LiveMonitor->>EmergencyStore: triggerSOS()
    EmergencyStore->>Backend (HTTP): POST /api/v1/emergency/sos
```
