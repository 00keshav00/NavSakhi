# OSM Loader Design Specification

This document specifies the architectural design for the OpenStreetMap (OSM) Loader within the SafeShe Dataset Engineering pipeline.

This is an architecture specification only. No implementation code is included.

---

## 1. Purpose

The OSM Loader is responsible for parsing raw OpenStreetMap data and transforming it into the structured spatial features required by SafeShe's ML Architecture V2. It extracts physical road attributes and surrounding Points of Interest (POIs) and spatially maps them to pre-defined road segments.

---

## 2. Inputs

The OSM Loader consumes the following inputs:

- **OSM PBF Files**: Highly compressed binary dumps of OpenStreetMap data (e.g., regional or state-level extracts). Used for heavy, offline, and production-scale extraction.
- **OSM API (Overpass)**: Live query endpoints used primarily for lightweight testing, localized prototyping, or dynamic fetching when a PBF is unavailable.
- **Administrative Boundaries**: Spatial polygons (GeoJSON/Shapefiles) used to crop the OSM data to the exact region of interest, significantly reducing memory overhead.
- **Road Segments**: The anchor dataset produced by the Road Segment Generator, providing the `segment_id`, `latitude`, and `longitude` against which all OSM features will be mapped.

---

## 3. Extraction Pipeline

The loader executes a strict multi-step pipeline:

1. **Load OSM**: Parse the raw PBF file or API response into memory.
2. **Extract Roads**: Filter the geometries for drivable, walkable, and cyclable paths (ignoring unroutable geometries like power lines).
3. **Extract POIs**: Filter nodes, ways, and relations that represent amenities, shops, tourism spots, and leisure areas. Polygons are reduced to their centroids.
4. **Extract Intersections**: Identify topological intersections by finding nodes shared by multiple distinct highway ways.
5. **Extract Road Tags**: Parse attributes bound directly to the road geometries (e.g., speed limits, surface types).
6. **Spatial Indexing**: Construct R-trees over the extracted roads and POIs to enable sub-millisecond spatial queries.
7. **Feature Generation**: Iterate over the input Road Segments, casting spatial buffers and calculating distances/counts against the R-tree indexes.
8. **Output Datasets**: Write the generated features to disk as structured, columnar datasets.

---

## 4. Road Features

Road features are intrinsic properties of the road segment itself. Extraction logic:

- **road_type**: Extracted from the `highway` tag (e.g., `residential`, `primary`, `trunk`).
- **lanes**: Extracted from the `lanes` tag, cast to an integer.
- **sidewalk**: Extracted from the `sidewalk` tag (e.g., `both`, `right`, `left`, `no`).
- **crossing**: Extracted by finding nodes tagged `highway=crossing` that intersect the segment.
- **junction**: Extracted from `junction=roundabout` or derived topologically.
- **bridge**: Extracted from `bridge=yes`.
- **tunnel**: Extracted from `tunnel=yes`.
- **surface**: Extracted from `surface` (e.g., `asphalt`, `unpaved`).
- **width**: Extracted from `width`, cast to a float representing meters.
- **speed**: Extracted from `maxspeed`, stripped of non-numeric characters and cast to a float (km/h).
- **curvature**: Derived mathematically by calculating `(true_path_length / straight_line_euclidean_distance)` of the segment geometry.

---

## 5. POI Features

POI features describe the environment surrounding the road segment. Extraction logic:

- **Police**: Extracted from `amenity=police`. Used for distance calculations.
- **Hospital**: Extracted from `amenity=hospital` or `amenity=clinic`. Used for distance calculations.
- **School**: Extracted from `amenity=school`. Used for count buffers.
- **College**: Extracted from `amenity=college` or `amenity=university`.
- **Restaurant**: Extracted from `amenity=restaurant`.
- **Cafe**: Extracted from `amenity=cafe`.
- **Bank**: Extracted from `amenity=bank`.
- **ATM**: Extracted from `amenity=atm`.
- **Mall**: Extracted from `shop=mall`.
- **Hotel**: Extracted from `tourism=hotel`.
- **Fuel**: Extracted from `amenity=fuel`.
- **Bus Stop**: Extracted from `highway=bus_stop` or `public_transport=stop_position`.
- **Metro**: Extracted from `railway=station`.
- **Park**: Extracted from `leisure=park`.
- **Pharmacy**: Extracted from `amenity=pharmacy`.
- **Commercial Density**: Extracted by aggregating all `shop=*`, `amenity=restaurant/cafe/bar`, and `landuse=commercial` tags, normalizing the count by the buffer area.

---

## 6. Spatial Queries

Features are assigned to road segments by querying the space around the segment centroid. Different features require different catchment radii based on human mobility and visibility.

- **20m Radius**: Used for immediate physical properties (e.g., *Crossings*, *Junctions*). Captures features physically touching or immediately adjacent to the segment.
- **50m Radius**: Used for immediate visibility and micro-access (e.g., *ATMs*, *Bus Stops*). Represents what a person can clearly see and reach in seconds.
- **100m Radius**: Used for local walking distance and foot-traffic magnets (e.g., *Restaurants*, *Cafes*). Represents the immediate vibrant block.
- **250m Radius**: Used for neighborhood footprint (e.g., *Parks*, *Malls*, *Schools*, *Commercial Density*). Captures the broader activity zone that influences ambient crowd levels.
- **500m Radius**: Used for broad accessibility (e.g., nearest *Police*, *Hospital*, *Metro* station). A 500m radius covers a standard 5-minute walking distance for critical infrastructure.

---

## 7. Performance

Because OSM data is massive and spatial joins are computationally expensive, the loader relies on strict performance mechanisms:

- **R-tree**: Bounding-box spatial indexes are mandatory for all POI and road layers to avoid O(N^2) Cartesian distance checks.
- **GeoPandas**: Utilized for vectorized spatial operations, ensuring that point-in-polygon and buffer queries are highly optimized.
- **Pyrosm**: Selected for its C-based parsing speed, reading PBF files directly into GeoDataFrames exponentially faster than pure Python XML parsers.
- **Shapely**: Powers the low-level geometric computations (buffers, distance metrics, curvature).
- **Caching**: Intermediate extractions (e.g., raw POI dataframes) are serialized to disk to prevent re-parsing the heavy PBF file on every pipeline run.
- **Parallel Processing**: The millions of input road segments are chunked. Spatial buffer joins are executed concurrently using multiprocessing pools, saturating CPU cores.

---

## 8. Output

The OSM Loader outputs strictly formatted tabular datasets:

1. **`osm_road_features.parquet`**: Contains segment-level intrinsic features (`segment_id`, `road_type`, `speed`, `lanes`, `surface`, etc.).
2. **`osm_poi_features.parquet`**: Contains bounded count features (`segment_id`, `restaurant_count_100m`, `bus_stop_count_50m`, `commercial_density_250m`, etc.).
3. **`osm_distance_features.parquet`**: Contains distance metrics (`segment_id`, `police_dist_m`, `hospital_dist_m`).

### Integration with Feature Engineering
These datasets serve as intermediate artifacts. The central **Feature Engineering** module consumes them by performing a series of simple, fast `LEFT JOIN` operations on `segment_id`. By keeping OSM processing separate from Feature Engineering, the pipeline remains modular, testable, and highly scalable.
