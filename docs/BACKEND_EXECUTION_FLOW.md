# SafeShe Backend Execution Flow

This document outlines the sequential execution flows for core system operations using Mermaid sequence diagrams.

## 1. Application Startup Flow

```mermaid
sequenceDiagram
    participant Uvicorn
    participant Main as main.py
    participant DB as db/init_db.py
    participant Agents as agents/registry.py

    Uvicorn->>Main: ASGI Lifespan Start
    Main->>DB: connect_to_mongo()
    DB-->>Main: Connected
    Main->>DB: initialize_database()
    Note right of DB: Creates 2dsphere & unique indexes
    DB-->>Main: Complete
    Main->>Agents: Pre-register Agent Classes
    Main-->>Uvicorn: Yield (Server Ready)
```

## 2. Standard Request Flow (e.g., Fetch Community Reports)

```mermaid
sequenceDiagram
    participant Client
    participant Router as api/v1/community.py
    participant DI as dependencies.py
    participant Service as CommunityService
    participant Repo as CommunityRepository
    participant DB as MongoDB

    Client->>Router: GET /community/?lat=...&lng=...
    Router->>DI: Depends(get_community_service)
    DI->>Repo: init(db)
    DI->>Service: init(repo)
    DI-->>Router: service instance
    
    Router->>Service: get_nearby_reports(lat, lng, radius)
    Service->>Repo: get_nearby(lat, lng, radius)
    Repo->>DB: $near geospatial query
    DB-->>Repo: BSON Documents
    Repo-->>Service: List[CommunityReport]
    Service-->>Router: List[CommunityReport]
    Router-->>Client: 200 OK (JSON)
```

## 3. Agentic Journey Planning Flow

```mermaid
sequenceDiagram
    participant Client
    participant Service as JourneyService
    participant Coord as IntelligenceCoordinator
    participant Workflow as WorkflowManager
    participant Agent as Specialized Agent (Routing/Weather)
    participant Engine as ML FeatureEngineer
    participant Provider as External API (OSRM)

    Client->>Service: create_journey_plan()
    Service->>Coord: generate_plan(source, destination)
    Coord->>Workflow: run_workflow("journey_plan")
    
    Workflow->>Agent: execute(context)
    Note right of Agent: Transitions via AgentLifecycle
    
    Agent->>Provider: fetch_data()
    Provider-->>Agent: Raw JSON
    
    Agent->>Engine: extract_features()
    Engine-->>Agent: Vector [14.0, 24.0, ...]
    
    Agent->>ML: predict(Vector)
    ML-->>Agent: Safety Score
    
    Agent-->>Workflow: Agent Results
    Workflow-->>Coord: Aggregated Context
    Coord-->>Service: JourneyPlan object
    Service-->>Client: 200 OK
```

## 4. Emergency / SOS Flow

```mermaid
sequenceDiagram
    participant User
    participant Router as api/v1/emergency.py
    participant Service as EmergencyService
    participant WS as WebSocket (Monitoring)
    participant Contacts as NotificationProvider

    User->>Router: POST /emergency/sos
    Router->>Service: activate_sos(user_id)
    Service->>DB: Update User.isSOSActive = True
    Service->>DB: Update Journey.state = FAILED
    Service->>WS: Broadcast SOS Alert to tracking sessions
    Service->>Contacts: send_sms(emergency_contacts)
    Contacts-->>Service: SMS Dispatched
    Service-->>Router: 200 OK (SOS Activated)
    Router-->>User: Emergency Mode Confirmed
```
