# Synthetic Generator Implementation Audit
**Date:** 2026-07-31
**Scope:** `ml/data_engineering/generators/synthetic_generator.py`

This document provides a comprehensive review of the Synthetic Generator's implementation against its architectural specification.

---

### 1. Architectural Compliance
**Status: Compliant**
- **Strictly Deterministic**: No random number generators (e.g., `np.random`) are utilized. Every score is mathematically generated via hardcoded equations leveraging the real-world contextual inputs.
- **Rule-Based & Validation Bound**: Heavily constrained rules govern the feature mapping (e.g., CCTV probabilities scale strictly with POIs). All outputs are constrained (`.clip(lower=0, upper=100)`) and heavily gated by strict validation logic (e.g., lighting max-capped in isolated rural zones, regardless of road type).
- **Confidence Scoring**: `synthetic_confidence` is correctly generated, actively degrading if foundational base features like population or commercial density are missing from the input vectors.
- **Independence**: It performs no Feature Engineering logic outside of calculating its mandated 6 columns and the confidence metric.

### 2. Assumptions
- **Proxy Use**: Since upstream Feature Engineering hasn't run yet, the generator leverages its own internal proxies for missing derived metrics. (e.g., utilizing a combination of low population and low commercial density as an internal `isolation_proxy`).
- **Junction Proxy**: Real junction tagging can be sparse in raw OSM. The generator gracefully falls back on `crossing > 0` as a temporary boolean proxy to estimate localized intersections if `junction` is entirely missing from the input dataset.
- **Crime Prior Isolation**: The generator correctly attempts to deduct risk via the `crime_score`. However, since district-level spatial joins happen downstream, it assumes a neutral `50.0` default prior if the exact crime dataset isn't fully mapped to the `segment_id` input matrix.

### 3. Limitations
- **Opaque Weights**: The weightings (e.g., `(bank_count * 30)`) are currently deterministic constants embedded in the `generate()` method. While they can be tweaked in code, they are not yet driven by a central, adjustable configuration manifest (like a JSON heuristic map).
- **Hard Memory Loads in Standalone Mode**: When executed via the CLI `build()` method, it eagerly left-joins all upstream Parquet datasets in Pandas at once. For a multi-million row dataset, this mega-join could temporarily spike RAM before writing out the slimmed-down synthetic features table.

### 4. Future Scalability
- **Vectorized Performance**: The entire `generate()` function relies purely on vectorized `numpy` and `pandas` operations (e.g., `np.where`, `pd.Series.clip`). It avoids all iterators/loops. This ensures it will process millions of road segments in seconds on a single CPU core.
- **Modular Pipeline Ready**: By decoupling the `generate(df: pd.DataFrame)` logic from the file I/O `build()` logic, the class is perfectly prepared to be ingested by a larger Airflow or Spark orchestration layer that passes pre-chunked or fully materialized dataframes directly into the function.
