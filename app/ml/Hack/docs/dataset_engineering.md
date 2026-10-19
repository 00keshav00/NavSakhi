# SafeShe Dataset Engineering Pipeline

This document defines the complete dataset engineering pipeline for SafeShe.

It is an architecture specification only.

- No code is defined here.
- No preprocessing logic is implemented here.
- No feature engineering logic is implemented here.
- No label formulas are implemented here.
- No CSV generation is implemented here.

The goal is to describe the stage-by-stage contract that transforms raw source data into the two final datasets used by the SafeShe ML pipeline:

- `crowd_dataset.csv`
- `safety_dataset.csv`

## 1. Pipeline Overview

SafeShe transforms raw data through a sequence of controlled engineering stages.

### Pipeline Flow

Raw Data

↓

Crime Loader

↓

Population Loader

↓

OSM Loader

↓

Weather Generator

↓

Community Report Generator

↓

Feature Engineering

↓

Label Generation

↓

Dataset Validation

↓

`crowd_dataset.csv`

↓

`safety_dataset.csv`

### Pipeline Goal

The pipeline produces consistent, validated, schema-aligned datasets for the crowd and safety models.

The engineering layer must preserve reproducibility, maintain source traceability, and keep the final datasets aligned with:

- [docs/dataset_schema.md](dataset_schema.md)
- [docs/feature_engineering.md](feature_engineering.md)
- [docs/label_generation.md](label_generation.md)
- [docs/osm_features.md](osm_features.md)

## 2. Stage Definitions

## Raw Data

### Input

- Browser GPS
- Timestamp
- TN Crime Data
- NCRB
- WorldPop GeoTIFF
- OpenStreetMap extracts
- OpenWeather API responses
- MongoDB community reports
- OSRM route metrics

### Output

- Source-specific raw records ready for loading

### Responsibility

- Hold unprocessed source data before any normalization or feature construction.
- Preserve the original source context for traceability and debugging.

### Dependencies

- None within the SafeShe engineering pipeline.
- Depends only on upstream external systems and source availability.

### Validation

- Confirm source availability and freshness.
- Confirm that raw records are parseable.
- Confirm that source timestamps, coordinates, and identifiers are present where required.

## Crime Loader

### Input

- TN Crime Data
- NCRB

### Output

- `ml/datasets/processed/crime_score.csv` (revenue districts only)
- `ml/datasets/processed/crime_score_commissionerates.csv`
- `ml/datasets/processed/crime_score_railway.csv`
- `ml/datasets/processed/crime_score_special_units.csv`

### Responsibility

- Load crime data from approved crime sources.
- Normalize whitespace and apply canonical district spelling corrections.
- Classify spatial records into revenue districts, commissionerates, railway police, or special units.
- Explicitly discard state-level or national-level aggregate rows from the final outputs.
- Provide the crime inputs used later for crime feature engineering and safety label context.

### Dependencies

- Raw crime source availability
- Canonical district mapping and spelling rules
- Versioned crime dataset snapshots

### Validation

- Validate that crime records are not empty.
- Validate region, district, or spatial identifiers.
- Validate that crime values are numeric and non-negative where applicable.
- Validate that the selected crime snapshot matches the configured dataset version.

## Population Loader

### Input

- WorldPop GeoTIFF

### Output

- Population density inputs aligned to the spatial query location
- Population-ready raster or joined records

### Responsibility

- Load population raster or raster-derived values.
- Convert population data into spatially addressable inputs.
- Provide the population context needed for crowd feature engineering.

### Dependencies

- WorldPop GeoTIFF availability
- Spatial coordinates or spatial grid references
- Projected or queryable geographic reference system

### Validation

- Validate that population data can be sampled or joined spatially.
- Validate that population values are finite and non-negative.
- Validate that raster lookups return a usable value or a defined fallback state.

## OSM Loader

### Input

- OpenStreetMap extracts
- OSM feature definitions from [docs/osm_features.md](osm_features.md)

### Output

- Normalized OSM spatial objects
- POI, road, and corridor inputs for feature engineering

### Responsibility

- Load raw OSM nodes, ways, and relations.
- Prepare OSM objects for spatial aggregation and feature extraction.
- Separate crowd-oriented, safety-oriented, and road-oriented source objects.

### Dependencies

- OSM source availability
- Spatial query boundary or route corridor definition
- Approved OSM tag mapping

### Validation

- Validate that OSM features are queryable for the requested area.
- Validate that geometry and tag records are parseable.
- Validate that the extracted OSM objects align with the approved feature inventory.

## Weather Generator

### Input

- OpenWeather API responses
- Timestamp
- Location coordinates

### Output

- Weather condition records
- Weather risk inputs for feature engineering

### Responsibility

- Produce a weather context for the requested location and time.
- Convert live or cached weather data into a consistent engineering input.
- Support runtime weather context and dataset-time weather snapshots.

### Dependencies

- OpenWeather API or cached weather snapshot
- Timestamp and location reference
- Fallback policy for unavailable live weather

### Validation

