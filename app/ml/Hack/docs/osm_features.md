# SafeShe OpenStreetMap Feature Specification

This document defines the OpenStreetMap-derived features required for the SafeShe dataset engineering layer.

SafeShe uses OSM as a spatial feature source, not as a routing engine. The goal is to convert map objects around a user location and route corridor into ML-ready numeric features for the crowd and safety models.

## Design Principles

- Features should be derived from the user location or route segment using a consistent spatial query policy.
- Prefer stable, interpretable features over highly granular raw OSM object dumps.
- Convert OSM geometry into counts, distances, densities, and categorical road indicators.
- Keep OSM-derived features reproducible across offline dataset generation and runtime inference.

## Feature Groups

### 1. Safety Features

These features support the safety score model and are focused on nearby protective infrastructure, road environment, and perceived security context.

| Feature Name | OSM Tag | OSM Value | Description | Why it is useful | How it will be transformed into an ML feature |
|---|---|---|---|---|---|
| Distance to nearest police station | `amenity` | `police` | Distance from the user location or route point to the nearest police station. | Closer police presence often implies faster response and stronger deterrence. | Compute nearest-neighbor distance in meters, then normalize or scale to a bounded numeric safety feature. |
| Distance to nearest hospital | `amenity` | `hospital` | Distance to the closest hospital or major medical facility. | Important for emergency access and route risk assessment. | Compute nearest distance in meters and transform into an inverse-distance or standardized numeric feature. |
| Distance to nearest clinic | `amenity` | `clinic` | Distance to nearby healthcare facilities. | Adds resilience when hospitals are farther away. | Compute nearest distance and optionally aggregate with hospital distance into a health-access feature set. |
| Street lighting presence | `highway` / `lit` | `yes`, `no`, or missing | Whether roads in the local area are tagged as lit. | Well-lit roads are generally safer for walking. | Convert to a binary or proportion-of-lit-roads feature within the query radius. |
| Pedestrian crossing availability | `highway` | `crossing`, `traffic_signals`, `uncontrolled` | Presence and type of crossings near the route. | Better crossings reduce vulnerable pedestrian exposure. | Convert crossing count, crossing density, or a crossing-quality score. |
| Sidewalk availability | `sidewalk` | `left`, `right`, `both`, `no`, `separate` | Presence of sidewalks on nearby roads. | Sidewalks improve pedestrian safety and reduce exposure to vehicle traffic. | Encode as binary or ordinal sidewalk quality/coverage feature. |
| Road type risk | `highway` | `motorway`, `primary`, `secondary`, `tertiary`, `residential`, `service`, etc. | Type of road segments near the route. | Higher-class roads may be less comfortable or more dangerous for walking depending on context. | Map road class to a risk score and aggregate across nearby road segments or route segments. |
| Traffic calming presence | `traffic_calming` | `bump`, `hump`, `table`, `island`, etc. | Road calming devices near the route. | Often reduces vehicle speed and pedestrian risk. | Count nearby traffic calming assets and convert to a normalized safety-improving feature. |
| Speed limit proxy | `maxspeed` | numeric or textual speed value | Posted or tagged speed limits on road segments. | Higher speeds typically increase pedestrian risk. | Parse to numeric speed, then convert to a risk score or weighted average across route segments. |
| Public security POI proximity | `amenity` / `office` | `security`, `government`, `townhall`, `police` | Nearby institutional presence related to governance or security. | Can proxy for monitored or managed urban zones. | Use distance and count-based aggregation into a proximity or density feature. |
| Route corridor road exposure | `highway` | any traversed road class | Road composition around the actual travel path. | A route surrounded by major roads may have different risk than a residential route. | Aggregate road-type counts or weighted distances inside the route corridor. |

### 2. Crowd Features

These features support the crowd density model and are intended to estimate how busy a location is at a given time.

| Feature Name | OSM Tag | OSM Value | Description | Why it is useful | How it will be transformed into an ML feature |
|---|---|---|---|---|---|
| Restaurant count within radius | `amenity` | `restaurant` | Number of restaurants near the query point. | Restaurants are strong proxies for foot traffic and social activity. | Count POIs inside a radius such as 500m, then optionally density-normalize by area. |
| Cafe count within radius | `amenity` | `cafe` | Number of cafes nearby. | Cafes correlate with active pedestrian zones. | Count and normalize by radius area. |
| Fast food count within radius | `amenity` | `fast_food` | Number of fast-food outlets nearby. | Common proxy for commercial footfall. | Count and normalize into a commercial activity feature. |
| Bus stop count within radius | `highway` | `bus_stop` | Number of public transport stops nearby. | Transit stops create recurring crowd concentration. | Count stops within a fixed radius and transform into a density feature. |
| Metro / railway station count | `railway` | `station` | Number of metro, rail, or subway stations nearby. | Stations attract large and time-dependent crowds. | Count nearby stations and convert to a density or proximity-weighted feature. |
| Office density | `office` | any office subtype | Density of office POIs around the point. | Offices correlate with daytime crowd inflow. | Count office POIs and normalize by area to produce a density score. |
| Commercial POI density | `landuse` / `shop` / `office` / `amenity` | commercial-related values | Density of commercial activity around the point. | Commercial zones are usually more crowded. | Aggregate multiple commercial POI classes into a single density score. |
| School count | `amenity` | `school` | Number of schools nearby. | Schools strongly affect crowding during opening and closing hours. | Count nearby schools, optionally applying hour-based weighting. |
| College / university count | `amenity` | `college`, `university` | Number of higher-education facilities nearby. | Educational zones create predictable spikes in crowd density. | Count nearby institutions and convert into density or weighted activity feature. |
| Park count | `leisure` | `park` | Number of parks or open public spaces nearby. | Parks can create crowd clusters during weekends and evenings. | Count parks within the radius and convert to an amenity density signal. |
| Market / marketplace count | `amenity` / `shop` | `marketplace` or market-like POIs | Local market activity near the point. | Markets are strong crowd generators. | Count market-related POIs and convert to a weighted crowd intensity feature. |
| Population density | external census, spatially joined with OSM grid | not an OSM tag | Population pressure around the location. | High population density usually implies higher baseline crowding. | Join OSM location with census grid values and use as a normalized numeric feature. |
| Commercial area score | derived from OSM POIs and land use | aggregated | A computed score representing commercial intensity. | Commercial hubs are generally crowded even off-peak. | Build a weighted score from POI counts and land-use signals, then scale to a numeric feature. |

