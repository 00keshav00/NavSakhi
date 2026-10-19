import logging
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import POPULATION_RASTER, ROAD_SEGMENTS, POPULATION_FEATURES

@dataclass
class PopulationLoaderConfig:
    """Configuration for the Population Loader."""
    raster_path: Path = POPULATION_RASTER
    segments_path: Path = ROAD_SEGMENTS
    output_path: Path = POPULATION_FEATURES
    epsg_wgs84: int = 4326
    epsg_metric: int = 3857
    buffer_radius_m: float = 100.0


class PopulationLoader:
    """
    Extracts population features from high-resolution demographic rasters (e.g., WorldPop).
    Strictly implements the architecture defined in docs/population_loader_design.md.
    """
    def __init__(self, config: PopulationLoaderConfig):
        self.config = config

    def _create_stencil_offsets(self, radius_m: float) -> List[Tuple[float, float]]:
        """
        Creates a 5-point spatial stencil (center, N, S, E, W) to estimate
        buffered calculations without heavy raster masking.
        """
        r = radius_m / 2.0
        return [(0.0, 0.0), (0.0, r), (0.0, -r), (r, 0.0), (-r, 0.0)]

    def build(self) -> None:
        """
        Executes the raster extraction pipeline.
        """
        import time
        start_time = time.time()
        logger.info(f"START: PopulationLoader | Output: {self.config.output_path}")

        if not self.config.segments_path.exists():
            raise FileNotFoundError(f"Input segments not found at {self.config.segments_path}")
        if not self.config.segments_path.exists():
            raise FileNotFoundError(f"Road segments file not found: {self.config.segments_path}")

        logger.info(f"Loading road segment anchors from {self.config.segments_path}")
        df = pd.read_parquet(self.config.segments_path)

        # Convert to GeoDataFrame in WGS84
        gdf = gpd.GeoDataFrame(
            df[['segment_id', 'latitude', 'longitude']], 
            geometry=gpd.points_from_xy(df.longitude, df.latitude),
            crs=f"EPSG:{self.config.epsg_wgs84}"
        )

        logger.info("Projecting segments to metric CRS for spatial offset generation...")
        gdf_metric = gdf.to_crs(epsg=self.config.epsg_metric)

        offsets = self._create_stencil_offsets(self.config.buffer_radius_m)
        all_samples = []

        logger.info(f"Opening raster: {self.config.raster_path}")
        # Use rasterio to natively read the GeoTIFF without loading the entire array into memory
        with rasterio.open(self.config.raster_path) as src:
            raster_crs = src.crs
            nodata = src.nodata if src.nodata is not None else -9999.0
            
            logger.info(f"Raster CRS detected as {raster_crs}. Nodata value: {nodata}")

            # Vectorized multi-point sampling using a spatial stencil
            for idx, (dx, dy) in enumerate(offsets):
                logger.info(f"Executing spatial sample {idx+1}/{len(offsets)} at offset ({dx}m, {dy}m)...")
                
                # Fast vectorized geometric translation
                shifted_metric = gdf_metric.translate(xoff=dx, yoff=dy)
                
                # Project directly to the raster's native CRS to ensure perfect pixel alignment
                shifted_native = shifted_metric.to_crs(raster_crs)
                coords = [(geom.x, geom.y) for geom in shifted_native]
                
                # rasterio.sample queries the disk efficiently using GDAL's block cache
                samples = np.array([val[0] for val in src.sample(coords)])
                
                # Clean invalid values (nodata and physical impossibilities)
                samples = np.where(samples == nodata, 0.0, samples)
                samples = np.where(samples < 0, 0.0, samples)
                
                all_samples.append(samples)

        # Stack the 1D arrays into a 2D matrix (5, N)
        stacked_samples = np.vstack(all_samples)

        logger.info("Computing final population metrics...")
        
        # Central point (offset 0,0) represents the direct density at the segment centroid
        population_density = stacked_samples[0, :]
        
        # The 100m buffer estimate is derived by averaging the stencil and scaling by 
        # the approximate area ratio of a 100m circle (pi * r^2 / cell_area).
        # To maintain deterministic bounds and avoid over-inflation, we utilize the 
        # mean ambient density multiplied by a standard neighborhood scaling factor (approx 3.14 for 100m vs 100m cell).
        population_count_100m = np.mean(stacked_samples, axis=0) * 3.14

        # Compute ranking/percentile
        pop_series = pd.Series(population_density)
        population_percentile = pop_series.rank(pct=True).values.astype('float32')

        # Compute Indicators based on relative percentiles for cross-city robustness
        urban_indicator = (population_percentile >= 0.50)
        high_density_indicator = (population_percentile >= 0.90)
        low_density_indicator = (population_percentile <= 0.25)

        # Missing Coverage Strategy
        # If all points in the stencil returned 0/nodata, flag as missing coverage
        population_missing_coverage = np.all(stacked_samples == 0.0, axis=0)

        # Construct the final dataset
        output_df = pd.DataFrame({
            'segment_id': df['segment_id'],
            'population_density': population_density.astype('float32'),
            'population_count_100m': population_count_100m.astype('float32'),
            'population_percentile': population_percentile,
            'urban_indicator': urban_indicator,
            'high_density_indicator': high_density_indicator,
            'low_density_indicator': low_density_indicator,
            'population_missing_coverage': population_missing_coverage
        })

        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        output_df.to_parquet(self.config.output_path, index=False)
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: PopulationLoader | Duration: {duration:.2f}s | Processed Rows: {len(output_df)} | Output: {self.config.output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the SafeShe Population Loader")
    parser.add_argument("--raster", type=str, required=True, help="Path to WorldPop GeoTIFF")
    parser.add_argument("--segments", type=str, default="ml/datasets/processed/road_segments.parquet", help="Path to input road segments")
    parser.add_argument("--out", type=str, default="ml/datasets/processed/population_features.parquet", help="Output path")
    args = parser.parse_args()
    
    config = PopulationLoaderConfig(
        raster_path=Path(args.raster),
        segments_path=Path(args.segments),
        output_path=Path(args.out)
    )
    
    loader = PopulationLoader(config)
    loader.build()
