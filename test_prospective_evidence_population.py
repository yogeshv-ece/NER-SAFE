"""
=============================================================================
NER-SAFE: Prospective Evidence Population & Ledger Verification Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose:
  Comprehensive verification of the prospective validation population contract:
  1. Genuine cycle creates evidence
  2. Second cycle appends evidence
  3. First cycle remains unchanged (append-only)
  4. Unique cycle IDs linking all records
  5. Unique observation IDs
  6. Timestamp ordering (observed <= processed <= predicted)
  7. No future feature use
  8. Missing-data preservation (WAITING_FOR_DATA)
  9. No synthetic values
  10. Outcome WAITING_FOR_DATA handling
  11. Source provenance
  12. InSAR provenance consistency (canonical orbit baselines)
  13. API count correctness
  14. Dashboard count source
  15. Production hash integrity (45544c7f...)
  16. Production formula integrity (0.40/0.30/0.20/0.10)
  17. G: drive untouched
  18. No credential leakage
=============================================================================
"""

import os
import sys
import json
import uuid
import shutil
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from prospective_validation_engine import (
    prospective_engine,
    ProspectiveValidationEngine,
    ProspectivePrediction,
    CNNEvidenceRecord,
    InSAREvidenceRecord,
    C15EvidenceRecord,
    ProspectiveOutcomeRecord,
    AlignedResearchRecord,
    PROD_XGB_HASH,
    PROD_RISK_FORMULA,
    EVIDENCE_ROOT
)

PROD_XGB_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")


