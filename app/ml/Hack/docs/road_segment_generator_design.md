# Road Segment Generator Design

This document specifies the architectural design for the Road Segment Generator within the SafeShe Dataset Engineering pipeline.

This is an architecture specification only. No implementation code is included.

---

## 1. Purpose

The Road Segment Generator is responsible for transforming raw OpenStreetMap (OSM) road networks into discrete, standardized Machine Learning training samples. It bridges the gap between continuous geographic polylines and tabular ML architectures.

---

## 2. Objectives

### Why Road Segments are the Prediction Unit
A user's journey is a sequence of roads, not a single point or a vast polygon. By making the road segment the fundamental unit of prediction, the ML model evaluates the exact environment the user traverses.

### Why 100–200 Meter Segments
- **Shorter than 100m**: Creates excessive noise, inflates the dataset size unnecessarily, and makes POI attribution erratic.
- **Longer than 200m**: Dilutes critical micro-features. A 500m road may start in a well-lit commercial zone and end in a dark, isolated residential zone.
- **100–200m**: The optimal sweet spot. It captures meaningful changes in infrastructure (lighting, sidewalks, CCTV) and local activity while maintaining a manageable dataset size.

### Advantages over District-Level Prediction
District-level prediction assumes uniform risk across massive areas, treating bustling main streets and dark alleys as identically risky. Road segments allow the model to isolate high-risk bottlenecks and propose safe routing alternatives *within* the exact same district.

---

## 3. Inputs

The generator requires the following inputs to produce the segments:

- **OSM Road Network**: The raw geometries of drivable, walkable, and cyclable paths.
- **OSM Way IDs**: The parent structural identifiers for continuous roads.
- **OSM Node IDs**: The foundational geographic points forming the ways.
- **Administrative Boundaries**: Spatial polygons used to map segments to their parent district or commissionerate.
- **Optional Elevation**: Topographic data to assess the slope or verticality of the segment.
- **Optional Traffic**: Historical or live speed metrics to gauge road activity.

---

## 4. Segmentation Algorithm

The algorithm must deterministically discretize the chaotic OSM road network.

- **Long OSM ways**: Ways exceeding 200m are mathematically split along their polyline into chunks targeting ~150m. For example, a 400m road is divided evenly into three ~133m segments.
- **Intersections**: Nodes shared by multiple intersecting ways act as natural hard-split points, ensuring segments do not cross through major junctions improperly.
- **Curved roads**: The algorithm follows the exact polyline geometry (node by node) to compute true path distance, rather than straight-line (Euclidean) distance, splitting the curve accurately.
- **Very short roads**: Ways natively shorter than 100m (e.g., connecting alleys, slip roads) are preserved as single segments to maintain topological accuracy without being arbitrarily merged.
- **Dead ends**: The terminal node of a dead-end street acts as a hard boundary, cleanly terminating the segment.
- **Bridges and tunnels**: Split just like standard roads, but their specific OSM vertical tags (`bridge=yes`, `tunnel=yes`, `layer`) are preserved to inform the ML model of the isolated environment.
- **Length Consistency**: The splitting math guarantees that segments derived from a single long way have roughly equal lengths, preventing anomalous 5-meter remainder fragments.

---

## 5. Segment Schema

Every generated road segment adheres to the following core schema:

| Column Name | Data Type | Description |
|---|---|---|
| `segment_id` | `string` | Deterministic hash (e.g., `way_id_offset`) ensuring uniqueness and reproducibility. |
| `way_id` | `int64` | The original parent OSM way identifier. |
| `start_node` | `int64` | The OSM node ID at the beginning of the segment. |
| `end_node` | `int64` | The OSM node ID at the end of the segment. |
| `latitude` | `float32` | The geographic centroid of the segment. |
| `longitude` | `float32` | The geographic centroid of the segment. |
| `length_m` | `float32` | The exact calculated path distance of the segment in meters. |
| `road_type` | `string` | Canonical OSM highway classification (e.g., `primary`, `residential`). |
| `district` | `string` | The parent revenue district, determined via spatial join. |
| `commissionerate` | `string` | The parent commissionerate (if applicable), determined via spatial join. |

---

## 6. Spatial Relationships

The segment centroid (`latitude`, `longitude`) acts as the anchor for all downstream spatial joins:

- **Crime**: Mapped via the `district` and `commissionerate` columns to attach the macro-level background prior.
- **Population**: Extracted via a raster-point lookup on the WorldPop GeoTIFF using the segment's centroid.
- **OSM POIs**: Extracted by casting a spatial buffer (e.g., 50m radius) around the segment to count nearby restaurants, transit stops, and hospitals.
- **Weather**: Applied to the segment based on the regional weather grid at the time of the dataset snapshot.
- **Synthetic Features**: Simulated directly for the segment based on its `road_type` and surrounding POI density.
- **Community Reports**: Matched by finding reports that fall within a defined radius of the segment centroid.

---

## 7. Output

**Output Dataset**: A tabular dataset (CSV or Parquet) containing millions of rows, where each row represents a single discrete road segment and its associated schema attributes.

**Role in Feature Engineering**: 
This output becomes the foundational "Left Table" of the dataset builder. It is passed to the Feature Engineering module, which executes sequential left-joins to attach outputs from the Crime Loader, OSM Loader, Population Loader, and Synthetic Generators onto each segment.

---

## 8. Future Scalability

The generator design is inherently scale-agnostic:

- **Other Cities / Whole States**: Because the algorithm relies purely on global OpenStreetMap topology and standard geospatial math, scaling up simply requires running the generator over a larger OSM bounding box (e.g., a state-level `.osm.pbf` file).
- **Entire India**: Processing the entire country is achievable without architectural redesign. It only requires distributed computing (e.g., Apache Spark or Dask) to partition the national OSM network and process the segmentation map-reduce style in parallel, outputting a nationwide road-segment database.
