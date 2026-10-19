import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import pandas as pd
import geopandas as gpd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import OSM_PBF_FILE, ROAD_SEGMENTS, PROCESSED_DATASETS_DIR

@dataclass
class OSMLoaderConfig:
    """Configuration for the OSM Loader."""
    pbf_path: Path = OSM_PBF_FILE
    segments_path: Path = ROAD_SEGMENTS
    output_dir: Path = PROCESSED_DATASETS_DIR
    epsg_metric: int = 3857  # For accurate buffering and distance calculations
    epsg_wgs84: int = 4326
    
    # Configurable spatial radii
    radius_crossing_m: float = 20.0
    radius_transit_m: float = 50.0
    radius_local_m: float = 100.0
    radius_neighborhood_m: float = 250.0
    radius_broad_m: float = 500.0
    
    max_distance_fallback_m: float = 25000.0
    commercial_area_sqkm: float = 0.196  # area of 250m circle

class OSMLoader:
    """
    Extracts spatial features from OpenStreetMap and maps them to standard road segments.
    Strictly implements the architecture defined in docs/osm_loader_design.md.
    """
    def __init__(self, config: OSMLoaderConfig):
        self.config = config
        
    def _extract_poi_subset(self, pois: gpd.GeoDataFrame, key: str, value: Any) -> gpd.GeoDataFrame:
        """Helper to safely filter POIs by tag without raising KeyError if tag missing."""
        if key not in pois.columns:
            return gpd.GeoDataFrame(columns=pois.columns, geometry='geometry', crs=pois.crs)
        if isinstance(value, list):
            subset = pois[pois[key].isin(value)]
        else:
            subset = pois[pois[key] == value]
        return subset

    def _compute_distance(self, segments: gpd.GeoDataFrame, poi_subset: gpd.GeoDataFrame, dist_col_name: str) -> pd.DataFrame:
        """Computes nearest-neighbor distance from segments to POIs utilizing spatial indexing (R-tree)."""
        max_dist = self.config.max_distance_fallback_m
        
        if poi_subset.empty:
            return pd.DataFrame({'segment_id': pd.Series(dtype='object'), dist_col_name: pd.Series(dtype='float32')}).set_index('segment_id')
            
        # sjoin_nearest leverages R-trees for highly optimized N-nearest queries
        joined = segments.sjoin_nearest(poi_subset, distance_col=dist_col_name, how='left')
        
        # Aggregate to minimum distance in case a segment ID has multiple geometries or equidistant POIs
        min_dists = joined.groupby('segment_id')[dist_col_name].min().reset_index()
        
        df = min_dists.copy()
        df[dist_col_name] = df[dist_col_name].fillna(max_dist).astype('float32')
        # Cap at maximum reasonable distance
        df[dist_col_name] = df[dist_col_name].clip(upper=max_dist)
        return df.set_index('segment_id')

    def _compute_count(self, segments_buffered: gpd.GeoDataFrame, poi_subset: gpd.GeoDataFrame, count_col_name: str) -> pd.DataFrame:
        """Computes POI count within a pre-computed buffered geometry utilizing R-tree spatial joins."""
        if poi_subset.empty:
            return pd.DataFrame({'segment_id': pd.Series(dtype='object'), count_col_name: pd.Series(dtype='int32')}).set_index('segment_id')
            
        # Spatial join utilizing GeoPandas vectorized intersection
        joined = gpd.sjoin(segments_buffered, poi_subset, how='inner', predicate='intersects')
        counts = joined.groupby('segment_id').size().reset_index(name=count_col_name)
        
        counts[count_col_name] = counts[count_col_name].astype('int32')
        return counts.set_index('segment_id')

    def build(self) -> None:
        """
        Executes the full OSM extraction pipeline: Loads PBF, extracts tags/POIs, 
        builds spatial indexes, executes queries, and exports 3 Parquet files.
        """
        import time
        start_time = time.time()
        logger.info(f"START: OSMLoader | Output: {self.config.output_dir}")
        try:
            from pyrosm import OSM
        except ImportError:
            logger.error("pyrosm is not installed. Required for parsing OSM PBF files.")
            raise

        if not self.config.segments_path.exists():
            raise FileNotFoundError(f"Required input segments not found at {self.config.segments_path}")

        # 1. Load Anchor Road Segments
        logger.info(f"Loading road segments from {self.config.segments_path}")
        segments_df = pd.read_parquet(self.config.segments_path)
        
        # Convert tabular segments to GeoDataFrame (Points at centroid)
        segments_gdf = gpd.GeoDataFrame(
            segments_df, 
            geometry=gpd.points_from_xy(segments_df.longitude, segments_df.latitude),
            crs=f"EPSG:{self.config.epsg_wgs84}"
        )
        # Project to metric CRS for accurate spatial buffering & distance calculations
        segments_gdf = segments_gdf.to_crs(epsg=self.config.epsg_metric)

        # Pre-compute buffers to reuse geometries and save memory/CPU
        logger.info("Pre-computing spatial buffers...")
        seg_20m = segments_gdf.copy()
        seg_20m['geometry'] = seg_20m.geometry.buffer(self.config.radius_crossing_m)
        
        seg_50m = segments_gdf.copy()
        seg_50m['geometry'] = seg_50m.geometry.buffer(self.config.radius_transit_m)
        
        seg_100m = segments_gdf.copy()
        seg_100m['geometry'] = seg_100m.geometry.buffer(self.config.radius_local_m)
        
        seg_250m = segments_gdf.copy()
        seg_250m['geometry'] = seg_250m.geometry.buffer(self.config.radius_neighborhood_m)
        
        seg_500m = segments_gdf.copy()
        seg_500m['geometry'] = seg_500m.geometry.buffer(self.config.radius_broad_m)

        # 2. Parse OSM PBF
        logger.info(f"Loading OSM PBF from {self.config.pbf_path}")
        osm = OSM(str(self.config.pbf_path))
        
        # Extract POIs
        logger.info("Extracting POIs from OSM...")
        custom_filter = {
            'amenity': True, 
            'shop': True, 
            'office': True,
            'tourism': True, 
            'craft': True,
            'leisure': True, 
            'railway': True, 
            'highway': ['bus_stop', 'crossing'],
            'building': ['commercial', 'retail'],
            'landuse': ['commercial']
        }
        pois = osm.get_pois(custom_filter=custom_filter)
        
        if pois is not None and not pois.empty:
            # Project to metric CRS for mathematically correct spatial calculations
            pois = pois.to_crs(epsg=self.config.epsg_metric)
            # Polygons to points
            pois['geometry'] = pois.geometry.centroid

        else:
            logger.warning("No POIs found in the OSM extract. Outputs will be zeroes.")
            pois = gpd.GeoDataFrame(columns=['amenity', 'shop', 'tourism', 'leisure', 'railway', 'highway', 'landuse'], geometry=[], crs=f"EPSG:{self.config.epsg_metric}")

        # 3. Generate Distance Features (500m logic limit)
        logger.info("Generating Distance Features...")
        distance_dfs = []
        
        police_pois = self._extract_poi_subset(pois, 'amenity', 'police')
        distance_dfs.append(self._compute_distance(segments_gdf, police_pois, 'police_dist_m'))
        
        hospital_pois = self._extract_poi_subset(pois, 'amenity', ['hospital', 'clinic'])
        distance_dfs.append(self._compute_distance(segments_gdf, hospital_pois, 'hospital_dist_m'))
        
        # Merge distance features
        dist_final = pd.DataFrame(index=segments_df['segment_id'].drop_duplicates())
        if distance_dfs:
            dist_final = dist_final.join(distance_dfs, how='left')
        dist_final = dist_final.fillna(self.config.max_distance_fallback_m).reset_index()
            
        # 4. Generate POI Count Features (Variable Radii)
        logger.info("Generating POI Features via spatial buffers...")
        poi_dfs = []
        
        POI_HIERARCHY = {
            'food': {'amenity': ['restaurant', 'cafe', 'fast_food', 'bakery', 'bar', 'pub', 'food_court']},
            'retail': {'shop': ['supermarket', 'convenience', 'grocery', 'clothes', 'electronics', 'furniture', 'bookstore', 'hardware', 'florist', 'beauty', 'cosmetics', 'mall', 'department_store']},
            'finance': {'amenity': ['bank', 'atm']},
            'health': {'amenity': ['hospital', 'clinic', 'pharmacy', 'doctors', 'dentist']},
            'education': {'amenity': ['school', 'college', 'university', 'kindergarten']},
            'transport': {'highway': ['bus_stop'], 'railway': ['station', 'subway_entrance'], 'amenity': ['parking', 'fuel']},
            'hospitality': {'tourism': ['hotel', 'guest_house', 'hostel']},
            'government': {'amenity': ['police', 'fire_station', 'post_office']},
            'recreation': {'leisure': ['park', 'stadium', 'playground'], 'amenity': ['cinema', 'theatre', 'library']}
        }
        
        # We will compute 250m densities for all hierarchies
        area_250m = 0.196 # sqkm
        diversity_df = pd.DataFrame(index=segments_df['segment_id'].drop_duplicates())
        diversity_df['commercial_diversity'] = 0
        
        for category, tags in POI_HIERARCHY.items():
            masks = []
            for tag_k, tag_v_list in tags.items():
                if tag_k in pois.columns:
                    masks.append(pois[tag_k].isin(tag_v_list))
            
            if masks:
                cat_mask = pd.concat(masks, axis=1).any(axis=1)
                cat_pois = pois[cat_mask]
                
                cat_counts = self._compute_count(seg_250m, cat_pois, f'{category}_count')
                
                # Update diversity (adds 1 if count > 0)
                if not cat_counts.empty:
                    presence = (cat_counts[f'{category}_count'] > 0).astype(int)
                    diversity_df = diversity_df.join(presence.rename(f'{category}_pres'), how='left')
                    diversity_df['commercial_diversity'] += diversity_df[f'{category}_pres'].fillna(0).astype(int)
                    diversity_df.drop(columns=[f'{category}_pres'], inplace=True)
                
                # Compute density
                cat_counts[f'{category}_density'] = (cat_counts[f'{category}_count'] / area_250m).astype('float32')
                poi_dfs.append(cat_counts[[f'{category}_density']])
        
        poi_dfs.append(diversity_df[['commercial_diversity']])
        
        # 5. Mapping Density Proxy
        logger.info("Generating Mapping Density Proxy...")
        seg_1000m = segments_gdf.copy()
        seg_1000m['geometry'] = seg_1000m.geometry.buffer(1000.0)
        mapping_density = self._compute_count(seg_1000m, pois, 'mapped_feature_count_1000m')
        mapping_density['mapped_feature_density'] = (mapping_density['mapped_feature_count_1000m'] / 3.14).astype('float32')
        poi_dfs.append(mapping_density[['mapped_feature_density']])
        
        # Merge POI features
        poi_final = pd.DataFrame(index=segments_df['segment_id'].drop_duplicates())
        if poi_dfs:
            poi_final = poi_final.join(poi_dfs, how='left')
        poi_final = poi_final.fillna(0).reset_index()

        # 6. Generate Road Features
        logger.info("Generating Road Features...")
        road_features_df = segments_df[['segment_id']].copy()
        
        # Safely extract preserved attributes from segments if available
        def extract_tag_with_imputation(df, tag_name, default='unknown'):
            if tag_name in df.columns:
                series = df[tag_name]
                imputed_flag = series.isna()
                filled = series.fillna(default)
                return filled, imputed_flag
            return pd.Series(default, index=df.index), pd.Series(True, index=df.index)

        road_type_s, _ = extract_tag_with_imputation(segments_df, 'road_type')
        road_features_df['road_type'] = road_type_s
        
        raw_lanes, lanes_imp = extract_tag_with_imputation(segments_df, 'lanes', default='2')
        road_features_df['lanes'] = raw_lanes.astype(str).str.extract(r'(\d+)').fillna(2).astype('int32')
        road_features_df['lanes_imputed'] = lanes_imp | raw_lanes.isna()
        
        raw_sidewalk, sidewalk_imp = extract_tag_with_imputation(segments_df, 'sidewalk', default='unknown')
        road_features_df['sidewalk'] = raw_sidewalk
        road_features_df['sidewalk_known'] = ~sidewalk_imp
        
        raw_surface, surface_imp = extract_tag_with_imputation(segments_df, 'surface', default='unknown')
        road_features_df['surface'] = raw_surface
        road_features_df['surface_known'] = ~surface_imp
        
        # Bridge/Tunnel binaries
        raw_bridge, _ = extract_tag_with_imputation(segments_df, 'bridge', default='no')
        road_features_df['bridge'] = raw_bridge.apply(lambda x: True if str(x).lower() == 'yes' else False)
        
        raw_tunnel, _ = extract_tag_with_imputation(segments_df, 'tunnel', default='no')
        road_features_df['tunnel'] = raw_tunnel.apply(lambda x: True if str(x).lower() == 'yes' else False)
        
        # Parse numeric speeds
        raw_speed, speed_imp = extract_tag_with_imputation(segments_df, 'maxspeed', default='40')
        road_features_df['speed'] = raw_speed.astype(str).str.extract(r'(\d+)').fillna(40).astype('float32')
        road_features_df['speed_imputed'] = speed_imp | raw_speed.isna()
        
        # Parse numeric road width
        raw_width, width_imp = extract_tag_with_imputation(segments_df, 'width', default='0')
        road_features_df['road_width'] = raw_width.astype(str).str.extract(r'(\d+\.?\d*)').fillna(0).astype('float32')
        road_features_df['road_width_imputed'] = width_imp | raw_width.isna()
        
        # 20m Crossings & Junctions
        crossing_pois = self._extract_poi_subset(pois, 'highway', 'crossing')
        cross_counts = self._compute_count(seg_20m, crossing_pois, 'cross_cnt')
        road_features_df = road_features_df.join(cross_counts, on='segment_id')
        road_features_df['crossing_known'] = road_features_df['cross_cnt'].notna()
        road_features_df['cross_cnt'] = road_features_df['cross_cnt'].fillna(0)
        road_features_df['crossing'] = (road_features_df['cross_cnt'] > 0)
        road_features_df.drop(columns=['cross_cnt'], inplace=True)
        
        # 7. Generate Graph Features
        logger.info("Generating Graph Features...")
        if 'start_node' in segments_df.columns and 'end_node' in segments_df.columns:
            # Calculate degree for every node in the graph
            all_nodes = pd.concat([segments_df['start_node'], segments_df['end_node']])
            node_degrees = all_nodes.value_counts()
            
            # For each segment, the complexity is the maximum degree of its endpoints
            segments_df['start_degree'] = segments_df['start_node'].map(node_degrees).fillna(2)
            segments_df['end_degree'] = segments_df['end_node'].map(node_degrees).fillna(2)
            segments_df['node_degree'] = segments_df[['start_degree', 'end_degree']].max(axis=1)
            
            road_features_df['node_degree'] = segments_df['node_degree'].astype('int32')
            road_features_df['dead_end_indicator'] = road_features_df['node_degree'] == 1
            road_features_df['intersection_indicator'] = road_features_df['node_degree'] >= 3
            road_features_df['complex_intersection_indicator'] = road_features_df['node_degree'] >= 4
        else:
            road_features_df['node_degree'] = 2
            road_features_df['dead_end_indicator'] = False
            road_features_df['intersection_indicator'] = False
            road_features_df['complex_intersection_indicator'] = False
        
        # Curvature proxy (Set to 1.0 baseline since heavy LineString geometries are decoupled in V2)
        road_features_df['curvature'] = 1.0

        # 6. Export Datasets
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        p_road = self.config.output_dir / "osm_road_features.parquet"
        p_poi = self.config.output_dir / "osm_poi_features.parquet"
        p_dist = self.config.output_dir / "osm_distance_features.parquet"
        
        logger.info("Writing output datasets to disk...")
        road_features_df.to_parquet(p_road, index=False)
        poi_final.to_parquet(p_poi, index=False)
        dist_final.to_parquet(p_dist, index=False)
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: OSMLoader | Duration: {duration:.2f}s | Processed Rows: {len(road_features_df)} | Output: {self.config.output_dir}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the SafeShe OSM Loader")
    parser.add_argument("--pbf", type=str, required=True, help="Path to input OSM PBF file")
    parser.add_argument("--segments", type=str, default="ml/datasets/processed/road_segments.parquet", help="Path to input road segments")
    parser.add_argument("--outdir", type=str, default="ml/datasets/processed", help="Directory for output Parquet files")
    args = parser.parse_args()
    
    config = OSMLoaderConfig(
        pbf_path=Path(args.pbf),
        segments_path=Path(args.segments),
        output_dir=Path(args.outdir)
    )
    
    loader = OSMLoader(config)
    loader.build()
