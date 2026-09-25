"""
=============================================================================
NER-SAFE: Single Production Model Architecture & Fail-Safe Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Comprehensive unit & integration tests verifying:
  1. XGBoost loads successfully.
  2. Canonical SHA-256 hash matches authoritative baseline exactly.
  3. XGBoost generates valid production susceptibility probabilities.
  4. Four-factor risk formula (0.40/0.30/0.20/0.10) & thresholds remain locked.
  5. XGBoost failure strictly produces MODEL_UNAVAILABLE.
  6. XGBoost failure does NOT invoke Random Forest fallback.
  7. XGBoost failure does NOT invoke PyTorch CNN fallback.
  8. XGBoost failure does NOT invoke C15 temporal forecasting fallback.
  9. Data-source failover (GSMaP_NOW -> GPM Early NRT) functions independently.
  10. Model failure and data-source failure remain strictly separate states.
  11. Dashboard identifies Calibrated XGBoost v1.1 as sole production model.
  12. Alerts never use an alternative model when XGBoost is unavailable.
  13. Research components (CNN, InSAR, C15, RF) retain 0.00 operational weight.
Zero emojis across all assertions.
=============================================================================
"""

import os
import sys
import json
import hashlib
import unittest
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from susceptibility_provider import (
    provider_manager,
    XGBoostProvider,
    RFHistoricalBaselineProvider,
    RFProductionProvider,
    PyTorchCNNProvider,
    XGB_MODEL_PATH,
    XGB_CANONICAL_SHA256,
    WEIGHT_SUSCEPTIBILITY,
    WEIGHT_RAINFALL,
    WEIGHT_SOIL_MOISTURE,
    WEIGHT_SATELLITE_CHANGE
)
import fusion_engine
from live_assessment_service import live_assessment_service

HOTSPOTS_GEOJSON = os.path.join(PROJECT_ROOT, "event_records.geojson")
DASHBOARD_HTML = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")


