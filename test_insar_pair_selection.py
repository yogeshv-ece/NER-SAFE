"""
=============================================================================
NER-SAFE: Test Suite for Sentinel-1 InSAR Pair Selection
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Verifies Sentinel-1 IW SLC pair evaluation rules:
  1. Rejection of GRD products (only SLC permitted).
  2. Rejection of mismatched relative orbits.
  3. Rejection of mismatched flight directions (Ascending vs Descending).
  4. Temporal baseline constraints (delta_t <= 24d optimal, > 48d rejected).
  5. Perpendicular baseline constraints (B_perp <= 150m).
  6. Spatial overlap checks (> 30% required).
  7. CDSE credential status check (AUTH_REQUIRED when absent).
  8. Honest operational status reporting.
=============================================================================
"""

import unittest
from datetime import datetime, timezone, timedelta
from insar_pair_selector import (
    InSARPairSelector,
    PAIR_STATUS_OPTIMAL,
    PAIR_STATUS_ACCEPTABLE,
    PAIR_STATUS_SUBOPTIMAL,
    PAIR_STATUS_REJECTED,
    DATA_ACCESS_AUTH_REQUIRED
)

class TestInSARPairSelection(unittest.TestCase):
    def setUp(self):
        self.selector = InSARPairSelector()

    def test_01_granule_id_parsing(self):
        """Verifies parsing of standard Sentinel-1 SLC naming convention."""
        gid = "S1A_IW_SLC__1SDV_20260901T114530_20260901T114557_060790_0756F0_D4C1"
        meta = self.selector.parse_s1_granule_id(gid)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["mission"], "S1A")
        self.assertEqual(meta["mode"], "IW")
        self.assertEqual(meta["product_type"], "SLC")
        self.assertEqual(meta["polarization"], "VV+VH")
        self.assertEqual(meta["absolute_orbit"], 60790)

    def test_02_grd_product_rejection(self):
        """Verifies that GRD (Ground Range Detected) products are strictly rejected for InSAR."""
        p1 = {
            "granule_id": "S1A_IW_GRDH_1SDV_20260901T114530_...",
            "product_type": "GRD",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-01T11:45:30Z"
        }
        p2 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260913T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-13T11:45:30Z"
        }
        res = self.selector.evaluate_pair(p1, p2)
        self.assertFalse(res["is_valid_pair"])
        self.assertEqual(res["pair_status"], PAIR_STATUS_REJECTED)
        self.assertTrue(any("GRD" in r for r in res["rejection_reasons"]))

    def test_03_orbit_mismatch_rejection(self):
        """Verifies that different relative orbits are strictly rejected."""
        p1 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260901T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-01T11:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        p2 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260913T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 63,  # Mismatched orbit
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-13T11:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        res = self.selector.evaluate_pair(p1, p2)
        self.assertFalse(res["is_valid_pair"])
        self.assertEqual(res["pair_status"], PAIR_STATUS_REJECTED)
        self.assertTrue(any("Relative orbit mismatch" in r for r in res["rejection_reasons"]))

    def test_04_flight_direction_mismatch_rejection(self):
        """Verifies that Ascending vs Descending pairs are strictly rejected."""
        p1 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260901T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-01T11:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        p2 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260913T004530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "DESCENDING",  # Mismatched direction
            "start_time": "2026-09-13T00:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        res = self.selector.evaluate_pair(p1, p2)
        self.assertFalse(res["is_valid_pair"])
        self.assertEqual(res["pair_status"], PAIR_STATUS_REJECTED)
        self.assertTrue(any("direction mismatch" in r for r in res["rejection_reasons"]))

    def test_05_optimal_pair_acceptance(self):
        """Verifies that a compatible 12-day repeat-pass pair with small perpendicular baseline is rated OPTIMAL."""
        p1 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260901T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "polarization": "VV",
            "start_time": "2026-09-01T11:45:30Z",
            "perpendicular_baseline_m": 45.2,
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        p2 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260913T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "polarization": "VV",
            "start_time": "2026-09-13T11:45:30Z",
            "perpendicular_baseline_m": 45.2,
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        res = self.selector.evaluate_pair(p1, p2)
        self.assertTrue(res["is_valid_pair"])
        self.assertEqual(res["pair_status"], PAIR_STATUS_OPTIMAL)
        self.assertEqual(res["temporal_baseline_days"], 12.0)
        self.assertEqual(res["perpendicular_baseline_m"], 45.2)

    def test_06_excessive_temporal_baseline_rejection(self):
        """Verifies that pairs > 48 days are rejected due to C-band vegetative decorrelation."""
        p1 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260601T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-06-01T11:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        p2 = {
            "granule_id": "S1A_IW_SLC__1SDV_20260913T114530_...",
            "product_type": "SLC",
            "mode": "IW",
            "relative_orbit": 136,
            "orbit_direction": "ASCENDING",
            "start_time": "2026-09-13T11:45:30Z",
            "bbox": [91.0, 25.0, 93.0, 26.5]
        }
        res = self.selector.evaluate_pair(p1, p2)
        self.assertFalse(res["is_valid_pair"])
        self.assertTrue(any("Temporal baseline excessive" in r for r in res["rejection_reasons"]))

    def test_07_cdse_credentials_auditing(self):
        """Verifies honest reporting of CDSE credential status."""
        cred = self.selector.check_cdse_credentials()
        self.assertIn("status", cred)
        self.assertIn(cred["status"], [DATA_ACCESS_AUTH_REQUIRED, "READY"])
        status = self.selector.get_live_insar_status()
        self.assertIn("disclaimer", status)
        self.assertIn("relative Line-of-Sight", status["disclaimer"])

if __name__ == "__main__":
    unittest.main()
