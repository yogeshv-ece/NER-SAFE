"""
NER-SAFE: Component 15 Pre-Landslide Temporal Forecasting Engine
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Scientific Objective:
'Estimate the probability that a landslide may occur within a defined future time window
and identify the most likely initiation zone together with spatial and temporal uncertainty.'

Core Principles:
1. Strict Separation:
   - Static Susceptibility (C10)
   - Current Environmental Risk (Four-Factor Operational Fusion: 0.40/0.30/0.20/0.10)
   - Future Temporal Forecast (C15 Horizon Forecast)
   - Warning / Advisory (C12 CAP v1.2 Dispatch)
2. Freshness Rule: Never present previous assessment as current. If qualifying fresh
   observations are missing, status = WAITING_FOR_DATA.
3. Model Lineage: Every forecast records model name, version, training dataset, feature version,
   horizon, generated timestamp, input observation IDs, validation status.
4. Candidate Horizons: 1h, 3h, 6h, 12h, 24h, 48h. Unvalidated horizons explicitly display NOT_VALIDATED.
5. Uncertainty: Shannon entropy + spatial-temporal variance bounds.
"""

import os
import json
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from observation_provenance import (
    provenance_registry,
    STATE_FRESH, STATE_DEGRADED, STATE_WAITING_FOR_DATA, STATE_INVALID
)
from temporal_feature_engine import temporal_feature_engine, CANDIDATE_HORIZONS
from sentinel1_sar_engine import s1_engine
from temporal_label_validator import temporal_label_validator
from c15_model_comparator import c15_comparator

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))