- Validate that weather status is parseable.
- Validate that weather records are finite and bounded where required.
- Validate that a fallback exists if the live API is unavailable.

## Community Report Generator

### Input

- MongoDB community reports
- Location coordinates
- Timestamp or recency window

### Output

- Aggregated community report signal
- Community-report-ready inputs for feature engineering

### Responsibility

- Aggregate community-generated safety signals.
- Convert raw user or community reports into a stable engineered input.
- Support runtime and dataset-level safety context.

### Dependencies

- MongoDB availability
- Report schema or collection structure
- Spatial or temporal aggregation window

### Validation

- Validate that report data is available or that a neutral fallback exists.
- Validate that report scores or counts are finite.
- Validate recency and deduplication rules where applicable.

## Feature Engineering

### Input

- Loaded crime records
- Loaded population inputs
- Loaded OSM objects
- Weather context
- Community report signal
- Timestamp and location metadata

### Output

- ML-ready feature tables
- Crowd-oriented feature set
- Safety-oriented feature set

### Responsibility

- Convert raw and loaded source records into model-ready tabular features.
- Apply the feature transformations defined in [docs/feature_engineering.md](feature_engineering.md).
- Produce the schema-aligned features required by the crowd and safety datasets.

### Dependencies

- All source loaders and generators must have completed successfully.
- Feature definitions must match [docs/dataset_schema.md](dataset_schema.md).
- OSM-derived transformations must match [docs/osm_features.md](osm_features.md).

### Validation

- Validate required features are present.
- Validate numeric ranges, categorical vocabularies, and spatial consistency.
- Validate that crowd-oriented and safety-oriented outputs are distinguishable and traceable.
- Validate that no feature conflicts with the frozen schema contract.

## Label Generation

### Input

- Crowd feature set
- Safety feature set
- Approved label inputs from [docs/label_generation.md](label_generation.md)

### Output

- `crowd_score`
- `safety_score`

### Responsibility

- Generate supervised labels for the two SafeShe datasets.
- Keep labels aligned with the approved architecture specification.
- Produce bounded, comparable regression targets.

### Dependencies

- Feature engineering must be complete.
- Approved label inputs must be available.
- Label definitions must match [docs/label_generation.md](label_generation.md).

### Validation

- Validate that labels are numeric.
- Validate that labels are finite.
- Validate that labels remain within the approved 0–100 range.
- Validate that labels are not null in the final outputs.
- Validate that label inputs are restricted to the approved feature set.

## Dataset Validation

### Input

- Feature-enriched records
- Generated labels
- Schema contract from [docs/dataset_schema.md](dataset_schema.md)

### Output

- Validated dataset records ready for export
- Rejected or flagged records when validation fails

### Responsibility

- Enforce the final schema contract.
- Ensure data quality before the datasets are written.
- Protect downstream model training from malformed or out-of-range values.

### Dependencies

- Feature engineering must have produced the final candidate records.
- Label generation must have completed.
- Validation rules must match the frozen dataset schema.

### Validation

- Validate latitude and longitude bounds.
- Validate non-negative distance values.
- Validate population, crime, crowd, and safety score ranges.
- Validate categorical consistency.
- Validate required columns, types, and null constraints.
- Validate that the dataset version metadata matches the configured schema version.

## 3. Final Dataset Outputs

### `crowd_dataset.csv`

#### Input

- Validated crowd-oriented feature records
- Generated `crowd_score`

#### Output

- Export-ready crowd dataset

#### Responsibility

- Store the final supervised dataset used for crowd prediction.
- Preserve the crowd feature schema exactly as specified.

#### Dependencies

- Crime Loader
- Population Loader
- OSM Loader
- Weather Generator where applicable
- Community Report Generator where applicable
- Feature Engineering
- Label Generation
- Dataset Validation

#### Validation

- Must contain all required crowd columns.
- Must contain a valid `crowd_score` label.
- Must satisfy schema and type rules from [docs/dataset_schema.md](dataset_schema.md).

### `safety_dataset.csv`

#### Input

- Validated safety-oriented feature records
- Generated `safety_score`

#### Output

- Export-ready safety dataset

#### Responsibility

- Store the final supervised dataset used for safety prediction.
- Preserve the safety feature schema exactly as specified.

#### Dependencies

- Crime Loader
- Population Loader
- OSM Loader
- Weather Generator
- Community Report Generator
- Feature Engineering
- Label Generation
- Dataset Validation

#### Validation

- Must contain all required safety columns.
- Must contain a valid `safety_score` label.
- Must satisfy schema and type rules from [docs/dataset_schema.md](dataset_schema.md).

## 4. Cross-Stage Requirements

### Traceability

Every generated record should remain traceable back to its source inputs through the engineering pipeline.

### Reproducibility

The same input sources and configuration must produce the same engineered dataset version when run under the same snapshot conditions.

### Schema Alignment

The final datasets must remain aligned with the frozen schema, feature engineering, and label generation documents.

### Architecture Boundary

This document defines only the engineering contract.

- No stage implementation is described here.
- No code is included here.
- No preprocessing behavior is implemented here.
- No model training behavior is described here.
