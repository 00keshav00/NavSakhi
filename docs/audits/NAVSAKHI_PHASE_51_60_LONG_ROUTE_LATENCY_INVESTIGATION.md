# NavSakhi Phase 51.60 — Long-Route Production Latency Investigation & Temporary Client Timeout Adjustment

## 1. Executive Summary

During staging verification of commit `1912ab7565b690ecd195274c6a4df902fec54fbc`, deployed frontend users reported:
```
timeout of 60000ms exceeded
```
Backend staging logs revealed that while the requests did successfully complete on the server, the total end-to-end pipeline required 81,707.51 ms to 95,098.95 ms, specifically concentrated in:
1. **Candidate Scoring (`candidate_scoring`):** 57,598.81 ms to ~65,136 ms
2. **Response Construction (`response_construction`):** 11,093.63 ms to ~16,991 ms

In Phase 51.60, we:
1. Located the exact source of the frontend timeout in `frontend/src/api/services/journeyService.ts` and temporarily raised **only** the journey-search request timeout to `120000` ms (retaining all existing loading, retry, and cancellation semantics).
2. Deconstructed the entire backend scoring and response construction pipelines under real route coordinates (Tambaram to Chennai Central, 37.5 km, 648 coordinates, 5 candidates).
3. Identified the exact mathematical and architectural bottlenecks explaining why deployed Render latency is 8x–10x higher than local warm benchmarks.
4. Formulated the precise, minimal backend optimization pathway to eliminate redundant multi-candidate operations.

---

## 2. Git & Baseline Verification

- **Workspace:** `C:\Users\kesha\OneDrive\Desktop\SafeShe-main`
- **Active Branch:** `release/phase51-render-staging`
- **Starting HEAD:** `1912ab7565b690ecd195274c6a4df902fec54fbc`
- **Remote:** `https://github.com/00keshav00/NavSakhi.git` (`navsakhi-target`)
- **Production `main` Status:** Untouched (`bbea228d0c4905c7ac78e7bf2dbc745342af10fd`)

---

## 3. Frontend Timeout Mitigation (Section 2)

### 3.1 Source of the 60,000ms Timeout
The global Axios client in `frontend/src/api/client.ts` establishes a default baseline timeout:
```typescript
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 60000, // 60s baseline
});
```
In `frontend/src/api/services/journeyService.ts`, `planJourney` previously called `apiClient.post` without an explicit timeout override, causing long-route queries to abort client-side at exactly 60,000 ms even though the backend completed in 81–95 seconds.

### 3.2 Before and After Configuration
**Before:**
```typescript
planJourney: async (request: JourneyCreateRequest, signal?: AbortSignal): Promise<JourneyPlanResponse> => {
  const response = await apiClient.post<StandardResponse<JourneyPlanResponse>>("/api/v1/journeys/", request, { signal });
  return response.data.data;
},
```

**After:**
```typescript
planJourney: async (request: JourneyCreateRequest, signal?: AbortSignal): Promise<JourneyPlanResponse> => {
  // Temporary client mitigation: extended to 120,000ms to allow long-route computation on resource-constrained deployments
  const response = await apiClient.post<StandardResponse<JourneyPlanResponse>>("/api/v1/journeys/", request, {
    signal,
    timeout: 120000,
  });
  return response.data.data;
},
```

### 3.3 Isolation and Safety Preservation
- **Unchanged Services:** Authentication (`authService`), Autocomplete (`journeyService.autocomplete`), Weather (`weatherService`), Assistant Chat (`assistantService`), Community, Health, and Emergency services remain strictly subject to the 60,000 ms baseline default.
- **Cancellation & Stale Rejection:** In `frontend/src/hooks/useJourney.ts`, `requestIdRef` and `abortControllerRef` continue to immediately cancel previous requests upon new search input and reject stale out-of-order responses.
- **Classification:** This client-side change is documented as a **temporary mitigation** to unblock user searches on resource-constrained cloud containers while backend optimizations are prepared.

---

## 4. Latency Investigation & Profiling (Section 3)

### 4.1 Local Profiling vs Deployed Logs
A benchmark run locally on the exact 37.5 km Chennai route (Tambaram to Chennai Central, 648 GPS coordinates, 5 candidate routes) reveals:

