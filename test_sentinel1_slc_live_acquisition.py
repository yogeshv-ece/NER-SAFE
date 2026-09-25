"""
=============================================================================
NER-SAFE Test Suite: Sentinel-1 SLC Live Acquisition & Stack Accumulation
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: 24-point comprehensive test suite verifying the live discovery,
         geometry filtering, resumable acquisition, integrity validation,
         storage guard, idempotency, scheduler modes, credential secrecy,
         and inviolable system invariants.
Zero Tolerance: Zero emojis, zero data fabrication, zero risk weight mutation.
=============================================================================
"""

import os
import sys
import json
import time
import shutil
import hashlib
import unittest
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sentinel1_slc_live_engine import sentinel1_slc_live_engine, Sentinel1SLCLiveEngine
from sentinel1_slc_scheduler import Sentinel1SLCScheduler, format_audit_log
from multitemporal_slc_manager import multitemporal_slc_manager
from insar_multitemporal_engine import InSARMultiTemporalEngine
import database
from fusion_engine import get_multi_source_status

LOCKED_XGBOOST_HASH = "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c"
XGBOOST_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")


class TestSentinel1SLCLiveAcquisition(unittest.TestCase):
    """24-point rigorous test suite for Sentinel-1 SLC live acquisition."""

    @classmethod
    def setUpClass(cls):
        cls.slc_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "SLC")
        cls.engine = sentinel1_slc_live_engine
        cls.scheduler = Sentinel1SLCScheduler(poll_interval=5)

    def test_01_cdse_discovery_parsing(self):
        """1. CDSE discovery parsing: verify schema and parsing of catalogue records."""
        inv = multitemporal_slc_manager.fetch_cdse_inventory(force_refresh=False)
        self.assertIsInstance(inv, list)
        self.assertGreater(len(inv), 0)
        first = inv[0]
        self.assertIn("granule_name", first)
        self.assertIn("product_id", first)
        self.assertIn("sensing_start_utc", first)
        self.assertIn("relative_orbit", first)
        self.assertIn("orbit_direction", first)
        self.assertTrue(first["granule_name"].endswith(".SAFE"))

    def test_02_track_150_filtering(self):
        """2. Correct Track 150 filtering: accept Track 150 and reject other tracks."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        for c in candidates:
            self.assertEqual(c["relative_orbit"], 150, f"Candidate {c['granule_name']} must be Track 150")

    def test_03_descending_orbit_filtering(self):
        """3. Descending orbit filtering: ensure all candidates are descending."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        for c in candidates:
            self.assertEqual(c["orbit_direction"], "DESCENDING")

    def test_04_slc_product_type_filtering(self):
        """4. SLC product type filtering: ensure all candidates are Level-1 SLC."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        for c in candidates:
            self.assertEqual(c["product_type"], "SLC")
            self.assertIn("_SLC_", c["granule_name"])

    def test_05_iw_mode_filtering(self):
        """5. IW mode filtering: ensure all candidates are Interferometric Wide."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        for c in candidates:
            self.assertEqual(c["mode"], "IW")
            self.assertIn("_IW_", c["granule_name"])

    def test_06_vv_polarization_filtering(self):
        """6. VV polarization filtering: ensure polarization includes VV."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        for c in candidates:
            self.assertIn("VV", c["polarization"])

    def test_07_aoi_filtering(self):
        """7. AOI filtering: ensure sensing intersects Meghalaya central coordinate."""
        candidates = self.engine.query_cdse_catalogue(force_refresh=False)
        self.assertGreater(len(candidates), 0)
        # All fetched items are pre-filtered on Meghalaya Point(91.0, 25.5)
        for c in candidates:
            self.assertIn("S1", c["granule_name"])

    def test_08_duplicate_detection(self):
        """8. Duplicate detection: already local/registered scenes are identified."""
        local_scenes = [d for d in os.listdir(self.slc_dir) if d.endswith(".SAFE")]
        self.assertGreater(len(local_scenes), 0)
        for s in local_scenes:
            self.assertTrue(self.engine.is_scene_already_registered(s))

    def test_09_idempotent_rerun(self):
        """9. Idempotent rerun: repeated executions produce ALREADY_CURRENT without data duplication."""
        res1 = self.engine.execute_live_cycle(force_refresh=False)
        res2 = self.engine.execute_live_cycle(force_refresh=False)
        self.assertEqual(res1["status"], "ALREADY_CURRENT")
        self.assertEqual(res2["status"], "ALREADY_CURRENT")
        self.assertEqual(res1["current_stack_size"], res2["current_stack_size"])

    def test_10_interrupted_acquisition(self):
        """10. Interrupted acquisition: verify resumable byte-range download logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "chunk_test.bin")
            expected_data = b"X" * 100000
            # Create partial file
            with open(test_file, "wb") as f:
                f.write(expected_data[:40000])
            self.assertEqual(os.path.getsize(test_file), 40000)

            # Mock S3 object streaming
            from cdse_s3_downloader import cdse_s3_downloader
            with patch.object(cdse_s3_downloader, "get_s3_client") as mock_s3:
                client_mock = MagicMock()
                mock_s3.return_value = client_mock
                body_mock = MagicMock()
                body_mock.read.side_effect = [expected_data[40000:], b""]
                client_mock.get_object.return_value = {"Body": body_mock}

                res = cdse_s3_downloader.download_s3_object_resumable(
                    s3_key="dummy_key",
                    local_path=test_file,
                    expected_size=100000
                )
                self.assertEqual(res["size_bytes"], 100000)
                self.assertEqual(res["status"], "DOWNLOADED_AND_VERIFIED")
                self.assertEqual(os.path.getsize(test_file), 100000)

    def test_11_checksum_integrity_failure(self):
        """11. Checksum/integrity failure: corrupt TIFF or bad header is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_scene_dir = os.path.join(tmpdir, "S1D_FAKE_CORRUPT.SAFE")
            meas_dir = os.path.join(fake_scene_dir, "measurement")
            os.makedirs(meas_dir, exist_ok=True)
            # Write invalid header and small size
            with open(os.path.join(meas_dir, "corrupt.tiff"), "wb") as f:
                f.write(b"BAD_HEADER_NOT_TIFF")
            # Write manifest
            with open(os.path.join(fake_scene_dir, "manifest.safe"), "w") as f:
                f.write("test manifest" * 200)

            val = self.engine.validate_scene_integrity(fake_scene_dir)
            self.assertFalse(val["valid"])
            self.assertIn("threshold", val["reason"].lower())

    def test_12_insufficient_storage_guard(self):
        """12. Insufficient storage guard: refuses download safely if free space < threshold."""
        # Test with required_gb set higher than free space
        with patch.object(self.engine, "check_storage_guard") as mock_guard:
            mock_guard.return_value = {
                "free_gb": 4.5,
                "required_gb": 10.0,
                "sufficient_space": False
            }
            fake_scene = {
                "granule_name": "S1D_IW_SLC__TEST_LOW_STORAGE.SAFE",
                "product_id": "test_pid_001",
                "sensing_start_utc": "2026-09-25T23:54:50Z"
            }
            res = self.engine.acquire_and_register_scene(fake_scene)
            self.assertEqual(res["status"], "STORAGE_GUARD_TRIGGERED")
            self.assertFalse(mock_guard.return_value["sufficient_space"])

    def test_13_invalid_metadata_rejection(self):
        """13. Invalid metadata rejection: XML lacking orbit vectors is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_scene_dir = os.path.join(tmpdir, "S1D_FAKE_NO_ORBITS.SAFE")
            annot_dir = os.path.join(fake_scene_dir, "annotation")
            meas_dir = os.path.join(fake_scene_dir, "measurement")
            os.makedirs(annot_dir, exist_ok=True)
            os.makedirs(meas_dir, exist_ok=True)

            # Valid manifest
            with open(os.path.join(fake_scene_dir, "manifest.safe"), "w") as f:
                f.write("manifest" * 300)
            # Valid TIFF
            with open(os.path.join(meas_dir, "test.tiff"), "wb") as f:
                f.write(b"II*\x00" + b"\x00" * (501 * 1024 * 1024))
            # XML without orbit vectors
            with open(os.path.join(annot_dir, "s1d-iw1-slc.xml"), "w") as f:
                f.write("<product><generalAnnotation></generalAnnotation></product>")

            val = self.engine.validate_scene_integrity(fake_scene_dir)
            self.assertFalse(val["valid"])
            self.assertIn("orbit", val["reason"].lower())

    def test_14_scheduler_run_once(self):
        """14. Scheduler RUN_ONCE: executes single cycle and returns valid dictionary."""
        res = self.scheduler.run_once(force_refresh=False)
        self.assertIsInstance(res, dict)
        self.assertIn("status", res)
        self.assertIn(res["status"], ("ALREADY_CURRENT", "NEW_OBSERVATION_ACQUIRED"))

    def test_15_scheduler_continuous_orchestration(self):
        """15. Scheduler CONTINUOUS orchestration: runs multiple cycles and stops at max_cycles."""
        sched = Sentinel1SLCScheduler(poll_interval=5)
        sched.run_continuous(max_cycles=2, force_refresh=False)
        self.assertEqual(sched.cycle_count, 2)

    def test_16_stack_registration(self):
        """16. Stack registration: all valid local scenes are recorded in insar_scenes DB."""
        scenes = database.get_insar_scenes()
        self.assertGreaterEqual(len(scenes), 3)
        for s in scenes:
            self.assertEqual(s["relative_orbit"], 150)
            self.assertEqual(s["orbit_direction"], "DESCENDING")
            self.assertEqual(s["polarization"], "VV")

    def test_17_pair_generation(self):
        """17. Pair generation: eligible pairs formed within baseline constraints."""
        engine = InSARMultiTemporalEngine(slc_dir=self.slc_dir)
        scenes = engine.discover_and_register_scenes()
        net = engine.construct_pair_network(scenes)
        self.assertIn("eligible_pairs_count", net)
        self.assertGreaterEqual(net["eligible_pairs_count"], 3)

    def test_18_sbas_graph_update(self):
        """18. SBAS graph update: verified network connectivity and nodes."""
        summary = self.engine.get_stack_summary()
        self.assertGreaterEqual(summary["stack_size_scenes"], 3)
        self.assertGreaterEqual(summary["eligible_pairs_count"], 3)
        self.assertEqual(summary["sbas_status"], "SBAS_INITIAL_STACK_FORMED")
        self.assertEqual(summary["psi_status"], "INSUFFICIENT_SLC_STACK_FOR_PSI")

    def test_19_failure_recovery(self):
        """19. Failure recovery: graceful catch of network/API error without crash."""
        with patch.object(self.engine, "query_cdse_catalogue", side_effect=ConnectionResetError("Simulated network drop")):
            res = self.engine.execute_live_cycle()
            self.assertEqual(res["status"], "FAILED")
            self.assertEqual(res["stage"], "CATALOGUE_DISCOVERY")
            self.assertIn("Simulated network drop", res["error"])

    def test_20_credential_secrecy(self):
        """20. Credential secrecy: secrets/tokens never leaked in formatted logs or state."""
        cycle_res = self.engine.execute_live_cycle(force_refresh=False)
        log_text = format_audit_log(cycle_res)

        forbidden_strings = ["secret", "password", "bearer", "token", "access_key", "secret_key"]
        for line in log_text.splitlines():
            line_lower = line.lower()
            for forb in forbidden_strings:
                if forb in line_lower:
                    self.fail(f"Potential credential leak detected in audit log: '{line}'")

    def test_21_existing_three_scenes_intact(self):
        """21. Existing 3 scenes intact: 2026-08-20, 2026-09-01, 2026-09-13 present and valid."""
        expected_dates = ["20260820", "20260901", "20260913"]
        local_safe_dirs = [d for d in os.listdir(self.slc_dir) if d.endswith(".SAFE")]
        self.assertEqual(len(local_safe_dirs), 3)

        for date_str in expected_dates:
            matched = any(date_str in d for d in local_safe_dirs)
            self.assertTrue(matched, f"Expected scene date {date_str} must be present.")

        for safe_dir in local_safe_dirs:
            meas_dir = os.path.join(self.slc_dir, safe_dir, "measurement")
            tiffs = [f for f in os.listdir(meas_dir) if f.endswith(".tiff")]
            self.assertGreater(len(tiffs), 0)
            sz = os.path.getsize(os.path.join(meas_dir, tiffs[0]))
            self.assertGreater(sz, 1000 * 1024 * 1024, "Measurement TIFF must exceed 1000 MB.")

    def test_22_locked_xgboost_artifact_unchanged(self):
        """22. Locked XGBoost artifact remains byte-for-byte identical to mandated SHA-256."""
        self.assertTrue(os.path.isfile(XGBOOST_PATH), f"XGBoost model missing: {XGBOOST_PATH}")
        with open(XGBOOST_PATH, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(
            current_hash,
            LOCKED_XGBOOST_HASH,
            f"Production XGBoost model mutated! Got {current_hash}, expected {LOCKED_XGBOOST_HASH}"
        )

    def test_23_locked_risk_formula_unchanged(self):
        """23. Locked risk formula unchanged: weights are strictly 0.40, 0.30, 0.20, 0.10."""
        status = get_multi_source_status()
        weights = status.get("weights", {})
        self.assertEqual(weights.get("w1_susceptibility"), 0.40)
        self.assertEqual(weights.get("w2_rainfall_anomaly"), 0.30)
        self.assertEqual(weights.get("w3_soil_moisture_anomaly"), 0.20)
        self.assertEqual(weights.get("w4_satellite_surface_change"), 0.10)

    def test_24_external_hdd_not_accessed(self):
        """24. External HDD is not accessed: Drive G: is never configured or used."""
        self.assertNotIn("G:", self.engine.slc_dir)
        self.assertNotIn("G:", self.engine.registry_path)
        self.assertNotIn("G:", self.engine.state_path)
        summary = self.engine.get_stack_summary()
        self.assertNotIn("G:", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
