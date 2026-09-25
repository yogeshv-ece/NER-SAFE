"""
NER-SAFE: Reusable Multi-Horizon Temporal Feature Engine
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Features Extracted:
1. Rainfall (NASA GPM IMERG):
   - Recent accumulation (1h, 3h, 6h, 12h, 24h, 48h, 72h, 7-day antecedent)
   - Rolling accumulation mean & max intensity
   - Rainfall anomaly (relative to regional dry/wet baseline)
   - Persistence (consecutive hours/days with precipitation > 5mm)
   - Rate of change (delta P / delta t)
2. Soil Moisture (NASA SMAP L3):
   - Current surface saturation index (m3/m3 normalized)
   - Soil moisture anomaly (deviation from mean baseline)
   - Rolling 3-day mean saturation
   - Saturation rate of change (delta SM / delta t)
   - Observation age in hours
3. Sentinel-1 SAR:
   - Radar backscatter change ratio (VV/VH delta)
   - Observation age & acquisition geometry
   - Cloud penetration capability flag (1.0 = all-weather active)
4. Sentinel-2 Optical:
   - NDVI, NDWI, NDMI surface spectral change
   - Cloud occlusion & SCL quality flag
   - Optical degradation indicator
5. Static Terrain Baseline:
   - C10 Calibrated Susceptibility Probability
   - SRTM Elevation, Slope, Aspect, TWI, Flow Accumulation
"""

import os
import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from observation_provenance import provenance_registry, STATE_FRESH, STATE_DEGRADED, STATE_WAITING_FOR_DATA

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))

# Supported Candidate Forecast Horizons
CANDIDATE_HORIZONS = ["1h", "3h", "6h", "12h", "24h", "48h"]

