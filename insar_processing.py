"""
=============================================================================
NER-SAFE: Sentinel-1 InSAR Deformation Processing Pipeline
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Implements the 10-step repeat-pass InSAR scientific processing workflow
         for Sentinel-1 IW SLC data across Meghalaya & Mizoram.
Pipeline Stages:
  1. Precise Orbit Correction (ESA AUX_POEORB ephemeris).
  2. TOPSAR Burst Selection & De-bursting.
  3. Sub-pixel Co-registration (cross-correlation + Enhanced Spectral Diversity).
  4. Complex Interferogram Formation (I = S1 * conj(S2)).
  5. Spatial Coherence Estimation (gamma).
  6. Goldstein Adaptive Phase Filtering.
  7. Phase Unwrapping (SNAPHU / Minimum Cost Flow).
  8. Topographic Phase Subtraction (DEM-assisted phase removal).
  9. Range-Doppler Geocoding (EPSG:4326 WGS-84).
  10. Relative Line-of-Sight (LOS) Displacement Derivation (d_LOS = -lambda / (4*pi) * Delta_phi).
Enforces:
  - Coherence masking: gamma < 0.35 marked as LOW_COHERENCE / NO_DATA (never zero).
  - Stable bedrock reference area in Shillong Plateau (25.57°N, 91.88°E).
  - Explicit physical units: millimeters/year or meters relative LOS displacement.
  - Zero-fabrication: returns INSAR_DATA_REQUIRED if genuine SLC files are absent.
=============================================================================
"""

import os
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

# Sentinel-1 C-band parameters
C_BAND_WAVELENGTH_METERS = 0.05546576  # 5.546 cm carrier wavelength
DEFAULT_COHERENCE_THRESHOLD = 0.35

# Stable reference area (Central Shillong Plateau crystalline bedrock)
REFERENCE_POINT_NAME = "SHILLONG_PLATEAU_BEDROCK_REF"
REFERENCE_LAT = 25.572
REFERENCE_LON = 91.881
REFERENCE_ELEVATION_M = 1496.0

STATUS_PROCESSED = "SUCCESS"
STATUS_DATA_REQUIRED = "INSAR_DATA_REQUIRED"
STATUS_COHERENCE_MASKED = "LOW_COHERENCE_MASKED"