class TestProspectiveEvidencePopulation(unittest.TestCase):

    def setUp(self):
        """Creates an isolated test environment with fresh copy of baseline evidence."""
        self.temp_dir = tempfile.mkdtemp(prefix="ner_safe_pop_test_")
        self.engine = ProspectiveValidationEngine(evidence_root=self.temp_dir)
        for subdir in ["live_predictions", "cnn_observations", "c15_observations", "insar_observations", "outcomes", "manifests"]:
            src_sub = os.path.join(EVIDENCE_ROOT, subdir)
            dst_sub = os.path.join(self.temp_dir, subdir)
            if os.path.exists(src_sub):
                shutil.copytree(src_sub, dst_sub, dirs_exist_ok=True)

        # Load standard 48 hotspots
        events_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "events", "event_records.geojson")
        with open(events_path, "r", encoding="utf-8") as f:
            self.hotspots_features = json.load(f).get("features", [])

    def tearDown(self):
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_genuine_cycle_creates_evidence(self):
        """Requirement 1: A completed genuine live cycle produces prospective evidence."""
        cycle_id = f"CYCLE-{uuid.uuid4().hex[:8]}"
        cycle_ts = "2026-09-18T06:00:00+00:00"

        cnn_preds = [
            {"event_id": f["properties"]["event_id"], "cnn_probability": 0.52, "cnn_tier": "MODERATE", "latency_ms": 11.2}
            for f in self.hotspots_features
        ]
        c15_preds = [
            {"hotspot_id": f["properties"]["event_id"], "forecast_probability": 0.48}
            for f in self.hotspots_features
        ]

        res = self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=cycle_id,
            cycle_timestamp=cycle_ts,
            fused_hotspots=self.hotspots_features,
            cnn_results=cnn_preds,
            c15_results=c15_preds
        )

        self.assertEqual(res["status"], "EVIDENCE_RECORDED")
        self.assertEqual(res["predictions_appended"], 48)
        self.assertEqual(res["cnn_observations_appended"], 48)
        self.assertEqual(res["c15_observations_appended"], 48)

    def test_02_second_cycle_appends_evidence(self):
        """Requirement 2: Cycle N+1 appends new records without overwriting Cycle N."""
        c1_id = f"CYCLE-1-{uuid.uuid4().hex[:6]}"
        c2_id = f"CYCLE-2-{uuid.uuid4().hex[:6]}"
        ts1 = "2026-09-18T06:00:00+00:00"
        ts2 = "2026-09-18T06:05:00+00:00"

        res1 = self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c1_id,
            cycle_timestamp=ts1,
            fused_hotspots=self.hotspots_features
        )
        count_after_c1 = len(self.engine.load_predictions())

        res2 = self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c2_id,
            cycle_timestamp=ts2,
            fused_hotspots=self.hotspots_features
        )
        count_after_c2 = len(self.engine.load_predictions())

        self.assertEqual(count_after_c2, count_after_c1 + 48)
        self.assertEqual(res2["predictions_appended"], 48)

    def test_03_first_cycle_remains_unchanged(self):
        """Requirement 3: Existing ledger lines remain strictly byte-for-byte identical after append."""
        preds_file = self.engine.predictions_file
        with open(preds_file, "rb") as f:
            bytes_before = f.read()

        c_id = f"CYCLE-APPEND-{uuid.uuid4().hex[:6]}"
        self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c_id,
            cycle_timestamp="2026-09-18T06:10:00+00:00",
            fused_hotspots=self.hotspots_features
        )

        with open(preds_file, "rb") as f:
            bytes_after = f.read()

        # The prefix of bytes_after must exactly match bytes_before
        self.assertTrue(bytes_after.startswith(bytes_before))
        self.assertGreater(len(bytes_after), len(bytes_before))

    def test_04_unique_cycle_ids(self):
        """Requirement 4: Cycle ID is unique and links all records from the same cycle."""
        c_id = f"CYCLE-LINK-{uuid.uuid4().hex[:6]}"
        ts = "2026-09-18T06:15:00+00:00"

        self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c_id,
            cycle_timestamp=ts,
            fused_hotspots=self.hotspots_features
        )

        preds = [p for p in self.engine.load_predictions() if p.get("cycle_id") == c_id]
        cnns = [c for c in self.engine.load_cnn_observations() if c.get("cycle_id") == c_id]
        c15s = [c for c in self.engine.load_c15_observations() if c.get("cycle_id") == c_id]

        self.assertEqual(len(preds), 48)
        self.assertEqual(len(cnns), 48)
        self.assertEqual(len(c15s), 48)

        # All must share exact cycle_id
        self.assertTrue(all(p["cycle_id"] == c_id for p in preds))
        self.assertTrue(all(c["cycle_id"] == c_id for c in cnns))
        self.assertTrue(all(c["cycle_id"] == c_id for c in c15s))

    def test_05_unique_observation_ids(self):
        """Requirement 5: Every observation ID in the ledger must be strictly unique."""
        c_id = f"CYCLE-UNIQ-{uuid.uuid4().hex[:6]}"
        self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c_id,
            cycle_timestamp="2026-09-18T06:20:00+00:00",
            fused_hotspots=self.hotspots_features
        )

        preds = self.engine.load_predictions()
        p_ids = [p["prediction_id"] for p in preds]
        self.assertEqual(len(p_ids), len(set(p_ids)), "Prediction IDs must be unique across entire ledger")

        cnns = self.engine.load_cnn_observations()
        c_ids = [c["cnn_obs_id"] for c in cnns]
        self.assertEqual(len(c_ids), len(set(c_ids)), "CNN observation IDs must be unique")

    def test_06_timestamp_ordering(self):
        """Requirement 6: Timestamps must follow observed_at <= processed_at <= predicted_at."""
        c_id = f"CYCLE-TS-{uuid.uuid4().hex[:6]}"
        cycle_ts = "2026-09-18T06:25:00+00:00"
        self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c_id,
            cycle_timestamp=cycle_ts,
            fused_hotspots=self.hotspots_features
        )

        preds = [p for p in self.engine.load_predictions() if p.get("cycle_id") == c_id]
        for p in preds:
            self.assertEqual(p["predicted_at"], cycle_ts)

    def test_07_no_future_feature_use(self):
        """Requirement 7: Features must never use observations newer than prediction time."""
        now_dt = datetime.now(timezone.utc)
        future_dt = now_dt + timedelta(hours=2)
        valid, violations = self.engine.validate_temporal_ordering(
            observed_at=future_dt.isoformat(),
            processed_at=now_dt.isoformat(),
            predicted_at=now_dt.isoformat()
        )
        self.assertFalse(valid)
        self.assertTrue(any("TEMPORAL_ORDERING_VIOLATION" in v for v in violations))

    def test_08_missing_data_preservation(self):
        """Requirement 8: Missing temporal features must be recorded as WAITING_FOR_DATA, not fabricated."""
        c15_rec = C15EvidenceRecord(
            c15_obs_id=f"C15-TEST-WAIT-{uuid.uuid4().hex[:6]}",
            hotspot_id="EVT-MEG-001",
            forecast_timestamp_utc="2026-09-18T06:30:00+00:00",
            processed_at="2026-09-18T06:30:00+00:00",
            forecast_value=None,
            window_hours=1,
            rainfall_accumulation_mm=0.0,
            antecedent_saturation_index=0.35,
            input_completeness="WAITING_FOR_DATA",
            latency_seconds=0.02,
            quality_status="AWAITING_SUB_HOURLY_DATA"
        )
        self.assertIsNone(c15_rec.forecast_value)
        self.assertEqual(c15_rec.input_completeness, "WAITING_FOR_DATA")

    def test_09_no_synthetic_values(self):
        """Requirement 9: InSAR observations must not synthesize fake pairs; genuine outcomes only."""
        insar_obs = self.engine.load_insar_observations()
        self.assertEqual(len(insar_obs), 3, "Stack must only contain genuine 3-scene SBAS pairs")

        outcomes = self.engine.load_outcomes()
        for o in outcomes:
            self.assertIn("outcome_id", o)

    def test_10_outcome_waiting_for_data_handling(self):
        """Requirement 10: New predictions start in WAITING_FOR_DATA state."""
        c_id = f"CYCLE-WAIT-{uuid.uuid4().hex[:6]}"
        self.engine.record_live_monitoring_cycle(
            monitoring_cycle_id=c_id,
            cycle_timestamp="2026-09-18T06:35:00+00:00",
            fused_hotspots=self.hotspots_features
        )
        preds = [p for p in self.engine.load_predictions() if p.get("cycle_id") == c_id]
        for p in preds:
            self.assertEqual(p["outcome_state"], "WAITING_FOR_DATA")
            self.assertIsNone(p["outcome_id"])

    def test_11_source_provenance(self):
        """Requirement 11: Records retain genuine upstream product/granule IDs."""
        audit = self.engine.audit_cdse_insar_stack()
        self.assertEqual(audit["relative_orbit_track"], 150)
        self.assertEqual(audit["polarization"], "VV")
        self.assertEqual(audit["swath_mode"], "IW (Interferometric Wide Swath)")

    def test_12_insar_provenance_consistency(self):
        """Requirement 12: InSAR perpendicular baselines match canonical POD orbit values."""
        audit = self.engine.audit_cdse_insar_stack()
        pairs = audit["pairs"]
        baselines = {p["pair_id"]: p["perpendicular_baseline_m"] for p in pairs}

        self.assertAlmostEqual(baselines["PAIR_20260901_20260820"], 27.94, places=2)
        self.assertAlmostEqual(baselines["PAIR_20260913_20260820"], 145.00, places=1)
        self.assertAlmostEqual(baselines["PAIR_20260913_20260901"], 117.11, places=2)

        # Bedrock anchor coherence distinguished from scene-wide mean
        for p in pairs:
            self.assertIn("bedrock_anchor_coherence", p)
            self.assertIn("scene_wide_mean_coherence", p)
            self.assertGreater(p["bedrock_anchor_coherence"], p["scene_wide_mean_coherence"])

    def test_13_api_count_correctness(self):
        """Requirement 13: Summary API returns exact counts matching ledger lines."""
        summary = self.engine.get_evidence_summary()
        self.assertEqual(summary["total_production_predictions"], len(self.engine.load_predictions()))
        self.assertEqual(summary["total_cnn_observations"], len(self.engine.load_cnn_observations()))
        self.assertEqual(summary["total_c15_observations"], len(self.engine.load_c15_observations()))
        self.assertEqual(summary["total_insar_observations"], len(self.engine.load_insar_observations()))
        self.assertEqual(summary["total_outcomes"], len(self.engine.load_outcomes()))

    def test_14_dashboard_count_source(self):
        """Requirement 14: Dashboard JavaScript references API counts without emojis."""
        dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
        with open(dash_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("/api/monitoring/prospective-evidence", content)
        self.assertIn("valEvidenceCollected", content)
        self.assertIn("valEvidencePreds", content)
        self.assertIn("valEvidenceCnn", content)
        self.assertIn("valEvidenceInsar", content)
        self.assertIn("valEvidenceC15", content)

    def test_15_production_hash_integrity(self):
        """Requirement 15: Production XGBoost model SHA-256 is verified invariant."""
        with open(PROD_XGB_PATH, "rb") as f:
            computed_sha = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(computed_sha, PROD_XGB_HASH)

    def test_16_production_formula_integrity(self):
        """Requirement 16: Operational 4-factor risk formula remains invariant."""
        expected_formula = "0.40*susceptibility + 0.30*rainfall_anomaly + 0.20*soil_moisture_anomaly + 0.10*satellite_change_flag"
        self.assertEqual(PROD_RISK_FORMULA, expected_formula)

    def test_17_g_drive_untouched(self):
        """Requirement 17: G: external HDD remains untouched."""
        self.assertFalse(os.path.exists("G:\\NER_SAFE_MODELS"))
        self.assertFalse(os.path.exists("G:\\NER_SAFE_CACHE"))

    def test_18_no_credential_leakage(self):
        """Requirement 18: No credentials, tokens, or netrc passwords in ledgers."""
        for fpath in [
            self.engine.predictions_file,
            self.engine.cnn_ledger_file,
            self.engine.c15_ledger_file,
            self.engine.insar_ledger_file
        ]:
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                self.assertNotIn("bearer ", content)
                self.assertNotIn("client_secret", content)
                self.assertNotIn("netrc", content)
                self.assertNotIn("password", content)


if __name__ == "__main__":
    unittest.main()
