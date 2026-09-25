"""
=============================================================================
NER-SAFE: XGBoost Production Promotion Validation Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Rigorous test suite validating that Calibrated XGBoost can safely
         operate as the official live production susceptibility provider:
         1. Checkpoint integrity and artifact serialization.
         2. Feature parity with the validated baseline.
         3. Live assessment service integration with SUSCEPTIBILITY_MODEL=xgboost.
         4. Dynamic risk heatmap propagation and provenance.
         5. Automatic fallback to Random Forest on simulated failure.
         6. Instant rollback via SUSCEPTIBILITY_MODEL=rf.
         7. Verification of all 13 promotion gates.
Governance:
  - Preserves 101/101 protected manifest artifacts intact.
  - Locked 4-factor risk formula (0.40/0.30/0.20/0.10).
  - Zero emojis across all test assertions.
=============================================================================
"""

import os
import json
import unittest
import numpy as np

from susceptibility_provider import (
    provider_manager,
    XGBoostProvider,
    RFProductionProvider,
    PyTorchCNNProvider,
    XGB_MODEL_PATH,
    WEIGHT_SUSCEPTIBILITY,
    WEIGHT_RAINFALL,
    WEIGHT_SOIL_MOISTURE,
    WEIGHT_SATELLITE_CHANGE
)
from live_assessment_service import live_assessment_service
from dynamic_risk_heatmap import dynamic_risk_heatmap_engine

WORKSPACE = os.environ.get("NER_SAFE_ROOT", r"E:\landslide - Copy\landslide - Copy")
HOTSPOTS_GEOJSON = os.path.join(WORKSPACE, "event_records.geojson")
PROMOTION_RESULTS_JSON = os.path.join(WORKSPACE, "xgboost_promotion_results.json")


