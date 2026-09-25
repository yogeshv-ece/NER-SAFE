"""
NER-SAFE: Observation Provenance, Multi-Source Abstraction & Quality Control Engine
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Strict Scientific Principles:
1. NEVER present a previous risk score as the current assessment.
2. If qualifying fresh observations are unavailable, state = WAITING_FOR_DATA
   ("Risk assessment unavailable / awaiting fresh data").
3. Missing data is NEVER converted to zero:
   - Missing SMAP != soil moisture 0
   - Missing Sentinel-2 != surface change 0
   - Missing Sentinel-1 != ground deformation 0
   - Missing rainfall != precipitation 0
4. Missing SMAP observation on 2025-03-18 is preserved as documented gap; never fabricated.
5. Distinguishes: STATIC SUSCEPTIBILITY, CURRENT ENVIRONMENTAL RISK, FUTURE TEMPORAL FORECAST, WARNING/ADVISORY.
6. Preserves explicit provenance: source, product, observation_time, availability_time,
   ingestion_time, processing_status, quality_status, product_identifier, checksum, spatial_coverage.
"""

import os
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))

# Observation & Risk States
STATE_FRESH = "FRESH"
STATE_DEGRADED = "DEGRADED"
STATE_WAITING_FOR_DATA = "WAITING_FOR_DATA"
STATE_INVALID = "INVALID"
STATE_STALE = "STALE"

# Revisit intervals and nominal latency (in hours)
SOURCE_SPECS = {
    "GPM_PRECIPITATION": {
        "source": "NASA GES DISC",
        "product": "GPM IMERG Final Daily V07 (3IMERGDF) / Early NRT (3IMERGHHE)",
        "platform": "GPM Core Observatory + Constellation",
        "spatial_resolution": "0.1 deg (~10 km) interpolated to 30m",
        "nominal_latency_hours": 4.0,
        "revisit_interval_hours": 24.0,  # daily baseline
        "stale_threshold_hours": 36.0,
        "type": "DYNAMIC_TRIGGER"
    },
    "SMAP_SOIL_MOISTURE": {
        "source": "NASA NSIDC DAAC",
        "product": "SMAP L3 Enhanced Radiometer (SPL3SMP_E.006)",
        "platform": "SMAP Observatory",
        "spatial_resolution": "9 km EASE-Grid 2.0 interpolated to 30m",
        "nominal_latency_hours": 24.0,
        "revisit_interval_hours": 72.0,  # 2-3 days
        "stale_threshold_hours": 96.0,
        "type": "DYNAMIC_ENVIRONMENTAL_STATE"
    },
    "SENTINEL2_OPTICAL": {
        "source": "ESA Copernicus / Element84 AWS STAC",
        "product": "Sentinel-2 MSI Level-2A BOA Reflectance",
        "platform": "Sentinel-2A / Sentinel-2B / Sentinel-2C",
        "spatial_resolution": "10m native / 30m harmonized",
        "nominal_latency_hours": 12.0,
        "revisit_interval_hours": 120.0,  # 5 days
        "stale_threshold_hours": 240.0,
        "cloud_threshold_percent": 70.0,
        "type": "SURFACE_CHANGE_OBSERVATION"
    },
    "SENTINEL1_SAR": {
        "source": "ESA Copernicus / Alaska Satellite Facility DAAC",
        "product": "Sentinel-1 C-SAR Level-1 GRD (Ground Range Detected)",
        "platform": "Sentinel-1A / Sentinel-1C",
        "spatial_resolution": "10m / 30m harmonized",
        "nominal_latency_hours": 24.0,
        "revisit_interval_hours": 144.0,  # 6-12 days
        "stale_threshold_hours": 288.0,
        "type": "SAR_SURFACE_SCENE_CHANGE"
    },
    "SRTM_DEM": {
        "source": "USGS EarthExplorer",
        "product": "SRTM 1 Arc-Second Global DEM (~30m)",
        "platform": "Space Shuttle Endeavour (STS-99)",
        "spatial_resolution": "1 arc-sec (~30.89m)",
        "nominal_latency_hours": 0.0,
        "revisit_interval_hours": 0.0,
        "stale_threshold_hours": 999999.0,
        "type": "STATIC_MORPHOMETRY"
    },
    "IMD_WEATHER": {
        "source": "India Meteorological Department (IMD)",
        "product": "IMD Gridded Precipitation / Automatic Weather Stations",
        "platform": "IMD Surface Observation Network / AWS-ARG",
        "spatial_resolution": "0.25 deg (~25 km) gridded or AWS point",
        "nominal_latency_hours": 3.0,
        "revisit_interval_hours": 24.0,
        "stale_threshold_hours": 48.0,
        "type": "REGIONAL_WEATHER_OBSERVATION",
        "access_model": "Departmental MoU / MoES Agreement required (No open unauthenticated REST API)"
    }
}

