# SafeShe Feature Engineering Specification

This document defines the feature engineering pipeline for the SafeShe Dataset Engineering layer.

It is an architecture specification only.

- No Python code is defined here.
- No preprocessing logic is implemented here.
- No model training is described here.
- The goal is to define how raw inputs become ML-ready features for the crowd and safety datasets.

## 1. Pipeline Overview

SafeShe transforms heterogeneous raw data sources into normalized tabular features for two downstream datasets:

- Crowd feature set for crowd density estimation.
- Safety feature set for journey safety estimation.

The feature engineering pipeline standardizes spatial, temporal, environmental, and community signals into consistent numeric and categorical representations.

### End-to-End Pipeline Diagram

```mermaid
flowchart TD
    A[Raw Sources] --> B[Source Ingestion]
    B --> C[Source Cleaning]
    C --> D[Feature Extraction]
    D --> E[Feature Normalization]
    E --> F[Feature Assembly]
    F --> G[Crowd Feature Set]
    F --> H[Safety Feature Set]

    subgraph Raw Sources
        A1[Browser GPS]
        A2[Timestamp]
        A3[OpenStreetMap]
        A4[Crime Dataset]
        A5[WorldPop GeoTIFF]
        A6[OpenWeather API]
        A7[MongoDB Community Reports]
        A8[OSRM Route Metrics]
    end

    Raw Sources --> A

    subgraph Normalized Features
        N1[Coordinates]
        N2[Temporal Features]
        N3[OSM POI Features]
        N4[Road Features]
        N5[Crime Risk Features]
        N6[Population Features]
        N7[Weather Risk Features]
        N8[Community Report Features]
        N9[Route Features]
    end

    D --> N1
    D --> N2
    D --> N3
    D --> N4
    D --> N5
    D --> N6
    D --> N7
    D --> N8
    D --> N9
```

## 2. Crime Feature Engineering

Crime features provide the safety model with a localized risk signal based on external crime statistics.

### 2.1 Input Source

- TN Crime Data
- NCRB

### 2.2 Feature Engineering Goals

- Convert spatial crime records into a location-level crime score.
- Preserve geographic comparability across regions.
- Provide a bounded numeric input for the safety dataset.

### 2.3 Transformations

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| District-level or zone-level crime counts | Aggregate counts across 38 canonical revenue districts (excluding state/national aggregates) | `crime_score` | Scale to a 0–100 risk range | Use nearest region-level statistic or a conservative fallback score |
| Crime counts by category | Weighted aggregation across violent, property, or public-order categories | `crime_score` | Normalize to a common risk scale | If one category is missing, compute the score from the available categories only |
| Historical crime snapshot | Temporal smoothing across recent periods | `crime_score` | Clip extreme outliers before scaling | If the snapshot is unavailable, use the latest cached crime summary |

### 2.4 Output Features

- `crime_score`

### 2.5 Notes

- Crime features are treated as static with periodic refresh.
- Crime values should remain stable enough to support offline dataset generation and runtime lookups.

## 3. Population Feature Engineering

Population features represent the baseline density pressure around a location.

### 3.1 Input Source

- WorldPop GeoTIFF

### 3.2 Feature Engineering Goals

- Convert raster population values into point-level or cell-level density indicators.
- Align the raster resolution with the OSM-based spatial query policy.

### 3.3 Transformations

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Raster population cell value | Sample the raster at the location or aggregate nearby cells | `population_density` | Normalize to a comparable density scale | Use nearest raster cell or neighborhood average |
| Raster-derived area estimate | Convert to density per square kilometer or equivalent unit | `population_density` | Standardize by area and clip extremes | Fall back to zero only if all raster lookups fail |

### 3.4 Output Features

- `population_density`

### 3.5 Notes

- Population features are treated as static with periodic refresh.
- The same sampling strategy must be used during dataset generation and runtime inference.

## 4. OpenStreetMap Feature Engineering

OSM features provide the main spatial context for both the crowd and safety datasets.

The authoritative OSM feature inventory is defined in [docs/osm_features.md](osm_features.md).

### 4.1 Input Source

- OpenStreetMap nodes, ways, and relations

### 4.2 Feature Engineering Goals

- Convert raw OSM geometries into distance, count, density, binary, and categorical features.
- Support both point-based extraction and route-corridor aggregation.
- Maintain feature parity between offline dataset creation and runtime inference.

### 4.3 Transformations

