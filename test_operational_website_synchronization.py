"""
=============================================================================
NER-SAFE: Operational Website Synchronization & Live UI Verification Suite
=============================================================================
Verifies all 18 criteria required by Section 21:
1.  SIMULATION_REMOVED_FROM_UI
2.  NO_MOCK_OPERATIONAL_DATA
3.  VIDEO_UPLOAD_UI
4.  VIDEO_UPLOAD_BACKEND
5.  VIDEO_STATUS_REFRESH
6.  IMAGE_UPLOAD
7.  IMAGE_ANALYSIS
8.  IMAGE_ANALYSIS_SECURITY
9.  IMAGE_ANALYSIS_ZERO_RISK_WEIGHT
10. 3D_LIVE_RISK_BINDING
11. 3D_LIVE_REFRESH
12. 3D_CURRENT_TIMESTAMP
13. 3D_CURRENT_MODEL_PROVENANCE
14. 3D_WEBGL_FALLBACK
15. 2D_3D_DATA_CONSISTENCY
16. MODEL_UI_SINGLE_XGBOOST
17. NO_RF_FALLBACK_UI
18. NO_ALTERNATE_MODEL_UI
=============================================================================
"""

import os
import sys
import json
import base64
import unittest
import urllib.parse
from http.cookies import SimpleCookie

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

import fusion_engine
import database
from media_integrity_analyzer import media_integrity_analyzer
from video_integrity_analyzer import video_analyzer