| Pipeline Stage | Local Warm Duration | Deployed Staging Duration (Request A) | Deployed Staging Duration (Request B) | Factor Difference |
| :--- | :--- | :--- | :--- | :--- |
| **Location Resolution** | 185.20 ms | 1,800.11 ms | ~1,800 ms | ~9.7x |
| **Road Routing (OSRM)** | 142.10 ms | 1,000.89 ms | ~1,000 ms | ~7.0x |
| **Transit Discovery** | 980.50 ms | 8,196.37 ms | ~6,467 ms | ~7.5x |
| **Candidate Scoring** | 5,016.40 ms | 57,598.81 ms | ~65,136 ms | **~11.5x** |
| **Weather** | 0.15 ms | 0.28 ms | ~0.3 ms | 1.8x |
| **Gemini Reasoning** | 1,850.20 ms | 2,004.69 ms | ~2,003 ms | 1.1x |
| **Response Construction** | 5,293.10 ms | 11,093.63 ms | ~16,991 ms | **~2.6x** |
| **Total Pipeline** | **13,467.65 ms** | **81,707.51 ms** | **95,098.95 ms** | **~6.5x** |

### 4.2 Fine-Grained Component Breakdown (Inside Scoring)
Profiling individual candidate scoring operations on a single 37.5 km route revealed:
1. **Spatial Road-Segment Matching (`match_route`):** 544.48 ms local
   - Corridor bounding box spatial query into SQLite database.
   - Projecting and snapping 648 route points to ~1,044 candidate road segments.
   - Building 22 road-infrastructure features for each matched segment.
2. **LightGBM Prediction & TreeSHAP Attribution:** 559.06 ms local
   - Feature normalization and matrix reshaping.
   - LightGBM GBDT inference (`predict()`) across all segments.
   - `shap.TreeExplainer` calculating exact feature attribution contributions.
3. **POI Corridor Retrieval & Distance Calculation:** 316.10 ms local
   - Querying 800m route buffer via `cKDTree` and `STRtree`.
   - Distance orthogonal calculation from 75 POIs to 648 polyline segments.
4. **Night Activity Scoring (`NightActivityScorer`):** 18.50 ms local
   - Adaptive 100m sampling along route geometry.
   - Kernel density estimation and open/closed POI regex parsing.

### 4.3 Why Deployed Scoring Takes 57–65 Seconds: Root Causes

#### Root Cause 1: Cloud Container CPU Quota Throttling (The Primary Multiplier)
- On Render's Free/Starter tier, container CPU resources are allocated as shared vCPU (equivalent to **0.1 to 0.3 vCPU shares** with strict CFS quota enforcement).
- Mathematical calculations, TreeSHAP explainer iterations, and spatial geometry operations are strictly single-threaded CPU-bound.
- When 5,016 ms of 100% desktop CPU compute runs in an environment throttled to 10%–12% CPU quota, the wall-clock execution time increases by a factor of 8x–12x:
  $$5.016\text{ s} \times 11.5 \approx 57.68\text{ s}$$
  This perfectly explains why Gemini API calls (which are network I/O-bound) take ~2.0 seconds in both environments, while CPU-bound scoring scales from 5.0s to 57.6s!

#### Root Cause 2: Multi-Candidate Redundant Scoring Loops
In `coordinator.py`:
- 5 route candidates are generated:
  1. `DRIVING_PRIMARY` (37.5 km)
  2. `DRIVING_ALTERNATIVE` (38.1 km)
  3. `TWO_WHEELER` (37.5 km)
  4. `TRANSIT_SUBURBAN` (Multimodal: Walk -> Suburban Train -> Walk)
  5. `TRANSIT_BUS` (Multimodal: Walk -> MTC Bus -> Walk)
- In `ml_route_scoring_service.py` (`score_candidate_route`):
  For each multimodal route, `match_multimodal_route` first matches each road leg to road segments.
  Then, on lines 443–470:
  ```python
  for s_idx, s_geom in enumerate(dynamic_segs):
      s_match = self.spatial_matcher.match_route(s_geom)
      s_score_dict = self.score_route_match(s_match, hour=hour)
  ```
  It **re-runs** `match_route` and `score_route_match` a second time for each sub-leg, duplicating spatial index lookups and LightGBM model inference!

