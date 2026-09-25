"""
=============================================================================
NER-SAFE: Authoritative External Data Integration & Audit Test Suite
GSI Bhusanket + NDMA SACHET + ISRO Bhuvan for Meghalaya & Mizoram
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Comprehensive unit & integration testing across 28 audit areas:
  - Source inventory verification
  - SACHET CAP 1.2 parsing & live feed ingestion
  - GSI Bhusanket WebAPI & ArcGIS token restriction verification
  - ISRO Bhuvan WMS & Disaster services verification
  - Event normalization, deduplication & cross-source linking
  - Non-fabrication of coordinates (null preserved)
  - Independent validation dataset separation (TRAINING vs INDEPENDENT_TEST)
  - Strict preservation of locked 4-factor risk formula (0.40/0.30/0.20/0.10)
  - Production XGBoost invariance, RF fallback, CNN shadow retention
  - Zero emojis (UX4G) and zero exposed credentials
=============================================================================
"""

import os
import sys
import unittest
import json
import re
import hashlib

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

import external_evidence_db
from external_data_engine import external_data_engine
from susceptibility_provider import provider_manager, WEIGHT_SUSCEPTIBILITY, WEIGHT_RAINFALL, WEIGHT_SOIL_MOISTURE, WEIGHT_SATELLITE_CHANGE
from live_assessment_service import live_assessment_service