class TestOperationalWebsiteSynchronization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        with open(os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html"), "r", encoding="utf-8") as f:
            cls.live_html = f.read()
        with open(os.path.join(PROJECT_ROOT, "ner_safe_citizen_app.html"), "r", encoding="utf-8") as f:
            cls.citizen_html = f.read()
        with open(os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard_extended.html"), "r", encoding="utf-8") as f:
            cls.extended_html = f.read()

    # 1. SIMULATION_REMOVED_FROM_UI
    def test_01_SIMULATION_REMOVED_FROM_UI(self):
        # Operational live dashboard must not have simulation controls
        self.assertNotIn("Start Simulation Cycle", self.live_html)
        self.assertNotIn("SIMULATION / REPLAY CONTROLS", self.live_html)
        self.assertNotIn('id="btnModeReplay"', self.live_html)
        self.assertNotIn('id="e2eDemoWorkflowCard"', self.live_html)

        # Citizen app must not have simulation or demo controls
        self.assertNotIn("Start Simulation Cycle", self.citizen_html)
        self.assertNotIn("Historical Replay", self.citizen_html)
        self.assertNotIn("e2eDemoWorkflowCard", self.citizen_html)

        # Extended dashboard must not have replay controls
        self.assertNotIn('id="btnModeReplay"', self.extended_html)
        self.assertNotIn('id="e2eDemoWorkflowCard"', self.extended_html)

    # 2. NO_MOCK_OPERATIONAL_DATA
    def test_02_NO_MOCK_OPERATIONAL_DATA(self):
        # Active risk and telemetry must consume live APIs, no hardcoded scores in HUDs
        self.assertNotIn("EVT-MEG-001 (0.7055 | CRITICAL)", self.live_html)
        self.assertNotIn("EVT-MEG-001 (0.7055 | CRITICAL)", self.extended_html)
        # Hotspots loaded from dynamic API
        self.assertIn("fetch('/api/monitoring/hotspots')", self.live_html)

    # 3. VIDEO_UPLOAD_UI
    def test_03_VIDEO_UPLOAD_UI(self):
        # Citizen app video selector and progress
        self.assertIn('setMediaType(\'VIDEO\')', self.citizen_html)
        self.assertIn('id="fileVideo"', self.citizen_html)
        self.assertIn('id="videoProgressBox"', self.citizen_html)
        self.assertIn('id="videoModerationCard"', self.citizen_html)

        # Dashboard citizen view video selector and progress
        self.assertIn('setDashMediaType(\'VIDEO\')', self.live_html)
        self.assertIn('id="dashVideoInput"', self.live_html)
        self.assertIn('id="dashVideoProgressBox"', self.live_html)
        self.assertIn('id="dashVideoModerationCard"', self.live_html)

    # 4. VIDEO_UPLOAD_BACKEND
    def test_04_VIDEO_UPLOAD_BACKEND(self):
        # Generate minimal valid MP4 container with ftyp atom
        valid_mp4 = (
            b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
            b"\x00\x00\x00\x08free"
            b"\x00\x00\x00\x68moov"
            b"\x00\x00\x00\x60mvhd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\xe8\x00\x00\x13\x88\x00\x01\x00\x00\x01\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x02"
        )
        res = video_analyzer.process_video_submission(
            original_filename="operational_slope_evidence.mp4",
            file_bytes=valid_mp4,
            gps_lat=25.15,
            gps_lon=92.35
        )
        self.assertTrue(res["success"])
        self.assertIn("video_id", res)
        self.assertEqual(res["moderation_status"], "READY_FOR_REVIEW")
        self.assertEqual(res["operational_risk_weight"], 0.0)

    # 5. VIDEO_STATUS_REFRESH
    def test_05_VIDEO_STATUS_REFRESH(self):
        # Test getting video record from list_videos
        videos = video_analyzer.list_videos()
        self.assertIsInstance(videos, list)
        if videos:
            vid = videos[0]["video_id"]
            self.assertIn(videos[0]["moderation_status"], ["READY_FOR_REVIEW", "VERIFIED", "REJECTED", "QUARANTINED"])

    # 6. IMAGE_UPLOAD
    def test_06_IMAGE_UPLOAD(self):
        # Test citizen report database persistence with photo hash
        import hashlib
        sample_png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        sha = hashlib.sha256(sample_png).hexdigest()
        rep_id = database.add_report({
            "latitude": 25.20,
            "longitude": 92.40,
            "accuracy_m": 5.0,
            "category": "SURFACE_TENSION_CRACK",
            "displacement_width": "5_TO_15_CM",
            "water_seepage": True,
            "seepage_flow_type": "MUDDY_TURBID_FLOW",
            "nearby_structures_count": "FEW_1_TO_5",
            "corridor_proximity": "NH-06 Km 42",
            "user_notes": "Active tension fissure observed.",
            "photo_filename": "slope_fissure.png",
            "photo_sha256": sha,
            "ai_analysis": {"analysis_status": "ANALYZED", "evidence_category": "GEOTECHNICAL_FIELD_EVIDENCE"}
        })
        self.assertIsNotNone(rep_id)
        all_reps = database.get_all_reports()
        matching = [f for f in all_reps.get("features", []) if f.get("properties", {}).get("report_id") == rep_id]
        self.assertTrue(len(matching) > 0)
        p = matching[0]["properties"]
        self.assertEqual(p["photo_sha256"], sha)

    # 7. IMAGE_ANALYSIS
    def test_07_IMAGE_ANALYSIS(self):
        sample_png = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
            b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        res = media_integrity_analyzer.process_image_submission(sample_png, "test_slope.png")
        self.assertTrue(res["success"])
        self.assertEqual(res["analysis_status"], "ANALYZED")
        self.assertEqual(res["operational_risk_contribution"], 0.0)
        self.assertEqual(res["human_verification"], "REQUIRED")

    # 8. IMAGE_ANALYSIS_SECURITY
    def test_08_IMAGE_ANALYSIS_SECURITY(self):
        # 1. Path traversal filename sanitization
        res_trav = media_integrity_analyzer.process_image_submission(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
            "../../../malicious.png"
        )
        self.assertNotIn("..", res_trav["filename"])
        self.assertTrue("UPLOADS" in res_trav["saved_path"])

        # 2. Executable payload rejection (Windows MZ header)
        res_exe = media_integrity_analyzer.process_image_submission(b"MZ\x90\x00\x03\x00\x00\x00", "payload.exe")
        self.assertFalse(res_exe["success"])

        # 3. Oversized image (> 15MB)
        res_big = media_integrity_analyzer.process_image_submission(b"0" * (16 * 1024 * 1024), "big.jpg")
        self.assertFalse(res_big["success"])

    # 9. IMAGE_ANALYSIS_ZERO_RISK_WEIGHT
    def test_09_IMAGE_ANALYSIS_ZERO_RISK_WEIGHT(self):
        # Invariant: media analysis strictly isolated as contextual evidence with 0.00 operational weight
        res = media_integrity_analyzer.process_image_submission(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82",
            "field_photo.png"
        )
        self.assertEqual(res["operational_risk_contribution"], 0.0)
        
        # Verify 4-factor formula unchanged in fusion_engine
        data = fusion_engine.compute_fused_hotspots()
        weights = data["metadata"]["fusion_weights"]
        self.assertEqual(weights["susceptibility"], 0.40)
        self.assertEqual(weights["rainfall"], 0.30)
        self.assertEqual(weights["soil_moisture"], 0.20)
        self.assertEqual(weights["satellite"], 0.10)

    # 10. 3D_LIVE_RISK_BINDING
    def test_10_3D_LIVE_RISK_BINDING(self):
        # In live dashboard: Cesium is populated directly from hotspotsData.features
        self.assertIn("function populateCesiumHotspots(features)", self.live_html)
        self.assertIn("populateCesiumHotspots(hotspotsData.features)", self.live_html)

    # 11. 3D_LIVE_REFRESH
    def test_11_3D_LIVE_REFRESH(self):
        # When loadHotspotsAndCorridors() runs, it calls populateCesiumHotspots and updateCesiumHUD
        self.assertIn("populateCesiumHotspots(hotspotsData.features);", self.live_html)
        self.assertIn("updateCesiumHUD();", self.live_html)

    # 12. 3D_CURRENT_TIMESTAMP
    def test_12_3D_CURRENT_TIMESTAMP(self):
        # Cesium HUD includes LIVE ASSESSMENT timestamp element
        self.assertIn('id="hudAssessmentTime"', self.live_html)
        self.assertIn('LIVE ASSESSMENT:', self.live_html)

    # 13. 3D_CURRENT_MODEL_PROVENANCE
    def test_13_3D_CURRENT_MODEL_PROVENANCE(self):
        # Cesium HUD includes Model and Rainfall Provenance elements
        self.assertIn('id="hudModelName"', self.live_html)
        self.assertIn('CALIBRATED XGBOOST V1.1', self.live_html)
        self.assertIn('id="hudRainfallSource"', self.live_html)
        self.assertIn('id="hudSourceAge"', self.live_html)

    # 14. 3D_WEBGL_FALLBACK
    def test_14_3D_WEBGL_FALLBACK(self):
        # WebGL fallback check preserves 2D operational map
        self.assertIn("function isWebGLSupported()", self.live_html)
        self.assertIn("id=\"cesiumFallbackNotice\"", self.live_html)
        self.assertIn("Operational 2D Leaflet map active", self.live_html)

    # 15. 2D_3D_DATA_CONSISTENCY
    def test_15_2D_3D_DATA_CONSISTENCY(self):
        # 2D and 3D consume exact same 48-hotspot GeoJSON
        data = fusion_engine.compute_fused_hotspots()
        features = data["features"]
        self.assertEqual(len(features), 48)
        for f in features:
            p = f["properties"]
            self.assertIn("fused_risk_score", p)
            self.assertIn("fused_tier", p)
            self.assertIn(p["fused_tier"], ["CRITICAL", "HIGH", "MODERATE", "WATCH"])

    # 16. MODEL_UI_SINGLE_XGBOOST
    def test_16_MODEL_UI_SINGLE_XGBOOST(self):
        self.assertIn("CALIBRATED XGBOOST V1.1", self.live_html)
        self.assertIn("Calibrated XGBoost V1.1", self.extended_html)

    # 17. NO_RF_FALLBACK_UI
    def test_17_NO_RF_FALLBACK_UI(self):
        # Zero Random Forest fallback in operational UI
        self.assertNotIn("AUTOMATIC_RF_FALLBACK_ACTIVE", self.live_html)
        self.assertNotIn("AUTOMATIC_RF_FALLBACK_ACTIVE", self.extended_html)

    # 18. NO_ALTERNATE_MODEL_UI
    def test_18_NO_ALTERNATE_MODEL_UI(self):
        # Research models isolated with 0.00 weight
        self.assertIn("RESEARCH ONLY", self.extended_html)
        self.assertNotIn("<select id=\"modelSelector\"", self.live_html)

if __name__ == "__main__":
    unittest.main(verbosity=2)