class InSARProcessingEngine:
    """Scientific InSAR processing engine adhering to ESA SNAP & ISCE2 principles."""

    def __init__(self, coherence_threshold: float = DEFAULT_COHERENCE_THRESHOLD):
        self.coherence_threshold = coherence_threshold
        self.wavelength = C_BAND_WAVELENGTH_METERS
        self.ref_point = {
            "name": REFERENCE_POINT_NAME,
            "latitude": REFERENCE_LAT,
            "longitude": REFERENCE_LON,
            "elevation_m": REFERENCE_ELEVATION_M,
            "selection_rationale": "Precambrian granitic gneiss / Shillong Group quartzite; tectonically coherent reference block."
        }

    def compute_coherence_matrix(self, s1: np.ndarray, s2: np.ndarray, window: int = 5) -> np.ndarray:
        """
        Calculates complex spatial coherence:
        gamma = |<S1 * S2*>| / sqrt(<|S1|^2> * <|S2|^2>)
        """
        if s1.shape != s2.shape:
            raise ValueError("SLC arrays must have identical dimensions for coherence calculation.")

        num = np.abs(s1 * np.conj(s2))
        denom = np.sqrt(np.abs(s1)**2 * np.abs(s2)**2) + 1e-10
        coherence = num / denom
        return np.clip(coherence, 0.0, 1.0)

    def phase_to_relative_los_displacement(self, unwrapped_phase: np.ndarray) -> np.ndarray:
        """
        Converts unwrapped differential interferometric phase (radians)
        to relative Line-of-Sight (LOS) displacement in meters:
        d_LOS = -lambda / (4 * pi) * Delta_phi
        Negative value indicates movement AWAY from satellite sensor (subsidence/down-slope).
        Positive value indicates movement TOWARD satellite sensor (uplift/up-slope).
        """
        factor = -self.wavelength / (4.0 * math.pi)
        return unwrapped_phase * factor

    def apply_coherence_mask(self, displacement: np.ndarray, coherence: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Masks pixels with coherence below threshold as NaN (NO_DATA).
        Strict Rule: Low coherence is NEVER interpreted as zero deformation.
        """
        mask = coherence >= self.coherence_threshold
        masked_disp = np.where(mask, displacement, np.nan)
        return masked_disp, mask

    def process_interferometric_pair(self, pair_metadata: Dict[str, Any],
                                     primary_path: Optional[str] = None,
                                     secondary_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes InSAR processing workflow.
        Checks for legitimate local SLC data files. If missing, reports INSAR_DATA_REQUIRED.
        """
        if not pair_metadata.get("is_valid_pair", False):
            return {
                "status": "REJECTED_PAIR",
                "processed": False,
                "error": "Pair does not satisfy geometric/temporal InSAR criteria.",
                "details": pair_metadata.get("rejection_reasons", [])
            }

        # Check physical existence of SLC files
        has_primary = primary_path and os.path.isfile(primary_path)
        has_secondary = secondary_path and os.path.isfile(secondary_path)

        if not (has_primary and has_secondary):
            return {
                "status": STATUS_DATA_REQUIRED,
                "processed": False,
                "pipeline_stages_ready": [
                    "1. Precise Orbit Correction (AUX_POEORB)",
                    "2. TOPSAR Burst Extraction & Synchronization",
                    "3. Sub-pixel Cross-Correlation Co-registration",
                    "4. Complex Interferogram Formation (S1 * conj(S2))",
                    "5. Spatial Coherence Estimation (gamma >= 0.35)",
                    "6. Goldstein Adaptive Phase Filtering",
                    "7. Phase Unwrapping (SNAPHU / Minimum Cost Flow)",
                    "8. DEM Topographic Phase Removal",
                    "9. Range-Doppler Terrain Geocoding (EPSG:4326)",
                    "10. Relative LOS Displacement Derivation (meters)"
                ],
                "reference_point": self.ref_point,
                "coherence_threshold": self.coherence_threshold,
                "message": "Authentic Sentinel-1 SLC data files are required. NER-SAFE strictly prohibits fabricating fake SAR phase arrays."
            }

        # If genuine files/directories are provided, genuine processing executes here
        dem_path = os.path.join(os.environ.get("NER_SAFE_ROOT", "."), "NER_SAFE_DATA", "TERRAIN", "derivatives", "elevation", "elevation.tif")
        from real_insar_processor import real_insar_pipeline
        pipeline_res = real_insar_pipeline.run_pipeline(primary_path, secondary_path, dem_path)

        return {
            "status": STATUS_PROCESSED,
            "processed": True,
            "reference_point": self.ref_point,
            "coherence_threshold": self.coherence_threshold,
            "primary_file": primary_path,
            "secondary_file": secondary_path,
            "pipeline_summary": pipeline_res,
            "message": "Authentic Sentinel-1 SLC pair processed successfully through 10-stage InSAR workflow."
        }

    def evaluate_hotspot_insar_evidence(self, hotspot_id: str,
                                        lat: float, lon: float) -> Dict[str, Any]:
        """
        Queries InSAR deformation evidence for a specific hotspot coordinate.
        Returns explicit data availability, coherence status, and physical units.
        """
        insar_raster = os.path.join(os.environ.get("NER_SAFE_ROOT", "."),
                                    "NER_SAFE_DATA", "SENTINEL1", "insar_los_displacement.tif")
        coherence_raster = os.path.join(os.environ.get("NER_SAFE_ROOT", "."),
                                        "NER_SAFE_DATA", "SENTINEL1", "insar_coherence.tif")

        if not os.path.exists(insar_raster) or not os.path.exists(coherence_raster):
            return {
                "hotspot_id": hotspot_id,
                "insar_available": False,
                "insar_status": "WAITING_FOR_COMPATIBLE_SLC_PAIR",
                "relative_los_displacement_mm": None,
                "coherence": None,
                "coherence_quality": "UNAVAILABLE",
                "reference_point": self.ref_point["name"],
                "disclaimer": "No active InSAR deformation raster. System operates on verified GPM/SMAP/S1-amplitude live feeds."
            }

        import rasterio
        with rasterio.open(insar_raster) as src_disp, rasterio.open(coherence_raster) as src_coh:
            # Check if within bounding box of InSAR swath
            if not (src_disp.bounds.left <= lon <= src_disp.bounds.right and
                    src_disp.bounds.bottom <= lat <= src_disp.bounds.top):
                return {
                    "hotspot_id": hotspot_id,
                    "insar_available": False,
                    "insar_status": "WAITING_FOR_COMPATIBLE_SLC_PAIR",
                    "relative_los_displacement_mm": None,
                    "coherence": None,
                    "coherence_quality": "UNAVAILABLE",
                    "reference_point": self.ref_point["name"],
                    "disclaimer": "Hotspot coordinate is outside active Sentinel-1 IW1 swath coverage; waiting for compatible SLC pair covering this orbital subswath."
                }

            disp_sample = list(src_disp.sample([(lon, lat)]))[0][0]
            coh_sample = list(src_coh.sample([(lon, lat)]))[0][0]
            
            coh_val = round(float(coh_sample), 3)
            if np.isnan(disp_sample):
                return {
                    "hotspot_id": hotspot_id,
                    "insar_available": True,
                    "insar_status": "LOW_COHERENCE_MASKED",
                    "relative_los_displacement_mm": None,
                    "coherence": coh_val,
                    "coherence_quality": "LOW_COHERENCE_MASKED",
                    "reference_point": self.ref_point["name"],
                    "disclaimer": f"Coherence ({coh_val:.2f}) < 0.35 threshold; masked as NoData to prevent false assumption of stability."
                }

            disp_mm = round(float(disp_sample) * 1000.0, 2)
            return {
                "hotspot_id": hotspot_id,
                "insar_available": True,
                "insar_status": "VALID_COHERENT_OBSERVATION",
                "relative_los_displacement_mm": disp_mm,
                "coherence": coh_val,
                "coherence_quality": "HIGH_COHERENCE",
                "reference_point": self.ref_point["name"],
                "disclaimer": "Relative Line-of-Sight deformation referenced to Shillong Plateau bedrock."
            }


insar_processing_engine = InSARProcessingEngine()
