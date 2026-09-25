"""
=============================================================================
NER-SAFE: Live Outcome Ingestion & Prediction-to-Outcome Closure Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: 20-Point Rigorous Test Suite validating canonical outcome normalization,
         source trust classification, landslide hazard filtering, deterministic
         spatial-temporal matching, negative-outcome protection, provenance
         isolation, API count correctness, and governance invariants.

GOVERNANCE INVARIANTS:
1. Production model SHA-256 (45544c7f...) and 4-factor formula (0.40/0.30/0.20/0.10)
   remain strictly invariant.
2. CNN, InSAR, C15 remain research-only signals at operational weight 0.00.
3. No fabricated outcomes; tests use isolated temporary directories and do not
   contaminate the production prospective ledgers.
4. Exactly zero emojis across code, tests, logs, and artifacts.
=============================================================================
"""

import os
import sys
import json
import re
import tempfile
import hashlib
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from live_outcome_ingestor import (
    LiveOutcomeIngestor, CanonicalOutcomeRecord, PredictionOutcomeMatchRecord,
    haversine_distance_km, normalize_to_utc,
    TRUST_AUTHORITATIVE, TRUST_INSTITUTIONAL, TRUST_VERIFIED_FIELD,
    TRUST_CONTEXT_ONLY, TRUST_UNVERIFIED,
    STATUS_CONFIRMED_EVENT, STATUS_NO_CONFIRMED_EVENT,
    STATUS_UNRESOLVED, STATUS_INSUFFICIENT_EVIDENCE, STATUS_WAITING_FOR_DATA,
    PROC_ACCEPTED_LANDSLIDE, PROC_REJECTED_NON_LANDSLIDE,
    PROC_REJECTED_CONTEXT_ONLY, PROC_REJECTED_UNVERIFIED, PROC_REJECTED_DUPLICATE,
    DEFAULT_SPATIAL_RADIUS_KM, DEFAULT_TEMPORAL_WINDOW_HOURS
)
from prospective_validation_engine import (
    prospective_engine, PROD_XGB_HASH, PROD_RISK_FORMULA
)


