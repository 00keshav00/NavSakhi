import hashlib
import logging
import math
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
from shapely.ops import substring

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import ROAD_SEGMENTS

@dataclass
class GeneratorConfig:
    """Configuration for the Road Segment Generator."""
    target_segment_length_m: float = 150.0
    min_segment_length_m: float = 100.0
    max_segment_length_m: float = 200.0
    epsg_metric: int = 3857  # Web Mercator for accurate meter-based length splitting
    epsg_wgs84: int = 4326   # Standard lat/lon for output
    output_path: Path = ROAD_SEGMENTS


class RoadSegmentGenerator:
    """
    Transforms continuous OSM road networks into discrete ML training samples (100-200m segments).
    
    This generator strictly follows the ML Architecture V2 specification:
    - Splits long ways deterministically.
    - Preserves topology and intersections (nodes are shared).
    - Computes accurate path distances and centroids.
    """
    
    def __init__(self, config: Optional[GeneratorConfig] = None):
        self.config = config or GeneratorConfig()
        
    def _generate_segment_id(self, way_id: Union[int, str], offset: int, u: Optional[int] = None, v: Optional[int] = None) -> str:
        """Generates a deterministic unique ID for the segment using SHA-256."""
        hash_input = f"{way_id}_{u}_{v}_{offset}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()[:16]
        
    def _generate_node_id(self, point: Point) -> int:
        """Generates a deterministic synthetic node ID based on 6-decimal coordinates."""
        hash_input = f"{point.y:.6f}_{point.x:.6f}".encode('utf-8')
        # Create a deterministic 64-bit signed integer
        return int(hashlib.md5(hash_input).hexdigest()[:15], 16) - (1 << 59)

    def process_file(self, osm_pbf_path: Union[str, Path]) -> gpd.GeoDataFrame:
        """
        Reads an OSM PBF file and processes its road network.
        
        Args:
            osm_pbf_path: Path to the raw OSM PBF file.
            
        Returns:
            A GeoDataFrame containing the split, standardized road segments.
        """
        try:
            from pyrosm import OSM
        except ImportError:
            logger.error("pyrosm is not installed. Required for parsing OSM PBF files.")
            raise

        logger.info(f"Loading OSM data from {osm_pbf_path}")
        osm = OSM(str(osm_pbf_path))
        
        # Extract drivable network. Pyrosm automatically cuts edges at intersections, 
        # naturally preserving topological junctions.
        nodes, edges = osm.get_network(network_type="driving", nodes=True)
        logger.info(f"Extracted {len(edges)} road edges from OSM graph.")
        
        return self.process_edges(edges)

    def process_edges(self, edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Splits road edges into ~150m ML-ready segments.
        
        Args:
            edges: GeoDataFrame of OSM edges.
            
        Returns:
            GeoDataFrame of the split segments.
        """
        logger.info("Projecting edges to metric CRS for accurate distance splitting...")
        # Project to a metric CRS (e.g., Web Mercator) for uniform distance calculation in meters
        edges_metric = edges.to_crs(epsg=self.config.epsg_metric)
        
        segments_data = []
        
        for idx, row in edges_metric.iterrows():
            way_id = row.get('id', row.get('osmid', 0))
            if isinstance(way_id, list):
                way_id = way_id[0]
                
            geom = row.geometry
            if not isinstance(geom, LineString) or geom.is_empty:
                continue
                
            length_m = geom.length
            
            road_type = row.get('highway', 'unknown')
            if isinstance(road_type, list):
                road_type = road_type[0]
                
            # Determine how many segments to split this edge into targeting ~150m per segment
            n_segments = max(1, math.ceil(length_m / self.config.target_segment_length_m))
            segment_length = length_m / n_segments
            
            # Original nodes defining the full edge (intersection to intersection)
            u = row.get('u', row.get('start_node', None))
            v = row.get('v', row.get('end_node', None))
            
            for i in range(n_segments):
                start_dist = i * segment_length
                end_dist = (i + 1) * segment_length
                if i == n_segments - 1:
                    end_dist = length_m  # Avoid float rounding issues at the terminal end
                    
                seg_geom = substring(geom, start_dist, end_dist)
                
                # To preserve continuous topology across synthetic splits, intermediate nodes get synthetic IDs
                start_node = u if i == 0 else None
                end_node = v if i == n_segments - 1 else None
                
                seg_id = self._generate_segment_id(way_id, i, u, v)
                
                seg_attrs = {
                    'segment_id': seg_id,
                    'way_id': way_id,
                    'start_node': start_node,
                    'end_node': end_node,
                    'length_m': seg_geom.length,
                    'road_type': road_type,
                    'geometry': seg_geom
                }
                
                # Preserve additional important tags (bridge, tunnel, oneway, etc.)
                for col in row.index:
                    if col not in ['geometry', 'u', 'v', 'id', 'osmid', 'length', 'highway']:
                        seg_attrs[col] = row[col]
                        
                segments_data.append(seg_attrs)
                
        logger.info(f"Split {len(edges)} original edges into {len(segments_data)} ML-ready segments.")
        
        # Create intermediate output GeoDataFrame
        segments_gdf = gpd.GeoDataFrame(segments_data, geometry='geometry', crs=f"EPSG:{self.config.epsg_metric}")
        
        # Compute exact centroids in projected CRS for mathematical correctness
        logger.info("Computing centroids and synthetic node topology...")
        centroids = segments_gdf.geometry.centroid
        centroids_wgs84 = centroids.to_crs(epsg=self.config.epsg_wgs84)
        segments_gdf['latitude'] = centroids_wgs84.y
        segments_gdf['longitude'] = centroids_wgs84.x

        # Project segments back to WGS84 for output and spatial joins
        logger.info("Projecting segments back to EPSG:4326...")
        segments_gdf = segments_gdf.to_crs(epsg=self.config.epsg_wgs84)
        
        # Resolve synthetic node IDs for continuous topology
        start_nodes = []
        end_nodes = []
        for geom, s_node, e_node in zip(segments_gdf.geometry, segments_gdf['start_node'], segments_gdf['end_node']):
            coords = list(geom.coords)
            start_pt = Point(coords[0])
            end_pt = Point(coords[-1])
            
            start_nodes.append(s_node if pd.notna(s_node) else self._generate_node_id(start_pt))
            end_nodes.append(e_node if pd.notna(e_node) else self._generate_node_id(end_pt))
            
        segments_gdf['start_node'] = start_nodes
        segments_gdf['end_node'] = end_nodes
        
        # --- Defensive Validation ---
        if segments_gdf["start_node"].isna().any():
            missing = int(segments_gdf["start_node"].isna().sum())
            raise ValueError(
                f"RoadSegmentGenerator validation failed: "
                f"{missing} segments still contain missing start_node values "
                "after topology generation."
            )

        if segments_gdf["end_node"].isna().any():
            missing = int(segments_gdf["end_node"].isna().sum())
            raise ValueError(
                f"RoadSegmentGenerator validation failed: "
                f"{missing} segments still contain missing end_node values "
                "after topology generation."
            )

        if segments_gdf["latitude"].isna().any():
            raise ValueError("Latitude contains missing values.")

        if segments_gdf["longitude"].isna().any():
            raise ValueError("Longitude contains missing values.")

        invalid = (~segments_gdf.geometry.is_valid).sum()
        if invalid:
            raise ValueError(
                f"{invalid} invalid geometries detected before export."
            )
        # ---------------------------
        
        # Ensure ID columns are strongly typed as 64-bit integers
        segments_gdf['start_node'] = segments_gdf['start_node'].astype('int64')
        segments_gdf['end_node'] = segments_gdf['end_node'].astype('int64')
        segments_gdf['way_id'] = segments_gdf['way_id'].astype('int64')
        
        return segments_gdf

    def build(self, osm_pbf_path: Union[str, Path]) -> None:
        """
        Executes the full generation pipeline and writes the output to a Parquet file.
        
        Args:
            osm_pbf_path: Path to the raw OSM PBF file.
        """
        import time
        start_time = time.time()
        logger.info(f"START: RoadSegmentGenerator | Output: {self.config.output_path}")
        segments_gdf = self.process_file(osm_pbf_path)
        
        # Ensure output directory exists
        out_path = Path(self.config.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Subset to the strictly required schema (plus any inherited tags like tunnel/bridge)
        # We drop the heavy geometry object as the centroid is the ML anchor.
        output_columns = ['segment_id', 'way_id', 'start_node', 'end_node', 
                          'latitude', 'longitude', 'length_m', 'road_type']
                          
        # Include preserved topological tags if they exist
        for optional_tag in ['bridge', 'tunnel', 'oneway', 'maxspeed', 'surface', 'lanes']:
            if optional_tag in segments_gdf.columns:
                output_columns.append(optional_tag)
                
        output_df = pd.DataFrame(segments_gdf[output_columns])
        
        output_df.to_parquet(out_path, index=False)
        duration = time.time() - start_time
        logger.info(f"COMPLETED: RoadSegmentGenerator | Duration: {duration:.2f}s | Processed Rows: {len(output_df)} | Output: {out_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the SafeShe Road Segment Generator")
    parser.add_argument("--pbf", type=str, required=True, help="Path to the input OSM PBF file")
    parser.add_argument("--out", type=str, help="Override default output Parquet path")
    args = parser.parse_args()
    
    config = GeneratorConfig()
    if args.out:
        config.output_path = Path(args.out)
        
    generator = RoadSegmentGenerator(config)
    generator.build(args.pbf)
