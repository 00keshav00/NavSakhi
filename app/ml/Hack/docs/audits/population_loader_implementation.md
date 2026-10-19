# Population Loader Implementation Audit
**Date:** 2026-07-31
**Scope:** `ml/data_engineering/loaders/population_loader.py`

This document provides a comprehensive review of the Population Loader's implementation against its architectural specification.

---

### 1. Architectural Compliance
**Status: Compliant**
- **Inputs**: The module successfully dynamically reads the WorldPop GeoTIFF and the `road_segments.parquet` centroids.
- **Outputs**: It successfully generates a standard Parquet file (`population_features.parquet`) strictly containing `segment_id`, `population_density`, and `population_count_100m`.
- **Vectorized & Low Memory Extraction**: Adhering strictly to constraints, it does NOT load the heavy raster into memory or rely on slow iterative masking. It employs highly vectorized geometric translations (via GeoPandas) combined with `rasterio.sample` to stream pixel reads directly from GDAL's block cache.
- **NoData Handling**: Explicit array masking sweeps nodata (-9999.0) and biologically impossible negative values to 0.0.

### 2. Assumptions
- **Raster Value Meaning**: Assumes the provided raster encodes absolute population count per pixel (standard WorldPop demographic methodology). Therefore, `population_density` simply reflects the population residing in the exact pixel spanning the centroid.
- **Buffer Geometry**: Assumes a 100m radius can be reliably estimated via a 5-point symmetric spatial stencil (Center, North, South, East, West) offset at 50m intervals, rather than doing an expensive precise raster cell count intersection over an explicit polygon.
- **Scaling Factor**: Assumes the average of the 5 stencil points accurately represents the surrounding ambient demographic footprint, which is then scaled (x 3.14) to approximate the total count within the 100m radius area.

### 3. Limitations
- **Resolution Coupling**: The accuracy of the 100m buffer estimate is highly coupled to the resolution of the input raster. If a low-resolution 1km raster is passed in, the 50m offsets will repeatedly hit the exact same pixel, neutralizing the buffer intent and resulting in the density and count being purely scaled versions of each other.
- **Edge Conditions**: If a road segment runs exactly along the coastline or an international boundary, some of the 5 offset sample points may fall off the edge of the raster's valid domain, which defaults to 0, marginally under-reporting the buffer count.

### 4. Future Scalability
- **Excellent Profile**: Because `rasterio.sample` uses disk-level pointers rather than loading arrays, the memory footprint remains exceedingly low and fundamentally constant, regardless of whether the input GeoTIFF covers a single city (5 MB) or the entire globe (50 GB). 
- **Chunking (Phase 2)**: For national-level processing (>50M segments), the current GeoPandas projection operations will max out RAM. A simple iteration wrapper to chunk the input DataFrame in batches of 1,000,000 rows would allow infinite horizontal scaling with no change to the core algorithm.
