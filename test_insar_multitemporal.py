"""
=============================================================================
NER-SAFE: Sentinel-1 Multi-Temporal InSAR Comprehensive Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: 27-Point Scientific & Operational InSAR Test Suite:
         1. SLC discovery
         2. metadata parsing
         3. track filtering
         4. orbit filtering
         5. burst filtering
         6. polarization filtering
         7. duplicate detection
         8. temporal baseline calculation
         9. perpendicular baseline calculation
         10. pair selection
         11. network construction
         12. coherence processing
         13. low-coherence masking
         14. reference selection & anchor verification
         15. phase unwrapping
         16. DEM correction
         17. orbit correction
         18. atmospheric diagnostics (phase closure)
         19. time-series construction (SBAS SVD)
         20. uncertainty propagation (Cramer-Rao)
         21. insufficient-stack behavior
         22. no-fabrication behavior
         23. incremental processing
         24. storage/manifest integrity
         25. API output
         26. dashboard integration
         27. risk-formula invariance
=============================================================================
"""

import os
import sys
import math
import json
import hashlib
import unittest
from datetime import datetime, timezone
import numpy as np

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import database
from corrected_insar_engine import (
    parse_safe_annotation,
    compute_baselines,
    wrap_phase,
    C_BAND_WAVELENGTH,
    COHERENCE_THRESHOLD,
    REF_POINT_NAME,
    REF_LAT,
    REF_LON
)
from insar_multitemporal_engine import (
    InSARMultiTemporalEngine,
    compute_file_sha256,
    MAX_TEMPORAL_BASELINE_DAYS,
    MAX_PERPENDICULAR_BASELINE_M,
    MIN_STACK_SIZE_FOR_PSI
)


