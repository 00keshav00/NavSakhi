# SafeShe Dataset Schema Specification

This document freezes the master dataset schema for the SafeShe Dataset Engineering layer.

It is an architecture specification only.

- No Python code is defined here.
- No CSV files are generated here.
- No preprocessing behavior is implemented here.
- The goal is to define the shape, semantics, and validation rules for all datasets produced by the SafeShe data engineering pipeline before implementation begins.

## 1. Dataset Overview

SafeShe produces two supervised-learning datasets.

### `crowd_dataset.csv`

Purpose:

- Train the crowd prediction model.
- Estimate how crowded a location is at a specific time.
- Provide a clean tabular target for a regression model.

Generation concept:

- Start with a geospatial location and timestamp.
- Collect OSM-derived spatial indicators around that point.
- Join population context from WorldPop.
- Add generated time features such as hour, day, and weekend.
- Compute the crowd label as a generated target for model supervision.

### `safety_dataset.csv`

Purpose:

- Train the safety prediction model.
- Estimate journey safety for a route point or route corridor.
- Combine crowd, crime, mobility, environmental, and road-context signals.

Generation concept:

- Start with a route point, route segment, or route-level aggregation.
- Pull crime context from crime datasets.
- Pull crowd score from the crowd pipeline or stored crowd output.
- Pull OSM road and place context.
- Pull weather and community-report signals.
- Add generated time features such as hour, day, and weekend.
- Compute the safety label as a generated target for model supervision.

## 2. Data Sources

### Crime Dataset

Used for risk context and safety label generation.

- **TN Crime Data**
  - Regional crime records normalized to 38 canonical revenue districts.
  - Commissionerates, Railway Police, and Special Units are separated from the main district output.
  - Used to derive a numeric crime intensity signal.
- **NCRB**
  - National-level crime statistics.
  - *Note: National or state-level aggregate records are explicitly excluded from local spatial engineering features.*

### Population

Used to estimate baseline exposure and foot-traffic pressure.

- **WorldPop GeoTIFF**
  - Raster-based population density source.
  - Spatially joined to point or grid locations.
  - Converted into a numeric population density feature.

### OpenStreetMap

Used for all spatial POI, road, and accessibility signals.

- **OSM Features defined in [docs/osm_features.md](osm_features.md)**
  - Safety features.
  - Crowd features.
  - Road features.
  - Stored as distance, count, density, binary, or categorical transforms.

### Generated Features

These are derived from request metadata or route metadata.

- **Time**
  - Timestamp or request time reference.
- **Day**
  - Day-derived feature such as Monday, Tuesday, etc.
- **Hour**
  - Hour of day from the timestamp.
- **Weekend**
  - Boolean indicator for Saturday and Sunday.

### Synthetic Features

These are computed or simulated during dataset engineering when live values are unavailable.

- **Weather**
  - OpenWeather-derived or synthetic weather risk representation.
- **Community Reports**
  - Aggregated social-signal or user-report feature stored in MongoDB or a similar upstream source.

## 3. Complete Feature Schema Table

The table below defines the master feature schema used across the SafeShe dataset engineering layer.

