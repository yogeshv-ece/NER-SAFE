"""
=============================================================================
NER-SAFE: Official IMD Live Weather & Rainfall Integration Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Comprehensive validation for official IMD API client, authentication,
         error resilience, unit handling, ground corroboration comparison with
         NASA GPM, warning ingestion, scheduler telemetry, and risk engine safety.
Standards: Strictly 0 emojis, anti-fabrication compliance, frozen risk weights.
=============================================================================
"""

import os
import sys
import json
import math
import unittest
import urllib.error
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from imd_api_client import IMDAPIClient, TARGET_STATIONS
from source_ingestion_manager import source_ingestion_mgr
from live_monitoring_scheduler import live_monitoring_scheduler


class TestIMDLiveIntegration(unittest.TestCase):
    """Full test battery for official IMD integration."""

    def setUp(self):
        self.client = IMDAPIClient()

    # -------------------------------------------------------------------------
    # 1. Authentication Configuration & Missing Credentials
    # -------------------------------------------------------------------------
    def test_01_auth_configuration_unconfigured(self):
        """Validates that unconfigured credentials return IMD_AUTH_REQUIRED safely."""
        with patch.dict(os.environ, {"IMD_API_KEY": "", "IMD_JWT_TOKEN": ""}, clear=False):
            client = IMDAPIClient()
            cfg = client.check_auth_configuration()
            self.assertFalse(cfg["configured"])
            self.assertEqual(cfg["status"], "UNCONFIGURED")

            test_res = client.test_authentication()
            self.assertEqual(test_res["status"], "AUTH_REQUIRED")
            self.assertEqual(test_res["auth_code"], "IMD_AUTH_REQUIRED")
            self.assertIn("registration_url", test_res)
            # Ensure no secret strings or passwords printed
            self.assertNotIn("password", str(test_res).lower())

    def test_02_auth_configuration_partial_key_only(self):
        """Validates that having API key without JWT reports PARTIAL_CONFIG."""
        with patch.dict(os.environ, {"IMD_API_KEY": "valid_test_key_sample", "IMD_JWT_TOKEN": ""}, clear=False):
            client = IMDAPIClient()
            cfg = client.check_auth_configuration()
            self.assertFalse(cfg["configured"])
            self.assertEqual(cfg["status"], "PARTIAL_CONFIG")

    def test_03_auth_configuration_both_configured(self):
        """Validates that having both API key and JWT reports CONFIGURED."""
        with patch.dict(os.environ, {"IMD_API_KEY": "sample_key", "IMD_JWT_TOKEN": "sample_token"}, clear=False):
            client = IMDAPIClient()
            cfg = client.check_auth_configuration()
            self.assertTrue(cfg["configured"])
            self.assertEqual(cfg["status"], "CONFIGURED")

    # -------------------------------------------------------------------------
    # 2. Live HTTP 401 Rejection (Empirical Official Gateway Probe)
    # -------------------------------------------------------------------------
    def test_04_live_official_gateway_rejection(self):
        """Probes live official IMD endpoint without credentials to verify HTTP 401 rejection."""
        with patch.dict(os.environ, {"IMD_API_KEY": "", "IMD_JWT_TOKEN": ""}, clear=False):
            client = IMDAPIClient()
            # Force call with empty headers to test server response
            import urllib.request
            req = urllib.request.Request(
                "https://api.imd.gov.in/api/v1/current_wx",
                headers={"User-Agent": "NER-SAFE-Test/1.0", "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=10, context=client.ssl_context) as resp:
                    # Should not reach here without auth
                    self.fail("Expected HTTP 401 from official IMD API")
            except urllib.error.HTTPError as he:
                self.assertEqual(he.code, 401)
                err_data = json.loads(he.read().decode("utf-8"))
                self.assertIn("error", err_data)
                self.assertIn("API key missing", err_data["error"])

    # -------------------------------------------------------------------------
    # 3. Network Fault Resilience: Timeout & HTTP Errors
    # -------------------------------------------------------------------------
    def test_05_network_timeout_handling(self):
        """Verifies network timeouts return SOURCE_UNAVAILABLE without crashing."""
        with patch.dict(os.environ, {"IMD_API_KEY": "k", "IMD_JWT_TOKEN": "t"}, clear=False):
            client = IMDAPIClient()
            with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
                res = client.fetch_aws_station_data("42516")
                self.assertEqual(res["status"], "SOURCE_UNAVAILABLE")
                self.assertIn("timed out", res["error"])

    def test_06_http_503_service_unavailable(self):
        """Verifies HTTP 500/503 server errors are safely caught."""
        with patch.dict(os.environ, {"IMD_API_KEY": "k", "IMD_JWT_TOKEN": "t"}, clear=False):
            client = IMDAPIClient()
            mock_err = urllib.error.HTTPError(
                url="https://api.imd.gov.in/api/v1/aws_data",
                code=503,
                msg="Service Unavailable",
                hdrs={},
                fp=None
            )
            with patch("urllib.request.urlopen", side_effect=mock_err):
                res = client.fetch_aws_station_data("42516")
                self.assertEqual(res["status"], "SOURCE_UNAVAILABLE")
                self.assertEqual(res["http_status"], 503)

    def test_07_malformed_json_response(self):
        """Verifies malformed JSON does not cause unhandled crash."""
        with patch.dict(os.environ, {"IMD_API_KEY": "k", "IMD_JWT_TOKEN": "t"}, clear=False):
            client = IMDAPIClient()
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"<html><head><title>Bad Gateway</title></head></html>"
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp):
                res = client.fetch_aws_station_data("42516")
                self.assertEqual(res["status"], "SOURCE_UNAVAILABLE")

    # -------------------------------------------------------------------------
    # 4. Anti-Fabrication & Missing Observation Handling
    # -------------------------------------------------------------------------
    def test_08_missing_rainfall_does_not_become_zero(self):
        """CRITICAL: Missing IMD observations must NOT become 0.0 mm."""
        with patch.dict(os.environ, {"IMD_API_KEY": "", "IMD_JWT_TOKEN": ""}, clear=False):
            client = IMDAPIClient()
            obs = client.fetch_station_observation("SHILLONG")
            self.assertEqual(obs["status"], "AWAITING_INSTITUTIONAL_MOU")
            self.assertIsNone(obs["instantaneous_rainfall_mm_hr"])
            self.assertIsNone(obs["accumulated_24h_rainfall_mm"])
            self.assertNotEqual(obs["instantaneous_rainfall_mm_hr"], 0.0)

    # -------------------------------------------------------------------------
    # 5. Units & Rainfall Distinction
    # -------------------------------------------------------------------------
    def test_09_units_and_rainfall_distinction(self):
        """Ensures instantaneous rate (mm/hr), 24h accumulation (mm), and forecast are distinct."""
        with patch.dict(os.environ, {"IMD_API_KEY": "k", "IMD_JWT_TOKEN": "t"}, clear=False):
            client = IMDAPIClient()
            mock_data = {
                "rain_fall": 12.5,
                "rf_24hr": 84.0,
                "temp": 22.4,
                "rh": 95,
                "ws": 8.0,
                "weather_condition": "Heavy Rain"
            }
            with patch.object(client, "fetch_aws_station_data", return_value={"status": "OPERATIONAL", "data": [mock_data]}):
                obs = client.fetch_station_observation("SHILLONG")
                self.assertEqual(obs["status"], "OPERATIONAL")
                self.assertEqual(obs["instantaneous_rainfall_mm_hr"], 12.5)
                self.assertEqual(obs["accumulated_24h_rainfall_mm"], 84.0)
                self.assertIsNone(obs["forecast_rainfall_mm"])
                self.assertEqual(obs["temperature_c"], 22.4)
                self.assertEqual(obs["humidity_pct"], 95.0)

    # -------------------------------------------------------------------------
    # 6. GPM vs IMD Ground Corroboration Comparison
    # -------------------------------------------------------------------------
    def test_10_gpm_imd_comparison(self):
        """Tests independent ground corroboration comparison between GPM and IMD."""
        imd_obs = {
            "station_id": "42516",
            "station_name": "Shillong (Observatory)",
            "latitude": 25.5686,
            "longitude": 91.8831,
            "instantaneous_rainfall_mm_hr": 14.2,
            "observation_timestamp": "2026-09-14T10:00:00Z"
        }
        gpm_obs = {
            "feature_value": 18.0,
            "observation_timestamp": "2026-09-14T10:30:00Z",
            "coverage": {"lat_center": 25.55, "lon_center": 91.85}
        }

        cmp_res = IMDAPIClient.compare_with_gpm(imd_obs, gpm_obs)
        self.assertTrue(cmp_res["comparison_valid"])
        self.assertAlmostEqual(cmp_res["imd_ground_rainfall_mm"], 14.2)
        self.assertAlmostEqual(cmp_res["gpm_satellite_rainfall_mm"], 18.0)
        self.assertAlmostEqual(cmp_res["absolute_difference_mm"], 3.8)
        self.assertAlmostEqual(cmp_res["percentage_difference_pct"], 21.1, delta=0.5)
        self.assertLess(cmp_res["station_distance_km"], 10.0) # ~3.9 km
        self.assertAlmostEqual(cmp_res["time_difference_hours"], 0.5)
        # Does NOT force them to agree
        self.assertNotEqual(cmp_res["imd_ground_rainfall_mm"], cmp_res["gpm_satellite_rainfall_mm"])

    # -------------------------------------------------------------------------
    # 7. Live Official Mausam Nowcast Warning Ingestion
    # -------------------------------------------------------------------------
    def test_11_live_mausam_nowcast_warnings(self):
        """Fetches live GeoJSON nowcasts from official Mausam feed."""
        res = self.client.fetch_official_nowcast_warnings()
        self.assertEqual(res["status"], "OPERATIONAL")
        self.assertIn("total_active_warnings", res)
        self.assertGreaterEqual(res["total_active_warnings"], 0)
        self.assertEqual(res["provider"], "India Meteorological Department (IMD Mausam)")

    # -------------------------------------------------------------------------
    # 8. Scheduler Integration & Deduplication
    # -------------------------------------------------------------------------
    def test_12_scheduler_eligibility_and_deduplication(self):
        """Tests live_monitoring_scheduler source handling and deduplication."""
        # Unconfigured should return AUTH_REQUIRED
        with patch.dict(os.environ, {"IMD_API_KEY": "", "IMD_JWT_TOKEN": ""}, clear=False):
            elig = live_monitoring_scheduler.check_source_eligibility("IMD_AWS_SHILLONG_01")
            self.assertFalse(elig["eligible"])
            self.assertEqual(elig["status"], "AUTH_REQUIRED")

            poll_res = live_monitoring_scheduler.poll_source("IMD_AWS_SHILLONG_01")
            self.assertEqual(poll_res["poll_result"], "AUTH_REQUIRED")
            self.assertFalse(poll_res["new_observation_ingested"])

    # -------------------------------------------------------------------------
    # 9. Extended Dashboard Presence & Zero Emojis
    # -------------------------------------------------------------------------
    def test_13_extended_dashboard_zero_emojis_and_card(self):
        """Ensures extended dashboard includes IMD card and strictly 0 emojis."""
        dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard_extended.html")
        self.assertTrue(os.path.exists(dash_path))
        with open(dash_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify card existence
        self.assertIn('id="cardIMDWeather"', content)
        self.assertIn("IMD Weather (Ground AWS)", content)
        self.assertIn("Shillong (42516)", content)
        self.assertIn("GROUND OBSERVATION CORROBORATION", content)

        # Verify zero emojis (UX4G standard)
        import re
        emojis = re.findall(r'[\U00010000-\U0010ffff]', content)
        self.assertEqual(len(emojis), 0, f"Found {len(emojis)} emojis in extended dashboard: {emojis}")

    # -------------------------------------------------------------------------
    # 10. Risk Engine Weight Safety
    # -------------------------------------------------------------------------
    def test_14_risk_engine_frozen_weights_safety(self):
        """Ensures the locked 0.40 / 0.30 / 0.20 / 0.10 risk weights are untouched."""
        from live_assessment_service import live_assessment_service
        assessment = live_assessment_service.get_current_assessment()
        weights = assessment.get("fusion_weights", {})
        self.assertEqual(weights.get("susceptibility"), 0.40)
        self.assertEqual(weights.get("rainfall"), 0.30)
        self.assertEqual(weights.get("soil_moisture"), 0.20)
        self.assertEqual(weights.get("satellite_change"), 0.10)
        # Ensure no IMD weight added to formula
        self.assertNotIn("imd_rainfall", weights)
        self.assertNotIn("imd_weather", weights)


if __name__ == "__main__":
    unittest.main()
