# SafeShe Data Acceptance Checklist

Before any external dataset can be queried by the SafeShe engine, it must strictly pass through this sequential validation pipeline. Do NOT activate a dataset merely because the file was received.

## Pipeline Gates

### 1. Ingestion & Provenance
- [ ] **Raw Data Preserved**: Dataset saved in its original format to `data/raw/` without modification.
- [ ] **Dataset Versioned**: Assigned a unique `dataset_version` and `ingestion_timestamp`.
- [ ] **Source Authenticated**: Verification that the data arrived from the documented authoritative partner.

### 2. Legal & Authorization
- [ ] **License Check**: Explicit confirmation that the data license permits usage in SafeShe.
- [ ] **Authorization Check**: No undocumented restrictions prohibit API exposure or ML inference.

### 3. Structural Validation
- [ ] **Schema Validation**: Matches required CSV/JSON/GeoJSON format. Missing or malformed columns result in rejection.
- [ ] **Coordinate Validation**: All lat/lon values fall within the SafeShe operational bounding box (Chennai/TN).
- [ ] **Duplicate Check**: Duplicate nodes, routes, or trips isolated and merged/flagged.

### 4. Semantic Validation
- [ ] **Service Consistency**: Stop sequences in trips correspond to existing physical stops.
- [ ] **Coverage Check**: Assess spatial resolution against expected gaps.
- [ ] **Freshness Check**: `last_updated` complies with the Data Registry's `freshness_policy`.

### 5. Deployment
- [ ] **Normalization**: Parsed data transferred to `data/normalized/`.
- [ ] **Indexing**: Spatial (KD-Tree) and ID-based indexes built in `data/indexed/`.
- [ ] **E2E Testing**: Relevant test matrices (e.g., `DATA-01` to `DATA-15`, `BUS-01` to `BUS-20`) pass locally.
- [ ] **Production Activation**: Registry status upgraded to `ACTIVE`.
