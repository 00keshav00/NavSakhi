import logging
from pathlib import Path
from typing import Dict
from dataclasses import dataclass
import numpy as np
import pandas as pd

from ml.config.paths import MASTER_FEATURE_TABLE, LABELS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SafetyLabelConfig:
    input_path: Path = MASTER_FEATURE_TABLE
    output_path: Path = LABELS
    
    # Tunable heuristic weights for risk generation
    # Positive weights INCREASE risk (dangerous)
    # Negative weights DECREASE risk (safe)
    weights: Dict[str, float] = None
    noise_percentage: float = 5.0  # Max +/- 5% stochastic perturbation

    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'dead_end': 15.0,              # Trapped environments
                'low_population': 20.0,        # Isolated areas
                'far_from_police': 25.0,       # No law enforcement
                'far_from_hospital': 10.0,     # Slow emergency response
                'sparse_commercial': 15.0,     # No natural surveillance ("eyes on the street")
                'unknown_crossing': 5.0,       # Poor pedestrian infrastructure
                
                'high_food_density': -15.0,    # High evening footfall
                'high_transit': -10.0,         # Public presence
                'urban_corridor': -10.0,       # Active thoroughfare
                'high_diversity': -20.0,       # Highly mixed-use (safest)
                'mapping_density': -5.0        # Well-mapped areas are generally affluent/safe
            }

class SafetyRiskLabelGenerator:
    """
    TEMPORARY Expert-Derived Safety Risk Generator.
    This module builds a synthetic target variable based purely on established 
    environmental criminology theories (e.g., CPTED - Crime Prevention Through Environmental Design, 
    Jane Jacobs' "Eyes on the Street").
    
    IN PRODUCTION: This entire module is discarded and replaced with real police incident data.
    """
    def __init__(self, config: SafetyLabelConfig):
        self.config = config

    def _normalize(self, series: pd.Series, invert: bool = False) -> pd.Series:
        """Min-Max scaler [0, 1]. Inverts if higher values should mean lower risk."""
        min_v = series.min()
        max_v = series.max()
        if max_v == min_v or pd.isna(max_v) or pd.isna(min_v):
            return pd.Series(0.0, index=series.index)
        
        scaled = (series - min_v) / (max_v - min_v)
        return 1.0 - scaled if invert else scaled

    def build(self):
        logger.info(f"START: SafetyRiskLabelGenerator | Output: {self.config.output_path}")
        
        if not self.config.input_path.exists():
            raise FileNotFoundError(f"Master features missing: {self.config.input_path}")
            
        logger.info("Loading master feature table...")
        df = pd.read_parquet(self.config.input_path)
        
        # We will build a base score starting at 50
        base_score = np.full(len(df), 50.0)
        
        # --- Apply Heuristics ---
        w = self.config.weights
        logger.info("Applying environmental criminology heuristics...")
        
        # 1. Dead end
        if 'dead_end_indicator' in df.columns:
            base_score += df['dead_end_indicator'].astype(float) * w['dead_end']
            
        # 2. Low population (Inverse of population percentile)
        if 'population_percentile' in df.columns:
            base_score += (1.0 - df['population_percentile']) * w['low_population']
            
        # 3. Far from Police (Normalized distance)
        if 'police_dist_m' in df.columns:
            base_score += self._normalize(df['police_dist_m']) * w['far_from_police']
            
        # 4. Far from Hospital
        if 'hospital_dist_m' in df.columns:
            base_score += self._normalize(df['hospital_dist_m']) * w['far_from_hospital']
            
        # 5. Sparse Commercial (Inverse of density/diversity)
        if 'commercial_density' in df.columns:
            base_score += self._normalize(df['commercial_density'], invert=True) * w['sparse_commercial']
            
        # 6. Unknown crossing
        if 'crossing_known' in df.columns:
            base_score += (~df['crossing_known']).astype(float) * w['unknown_crossing']
            
        # --- Decrease Risk ---
        # 7. High Food Density
        if 'food_density' in df.columns:
            base_score += self._normalize(df['food_density']) * w['high_food_density']
            
        # 8. High Transit
        if 'transport_density' in df.columns:
            base_score += self._normalize(df['transport_density']) * w['high_transit']
            
        # 9. Urban Corridor
        if 'urban_indicator' in df.columns:
            base_score += df['urban_indicator'].astype(float) * w['urban_corridor']
            
        # 10. High Diversity
        if 'commercial_diversity' in df.columns:
            base_score += self._normalize(df['commercial_diversity']) * w['high_diversity']
            
        # 11. Mapping Density
        if 'mapped_feature_density' in df.columns:
            base_score += self._normalize(df['mapped_feature_density']) * w['mapping_density']
            
        # Apply stochastic perturbation (+/- 5%)
        logger.info(f"Injecting {self.config.noise_percentage}% stochastic noise...")
        np.random.seed(42)
        noise = np.random.uniform(-self.config.noise_percentage, self.config.noise_percentage, len(base_score))
        
        final_score = base_score * (1 + (noise / 100.0))
        
        # Clip strictly between 0 and 100
        final_score = np.clip(final_score, 0.0, 100.0)
        
        # Classify based on percentiles (33%, 66%)
        p33 = np.percentile(final_score, 33)
        p66 = np.percentile(final_score, 66)
        
        conditions = [
            (final_score < p33),
            (final_score >= p33) & (final_score < p66),
            (final_score >= p66)
        ]
        choices = ['Low', 'Medium', 'High']
        risk_class = np.select(conditions, choices, default='Medium')
        
        out_df = pd.DataFrame({
            'segment_id': df['segment_id'],
            'risk_score': final_score.astype('float32'),
            'risk_class': risk_class
        })
        
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_parquet(self.config.output_path, index=False)
        logger.info(f"COMPLETED: Generated {len(out_df)} labels -> {self.config.output_path}")
        
if __name__ == "__main__":
    SafetyRiskLabelGenerator(SafetyLabelConfig()).build()
