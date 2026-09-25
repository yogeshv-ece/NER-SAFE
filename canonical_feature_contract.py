"""
NER-SAFE: Canonical Live Multi-Model Feature Contract & Provenance Registry
Defines the authoritative live data contract across operational and research models:
- Calibrated XGBoost (Production Susceptibility)
- Calibrated Random Forest (Fallback Susceptibility)
- Spatial CNN (Live Shadow Context Inference)
- C15 Pre-Landslide Forecaster (Live Multi-Window Horizon Forecast)
- Sentinel-1 InSAR SBAS (Live Research Deformation Inversion)
- NASA GPM IMERG Early NRT (Dynamic Rainfall Anomaly)
- NASA SMAP SPL2SMP_NRT (Dynamic Soil Moisture Anomaly)
- Copernicus Sentinel-1 GRD / Sentinel-2 L2A (Dynamic Surface Disturbance)
"""

import os
import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Strict freshness thresholds (in hours)
MAX_FEATURE_AGE_HOURS = {
    "rainfall": 24.0,           # GPM Early NRT available ~4h
    "soil_moisture": 72.0,      # SMAP 2-3 day repeat
    "optical_satellite": 168.0, # Sentinel-2 5-day repeat
    "sar_satellite": 288.0,     # Sentinel-1 12-day orbital repeat
    "insar_deformation": 864.0, # Sentinel-1 36-day max baseline
    "terrain_static": 87600.0   # SRTM 30m static DEM baseline (10 years)
}

@dataclass
class CanonicalFeatureRecord:
    hotspot_id: str
    latitude: float
    longitude: float
    reference_time_utc: str
    
    # Operational Model Signals
    susceptibility_xgboost: float
    susceptibility_rf_fallback: float
    rainfall_anomaly: float
    soil_moisture_anomaly: float
    satellite_change_flag: float
    
    # Research & Shadow Model Signals
    cnn_probability: Optional[float] = None
    cnn_uncertainty: Optional[float] = None
    cnn_status: str = "AWAITING_INFERENCE"
    
    c15_probability: Optional[float] = None
    c15_entropy: Optional[float] = None
    c15_status: str = "INSUFFICIENT_TEMPORAL_INPUT"
    
    insar_deformation_indicator: Optional[float] = None
    insar_velocity_mm_yr: Optional[float] = None
    insar_coherence: Optional[float] = None
    insar_quality: Optional[float] = None
    insar_status: str = "RESEARCH_ONLY"
    
    # Metadata, Timestamps & Provenance
    feature_timestamps: Dict[str, str] = field(default_factory=dict)
    source_provenance: Dict[str, str] = field(default_factory=dict)
    feature_freshness: Dict[str, str] = field(default_factory=dict)
    data_quality_flags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiModelDataContractManager:
    """Manages the extraction, validation, and enforcement of the canonical feature contract."""

    @staticmethod
    def validate_temporal_alignment(record: CanonicalFeatureRecord) -> Tuple[bool, List[str]]:
        """
        Enforces strict temporal leakage prevention:
        No feature observation timestamp may exceed reference_time_utc.
        """
        ref_dt = datetime.fromisoformat(record.reference_time_utc.replace("Z", "+00:00"))
        violations = []
        
        for feat_name, ts_str in record.feature_timestamps.items():
            if not ts_str:
                continue
            try:
                obs_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if obs_dt > ref_dt:
                    violations.append(
                        f"TEMPORAL_LEAKAGE_DETECTED: Feature '{feat_name}' observation time {obs_dt} "
                        f"is in the future relative to reference prediction time {ref_dt}"
                    )
            except Exception as e:
                violations.append(f"INVALID_TIMESTAMP: Feature '{feat_name}' timestamp '{ts_str}' error: {e}")
                
        is_valid = (len(violations) == 0)
        return is_valid, violations

    @staticmethod
    def evaluate_freshness(ts_str: str, max_age_hours: float, ref_dt: datetime) -> Tuple[str, float]:
        """Calculates exact feature age and returns categorized freshness."""
        if not ts_str:
            return "NO_DATA", 99999.0
        try:
            obs_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (ref_dt - obs_dt).total_seconds() / 3600.0
            if age_hours < 0:
                return "FUTURE_INVALID", age_hours
            if age_hours <= max_age_hours * 0.33:
                return "FRESH", round(age_hours, 1)
            elif age_hours <= max_age_hours:
                return "RECENT", round(age_hours, 1)
            elif age_hours <= max_age_hours * 2.0:
                return "AGING", round(age_hours, 1)
            else:
                return "STALE", round(age_hours, 1)
        except Exception:
            return "PARSE_ERROR", 99999.0


contract_manager = MultiModelDataContractManager()
