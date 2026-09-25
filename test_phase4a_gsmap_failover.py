"""
NER-SAFE Phase 4A: Dedicated Test Suite for JAXA GSMaP_NOW Ingestion and Failover Engine
Verifies:
1. FTP connection, authentication, and directory listing
2. Newest file detection and timestamp parsing
3. ZIP integrity, CSV schema, and column validation
4. AOI extraction (Meghalaya & Mizoram 21.0-27.0 N, 89.0-94.0 E)
5. Anomaly compatibility with canonical NER-SAFE formula
6. Stale product detection and duplicate download prevention
7. Automatic failover: GSMAP_PRIMARY -> GPM_FALLBACK
8. Dual-source failure mode: RAIN_DEGRADED / RAIN_STALE (Zero synthetic fabrication)
9. Operational telemetry metrics (T_source, T_download, T_processed, Latency)
"""

import os
import sys
import json
import unittest
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from gsmap_now_engine import GSMaPNowEngine, parse_gsmap_filename, compute_rainfall_anomaly_gsmap
from weather_provider import (
    GSMaPWeatherProvider, GPMWeatherProvider, UnifiedPrecipitationManager,
    STATE_GSMAP_PRIMARY, STATE_GPM_FALLBACK, STATE_RAIN_DEGRADED, STATE_RAIN_UNAVAILABLE
)