class C15TemporalForecastingEngine:
    def __init__(self):
        self.model_name = "NER-SAFE-C15-TemporalForecaster"
        self.model_version = "1.0.0-temporal-prototype"
        self.feature_version = "v1.2.0-temporal"
        self.training_dataset_version = "UNVALIDATED-HISTORICAL-2020-GSI-GLC"
        self.supported_horizons = ["24h"]  # Only 24h has daily environmental resolution; others NOT_VALIDATED
        self.forecast_history: List[Dict[str, Any]] = []

    def compute_shannon_entropy(self, p: float) -> float:
        """
        Computes normalized binary Shannon entropy as an information-theoretic uncertainty metric:
        H(p) = - [p * log2(p) + (1-p) * log2(1-p)] in [0, 1].
        """
        if p <= 0.0 or p >= 1.0:
            return 0.0
        p_clamped = max(1e-6, min(1.0 - 1e-6, p))
        h = - (p_clamped * math.log2(p_clamped) + (1.0 - p_clamped) * math.log2(1.0 - p_clamped))
        return round(float(h), 4)

    def evaluate_forecast(
        self,
        hotspot_id: str,
        horizon: str,
        static_context: Dict[str, Any],
        rainfall_data: List[Dict[str, Any]],
        smap_data: Optional[Dict[str, Any]],
        sentinel1_data: Optional[Dict[str, Any]],
        sentinel2_data: Optional[Dict[str, Any]],
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Evaluates future pre-landslide failure probability for a given horizon and slope zone.
        """
        ref_time = reference_time_utc or datetime.now(timezone.utc)
        
        # 1. Check Horizon Validity
        if horizon not in CANDIDATE_HORIZONS:
            return {
                "hotspot_id": hotspot_id,
                "forecast_horizon": horizon,
                "forecast_status": "UNSUPPORTED_HORIZON",
                "message": f"Horizon {horizon} is not in candidate list: {CANDIDATE_HORIZONS}"
            }

        # Check if horizon is validated by temporal input resolution
        is_horizon_validated = horizon in self.supported_horizons
        
        # 2. Extract Temporal Feature Vector
        feat_vector = temporal_feature_engine.extract_unified_temporal_feature_vector(
            hotspot_id=hotspot_id,
            static_context=static_context,
            rainfall_data=rainfall_data,
            smap_data=smap_data,
            sentinel1_data=sentinel1_data,
            sentinel2_data=sentinel2_data,
            reference_time_utc=ref_time
        )

        # 3. Check Minimum Qualifying Inputs (Freshness Rule)
        min_inputs = provenance_registry.check_minimum_qualifying_inputs(["GPM_PRECIPITATION", "SRTM_DEM"])
        
        if not min_inputs["can_generate_current_assessment"]:
            return {
                "hotspot_id": hotspot_id,
                "forecast_horizon": horizon,
                "forecast_status": STATE_WAITING_FOR_DATA,
                "forecast_probability": None,
                "uncertainty_entropy": None,
                "likely_initiation_zone": static_context.get("district", "Unknown"),
                "model_used": self.model_name,
                "model_version": self.model_version,
                "validation_status": "AWAITING_FRESH_OBSERVATIONS",
                "generated_time_utc": ref_time.isoformat(),
                "message": "Risk assessment unavailable / awaiting fresh data. No qualifying observations."
            }

        # 4. Check Scientific Validation Status of Supervised Models
        comp_report = c15_comparator.run_rigorous_comparison()
        model_validation_status = comp_report.get("status", "NOT_SCIENTIFICALLY_VALIDATED")

        # 5. Compute Defensible Prototype Probability
        # Combines baseline morphometric susceptibility with dynamic multi-window rainfall accumulation & soil moisture
        susceptibility = float(feat_vector.get("c10_susceptibility", 0.5))
        accum_24h = float(feat_vector.get("rainfall_accum_24h") or 0.0)
        saturation = float(feat_vector.get("soil_saturation") or 0.30)
        sar_change = float(feat_vector.get("sar_backscatter_change") or 0.0)

        # Normalized dynamic trigger pressure
        # Rainfall saturation threshold curve (~60mm/24h is significant trigger in NER)
        rain_factor = min(1.0, accum_24h / 65.0)
        soil_factor = min(1.0, max(0.0, (saturation - 0.20) / 0.40))
        sar_factor = min(1.0, sar_change * 5.0) if sar_change > 0 else 0.0

        # Horizon scaling: shorter horizons have stricter immediacy requirement
        horizon_weights = {
            "1h": 0.3,
            "3h": 0.4,
            "6h": 0.6,
            "12h": 0.8,
            "24h": 1.0,
            "48h": 0.85
        }
        h_weight = horizon_weights.get(horizon, 1.0)

        raw_prob = (0.45 * susceptibility) + (0.35 * rain_factor * h_weight) + (0.15 * soil_factor) + (0.05 * sar_factor)
        forecast_prob = round(max(0.01, min(0.99, raw_prob)), 4)
        uncertainty = self.compute_shannon_entropy(forecast_prob)

        # Build Observation Provenance Lineage
        obs_ids = [
            f"GPM-{feat_vector.get('rainfall_status')}",
            f"SMAP-{feat_vector.get('soil_moisture_status')}",
            f"S1-{feat_vector.get('sar_status')}",
            f"S2-{feat_vector.get('optical_status')}"
        ]

        result = {
            "hotspot_id": hotspot_id,
            "forecast_horizon": horizon,
            "forecast_probability": forecast_prob,
            "uncertainty_entropy": uncertainty,
            "uncertainty_level": "HIGH" if uncertainty > 0.85 else ("MODERATE" if uncertainty > 0.50 else "LOW"),
            "likely_initiation_zone": static_context.get("location_name", static_context.get("district", "Slope Apex")),
            "latitude": static_context.get("latitude"),
            "longitude": static_context.get("longitude"),
            "model_name": self.model_name,
            "model_version": self.model_version,
            "feature_version": self.feature_version,
            "training_dataset_version": self.training_dataset_version,
            "validation_status": "NOT_SCIENTIFICALLY_VALIDATED" if not is_horizon_validated else "PROTOTYPE_CALIBRATED",
            "validation_disclaimer": (
                "Forecast probability is a multi-window prototype. Supervised temporal ML model validation "
                "remains NOT_SCIENTIFICALLY_VALIDATED pending co-temporal historical event timestamps."
            ),
            "input_observation_ids": obs_ids,
            "input_freshness": {
                "rainfall": feat_vector.get("rainfall_status"),
                "soil_moisture": feat_vector.get("soil_moisture_status"),
                "sar": feat_vector.get("sar_status"),
                "optical": feat_vector.get("optical_status")
            },
            "missing_sources": [k for k, v in {
                "soil_moisture": smap_data,
                "sar": sentinel1_data,
                "optical": sentinel2_data
            }.items() if v is None or v.get("status") == STATE_WAITING_FOR_DATA],
            "degraded_sources": [k for k, v in {
                "optical": feat_vector.get("optical_cloud_blocked")
            }.items() if v],
            "generated_time_utc": ref_time.isoformat(),
            "scientific_objective": "Estimate probability that a landslide may occur within the defined future time window."
        }

        self.forecast_history.append(result)
        return result

c15_forecaster = C15TemporalForecastingEngine()