#### Safety-oriented OSM features

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Police POIs | Nearest-neighbor distance to the closest police station | `police_distance` | Express in meters and scale consistently | Use nearest valid security POI or a large fallback distance |
| Hospital or clinic POIs | Nearest-neighbor distance to medical infrastructure | `hospital_distance` | Express in meters and cap extreme values | Use the nearest clinic or hospital when only one is present |
| Road lighting tags | Aggregate lit road coverage in the query area | `lighting_score` | Convert to a bounded 0–100 scale | Use neutral lighting score when the tag is missing |
| Road class tags | Map road hierarchy to a risk score | `road_type`, `road_type_risk` | Convert road categories into canonical values and bounded risk | Use `unknown` for missing road classes |
| Sidewalk tags | Encode sidewalk presence and coverage | `sidewalk_presence`, `route_corridor_sidewalk_score` | Convert to categorical or percentage coverage | Use an unknown or absent-sidewalk representation when missing |
| Foot access tags | Encode pedestrian accessibility | `foot_access` | Map access tags to canonical categories | Use `unknown` when pedestrian access is not tagged |
| Speed limit tags | Parse posted speed values into a numeric road-risk signal | `max_speed` | Convert textual limits to numeric values | Use inferred regional defaults only if no tag is present |
| Junction and intersection data | Count intersections and encode junction complexity | `intersection_density`, `junction_complexity` | Normalize by area or route length | Use zero or unknown complexity when topology is unavailable |
| One-way tags | Encode directionality of road flow | `oneway` | Store as boolean or binary value | Default to false only when the road is explicitly bidirectional or no tag exists |
| Traffic calming tags | Count calming devices around the location | `traffic_calming_count` | Normalize by radius or corridor length | Use zero when no calming feature is found |

#### Crowd-oriented OSM features

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Restaurant POIs | Count restaurants within a spatial radius | `restaurant_count` | Normalize by query area or radius size | Use zero if no restaurants are found |
| Bus stop POIs | Count bus stops within a spatial radius | `bus_stop_count` | Normalize by query area or radius size | Use zero if no bus stops are found |
| Metro or railway station POIs | Count transit stations nearby | `metro_count` | Normalize by query area or route buffer | Use zero if no station is found |
| Office POIs | Count office locations and convert to density | `office_density` | Normalize by area | Use zero when office POIs are absent |
| Commercial land-use and POIs | Aggregate commercial land-use intensity | `commercial_density`, `commercial_density_score` | Scale to a bounded density or score | Use a neutral low value if commercial tags are missing |
| School POIs | Count nearby schools | Crowd-supporting auxiliary signal | Normalize by area and optionally by time bucket | Use zero if no schools are found |
| College and university POIs | Count higher-education facilities nearby | Crowd-supporting auxiliary signal | Normalize by area and optionally by time bucket | Use zero if no institutions are found |
| Park POIs | Count parks and public open spaces | Crowd-supporting auxiliary signal | Normalize by area | Use zero if no parks are found |
| Market or marketplace POIs | Count market activity near the point | Crowd-supporting auxiliary signal | Normalize by area | Use zero if no market POIs are found |

#### Road-corridor OSM features

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Route segments and road classes | Aggregate road class exposure along the route corridor | `route_corridor_road_exposure` | Normalize by corridor length | Use corridor-only fallback when full route graph data is not available |
| Road lighting along the route | Aggregate lit coverage across route segments | `route_corridor_lighting_score` | Normalize to a 0–100 score | Use area-level lighting score if corridor data is missing |
| Sidewalk coverage along the route | Aggregate sidewalk availability across route segments | `route_corridor_sidewalk_score` | Normalize to a 0–100 score | Use point-level sidewalk presence when route data is incomplete |

### 4.4 Output Features

OSM feature engineering produces the following model-ready outputs:

- `restaurant_count`
- `bus_stop_count`
- `metro_count`
- `office_density`
- `commercial_density`
- `commercial_density_score`
- `road_type`
- `road_type_risk`
- `lighting_score`
- `police_distance`
- `hospital_distance`
- `road_surface`
- `sidewalk_presence`
- `foot_access`
- `max_speed`
- `intersection_density`
- `junction_complexity`
- `oneway`
- `traffic_calming_count`
- `route_corridor_road_exposure`
- `route_corridor_lighting_score`
- `route_corridor_sidewalk_score`

### 4.5 Notes

- OSM features should remain consistent with [docs/osm_features.md](osm_features.md).
- Point-based features are preferred for crowd estimation.
- Corridor-based features are preferred for safety estimation.
- OSM-derived features are generally static or periodically refreshed.

## 5. Weather Feature Engineering

Weather features provide dynamic environmental context for the safety model.

### 5.1 Input Source

- OpenWeather API

### 5.2 Feature Engineering Goals

- Convert live weather conditions into a consistent risk signal.
- Preserve a stable fallback for offline or unavailable API responses.