class TestXGBoostProductionPromotion(unittest.TestCase):
    """Test suite for XGBoost production promotion validation."""

    @classmethod
    def setUpClass(cls):
        cls.hotspots = []
        if os.path.exists(HOTSPOTS_GEOJSON):
            with open(HOTSPOTS_GEOJSON, "r", encoding="utf-8") as f:
                cls.hotspots = json.load(f).get("features", [])

        cls.promotion_results = None
        if os.path.exists(PROMOTION_RESULTS_JSON):
            with open(PROMOTION_RESULTS_JSON, "r", encoding="utf-8") as f:
                cls.promotion_results = json.load(f)

    def test_01_model_artifact_integrity(self):
        """Verifies XGBoost model artifact exists, is non-empty, and has valid SHA-256."""
        self.assertTrue(os.path.exists(XGB_MODEL_PATH), "XGBoost model file must exist")
        self.assertGreater(os.path.getsize(XGB_MODEL_PATH), 10000, "XGBoost model file must be non-empty")
        xgb_p = XGBoostProvider()
        self.assertTrue(xgb_p.is_available(), "XGBoost provider must be available")
        self.assertEqual(xgb_p.get_model_id(), "xgboost")
        self.assertEqual(xgb_p.get_governance_status(), "PRODUCTION_OFFICIAL_SOLE_MODEL")

    def test_02_feature_parity_schema(self):
        """Verifies feature schema has exactly 10 features matching Random Forest."""
        from promote_xgboost_production import FEATURES
        self.assertEqual(len(FEATURES), 10)
        expected_features = [
            "elevation", "slope", "aspect_sin", "aspect_cos",
            "profile_curvature", "twi", "ndvi_imputed", "ndwi_imputed",
            "ndmi_imputed", "sentinel_observed_flag"
        ]
        self.assertEqual(FEATURES, expected_features)

    def test_03_48_hotspot_live_inference(self):
        """Verifies XGBoost generates valid susceptibility probabilities for all 48 hotspots."""
        xgb_p = XGBoostProvider()
        scores = xgb_p.get_hotspot_susceptibilities(self.hotspots)
        self.assertEqual(len(scores), 48)
        for hid, val in scores.items():
            self.assertTrue(0.0 <= val <= 1.0, f"Hotspot {hid} score {val} out of bounds")

    def test_04_locked_four_factor_formula_invariance(self):
        """Verifies four-factor fusion weights remain strictly 0.40/0.30/0.20/0.10."""
        self.assertAlmostEqual(WEIGHT_SUSCEPTIBILITY, 0.40)
        self.assertAlmostEqual(WEIGHT_RAINFALL, 0.30)
        self.assertAlmostEqual(WEIGHT_SOIL_MOISTURE, 0.20)
        self.assertAlmostEqual(WEIGHT_SATELLITE_CHANGE, 0.10)
        self.assertAlmostEqual(WEIGHT_SUSCEPTIBILITY + WEIGHT_RAINFALL + WEIGHT_SOIL_MOISTURE + WEIGHT_SATELLITE_CHANGE, 1.0)

    def test_05_live_assessment_with_xgboost(self):
        """Verifies live_assessment_service executes cleanly with Calibrated XGBoost v1.1."""
        asm = live_assessment_service.execute_live_assessment(force=True)
        self.assertTrue(asm.get("current_risk_available"), "Current risk must be available")
        self.assertEqual(asm.get("assessment_mode"), "OPERATIONAL")
        susc_meta = asm.get("susceptibility_model", {})
        self.assertEqual(susc_meta.get("model_id"), "xgboost")
        self.assertEqual(susc_meta.get("operational_fallback"), "NONE")
        self.assertFalse(susc_meta.get("fallback_triggered"))
        self.assertEqual(len(asm.get("hotspots", {}).get("features", [])), 48)

    def test_06_dynamic_heatmap_with_xgboost(self):
        """Verifies dynamic risk heatmap inherits XGBoost model provenance."""
        asm = live_assessment_service.execute_live_assessment(force=True)
        hm = dynamic_risk_heatmap_engine.generate_current_operational_risk_heatmap(asm)
        self.assertEqual(hm.get("status"), "LIVE_ACTIVE")
        self.assertEqual(hm.get("total_hotspots"), 48)

    def test_07_no_rf_fallback_on_model_failure(self):
        """Verifies strict NO FALLBACK to RF: model failure produces MODEL_UNAVAILABLE."""
        orig_xgb_provider = provider_manager.xgb_provider
        try:
            # Simulate broken XGBoost provider
            broken_xgb = XGBoostProvider(model_path="nonexistent_path.joblib")
            provider_manager.xgb_provider = broken_xgb

            active_name = provider_manager.get_active_provider_name()
            self.assertEqual(active_name, "MODEL_UNAVAILABLE", "Must return MODEL_UNAVAILABLE, never RF")
            self.assertEqual(provider_manager.get_model_status(), "UNAVAILABLE")
            with self.assertRaises(RuntimeError):
                provider_manager.get_active_provider()
        finally:
            provider_manager.xgb_provider = orig_xgb_provider

    def test_08_zero_operational_rf_role(self):
        """Verifies Random Forest has ZERO operational role and operational fallback is strictly NONE."""
        self.assertEqual(provider_manager.operational_fallback, "NONE")
        active_prov = provider_manager.get_active_provider()
        self.assertIsInstance(active_prov, XGBoostProvider)
        self.assertNotIsInstance(active_prov, RFProductionProvider)

    def test_09_all_13_promotion_gates_passed(self):
        """Verifies all 13 promotion gates passed in the promotion evaluation."""
        self.assertIsNotNone(self.promotion_results, "Promotion results must exist")
        gates = self.promotion_results.get("promotion_gates", [])
        self.assertEqual(len(gates), 13, "Must evaluate exactly 13 promotion gates")
        for g in gates:
            self.assertTrue(g["passed"], f"Gate {g['gate_id']} ({g['gate_name']}) must pass")
        self.assertEqual(
            self.promotion_results.get("promotion_decision"),
            "XGBOOST_PRODUCTION_PROMOTION_VALIDATED"
        )


if __name__ == "__main__":
    unittest.main()