| Feature Name | Data Type | Source | Transformation | Static or Runtime | Used By | Example Value | Description |
|---|---|---|---|---|---|---|---|
| latitude | float32 | Browser GPS | Raw coordinate retained as-is | Runtime | Crowd, Safety | 13.0827 | Latitude of the user or route point. |
| longitude | float32 | Browser GPS | Raw coordinate retained as-is | Runtime | Crowd, Safety | 80.2707 | Longitude of the user or route point. |
| hour | int32 | Timestamp | Extract hour from timestamp | Runtime | Crowd, Safety | 18 | Hour of day in 24-hour format. |
| day_of_week | int32 | Timestamp | Extract weekday index from timestamp | Runtime | Crowd, Safety | 5 | Day index in a stable numeric representation. |
| weekend | boolean | Timestamp | Derive from day_of_week | Runtime | Crowd, Safety | true | Indicates whether the timestamp falls on Saturday or Sunday. |
| crime_score | float32 | TN Crime Data, NCRB | Normalize crime statistics into a 0–100 risk signal | Static with periodic refresh | Safety | 72.4 | Local crime intensity used as a safety risk indicator. |
| population_density | float32 | WorldPop GeoTIFF | Raster sample or spatial join; normalize to density | Static with periodic refresh | Crowd, Safety | 1845.2 | Population pressure around the location. |
| restaurant_count | int32 | OpenStreetMap (amenity=restaurant) | Count POIs within the extraction radius | Static | Crowd | 12 | Restaurant proximity proxy for crowding. |
| bus_stop_count | int32 | OpenStreetMap (highway=bus_stop) | Count bus stops within the extraction radius | Static | Crowd | 4 | Transit-stop proxy for crowd concentration. |
| metro_count | int32 | OpenStreetMap (railway=station) | Count metro or rail stations nearby | Static | Crowd | 1 | Metro or rail station proximity signal. |
| office_density | float32 | OpenStreetMap (office=*) | POI count normalized by area | Static | Crowd | 0.67 | Office concentration signal. |
| commercial_density | float32 | OpenStreetMap (landuse/shop/amenity/office) | Aggregate commercial POI and land-use score | Static | Crowd, Safety | 0.81 | Commercial activity intensity. |
| commercial_density_score | float32 | OpenStreetMap (derived) | Normalized commercial activity score | Static | Crowd | 74.3 | Model-ready commercial density signal. |
| road_type | categorical | OpenStreetMap | Map road class to canonical category | Static | Safety | residential | Road classification near the route or point. |
| road_type_risk | float32 | OpenStreetMap | Convert road class to numeric risk score | Static | Safety | 28.0 | Risk score derived from road class. |
| lighting_score | float32 | OpenStreetMap (lit=yes/no) | Binary lighting signals and road-lit coverage aggregated to score | Static with periodic refresh | Safety | 82.0 | Indicates how well lit the local area is. |
| police_distance | float32 | OpenStreetMap (amenity=police) | Nearest-neighbor distance in meters | Static with periodic refresh | Safety | 430.5 | Distance to the nearest police station. |
| hospital_distance | float32 | OpenStreetMap (amenity=hospital/clinic) | Nearest-neighbor distance in meters | Static with periodic refresh | Safety | 920.1 | Distance to the nearest hospital or clinic. |
| road_surface | categorical | OpenStreetMap | Map surface tag to canonical class | Static | Safety | asphalt | Road surface quality signal. |
| sidewalk_presence | categorical or boolean | OpenStreetMap | Encode sidewalk availability | Static | Safety | both | Whether sidewalks exist on nearby roads. |
| foot_access | categorical | OpenStreetMap | Encode pedestrian access restrictions | Static | Safety | yes | Whether a road is intended or allowed for walking. |
| max_speed | float32 | OpenStreetMap | Parse `maxspeed` to numeric value | Static | Safety | 40 | Posted road speed limit. |
| intersection_density | float32 | OpenStreetMap | Count intersections per area | Static | Safety, optional Crowd | 0.14 | Road-network complexity around the point. |
| junction_complexity | categorical | OpenStreetMap | Encode junction type or complexity score | Static | Safety | roundabout | Junction type around the route context. |
| oneway | boolean | OpenStreetMap | Convert oneway tag to boolean indicator | Static | Safety | false | Directionality of nearby roads. |
| traffic_calming_count | int32 | OpenStreetMap | Count calming devices in radius | Static | Safety | 3 | Counts speed-reduction road features. |
| weather | categorical | OpenWeather API | Convert current conditions to weather class | Runtime | Safety | rainy | Live environmental condition. |
| weather_risk | float32 | OpenWeather API | Map weather class to numeric risk score | Runtime | Safety | 64.0 | Risk contribution from weather conditions. |
| crowd_score | float32 | Crowd dataset or crowd model output | Use predicted or stored crowd value | Runtime | Safety | 58.7 | Crowd pressure used by the safety model. |
| community_reports | float32 | MongoDB | Aggregate recent user or community reports | Runtime | Safety | 0.35 | Crowd-sourced safety signal. |
| walking_distance | float32 | OSRM | Route distance or pedestrian path length | Runtime | Safety | 1420.0 | Distance that the user would walk or traverse. |
| transport_mode | categorical | User input | Normalize transport mode to canonical label | Runtime | Safety | walk | Selected travel mode. |
| route_corridor_road_exposure | float32 | OpenStreetMap + OSRM | Aggregate road-class exposure over route corridor | Runtime | Safety | 0.44 | Route-level road risk summary. |
| route_corridor_lighting_score | float32 | OpenStreetMap | Aggregate lit coverage over route corridor | Runtime | Safety | 77.0 | Route-level lighting quality. |
| route_corridor_sidewalk_score | float32 | OpenStreetMap | Aggregate sidewalk coverage along route | Runtime | Safety | 69.0 | Route-level sidewalk availability. |
| time_weight | float32 | Timestamp | Convert time bucket to relative crowding weight | Runtime | Crowd | 0.9 | Time-of-day crowding signal. |

### Feature interpretation notes

- Features listed as OSM-derived should be aligned with the detailed OSM tag mapping in [docs/osm_features.md](osm_features.md).
- Count-based features are treated as integer-like or density-like numeric inputs.
- Distance-based features are treated as meters.
- Route-corridor features are produced by aggregating multiple OSM segments rather than a single point query.

## 4. Crowd Dataset Schema

### `crowd_dataset.csv`

This dataset is used to train the crowd prediction model.

#### Input Features

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

#### Optional/derived context

- road_type
- lighting_score
- police_distance
- hospital_distance
- route_corridor_road_exposure
- route_corridor_lighting_score
- route_corridor_sidewalk_score

#### Target Label

- crowd_score

#### Description

- Represents the local crowd intensity at a given location and time.
- Stores spatial, temporal, and population-driven signals.
- Uses OSM-derived density proxies and generated time features.
- The target is a generated label intended for regression training.

## 5. Safety Dataset Schema

### `safety_dataset.csv`

This dataset is used to train the safety prediction model.

#### Input Features

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

#### Optional/derived context