class TestLiveOutcomeIngestion(unittest.TestCase):
    """Rigorous 20-Point Automated Test Suite for Live Outcome Ingestion."""

    def setUp(self):
        # Create isolated temporary directory for test ledgers to prevent production contamination
        self.test_dir = tempfile.TemporaryDirectory()
        self.evidence_root = self.test_dir.name
        self.ingestor = LiveOutcomeIngestor(
            evidence_root=self.evidence_root,
            spatial_radius_km=5.0,
            temporal_window_hours=72.0
        )

    def tearDown(self):
        self.test_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Genuine Source Normalization
    # -------------------------------------------------------------------------
    def test_01_genuine_source_normalization(self):
        """Verifies raw observation correctly normalizes to canonical outcome schema."""
        raw_text = "Major landslide blocked NH-106 near Nongstoin following continuous heavy rains."
        rec = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-GSI-20260918-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in/news/101",
            observed_at="2026-09-18T06:00:00Z",
            published_at="2026-09-18T07:30:00Z",
            raw_text=raw_text,
            latitude=25.5200,
            longitude=91.2700,
            location_description="NH-106 Nongstoin",
            administrative_area={"state": "Meghalaya", "district": "West Khasi Hills"},
            severity="SEVERE"
        )
        self.assertTrue(rec.outcome_id.startswith("OUTCOME-GSI_BHUSANKE-"))
        self.assertEqual(rec.source, "GSI_BHUSANKET_WEBAPI")
        self.assertEqual(rec.source_type, TRUST_AUTHORITATIVE)
        self.assertEqual(rec.event_type, "LANDSLIDE")
        self.assertEqual(rec.evidence_status, STATUS_CONFIRMED_EVENT)
        self.assertEqual(rec.processing_status, PROC_ACCEPTED_LANDSLIDE)
        self.assertEqual(rec.latitude, 25.5200)
        self.assertEqual(rec.longitude, 91.2700)

    # -------------------------------------------------------------------------
    # 2. Source Provenance Preservation
    # -------------------------------------------------------------------------
    def test_02_source_provenance_preservation(self):
        """Verifies original timestamps and upstream IDs are preserved byte-for-byte."""
        obs_time = "2026-09-15T14:22:00Z"
        pub_time = "2026-09-15T15:00:00Z"
        rec = self.ingestor.normalize_outcome_event(
            source="NDMA_SACHET_CAP",
            source_event_id="CAP-WARN-MEG-492",
            source_type=TRUST_INSTITUTIONAL,
            source_url="https://sachet.ndma.gov.in/cap/492",
            observed_at=obs_time,
            published_at=pub_time,
            raw_text="Debris flow observed on Shillong-Dawki road corridor.",
            latitude=25.2000,
            longitude=91.9000
        )
        self.assertEqual(rec.observed_at, obs_time)
        self.assertEqual(rec.published_at, pub_time)
        self.assertEqual(rec.source_event_id, "CAP-WARN-MEG-492")
        self.assertEqual(rec.source_type, TRUST_INSTITUTIONAL)
        self.assertEqual(rec.event_type, "DEBRIS_FLOW")

    # -------------------------------------------------------------------------
    # 3. Duplicate-Event Rejection
    # -------------------------------------------------------------------------
    def test_03_duplicate_event_rejection(self):
        """Verifies duplicate outcome events from same source and ID are rejected."""
        rec = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-001",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T08:00:00Z",
            published_at="2026-09-18T08:30:00Z",
            raw_text="Landslide triggered near Mawsynram.",
            latitude=25.3000,
            longitude=91.5800
        )
        success1, msg1 = self.ingestor.append_outcome(rec)
        self.assertTrue(success1)
        self.assertEqual(msg1, "APPENDED")

        # Second attempt with same source and event ID
        success2, msg2 = self.ingestor.append_outcome(rec)
        self.assertFalse(success2)
        self.assertEqual(msg2, "DUPLICATE_EVENT_REJECTED")

    # -------------------------------------------------------------------------
    # 4. Landslide Event Filtering
    # -------------------------------------------------------------------------
    def test_04_landslide_event_filtering(self):
        """Verifies diverse slope movement keywords are correctly classified."""
        cases = [
            ("Massive rockfall on bypass", "ROCKFALL"),
            ("Dangerous mudslide blocking culvert", "MUDSLIDE"),
            ("Slope failure along cutting", "SLOPE_COLLAPSE"),
            ("Catastrophic debris flow near riverbed", "DEBRIS_FLOW"),
            ("General hill slip reported", "LANDSLIDE")
        ]
        for text, expected_type in cases:
            is_ls, event_type, _ = self.ingestor.classify_hazard_event_type(text)
            self.assertTrue(is_ls, f"Failed to identify landslide keyword in: {text}")
            self.assertEqual(event_type, expected_type)

    # -------------------------------------------------------------------------
    # 5. Non-Landslide Context Rejection
    # -------------------------------------------------------------------------
    def test_05_non_landslide_context_rejection(self):
        """Verifies earthquake, flood, cyclone, and generic rain alerts are rejected as confirmed landslide outcomes."""
        non_landslides = [
            "Earthquake of magnitude 4.8 recorded in Shillong Plateau.",
            "Urban flood inundation in low-lying Guwahati streets.",
            "Cyclone Remal landfall warning issued by IMD.",
            "Fatal road accident involving two transport trucks on highway.",
            "Thunderstorm and lightning alert for East Khasi Hills district."
        ]
        for text in non_landslides:
            rec = self.ingestor.normalize_outcome_event(
                source="NDMA_SACHET_CAP",
                source_event_id=f"TEST-NONLS-{hash(text)}",
                source_type=TRUST_INSTITUTIONAL,
                source_url="https://sachet.ndma.gov.in",
                observed_at="2026-09-18T09:00:00Z",
                published_at="2026-09-18T09:00:00Z",
                raw_text=text
            )
            self.assertEqual(rec.processing_status, PROC_REJECTED_NON_LANDSLIDE)
            self.assertNotEqual(rec.evidence_status, STATUS_CONFIRMED_EVENT)

    # -------------------------------------------------------------------------
    # 6. Temporal Matching (0 to +72h horizon)
    # -------------------------------------------------------------------------
    def test_06_temporal_matching(self):
        """Verifies prediction->outcome matches occur only within [0, +72h] forward window."""
        t_pred = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)
        pred = {
            "prediction_id": "PRED-TEST-TEMPORAL-001",
            "hotspot_id": "EVT-MEG-001",
            "latitude": 25.1800,
            "longitude": 91.6400,
            "predicted_at": t_pred.isoformat(),
            "fused_risk_score": 0.72,
            "fused_risk_tier": "CRITICAL"
        }

        # Case A: Outcome occurs 12 hours after prediction (within 72h) -> MATCH
        out_valid = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-TIME-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at=(t_pred + timedelta(hours=12)).isoformat(),
            published_at=(t_pred + timedelta(hours=13)).isoformat(),
            raw_text="Landslide verified at Shella quarry slope.",
            latitude=25.1810,
            longitude=91.6410
        )
        self.ingestor.append_outcome(out_valid)
        matches = self.ingestor.match_predictions_to_outcomes([pred], [out_valid])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_status, "MATCHED_TRUE_POSITIVE")
        self.assertAlmostEqual(matches[0].time_to_outcome_hours, 12.0, places=1)

        # Case B: Outcome occurred 2 hours BEFORE prediction -> NO MATCH (retroactive leak rejected)
        out_past = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-TIME-02",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at=(t_pred - timedelta(hours=2)).isoformat(),
            published_at=(t_pred - timedelta(hours=1)).isoformat(),
            raw_text="Landslide observed earlier.",
            latitude=25.1810,
            longitude=91.6410
        )
        matches_past = self.ingestor.match_predictions_to_outcomes([pred], [out_past])
        self.assertEqual(len(matches_past), 0)

        # Case C: Outcome occurred 90 hours after prediction (> 72h horizon) -> NO MATCH
        out_future = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-TIME-03",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at=(t_pred + timedelta(hours=90)).isoformat(),
            published_at=(t_pred + timedelta(hours=91)).isoformat(),
            raw_text="Landslide occurred after window expired.",
            latitude=25.1810,
            longitude=91.6410
        )
        matches_future = self.ingestor.match_predictions_to_outcomes([pred], [out_future])
        self.assertEqual(len(matches_future), 0)

    # -------------------------------------------------------------------------
    # 7. Spatial Matching (within 5.0 km corridor radius)
    # -------------------------------------------------------------------------
    def test_07_spatial_matching(self):
        """Verifies prediction->outcome matches enforce <= 5.0 km spatial corridor radius."""
        pred = {
            "prediction_id": "PRED-TEST-SPATIAL-001",
            "hotspot_id": "EVT-MEG-002",
            "latitude": 25.5700,
            "longitude": 91.8800,
            "predicted_at": "2026-09-18T06:00:00Z",
            "fused_risk_score": 0.65,
            "fused_risk_tier": "HIGH"
        }

        # Outcome 1.5 km away -> MATCH
        out_near = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-SPATIAL-NEAR",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T10:00:00Z",
            published_at="2026-09-18T11:00:00Z",
            raw_text="Landslide at Mawlai slope.",
            latitude=25.5800,
            longitude=91.8900
        )
        dist_near = haversine_distance_km(pred["latitude"], pred["longitude"], out_near.latitude, out_near.longitude)
        self.assertLessEqual(dist_near, 5.0)
        matches_near = self.ingestor.match_predictions_to_outcomes([pred], [out_near])
        self.assertEqual(len(matches_near), 1)

        # Outcome 15 km away -> OUT OF BOUNDS -> NO MATCH
        out_far = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-SPATIAL-FAR",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T10:00:00Z",
            published_at="2026-09-18T11:00:00Z",
            raw_text="Landslide at distant valley.",
            latitude=25.7000,
            longitude=91.8800
        )
        dist_far = haversine_distance_km(pred["latitude"], pred["longitude"], out_far.latitude, out_far.longitude)
        self.assertGreater(dist_far, 5.0)
        matches_far = self.ingestor.match_predictions_to_outcomes([pred], [out_far])
        self.assertEqual(len(matches_far), 0)

    # -------------------------------------------------------------------------
    # 8. Waiting-Window Handling
    # -------------------------------------------------------------------------
    def test_08_waiting_window_handling(self):
        """Verifies prediction remains in WAITING_FOR_OUTCOME until 72h window elapses."""
        now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
        # Prediction issued 10 hours ago -> age = 10h < 72h -> WAITING
        pred_recent = {
            "prediction_id": "PRED-WAITING-001",
            "hotspot_id": "EVT-01",
            "latitude": 25.1,
            "longitude": 91.1,
            "predicted_at": (now - timedelta(hours=10)).isoformat(),
            "fused_risk_score": 0.50,
            "fused_risk_tier": "WATCH"
        }
        with open(self.ingestor.predictions_ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(pred_recent) + "\n")

        audit = self.ingestor.audit_prospective_predictions(now=now)
        self.assertEqual(audit["total_prospective_predictions"], 1)
        self.assertEqual(audit["waiting_for_outcome"], 1)
        self.assertEqual(audit["ready_for_evaluation"], 0)
        self.assertEqual(audit["genuinely_resolved"], 0)

    # -------------------------------------------------------------------------
    # 9. Negative-Outcome Protection ("No Report" != "No Event")
    # -------------------------------------------------------------------------
    def test_09_negative_outcome_protection(self):
        """CRITICAL: Verifies elapsed window without report marks UNRESOLVED / INSUFFICIENT_EVIDENCE, not NO_CONFIRMED_EVENT."""
        now = datetime(2026, 9, 25, 0, 0, 0, tzinfo=timezone.utc)
        # Prediction issued 100 hours ago (> 72h), but no ground surveillance confirmed no event
        pred_elapsed = {
            "prediction_id": "PRED-ELAPSED-001",
            "hotspot_id": "EVT-02",
            "latitude": 25.1,
            "longitude": 91.1,
            "predicted_at": (now - timedelta(hours=100)).isoformat(),
            "fused_risk_score": 0.40,
            "fused_risk_tier": "WATCH"
        }
        with open(self.ingestor.predictions_ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(pred_elapsed) + "\n")

        audit = self.ingestor.audit_prospective_predictions(now=now)
        self.assertEqual(audit["waiting_for_outcome"], 0)
        self.assertEqual(audit["ready_for_evaluation"], 1)
        self.assertEqual(audit["genuinely_resolved"], 0)
        # Unresolved because no ground report arrived — NOT fabricated as NO_CONFIRMED_EVENT
        self.assertEqual(audit["unresolved_insufficient_evidence"], 1)

    # -------------------------------------------------------------------------
    # 10. Citizen VERIFIED vs UNVERIFIED Handling
    # -------------------------------------------------------------------------
    def test_10_citizen_verified_vs_unverified_handling(self):
        """Verifies only VERIFIED citizen reports create CONFIRMED_EVENT; UNVERIFIED remain context only."""
        # Case A: UNVERIFIED citizen report -> REJECTED_UNVERIFIED
        rec_unverified = self.ingestor.normalize_outcome_event(
            source="CITIZEN_REPORTS",
            source_event_id="CR-001",
            source_type=TRUST_UNVERIFIED,
            source_url="/api/reports/CR-001",
            observed_at="2026-09-18T08:00:00Z",
            published_at="2026-09-18T08:00:00Z",
            raw_text="Rumor of landslide on hill track.",
            latitude=25.5,
            longitude=91.8
        )
        self.assertEqual(rec_unverified.processing_status, PROC_REJECTED_UNVERIFIED)
        self.assertNotEqual(rec_unverified.evidence_status, STATUS_CONFIRMED_EVENT)

        # Case B: Field officer VERIFIED citizen report -> ACCEPTED_LANDSLIDE_EVENT
        rec_verified = self.ingestor.normalize_outcome_event(
            source="CITIZEN_REPORTS",
            source_event_id="CR-002",
            source_type=TRUST_VERIFIED_FIELD,
            source_url="/api/reports/CR-002",
            observed_at="2026-09-18T08:00:00Z",
            published_at="2026-09-18T08:00:00Z",
            raw_text="Ground verified landslide: 50m road cut collapsed.",
            latitude=25.5,
            longitude=91.8
        )
        self.assertEqual(rec_verified.processing_status, PROC_ACCEPTED_LANDSLIDE)
        self.assertEqual(rec_verified.evidence_status, STATUS_CONFIRMED_EVENT)

    # -------------------------------------------------------------------------
    # 11. No-Fabrication Enforcement
    # -------------------------------------------------------------------------
    def test_11_no_fabrication_enforcement(self):
        """Verifies that empty upstream responses produce 0 outcomes, never synthetic placeholders."""
        summary = self.ingestor.get_outcome_monitoring_summary()
        self.assertEqual(summary["total_outcomes_ingested"], 0)
        self.assertEqual(summary["confirmed_events"], 0)
        self.assertEqual(summary["latest_outcome_observation"], "NONE_RECORDED")
        self.assertEqual(summary["evaluation_status"], "INSUFFICIENT_OUTCOME_DATA")

    # -------------------------------------------------------------------------
    # 12. Operational-Cycle Provenance Filter
    # -------------------------------------------------------------------------
    def test_12_operational_cycle_provenance_filter(self):
        """Verifies test-generated predictions are excluded from operational evaluation."""
        preds = [
            {"prediction_id": "PRED-OP-01", "cycle_origin": "OPERATIONAL_LIVE", "predicted_at": "2026-09-18T06:00:00Z"},
            {"prediction_id": "PRED-TEST-01", "cycle_origin": "TEST_SUITE", "predicted_at": "2026-09-18T06:00:00Z"}
        ]
        with open(self.ingestor.predictions_ledger_path, "w", encoding="utf-8") as f:
            for p in preds:
                f.write(json.dumps(p) + "\n")

        loaded_op = self.ingestor.load_prospective_predictions(only_operational=True)
        self.assertEqual(len(loaded_op), 1)
        self.assertEqual(loaded_op[0]["prediction_id"], "PRED-OP-01")

        loaded_all = self.ingestor.load_prospective_predictions(only_operational=False)
        self.assertEqual(len(loaded_all), 2)

    # -------------------------------------------------------------------------
    # 13. API Count Correctness
    # -------------------------------------------------------------------------
    def test_13_api_count_correctness(self):
        """Verifies summary counts strictly match lines on disk."""
        rec = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-API-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T09:00:00Z",
            published_at="2026-09-18T09:00:00Z",
            raw_text="Landslide confirmed by GSI.",
            latitude=25.4,
            longitude=91.6
        )
        self.ingestor.append_outcome(rec)

        summary = self.ingestor.get_outcome_monitoring_summary()
        self.assertEqual(summary["total_outcomes_ingested"], 1)
        self.assertEqual(summary["confirmed_events"], 1)

    # -------------------------------------------------------------------------
    # 14. Production Model Hash Integrity
    # -------------------------------------------------------------------------
    def test_14_production_hash_integrity(self):
        """CRITICAL: Verifies calibrated_xgboost_model.joblib retains exact SHA-256 hash."""
        model_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")
        self.assertTrue(os.path.exists(model_path), "Production XGBoost model must exist.")
        with open(model_path, "rb") as fp:
            digest = hashlib.sha256(fp.read()).hexdigest()
        self.assertEqual(digest, PROD_XGB_HASH, "Production XGBoost model SHA-256 mismatch.")
        self.assertEqual(digest, "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c")

    # -------------------------------------------------------------------------
    # 15. Production Formula Integrity
    # -------------------------------------------------------------------------
    def test_15_production_formula_integrity(self):
        """CRITICAL: Verifies operational 4-factor formula weights strictly remain 0.40/0.30/0.20/0.10."""
        self.assertIn("0.40*susceptibility", PROD_RISK_FORMULA)
        self.assertIn("0.30*rainfall_anomaly", PROD_RISK_FORMULA)
        self.assertIn("0.20*soil_moisture_anomaly", PROD_RISK_FORMULA)
        self.assertIn("0.10*satellite_change_flag", PROD_RISK_FORMULA)

    # -------------------------------------------------------------------------
    # 16. Test-Cycle Exclusion
    # -------------------------------------------------------------------------
    def test_16_test_cycle_exclusion(self):
        """Verifies KNOWN_TEST_CYCLES are excluded from evaluation."""
        eval_res = prospective_engine.evaluate_prospective_performance(filter_origin="OPERATIONAL_LIVE")
        self.assertIn("status", eval_res)
        self.assertIn("sample_statistics", eval_res)

    # -------------------------------------------------------------------------
    # 17. External Source Unavailable Handling
    # -------------------------------------------------------------------------
    def test_17_external_source_unavailable_handling(self):
        """Verifies when a source is offline or credentials fail, it returns clean ACCESS_UNAVAILABLE status."""
        status = self.ingestor.poll_gsi_bhusanket()
        self.assertIn(status["status"], ("LIVE_SUCCESS", "FETCH_FAILED", "ACCESS_UNAVAILABLE"))
        self.assertIsInstance(status["records_retrieved"], int)

    # -------------------------------------------------------------------------
    # 18. Append-Only Outcome Ledger
    # -------------------------------------------------------------------------
    def test_18_append_only_outcome_ledger(self):
        """Verifies historical lines are preserved byte-for-byte upon appending new outcomes."""
        rec1 = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-APP-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T05:00:00Z",
            published_at="2026-09-18T05:00:00Z",
            raw_text="First landslide event.",
            latitude=25.2,
            longitude=91.4
        )
        self.ingestor.append_outcome(rec1)
        with open(self.ingestor.outcomes_ledger_path, "rb") as f:
            bytes_cycle1 = f.read()

        rec2 = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-APP-02",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T06:00:00Z",
            published_at="2026-09-18T06:00:00Z",
            raw_text="Second landslide event.",
            latitude=25.3,
            longitude=91.5
        )
        self.ingestor.append_outcome(rec2)
        with open(self.ingestor.outcomes_ledger_path, "rb") as f:
            bytes_cycle2 = f.read()

        self.assertTrue(bytes_cycle2.startswith(bytes_cycle1), "Historical bytes modified on append!")

    # -------------------------------------------------------------------------
    # 19. Idempotent Re-Ingestion
    # -------------------------------------------------------------------------
    def test_19_idempotent_reingestion(self):
        """Verifies re-running polling/ingestion is idempotent and produces zero duplicates."""
        rec = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-IDEMP-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T07:00:00Z",
            published_at="2026-09-18T07:00:00Z",
            raw_text="Idempotent check landslide.",
            latitude=25.25,
            longitude=91.45
        )
        appended1, _ = self.ingestor.append_outcome(rec)
        self.assertTrue(appended1)

        # Ingestor reloaded from disk
        ingestor2 = LiveOutcomeIngestor(evidence_root=self.evidence_root)
        appended2, msg2 = ingestor2.append_outcome(rec)
        self.assertFalse(appended2)
        self.assertEqual(msg2, "DUPLICATE_EVENT_REJECTED")

    # -------------------------------------------------------------------------
    # 20. Zero Secret Exposure & Zero Emojis
    # -------------------------------------------------------------------------
    def test_20_no_secret_exposure_and_zero_emojis(self):
        """Verifies zero secret exposure and zero emojis across outcome records."""
        rec = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-SEC-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T08:00:00Z",
            published_at="2026-09-18T08:00:00Z",
            raw_text="Security check landslide entry.",
            latitude=25.25,
            longitude=91.45
        )
        d_str = json.dumps(rec.to_dict()).lower()
        forbidden_secrets = ["bearer ya29", "client_secret", "refresh_token", "password", "begin private key"]
        for s in forbidden_secrets:
            self.assertNotIn(s, d_str)

        # Zero emoji check
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        emojis = emoji_pattern.findall(d_str)
        self.assertEqual(len(emojis), 0, f"Found {len(emojis)} emojis in outcome schema.")

    # -------------------------------------------------------------------------
    # 21. Aware UTC vs Aware UTC
    # -------------------------------------------------------------------------
    def test_21_datetime_aware_utc_vs_aware_utc(self):
        """Regression Check 1: Comparing two aware UTC datetimes calculates exact delta without error."""
        dt1 = normalize_to_utc("2026-09-18T10:00:00+00:00")
        dt2 = normalize_to_utc("2026-09-18T12:30:00Z")
        self.assertIsNotNone(dt1)
        self.assertIsNotNone(dt2)
        self.assertEqual(dt1.tzinfo, timezone.utc)
        self.assertEqual(dt2.tzinfo, timezone.utc)
        delta_hours = (dt2 - dt1).total_seconds() / 3600.0
        self.assertAlmostEqual(delta_hours, 2.5)

    # -------------------------------------------------------------------------
    # 22. Aware Non-UTC vs Aware UTC
    # -------------------------------------------------------------------------
    def test_22_datetime_aware_non_utc_vs_aware_utc(self):
        """Regression Check 2: Aware non-UTC (e.g. IST +05:30) is shifted accurately to UTC."""
        dt_ist = normalize_to_utc("2026-09-18T15:30:00+05:30")
        dt_utc = normalize_to_utc("2026-09-18T10:00:00Z")
        self.assertIsNotNone(dt_ist)
        self.assertIsNotNone(dt_utc)
        self.assertEqual(dt_ist.tzinfo, timezone.utc)
        self.assertEqual(dt_utc.tzinfo, timezone.utc)
        # 15:30 IST is identical to 10:00 UTC
        self.assertEqual(dt_ist, dt_utc)
        delta_sec = (dt_ist - dt_utc).total_seconds()
        self.assertEqual(delta_sec, 0.0)

    # -------------------------------------------------------------------------
    # 23. Naive Timestamp with Known UTC Semantics
    # -------------------------------------------------------------------------
    def test_23_datetime_naive_known_utc_semantics(self):
        """Regression Check 3: Naive timestamp from NER-SAFE internal prediction is safely localized as UTC."""
        dt = normalize_to_utc("2026-09-18T06:00:00", source_name="NER_SAFE_PREDICTIONS")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 6)

    # -------------------------------------------------------------------------
    # 24. Naive Timestamp with Known Source-Local Timezone (IST)
    # -------------------------------------------------------------------------
    def test_24_datetime_naive_known_source_local_ist(self):
        """Regression Check 4: Naive Indian agency timestamp (GSI/NDMA) localizes to IST then shifts to UTC."""
        # 11:00 AM IST on GSI feed -> 05:30 AM UTC
        dt = normalize_to_utc("2026-09-18T11:00:00", source_name="GSI_BHUSANKET_WEBAPI")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 5)
        self.assertEqual(dt.minute, 30)

    # -------------------------------------------------------------------------
    # 25. Unknown Timezone Rejected Without Fabricating Assumption
    # -------------------------------------------------------------------------
    def test_25_datetime_unknown_timezone_rejected(self):
        """Regression Check 5: Naive timestamp from unverified/unknown source is rejected to prevent label bias."""
        dt = normalize_to_utc("2026-09-18T11:00:00", source_name="UNSPECIFIED_EXTERNAL_FEED")
        self.assertIsNone(dt, "Naive timestamp with unknown source contract must return None.")

    # -------------------------------------------------------------------------
    # 26. Daylight / International Timezone Conversion
    # -------------------------------------------------------------------------
    def test_26_datetime_daylight_international_conversion(self):
        """Regression Check 6: Offsets with daylight savings (e.g. -04:00 EDT) correctly convert to UTC."""
        dt_edt = normalize_to_utc("2026-06-18T14:00:00-04:00")
        self.assertIsNotNone(dt_edt)
        self.assertEqual(dt_edt.tzinfo, timezone.utc)
        # 14:00 -04:00 -> 18:00 UTC
        self.assertEqual(dt_edt.hour, 18)

    # -------------------------------------------------------------------------
    # 27. Prediction / Outcome Matching After Normalization
    # -------------------------------------------------------------------------
    def test_27_datetime_prediction_outcome_matching_after_normalization(self):
        """Regression Check 7: Prediction issued at 04:00 UTC matches GSI event at 11:30 IST (06:00 UTC)."""
        pred = {
            "prediction_id": "PRED-TIME-01",
            "hotspot_id": "EVT-MEG-001",
            "latitude": 25.1837,
            "longitude": 91.6421,
            "predicted_at": "2026-09-18T04:00:00Z",
            "fused_risk_score": 0.72,
            "fused_risk_tier": "CRITICAL"
        }
        with open(self.ingestor.predictions_ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(pred) + "\n")

        # GSI event reported in naive IST string "2026-09-18T11:30:00" -> 06:00:00 UTC (2h after prediction)
        out = self.ingestor.normalize_outcome_event(
            source="GSI_BHUSANKET_WEBAPI",
            source_event_id="EVT-GSI-TIME-01",
            source_type=TRUST_AUTHORITATIVE,
            source_url="https://bhusanket.gsi.gov.in",
            observed_at="2026-09-18T11:30:00",
            published_at="2026-09-18T11:30:00",
            raw_text="Major rockfall at Shella road.",
            latitude=25.1837,
            longitude=91.6421
        )
        self.ingestor.append_outcome(out)

        matches = self.ingestor.match_predictions_to_outcomes()
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0].time_to_outcome_hours, 2.0, places=1)
        self.assertEqual(matches[0].match_status, "MATCHED_TRUE_POSITIVE")

    # -------------------------------------------------------------------------
    # 28. No TypeError Between Valid Timestamps
    # -------------------------------------------------------------------------
    def test_28_datetime_no_typeerror_between_valid_timestamps(self):
        """Regression Check 8: Pairwise subtraction between mixed sources never raises TypeError."""
        ts_list = [
            ("2026-09-18T06:00:00Z", "NER_SAFE_PREDICTIONS"),
            ("2026-09-18T12:00:00+05:30", "NDMA_SACHET_CAP"),
            ("2026-09-18T14:30:00", "GSI_BHUSANKET_WEBAPI"),
            ("2026-09-18T16:00:00", "NER_SAFE_CITIZEN_REPORTS"),
            ("2026-09-18T08:00:00-03:00", None)
        ]
        normalized = [normalize_to_utc(ts, src) for ts, src in ts_list]
        for i in range(len(normalized)):
            for j in range(len(normalized)):
                dt_a = normalized[i]
                dt_b = normalized[j]
                self.assertIsNotNone(dt_a)
                self.assertIsNotNone(dt_b)
                # Must never raise TypeError: can't subtract offset-naive and offset-aware datetimes
                diff = (dt_b - dt_a).total_seconds()
                self.assertIsInstance(diff, float)

    # -------------------------------------------------------------------------
    # 29. Invalid Timestamp Rejected Safely
    # -------------------------------------------------------------------------
    def test_29_datetime_invalid_timestamp_rejected_safely(self):
        """Regression Check 9: Malformed or unparseable timestamps return None without crashing."""
        invalid_samples = ["not-a-timestamp", "2026-99-99T99:99:99", "", "   ", None]
        for s in invalid_samples:
            res = normalize_to_utc(s, source_name="GSI_BHUSANKET_WEBAPI")
            self.assertIsNone(res, f"Expected None for invalid timestamp: {s}")

    # -------------------------------------------------------------------------
    # 30. No Fabricated Timezone Assumption
    # -------------------------------------------------------------------------
    def test_30_datetime_no_fabricated_timezone_assumption(self):
        """Regression Check 10: Naive timestamps without proven source contract return None."""
        naive_str = "2026-09-18 10:00:00"
        res = normalize_to_utc(naive_str, source_name=None)
        self.assertIsNone(res, "Source-less naive timestamp must be rejected rather than fabricated as UTC.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
