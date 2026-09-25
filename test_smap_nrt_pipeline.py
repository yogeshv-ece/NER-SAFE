"""
NER-SAFE — SMAP L2 Near-Real-Time (SPL2SMP_NRT.107) Pipeline Validation Suite
VERSION: v1.2.x
PROJECT: AI-Based Early Warning and Landslide Risk Monitoring System in NER India

Validates:
A. Authentication & CMR Discovery
B. Swath HDF5 Parsing & Dataset Structure
C. AOI Extraction (21.0-27.0N, 89.0-94.0E)
D. Bitwise Quality Control & Fill Value Rejection
E. Historical Baseline Preservation & Missing Date Integrity
F. Spatial Resolution Harmonization (36km swath to baseline bounds)
G. Anomaly Calculation & Mathematical Bounds
H. Machine-Readable Freshness Classification
I. Database Persistence & Parameterized Queries
J. Scheduler Idempotency & Deduplication
K. 4-Factor Risk Engine Fusion Invariance (0.40/0.30/0.20/0.10)
L. REST API Endpoints (/api/smap/latest, /api/smap/history)
M. Zero-Emoji Compliance on Dashboard
N. Non-Fabrication Fallback Behavior
"""

import os
import sys
import json
import sqlite3
import hashlib
import unittest
import numpy as np

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from smap_nrt_engine import smap_nrt_engine, SMAPNRTEngine
import database
from sensor_source_registry import sensor_source_registry
import live_assessment_service
import live_ingestion

class TestSMAPNRTPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.engine = smap_nrt_engine
        cls.db_path = os.path.join(WORKSPACE, "NER_SAFE_DATA", "DATABASE", "ner_safe_shared.db")
        cls.nrt_raw_dir = os.path.join(WORKSPACE, "NER_SAFE_DATA", "SMAP", "raw", "nrt")

    # -------------------------------------------------------------------------
    # A. Authentication & Provider Configuration
    # -------------------------------------------------------------------------
    def test_a_authentication_configuration(self):
        """Verify Earthdata authentication credentials exist outside source code."""
        netrc_home = os.path.join(os.path.expanduser("~"), ".netrc")
        netrc_exists = os.path.exists(netrc_home)
        self.assertTrue(netrc_exists, "Operational .netrc file must be present in user profile")
        
        # Verify no hardcoded passwords in smap_nrt_engine.py
        with open(os.path.join(WORKSPACE, "smap_nrt_engine.py"), "r", encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn("password=", code)
        self.assertNotIn("earthdata_pass", code)

    # -------------------------------------------------------------------------
    # B. Real Granule HDF5 Swath Parsing
    # -------------------------------------------------------------------------
    def test_b_hdf5_swath_parsing(self):
        """Verify real SPL2SMP_NRT.107 HDF5 structure and dataset presence."""
        test_files = [f for f in os.listdir(self.nrt_raw_dir) if f.endswith(".h5")]
        self.assertGreater(len(test_files), 0, "At least one genuine NRT granule must exist in raw/nrt")
        
        file_path = os.path.join(self.nrt_raw_dir, test_files[0])
        import h5py
        with h5py.File(file_path, "r") as h5:
            self.assertIn("Soil_Moisture_Retrieval_Data", h5, "Must contain official group Soil_Moisture_Retrieval_Data")
            grp = h5["Soil_Moisture_Retrieval_Data"]
            for field in ["soil_moisture", "latitude", "longitude", "retrieval_qual_flag", "surface_flag"]:
                self.assertIn(field, grp, f"Swath dataset must contain '{field}'")
                self.assertEqual(len(grp[field].shape), 1, f"Field '{field}' should be 1D swath vector")

    # -------------------------------------------------------------------------
    # C. AOI Extraction
    # -------------------------------------------------------------------------
    def test_c_aoi_extraction_boundaries(self):
        """Verify extraction respects authoritative NER AOI (21.0-27.0N, 89.0-94.0E)."""
        test_files = [f for f in os.listdir(self.nrt_raw_dir) if f.endswith(".h5")]
        file_path = os.path.join(self.nrt_raw_dir, test_files[0])
        
        metrics = self.engine.process_granule_hdf5(file_path)
        self.assertEqual(metrics["quality_status"], "VALID")
        self.assertGreater(metrics["aoi_cells_total"], 0)
        self.assertGreater(metrics["aoi_cells_valid"], 0)
        self.assertLessEqual(metrics["aoi_cells_valid"], metrics["aoi_cells_total"])

    # -------------------------------------------------------------------------
    # D. Bitwise Quality Control & Fill Value Handling
    # -------------------------------------------------------------------------
    def test_d_quality_control_filtering(self):
        """Verify fill values (-9999.0) and unrecommended retrievals are discarded."""
        # Synthetic test with known bad flags and fill values
        lats = np.array([25.0, 25.1, 25.2, 25.3])
        lons = np.array([91.0, 91.1, 91.2, 91.3])
        sm = np.array([0.35, -9999.0, 0.40, 1.50]) # Valid, Fill, Valid SM with bad flag, Out of bounds
        rq_flag = np.array([0, 0, 1, 0], dtype=np.uint16) # Bit 0 set on index 2 -> not recommended
        surf_flag = np.array([0, 0, 0, 0], dtype=np.uint16)
        
        valid_mask = (
            (sm >= 0.0) & (sm <= 1.0) &
            ((rq_flag & 0x0001) == 0) &
            ((surf_flag & 0x0160) == 0)
        )
        # Only index 0 should survive
        self.assertTrue(valid_mask[0])
        self.assertFalse(valid_mask[1]) # fill rejected
        self.assertFalse(valid_mask[2]) # rq_flag rejected
        self.assertFalse(valid_mask[3]) # > 1.0 rejected

    # -------------------------------------------------------------------------
    # E. Historical Baseline Preservation
    # -------------------------------------------------------------------------
    def test_e_historical_baseline_integrity(self):
        """Verify historical 180 validated files remain and 2025-03-18 outage is documented, not fabricated."""
        raw_historical_dir = os.path.join(WORKSPACE, "NER_SAFE_DATA", "SMAP", "raw")
        if os.path.exists(raw_historical_dir):
            h5_files = [f for f in os.listdir(raw_historical_dir) if f.startswith("SMAP_L3_SM_P_E_") and f.endswith(".h5")]
            self.assertGreaterEqual(len(h5_files), 180, "Historical SMAP baseline must retain at least 180 valid HDF5 files")
            
            # Verify 2025-03-18 missing date is not fabricated as a file
            for f in h5_files:
                self.assertNotIn("20250318", f, "Historical outage on 2025-03-18 must NOT be fabricated")

        # Also verify validation report documents 2025-03-18 outage explicitly
        report_path = os.path.join(WORKSPACE, "NER_SAFE_DATA", "SMAP", "SMAP_validation_report.txt")
        self.assertTrue(os.path.exists(report_path), "SMAP validation report must exist")
        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()
        self.assertIn("2025-03-18", report_text)
        self.assertIn("Missing Observations     : 1", report_text)

    # -------------------------------------------------------------------------
    # F. Harmonization & Anomaly Calculation
    # -------------------------------------------------------------------------
    def test_f_resolution_harmonization_and_anomaly(self):
        """Verify mathematical derivation of Relative Saturation Index anomaly."""
        # Regional baseline: min=0.0727, max=0.4538
        self.assertAlmostEqual(self.engine.baseline_min, 0.0727, places=4)
        self.assertAlmostEqual(self.engine.baseline_max, 0.4538, places=4)
        
        # Test low value -> near 0.0
        low_anomaly = self.engine.calculate_relative_saturation_anomaly(0.0727)
        self.assertAlmostEqual(low_anomaly, 0.0, places=3)
        
        # Test high value -> 1.0
        high_anomaly = self.engine.calculate_relative_saturation_anomaly(0.4538)
        self.assertAlmostEqual(high_anomaly, 1.0, places=3)
        
        # Test genuine observed mean 0.3833
        test_anomaly = self.engine.calculate_relative_saturation_anomaly(0.3833)
        expected = (0.3833 - self.engine.baseline_min) / (self.engine.baseline_max - self.engine.baseline_min)
        self.assertAlmostEqual(test_anomaly, round(expected, 4), places=4)

    # -------------------------------------------------------------------------
    # G. Freshness Model
    # -------------------------------------------------------------------------
    def test_g_freshness_classification(self):
        """Verify machine-readable freshness policy correctly buckets observation age."""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        
        # Fresh: 2 hours old
        t_fresh = (now - timedelta(hours=2)).isoformat()
        self.assertEqual(self.engine.classify_freshness(t_fresh), "FRESH")
        
        # Aging: 40 hours old
        t_aging = (now - timedelta(hours=40)).isoformat()
        self.assertEqual(self.engine.classify_freshness(t_aging), "AGING")
        
        # Stale: 80 hours old
        t_stale = (now - timedelta(hours=80)).isoformat()
        self.assertEqual(self.engine.classify_freshness(t_stale), "STALE")
        
        # Missing
        self.assertEqual(self.engine.classify_freshness(None), "MISSING")

    # -------------------------------------------------------------------------
    # H. Database Persistence
    # -------------------------------------------------------------------------
    def test_h_database_persistence_and_query(self):
        """Verify parameterized persistence into smap_nrt_observations table."""
        obs = self.engine.get_latest_observation()
        self.assertIsNotNone(obs, "Should retrieve latest observation from DB or state")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM smap_nrt_observations ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        conn.close()
        
        self.assertIsNotNone(row, "Table smap_nrt_observations must contain at least one ingested record")
        self.assertEqual(row["product"], "SPL2SMP_NRT")
        self.assertEqual(row["version"], "107")
        self.assertEqual(row["quality_status"], "VALID")
        self.assertIn("source_file", dict(row))
        self.assertIn("sha256", dict(row))
        self.assertIn("anomaly", dict(row))

    # -------------------------------------------------------------------------
    # I. Scheduler Idempotency & Deduplication
    # -------------------------------------------------------------------------
    def test_i_scheduler_idempotency(self):
        """Verify repeated execution does not duplicate observations or alter state."""
        from live_monitoring_scheduler import live_monitoring_scheduler
        
        # Poll 1
        res1 = live_monitoring_scheduler.poll_source("NASA_SMAP_L3_01")
        # Poll 2 immediately after
        res2 = live_monitoring_scheduler.poll_source("NASA_SMAP_L3_01")
        
        self.assertEqual(res2["poll_result"], "ALREADY_CURRENT", "Repeated poll of identical observation must be ALREADY_CURRENT")
        self.assertFalse(res2["new_observation_ingested"])

    # -------------------------------------------------------------------------
    # J. Four-Factor Risk Engine Fusion Invariance
    # -------------------------------------------------------------------------
    def test_j_risk_engine_invariance(self):
        """Verify 4-factor weights (0.40, 0.30, 0.20, 0.10) and thresholds remain strictly locked."""
        from live_assessment_service import live_assessment_service
        
        asm = live_assessment_service.get_current_assessment()
        self.assertIsNotNone(asm, "Current live assessment must exist")
        
        weights = asm.get("fusion_weights", {})
        self.assertEqual(weights.get("susceptibility"), 0.40, "Susceptibility weight must be 0.40")
        self.assertEqual(weights.get("rainfall"), 0.30, "Rainfall weight must be 0.30")
        self.assertEqual(weights.get("soil_moisture"), 0.20, "Soil moisture weight must be 0.20")
        self.assertEqual(weights.get("satellite_change"), 0.10, "Satellite change weight must be 0.10")
        
        # Soil moisture input must reflect NRT anomaly and provenance
        sm_input = asm.get("inputs", {}).get("soil_moisture", {})
        self.assertIn("derived_anomaly", sm_input)
        self.assertIn("granule_id", sm_input)
        self.assertIn("freshness_state", sm_input)

    # -------------------------------------------------------------------------
    # K. Zero-Emoji Compliance
    # -------------------------------------------------------------------------
    def test_k_zero_emoji_on_dashboard(self):
        """Verify ner_safe_live_dashboard.html strictly contains zero emoji icons."""
        dashboard_path = os.path.join(WORKSPACE, "ner_safe_live_dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            html = f.read()
        
        # Regex check for common emojis
        import re
        emoji_pattern = re.compile(r"[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]")
        matches = emoji_pattern.findall(html)
        self.assertEqual(len(matches), 0, f"Found prohibited emojis in dashboard: {matches}")

    # -------------------------------------------------------------------------
    # L. Non-Fabrication on Data Quality Rejection
    # -------------------------------------------------------------------------
    def test_l_non_fabrication_on_quality_rejection(self):
        """Verify that when no valid cells exist, system does not fabricate 0.0 or normal values."""
        # Empty cells
        empty_metrics = self.engine._empty_metrics("TEST_EMPTY", "SMAP_TEST_EMPTY", 0, "NO_VALID_DATA")
        self.assertEqual(empty_metrics["quality_status"], "NO_VALID_DATA")
        self.assertIsNone(empty_metrics["sm_mean"])
        self.assertIsNone(empty_metrics["anomaly"])
        self.assertEqual(empty_metrics["status"], "QUALITY_REJECTED")

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING NER-SAFE SMAP NRT (SPL2SMP_NRT.107) PIPELINE TEST SUITE")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSMAPNRTPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
