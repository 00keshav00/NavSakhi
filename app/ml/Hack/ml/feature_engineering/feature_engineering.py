import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import (
    ROAD_SEGMENTS,
    CRIME_FEATURES,
    OSM_ROAD_FEATURES,
    OSM_POI_FEATURES,
    OSM_DISTANCE_FEATURES,
    POPULATION_FEATURES,
    SYNTHETIC_FEATURES,
    MASTER_FEATURE_TABLE
)

@dataclass
class FeatureEngineeringConfig:
    """Configuration for the ML Feature Engineering pipeline."""
    # Input paths for all sub-domain feature datasets
    segments_path: Path = ROAD_SEGMENTS
    crime_path: Path = CRIME_FEATURES  # Fallback handled if CSV
    road_features_path: Path = OSM_ROAD_FEATURES
    poi_features_path: Path = OSM_POI_FEATURES
    dist_features_path: Path = OSM_DISTANCE_FEATURES
    pop_features_path: Path = POPULATION_FEATURES
    synth_features_path: Path = SYNTHETIC_FEATURES
    
    # Final output path
    output_path: Path = MASTER_FEATURE_TABLE
    
    # Derived metric configurations
    commercial_buffer_area_sqkm: float = 0.196  # Area of a 250m radius circle

class FeatureEngineer:
    """
    Central aggregation and derived metrics engine.
    Strictly implements the architecture defined in docs/feature_catalog.md.
    """
    def __init__(self, config: FeatureEngineeringConfig):
        self.config = config

    def _safe_read(self, path: Path) -> pd.DataFrame:
        """Gracefully attempts to load a Parquet file, returning empty DataFrame on failure."""
        if path.exists():
            return pd.read_parquet(path)
        logger.warning(f"Feature file missing: {path}. Pipeline will proceed with NaN for these features.")
        return pd.DataFrame()

    def load_and_join(self) -> pd.DataFrame:
        """Left-joins all component datasets onto the master segment IDs."""
        if not self.config.segments_path.exists():
            raise FileNotFoundError(f"Base anchor dataset missing: {self.config.segments_path}")
            
        master_df = pd.read_parquet(self.config.segments_path)
        logger.info(f"Loaded {len(master_df)} base road segments as anchors.")

        files = {
            'Crime Features': self.config.crime_path,
            'Road Features': self.config.road_features_path,
            'POI Features': self.config.poi_features_path,
            'Distance Features': self.config.dist_features_path,
            'Population Features': self.config.pop_features_path,
            'Synthetic Features': self.config.synth_features_path
        }
        
        for name, path in files.items():
            df = self._safe_read(path)
            if not df.empty and 'segment_id' in df.columns:
                logger.info(f"Joining {name} ({len(df.columns)} columns)...")
                # Drop overlapping columns (except join key) to prevent Pandas _x _y suffixes
                cols_to_use = df.columns.difference(master_df.columns).tolist() + ['segment_id']
                master_df = master_df.merge(df[cols_to_use], on='segment_id', how='left')
                
        return master_df

    def _min_max_scale(self, series: pd.Series, max_val: Optional[float] = None) -> pd.Series:
        """Helper for robust vectorized min-max scaling to 0-100 range."""
        min_v = series.min()
        max_v = max_val if max_val is not None else series.max()
        if max_v == min_v or pd.isna(max_v):
            return pd.Series(0.0, index=series.index)
        return ((series - min_v) / (max_v - min_v) * 100.0).fillna(0.0)

    def generate_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generates higher-order metrics by mathematically combining base features."""
        logger.info("Engineering derived feature: commercial_density")
        # Combines heavy commercial POIs normalized by spatial area
        mall = df.get('mall_count_250m', pd.Series(0, index=df.index))
        rest = df.get('restaurant_count_100m', pd.Series(0, index=df.index))
        bank = df.get('bank_count_100m', pd.Series(0, index=df.index))
        
        df['commercial_density'] = (mall + rest + bank) / self.config.commercial_buffer_area_sqkm
        df['commercial_density'] = df['commercial_density'].astype('float32')

        logger.info("Engineering derived feature: accessibility_score")
        # Combines physical road attributes: width, classification, and pedestrian paths
        width_score = self._min_max_scale(df.get('road_width', pd.Series(0, index=df.index)), max_val=30.0)
        
        # Sidewalk presence mapping
        sidewalk_raw = df.get('sidewalk', pd.Series('unknown', index=df.index)).astype(str).str.lower()
        sidewalk_score = sidewalk_raw.isin(['both', 'left', 'right']).astype(float) * 50.0
        
        # Road hierarchy mapping
        road_type = df.get('road_type', pd.Series('unknown', index=df.index)).astype(str).str.lower()
        rt_score = pd.Series(20.0, index=df.index)
        rt_score[road_type.isin(['primary', 'trunk', 'motorway'])] = 50.0
        rt_score[road_type.isin(['secondary', 'tertiary'])] = 30.0
        
        df['accessibility_score'] = ((width_score * 0.4) + (sidewalk_score * 0.4) + (rt_score * 0.2)).clip(0, 100).astype('float32')

        logger.info("Engineering derived feature: transit_density")
        # Weighted metric of localized public transit access
        bus = df.get('bus_stop_count_50m', pd.Series(0, index=df.index))
        metro = df.get('metro_count_500m', pd.Series(0, index=df.index))
        td = (bus * 1.0) + (metro * 5.0)
        df['transit_density'] = (td / 20.0).clip(0.0, 1.0).astype('float32')

        logger.info("Engineering derived feature: emergency_accessibility")
        # Distance-decay metric combining police and hospital proximity
        p_dist = df.get('police_dist_m', pd.Series(5000.0, index=df.index)).clip(0, 5000)
        h_dist = df.get('hospital_dist_m', pd.Series(5000.0, index=df.index)).clip(0, 5000)
        
        # Invert: 0m = 100 score, 5000m = 0 score
        p_score = ((5000.0 - p_dist) / 5000.0) * 100.0
        h_score = ((5000.0 - h_dist) / 5000.0) * 100.0
        df['emergency_accessibility'] = ((p_score * 0.5) + (h_score * 0.5)).astype('float32')

        logger.info("Engineering derived feature: walkability")
        # Combines safety speed limits, explicit crossings, and sidewalks
        speed = df.get('speed', pd.Series(40.0, index=df.index))
        speed_score = ((120.0 - speed.clip(0, 120)) / 120.0) * 50.0  # Lower speeds score higher
        cross_score = df.get('crossing', pd.Series(False, index=df.index)).astype(float) * 20.0
        
        df['walkability'] = (sidewalk_score + speed_score + cross_score).clip(0, 100).astype('float32')

        logger.info("Engineering derived feature: isolation_index")
        # Inverse metric of ambient human footprint
        pop = df.get('population_density', pd.Series(0.0, index=df.index)).fillna(0.0)
        comm = df['commercial_density']
        
        pop_norm = self._min_max_scale(pop.clip(0, 50000), max_val=50000.0)
        comm_norm = self._min_max_scale(comm.clip(0, 100), max_val=100.0)
        
        activity_footprint = (pop_norm * 0.5) + (comm_norm * 0.5)
        df['isolation_index'] = (100.0 - activity_footprint).clip(0, 100).astype('float32')

        logger.info("Engineering derived feature: road_complexity")
        # Structural difficulty and conflict-point proxy
        lanes = pd.to_numeric(df.get('lanes', pd.Series(2.0, index=df.index)), errors='coerce').fillna(2).clip(1, 8)
        lanes_score = ((lanes - 1.0) / 7.0) * 30.0
        
        oneway_score = (df.get('oneway', pd.Series('no', index=df.index)) == 'yes').astype(float) * 10.0
        
        curve = df.get('curvature', pd.Series(1.0, index=df.index)).clip(1.0, 3.0)
        curve_score = ((curve - 1.0) / 2.0) * 40.0
        
        df['road_complexity'] = (lanes_score + cross_score + oneway_score + curve_score).clip(0, 100).astype('float32')

        logger.info("Engineering derived feature: human_activity_score")
        # Combines population density, commercial density, leisure, and transit
        pop_norm_act = (pop.clip(0, 50000) / 50000.0) * 100.0
        comm_norm_act = (df.get('commercial_density', pd.Series(0, index=df.index)).clip(0, 100) / 100.0) * 100.0
        transit_act = (df.get('bus_stop_count_50m', pd.Series(0, index=df.index)) * 5.0 + df.get('metro_count_500m', pd.Series(0, index=df.index)) * 20.0).clip(0, 100)
        rest_act = df.get('restaurant_count_100m', pd.Series(0, index=df.index))
        cafe_act = df.get('cafe_count_100m', pd.Series(0, index=df.index))
        leisure_act = (rest_act + cafe_act) * 10.0
        df['human_activity_score'] = (pop_norm_act * 0.3 + comm_norm_act * 0.3 + transit_act * 0.2 + leisure_act * 0.2).clip(0, 100).astype('float32')

        logger.info("Engineering derived feature: desertion_score")
        # Inverse of human activity, representing isolated and deserted spaces
        df['desertion_score'] = (100.0 - df['human_activity_score']).astype('float32')
        
        logger.info("Engineering derived feature: essential_services_density")
        # Aggregates proximity and counts of key essential services
        h_dist_ess = df.get('hospital_dist_m', pd.Series(5000.0, index=df.index))
        p_dist_ess = df.get('police_dist_m', pd.Series(5000.0, index=df.index))
        
        import numpy as np
        h_prox = np.where(h_dist_ess < 1000, 20.0, 0.0)
        p_prox = np.where(p_dist_ess < 1000, 20.0, 0.0)
        
        pharm = df.get('pharmacy_count_100m', pd.Series(0, index=df.index))
        bank = df.get('bank_count_100m', pd.Series(0, index=df.index))
        atm = df.get('atm_count_50m', pd.Series(0, index=df.index))
        mall = df.get('mall_count_250m', pd.Series(0, index=df.index))
        
        df['essential_services_density'] = (h_prox + p_prox + pharm * 10.0 + bank * 10.0 + atm * 5.0 + rest_act * 5.0 + mall * 10.0).clip(0, 100).astype('float32')

        return df

    def build(self) -> None:
        """Executes the complete joining and feature generation pipeline."""
        import time
        start_time = time.time()
        logger.info(f"START: FeatureEngineer | Output: {self.config.output_path}")
        master_df = self.load_and_join()
        
        master_df = self.generate_derived_features(master_df)
        
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        master_df.to_parquet(self.config.output_path, index=False)
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: FeatureEngineer | Duration: {duration:.2f}s | Processed Rows: {len(master_df)} | Output: {self.config.output_path}")

if __name__ == "__main__":
    engineer = FeatureEngineer(FeatureEngineeringConfig())
    engineer.build()