### 3. Road Features

These features describe the local road network and support both safety modeling and route interpretation.

| Feature Name | OSM Tag | OSM Value | Description | Why it is useful | How it will be transformed into an ML feature |
|---|---|---|---|---|---|
| Road type | `highway` | `motorway`, `primary`, `secondary`, `tertiary`, `residential`, `service`, `living_street`, `unclassified`, etc. | Classification of road segments in the area. | Road class is a strong signal for vehicle speed, pedestrian exposure, and route comfort. | Encode as ordinal risk, one-hot category, or weighted segment score. |
| Road hierarchy proximity | `highway` | various road classes | Distance to higher- and lower-order roads. | Proximity to high-speed roads can increase perceived danger. | Compute distance-weighted road hierarchy features. |
| Intersection density | `highway` + network topology | road graph structure | Number of intersections around the point or corridor. | Dense intersections can indicate active, mixed-use areas and more crossing complexity. | Count intersections in the query area and convert to density. |
| Junction complexity | `junction` | `roundabout`, `intersection`, `circular` | Type of junctions near the route. | Complex junctions can affect pedestrian safety and route ease. | Encode the dominant junction type or use a complexity score. |
| Road surface quality | `surface` | `asphalt`, `paved`, `gravel`, `unpaved`, etc. | Surface material of nearby roads. | Surface quality affects walkability and accessibility. | Convert surface to a categorical risk or comfort score. |
| Road lighting | `lit` | `yes`, `no`, missing | Whether road segments are lit. | A critical safety signal for night travel. | Convert to a binary feature or ratio of lit road length in the area. |
| Foot access | `foot` | `yes`, `designated`, `no`, `private` | Whether pedestrians are allowed or intended on the road. | Helps identify unsuitable walking segments. | Encode as accessibility score for walkability. |
| Sidewalk presence | `sidewalk` | `left`, `right`, `both`, `no`, `separate` | Sidewalk coverage on each segment. | Higher sidewalk coverage improves pedestrian safety. | Translate to binary or ordinal sidewalk coverage feature. |
| Max speed | `maxspeed` | numeric or textual | Posted speed limit on the road. | Speed is a key risk factor for pedestrian exposure. | Parse to numeric and convert to risk intensity. |
| One-way restriction | `oneway` | `yes`, `no`, `-1` | Directionality of the road. | Can affect routing complexity and nearby traffic flow. | Encode as binary or directional road feature. |

## Static vs Runtime Features

### Static Features

These are generally stable and can be precomputed or refreshed on a slow schedule.

- Restaurant count
- Bus stop count
- Metro count
- Office density
- Commercial density
- Population density
- Crime score
- Lighting score
- Police distance
- Hospital distance
- Road type
- Sidewalk presence
- Max speed
- Intersection density
- Junction complexity
- Foot access
- One-way restriction

### Runtime Features

These must be updated at request time or near-request time because they depend on time, route, or live conditions.

- Hour
- Day of week
- Weather
- Crowd score
- Community reports
- Walking distance
- Transport mode
- Time weight
- Route corridor road exposure
- Route-specific lighting or road-type aggregation

## Recommended Extraction Radius

The extraction radius should be feature-specific rather than universal.

- Immediate pedestrian safety context: 100m to 250m
- Local crowd activity context: 300m to 750m
- Commercial and transit context: 500m to 1000m
- Broader population or mixed-land-use context: 1000m to 1500m

Recommended defaults:

- Crowd features: 500m radius for POI counts, 1000m for transit hubs if needed
- Safety features: 250m to 500m radius for police, hospital, lighting, sidewalk, and road context
- Road features: route corridor aggregation rather than a point-only radius when possible

## Assumptions

- OSM data is assumed to be available through a local extract, Overpass, OSMnx graph, or a cached tile/graph service.
- Tags may be missing or inconsistent across regions, so fallback logic is required for absent values.
- Some OSM properties are incomplete in many geographies, especially `lit`, `sidewalk`, `maxspeed`, and `surface`.
- Count-based POI features are assumed to be more stable than exact distance features for crowded urban areas.
- Distances should be measured in meters after projecting coordinates into an appropriate metric CRS.
- When multiple OSM objects satisfy the same feature, the nearest distance or aggregated count should be used consistently.
- The same extraction policy must be used during dataset generation and runtime inference to avoid train-inference skew.
- Safety and crowd scores are generated labels, not direct OSM tags, and should be derived from the transformed OSM feature set plus other non-OSM sources.

## Notes for Dataset Engineering

- Keep OSM-derived features in numeric form whenever possible.
- Use counts for density-heavy urban indicators and distances for sparse infrastructure signals.
- When both count and distance are available for the same concept, prefer count for crowd modeling and distance for safety modeling.
- Aggregate features by route segment when building safety datasets so the model can learn route-level risk rather than only point-level risk.
- Document the exact extraction radius used for each generated dataset version to preserve reproducibility.
