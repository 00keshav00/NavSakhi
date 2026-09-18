# AI Agent & Intelligence Layer

**Location:** `app/intelligence/`
**Purpose:** The core decision-making orchestration layer of the SafeShe platform.

## 1. Journey Intelligence Coordinator
**File:** `app/intelligence/journey/coordinator.py`

### Responsibilities:
- **Planning:** Receives a source and destination, and generates potential routes.
- **Evaluation:** Passes generated routes to the Evaluation Pipeline to calculate safety scores based on ML heuristics.
- **Recommendation:** Ranks evaluated routes and selects the optimal path.
- **Monitoring:** Runs an asynchronous loop (`_active_monitor_loop`) that ticks every 5 seconds to simulate real-time environmental hazard checks.

### Current Status & Known Issues:
- **FATAL BUG:** Line 46 contains `self.tool_manager = tool_manager or JourneyToolManager()`. The class `JourneyToolManager` does not exist (likely renamed to `ToolManager` in `app/tools/manager.py`). This causes a `NameError` that crashes the entire backend startup sequence.
- **Limitations:** The monitoring loop relies on a hardcoded 5-second tick rather than a true event-driven pub/sub architecture.

## 2. Evaluation Pipeline
**File:** `app/intelligence/journey/evaluation/pipeline.py`

### Mechanism:
1. Gathers context for a route (Time of day, simulated weather, community reports in the vicinity).
2. Converts context into a feature array: `[time_feat, weather_feat, crowd_feat, police_feat]`.
3. Passes features to the ML Model stub via the `SafetyPredictionTool`.

## 3. Tool Manager
**Location:** `app/tools/`

### Tools Available to the Agent:
- **SafetyPredictionTool (`predictions.py`):** Bridges the gap between the Coordinator and the raw ML model. 
- **WeatherTool (`weather.py`):** Queries the `WeatherProvider`.
- **LocationTool (`location.py`):** Queries geocoding coordinates.
- **CommunityTool (`community.py`):** Queries local DB hazard reports.

### Status:
Strictly enforced boundaries. The Coordinator must execute tasks via the `ToolManager` rather than calling external APIs directly, enforcing a true Agentic sandbox. However, tools are currently called imperatively rather than chosen autonomously by an LLM loop.
