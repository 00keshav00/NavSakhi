# SafeShe Label Generation Specification

This document defines the label generation strategy for the SafeShe ML pipeline.

It is an architecture specification only.

- No Python code is defined here.
- No formulas are implemented here.
- No model training behavior is described here.
- The goal is to define how supervised labels are constructed and validated before implementation begins.

## 1. Label Generation Overview

SafeShe uses two generated regression targets:

- `crowd_score` for crowd density estimation.
- `safety_score` for journey safety estimation.

Both labels are generated during dataset engineering and are not treated as raw source fields.

The labels must be:

- Bounded to a stable output range.
- Reproducible across offline dataset creation and runtime dataset refreshes.
- Interpretable enough for architecture review and downstream model calibration.

## 2. Crowd Score

### Purpose

`crowd_score` represents how crowded a location is expected to be at a specific time.

It is the target label for the crowd prediction model and is used to estimate pedestrian concentration, commercial activity intensity, and transit-driven footfall.

### Inputs Used

Crowd score generation uses the following inputs:

- Latitude and longitude for the location anchor.
- Hour and day-of-week for temporal context.
- Weekend indicator for temporal grouping.
- OSM crowd-oriented features such as:
  - restaurant_count
  - bus_stop_count
  - metro_count
  - office_density
  - commercial_density_score
- Population density from WorldPop.
- Time-weighting derived from timestamp.

### Output Range

- Minimum: `0`
- Maximum: `100`

Interpretation:

- Lower values indicate low crowd pressure.
- Higher values indicate dense or highly active surroundings.

### Normalization

The crowd score must be normalized into a bounded 0–100 scale.

Normalization expectations:

- Combine heterogeneous feature inputs into a common score space.
- Keep the output stable across different neighborhoods and city scales.
- Prevent very large POI counts from dominating the final target.
- Preserve relative crowd intensity rather than absolute raw counts.

### Validation Rules

The crowd score must satisfy the following rules:

- Must be numeric.
- Must be finite.
- Must lie within `0–100`.
- Must not be null in the final crowd dataset.
- Must be derived from the approved crowd feature set only.
- Must remain comparable across dataset versions.

## 3. Safety Score

### Purpose

`safety_score` represents the predicted safety of a journey or route context.

It is the target label for the safety prediction model and is used to describe how safe or risky a walking or travel path is expected to be.

### Inputs Used

Safety score generation uses the following inputs:

- Crime score.
- Crowd score.
- Weather risk or weather condition class.
- Lighting score.
- Police distance.
- Hospital distance.
- Community reports.
- Hour and day-of-week for temporal context.
- Weekend indicator for temporal grouping.
- Road type and route-corridor road exposure.
- Walking distance.
- Transport mode.
- OSM-derived route-quality features such as corridor lighting and sidewalk coverage.

### Output Range

- Minimum: `0`
- Maximum: `100`

Interpretation:

- Lower values indicate unsafe or high-risk journey conditions.
- Higher values indicate safer or more favorable journey conditions.

### Normalization

The safety score must be normalized into a bounded 0–100 scale.

Normalization expectations:

- Combine crime, crowd, road, environmental, and community signals into one comparable scale.
- Prevent any single feature family from overwhelming the safety label.
- Preserve route-level comparability across regions and times.
- Ensure the final label can be interpreted consistently by downstream users.

### Validation Rules

The safety score must satisfy the following rules:

- Must be numeric.
- Must be finite.
- Must lie within `0–100`.
- Must not be null in the final safety dataset.
- Must only use approved safety input features.
- Must remain comparable across dataset versions.

## 4. Label Construction Principles

The label generation strategy follows these principles:

- Labels are generated, not observed directly.
- Labels are designed for regression use cases.
- Labels must remain aligned with the frozen dataset schema and feature engineering documents.
- Labels must use consistent normalization so that dataset refreshes do not shift semantics unexpectedly.
- Labels should be stable enough to support offline training, evaluation, and replayable dataset builds.

## 5. Relationship to Other Documents

This document must be read together with:

- [docs/dataset_schema.md](dataset_schema.md)
- [docs/feature_engineering.md](feature_engineering.md)
- [docs/osm_features.md](osm_features.md)

Those documents define the dataset columns, raw-to-feature transformations, and OSM source mapping. This document defines only the final label strategy.

## 6. Implementation Boundary

This document intentionally stops before implementation details.

- No exact mathematical formula is defined here.
- No preprocessing pipeline is defined here.
- No model training behavior is defined here.
- No CSV generation is defined here.
- No code is required or included.
