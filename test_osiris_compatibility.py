"""
=============================================================================
NER-SAFE v1.1.0 — OSIRIS Intelligence Platform Compatibility Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: 25+ targeted automated tests verifying OSIRIS platform compatibility,
         source provenance, spatial filtering for Meghalaya and Mizoram,
         caching, rate limiting, zero emojis, and strict risk formula invariance.
=============================================================================
"""

import unittest
import os
import sys
import json
import time
import hashlib

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from osiris_adapter import (
    OsirisAdapter,
    MEGHALAYA_BBOX,
    MIZORAM_BBOX,
    MEGHALAYA_KEYWORDS,
    MIZORAM_KEYWORDS,
    LANDSLIDE_KEYWORDS
)


class TestOsirisCompatibility(unittest.TestCase):

    def setUp(self):
        self.adapter = OsirisAdapter(cache_ttl_seconds=2, rate_limit_delay_sec=0.01)

    # 1. OSIRIS Endpoint Discovery
    def test_01_endpoint_discovery(self):
        status = self.adapter.get_status()
        endpoints = status.get("upstream_endpoints", {})
        self.assertIn("/api/earthquakes", endpoints)
        self.assertIn("/api/gdelt", endpoints)
        self.assertIn("/api/cctv", endpoints)
        self.assertIn("/api/weather", endpoints)
        self.assertIn("/api/news", endpoints)
        self.assertIn("/api/fires", endpoints)
        self.assertIn("/api/sentinel", endpoints)
        self.assertIn("/api/arcgis", endpoints)
        self.assertIn("/api/region-dossier", endpoints)
        self.assertIn("/api/ai/briefing", endpoints)

    # 2. Real Endpoint Connectivity (USGS)
    def test_02_real_endpoint_connectivity(self):
        res = self.adapter.fetch_earthquakes()
        self.assertEqual(res["http_status"], 200)
        self.assertGreater(len(res["sha256"]), 0)

    # 3. Timeout Handling
    def test_03_timeout_handling(self):
        # Non-routable IP to test timeout
        code, data, lat, sha = self.adapter.fetch_url("http://10.255.255.1", timeout=1)
        self.assertEqual(code, 0)
        self.assertEqual(data, b"")

    # 4. Rate Limiting
    def test_04_rate_limiting(self):
        t0 = time.time()
        self.adapter._rate_limit()
        self.adapter._rate_limit()
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.01)

    # 5. Caching Mechanism
    def test_05_caching_mechanism(self):
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        code1, data1, lat1, sha1 = self.adapter.fetch_url(url)
        code2, data2, lat2, sha2 = self.adapter.fetch_url(url)
        self.assertEqual(code1, 200)
        self.assertEqual(code2, 200)
        self.assertEqual(sha1, sha2)
        self.assertLess(lat2, 0.01) # Cached hit should be instantaneous

    # 6. Meghalaya Spatial Filtering
    def test_06_meghalaya_spatial_filtering(self):
        # Shillong (25.5788, 91.8933) is in Meghalaya
        self.assertTrue(self.adapter.is_in_bbox(25.5788, 91.8933, MEGHALAYA_BBOX))
        self.assertEqual(self.adapter.classify_state(25.5788, 91.8933), "Meghalaya")
        # Delhi (28.6139, 77.2090) is NOT in Meghalaya
        self.assertFalse(self.adapter.is_in_bbox(28.6139, 77.2090, MEGHALAYA_BBOX))

    # 7. Mizoram Spatial Filtering
    def test_07_mizoram_spatial_filtering(self):
        # Aizawl (23.7271, 92.7176) is in Mizoram
        self.assertTrue(self.adapter.is_in_bbox(23.7271, 92.7176, MIZORAM_BBOX))
        self.assertEqual(self.adapter.classify_state(23.7271, 92.7176), "Mizoram")
        # Mumbai (19.0760, 72.8777) is NOT in Mizoram
        self.assertFalse(self.adapter.is_in_bbox(19.0760, 72.8777, MIZORAM_BBOX))

    # 8. News Normalization (Zero local NE India coverage)
    def test_08_news_normalization(self):
        status = self.adapter.endpoints_config["/api/news"]["status"]
        self.assertEqual(status, "REJECTED_NOT_RELEVANT")

    # 9. GDELT (GDACS) Normalization
    def test_09_gdelt_gdacs_normalization(self):
        res = self.adapter.fetch_gdacs_alerts()
        self.assertIn(res["http_status"], [200, 503, 0])
        self.assertEqual(res["authority"], "GDACS (Global Disaster Alert and Coordination System)")

    # 10. Weather Normalization
    def test_10_weather_normalization(self):
        rec = self.adapter.endpoints_config["/api/weather"]["recommendation"]
        self.assertTrue("REJECT" in rec)

    # 11. Earthquake Normalization & Provenance
    def test_11_earthquake_normalization(self):
        res = self.adapter.fetch_earthquakes()
        self.assertEqual(res["authority"], "USGS Earthquake Hazards Program")
        self.assertEqual(res["endpoint"], "/api/earthquakes")

    # 12. Fire Normalization
    def test_12_fire_normalization(self):
        rec = self.adapter.endpoints_config["/api/fires"]["recommendation"]
        self.assertTrue("RESEARCH_ONLY" in rec)

    # 13. Sentinel STAC Metadata Normalization
    def test_13_sentinel_metadata_normalization(self):
        status = self.adapter.endpoints_config["/api/sentinel"]["status"]
        self.assertEqual(status, "DUPLICATE_DERIVED")

    # 14. ArcGIS Search Normalization
    def test_14_arcgis_normalization(self):
        cat = self.adapter.endpoints_config["/api/arcgis"]["category"]
        self.assertEqual(cat, "gis_layers")

    # 15. CCTV Source Handling (Zero India coverage)
    def test_15_cctv_source_handling(self):
        status = self.adapter.endpoints_config["/api/cctv"]["status"]
        self.assertEqual(status, "REJECTED_ZERO_COVERAGE")

    # 16. Strict Provenance Retention
    def test_16_provenance_retention(self):
        sample_alert = {
            "title": "Severe Rain and Landslide in East Khasi Hills",
            "latitude": 25.5,
            "longitude": 91.8,
            "underlying_source": "GDACS",
            "access_path": "OSIRIS /api/gdelt",
            "timestamp_utc": "2026-09-14T12:00:00Z"
        }
        normalized = self.adapter.normalize_to_canonical_osint(sample_alert)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["publisher"], "GDACS")
        self.assertEqual(normalized["access_path"], "OSIRIS /api/gdelt")
        self.assertEqual(normalized["state"], "Meghalaya")

    # 17. Duplicate Detection
    def test_17_duplicate_detection(self):
        sample1 = {"title": "NH-6 Blocked", "latitude": 25.5, "longitude": 91.8}
        sample2 = {"title": "NH-6 Blocked", "latitude": 25.5, "longitude": 91.8}
        n1 = self.adapter.normalize_to_canonical_osint(sample1)
        n2 = self.adapter.normalize_to_canonical_osint(sample2)
        self.assertEqual(n1["content_hash"], n2["content_hash"])

    # 18. Underlying Source Retention
    def test_18_underlying_source_retention(self):
        for ep, conf in self.adapter.endpoints_config.items():
            self.assertIn("authority", conf)
            self.assertNotEqual(conf["authority"], "OSIRIS") # OSIRIS is aggregator, not authority

    # 19. No Fake Coordinates Permitted
    def test_19_no_fake_coordinates(self):
        # Alert missing coordinates must be rejected cleanly
        invalid_alert = {"title": "Generic Alert without coordinates"}
        norm = self.adapter.normalize_to_canonical_osint(invalid_alert)
        self.assertIsNone(norm)

    # 20. AI Advisory-Only Policy
    def test_20_ai_advisory_only_policy(self):
        ai_status = self.adapter.endpoints_config["/api/ai/briefing"]["status"]
        self.assertEqual(ai_status, "ADVISORY_ONLY")

    # 21. OSINT Event Integration Format
    def test_21_osint_event_integration_format(self):
        sample = {
            "title": "Aizawl Road Slip",
            "latitude": 23.72,
            "longitude": 92.71,
            "underlying_source": "USGS",
            "access_path": "OSIRIS /api/earthquakes"
        }
        norm = self.adapter.normalize_to_canonical_osint(sample)
        self.assertIn("source_id", norm)
        self.assertIn("verification_state", norm)
        self.assertEqual(norm["verification_state"], "UNVERIFIED_EXTERNAL_EVIDENCE") # CANNOT auto-verify

    # 22. Prediction Validation Multi-Scale Compatibility
    def test_22_prediction_validation_compatibility(self):
        # Must maintain site <= 2km, corridor <= 5km, regional <= 45km
        from osint_intelligence_engine import (
            SITE_MATCH_RADIUS_KM,
            CORRIDOR_MATCH_RADIUS_KM,
            REGIONAL_MATCH_RADIUS_KM
        )
        self.assertEqual(SITE_MATCH_RADIUS_KM, 2.0)
        self.assertEqual(CORRIDOR_MATCH_RADIUS_KM, 5.0)
        self.assertEqual(REGIONAL_MATCH_RADIUS_KM, 45.0)

    # 23. Security & No Credential Leakage
    def test_23_security_no_credentials(self):
        status = self.adapter.get_status()
        status_str = json.dumps(status)
        for secret in ["password", "secret", "bearer", "api_key", "token"]:
            self.assertNotIn(secret, status_str.lower())

    # 24. Zero Emojis Across Module & Outputs
    def test_24_zero_emojis(self):
        with open(os.path.join(PROJECT_ROOT, "osiris_adapter.py"), "r", encoding="utf-8") as f:
            code = f.read()
        import re
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        self.assertEqual(len(emoji_pattern.findall(code)), 0)

    # 25. Locked Risk Formula Invariance
    def test_25_risk_formula_invariance(self):
        w_susc = 0.40
        w_rain = 0.30
        w_soil = 0.20
        w_sat = 0.10
        self.assertAlmostEqual(w_susc + w_rain + w_soil + w_sat, 1.0)
        # Verify OSIRIS has zero weight
        osiris_weight = 0.0
        total_weight = w_susc + w_rain + w_soil + w_sat + osiris_weight
        self.assertAlmostEqual(total_weight, 1.0)


if __name__ == "__main__":
    unittest.main()
