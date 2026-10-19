import logging
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from ml.config.paths import MASTER_FEATURE_TABLE, LABELS

@dataclass
class LabelGeneratorConfig:
    """Configuration for deterministic label generation."""
    input_path: Path = MASTER_FEATURE_TABLE
    output_path: Path = LABELS
    
    # Domain-expert heuristic weights for safety scoring
    weight_infra_boost: float = 0.5
    weight_eyes_boost: float = 0.2
    weight_isolation_penalty: float = 0.5
    
    # Cap thresholds
    extreme_risk_crime_threshold: float = 80.0
    extreme_risk_isolation_threshold: float = 80.0
    extreme_risk_safety_cap: float = 40.0

class LabelGenerator:
    """
    Generates deterministic target labels (safety_score, crowd_score) for ML training.
    Strictly implements the architecture defined in docs/label_generation_v2.md.
    """
    def __init__(self, config: LabelGeneratorConfig):
        self.config = config

    def _safe_get(self, df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
        """Safely extracts a numeric column, handling missing columns gracefully."""
        if col in df.columns:
            return df[col].fillna(default)
        return pd.Series(default, index=df.index)

    def generate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Executes strictly deterministic, vectorized heuristics to synthesize target labels."""
        logger.info(f"Synthesizing target labels for {len(df)} segments...")
        
        # --- 1. Crowd Score Extraction ---
        # The crowd score represents ambient foot traffic and density.
        pop_density = self._safe_get(df, 'population_density', 0.0)
        pop_score = (pop_density / 50000.0 * 100.0).clip(0, 100)
        
        comm_density = self._safe_get(df, 'commercial_density', 0.0)
        comm_score = (comm_density / 5.0 * 100.0).clip(0, 100)
        
        transit = self._safe_get(df, 'transit_density', 0.0) * 100.0
        night_activity = self._safe_get(df, 'synth_night_activity', 0.0)
        
        # Heuristic: Dense population, vibrant commerce, and active transit hubs generate crowds.
        crowd = (pop_score * 0.3) + (comm_score * 0.3) + (transit * 0.2) + (night_activity * 0.2)
        crowd = crowd.clip(0, 100)

        # --- 2. Safety Score Extraction ---
        # Background prior intercepts
        crime = self._safe_get(df, 'crime_score', 50.0)
        
        # Infrastructure variables
        lighting = self._safe_get(df, 'synth_lighting', 0.0)
        cctv = self._safe_get(df, 'synth_cctv', 0.0)
        walkability = self._safe_get(df, 'walkability', 50.0)
        emergency = self._safe_get(df, 'emergency_accessibility', 50.0)
        isolation = self._safe_get(df, 'isolation_index', 50.0)
        
        # The baseline safety is inversely proportional to historical macro-level crime
        base_safety = 100.0 - crime
        
        # Micro-infrastructure acts as a strong multiplier
        infra_boost = (lighting * 0.4) + (cctv * 0.3) + (emergency * 0.3)
        
        # "Eyes on the street" doctrine: ambient crowds act as a natural deterrent
        eyes_boost = crowd * self.config.weight_eyes_boost
        
        # Severe penalty for geometric isolation
        isolation_penalty = isolation * self.config.weight_isolation_penalty
        
        # Synthesize final continuous target
        safety = base_safety + (infra_boost * self.config.weight_infra_boost) + eyes_boost - isolation_penalty
        
        # Strict Validation Limits
        # If the area is statistically highly dangerous and physically isolated, cap safety rigidly.
        extreme_risk = (crime > self.config.extreme_risk_crime_threshold) | (isolation > self.config.extreme_risk_isolation_threshold)
        safety = np.where(extreme_risk, safety.clip(upper=self.config.extreme_risk_safety_cap), safety)
        
        safety = safety.clip(0, 100)

        # --- 3. Label Confidence ---
        # Driven by the upstream synthetic generator's confidence, as labels are inherently synthetic proxies right now.
        synth_conf = self._safe_get(df, 'synthetic_confidence', 50.0)

        # --- 4. Export ---
        out = pd.DataFrame({
            'segment_id': df['segment_id'],
            'safety_score': safety.astype('float32'),
            'crowd_score': crowd.astype('float32'),
            'label_confidence': synth_conf.astype('float32')
        })
        
        return out

    def build(self) -> None:
        """End-to-end wrapper to load master features and output standard labels."""
        import time
        start_time = time.time()
        logger.info(f"START: LabelGenerator | Output: {self.config.output_path}")

        if not self.config.input_path.exists():
            raise FileNotFoundError(f"Master feature table not found at {self.config.input_path}")
            
        logger.info(f"Loading master feature table from {self.config.input_path}...")
        df = pd.read_parquet(self.config.input_path)
        
        labels_df = self.generate(df)
        
        self.config.output_path.parent.mkdir(parents=True, exist_ok=True)
        labels_df.to_parquet(self.config.output_path, index=False)
        
        duration = time.time() - start_time
        logger.info(f"COMPLETED: LabelGenerator | Duration: {duration:.2f}s | Processed Rows: {len(labels_df)} | Output: {self.config.output_path}")


if __name__ == "__main__":
    generator = LabelGenerator(LabelGeneratorConfig())
    generator.build()