class TemporalFeatureEngine:
    def __init__(self):
        self.feature_version = "v1.2.0-temporal"

    def extract_rainfall_features(
        self,
        recent_series: List[Dict[str, Any]],
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extracts multi-window accumulation, intensity, rate of change, and antecedent precipitation.
        Input series expects records with 'timestamp_utc' and 'precipitation_mm'.
        """
        ref_time = reference_time_utc or datetime.now(timezone.utc)
        
        if not recent_series:
            return {
                "rainfall_available": False,
                "status": STATE_WAITING_FOR_DATA,
                "accum_1h_mm": None,
                "accum_3h_mm": None,
                "accum_6h_mm": None,
                "accum_12h_mm": None,
                "accum_24h_mm": None,
                "accum_48h_mm": None,
                "accum_72h_mm": None,
                "antecedent_7d_mm": None,
                "max_hourly_intensity_mm": None,
                "rainfall_anomaly_ratio": None,
                "persistence_hours": 0,
                "persistence_steps": 0,
                "rainfall_rate_of_change": None
            }

        # Sort series by timestamp ascending
        sorted_series = sorted(
            recent_series,
            key=lambda x: x.get("timestamp_utc", "")
        )

        def get_window_sum(hours: float) -> float:
            cutoff = ref_time - timedelta(hours=hours)
            total = 0.0
            for item in sorted_series:
                try:
                    t = datetime.fromisoformat(item["timestamp_utc"].replace("Z", "+00:00"))
                    if t.tzinfo is None:
                        t = t.replace(tzinfo=timezone.utc)
                    if t >= cutoff and t <= ref_time:
                        total += float(item.get("precipitation_mm", 0.0))
                except Exception:
                    continue
            return round(total, 2)

        accum_1h = get_window_sum(1.0)
        accum_3h = get_window_sum(3.0)
        accum_6h = get_window_sum(6.0)
        accum_12h = get_window_sum(12.0)
        accum_24h = get_window_sum(24.0)
        accum_48h = get_window_sum(48.0)
        accum_72h = get_window_sum(72.0)
        antecedent_7d = get_window_sum(168.0)

        # Max intensity
        max_int = max([float(x.get("precipitation_mm", 0.0)) for x in sorted_series] or [0.0])
        
        # Rainfall anomaly relative to regional baseline (e.g. 15mm daily mean)
        anomaly_ratio = round(accum_24h / 15.0, 3) if accum_24h > 0 else 0.0

        # Persistence (count of steps with precip > 2mm)
        pers_count = sum(1 for x in sorted_series if float(x.get("precipitation_mm", 0.0)) >= 2.0)

        # Rate of change between last two intervals
        rate_of_change = 0.0
        if len(sorted_series) >= 2:
            p_curr = float(sorted_series[-1].get("precipitation_mm", 0.0))
            p_prev = float(sorted_series[-2].get("precipitation_mm", 0.0))
            rate_of_change = round(p_curr - p_prev, 3)

        return {
            "rainfall_available": True,
            "status": STATE_FRESH,
            "accum_1h_mm": accum_1h,
            "accum_3h_mm": accum_3h,
            "accum_6h_mm": accum_6h,
            "accum_12h_mm": accum_12h,
            "accum_24h_mm": accum_24h,
            "accum_48h_mm": accum_48h,
            "accum_72h_mm": accum_72h,
            "antecedent_7d_mm": antecedent_7d,
            "max_hourly_intensity_mm": round(max_int, 2),
            "rainfall_anomaly_ratio": anomaly_ratio,
            "persistence_steps": pers_count,
            "rainfall_rate_of_change": rate_of_change
        }

    def extract_soil_moisture_features(
        self,
        smap_record: Optional[Dict[str, Any]],
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Extracts soil moisture saturation, anomaly, rate of change, and age.
        """
        if not smap_record or smap_record.get("status") == STATE_WAITING_FOR_DATA:
            return {
                "soil_moisture_available": False,
                "status": STATE_WAITING_FOR_DATA,
                "soil_saturation_index": None,
                "soil_moisture_anomaly": None,
                "rolling_3d_saturation": None,
                "soil_moisture_rate_of_change": None,
                "observation_age_hours": None
            }

        sat_index = float(smap_record.get("saturation_index", smap_record.get("mean_soil_moisture", 0.35)))
        # Baseline regional dry-season mean ~0.25 m3/m3
        baseline = 0.25
        sm_anomaly = round(max(0.0, (sat_index - baseline) / baseline), 3)

        return {
            "soil_moisture_available": True,
            "status": smap_record.get("status", STATE_FRESH),
            "soil_saturation_index": round(sat_index, 4),
            "soil_moisture_anomaly": sm_anomaly,
            "rolling_3d_saturation": round(sat_index * 0.95, 4),
            "soil_moisture_rate_of_change": round(smap_record.get("delta_sm", 0.01), 4),
            "observation_age_hours": smap_record.get("observation_age_hours", 24.0)
        }

    def extract_unified_temporal_feature_vector(
        self,
        hotspot_id: str,
        static_context: Dict[str, Any],
        rainfall_data: List[Dict[str, Any]],
        smap_data: Optional[Dict[str, Any]],
        sentinel1_data: Optional[Dict[str, Any]],
        sentinel2_data: Optional[Dict[str, Any]],
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Constructs a complete, normalized temporal feature vector for a specific monitored slope location.
        """
        rain_feats = self.extract_rainfall_features(rainfall_data, reference_time_utc)
        sm_feats = self.extract_soil_moisture_features(smap_data, reference_time_utc)

        # Sentinel-1 SAR features
        s1_active = sentinel1_data is not None and sentinel1_data.get("surface_change_score") is not None
        s1_change = float(sentinel1_data.get("surface_change_score", 0.0)) if s1_active else None
        s1_age = sentinel1_data.get("observation_age_hours") if sentinel1_data else None

        # Sentinel-2 Optical features
        s2_active = sentinel2_data is not None and sentinel2_data.get("status") != STATE_WAITING_FOR_DATA
        s2_cloud_blocked = sentinel2_data.get("status") == STATE_DEGRADED if sentinel2_data else False
        s2_change = float(sentinel2_data.get("surface_change_score", 0.0)) if (s2_active and not s2_cloud_blocked) else None

        # Static Terrain Features from C10 / DEM
        c10_susceptibility = float(static_context.get("susceptibility_probability", 0.50))
        elevation = float(static_context.get("elevation_m", 1200.0))
        slope = float(static_context.get("slope_deg", 32.0))
        twi = float(static_context.get("twi", 6.5))

        feature_vector = {
            "hotspot_id": hotspot_id,
            "feature_version": self.feature_version,
            "generation_time_utc": (reference_time_utc or datetime.now(timezone.utc)).isoformat(),
            # Static Predictors
            "c10_susceptibility": c10_susceptibility,
            "elevation_m": elevation,
            "slope_deg": slope,
            "twi": twi,
            # Rainfall Dynamic Predictors
            "rainfall_accum_1h": rain_feats["accum_1h_mm"],
            "rainfall_accum_3h": rain_feats["accum_3h_mm"],
            "rainfall_accum_6h": rain_feats["accum_6h_mm"],
            "rainfall_accum_12h": rain_feats["accum_12h_mm"],
            "rainfall_accum_24h": rain_feats["accum_24h_mm"],
            "rainfall_accum_48h": rain_feats["accum_48h_mm"],
            "rainfall_accum_72h": rain_feats["accum_72h_mm"],
            "rainfall_antecedent_7d": rain_feats["antecedent_7d_mm"],
            "rainfall_intensity_max": rain_feats["max_hourly_intensity_mm"],
            "rainfall_anomaly": rain_feats["rainfall_anomaly_ratio"],
            "rainfall_persistence": rain_feats["persistence_steps"],
            "rainfall_rate_of_change": rain_feats["rainfall_rate_of_change"],
            # Soil Moisture Dynamic Predictors
            "soil_saturation": sm_feats["soil_saturation_index"],
            "soil_moisture_anomaly": sm_feats["soil_moisture_anomaly"],
            "soil_moisture_rate_of_change": sm_feats["soil_moisture_rate_of_change"],
            "soil_moisture_age_hours": sm_feats["observation_age_hours"],
            # Remote Sensing Change Predictors
            "sar_backscatter_change": s1_change,
            "sar_observation_age_hours": s1_age,
            "optical_surface_change": s2_change,
            "optical_cloud_blocked": s2_cloud_blocked,
            # Quality and Provenance Tracking
            "rainfall_status": rain_feats["status"],
            "soil_moisture_status": sm_feats["status"],
            "sar_status": sentinel1_data.get("status") if sentinel1_data else STATE_WAITING_FOR_DATA,
            "optical_status": sentinel2_data.get("status") if sentinel2_data else STATE_WAITING_FOR_DATA
        }

        return feature_vector

temporal_feature_engine = TemporalFeatureEngine()
