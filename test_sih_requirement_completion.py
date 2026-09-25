"""
NER-SAFE: SIH 26001 Requirement Completion & Traceability Test Suite
Verifies:
1. Complete SIH requirement matrix coverage (24/24 requirements documented).
2. Source-agnostic ingestion manager lifecycle states and credential boundaries.
3. Strict No-InSAR scientific disclaimer enforcement.
4. Multilingual early warning bulletin generation (en, hi, khasi, mizo).
5. Road connectivity operational status classification (OPEN, AT_RISK, BLOCKED, UNKNOWN).
"""

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

from source_ingestion_manager import (
    source_ingestion_mgr, STATE_FRESH, STATE_RECENT, STATE_DATA_STALE,
    STATE_AUTH_REQUIRED, STATE_INVALID
)
from alert_dissemination_engine import alert_dissemination_engine, MULTILINGUAL_TEMPLATES
from road_connectivity_analyzer import (
    road_connectivity_analyzer, STATUS_OPEN, STATUS_AT_RISK, STATUS_BLOCKED, STATUS_UNKNOWN
)

class TestSIHRequirementCompletion(unittest.TestCase):
    def test_01_matrix_file_exists(self):
        """Verifies authoritative SIH 26001 requirement matrix exists."""
        matrix_path = os.path.join(WORKSPACE, "NER_SAFE_SIH_26001_REQUIREMENT_MATRIX.md")
        self.assertTrue(os.path.isfile(matrix_path), "Requirement matrix file must exist")
        with open(matrix_path, "r", encoding="utf-8") as f:
            content = f.read()
        for i in range(1, 25):
            req_tag = f"REQ-{i:02d}"
            self.assertIn(req_tag, content, f"Matrix must cover {req_tag}")

    def test_02_source_ingestion_freshness_states(self):
        """Verifies ingestion manager evaluates freshness correctly."""
        now = datetime.now(timezone.utc)
        
        # 1. Fresh observation (<4h GPM)
        obs_fresh = (now - timedelta(hours=2)).isoformat()
        state = source_ingestion_mgr.evaluate_freshness(datetime.fromisoformat(obs_fresh), "GPM_PRECIPITATION")
        self.assertEqual(state, STATE_FRESH)
        
        # 2. Stale observation (>12h GPM)
        obs_stale = (now - timedelta(hours=14)).isoformat()
        state = source_ingestion_mgr.evaluate_freshness(datetime.fromisoformat(obs_stale), "GPM_PRECIPITATION")
        self.assertEqual(state, STATE_DATA_STALE)
        
        # 3. Future observation -> Invalid
        obs_future = (now + timedelta(hours=5)).isoformat()
        state = source_ingestion_mgr.evaluate_freshness(datetime.fromisoformat(obs_future), "GPM_PRECIPITATION")
        self.assertEqual(state, STATE_INVALID)

    def test_03_credential_aware_boundaries(self):
        """Verifies credential awareness without fake logins."""
        # Unauthenticated environment checks
        has_gpm, status_gpm = source_ingestion_mgr.check_credentials("GPM_PRECIPITATION")
        has_s1, status_s1 = source_ingestion_mgr.check_credentials("SENTINEL1_SAR")
        has_imd, status_imd = source_ingestion_mgr.check_credentials("IMD_WEATHER")
        
        # IMD must honestly return AWAITING_INSTITUTIONAL_MOU
        self.assertIn("AWAITING_INSTITUTIONAL_MOU", status_imd)
        self.assertIn("CDSE", status_s1)

    def test_04_no_insar_disclaimer_strictness(self):
        """Verifies exact mandatory InSAR disclaimer wording."""
        s1_spec = source_ingestion_mgr.specs.get("SENTINEL1_SAR", {})
        expected_disclaimer = "Sentinel-1 SAR surface-change monitoring is used as an all-weather/night-capable surface-change signal. This implementation does not perform InSAR displacement measurement."
        self.assertEqual(s1_spec.get("disclaimer"), expected_disclaimer)

    def test_05_multilingual_alert_generation(self):
        """Verifies alert dissemination supports all 4 regional languages."""
        alert = alert_dissemination_engine.create_alert(
            hotspot_id="EVT-MEG-001",
            risk_score=0.7055,
            risk_tier="CRITICAL",
            district="East Khasi Hills",
            state="Meghalaya"
        )
        self.assertIn("multilingual_content", alert)
        content = alert["multilingual_content"]
        self.assertIn("en", content)
        self.assertIn("hi", content)
        self.assertIn("khasi", content)
        self.assertIn("mizo", content)
        self.assertIn("KA JINGMA", content["khasi"]["headline"])
        self.assertIn("LEILASO", content["mizo"]["headline"])

    def test_06_road_connectivity_states(self):
        """Verifies road connectivity correctly evaluates OPEN, AT_RISK, BLOCKED, UNKNOWN."""
        # 1. Verified physical blockage
        res_blocked = road_connectivity_analyzer.evaluate_road_status(
            "NH-206", hotspot_id="EVT-MEG-001", verified_blockage=True
        )
        self.assertEqual(res_blocked["status"], STATUS_BLOCKED)
        
        # 2. Unverified report
        res_unk = road_connectivity_analyzer.evaluate_road_status(
            "NH-206", hotspot_id="EVT-MEG-001", unverified_report=True
        )
        self.assertEqual(res_unk["status"], STATUS_UNKNOWN)
        
        # 3. Intersecting critical corridor
        res_risk = road_connectivity_analyzer.evaluate_road_status(
            "NH-206", hotspot_id="EVT-MEG-001"
        )
        self.assertEqual(res_risk["status"], STATUS_AT_RISK)
        
        # 4. Safe road
        res_open = road_connectivity_analyzer.evaluate_road_status(
            "Safe-Highway", hotspot_id="NON_EXISTENT_HOTSPOT"
        )
        self.assertEqual(res_open["status"], STATUS_OPEN)

if __name__ == "__main__":
    unittest.main()