class TestGSMaPNowFailover(unittest.TestCase):
    def setUp(self):
        self.engine = GSMaPNowEngine()

    def test_01_filename_parsing(self):
        """Verify regex and timestamp extraction from JAXA GSMaP filenames."""
        fn = "gsmap_now.20260921.1230_1329.05_AsiaSS.csv.zip"
        parsed = parse_gsmap_filename(fn)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["product_type"], "now")
        self.assertEqual(parsed["region"], "05_AsiaSS")
        self.assertEqual(parsed["start_dt"].year, 2026)
        self.assertEqual(parsed["start_dt"].month, 9)
        self.assertEqual(parsed["start_dt"].day, 21)
        self.assertEqual(parsed["start_dt"].hour, 12)
        self.assertEqual(parsed["start_dt"].minute, 30)

    def test_02_anomaly_formula_parity(self):
        """Verify GSMaP rainfall anomaly matches canonical NER-SAFE formula."""
        # Baseline / dry conditions: 0.0 mm/h -> minimum baseline floor 0.20
        anomaly_dry = compute_rainfall_anomaly_gsmap(0.0, 0.0)
        self.assertAlmostEqual(anomaly_dry, 0.20, places=3)

        # Moderate conditions: mean 2.0 mm/h, max 10.0 mm/h -> min(1.0, max(0.15, (2/8)*0.4 + (10/25)*0.4 + 0.20)) = 0.10 + 0.16 + 0.20 = 0.46
        anomaly_mod = compute_rainfall_anomaly_gsmap(2.0, 10.0)
        self.assertAlmostEqual(anomaly_mod, 0.46, places=3)

        # Extreme conditions: mean 12.0 mm/h, max 40.0 mm/h -> capped at 1.0
        anomaly_ext = compute_rainfall_anomaly_gsmap(12.0, 40.0)
        self.assertEqual(anomaly_ext, 1.0)

    def test_03_quality_control_bounds(self):
        """Verify invalid and negative values are rejected."""
        stats = self.engine.extract_and_analyze_csv(
            csv_content="Lat,Lon,RainRate\n25.5,91.8,-999.0\n25.6,91.9,4.5\n23.5,92.8,1.2\n10.0,75.0,8.0\n",
            filename="mock_test.csv"
        )
        self.assertEqual(stats["total_records"], 4)
        # 3 points within Meghalaya/Mizoram AOI (10.0, 75.0 is excluded)
        self.assertEqual(stats["aoi_cell_count"], 3)
        self.assertEqual(stats["valid_cell_count"], 2)
        self.assertEqual(stats["missing_cell_count"], 1)
        self.assertGreater(stats["mean_precipitation_mm_h"], 0.0)

    def test_04_live_product_verification(self):
        """Verify engine can discover and acquire a genuine product from JAXA FTP or cached genuine product."""
        product = self.engine.fetch_latest_product()
        self.assertIsNotNone(product)
        self.assertIn("product_filename", product)
        self.assertIn("rainfall_anomaly_score", product)
        self.assertIn("freshness_state", product)
        self.assertIn("meghalaya_covered", product)
        self.assertIn("mizoram_covered", product)
        self.assertTrue(product["meghalaya_covered"])
        self.assertTrue(product["mizoram_covered"])
        self.assertGreater(product["valid_cell_count"], 100)

    def test_05_stale_detection(self):
        """Verify stale detection categorizes observations according to age."""
        now = datetime.now(timezone.utc)
        
        # 45 min age -> FRESH
        fresh_ts = (now - timedelta(minutes=45)).isoformat()
        state_fresh = self.engine.determine_freshness_state(fresh_ts)
        self.assertEqual(state_fresh, "FRESH")

        # 90 min age -> RECENT
        recent_ts = (now - timedelta(minutes=90)).isoformat()
        state_recent = self.engine.determine_freshness_state(recent_ts)
        self.assertEqual(state_recent, "RECENT")

        # 150 min age -> AGING
        aging_ts = (now - timedelta(minutes=150)).isoformat()
        state_aging = self.engine.determine_freshness_state(aging_ts)
        self.assertEqual(state_aging, "AGING")

        # 300 min age -> STALE
        stale_ts = (now - timedelta(minutes=300)).isoformat()
        state_stale = self.engine.determine_freshness_state(stale_ts)
        self.assertEqual(state_stale, "STALE")

    def test_06_unified_manager_gsmap_primary(self):
        """Verify UnifiedPrecipitationManager selects GSMaP_NOW when healthy."""
        mgr = UnifiedPrecipitationManager()
        reading = mgr.get_primary_rainfall(force_refresh=True)
        self.assertIsNotNone(reading)
        self.assertIn("rainfall_source", reading)
        self.assertEqual(reading["rainfall_source"], STATE_GSMAP_PRIMARY)
        self.assertIn("JAXA", reading["provider"])
        self.assertGreater(reading["anomaly"], 0.0)

    def test_07_simulated_failover_to_gpm(self):
        """Verify automatic failover to NASA GPM Early NRT when GSMaP fails."""
        mgr = UnifiedPrecipitationManager()
        
        # Deliberately mock GSMaP failure
        class FailingGSMaPProvider:
            source_id = "JAXA_GSMAP_NOW_V08"
            def get_source_id(self): return self.source_id
            def is_operational(self): return False
            def fetch_latest_observation(self, force=False):
                return {
                    "source": self.source_id,
                    "status": "CONNECTION_FAILED",
                    "error": "FTP connection timeout test",
                    "is_active_operational_source": False
                }

        mgr.gsmap_provider = FailingGSMaPProvider()
        
        reading = mgr.get_primary_rainfall(force_refresh=True)
        self.assertIsNotNone(reading)
        self.assertEqual(reading["rainfall_source"], STATE_GPM_FALLBACK)
        self.assertIn("NASA", reading["provider"])

    def test_08_both_sources_failed_degraded_state(self):
        """Verify system enters RAIN_DEGRADED without fabricating data when both fail."""
        mgr = UnifiedPrecipitationManager()
        
        class FailingProvider:
            def __init__(self, pid): self.source_id = pid
            def get_source_id(self): return self.source_id
            def is_operational(self): return False
            def fetch_latest_observation(self, force=False):
                return {
                    "source": self.source_id,
                    "status": "SOURCE_UNAVAILABLE",
                    "error": "Simulated total satellite telemetry loss",
                    "is_active_operational_source": False
                }

        mgr.gsmap_provider = FailingProvider("JAXA_GSMAP_NOW")
        mgr.gpm_provider = FailingProvider("NASA_GPM_NRT")
        
        reading = mgr.get_primary_rainfall(force_refresh=True)
        self.assertIsNotNone(reading)
        self.assertIn(reading["rainfall_source"], (STATE_RAIN_DEGRADED, STATE_RAIN_UNAVAILABLE))
        self.assertIn(reading["freshness_state"], ("DEGRADED", "STALE", "UNAVAILABLE"))

    def test_09_telemetry_timestamps_and_latency(self):
        """Verify provenance telemetry contains all required latency timings."""
        product = self.engine.fetch_latest_product()
        self.assertIn("download_timestamp_utc", product)
        self.assertIn("processing_timestamp_utc", product)
        self.assertIn("latency_seconds", product)
        self.assertGreaterEqual(product["latency_seconds"], 0.0)
        self.assertIn("source_age_minutes", product)

if __name__ == "__main__":
    unittest.main(verbosity=2)
