# Safety Data Integration Requirements

## Purpose
SafeShe models multimodal mobility risk using objective physical and environmental datasets. We evaluate safety across temporal (night-time exposure), spatial (isolation), and topological (infrastructure quality) dimensions. We are actively seeking partnerships with civic authorities and urban safety organizations to rigorously elevate our predictive Machine Learning pipeline.

## Required Aggregation & Privacy (CRITICAL)
- SafeShe enforces strict privacy invariants. **We DO NOT ingest, process, or store unanonymized victim data or personally identifying information (PII).**
- All safety and crime incident data MUST be aggregated both spatially (e.g., hexagonal grid grids, ward-level vectors) and temporally (e.g., month/year buckets, time-of-day ratios).

## Required Fields and Features
We request aggregated datasets featuring:
1. **Spatial Resolution**: Minimum resolution of a 500m x 500m H3 Hexagon or standard municipal ward boundaries.
2. **Temporal Resolution**: Separation of incidents by time-of-day (e.g., Daytime vs. Nighttime), to allow the ML model to accurately dynamically re-score routes at 23:00 vs 14:00.
3. **Incident Typology**: Categorical mapping of risk indicators (e.g., harassment complaints, lighting outages, pedestrian accidents, severe infrastructural hazards).
4. **Historical Period**: A minimum 2-year lookback to smooth statistical outliers and prevent anomaly-driven route distortion.

## Quality and Frequency
- **Update Frequency**: Minimum quarterly publication to prevent model drift.
- **Source Authority**: Only Tier-1 (Official Police / Govt) or Tier-2 (Verified Safety Institutions) sources will be permitted into the ML feature pipeline. Unverified community/crowdsourced models require severe filtering and separate "Community" tagging.