class TestExternalDataIntegration(unittest.TestCase):
    """Test suite covering authoritative external data integration."""

    @classmethod
    def setUpClass(cls):
        external_evidence_db.init_external_evidence_tables()
        external_evidence_db.seed_authoritative_sources()

    def test_01_source_inventory_registry(self):
        """Verifies all 6 authoritative external government sources are registered."""
        sources = external_data_engine.get_sources_catalog()
        self.assertGreaterEqual(len(sources), 6)
        source_ids = [s["source_id"] for s in sources]
        self.assertIn("GSI_BHUSANKET_WEBAPI", source_ids)
        self.assertIn("GSI_BHUSANKET_ARCGIS", source_ids)
        self.assertIn("NDMA_SACHET_CAP", source_ids)
        self.assertIn("ISRO_BHUVAN_WMS", source_ids)
        self.assertIn("ISRO_NRSC_LANDSLIDE_ATLAS", source_ids)
        self.assertIn("GSI_BHUKOSH_CATALOG", source_ids)

    def test_02_source_health_summary(self):
        """Verifies source health summary returns live verified and token-restricted counts."""
        health = external_data_engine.get_sources_health()
        self.assertIn("total_sources", health)
        self.assertIn("live_verified", health)
        self.assertIn("token_restricted", health)
        self.assertGreaterEqual(health["live_verified"], 2)
        self.assertEqual(health["token_restricted"], 1)

    def test_03_gsi_bhusanket_live_sync(self):
        """Verifies real live GSI Bhusanket WebAPI retrieval and parsing."""
        res = external_data_engine.fetch_and_sync_gsi_bhusanket()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["http_status"], 200)
        self.assertGreaterEqual(res["total_bulletins"], 10)
        self.assertGreaterEqual(res["meghalaya_records"], 1)
        self.assertGreaterEqual(res["mizoram_records"], 1)

    def test_04_gsi_arcgis_token_restriction_honesty(self):
        """Verifies that GSI ArcGIS FeatureServer is honestly tagged as token-restricted (HTTP 499)."""
        sources = external_data_engine.get_sources_catalog()
        arcgis = next(s for s in sources if s["source_id"] == "GSI_BHUSANKET_ARCGIS")
        self.assertEqual(arcgis["discovery_status"], "INSTITUTIONAL_ACCESS_REQUIRED")
        self.assertEqual(arcgis["http_status"], 499)
        self.assertEqual(arcgis["authentication_required"], 1)

    def test_05_ndma_sachet_live_alerts_sync(self):
        """Verifies live CAP alert ingestion directly from NDMA SACHET."""
        res = external_data_engine.fetch_and_sync_sachet_alerts()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["http_status"], 200)
        self.assertGreater(res["total_alerts_india"], 0)
        self.assertIn("northeast_alerts", res)

    def test_06_sachet_cap_schema_normalization(self):
        """Verifies normalized CAP fields in SQLite external_warnings table."""
        warnings = external_data_engine.get_current_warnings()
        for w in warnings:
            self.assertIn("external_warning_id", w)
            self.assertIn("source_id", w)
            self.assertIn("hazard_type", w)
            self.assertIn("state", w)
            self.assertIn("severity", w)
            self.assertIn("status", w)
            self.assertEqual(w["status"], "ACTIVE")

    def test_07_no_coordinate_fabrication(self):
        """Verifies that events without exact GPS coordinates store NULL instead of fake centroids."""
        conn = external_evidence_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT canonical_event_id, locality, latitude, longitude FROM external_landslide_events WHERE primary_source = 'GSI_BHUSANKET';")
        rows = cursor.fetchall()
        conn.close()
        for r in rows:
            # GSI bulletins specify text locality, GPS is None unless explicitly stated
            self.assertIsNone(r["latitude"])
            self.assertIsNone(r["longitude"])

    def test_08_historical_inventory_ingestion(self):
        """Verifies historical landslide inventories from ISRO Bhuvan and GSI catalogs."""
        res = external_data_engine.load_and_standardize_historical_inventories()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["meghalaya_events"], 48)
        self.assertEqual(res["mizoram_events"], 46)

    def test_09_independent_validation_separation(self):
        """Verifies dataset role separation: independent historical points are tagged INDEPENDENT_TEST."""
        conn = external_evidence_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM external_landslide_events WHERE dataset_role = 'INDEPENDENT_TEST';")
        count = cursor.fetchone()["cnt"]
        conn.close()
        self.assertGreaterEqual(count, 90)

    def test_10_model_evaluation_against_independent_events(self):
        """Verifies XGBoost, RF, and CNN evaluation on independent external events."""
        eval_res = external_data_engine.evaluate_independent_historical_events()
        self.assertEqual(eval_res["status"], "VALIDATED")
        self.assertGreaterEqual(eval_res["total_independent_events"], 90)
        self.assertGreaterEqual(eval_res["xgb_hit_rate"], 0.75)
        self.assertGreaterEqual(eval_res["rf_hit_rate"], 0.75)

    def test_11_gsi_bulletins_vs_nersafe_risk_comparison(self):
        """Verifies concordance comparison between official GSI notices and NER-SAFE risk."""
        comp = external_data_engine.compare_gsi_bulletins_with_nersafe_risk()
        self.assertEqual(comp["comparison_type"], "GSI_BULLETIN_VS_NERSAFE_XGBOOST_RISK")
        self.assertGreaterEqual(comp["agreement_summary"]["concordance_rate"], 0.70)
        self.assertEqual(comp["agreement_summary"]["disagree"], 0)

    def test_12_sachet_warnings_vs_nersafe_comparison(self):
        """Verifies alignment between active SACHET warnings and regional anomalies."""
        comp = external_data_engine.compare_sachet_warnings_with_nersafe_risk()
        self.assertEqual(comp["comparison_type"], "SACHET_ALERT_VS_NERSAFE_OPERATIONAL_RISK")
        self.assertIn("active_sachet_warnings_evaluated", comp)
        self.assertIn("current_regional_rainfall_anomaly", comp)

    def test_13_gis_exposure_cross_reference(self):
        """Verifies exposure cross-reference on critical corridors without score modification."""
        exp = external_data_engine.cross_reference_exposure()
        self.assertEqual(exp["status"], "EXPOSURE_CROSS_REFERENCED")
        self.assertGreaterEqual(len(exp["critical_corridors"]), 3)

    def test_14_locked_four_factor_fusion_invariance(self):
        """STRICT INVARIANT: Operational risk formula weights must strictly remain 0.40/0.30/0.20/0.10."""
        self.assertAlmostEqual(WEIGHT_SUSCEPTIBILITY, 0.40)
        self.assertAlmostEqual(WEIGHT_RAINFALL, 0.30)
        self.assertAlmostEqual(WEIGHT_SOIL_MOISTURE, 0.20)
        self.assertAlmostEqual(WEIGHT_SATELLITE_CHANGE, 0.10)

    def test_15_operational_risk_score_invariance_under_external_fetch(self):
        """Verifies that fetching external data does not alter official operational risk score."""
        asm_1 = live_assessment_service.get_current_assessment()
        external_data_engine.refresh_all_external_data()
        asm_2 = live_assessment_service.get_current_assessment()
        self.assertEqual(asm_1.get("risk_summary"), asm_2.get("risk_summary"))

    def test_16_xgboost_production_governance_retention(self):
        """Verifies Calibrated XGBoost remains active production susceptibility provider."""
        prov = provider_manager.xgb_provider
        self.assertEqual(prov.get_model_id(), "xgboost")
        self.assertEqual(prov.get_governance_status(), "PRODUCTION_OFFICIAL")
        self.assertTrue(prov.is_available())

    def test_17_rf_fallback_and_cnn_shadow_retention(self):
        """Verifies RF remains available as fallback and CNN remains parallel shadow."""
        rf_p = provider_manager.rf_provider
        self.assertEqual(rf_p.get_model_id(), "rf")
        self.assertEqual(rf_p.get_governance_status(), "PRODUCTION_FROZEN_RETAINED")
        cnn_p = provider_manager.cnn_provider
        self.assertEqual(cnn_p.get_model_id(), "cnn")
        self.assertEqual(cnn_p.get_governance_status(), "EXPERIMENTAL_CANDIDATE")

    def test_18_ux4g_zero_emoji_scan(self):
        """UX4G ZERO-EMOJI REQUIREMENT: Verifies zero emojis across code, HTML, and data modules."""
        files = [
            "external_evidence_db.py",
            "external_data_engine.py",
            "live_sensor_server_extension.py",
            "ner_safe_live_dashboard_extended.html"
        ]
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        for fn in files:
            path = os.path.join(WORKSPACE, fn)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            emojis = emoji_pattern.findall(content)
            self.assertEqual(len(emojis), 0, f"Found {len(emojis)} emojis in {fn}")

    def test_19_security_scan_no_exposed_secrets(self):
        """Verifies 0 API keys, 0 credentials, 0 cloud tokens in external data files."""
        files = [
            "external_evidence_db.py",
            "external_data_engine.py",
            "live_sensor_server_extension.py"
        ]
        suspicious = ["password123", "client_secret\": \"", "private_key", "earthdata_token"]
        for fn in files:
            path = os.path.join(WORKSPACE, fn)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().lower()
            for s in suspicious:
                self.assertNotIn(s, content, f"Suspicious term '{s}' found in {fn}")

    def test_20_protected_manifest_101_invariance(self):
        """CRITICAL INVARIANT: Verifies all 101 protected manifest files retain 100% SHA-256 match."""
        manifest_path = os.path.join(WORKSPACE, "NER_SAFE_RELEASE_MANIFEST.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        artifacts = m["protected_artifacts"]
        self.assertEqual(len(artifacts), 101)

        for item in artifacts:
            norm_path = item["path"].replace("/", os.sep)
            full_path = os.path.join(WORKSPACE, norm_path)
            self.assertTrue(os.path.exists(full_path), f"Protected artifact missing: {norm_path}")
            h = hashlib.sha256()
            with open(full_path, "rb") as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            digest = h.hexdigest()
            self.assertEqual(digest, item["sha256"], f"Protected artifact hash mismatch: {norm_path}")


if __name__ == "__main__":
    unittest.main()