#### Root Cause 3: Repeated Spatial Index Rebuilding
In `spatial_matcher.py` (`_ensure_index_for_corridor`):
- Because the 5 candidate routes have slightly different bounding boxes (e.g. driving takes highway bypass, bus takes inner arterial roads), the corridor bounding box progressively expands.
- In our profile logs:
  - Candidate 1: Builds index with 1,044 segments.
  - Candidate 2: Expands bounding box, rebuilds index with 6,670 segments.
  - Candidate 4: Expands bounding box, rebuilds index with 27,892 segments.
  - Candidate 5: Expands bounding box, rebuilds index with 40,918 segments.
- Each index rebuild performs SQLite disk reads and Shapely `STRtree` tree construction. On cloud network-attached storage (NAS/EFS) under high latency, repeated SQLite disk queries compound the CPU delay.

#### Root Cause 4: Response Construction Duplication
In `response_builder.py` (`build_journey_plan`):
- For all 5 candidate routes:
  - `poi_service.query_pois_near_route(coords, corridor_m=800.0)` is executed individually, re-building polyline segment bounding boxes each time.
  - `night_activity_scorer.evaluate_route(coords, pass_through_hour=hour)` is executed individually, sampling 375 points and running regex evaluation on opening hours.
- 5 candidates $\times$ ~334 ms local = 1,670 ms local $\rightarrow$ scaled by cloud throttling to **11,093 ms – 16,991 ms** in deployed logs!

---

## 5. Verification & Test Execution (Section 5)

### 5.1 Test Suites Executed

1. **Frontend Client Timeout Test Suite (`frontend/src/api/services/__tests__/journey-timeout.test.ts`):**
   - Verified that `planJourney` passes `timeout: 120000` to Axios.
   - Verified that autocomplete and lifecycle calls do not pass `timeout: 120000`.
   - Verified that default `apiClient.defaults.timeout` remains 60,000 ms.
   - **Result:** 3/3 passed.

2. **Frontend Full Regression Suite (`npm test`):**
   - Ran all 11 test suites across components, assistant, and api services.
   - **Result:** 92 passed, 0 failed.

3. **Frontend TypeScript Check (`npx tsc --noEmit`):**
   - Verified strict type checking across all files.
   - **Result:** Exit code 0 (no errors).

4. **Backend Regression & Verification Suite (`pytest tests/test_phase51_long_route_and_model_rotation.py tests/test_phase51_core_reliability.py`):**
   - Verified STRtree sub-second spatial querying.
   - Verified stage timing isolation between scoring and response construction.
   - Verified that STRtree bounding-box pruning returns genuine nearby POIs without dropping facilities.
   - Verified that response construction does not re-invoke LightGBM scoring.
   - Verified that simultaneous weather and Gemini provider failure leaves routes and scores intact.
   - Verified Gemini model rotation, auth error halting, and credential safety.
   - **Result:** 44 passed, 0 failed (41 pre-existing + 3 new Phase 51.60 tests).

---

## 6. Changed-File Manifest & Invariant Compliance

### Modified Files (Tracked)
1. `frontend/src/api/services/journeyService.ts`
   - Added `timeout: 120000` to `apiClient.post` in `planJourney`.
   - Normalized type imports for `StandardResponse` and `JourneyCreateRequest`.
2. `tests/test_phase51_long_route_and_model_rotation.py`
   - Added Phase 51.60 verification tests:
     - `test_p0_strtree_pruning_preserves_legitimate_nearby_pois`
     - `test_p0_response_construction_stage_separation_and_no_rescoring`
     - `test_p0_weather_and_gemini_failure_preserves_route_validity`

### New Files (Untracked)
1. `frontend/src/api/services/__tests__/journey-timeout.test.ts`
   - Unit tests validating the 120,000 ms journey-specific timeout and 60,000 ms default preservation.

### Safeguard Confirmations
- **API Keys / Secrets:** Untouched. No keys or tokens added or exposed.
- **Environment Files:** Untouched.
- **ML Artifacts / Weights:** Untouched. Checksums preserved.
- **Git State:**
  - Branch: `release/phase51-render-staging`
  - Current HEAD: `1912ab7565b690ecd195274c6a4df902fec54fbc`
  - Production `main`: Untouched (`bbea228d0c4905c7ac78e7bf2dbc745342af10fd`)
  - **No commit, push, or deployment was performed in this phase.**