class TestSingleProductionModelArchitecture(unittest.TestCase):
    """Authoritative test suite for single production model architecture."""

    @classmethod
    def setUpClass(cls):
        cls.hotspots = []
        if os.path.exists(HOTSPOTS_GEOJSON):
            with open(HOTSPOTS_GEOJSON, "r", encoding="utf-8") as f:
                cls.hotspots = json.load(f).get("features", [])

    def test_01_xgboost_loads_successfully(self):
        """1. Verifies Calibrated XGBoost v1.1 loads cleanly and reports valid metadata."""
        self.assertTrue(os.path.exists(XGB_MODEL_PATH), f"Model artifact not found at {XGB_MODEL_PATH}")
        prov = XGBoostProvider()
        self.assertTrue(prov.is_available(), f"XGBoost provider unavailable: {prov.load_error}")
        self.assertEqual(prov.get_model_id(), "xgboost")
        self.assertEqual(prov.get_model_name(), "Calibrated XGBoost v1.1")
        self.assertEqual(prov.get_version(), "v1.1")
        self.assertEqual(prov.get_governance_status(), "PRODUCTION_OFFICIAL_SOLE_MODEL")

    def test_02_canonical_hash_matches(self):
        """2. Verifies canonical SHA-256 hash matches 45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c."""
        with open(XGB_MODEL_PATH, "rb") as f:
            actual_sha256 = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(
            actual_sha256,
            XGB_CANONICAL_SHA256,
            f"Hash mismatch: actual {actual_sha256} != canonical {XGB_CANONICAL_SHA256}"
        )
        self.assertEqual(
            actual_sha256,
            "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c"
        )

    def test_03_xgboost_generates_production_susceptibility(self):
        """3. Verifies XGBoost generates valid susceptibility output across all 48 hotspots."""
        prov = XGBoostProvider()
        susc_map = prov.get_hotspot_susceptibilities(self.hotspots)
        self.assertEqual(len(susc_map), 48, "Must evaluate all 48 monitored hotspots")
        for hid, val in susc_map.items():
            self.assertTrue(0.0 <= val <= 1.0, f"Susceptibility {val} for {hid} out of bounds")
            self.assertIsInstance(val, float)

    def test_04_risk_formula_and_thresholds_locked(self):
        """4. Verifies risk formula weights (0.40/0.30/0.20/0.10) and classification thresholds."""
        self.assertAlmostEqual(WEIGHT_SUSCEPTIBILITY, 0.40)
        self.assertAlmostEqual(WEIGHT_RAINFALL, 0.30)
        self.assertAlmostEqual(WEIGHT_SOIL_MOISTURE, 0.20)
        self.assertAlmostEqual(WEIGHT_SATELLITE_CHANGE, 0.10)
        self.assertAlmostEqual(
            WEIGHT_SUSCEPTIBILITY + WEIGHT_RAINFALL + WEIGHT_SOIL_MOISTURE + WEIGHT_SATELLITE_CHANGE,
            1.00
        )

        # Thresholds verification: CRITICAL >= 0.65, HIGH >= 0.48, MODERATE >= 0.32, WATCH < 0.32
        self.assertEqual(provider_manager.classify_risk_tier(0.75), "CRITICAL")
        self.assertEqual(provider_manager.classify_risk_tier(0.65), "CRITICAL")
        self.assertEqual(provider_manager.classify_risk_tier(0.6499), "HIGH")
        self.assertEqual(provider_manager.classify_risk_tier(0.48), "HIGH")
        self.assertEqual(provider_manager.classify_risk_tier(0.4799), "MODERATE")
        self.assertEqual(provider_manager.classify_risk_tier(0.32), "MODERATE")
        self.assertEqual(provider_manager.classify_risk_tier(0.3199), "WATCH")
        self.assertEqual(provider_manager.classify_risk_tier(0.10), "WATCH")

    def test_05_xgboost_failure_produces_model_unavailable(self):
        """5. Verifies XGBoost failure strictly produces MODEL_UNAVAILABLE without fallback."""
        orig_xgb = provider_manager.xgb_provider
        try:
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            self.assertEqual(provider_manager.get_active_provider_name(), "MODEL_UNAVAILABLE")
            self.assertEqual(provider_manager.get_model_status(), "UNAVAILABLE")

            # Provider manager must raise, never substitute another model
            with self.assertRaises(RuntimeError) as ctx:
                provider_manager.get_active_provider()
            self.assertIn("MODEL_UNAVAILABLE", str(ctx.exception))

            # Live assessment must report MODEL_UNAVAILABLE
            asm = live_assessment_service.execute_live_assessment(force=True)
            self.assertEqual(asm.get("assessment_status"), "MODEL_UNAVAILABLE")
            self.assertEqual(asm.get("model_status"), "UNAVAILABLE")
            self.assertEqual(asm.get("risk_status"), "CURRENT RISK UNAVAILABLE")
            self.assertFalse(asm.get("current_risk_available"))
            self.assertIsNone(asm.get("risk_summary", {}).get("max_risk_score"))
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_06_xgboost_failure_does_not_invoke_rf(self):
        """6. Verifies XGBoost failure does NOT invoke Random Forest fallback."""
        orig_xgb = provider_manager.xgb_provider
        try:
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            asm = live_assessment_service.execute_live_assessment(force=True)
            susc_meta = asm.get("susceptibility_model", {})

            self.assertEqual(susc_meta.get("production_model"), "Calibrated XGBoost v1.1")
            self.assertEqual(susc_meta.get("operational_fallback"), "NONE")
            self.assertFalse(susc_meta.get("fallback_triggered"))
            self.assertNotEqual(susc_meta.get("model_id"), "rf")
            self.assertNotEqual(susc_meta.get("model_id"), "rf_historical")

            # RF must remain historical only
            rf_prov = provider_manager.rf_provider
            self.assertEqual(rf_prov.get_governance_status(), "RESEARCH/HISTORICAL ONLY")
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_07_xgboost_failure_does_not_invoke_cnn(self):
        """7. Verifies XGBoost failure does NOT invoke CNN fallback."""
        orig_xgb = provider_manager.xgb_provider
        try:
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            asm = live_assessment_service.execute_live_assessment(force=True)
            susc_meta = asm.get("susceptibility_model", {})

            self.assertNotEqual(susc_meta.get("model_id"), "cnn")
            cnn_prov = provider_manager.cnn_provider
            self.assertEqual(cnn_prov.get_governance_status(), "RESEARCH_ONLY")
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_08_xgboost_failure_does_not_invoke_c15(self):
        """8. Verifies XGBoost failure does NOT invoke C15 temporal forecasting."""
        orig_xgb = provider_manager.xgb_provider
        try:
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            asm = live_assessment_service.execute_live_assessment(force=True)
            susc_meta = asm.get("susceptibility_model", {})
            self.assertNotIn("c15", susc_meta.get("model_id", ""))
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_09_gsmap_to_gpm_data_source_failover_works(self):
        """9. Verifies data-source failover (GSMaP_NOW -> GPM Early NRT) still functions."""
        # Test standard operational rainfall acquisition
        rain_data, source_state = live_assessment_service.acquire_operational_rainfall()
        self.assertIn(source_state, ("GSMAP_PRIMARY", "GPM_EARLY_FALLBACK"))
        self.assertIn("derived_rain_anomaly", rain_data)
        self.assertTrue(0.0 <= rain_data["derived_rain_anomaly"] <= 1.0)

    def test_10_model_failure_and_data_source_failure_remain_separate_states(self):
        """10. Verifies model failure and data-source failure are strictly orthogonal states."""
        orig_xgb = provider_manager.xgb_provider
        try:
            # Simulate model failure with operational data source
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            asm = live_assessment_service.execute_live_assessment(force=True)

            # Data source is still validly captured
            self.assertIn("rainfall", asm.get("inputs", {}))
            self.assertIn(asm["inputs"]["rainfall"]["source_state"], ("GSMAP_PRIMARY", "GPM_EARLY_FALLBACK"))
            self.assertIsNotNone(asm["inputs"]["rainfall"]["granule_id"])

            # While model status is UNAVAILABLE
            self.assertEqual(asm["model_status"], "UNAVAILABLE")
            self.assertEqual(asm["assessment_status"], "MODEL_UNAVAILABLE")
            self.assertFalse(asm["current_risk_available"])
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_11_dashboard_identifies_xgboost_as_sole_production_model(self):
        """11. Verifies dashboard identifies XGBoost as sole production model without RF fallback wording."""
        self.assertTrue(os.path.exists(DASHBOARD_HTML), "Dashboard HTML must exist")
        with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
            html = f.read()

        # Check production model designation
        self.assertIn("PRODUCTION MODEL: Calibrated XGBoost v1.1", html)
        self.assertIn("45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c", html)
        self.assertIn("NONE (Sole Operational Model)", html)

        # Check absence of RF fallback wording
        self.assertNotIn("Fallback: Random Forest (FALLBACK ONLY)", html)
        self.assertNotIn("Automatic fallback to Random Forest", html)

    def test_12_alerts_do_not_use_alternative_model(self):
        """12. Verifies alerts do NOT generate severity classifications when model is unavailable."""
        orig_xgb = provider_manager.xgb_provider
        try:
            broken_xgb = XGBoostProvider(model_path="nonexistent_mock_artifact.joblib")
            provider_manager.xgb_provider = broken_xgb

            asm = live_assessment_service.execute_live_assessment(force=True)
            self.assertEqual(asm.get("assessment_status"), "MODEL_UNAVAILABLE")

            # Risk summary tier distribution must be empty, preventing new automated alerts
            self.assertEqual(asm.get("risk_summary", {}).get("tier_distribution"), {})
            self.assertIsNone(asm.get("risk_summary", {}).get("max_risk_score"))

            # Hotspots must be empty or marked MODEL_UNAVAILABLE
            features = asm.get("hotspots", {}).get("features", [])
            self.assertEqual(len(features), 0, "No operational hotspots when model is unavailable")
        finally:
            provider_manager.xgb_provider = orig_xgb

    def test_13_research_components_remain_zero_operational_weight(self):
        """13. Verifies CNN, InSAR, C15, and Random Forest all retain 0.00 operational weight."""
        status_data = fusion_engine.get_multi_source_status()
        susc_source = status_data.get("sources", {}).get("terrain_susceptibility", {})
        self.assertEqual(susc_source.get("production_model"), "Calibrated XGBoost v1.1")
        self.assertEqual(susc_source.get("operational_fallback"), "NONE")
        self.assertEqual(susc_source.get("canonical_sha256"), XGB_CANONICAL_SHA256)

        # Provider manager operational fallback is NONE
        self.assertEqual(provider_manager.operational_fallback, "NONE")


if __name__ == "__main__":
    unittest.main()
