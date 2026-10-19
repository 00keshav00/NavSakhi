# Label Generation V2

This document defines the architectural strategy for generating the target labels (`safety_score` and `crowd_score`) in the SafeShe ML Pipeline V2. 

This is an architecture specification only. No implementation code is included.

---

## 1. Purpose

In supervised machine learning, models require target labels to learn from. Because raw, objective, localized safety metrics do not exist natively at the road-segment level, SafeShe must deterministically synthesize these labels during the prototyping phase, before transitioning to a fully supervised real-world feedback loop.

---

## 2. Target Labels

The platform utilizes two distinct regression targets.

### 2.1 `safety_score`
- **Meaning**: The estimated immediate physical and psychological safety of traversing a specific road segment at a specific time.
- **Range**: `0 to 100`
- **Interpretation**: Higher values indicate safer travel conditions. A score of 0 represents an extremely hostile or high-risk environment. A score of 100 represents an impeccably lit, secure, and comfortable environment. Used directly for safe routing and navigation algorithms.

### 2.2 `crowd_score`
- **Meaning**: The estimated density of pedestrian foot traffic and ambient human activity on a road segment at a specific time.
- **Range**: `0 to 100`
- **Interpretation**: Higher values indicate higher density. A score of 0 means the road is desolate. A score of 100 implies a bustling market or busy transit hub. It is used both as an independent metric for users and as a critical input feature for the `safety_score` (i.e., "eyes on the street" principle).

---

## 3. Label Inputs

The target labels are derived from the structured ML Feature Catalog.

| Feature Category | Contribution to `safety_score` | Contribution to `crowd_score` |
|---|---|---|
| **Background Priors** | Defines the baseline intercept (`crime_score`). | Negligible impact. |
| **Road Features** | Infrastructure quality (sidewalks, crossings, speed limit). | Wide roads and pedestrian crossings support higher capacity. |
| **POIs** | Security (`police_dist`), late-night anchors (Hospitals, ATMs). | Activity magnets (Restaurants, Malls, Metro stations). |
| **Population** | Contextualizes baseline risk and isolation. | Primary baseline for neighborhood density. |
| **Environmental** | Poor weather drops safety (low visibility, slipping risk). | Severe weather drops crowd expectations significantly. |
| **Temporal** | Modulates all other features (day vs night). | Modulates POI activity (rush hour vs 3 AM). |
| **Synthetic Features** | Strong drivers (Lighting, CCTV, Road Maintenance). | Night Activity drives the late-night crowd estimate. |
| **Community Features**| Direct crowd-sourced safety modifiers. | Event reports or localized gatherings. |

---

## 4. Initial Label Strategy

During the prototype phase, labels are generated deterministically to bootstrap the ML model. The model learns to predict the output of our expert heuristic engine.

- **Deterministic Scoring**: Labels are generated using a mathematical, rule-based formula (e.g., a weighted sum and non-linear penalties) rather than manual human annotation.
- **Rule-Based Weighting**: Domain expertise dictates the weights. For example:
  - High `crime_score` lowers the initial safety baseline.
  - Presence of `synth_lighting` strongly boosts safety during `night_flag=True`.
  - High `isolation_index` heavily penalizes safety.
- **Confidence Levels**: Each generated label carries a hidden confidence score based on the ratio of real data to synthetic data. A segment relying purely on synthetic lighting and inferred road types has lower label confidence than a segment with verified municipal data.

---

## 5. Future Evolution

The deterministic labels are a temporary scaffolding. The long-term architecture transitions from engineered labels to real-world supervised labels.

As the platform launches, the deterministic labels will be gradually replaced and fine-tuned by:
1. **User Reports**: Users actively tapping "I felt unsafe here" or "This street is completely dark" in the app.
2. **Incident Data**: Integration of verified emergency calls, police reports, or local news geolocations.
3. **GPS Traces**: Passive telemetry analysis. If the routing engine suggests a fast, dark shortcut, but 95% of users deviate to take a longer, well-lit main road, the platform implicitly learns to drop the safety label of the avoided shortcut.
4. **Community Feedback**: Upvotes/downvotes on proposed safe routes.

Once real-world data reaches critical mass, the ML model transitions from mimicking the heuristic engine to predicting actual human safety sentiment.

---

## 6. Validation

Before any generated labels are passed to the Model Training module, they must pass strict dataset validation.

### Sanity Checks
- **Boundary Checks**: No score can drop below 0 or exceed 100.
- **Logical Checks**: A desolate road segment (`crowd_score` < 10) in a high-risk district (`crime_score` > 80) without lighting MUST yield a strictly low `safety_score`.
- **Distribution Checks**: The Dataset Builder analyzes the bell curve of the generated scores to ensure the labels are well-distributed (not heavily skewed to exactly 50 or clustering at boundaries).

### Versioning
Every label generation heuristic is strictly versioned (e.g., `label_v2.1.0`). If the weighting rules change, the version increments, ensuring that ML performance regressions can be traced directly back to the label formula.