- road_surface
- sidewalk_presence
- foot_access
- max_speed
- intersection_density
- junction_complexity
- oneway

#### Target Label

- safety_score

#### Description

- Represents journey safety at a point or along a route corridor.
- Combines crime, crowd, weather, road, and community signals.
- Includes both static infrastructure signals and runtime signals.
- The target is a generated label intended for regression training.

## 6. Label Definitions

### `crowd_score`

- A numeric label representing how crowded a location is expected to be.
- Higher values indicate stronger pedestrian or commercial activity.
- Used only as the regression target for the crowd prediction model.
- The label is derived during dataset engineering and should not be treated as a raw source field.

- Output range: `0–100`.

### `safety_score`

- A numeric label representing predicted journey safety.
- Higher values indicate safer travel conditions.
- Used only as the regression target for the safety prediction model.
- The label is derived during dataset engineering and should not be treated as a raw source field.

- Output range: `0–100`.

## 7. Missing Value Policy

### Missing OSM tags

- Missing tags must not break dataset generation.
- If a POI or road tag is missing, use the following fallback order:
  - nearest valid object within radius
  - aggregated count fallback
  - zero for count-based features
  - neutral score for risk-based features
- For categorical road attributes, use `unknown` when no valid OSM tag is available.

### Missing crime values

- If crime values are missing at the target location, use the nearest available region-level statistic.
- If no region-level value is available, use a conservative default risk value and mark the record for review.
- Missing crime values should never silently become negative or infinite.

### Missing weather

- If live weather is unavailable, use the most recent cached value.
- If no cached value exists, use a neutral synthetic weather state and retain a missingness flag if the pipeline supports it.
- Weather should be stable enough to allow offline reproducibility.

### Missing population values

- If WorldPop sampling fails or returns no value, use the nearest raster cell or spatially averaged neighborhood value.
- If the raster value is unavailable, default to zero only after logging the failure in the engineering pipeline.

## 8. Data Types

### float32

Use for continuous numeric signals such as:

- crime_score
- population_density
- office_density
- commercial_density
- commercial_density_score
- lighting_score
- police_distance
- hospital_distance
- weather_risk
- crowd_score
- safety_score
- walking_distance
- route-corridor aggregate scores

### int32

Use for discrete numeric signals such as:

- hour
- restaurant_count
- bus_stop_count
- metro_count
- traffic_calming_count
- intersection_density when stored as integer counts

### categorical

Use for symbolic or bucketed values such as:

- day_of_week
- transport_mode
- road_type
- road_surface
- junction_complexity
- weather

### boolean

Use for binary states such as:

- weekend
- oneway
- foot_access when represented as allow / disallow
- lit presence when represented as yes / no

### datetime

Use for the original event timestamp before feature extraction.

- The raw timestamp should be preserved in the engineering layer where possible.
- Hour, day, and weekend are derived from datetime values.

## 9. Dataset Validation Rules

The dataset engineering pipeline must reject or flag records that violate the following rules.

### Geographic checks

- Latitude must be between `-90` and `90`.
- Longitude must be between `-180` and `180`.
- Location coordinates must be finite numeric values.

### Distance checks

- Police distance must be non-negative.
- Hospital distance must be non-negative.
- Walking distance must be non-negative.
- No distance feature may be infinite in the exported dataset.

### Risk and score checks

- Crime score must be within `0–100`.
- Crowd score must be within `0–100`.
- Safety score must be within `0–100`.
- Weather risk must be within the configured bounded range used by the project.
- Lighting score must be within `0–100`.
- Road-type risk must be within `0–100`.

### Density and count checks

- Population density must be greater than or equal to `0`.
- POI counts must be greater than or equal to `0`.
- Density features must be finite.

### Type checks

- Categorical values must be normalized to a known vocabulary.
- Boolean values must be stored consistently as boolean or binary encoded values.
- Datetime inputs must be parseable before feature extraction.
- Numeric values must use a consistent precision policy before export.

### Schema checks

- Every required feature for a dataset must be present before export.
- No duplicate columns are allowed.
- No record should contain a null target label.

## 10. Dataset Versioning

Each generated dataset must carry version metadata.

### Schema Version

- Identifies the overall dataset schema contract.
- Initial version: `1.0.0`
- Increment when columns, types, or validation rules change.

### Feature Version

- Identifies the feature set definition.
- Initial version: `1.0.0`
- Increment when feature engineering logic or feature naming changes.

### OSM Version

- Identifies the OSM extraction rules and tag mapping set.
- Initial version: `1.0.0`
- Increment when OSM tags, radii, or corridor aggregation rules change.

### Crime Dataset Version

- Identifies the upstream crime data snapshot.
- Initial version: `1.0.0`
- Increment when TN Crime or NCRB source snapshots change.

### Population Dataset Version

- Identifies the upstream WorldPop snapshot.
- Initial version: `1.0.0`
- Increment when the raster snapshot or spatial join logic changes.

## Notes

- The schema should remain stable across training and inference.
- Any new feature added to the pipeline must be reflected in this document before implementation.
- The dataset engineering layer should treat this file as the source of truth for column naming and source semantics.
