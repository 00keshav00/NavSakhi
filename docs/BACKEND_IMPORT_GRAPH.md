# SafeShe Backend Import Graph

This document visualizes the complete dependency injection and import architecture of the backend, from the entry point down to the statistical ML models and external providers.

```mermaid
graph TD
    subgraph Entry
        Main[main.py]
        Dependencies[api/dependencies.py]
    end

    subgraph API Layer
        Router[api/v1/router.py]
        Routes[api/v1/*.py endpoints]
        WS[api/websockets/*.py]
    end

    subgraph Service Layer
        Services[services/*_service.py]
    end

    subgraph Intelligence & Agent Layer
        Workflow[agents/workflow_manager.py]
        Coordinator[intelligence/*/coordinator.py]
        AgentLifecycle[agents/lifecycle.py]
        BaseAgent[agents/base.py]
        ToolManager[tools/manager.py]
        Reasoning[agents/reasoning/engine.py]
    end

    subgraph Data Access Layer
        Repositories[repositories/*_repository.py]
        Models[models/*.py]
        Schemas[schemas/*.py]
        DB[db/connection.py]
    end

    subgraph External & ML
        ProviderRegistry[providers/registry.py]
        Providers[providers/*/*.py]
        ML[ml/predictor.py & models.py]
        Features[ml/features.py]
    end

    %% Wiring
    Main --> Router
    Main --> WS
    Main --> DB
    
    Router --> Routes
    Routes --> Dependencies
    Dependencies --> Services
    Dependencies --> Repositories
    Dependencies --> Coordinator
    Dependencies --> ProviderRegistry
    
    Services --> Repositories
    Services --> Coordinator
    
    Repositories --> Models
    Repositories --> DB
    Routes --> Schemas
    Services --> Schemas

    Coordinator --> Workflow
    Workflow --> AgentLifecycle
    AgentLifecycle --> BaseAgent
    
    BaseAgent --> ToolManager
    BaseAgent --> Reasoning
    
    ToolManager --> ProviderRegistry
    Reasoning --> LLM[providers/llm_provider.py]
    
    ProviderRegistry --> Providers
    Providers --> Features
    Features --> ML
    
    %% Styling
    classDef layer fill:#2d3436,stroke:#74b9ff,stroke-width:2px,color:#dfe6e9;
    classDef entry fill:#0984e3,stroke:#74b9ff,stroke-width:2px,color:#fff;
    classDef db fill:#00b894,stroke:#55efc4,stroke-width:2px,color:#fff;
    classDef ai fill:#6c5ce7,stroke:#a29bfe,stroke-width:2px,color:#fff;
    
    class Main,Dependencies entry;
    class DB,Models,Repositories db;
    class Coordinator,Workflow,AgentLifecycle,BaseAgent,Reasoning,ToolManager ai;
```