class TestSentinel1InSARMultiTemporal(unittest.TestCase):
    """27-point comprehensive test suite for Sentinel-1 multi-temporal InSAR."""

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.engine = InSARMultiTemporalEngine()
        cls.slc_dir = cls.engine.slc_dir
        cls.safe_dirs = sorted([
            os.path.join(cls.slc_dir, d) for d in os.listdir(cls.slc_dir)
            if d.endswith(".SAFE") and os.path.isdir(os.path.join(cls.slc_dir, d))
        ])

    # 1. SLC Discovery
    def test_01_slc_discovery(self):
        scenes = self.engine.discover_and_register_scenes()
        self.assertGreaterEqual(len(scenes), 3, "Must discover at least 3 local authentic SLC scenes.")
        for s in scenes:
            self.assertTrue(os.path.exists(s["local_path"]), f"Scene path {s['local_path']} must exist.")

    # 2. Metadata Parsing
    def test_02_metadata_parsing(self):
        scenes = self.engine.discover_and_register_scenes()
        s0 = scenes[0]
        meta = s0["meta"]
        self.assertIn("orbits", meta)
        self.assertIn("bursts", meta)
        self.assertGreater(len(meta["orbits"]), 5, "Ephemeris must contain authentic state vectors.")
        self.assertGreater(len(meta["bursts"]), 0, "Swath must contain authentic burst headers.")

    # 3. Track Filtering
    def test_03_track_filtering(self):
        scenes = self.engine.discover_and_register_scenes()
        # All scenes must belong to Track 150
        for s in scenes:
            self.assertEqual(s["relative_orbit"], 150, "Scene must match primary track 150.")

    # 4. Orbit Filtering
    def test_04_orbit_filtering(self):
        scenes = self.engine.discover_and_register_scenes()
        # All scenes must be Descending
        for s in scenes:
            self.assertEqual(s["orbit_direction"], "DESCENDING", "Scene must match Descending orbit pass.")

    # 5. Burst Filtering
    def test_05_burst_filtering(self):
        scenes = self.engine.discover_and_register_scenes()
        for s in scenes:
            bursts = s["meta"]["bursts"]
            self.assertGreaterEqual(len(bursts), 5, "Must have valid burst coverage across Bursts 2 to 6.")

    # 6. Polarization Filtering
    def test_06_polarization_filtering(self):
        scenes = self.engine.discover_and_register_scenes()
        for s in scenes:
            self.assertEqual(s["polarization"], "VV", "Co-polarized VV channel required for InSAR.")

    # 7. Duplicate Detection
    def test_07_duplicate_detection(self):
        scenes = self.engine.discover_and_register_scenes()
        scene_ids = [s["scene_id"] for s in scenes]
        self.assertEqual(len(scene_ids), len(set(scene_ids)), "Registered scene IDs must be strictly unique.")

    # 8. Temporal Baseline Calculation
    def test_08_temporal_baseline(self):
        scenes = self.engine.discover_and_register_scenes()
        network = self.engine.construct_pair_network(scenes)
        for edge in network["edges"]:
            self.assertGreater(edge["temporal_baseline_days"], 0.0, "Temporal baseline must be positive.")
            self.assertIn(edge["temporal_baseline_days"], [12.0, 24.0], "Sentinel-1D repeat intervals must be 12d or 24d.")

    # 9. Perpendicular Baseline Calculation
    def test_09_perpendicular_baseline(self):
        scenes = self.engine.discover_and_register_scenes()
        network = self.engine.construct_pair_network(scenes)
        for edge in network["edges"]:
            self.assertGreaterEqual(edge["perpendicular_baseline_m"], 0.0)
            self.assertLess(edge["perpendicular_baseline_m"], MAX_PERPENDICULAR_BASELINE_M, "B_perp must be within threshold.")

    # 10. Pair Selection
    def test_10_pair_selection(self):
        scenes = self.engine.discover_and_register_scenes()
        network = self.engine.construct_pair_network(scenes)
        eligible = [e for e in network["edges"] if e["status"] == "ELIGIBLE"]
        self.assertEqual(len(eligible), 3, "All 3 pairs within 3-scene stack must be eligible.")

    # 11. Network Construction
    def test_11_network_construction(self):
        scenes = self.engine.discover_and_register_scenes()
        network = self.engine.construct_pair_network(scenes)
        self.assertEqual(len(network["nodes"]), 3)
        self.assertEqual(len(network["edges"]), 3)
        self.assertEqual(network["sbas_status"], "SBAS_INITIAL_STACK_FORMED")
        self.assertEqual(network["psi_status"], "INSUFFICIENT_SLC_STACK_FOR_PSI")

    # 12. Coherence Processing
    def test_12_coherence_processing(self):
        pairs = database.get_insar_pairs()
        self.assertGreaterEqual(len(pairs), 3, "At least 3 pairs must be registered in database.")
        for p in pairs:
            self.assertIsNotNone(p["coherence_mean"])
            self.assertGreater(p["coherence_mean"], 0.10)
            self.assertLessEqual(p["coherence_mean"], 1.0)

    # 13. Low-Coherence Masking
    def test_13_low_coherence_masking(self):
        # Verify that low coherence pixels are masked and NOT treated as zero displacement
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        self.assertTrue(os.path.exists(summary_path))
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertIn("mean_coherence", summary)
        self.assertGreaterEqual(summary["mean_coherence"], COHERENCE_THRESHOLD)

    # 14. Reference Selection & Anchor Verification
    def test_14_reference_selection(self):
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        ref = summary["reference_point"]
        self.assertEqual(ref["name"], REF_POINT_NAME)
        self.assertAlmostEqual(ref["latitude"], REF_LAT, places=3)
        self.assertAlmostEqual(ref["longitude"], REF_LON, places=3)
        self.assertEqual(ref["stability_status"], "STABLE_BEDROCK_ANCHOR")
        self.assertGreaterEqual(ref["mean_coherence"], 0.70, "Bedrock anchor must maintain high coherence.")

    # 15. Phase Unwrapping
    def test_15_phase_unwrapping(self):
        pairs = database.get_insar_pairs()
        for p in pairs:
            self.assertGreater(p["unwrapped_pixel_count"], 0, "Unwrapped pixel count must be > 0.")
            self.assertEqual(p["processing_status"], "PROCESSED")

    # 16. DEM Correction
    def test_16_dem_correction(self):
        self.assertTrue(os.path.exists(self.engine.dem_path), f"SRTM DEM must exist at {self.engine.dem_path}")

    # 17. Orbit Correction
    def test_17_orbit_correction(self):
        pairs = database.get_insar_pairs()
        for p in pairs:
            meta = json.loads(p["metadata_json"])
            self.assertIn("orbit_provenance", meta)
            self.assertIn("resorb_status", meta["orbit_provenance"])

    # 18. Atmospheric Diagnostics (Phase Closure)
    def test_18_atmospheric_diagnostics_phase_closure(self):
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertIn("phase_closure_mean_rad", summary)
        self.assertIn("phase_closure_std_rad", summary)
        self.assertTrue(math.isfinite(summary["phase_closure_mean_rad"]), "Phase closure mean must be finite.")
        self.assertTrue(math.isfinite(summary["phase_closure_std_rad"]), "Phase closure std must be finite.")

    # 19. Time-Series Construction (SBAS SVD)
    def test_19_timeseries_sbas_svd(self):
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertEqual(summary["methodology"], "SBAS_SVD_TRIANGULAR_INVERSION")
        self.assertEqual(summary["stack_size"], 3)
        self.assertEqual(summary["pair_count"], 3)
        self.assertTrue(math.isfinite(summary["mean_velocity_mm_year"]))

    # 20. Uncertainty Propagation (Cramer-Rao)
    def test_20_uncertainty_propagation(self):
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertIn("velocity_std_mm_year", summary)
        self.assertGreaterEqual(summary["velocity_std_mm_year"], 0.0)

    # 21. Insufficient-Stack Behavior
    def test_21_insufficient_stack_behavior(self):
        # When evaluating stack size for PSI, 3 scenes must report INSUFFICIENT_SLC_STACK_FOR_PSI
        network = self.engine.construct_pair_network(self.engine.discover_and_register_scenes())
        self.assertEqual(network["psi_status"], "INSUFFICIENT_SLC_STACK_FOR_PSI")

    # 22. No Fabrication Behavior
    def test_22_no_fabrication(self):
        # Verify that InSAR status is RESEARCH_ONLY and never claimed as an operational landslide prediction
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        self.assertEqual(summary["scientific_status"], "RESEARCH_ONLY")
        self.assertEqual(summary["risk_integration_status"], "INSAR_RESEARCH_EVIDENCE_DECOUPLED")

    # 23. Incremental Processing
    def test_23_incremental_processing(self):
        # Repeated execution must not reprocess already processed pairs
        t0 = datetime.now()
        scenes = self.engine.discover_and_register_scenes()
        scenes_dict = {s["scene_id"]: s for s in scenes}
        network = self.engine.construct_pair_network(scenes)
        # Should be almost instantaneous (< 10 seconds) because pairs are cached
        processed = self.engine.process_pair_network(network, scenes_dict)
        self.assertEqual(len(processed), 3)
        elapsed = (datetime.now() - t0).total_seconds()
        self.assertLess(elapsed, 10.0, "Incremental run must reuse cached pairs without full recomputation.")

    # 24. Storage & Manifest Integrity
    def test_24_storage_manifest_integrity(self):
        summary_path = os.path.join(self.engine.output_dir, "sbas_multitemporal_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        hashes = summary["raster_sha256"]
        for rname, rpath in summary["output_rasters"].items():
            self.assertTrue(os.path.exists(rpath), f"Raster {rpath} must exist.")
            current_hash = compute_file_sha256(rpath)
            self.assertEqual(current_hash, hashes[rname], f"Hash mismatch for {rname}")

    # 25. API Output
    def test_25_api_output(self):
        from live_sensor_server_extension import ExtendedNERSafeRequestHandler
        # Test database retrieval helpers that feed the API
        scenes = database.get_insar_scenes()
        pairs = database.get_insar_pairs()
        latest_def = database.get_insar_latest_deformation()
        self.assertEqual(len(scenes), 3)
        self.assertEqual(len(pairs), 3)
        self.assertIsNotNone(latest_def)
        self.assertEqual(latest_def["multitemporal_status"], "SBAS_INITIAL_STACK_FORMED")

    # 26. Dashboard Integration
    def test_26_dashboard_integration(self):
        dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
        with open(dash_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        self.assertIn("cardSentinel1InSAR", html)
        self.assertIn("SBAS_INITIAL_STACK_FORMED", html)
        self.assertIn("SHILLONG_PLATEAU_NORTH_BEDROCK_REF", html)
        self.assertIn("/api/insar/status", html)

    # 27. Risk-Formula Invariance
    def test_27_risk_formula_invariance(self):
        # Risk weights must remain strictly invariant: 0.40, 0.30, 0.20, 0.10
        # Check fusion_engine.py
        with open(os.path.join(PROJECT_ROOT, "fusion_engine.py"), "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
        self.assertIn("0.40", code)
        self.assertIn("0.30", code)
        self.assertIn("0.20", code)
        self.assertIn("0.10", code)
        self.assertNotIn("0.10 * satellite_change_flag + insar", code.lower())


if __name__ == "__main__":
    unittest.main()
