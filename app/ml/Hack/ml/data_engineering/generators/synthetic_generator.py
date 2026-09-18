import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import (
    SYNTHETIC_FEATURES,
    OSM_ROAD_FEATURES,
    OSM_POI_FEATURES,
    OSM_DISTANCE_FEATURES,
    POPULATION_FEATURES
)

@dataclass
class SyntheticGeneratorConfig:
    """Configuration for the deterministic Synthetic Feature Generator."""
    output_path: Path = SYNTHETIC_FEATURES
    
    # Base feature paths used when the generator is executed as a standalone CLI
    road_features_path: Path = OSM_ROAD_FEATURES
    poi_features_path: Path = OSM_POI_FEATURES
    dist_features_path: Path = OSM_DISTANCE_FEATURES
    pop_features_path: Path = POPULATION_FEATURES

class SyntheticGenerator:
    """
    Generates deterministic, rule-based synthetic micro-features acting as stand-ins
    until physical IoT/camera data is integrated.
    Strictly implements the architecture defined in docs/synthetic_generator_design.md.
    """
    def __init__(self, config: SyntheticGeneratorConfig):
        self.config = config

    def _safe_get(self, df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
        """Safely extracts a numeric column, handling missing columns gracefully."""
        if col in df.columns:
            return df[col].fillna(default)
        return pd.Series(default, index=df.index)

    def _safe_get_str(self, df: pd.DataFrame, col: str, default: str = 'unknown') -> pd.Series:
        """Safely extracts a categorical column, normalizing string formats."""
        if col in df.columns:
            return df[col].fillna(default).astype(str).str.lower()
        return pd.Series(default, index=df.index)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Executes strict, non-random deterministic rules on a pre-joined master DataFrame
        containing Road, POI, Crime, and Population features.
        """
        logger.info(f"Applying deterministic synthetic heuristics to {len(df)} segments...")
        out = pd.DataFrame({'segment_id': df['segment_id']})
        
        # --- 1. Safely Extract Dependencies ---
        # Road Attributes
        road_type = self._safe_get_str(df, 'road_type')
        surface = self._safe_get_str(df, 'surface')
        tunnel = self._safe_get(df, 'tunnel', False).astype(bool)
        road_width = self._safe_get(df, 'road_width', 5.0)
        curvature = self._safe_get(df, 'curvature', 1.0)
        
        # Proxies (fallback if junction missing)
        junction = self._safe_get(df, 'crossing', False).astype(float) 
        
        # OSM POIs
        comm_density = self._safe_get(df, 'commercial_density', 0.0)
        bank_count = self._safe_get(df, 'bank_count_100m', 0.0)
        atm_count = self._safe_get(df, 'atm_count_50m', 0.0)
        mall_count = self._safe_get(df, 'mall_count_250m', 0.0)
        rest_count = self._safe_get(df, 'restaurant_count_100m', 0.0)
        cafe_count = self._safe_get(df, 'cafe_count_100m', 0.0)
        metro_count = self._safe_get(df, 'metro_count_500m', 0.0)
        police_dist = self._safe_get(df, 'police_dist_m', 5000.0)
        
        # Demographics & Prior
        pop_density = self._safe_get(df, 'population_density', 0.0)
        crime_score = self._safe_get(df, 'crime_score', 50.0)

        # --- 1.5. Derived Scores for internal synthetic heuristics ---
        # A) human_activity_score (0-100)
        # Using pop density, commercial density, restaurants, cafes, bus stops, metro stations
        pop_norm = (pop_density.clip(0, 50000) / 50000.0) * 100.0
        comm_norm = (comm_density.clip(0, 100) / 100.0) * 100.0
        transit = (self._safe_get(df, 'bus_stop_count_50m', 0.0) * 5.0 + metro_count * 20.0).clip(0, 100)
        leisure = (rest_count + cafe_count) * 10.0
        human_activity_score = (pop_norm * 0.3 + comm_norm * 0.3 + transit * 0.2 + leisure * 0.2).clip(0, 100)

        # B) desertion_score (0-100)
        # Represents isolation and low human presence
        desertion_score = 100.0 - human_activity_score

        # C) essential_services_density
        # Based on nearby hospitals, police stations, pharmacies, banks, ATMs, restaurants, and shops
        hospital_dist = self._safe_get(df, 'hospital_dist_m', 5000.0)
        hospital_prox = np.where(hospital_dist < 1000, 20.0, 0.0)
        police_prox = np.where(police_dist < 1000, 20.0, 0.0)
        pharmacy_count = self._safe_get(df, 'pharmacy_count_100m', 0.0)
        
        essential_services_density = (hospital_prox + police_prox + pharmacy_count * 10.0 + bank_count * 10.0 + atm_count * 5.0 + rest_count * 5.0 + mall_count * 10.0).clip(0, 100)


        # --- 2. Generate Deterministic Features ---

        # A) Lighting
        light = pd.Series(40.0, index=df.index) # Default residential/suburban baseline
        light[road_type.isin(['primary', 'trunk', 'motorway', 'primary_link'])] = 80.0
        light[road_type.isin(['secondary', 'tertiary'])] = 60.0
        light[road_type.isin(['unclassified', 'track', 'path', 'pedestrian'])] = 20.0
        
        # Incorporate derived scores
        light += (human_activity_score * 0.3)
        light += junction * 10.0
        
        # Validation: Lighting cannot be high in desolate areas unless it's a major highway
        light = np.where((desertion_score > 80.0) & (~road_type.isin(['primary', 'trunk', 'motorway'])), 
                         light.clip(upper=30.0), light)
        out['synth_lighting'] = light.clip(lower=0, upper=100).astype('float32')

        # B) CCTV
        cctv = essential_services_density * 0.6  # Essential services are heavy CCTV drivers
        cctv += comm_density * 20.0
        cctv += junction * 10.0
        
        # Validation: Zero probability of extensive CCTV in pure residential/desolate zones
        cctv = np.where((desertion_score > 80.0), cctv.clip(upper=10.0), cctv)
        out['synth_cctv'] = cctv.clip(lower=0, upper=100).astype('float32')

        # C) Road Maintenance
        maint = pd.Series(50.0, index=df.index)
        maint[surface.isin(['asphalt', 'paved', 'concrete'])] = 70.0
        maint[surface.isin(['unpaved', 'dirt', 'gravel', 'ground'])] = 20.0
        maint[road_type.isin(['primary', 'trunk', 'motorway'])] += 20.0
        
        bad_surface = surface.isin(['unpaved', 'dirt', 'gravel', 'ground'])
        # Validation: Cannot have high maintenance score if surface is physically dirt
        maint = np.where(bad_surface, maint.clip(upper=40.0), maint)
        out['synth_road_maintenance'] = maint.clip(lower=0, upper=100).astype('float32')

        # D) Night Activity
        night = human_activity_score * 0.5  # Base night activity strongly correlates with human activity
        night += (rest_count + cafe_count) * 15.0
        night += metro_count * 20.0
        
        # Validation: No ambient night activity in desolate areas
        night = np.where(desertion_score > 70.0, night.clip(upper=10.0), night)
        out['synth_night_activity'] = night.clip(lower=0, upper=100).astype('float32')

        # E) Visibility
        vis = pd.Series(70.0, index=df.index)
        vis -= np.where(road_width < 5.0, 20.0, 0.0)
        vis -= np.where(curvature > 1.5, 30.0, 0.0)
        
        # Tunnels crush visibility, but active lighting mitigates it
        vis -= np.where(tunnel, 40.0 - (out['synth_lighting'] * 0.4), 0.0)
        
        # Validation: Severe blind corners cap visibility strictly
        vis = np.where(curvature > 2.0, vis.clip(upper=40.0), vis)
        out['synth_visibility'] = vis.clip(lower=0, upper=100).astype('float32')

        # F) Community Safety (Sentiment Proxy)
        safe = pd.Series(50.0, index=df.index)
        safe += essential_services_density * 0.2
        safe += out['synth_lighting'] * 0.2
        
        # High desertion heavily penalizes perceived community safety
        safe -= desertion_score * 0.3
        
        # Modulate by macro crime score prior
        safe -= (crime_score - 50.0) * 0.5 
        
        # Validation: Highly desolate areas with severe crime priors are inherently unsafe
        high_risk_iso = (desertion_score > 80.0) & (crime_score > 70)
        safe = np.where(high_risk_iso, safe.clip(upper=30.0), safe)
        out['synth_community_safety'] = safe.clip(lower=0, upper=100).astype('float32')

        # --- 3. Synthetic Confidence ---
        conf = pd.Series(85.0, index=df.index)
        
        # Confidence drops when foundational driving features are absent
        missing_comm = (comm_density == 0.0) & (bank_count == 0)
        missing_pop = (pop_density == 0.0)
        
        conf -= missing_comm.astype(float) * 15.0
        conf -= missing_pop.astype(float) * 15.0
        
        out['synthetic_confidence'] = conf.clip(lower=0, upper=100).astype('float32')
        
        return out

    def build(self) -> None:
        """
        Standalone pipeline execution.
        Joins available real feature parquets and runs deterministic generation.
        """
        import time
        start_time = time.time()
        logger.info(f"START: SyntheticGenerator | Output: {self.config.output_path}")
        logger.info("Aggregating base feature datasets...")
        dfs = []
        
        if self.config.road_features_path.exists():
            dfs.append(pd.read_parquet(self.config.road_features_path))
        if self.config.poi_features_path.exists():
            dfs.append(pd.read_parquet(self.config.poi_features_path))
        if self.config.dist_features_path.exists():
            dfs.append(pd.read_parquet(self.config.dist_features_path))
        if self.config.pop_features_path.exists():
            dfs.append(pd.read_parquet(self.config.pop_features_path))
            
        if not dfs:
            raise FileNotFoundError("No base feature parquets found. Ensure Loaders have been executed.")
            
        # Left join all tables on segment_id
        master_df = dfs[0]
        for df in dfs[1:]:
            master_df = master_df.merge(df, on='segment_id', how='left')
            
        synthetic_df = self.generate(master_df)
        
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        synthetic_df.to_parquet(self.config.output_path, index=False)
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: SyntheticGenerator | Duration: {duration:.2f}s | Processed Rows: {len(synthetic_df)} | Output: {self.config.output_path}")


if __name__ == "__main__":
    generator = SyntheticGenerator(SyntheticGeneratorConfig())
    generator.build()
