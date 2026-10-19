# SafeShe Agentic AI Architecture

This document maps the complete Agentic AI structure located under `app/agents/` and `app/intelligence/`.

## 1. Architectural Overview

The SafeShe backend utilizes a state-driven, deterministic cognitive architecture. Unlike typical autonomous agents that loop indefinitely, SafeShe agents follow a strict 10-stage `AgentLifecycle` to prevent runaway LLM execution and ensure deterministic API response times.

### Lifecycle Pipeline (`AgentLifecycle`)
Every agent execution goes through the following states in order:
1. `INITIALIZING`
2. `UNDERSTANDING_GOAL`
3. `PLANNING` (`PlanningEngine` generating an `ExecutionPlan`)
4. `SELECTING_TOOLS` (`StrategyGenerator` mapped against `global_tool_registry`)
5. `WAITING_FOR_TOOL_EXECUTION` (Execution via `ToolManager`)
6. `PROCESSING_RESULTS` (`ReasoningEngine`)
7. `REASONING`
8. `DECISION_READY`
9. `RESPONDING`
10. `COMPLETED` (or `FAILED`)

## 2. Core Components

### `BaseAgent` (`agents/base.py`)
- The foundational abstract class.
- Initializes all cognitive engines: `PlanningEngine`, `StrategyGenerator`, `ReasoningEngine`, `MemoryManager`, `ReflectionEngine`.
- Handles inter-agent communication via `CollaborationCoordinator`.
- **Mock Status**: The `execute_tools()` method is currently **stubbed**. It bypasses the real `ToolManager` and returns `{"mock_result": True}` instead of executing actual HTTP or Python tool definitions.

### `WorkflowManager` (`agents/workflow_manager.py`)
- **Purpose**: Maps user goals (e.g. `journey_plan`, `emergency`) to a specific sequence of specialized agents.
- **Workflow Mappings**:
  - `journey_plan` -> `RoutingAgent`, `WeatherAgent`, `CommunityAgent`, `TransitAgent`
  - `emergency` -> `EmergencyAgent`, `WeatherAgent`, `CommunityAgent`
  - `assistant` -> `AssistantAgent`, `WeatherAgent`, `CommunityAgent`

### `ExecutionContext` (`agents/context.py`)
- **Purpose**: Immutable data class holding the `goal`, `agent_identity`, `session_id`, `working_memory_ref`, and `available_tools`.
- Prevents state mutation during cognitive loops.

### `AgentRegistry` (`agents/registry.py`)
- **Purpose**: Dynamic class discovery. Agent classes register themselves on boot so the `WorkflowManager` can instantiate them by name without circular imports.

## 3. Subsystems (`app/intelligence/` & `app/tools/`)

### Intelligence Module
- Separated into `decision`, `emergency`, `journey`, and `response` packages.
- Contains the LLM Provider bindings (Ollama fallback) and prompt construction logic. 
- Serves as the brain for the `ReasoningEngine`.

### Tool Registry
- `app/tools/registry.py` defines standard capabilities the agent can invoke (e.g. `get_weather`, `calculate_route`).
- Since `execute_tools()` in `base.py` is stubbed, these tools are registered but not physically invoked during the current milestone.

## 4. Current Implementation Status

**Status: PARTIALLY IMPLEMENTED (MOCKED EXECUTION)**

- **Fully Implemented**: Lifecycle states, Context management, Workflow orchestration, Registry.
- **Mocked / Stubbed**: 
  - Tool Execution (`execute_tools` returns mock dictionaries).
  - Decision making (`make_decision` uses `pass`).
  - Many specialized agents (`assistant.py`, `coordinator.py`) are virtually empty files (37 bytes) containing only a `pass` statement or a class definition.
- **Conclusion**: The framework is deeply sophisticated and ready for real cognitive loops, but currently bypasses actual LLM tool-calling to ensure fast UI testing.
