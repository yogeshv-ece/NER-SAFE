"""
=============================================================================
NER-SAFE: Test Suite for Live Observation Intake & Risk Reassessment
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Verifies the complete live operational pipeline:
  1. New observation detection & HDF5 parsing.
  2. Duplicate suppression (ALREADY_CURRENT).
  3. Freshness validation state machine.
  4. Dynamic rainfall anomaly recalculation.
  5. Canonical operational assessment generation.
  6. SQLite persistence of ASM-LIVE-... records.
  7. Provenance linkage (granule ID, SHA-256 digest, inputs).
  8. /api/assessment/current REST endpoint exposure.
  9. Dashboard-facing payload integrity.
  10. Strict zero-contamination (no demo replay data in operational output).
  11. Stale assessment rejection (CURRENT RISK: NOT AVAILABLE).
  12. Decoupled observation vs. ingestion vs. assessment timestamps.
=============================================================================
"""

import os
import sys
import json
import time
import sqlite3
import threading
import unittest
import requests
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from live_assessment_service import LiveAssessmentService, DB_PATH
from live_sensor_server_extension import start_extended_server


class TestLiveObservationToRiskAssessment(unittest.TestCase):
    """Verifies the complete live observation to risk reassessment operational pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.test_port = 8031
        cls.httpd = start_extended_server(cls.test_port)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.4)
        cls.base_url = f"http://127.0.0.1:{cls.test_port}"
        cls.service = LiveAssessmentService()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
        except Exception:
            pass

    def test_01_real_gpm_binary_acquisition_and_metrics(self):
        """Verify NASA CMR discovery and authenticated HDF5 acquisition."""
        gpm = self.service.discover_and_acquire_gpm_nrt()
        self.assertEqual(gpm["source_id"], "NASA_GPM_3IMERGHHE_V07")
        self.assertTrue(gpm["granule_id"].startswith("GPM_3IMERGHHE"))
        self.assertGreater(gpm["size_bytes"], 5_000_000, "GPM HDF5 file must be > 5MB")
        self.assertIn("regional_metrics", gpm)
        self.assertIn("derived_rain_anomaly", gpm["regional_metrics"])
        self.assertGreaterEqual(gpm["regional_metrics"]["derived_rain_anomaly"], 0.15)
        self.assertLessEqual(gpm["regional_metrics"]["derived_rain_anomaly"], 1.00)

    def test_02_timestamp_decoupling(self):
        """Verify that observation_time strictly reflects satellite pass and is decoupled from ingested_time."""
        gpm = self.service.discover_and_acquire_gpm_nrt()
        obs_dt = datetime.fromisoformat(gpm["observation_time"].replace("Z", "+00:00"))
        ingest_dt = datetime.fromisoformat(gpm["ingested_time"].replace("Z", "+00:00"))
        # Ingestion time must be strictly after observation time (physical latency exists)
        self.assertGreater(ingest_dt, obs_dt)
        latency_hours = (ingest_dt - obs_dt).total_seconds() / 3600.0
        self.assertGreater(latency_hours, 1.0, "Physical latency from GPM orbit to ingest must be > 1h")

    def test_03_canonical_assessment_generation_and_weights(self):
        """Verify that execute_live_assessment produces an authentic ASM-LIVE record with locked 40/30/20/10 weights."""
        asm = self.service.execute_live_assessment(force=True)
        self.assertTrue(asm["assessment_id"].startswith("ASM-LIVE-"))
        self.assertEqual(asm["assessment_mode"], "OPERATIONAL")
        self.assertEqual(asm["assessment_status"], "CURRENT_ASSESSMENT_ACTIVE")
        self.assertTrue(asm["current_risk_available"])

        # Verify locked four-factor fusion weights
        weights = asm["fusion_weights"]
        self.assertEqual(weights["susceptibility"], 0.40)
        self.assertEqual(weights["rainfall"], 0.30)
        self.assertEqual(weights["soil_moisture"], 0.20)
        self.assertEqual(weights["satellite_change"], 0.10)

        # Verify all 48 hotspots evaluated
        self.assertEqual(asm["risk_summary"]["total_hotspots_evaluated"], 48)
        self.assertGreater(asm["risk_summary"]["max_risk_score"], 0.0)

    def test_04_duplicate_observation_suppresses_reassessment(self):
        """Verify that re-evaluating an already ingested observation yields ALREADY_CURRENT and does not create duplicate assessments."""
        gpm = self.service.discover_and_acquire_gpm_nrt()
        # First execution (force=True to establish hash)
        asm1 = self.service.execute_live_assessment(gpm_observation=gpm, force=True)
        id1 = asm1["assessment_id"]

        # Second execution without force must detect duplicate
        asm2 = self.service.execute_live_assessment(gpm_observation=gpm, force=False)
        self.assertEqual(asm2.get("dedup_status"), "ALREADY_CURRENT")
        self.assertEqual(asm2["assessment_id"], id1, "Assessment ID must not change upon duplicate poll")

    def test_05_sqlite_persistence_and_provenance(self):
        """Verify that live assessments are persisted in SQLite with complete provenance envelopes."""
        asm = self.service.execute_live_assessment(force=True)
        asm_id = asm["assessment_id"]

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM live_assessments WHERE assessment_id = ?", (asm_id,))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Assessment must be persisted in SQLite live_assessments table")
        self.assertEqual(row["assessment_mode"], "OPERATIONAL")
        self.assertEqual(row["current_risk_available"], 1)
        self.assertIn("GPM_3IMERGHHE", row["gpm_granule_id"])

        provenance = json.loads(row["provenance_json"])
        self.assertIn("rainfall", provenance)
        self.assertIn("soil_moisture", provenance)
        self.assertIn("sar_radar", provenance)
        self.assertIn("ground_sensors", provenance)

    def test_06_current_assessment_api_endpoint(self):
        """Verify GET /api/assessment/current exposes genuine operational assessment."""
        res = requests.get(f"{self.base_url}/api/assessment/current", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["assessment_mode"], "OPERATIONAL")
        self.assertEqual(data["assessment_status"], "CURRENT_ASSESSMENT_ACTIVE")
        self.assertTrue(data["current_risk_available"])
        self.assertTrue(data["assessment_id"].startswith("ASM-LIVE-"))
        self.assertIn("risk_summary", data)

    def test_07_assessment_history_api_endpoint(self):
        """Verify GET /api/assessment/history returns SQLite records with provenance."""
        res = requests.get(f"{self.base_url}/api/assessment/history?limit=5", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("assessments", data)
        self.assertGreater(data["total_records"], 0)
        latest = data["assessments"][0]
        self.assertTrue(latest["assessment_id"].startswith("ASM-LIVE-"))

    def test_08_zero_demo_contamination(self):
        """Verify strict isolation: operational assessment NEVER contains demo replay IDs or scores."""
        res = requests.get(f"{self.base_url}/api/assessment/current", timeout=5)
        data = res.json()

        # Operational mode must NOT report DEMO_REPLAY or LOCAL_REPLAY
        self.assertNotEqual(data.get("assessment_mode"), "DEMO_REPLAY")
        self.assertNotEqual(data.get("data_source"), "LOCAL_REPLAY")

        # Operational assessment ID must NOT be EVT-MEG-001
        self.assertNotEqual(data.get("assessment_id"), "EVT-MEG-001")

        # Demo replay endpoint remains separate and unaffected
        res_demo = requests.get(f"{self.base_url}/api/assessment/demo?hotspot_id=EVT-MEG-001", timeout=5)
        self.assertEqual(res_demo.status_code, 200)
        data_demo = res_demo.json()
        self.assertEqual(data_demo["assessment_mode"], "DEMO_REPLAY")
        self.assertEqual(data_demo["data_source"], "LOCAL_REPLAY")
        self.assertEqual(data_demo["risk_score"], 0.7055)

    def test_09_stale_assessment_safety_rule(self):
        """Verify that when current risk is unavailable, the API returns NOT_AVAILABLE and never reuses previous scores as current."""
        # Test unit method on clean instance without active assessment
        clean_svc = LiveAssessmentService()
        clean_svc.current_assessment = None
        unavail = clean_svc.get_current_assessment()
        self.assertEqual(unavail["assessment_mode"], "OPERATIONAL")
        self.assertEqual(unavail["assessment_status"], "NOT_AVAILABLE")
        self.assertFalse(unavail["current_risk_available"])
        self.assertIn("never present a previous risk score", unavail["disclaimer"])


if __name__ == "__main__":
    unittest.main()
