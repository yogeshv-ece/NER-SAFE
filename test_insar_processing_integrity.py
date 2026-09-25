"""
=============================================================================
NER-SAFE: Test Suite for InSAR Processing Pipeline Integrity
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validates mathematical and operational integrity of InSAR processing:
  1. Coherence calculation matrix values in [0, 1].
  2. Phase to relative LOS displacement formula (C-band lambda = 0.05546576 m).
  3. Coherence threshold masking (low coherence masked as NaN, never zero).
  4. Stable bedrock reference point configuration (Shillong Plateau).
  5. Zero-fabrication: reports INSAR_DATA_REQUIRED when genuine SLC files are absent.
  6. Scientific limitation disclaimers (no vertical displacement claim without 3D decomposition).
=============================================================================
"""

import math
import unittest
import numpy as np
from insar_processing import (
    InSARProcessingEngine,
    C_BAND_WAVELENGTH_METERS,
    DEFAULT_COHERENCE_THRESHOLD,
    STATUS_DATA_REQUIRED,
    REFERENCE_POINT_NAME
)

class TestInSARProcessingIntegrity(unittest.TestCase):
    def setUp(self):
        self.engine = InSARProcessingEngine()

    def test_01_coherence_matrix_bounds(self):
        """Verifies complex spatial coherence is strictly bounded in [0.0, 1.0]."""
        np.random.seed(42)
        s1 = np.random.randn(10, 10) + 1j * np.random.randn(10, 10)
        s2 = s1 + 0.1 * (np.random.randn(10, 10) + 1j * np.random.randn(10, 10))
        gamma = self.engine.compute_coherence_matrix(s1, s2)
        self.assertEqual(gamma.shape, (10, 10))
        self.assertTrue(np.all(gamma >= 0.0))
        self.assertTrue(np.all(gamma <= 1.0))

    def test_02_phase_to_relative_los_formula(self):
        """Verifies phase-to-displacement conversion adheres to d_LOS = -lambda / (4*pi) * Delta_phi."""
        phase = np.array([0.0, 2.0 * math.pi, -2.0 * math.pi])
        disp = self.engine.phase_to_relative_los_displacement(phase)
        expected_half_lambda = -C_BAND_WAVELENGTH_METERS / 2.0
        self.assertAlmostEqual(disp[0], 0.0, places=6)
        self.assertAlmostEqual(disp[1], expected_half_lambda, places=6)
        self.assertAlmostEqual(disp[2], -expected_half_lambda, places=6)

    def test_03_coherence_masking_never_zeros(self):
        """
        Verifies that low coherence pixels are masked as NaN/NO_DATA and
        NEVER treated as zero deformation (which would falsely imply stability).
        """
        disp = np.array([0.012, -0.045, 0.003, -0.018])
        coherence = np.array([0.85, 0.20, 0.60, 0.15])  # Two below 0.35
        masked_disp, mask = self.engine.apply_coherence_mask(disp, coherence)
        
        # Valid pixels retained
        self.assertEqual(masked_disp[0], 0.012)
        self.assertEqual(masked_disp[2], 0.003)
        # Invalid pixels are NaN
        self.assertTrue(np.isnan(masked_disp[1]))
        self.assertTrue(np.isnan(masked_disp[3]))
        # Ensure mask correctly identifies invalid pixels
        self.assertFalse(mask[1])
        self.assertFalse(mask[3])

    def test_04_stable_bedrock_reference_area(self):
        """Verifies reproducible stable bedrock reference point configuration."""
        ref = self.engine.ref_point
        self.assertEqual(ref["name"], REFERENCE_POINT_NAME)
        self.assertAlmostEqual(ref["latitude"], 25.572, places=3)
        self.assertAlmostEqual(ref["longitude"], 91.881, places=3)
        self.assertIn("Precambrian", ref["selection_rationale"])

    def test_05_zero_fabrication_on_missing_slc(self):
        """
        Verifies that when SLC files are absent on disk, the engine honestly
        returns INSAR_DATA_REQUIRED and does not fabricate phase arrays.
        """
        valid_pair_meta = {
            "is_valid_pair": True,
            "primary_id": "S1A_IW_SLC__1SDV_20260901...",
            "secondary_id": "S1A_IW_SLC__1SDV_20260913...",
            "pair_status": "OPTIMAL"
        }
        res = self.engine.process_interferometric_pair(valid_pair_meta,
                                                       primary_path=None,
                                                       secondary_path=None)
        self.assertEqual(res["status"], STATUS_DATA_REQUIRED)
        self.assertFalse(res["processed"])
        self.assertIn("pipeline_stages_ready", res)
        self.assertEqual(len(res["pipeline_stages_ready"]), 10)
        self.assertIn("prohibits fabricating fake SAR phase arrays", res["message"])

    def test_06_hotspot_insar_evidence_query(self):
        """Verifies hotspot InSAR query reports authentic status without active raster."""
        ev = self.engine.evaluate_hotspot_insar_evidence("EVT-MEG-001", 25.18, 91.64)
        self.assertEqual(ev["hotspot_id"], "EVT-MEG-001")
        self.assertFalse(ev["insar_available"])
        self.assertEqual(ev["insar_status"], "WAITING_FOR_COMPATIBLE_SLC_PAIR")
        self.assertIsNone(ev["relative_los_displacement_mm"])

if __name__ == "__main__":
    unittest.main()