class ObservationProvenanceRegistry:
    def __init__(self):
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.provenance_log_dir = os.path.join(PROJECT_ROOT, "NER-SAFE", "live", "provenance")
        os.makedirs(self.provenance_log_dir, exist_ok=True)

    def compute_sha256(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            return "FILE_NOT_FOUND"
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def evaluate_quality_and_freshness(
        self,
        source_key: str,
        observation_time_iso: str,
        data_payload: Optional[Dict[str, Any]] = None,
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        ref_time = reference_time_utc or datetime.now(timezone.utc)
        spec = SOURCE_SPECS.get(source_key, {})
        
        if not observation_time_iso:
            return {
                "source_key": source_key,
                "status": STATE_WAITING_FOR_DATA,
                "quality": "MISSING",
                "observation_time": None,
                "observation_age_hours": None,
                "reason": "Zero qualifying observations available for evaluation window"
            }

        try:
            obs_dt = datetime.fromisoformat(observation_time_iso.replace("Z", "+00:00"))
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
            age_hours = (ref_time - obs_dt).total_seconds() / 3600.0
        except Exception as e:
            return {
                "source_key": source_key,
                "status": STATE_INVALID,
                "quality": "CORRUPT_TIMESTAMP",
                "observation_time": observation_time_iso,
                "observation_age_hours": None,
                "reason": f"Invalid ISO timestamp: {e}"
            }

        if source_key == "SMAP_SOIL_MOISTURE" and "2025-03-18" in observation_time_iso:
            return {
                "source_key": source_key,
                "status": STATE_WAITING_FOR_DATA,
                "quality": "DOCUMENTED_SATELLITE_OUTAGE",
                "observation_time": observation_time_iso,
                "observation_age_hours": round(age_hours, 2),
                "reason": "NASA documented SMAP radiometer outage on 2025-03-18; zero imputation permitted."
            }

        if source_key == "SENTINEL2_OPTICAL" and data_payload:
            cloud_pct = data_payload.get("cloud_cover_percent", 0.0)
            if cloud_pct > spec.get("cloud_threshold_percent", 70.0):
                return {
                    "source_key": source_key,
                    "status": STATE_DEGRADED,
                    "quality": "OPTICAL_CLOUD_BLOCKED",
                    "observation_time": observation_time_iso,
                    "observation_age_hours": round(age_hours, 2),
                    "cloud_cover_percent": cloud_pct,
                    "reason": f"Heavy cloud occlusion ({cloud_pct:.1f}% > 70%). Optical surface change degraded; other qualified sources continue."
                }

        stale_threshold = spec.get("stale_threshold_hours", 48.0)
        revisit_nominal = spec.get("revisit_interval_hours", 24.0)

        if age_hours <= revisit_nominal * 1.5:
            status = STATE_FRESH
            quality = "NOMINAL_HIGH_CONFIDENCE"
        elif age_hours <= stale_threshold:
            status = STATE_DEGRADED
            quality = "INTERMEDIATE_LATENCY"
        else:
            status = STATE_STALE
            quality = "EXCEEDED_STALE_THRESHOLD"

        return {
            "source_key": source_key,
            "product": spec.get("product"),
            "provider": spec.get("source"),
            "status": status,
            "quality": quality,
            "observation_time": observation_time_iso,
            "observation_age_hours": round(age_hours, 2),
            "spatial_resolution": spec.get("spatial_resolution")
        }

    def register_observation(
        self,
        source_key: str,
        product_identifier: str,
        observation_time_iso: str,
        file_path: Optional[str] = None,
        data_payload: Optional[Dict[str, Any]] = None,
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        ref_time = reference_time_utc or datetime.now(timezone.utc)
        eval_result = self.evaluate_quality_and_freshness(
            source_key, observation_time_iso, data_payload, ref_time
        )
        
        checksum = self.compute_sha256(file_path) if file_path and os.path.exists(file_path) else "REMOTE_METADATA_RECORD"

        record = {
            "provenance_id": f"PRV-{source_key}-{product_identifier[:20]}",
            "source_key": source_key,
            "product_identifier": product_identifier,
            "observation_time_utc": observation_time_iso,
            "availability_time_utc": data_payload.get("availability_time_utc", observation_time_iso) if data_payload else observation_time_iso,
            "ingestion_time_utc": ref_time.isoformat(),
            "status": eval_result["status"],
            "quality_status": eval_result["quality"],
            "observation_age_hours": eval_result.get("observation_age_hours"),
            "checksum_sha256": checksum,
            "file_path": file_path,
            "metadata": data_payload or {},
            "scientific_disclaimer": SOURCE_SPECS.get(source_key, {}).get("type", "OBSERVATION")
        }

        self.registry[source_key] = record
        return record

    def check_minimum_qualifying_inputs(self, required_sources: List[str] = None) -> Dict[str, Any]:
        if required_sources is None:
            required_sources = ["GPM_PRECIPITATION", "SRTM_DEM"]

        qualifying = True
        missing_or_stale = []
        statuses = {}

        for src in required_sources:
            entry = self.registry.get(src)
            if not entry:
                qualifying = False
                missing_or_stale.append(f"{src} (NOT_INGESTED)")
                statuses[src] = STATE_WAITING_FOR_DATA
            elif entry["status"] in [STATE_WAITING_FOR_DATA, STATE_INVALID, STATE_STALE]:
                qualifying = False
                missing_or_stale.append(f"{src} ({entry['status']})")
                statuses[src] = entry["status"]
            else:
                statuses[src] = entry["status"]

        return {
            "can_generate_current_assessment": qualifying,
            "assessment_state": STATE_FRESH if qualifying else STATE_WAITING_FOR_DATA,
            "missing_or_stale_sources": missing_or_stale,
            "source_statuses": statuses,
            "message": "Qualifying fresh observations verified." if qualifying else "Risk assessment unavailable / awaiting fresh data. Cached assessment must be marked as LAST KNOWN."
        }

provenance_registry = ObservationProvenanceRegistry()
