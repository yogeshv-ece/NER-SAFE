"""
=============================================================================
NER-SAFE: Test Suite for Live Observation to Dynamic GIS Heatmap
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validates the complete operational GIS heatmap update chain:
  1. Real GPM observation intake and rainfall anomaly update.
  2. Live operational assessment generation (ASM-LIVE-...).
  3. Dynamic GeoJSON risk surface generation.
  4. Layer metadata catalog integrity (all 11 layers represented).
  5. Zero-stale enforcement: returns NOT_AVAILABLE when live data absent.
  6. InSAR layer integrity: returns AUTH_REQUIRED/WAITING without fabrication.
  7. REST endpoints exposure (/api/heatmap/current, /api/heatmap/layers, /api/models/comparison).
  8. Strict isolation: Demo replay never leaks into live operational heatmap.
=============================================================================
"""

import os
import json
import time
import threading
import unittest
import requests
from datetime import datetime, timezone

from dynamic_risk_heatmap import DynamicRiskHeatmapEngine, dynamic_risk_heatmap_engine
from live_assessment_service import LiveAssessmentService
from live_sensor_server_extension import start_extended_server

class TestLiveObservationToHeatmap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        cls.test_port = sock.getsockname()[1]
        sock.close()

        cls.httpd = start_extended_server(cls.test_port)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.4)
        cls.base_url = f"http://127.0.0.1:{cls.test_port}"
        cls.engine = dynamic_risk_heatmap_engine
        cls.service = LiveAssessmentService()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
        except Exception:
            pass

    def test_01_layer_catalog_contains_eleven_layers(self):
        """Verifies that the GIS heatmap engine publishes all 11 required layers."""
        cat = self.engine.get_layer_catalog()
        self.assertIn("total_layers", cat)
        self.assertEqual(cat["total_layers"], 11)
        layer_ids = [l["id"] for l in cat["layers"]]
        self.assertIn("current_operational_risk", layer_ids)
        self.assertIn("rf_susceptibility", layer_ids)
        self.assertIn("xgboost_probability", layer_ids)
        self.assertIn("cnn_susceptibility", layer_ids)
        self.assertIn("rainfall_trigger", layer_ids)
        self.assertIn("soil_moisture", layer_ids)
        self.assertIn("sar_change", layer_ids)
        self.assertIn("insar_deformation", layer_ids)
        self.assertIn("exposure_infrastructure", layer_ids)
        self.assertIn("road_vulnerability", layer_ids)
        self.assertIn("regional_hotspots", layer_ids)

    def test_02_dynamic_heatmap_reflects_active_assessment(self):
        """Verifies that the dynamic risk heatmap accurately maps the current live assessment."""
        asm = self.service.execute_live_assessment(force=True)
        self.assertTrue(asm["assessment_id"].startswith("ASM-LIVE-"))

        heat = self.engine.generate_current_operational_risk_heatmap(asm)
        self.assertEqual(heat["status"], "LIVE_ACTIVE")
        self.assertTrue(heat["current_risk_available"])
        self.assertEqual(heat["assessment_id"], asm["assessment_id"])

        geojson = heat["geojson"]
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 48)

        # Verify property integrity of first hotspot
        f0 = geojson["features"][0]
        self.assertIn("geometry", f0)
        props = f0["properties"]
        self.assertIn("risk_score", props)
        self.assertIn("risk_tier", props)
        self.assertIn("color", props)
        self.assertIn("susceptibility_baseline", props)
        self.assertIn("rainfall_anomaly", props)
        self.assertIn("provenance", props)

    def test_03_zero_stale_enforcement(self):
        """Verifies that when no live assessment is available, current risk heatmap reports NOT_AVAILABLE."""
        stale_asm = {
            "assessment_mode": "OPERATIONAL",
            "assessment_status": "NOT_AVAILABLE",
            "current_risk_available": False,
            "reason": "Observation feed expired (> 3h). Zero-tolerance stale rule enforced."
        }
        heat = self.engine.generate_current_operational_risk_heatmap(stale_asm)
        self.assertEqual(heat["status"], "NOT_AVAILABLE")
        self.assertFalse(heat["current_risk_available"])
        self.assertEqual(len(heat["geojson"]["features"]), 0)
        self.assertIn("Zero-tolerance stale rule", heat["reason"])

    def test_04_cnn_experimental_heatmap_surface(self):
        """Verifies experimental PyTorch CNN spatial risk heatmap properties."""
        cnn_heat = self.engine.generate_cnn_susceptibility_heatmap()
        self.assertEqual(cnn_heat["status"], "EXPERIMENTAL")
        self.assertEqual(cnn_heat["model_type"], "EXPERIMENTAL_DEEP_LEARNING")
        self.assertEqual(len(cnn_heat["geojson"]["features"]), 48)

        f0 = cnn_heat["geojson"]["features"][0]
        self.assertIn("cnn_susceptibility_probability", f0["properties"])
        self.assertIn("PyTorch Spatial CNN", f0["properties"]["model_framework"])

    def test_05_insar_heatmap_data_access_integrity(self):
        """Verifies InSAR heatmap reports authentic status (LIVE_VERIFIED when real SLC acquired or WAITING_FOR_COMPATIBLE_PAIR without fabrication)."""
        insar_heat = self.engine.generate_insar_deformation_heatmap()
        if insar_heat.get("status") == "LIVE_VERIFIED":
            self.assertEqual(insar_heat["status"], "LIVE_VERIFIED")
            self.assertEqual(insar_heat["data_access"], "VERIFIED_CDSE_S3")
            self.assertEqual(len(insar_heat["geojson"]["features"]), 48)
            self.assertIn("relative_los_displacement_meters", insar_heat["units"])
        else:
            self.assertEqual(insar_heat["status"], "INSAR_WAITING_FOR_COMPATIBLE_PAIR")
            self.assertEqual(insar_heat["data_access"], "AUTH_REQUIRED")
            self.assertEqual(len(insar_heat["geojson"]["features"]), 0)
            self.assertIn("requires repeat-pass Sentinel-1 IW SLC", insar_heat["disclaimer"])

    def test_06_rest_api_heatmap_current_endpoint(self):
        """Verifies GET /api/heatmap/current returns valid GeoJSON payload."""
        res = requests.get(f"{self.base_url}/api/heatmap/current", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("layer_id", data)
        self.assertEqual(data["layer_id"], "current_operational_risk")
        self.assertIn("geojson", data)

    def test_07_rest_api_heatmap_layers_endpoint(self):
        """Verifies GET /api/heatmap/layers returns complete catalog."""
        res = requests.get(f"{self.base_url}/api/heatmap/layers", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_layers"], 11)

    def test_08_rest_api_models_comparison_endpoint(self):
        """Verifies GET /api/models/comparison returns scientific comparison and RF retention."""
        res = requests.get(f"{self.base_url}/api/models/comparison", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["governance_decision"], "PRODUCTION_FROZEN_RF_RETAINED")
        self.assertEqual(data["production_model"]["model_name"], "Calibrated Random Forest")
        self.assertEqual(data["production_model"]["pr_auc"], 0.3151)
        self.assertEqual(len(data["experimental_models"]), 2)

    def test_09_demo_replay_isolation_from_heatmap(self):
        """Verifies that demo replay endpoint remains separate and does not taint operational heatmap."""
        demo_res = requests.get(f"{self.base_url}/api/assessment/demo?hotspot_id=EVT-MEG-001", timeout=5)
        self.assertEqual(demo_res.status_code, 200)
        demo_data = demo_res.json()
        self.assertEqual(demo_data["assessment_mode"], "DEMO_REPLAY")

        # Operational heatmap must NOT carry demo mode
        heat_res = requests.get(f"{self.base_url}/api/heatmap/current", timeout=5)
        heat_data = heat_res.json()
        if heat_data.get("current_risk_available"):
            for f in heat_data["geojson"]["features"]:
                self.assertEqual(f["properties"]["provenance"]["mode"], "OPERATIONAL")

if __name__ == "__main__":
    unittest.main()
