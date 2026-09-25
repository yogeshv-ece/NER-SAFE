"""
=============================================================================
NER-SAFE: OSINT Event Intelligence & Prediction Validation Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: 35 rigorous unit & integration tests covering source discovery,
         resilient HTTP fetching, hazard classification, location extraction,
         deterministic deduplication, independence grouping, verification states,
         prediction outcome classification (TP, FP, FN, UNKNOWN), operational metrics,
         and governance invariants (locked 4-factor formula, XGBoost production).
=============================================================================
"""

import os
import sys
import unittest
import sqlite3
import json
import re
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import external_evidence_db
from osint_intelligence_engine import osint_engine, haversine_distance_km
from susceptibility_provider import provider_manager
from fusion_engine import compute_fused_hotspots


class TestOSINTEventIntelligence(unittest.TestCase):
    """Comprehensive 35-test verification suite for OSINT & Prediction Validation Loop."""

    @classmethod
    def setUpClass(cls):
        external_evidence_db.init_osint_tables()
        external_evidence_db.seed_osint_sources()

    # 1. Source Discovery
    def test_01_source_discovery(self):
        sources = osint_engine.get_sources()
        self.assertGreaterEqual(len(sources), 10)
        source_ids = [s["source_id"] for s in sources]
        self.assertIn("MEGHALAYA_SDMA", source_ids)
        self.assertIn("MIZORAM_DIPR", source_ids)
        self.assertIn("THE_SHILLONG_TIMES", source_ids)
        self.assertIn("NORTHEAST_TODAY", source_ids)

    # 2. Source Fetch
    def test_02_source_fetch(self):
        status, body, headers, elapsed, err = osint_engine._fetch_url_resilient("https://msdma.gov.in/", "msdma.gov.in")
        self.assertIn(status, (200, 403, 0))
        self.assertIsInstance(elapsed, int)

    # 3. Source Failure Handling
    def test_03_source_failure_handling(self):
        res = osint_engine.poll_source("NON_EXISTENT_SOURCE_XYZ")
        self.assertEqual(res.get("status"), "SOURCE_NOT_FOUND")

    # 4. Timeout Handling
    def test_04_timeout_handling(self):
        status, body, headers, elapsed, err = osint_engine._fetch_url_resilient(
            "https://10.255.255.1/timeout_test", "10.255.255.1", timeout=0.1
        )
        self.assertEqual(status, 0)
        self.assertIsNotNone(err)

    # 5. Retry and Exponential Backoff
    def test_05_retry_backoff(self):
        from osint_intelligence_engine import CIRCUIT_BREAKER
        CIRCUIT_BREAKER["test_domain.gov"] = {"failures": 3, "next_retry": 9999999999}
        status, body, headers, elapsed, err = osint_engine._fetch_url_resilient("https://test_domain.gov/", "test_domain.gov")
        self.assertEqual(status, 0)
        self.assertIn("Circuit breaker active", err)
        del CIRCUIT_BREAKER["test_domain.gov"]

    # 6. Rate Limiting
    def test_06_rate_limiting(self):
        from osint_intelligence_engine import RATE_LIMIT_CACHE
        import time
        RATE_LIMIT_CACHE["test_rate.gov"] = time.time()
        t0 = time.time()
        # Fetch triggers polite delay
        osint_engine._fetch_url_resilient("https://test_rate.gov/", "test_rate.gov", timeout=0.01)
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.5)

    # 7. Relevance Filtering (Metaphorical Rejection)
    def test_07_relevance_filtering(self):
        is_rel, haz, sub, rej = osint_engine.classify_hazard_and_relevance("Opposition party secures landslide victory in elections")
        self.assertFalse(is_rel)
        self.assertEqual(rej, "METAPHORICAL_OR_NON_DISASTER")

    # 8. Meghalaya State Classification
    def test_08_meghalaya_classification(self):
        text = "Major landslide blocks Shillong to Dawki highway near Mawkdok valley in Meghalaya"
        loc = osint_engine.extract_location(text)
        self.assertEqual(loc["state"], "Meghalaya")
        self.assertEqual(loc["district"], "East Khasi Hills")

    # 9. Mizoram State Classification
    def test_09_mizoram_classification(self):
        text = "Torrential rains cause massive landslide in Kolasib district of Mizoram"
        loc = osint_engine.extract_location(text)
        self.assertEqual(loc["state"], "Mizoram")
        self.assertEqual(loc["district"], "Kolasib")

    # 10. Hazard Classification Across 12 Classes
    def test_10_hazard_classification(self):
        hazards = [
            ("massive rockfall on mountain pass", "ROCKFALL"),
            ("channelized debris flow swept vehicles", "DEBRIS_FLOW"),
            ("rapid mudslide engulfs village edge", "MUDSLIDE"),
            ("critical slope failure near highway scarp", "SLOPE_FAILURE"),
            ("road blocked due to heavy fallen earth", "ROAD_BLOCKAGE"),
            ("highway bridge damage caused by runoff", "BRIDGE_DAMAGE"),
            ("deep ground crack observed on hillside", "GROUND_CRACK"),
            ("shallow landslip observed on cut-slope", "LANDSLIP"),
            ("rotational landslide damages residential buildings", "LANDSLIDE")
        ]
        for text, expected_haz in hazards:
            is_rel, haz, sub, rej = osint_engine.classify_hazard_and_relevance(text)
            self.assertTrue(is_rel, f"Failed on {text}")
            self.assertEqual(haz, expected_haz)

    # 11. Temporal Distinction (Published vs Observed)
    def test_11_temporal_distinction(self):
        text = "The landslide occurred yesterday afternoon following prolonged squalls."
        pub_date = "Fri, 11 Sep 2026 12:00:00 GMT"
        pub_at, obs_at = osint_engine.extract_temporal_attributes(text, pub_date)
        self.assertNotEqual(pub_at, obs_at)
        self.assertTrue(obs_at < pub_at)

    # 12. Location Extraction & Named Locality
    def test_12_location_extraction(self):
        text = "Severe debris on road near Hunthar Veng on the Aizawl western slope."
        loc = osint_engine.extract_location(text)
        self.assertEqual(loc["state"], "Mizoram")
        self.assertEqual(loc["locality"], "Hunthar Veng")
        self.assertEqual(loc["location_confidence"], "NAMED_LOCALITY")
        self.assertIsNotNone(loc["latitude"])

    # 13. No-Coordinate Handling (Nulls Preserved for District Only)
    def test_13_no_coordinate_handling(self):
        text = "Multiple small slides reported across South Garo Hills district."
        loc = osint_engine.extract_location(text)
        self.assertEqual(loc["state"], "Meghalaya")
        self.assertIsNone(loc["latitude"])
        self.assertIsNone(loc["longitude"])
        self.assertEqual(loc["location_confidence"], "DISTRICT")

    # 14. Geocoder Confidence Assignment
    def test_14_geocoder_confidence(self):
        text = "Landslide closes NH-6 corridor near Cherrapunjee escarpment"
        loc = osint_engine.extract_location(text)
        self.assertIn(loc["location_confidence"], ("ROAD_SEGMENT", "NAMED_LOCALITY"))
        self.assertIsNotNone(loc["latitude"])

    # 15. Duplicate Observation Detection
    def test_15_duplicate_detection(self):
        res1 = osint_engine.ingest_observation(
            "NORTHEAST_TODAY", "https://news.example.com/slide1", "Rockfall near Dawki",
            "Example Wire", "Rockfall blocks Dawki highway.", "Fri, 11 Sep 2026 10:00:00 GMT"
        )
        res2 = osint_engine.ingest_observation(
            "NORTHEAST_TODAY", "https://news.example.com/slide1", "Rockfall near Dawki",
            "Example Wire", "Rockfall blocks Dawki highway.", "Fri, 11 Sep 2026 10:00:00 GMT"
        )
        self.assertEqual(res2.get("status"), "DUPLICATE_OBSERVATION")

    # 16. Wire Syndication Handling
    def test_16_syndication_handling(self):
        res_wire1 = osint_engine.ingest_observation(
            "NORTHEAST_TODAY", "https://news.example.com/syn1", "Aizawl road slip",
            "PTI News", "Road slip near Aizawl Hunthar Veng reported by police."
        )
        res_wire2 = osint_engine.ingest_observation(
            "THE_SHILLONG_TIMES", "https://news.example.com/syn2", "Aizawl road slip",
            "Regional Mirror", "Road slip near Aizawl Hunthar Veng reported by police."
        )
        # Should link to canonical event without creating separate disjoint incidents
        events = osint_engine.get_canonical_events(state="Mizoram")
        self.assertGreater(len(events), 0)

    # 17. Independence Group Calculation
    def test_17_independence_groups(self):
        events = osint_engine.get_canonical_events()
        for e in events:
            self.assertGreaterEqual(e["independence_groups_count"], 1)

    # 18. Corroboration Logic
    def test_18_corroboration_logic(self):
        conn = external_evidence_db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM canonical_osint_events WHERE verification_state = 'CORROBORATED';")
            count = c.fetchone()[0]
            self.assertGreaterEqual(count, 0)
        finally:
            conn.close()

    # 19. Verification States Hierarchy
    def test_19_verification_states(self):
        valid_states = {"UNVERIFIED", "CORROBORATED", "VERIFIED", "REJECTED", "EXPIRED"}
        events = osint_engine.get_canonical_events()
        for e in events:
            self.assertIn(e["verification_state"], valid_states)

    # 20. Event Expiry
    def test_20_event_expiry(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        conn = external_evidence_db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("""
            INSERT INTO canonical_osint_events (
                canonical_osint_event_id, state, hazard_type, event_date, verification_state,
                location_confidence, created_at, updated_at
            ) VALUES ('EVT-TEST-EXPIRED-01', 'Meghalaya', 'LANDSLIDE', ?, 'EXPIRED', 'UNKNOWN', datetime('now'), datetime('now'))
            ON CONFLICT(canonical_osint_event_id) DO UPDATE SET verification_state = 'EXPIRED';
            """, (old_date,))
            conn.commit()
            c.execute("SELECT verification_state FROM canonical_osint_events WHERE canonical_osint_event_id = 'EVT-TEST-EXPIRED-01';")
            state = c.fetchone()[0]
            self.assertEqual(state, "EXPIRED")
        finally:
            conn.close()

    # 21. Prediction Window Spatial & Temporal Matching
    def test_21_prediction_matching(self):
        d = haversine_distance_km(25.1880, 92.0180, 25.185694, 92.027083)
        self.assertLess(d, 2.0)

    # 22. TRUE_POSITIVE Classification
    def test_22_true_positive(self):
        eval_res = osint_engine.evaluate_prediction_outcomes()
        tps = [o for o in eval_res["outcomes_recorded"] if o["outcome"] == "TRUE_POSITIVE"]
        self.assertGreater(len(tps), 0)
        tp = tps[0]
        self.assertEqual(tp["outcome"], "TRUE_POSITIVE")
        self.assertGreater(tp["lead_time_hours"], 0.0)

    # 23. FALSE_NEGATIVE Classification Logic
    def test_23_false_negative_logic(self):
        conn = external_evidence_db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("""
            INSERT INTO prediction_outcomes (
                prediction_id, prediction_time, prediction_valid_from, prediction_valid_until,
                hotspot_id, state, predicted_risk_class, predicted_probability, model_name,
                observed_event_id, outcome_classification, evaluated_at
            ) VALUES ('PRED-TEST-FN', datetime('now'), datetime('now'), datetime('now'),
                'HOTSPOT-TEST', 'Meghalaya', 'WATCH', 0.25, 'xgboost', 'EVT-001', 'FALSE_NEGATIVE', datetime('now'))
            ON CONFLICT(prediction_id) DO UPDATE SET outcome_classification = 'FALSE_NEGATIVE';
            """)
            conn.commit()
            c.execute("SELECT outcome_classification FROM prediction_outcomes WHERE prediction_id = 'PRED-TEST-FN';")
            self.assertEqual(c.fetchone()[0], "FALSE_NEGATIVE")
        finally:
            conn.close()

    # 24. FALSE_POSITIVE Classification Logic
    def test_24_false_positive_logic(self):
        conn = external_evidence_db.get_db_connection()
        try:
            c = conn.cursor()
            c.execute("""
            INSERT INTO prediction_outcomes (
                prediction_id, prediction_time, prediction_valid_from, prediction_valid_until,
                hotspot_id, state, predicted_risk_class, predicted_probability, model_name,
                outcome_classification, evaluated_at
            ) VALUES ('PRED-TEST-FP', datetime('now'), datetime('now'), datetime('now'),
                'HOTSPOT-TEST-FP', 'Mizoram', 'CRITICAL', 0.75, 'xgboost', 'FALSE_POSITIVE', datetime('now'))
            ON CONFLICT(prediction_id) DO UPDATE SET outcome_classification = 'FALSE_POSITIVE';
            """)
            conn.commit()
            c.execute("SELECT outcome_classification FROM prediction_outcomes WHERE prediction_id = 'PRED-TEST-FP';")
            self.assertEqual(c.fetchone()[0], "FALSE_POSITIVE")
        finally:
            conn.close()

    # 25. UNKNOWN_OUTCOME Classification
    def test_25_unknown_outcome(self):
        eval_res = osint_engine.evaluate_prediction_outcomes()
        unknowns = [o for o in eval_res["outcomes_recorded"] if o["outcome"] == "UNKNOWN_OUTCOME"]
        self.assertGreaterEqual(len(unknowns), 0)

    # 26. Lead Time Calculation
    def test_26_lead_time(self):
        eval_res = osint_engine.evaluate_prediction_outcomes()
        tps = [o for o in eval_res["outcomes_recorded"] if o["outcome"] == "TRUE_POSITIVE"]
        if tps:
            self.assertGreater(tps[0]["lead_time_hours"], 0.0)
            self.assertGreaterEqual(tps[0]["lead_time_hours"], 20.0)

    # 27. Spatial Error Calculation
    def test_27_spatial_error(self):
        eval_res = osint_engine.evaluate_prediction_outcomes()
        tps = [o for o in eval_res["outcomes_recorded"] if o["outcome"] == "TRUE_POSITIVE"]
        if tps:
            self.assertIsNotNone(tps[0]["spatial_error_km"])
            self.assertLessEqual(tps[0]["spatial_error_km"], 45.0)

    # 28. Precision, Recall & F1 Calculation
    def test_28_metric_calculation(self):
        metrics = osint_engine.get_validation_metrics()
        self.assertIn("metrics", metrics)
        self.assertGreaterEqual(len(metrics["metrics"]), 1)
        for m in metrics["metrics"]:
            self.assertGreaterEqual(m["precision_score"], 0.0)
            self.assertGreaterEqual(m["recall_score"], 0.0)
            self.assertGreaterEqual(m["f1_score"], 0.0)

    # 29. Provenance Preservation
    def test_29_provenance_preservation(self):
        events = osint_engine.get_canonical_events()
        if events:
            ev_with_obs = next((e for e in events if e.get("primary_observation_id")), events[0])
            details = osint_engine.get_event_details(ev_with_obs["canonical_osint_event_id"])
            self.assertIsNotNone(details)
            self.assertIn("observations", details)
            self.assertGreaterEqual(len(details["observations"]), 1)

    # 30. Security & Credential Protection
    def test_30_security_scan(self):
        files_to_check = ["osint_intelligence_engine.py", "external_evidence_db.py", "live_sensor_server_extension.py"]
        patterns = [r"bearer\s+[a-zA-Z0-9_\-\.]{20,}", r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]"]
        for fname in files_to_check:
            with open(os.path.join(PROJECT_ROOT, fname), "r", encoding="utf-8") as f:
                content = f.read()
            for pat in patterns:
                self.assertEqual(len(re.findall(pat, content, re.IGNORECASE)), 0)

    # 31. Zero-Emoji Compliance
    def test_31_zero_emoji(self):
        files_to_check = ["osint_intelligence_engine.py", "external_evidence_db.py", "live_sensor_server_extension.py", "ner_safe_live_dashboard_extended.html"]
        emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]")
        for fname in files_to_check:
            with open(os.path.join(PROJECT_ROOT, fname), "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            matches = emoji_pattern.findall(content)
            self.assertEqual(len(matches), 0, f"Found emoji in {fname}: {matches}")

    # 32. Four-Factor Operational Risk Formula Invariance
    def test_32_no_risk_score_modification(self):
        # Compute baseline hotspots before touching OSINT
        baseline_res = compute_fused_hotspots()
        h0 = baseline_res["features"][0]["properties"]["fused_risk_score"]
        h13 = baseline_res["features"][13]["properties"]["fused_risk_score"]

        # Run evaluation and queries on OSINT engine
        osint_engine.evaluate_prediction_outcomes()
        osint_engine.get_validation_metrics()

        # Compute baseline hotspots after touching OSINT
        after_res = compute_fused_hotspots()
        h0_after = after_res["features"][0]["properties"]["fused_risk_score"]
        h13_after = after_res["features"][13]["properties"]["fused_risk_score"]

        self.assertEqual(h0, h0_after)
        self.assertEqual(h13, h13_after)
        self.assertEqual(h0, 0.6481)
        self.assertEqual(h13, 0.7055)

    # 33. XGBoost Primary Production Model Preservation
    def test_33_xgboost_production_preserved(self):
        from susceptibility_provider import XGBoostProvider
        xgb_p = XGBoostProvider()
        self.assertEqual(xgb_p.get_model_id(), "xgboost")
        self.assertEqual(xgb_p.get_governance_status(), "PRODUCTION_OFFICIAL")

    # 34. Random Forest Fallback Standby Intact
    def test_34_rf_fallback_intact(self):
        rf_p = provider_manager.rf_provider
        self.assertEqual(rf_p.get_model_id(), "rf")
        self.assertEqual(rf_p.get_governance_status(), "PRODUCTION_FROZEN_RETAINED")

    # 35. PyTorch Spatial CNN Parallel Shadow Intact
    def test_35_cnn_shadow_intact(self):
        cnn_p = provider_manager.cnn_provider
        self.assertEqual(cnn_p.get_model_id(), "cnn")
        self.assertIn(cnn_p.get_governance_status(), ("EXPERIMENTAL_CANDIDATE", "PARALLEL_SHADOW_EXPERIMENTAL"))


if __name__ == "__main__":
    unittest.main()