### 5.3 Transformations

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Weather condition string | Map the live condition to a canonical category | `weather` | Use a fixed vocabulary | Use the most recent cached weather or a neutral fallback class |
| Weather condition and intensity | Convert conditions into a numeric risk score | `weather_risk` | Scale to a bounded score range | Use neutral weather risk when the API is unavailable |
| Temperature, rain, wind, humidity signals | Combine into a composite weather risk profile | `weather_risk` | Normalize each component before aggregation | Fall back to the cached summary or a neutral default |

### 5.4 Output Features

- `weather`
- `weather_risk`

### 5.5 Notes

- Weather features are runtime features.
- Weather should be reproducible for dataset generation by storing a snapshot or cache value.

## 6. Community Report Feature Engineering

Community report features capture user- or community-generated signals about safety conditions.

### 6.1 Input Source

- MongoDB community report store

### 6.2 Feature Engineering Goals

- Convert raw reports into a stable numeric signal.
- Reduce noise from duplicate, stale, or unverifiable reports.
- Keep the signal interpretable for the safety model.

### 6.3 Transformations

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| User reports | Aggregate recent reports in the relevant spatial window | `community_reports` | Normalize by time window or report volume | Use zero or a neutral low-risk score when no reports exist |
| Report severity or category | Weight reports by type, recency, or confidence | `community_reports` | Convert to a bounded score | Ignore stale or unverified reports if they cannot be trusted |
| Community report counts | Deduplicate and summarize repeated signals | `community_reports` | Normalize to a score range | If no reports are available, keep the feature at a safe default |

### 6.4 Output Features

- `community_reports`

### 6.5 Notes

- Community report features are runtime features.
- The same aggregation window should be used consistently across all generated datasets.

## 7. Temporal Feature Engineering

Temporal features are derived from the timestamp and are shared across both datasets.

### 7.1 Input Source

- Timestamp

### 7.2 Transformations

| Input Source | Transformation | Output Feature | Normalization | Missing Value Handling |
|---|---|---|---|---|
| Timestamp | Extract hour of day | `hour` | Store as an integer from 0 to 23 | Use a valid default hour only if the timestamp is missing after validation |
| Timestamp | Extract day of week | `day_of_week` | Store as a consistent numeric weekday index | Use a fixed weekday fallback only if required by the pipeline |
| Timestamp | Derive weekend indicator | `weekend` | Store as boolean | Use false only when the weekend status cannot be determined |
| Timestamp | Derive time-of-day weighting | `time_weight` | Map time buckets to a bounded weight | Use a neutral weight when time bucketing fails |

### 7.3 Output Features

- `hour`
- `day_of_week`
- `weekend`
- `time_weight`

## 8. Raw to ML-Ready Feature Contract

This section defines the final feature assembly expectation.

### Crowd-ready features

- latitude
- longitude
- hour
- day_of_week
- weekend
- restaurant_count
- bus_stop_count
- metro_count
- office_density
- commercial_density_score
- population_density
- time_weight

### Safety-ready features

- crime_score
- crowd_score
- weather
- weather_risk
- lighting_score
- police_distance
- hospital_distance
- community_reports
- hour
- day_of_week
- weekend
- road_type
- road_type_risk
- walking_distance
- transport_mode
- route_corridor_road_exposure
- route_corridor_lighting_score
- route_corridor_sidewalk_score
- population_density

## 9. Normalization Strategy

Feature normalization is source-dependent and must be consistent across dataset generation and runtime use.

- Distance features should be measured in meters.
- Count features should be non-negative integers or integer-like values.
- Density features should be normalized by area, corridor length, or spatial window size.
- Score features should be bounded to a consistent range, preferably 0–100.
- Categorical features should be encoded into a canonical vocabulary before export.
- Boolean features should use a single representation across the pipeline.

## 10. Missing Value Strategy

Feature engineering must define graceful handling for incomplete source data.

- If OSM data is missing, use a neutral or zero-like fallback depending on feature type.
- If crime data is missing, fall back to the nearest valid region-level value.
- If population data is missing, use the nearest raster cell or a neighborhood average.
- If weather data is missing, use the latest cached snapshot or a neutral condition.
- If community reports are missing, use a zero-report baseline.
- Missing values must never break dataset construction.

## 11. Feature Engineering Assumptions

- The same spatial query policy must be used for offline dataset generation and runtime inference.
- Route-corridor features are only used when OSRM route geometry is available.
- OSM feature availability varies by geography, so fallback logic is required.
- Feature names must match the frozen dataset schema document.
- This document intentionally stops before preprocessing, scaling, encoding, and model training details.

## 12. Implementation Boundary

This document defines how data should be transformed conceptually, not how the transformation should be coded.

- No preprocessing functions are implemented here.
- No model-specific logic is implemented here.
- No training workflow is described here.
- No CSV generation is described here.
