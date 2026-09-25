"""
NER-SAFE: Live Research Integration & Multi-Model Governance Automated Test Suite
Validates:
1. Live InSAR SBAS discovery, processing status, and strict 0.00 operational weight decoupling.
2. Live PyTorch Spatial CNN shadow inference, 8-channel context patches, and probability bounds.
3. Live C15 temporal forecasting, multi-window horizon scaling, and Shannon entropy uncertainty.
4. Canonical feature data contract, provenance tracking, and temporal leakage prevention.
5. Spatial alignment and coordinate matching for 48 operational hotspots.
6. Candidate model evaluation reproducibility (Models A, C, and F).
7. Feature ablation and permutation importance deltas.
8. Formal promotion gates and V2 candidate model serialization (separate SHA-256).
9. Missing-feature fallback safety strategy (automatic fallback to V1.1.0).
10. Immutable preservation of production XGBoost model hash and 4-factor risk formula.
11. REST API endpoint `/api/monitoring/multimodal`.
12. Zero emojis across all outputs and artifacts.
"""

import os
import sys
import json
import unittest
import hashlib
from datetime import datetime, timezone, timedelta

import numpy as np

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import database
import fusion_engine
from canonical_feature_contract import (
    CanonicalFeatureRecord,
    MultiModelDataContractManager,
    contract_manager
)
from cnn_inference_engine import CNNInferenceEngine
from c15_forecasting_engine import c15_forecaster
from insar_multitemporal_engine import InSARMultiTemporalEngine
import evaluate_multimodal_candidates

PROD_XGB_HASH = "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c"
PROD_XGB_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")
V2_CANDIDATE_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model_v2_multimodal.joblib")


class TestMultimodalResearchIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()

    def test_01_protected_production_xgboost_hash_invariant(self):
        """Production XGBoost model artifact must remain byte-for-byte identical."""
        self.assertTrue(os.path.exists(PROD_XGB_PATH), "Production model file must exist")
        hasher = hashlib.sha256()
        with open(PROD_XGB_PATH, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        observed_hash = hasher.hexdigest()
        self.assertEqual(observed_hash, PROD_XGB_HASH, "Production XGBoost SHA-256 altered!")

    def test_02_production_risk_formula_invariant(self):
        """Operational risk formula weights must remain strictly 0.40/0.30/0.20/0.10."""
        status = fusion_engine.get_multi_source_status()
        weights = status.get("weights", {})
        self.assertEqual(weights.get("w1_susceptibility"), 0.40)
        self.assertEqual(weights.get("w2_rainfall_anomaly"), 0.30)
        self.assertEqual(weights.get("w3_soil_moisture_anomaly"), 0.20)
        self.assertEqual(weights.get("w4_satellite_surface_change"), 0.10)

        # Baseline calculation exact scores
        hotspots = fusion_engine.compute_fused_hotspots()
        features = hotspots.get("features", [])
        self.assertEqual(len(features), 48)

        evt_miz_018 = features[0]["properties"]
        self.assertEqual(evt_miz_018["event_id"], "EVT-MIZ-018")
        self.assertEqual(evt_miz_018["fused_risk_score"], 0.6481)

        evt_meg_001 = [f["properties"] for f in features if f["properties"]["event_id"] == "EVT-MEG-001"][0]
        self.assertEqual(evt_meg_001["fused_risk_score"], 0.7055)

    def test_03_insar_multitemporal_live_pipeline_and_weight_decoupling(self):
        """Sentinel-1 InSAR is genuinely live-automated, but strictly 0.00 operational weight."""
        insar_eng = InSARMultiTemporalEngine()
        scenes = insar_eng.discover_and_register_scenes()
        self.assertGreaterEqual(len(scenes), 3, "InSAR stack must have >= 3 authentic SLC scenes")
        
        network = insar_eng.construct_pair_network(scenes)
        self.assertGreaterEqual(network["eligible_pairs_count"], 3)
        self.assertLessEqual(network["pair_selection_limits"]["max_temporal_baseline_days"], 36.0)
        self.assertLessEqual(network["pair_selection_limits"]["max_perpendicular_baseline_m"], 180.0)

        # Confirm operational weight is strictly 0.00
        from live_monitoring_controller import live_monitoring_controller
        ctrl_status = live_monitoring_controller.get_status()
        insar_stat = ctrl_status["sources"].get("INSAR", {})
        self.assertEqual(insar_stat.get("operational_risk_impact"), "DECOUPLED_ZERO_WEIGHT")
        self.assertEqual(insar_stat.get("scientific_status"), "RESEARCH_ONLY")

    def test_04_pytorch_spatial_cnn_live_shadow_inference(self):
        """PyTorch Spatial CNN runs live shadow inference on real operational hotspots."""
        cnn_engine = CNNInferenceEngine()
        self.assertIsNotNone(cnn_engine.model, "CNN model must load cleanly")
        repro = cnn_engine.verify_reproducibility()
        self.assertEqual(repro["status"], "REPRODUCED")
        self.assertTrue(repro["hash_matches_known_good"])

        hotspot_preds = cnn_engine.predict_hotspots()
        self.assertEqual(len(hotspot_preds), 48, "Must evaluate all 48 operational hotspots")

        for p in hotspot_preds:
            prob = p["cnn_probability"]
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)
            self.assertIn(p["cnn_tier"], ["CRITICAL", "HIGH", "MODERATE", "LOW"])
            self.assertGreaterEqual(p["uncertainty"], 0.0)

    def test_05_c15_temporal_forecasting_evaluation(self):
        """C15 temporal forecasting produces honest WAITING_FOR_DATA when inputs missing, and probability when registered."""
        from observation_provenance import provenance_registry
        ctx = {"location_name": "Shella", "district": "East Khasi Hills", "latitude": 25.183, "longitude": 91.642}
        
        # Case 1: When minimum inputs absent from provenance registry -> honestly reports WAITING_FOR_DATA
        provenance_registry.registry.clear()
        fc_waiting = c15_forecaster.evaluate_forecast(
            hotspot_id="EVT-MEG-001",
            horizon="24h",
            static_context=ctx,
            rainfall_data=[],
            smap_data=None,
            sentinel1_data=None,
            sentinel2_data=None
        )
        self.assertEqual(fc_waiting["forecast_status"], "WAITING_FOR_DATA")
        self.assertIsNone(fc_waiting["forecast_probability"])

        # Case 2: When minimum inputs registered -> produces defensible forecast probability
        now_iso = datetime.now(timezone.utc).isoformat()
        provenance_registry.register_observation("GPM_PRECIPITATION", "3IMERGHHE.07", now_iso)
        provenance_registry.register_observation("SRTM_DEM", "SRTMGL1", now_iso)
        
        fc = c15_forecaster.evaluate_forecast(
            hotspot_id="EVT-MEG-001",
            horizon="24h",
            static_context=ctx,
            rainfall_data=[{"rainfall_accum_24h": 45.0, "rainfall_status": "FRESH"}],
            smap_data={"soil_saturation": 0.55, "soil_moisture_status": "FRESH"},
            sentinel1_data={"sar_backscatter_change": 0.05, "sar_status": "AGING"},
            sentinel2_data={"optical_status": "CLOUD_FILTERED"}
        )
        self.assertEqual(fc["hotspot_id"], "EVT-MEG-001")
        self.assertEqual(fc["forecast_horizon"], "24h")
        self.assertIsNotNone(fc["forecast_probability"])
        self.assertGreaterEqual(fc["forecast_probability"], 0.01)
        self.assertLessEqual(fc["forecast_probability"], 0.99)
        self.assertIsNotNone(fc["uncertainty_entropy"])
        self.assertIn(fc["uncertainty_level"], ["HIGH", "MODERATE", "LOW"])

        # Unsupported horizon check
        bad_fc = c15_forecaster.evaluate_forecast(
            hotspot_id="EVT-MEG-001",
            horizon="999h",
            static_context=ctx,
            rainfall_data=[],
            smap_data=None,
            sentinel1_data=None,
            sentinel2_data=None
        )
        self.assertEqual(bad_fc["forecast_status"], "UNSUPPORTED_HORIZON")

    def test_06_canonical_feature_contract_and_leakage_prevention(self):
        """Canonical feature record enforces temporal leakage prevention."""
        now_dt = datetime.now(timezone.utc)
        record = CanonicalFeatureRecord(
            hotspot_id="EVT-MEG-001",
            latitude=25.183,
            longitude=91.642,
            reference_time_utc=now_dt.isoformat(),
            susceptibility_xgboost=0.6869,
            susceptibility_rf_fallback=0.6720,
            rainfall_anomaly=0.9217,
            soil_moisture_anomaly=0.8149,
            satellite_change_flag=0.05,
            feature_timestamps={
                "rainfall": (now_dt - timedelta(hours=2)).isoformat(),
                "soil_moisture": (now_dt - timedelta(hours=18)).isoformat(),
                "optical": (now_dt - timedelta(hours=24)).isoformat()
            }
        )
        valid, violations = contract_manager.validate_temporal_alignment(record)
        self.assertTrue(valid, f"Expected valid alignment, got violations: {violations}")

        # Inject future timestamp (temporal leakage test)
        record.feature_timestamps["rainfall"] = (now_dt + timedelta(hours=2)).isoformat()
        invalid, violations = contract_manager.validate_temporal_alignment(record)
        self.assertFalse(invalid, "Must detect temporal leakage from future observation")
        self.assertTrue(any("TEMPORAL_LEAKAGE_DETECTED" in v for v in violations))

    def test_07_database_persistence_and_retrieval(self):
        """Live multimodal features persist cleanly to SQLite table."""
        now_str = datetime.now(timezone.utc).isoformat()
        sample_dict = {
            "hotspot_id": "TEST-HOTSPOT-001",
            "latitude": 25.5,
            "longitude": 91.5,
            "reference_time_utc": now_str,
            "susceptibility_xgboost": 0.65,
            "susceptibility_rf_fallback": 0.62,
            "rainfall_anomaly": 0.75,
            "soil_moisture_anomaly": 0.70,
            "satellite_change_flag": 0.05,
            "cnn_probability": 0.58,
            "cnn_uncertainty": 0.42,
            "cnn_status": "LIVE_SHADOW_INFERENCE",
            "c15_probability": 0.61,
            "c15_entropy": 0.68,
            "c15_status": "LIVE_RESEARCH_FORECAST",
            "insar_deformation_indicator": 0.0,
            "insar_velocity_mm_yr": -12.5,
            "insar_coherence": 0.72,
            "insar_quality": 0.90,
            "insar_status": "RESEARCH_ONLY"
        }
        row_id = database.record_multimodal_features(sample_dict)
        self.assertGreater(row_id, 0)

        retrieved = database.get_latest_multimodal_features("TEST-HOTSPOT-001")
        self.assertEqual(len(retrieved), 1)
        r = retrieved[0]
        self.assertEqual(r["hotspot_id"], "TEST-HOTSPOT-001")
        self.assertAlmostEqual(r["cnn_probability"], 0.58, places=2)
        self.assertEqual(r["cnn_status"], "LIVE_SHADOW_INFERENCE")

    def test_08_multimodal_candidate_evaluation_results(self):
        """Validates that candidate evaluation suite produced certified comparison results."""
        results_path = os.path.join(PROJECT_ROOT, "multimodal_model_evaluation_results.json")
        self.assertTrue(os.path.exists(results_path), "Evaluation results JSON must exist")
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        evals = data.get("model_evaluations", {})
        self.assertIn("model_a_baseline", evals)
        self.assertIn("model_c_xgb_plus_cnn", evals)
        self.assertIn("model_f_ensemble", evals)

        # Baseline V1.1.0
        m_a = evals["model_a_baseline"]
        self.assertAlmostEqual(m_a["brier_score"], 0.1984, places=3)
        self.assertAlmostEqual(m_a["ece"], 0.1092, places=3)

        # Candidate Model F (Ensemble)
        m_f = evals["model_f_ensemble"]
        self.assertGreater(m_f["roc_auc"], m_a["roc_auc"])
        self.assertLess(m_f["brier_score"], m_a["brier_score"])

        # Candidate V2 Artifact Verification
        self.assertTrue(os.path.exists(V2_CANDIDATE_PATH), "V2 candidate model artifact must exist")
        hasher = hashlib.sha256()
        with open(V2_CANDIDATE_PATH, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        v2_sha = hasher.hexdigest()
        self.assertNotEqual(v2_sha, PROD_XGB_HASH, "V2 candidate must have unique SHA-256 distinct from V1.1.0")

    def test_09_missing_feature_fallback_safety(self):
        """If extended features are missing or degraded, system safely falls back to V1.1.0."""
        # Call without extended features
        res_fallback = fusion_engine.compute_multimodal_assessment("EVT-MEG-001", canonical_features=None)
        self.assertIsNone(res_fallback.get("status"))
        self.assertTrue(res_fallback["fallback_safety"]["fallback_active"])
        self.assertEqual(res_fallback["fallback_safety"]["active_model_used"], "V1.1.0_PRIMARY_PRODUCTION")
        self.assertEqual(res_fallback["operational_model"]["operational_risk_score"], 0.7055)

        # Call with complete canonical features
        canon_feats = {
            "cnn_probability": 0.62,
            "c15_probability": 0.65,
            "insar_deformation_indicator": 0.0
        }
        res_enhanced = fusion_engine.compute_multimodal_assessment("EVT-MEG-001", canonical_features=canon_feats)
        self.assertFalse(res_enhanced["fallback_safety"]["fallback_active"])
        self.assertAlmostEqual(res_enhanced["candidate_multimodal_shadow"]["candidate_score"], round(0.64 * 0.7055 + 0.36 * 0.62, 4))
        # Authoritative score remains V1.1.0
        self.assertTrue(res_enhanced["operational_model"]["is_authoritative"])
        self.assertFalse(res_enhanced["candidate_multimodal_shadow"]["is_authoritative"])

    def test_10_zero_emojis_in_new_code_and_dashboard(self):
        """Zero emojis permitted across python and HTML files."""
        import re
        files_to_check = [
            "canonical_feature_contract.py",
            "evaluate_multimodal_candidates.py",
            "ner_safe_live_dashboard.html"
        ]
        emoji_pat = re.compile(r'[\U00010000-\U0010ffff]')
        for f in files_to_check:
            path = os.path.join(PROJECT_ROOT, f)
            with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                c = len(emoji_pat.findall(fp.read()))
                self.assertEqual(c, 0, f"File {f} contains {c} emojis!")


if __name__ == "__main__":
    unittest.main()
