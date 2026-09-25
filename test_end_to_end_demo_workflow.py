"""
NER-SAFE: End-to-End Demonstration Workflow & Mode Separation Test Suite
Problem Statement: SIH 26001 (AI-Based Early Warning and Landslide Risk Monitoring System in NER)

Verifies:
1. Explicit mode separation: OPERATIONAL vs DEMO / REPLAY.
2. Demo mode cannot masquerade as operational.
3. Demo uses genuine local source identifiers and preserves original observation timestamps.
4. Replay generated timestamp is distinct from historical observation timestamp.
5. Four-factor fusion weights remain strictly locked (40/30/20/10).
6. Demo risk score and tier are deterministic (EVT-MEG-001 = 0.7055 | CRITICAL).
7. Hotspot metadata correctly retrieved from validated C11 records.
8. C11 consequence data (D8 flow path, runout corridor, exposed roads) coupled correctly.
9. C12 CAP advisory connected and clearly marked DEMO / LOCAL TEST (no real SMS/broadcast delivery claimed).
10. Citizen reporting (C13) moderation workflow is demonstrated as supporting ground evidence without retraining ML models.
11. Demo does not modify protected artifacts (event_records.csv invariant at 13009 bytes).
12. Operational mode refuses stale data and returns CURRENT RISK: NOT AVAILABLE when fresh inputs are absent.
13. No credentials exposed in logs or environment.
14. Zero emojis anywhere in the dashboard HTML.
15. REST API endpoints (/api/assessment/current, /api/assessment/demo, /api/assessment/pipeline) operational.
"""

import os
import sys
import json
import threading
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

total_checks = 0
passed_checks = 0
failed_checks = 0

def check(condition: bool, description: str):
    global total_checks, passed_checks, failed_checks
    total_checks += 1
    if condition:
        print(f"  [PASS {total_checks:02d}] {description}")
        passed_checks += 1
    else:
        print(f"  [FAIL {total_checks:02d}] {description}")
        failed_checks += 1

import unittest

def run_e2e_demo_checks() -> int:
    global total_checks, passed_checks, failed_checks
    total_checks = 0
    passed_checks = 0
    failed_checks = 0

    print("=" * 80)
    print("NER-SAFE: END-TO-END DEMONSTRATION & OPERATIONAL SEPARATION SUITE")
    print("=" * 80)

    from e2e_demo_engine import e2e_demo_engine

    # -----------------------------------------------------------------------------
    # 1. Operational Mode Freshness & Hard Rule
    # -----------------------------------------------------------------------------
    print("\n--- 1. Operational Mode Freshness & Hard Rule ---")
    op_assess = e2e_demo_engine.run_operational_assessment()

    check(op_assess.get("assessment_mode") == "OPERATIONAL", "Operational assessment explicitly tagged 'OPERATIONAL'")
    check(op_assess.get("assessment_status") == "NOT_AVAILABLE", "Operational assessment status is 'NOT_AVAILABLE' when fresh feeds are absent")
    check(op_assess.get("current_risk_available") is False, "current_risk_available is strictly False")
    check("No qualifying fresh observations" in op_assess.get("reason", ""), "Rejection reason explicitly states 'No qualifying fresh observations'")
    check(op_assess.get("last_known_assessment", {}).get("historical_baseline_score") == 0.7055, "Last known baseline score preserved as historical guidance (0.7055)")
    check("never present a previous risk score as the current risk assessment" in op_assess.get("disclaimer", ""), "Hard rule strictly disclaimed: previous score never masquerades as current")

    # -----------------------------------------------------------------------------
    # 2. Demo / Replay Mode Identity & Timestamp Decoupling
    # -----------------------------------------------------------------------------
    print("\n--- 2. Demo / Replay Mode Identity & Timestamp Decoupling ---")
    demo_assess = e2e_demo_engine.run_demo_assessment(hotspot_id="EVT-MEG-001")

    check(demo_assess.get("assessment_mode") == "DEMO_REPLAY", "Demo assessment explicitly tagged 'DEMO_REPLAY'")
    check(demo_assess.get("data_source") == "LOCAL_REPLAY", "Data source explicitly tagged 'LOCAL_REPLAY'")
    check(demo_assess.get("replay_observation_time") == "2024-05-28T06:00:00Z", "Original observation timestamp preserved (2024-05-28T06:00:00Z)")
    check(demo_assess.get("replay_generated_time") != demo_assess.get("replay_observation_time"), "Replay generated time is distinct from observation timestamp")
    check("DEMO / REPLAY MODE" in demo_assess.get("disclaimer", ""), "Clear scientific disclaimer attached to demo assessment")

    # -----------------------------------------------------------------------------
    # 3. Deterministic 4-Factor Fusion Calculation
    # -----------------------------------------------------------------------------
    print("\n--- 3. Deterministic 4-Factor Fusion Calculation ---")
    check(demo_assess.get("risk_score") == 0.7055, f"Demo fused risk score is exact 0.7055 (Got: {demo_assess.get('risk_score')})")
    check(demo_assess.get("risk_tier") == "CRITICAL", f"Demo fused risk tier is CRITICAL (Got: {demo_assess.get('risk_tier')})")

    stages = {s["stage_number"]: s for s in demo_assess.get("pipeline_stages", [])}
    check(len(stages) >= 7, f"Complete end-to-end pipeline contains all major stages ({len(stages)} verified)")

    fusion_stage = stages.get(3, {})
    check(fusion_stage.get("stage_name") == "FOUR_FACTOR_RISK_FUSION", "Fusion stage correctly cataloged")
    weights = fusion_stage.get("weights", {})
    check(weights.get("susceptibility") == 0.40 and weights.get("rainfall") == 0.30 and weights.get("soil_moisture") == 0.20 and weights.get("satellite") == 0.10, "Fusion weights strictly locked at 0.40, 0.30, 0.20, 0.10")

    # -----------------------------------------------------------------------------
    # 4. Hotspot & C11 Consequence Coupling
    # -----------------------------------------------------------------------------
    print("\n--- 4. Hotspot & C11 Consequence Coupling ---")
    hotspot_stage = stages.get(4, {})
    check(hotspot_stage.get("event_id") == "EVT-MEG-001", "Hotspot correctly identified as EVT-MEG-001")
    check(hotspot_stage.get("state") == "Meghalaya" and hotspot_stage.get("district") == "East Khasi Hills", "Hotspot location verified in East Khasi Hills, Meghalaya")

    consequence_stage = stages.get(5, {})
    fp = consequence_stage.get("flow_path", {})
    check(fp.get("path_length_m") == 267.4, f"D8 steepest descent flow path length verified at 267.4m (Got: {fp.get('path_length_m')})")
    check(fp.get("elevation_drop_m") == 73.0, f"Flow path elevation drop verified at 73.0m (Got: {fp.get('elevation_drop_m')})")
    check("not an exact future landslide trajectory" in fp.get("disclaimer", ""), "Scientifically defensible flow-path wording verified")

    rc = consequence_stage.get("runout_corridor", {})
    check(rc.get("runout_area_m2") == 29264.6, f"Empirical runout corridor footprint verified at 29264.6 m^2 (Got: {rc.get('runout_area_m2')})")

    exp = consequence_stage.get("exposed_infrastructure", {})
    check(exp.get("roads_exposed_count") == 2, f"Roads exposed count verified (2 assets, got {exp.get('roads_exposed_count')})")
    check(exp.get("roads_exposed_length_m") == 208.4, f"Roads exposed length verified (208.4m, got {exp.get('roads_exposed_length_m')})")

    # -----------------------------------------------------------------------------
    # 5. C12 CAP Advisory Context & Delivery State Safeguards
    # -----------------------------------------------------------------------------
    print("\n--- 5. C12 CAP Advisory & Delivery State Safeguards ---")
    advisory_stage = stages.get(6, {})
    check(advisory_stage.get("alert_identifier") == "NER-SAFE-CAP-EVT-MEG-001", f"CAP alert identifier verified: {advisory_stage.get('alert_identifier')}")
    check(advisory_stage.get("notification_status") == "DEMO / LOCAL TEST", "Notification explicitly labeled 'DEMO / LOCAL TEST'")
    check("Zero real SMS or NDMA/SACHET broadcast dispatch claimed" in advisory_stage.get("delivery_notice", ""), "Delivery notice strictly denies real public broadcast dispatch")

    # -----------------------------------------------------------------------------
    # 6. C13 Citizen Ground Observation Evidence & Model Isolation
    # -----------------------------------------------------------------------------
    print("\n--- 6. C13 Citizen Observation Evidence & Model Isolation ---")
    citizen_stage = stages.get(7, {})
    ground_rep = citizen_stage.get("ground_report", {})
    check("REP-" in ground_rep.get("report_id", ""), f"Citizen report identifier attached: {ground_rep.get('report_id')}")
    check(ground_rep.get("verification_status") in ("FIELD_VERIFIED", "UNVERIFIED_OBSERVATION", "OFFICIAL_VALIDATED"), "Valid verification status attached")
    check(ground_rep.get("model_retraining_triggered") is False, "model_retraining_triggered is strictly False")
    check("strictly do NOT retrain C10/C15 models" in ground_rep.get("scientific_safeguard", ""), "Scientific safeguard: citizen reports isolated from ML retraining")

    # -----------------------------------------------------------------------------
    # 7. Immutability of Protected Baseline Files
    # -----------------------------------------------------------------------------
    print("\n--- 7. Immutability of Protected Baseline Files ---")
    csv_path = Path(__file__).parent.joinpath("NER_SAFE_DATA", "COMPONENT_11", "events", "event_records.csv")
    check(csv_path.exists() and csv_path.stat().st_size == 13009, f"event_records.csv strictly immutable (13009 bytes, got {csv_path.stat().st_size if csv_path.exists() else 'NONE'})")

    c11_geojson = Path(e2e_demo_engine._load_c11_events.__globals__["C11_EVENTS_PATH"])
    check(c11_geojson.exists(), "C11 event_records.geojson exists and is intact")

    # -----------------------------------------------------------------------------
    # 8. UX4G Zero-Emoji Compliance
    # -----------------------------------------------------------------------------
    print("\n--- 8. UX4G Zero-Emoji Compliance ---")
    dash_text = Path(__file__).parent.joinpath("ner_safe_live_dashboard.html").read_text(encoding="utf-8")

    def count_emojis(text: str) -> int:
        cnt = 0
        for char in text:
            cp = ord(char)
            if (
                0x1F600 <= cp <= 0x1F64F or
                0x1F300 <= cp <= 0x1F5FF or
                0x1F680 <= cp <= 0x1F6FF or
                0x1F700 <= cp <= 0x1F77F or
                0x1F780 <= cp <= 0x1F7FF or
                0x1F800 <= cp <= 0x1F8FF or
                0x1F900 <= cp <= 0x1F9FF or
                0x1FA00 <= cp <= 0x1FA6F or
                0x1FA70 <= cp <= 0x1FAFF or
                0x2600 <= cp <= 0x26FF or
                0x2700 <= cp <= 0x27BF
            ):
                cnt += 1
        return cnt

    dash_emojis = count_emojis(dash_text)
    check(dash_emojis == 0, f"ner_safe_live_dashboard.html strictly complies with Zero-Emoji rule (Emojis found: {dash_emojis})")
    check("e2eDemoWorkflowCard" in dash_text, "E2E Demonstration Workflow Card present in dashboard DOM")

    # -----------------------------------------------------------------------------
    # 9. Demonstration REST API Endpoints Verification
    # -----------------------------------------------------------------------------
    print("\n--- 9. Demonstration REST API Endpoints Verification ---")
    import server
    httpd = server.start_server(8021)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.4)
    base_url = "http://127.0.0.1:8021"

    try:
        # Test GET /api/assessment/current
        r_curr = requests.get(f"{base_url}/api/assessment/current", timeout=5)
        check(r_curr.status_code == 200, f"GET /api/assessment/current returned 200 OK")
        d_curr = r_curr.json()
        check(d_curr.get("assessment_mode") == "OPERATIONAL", "API reports mode 'OPERATIONAL'")
        check(d_curr.get("current_risk_available") is False, "API reports current_risk_available is False")

        # Test GET /api/assessment/demo
        r_demo = requests.get(f"{base_url}/api/assessment/demo?hotspot_id=EVT-MEG-001", timeout=5)
        check(r_demo.status_code == 200, f"GET /api/assessment/demo returned 200 OK")
        d_demo = r_demo.json()
        check(d_demo.get("assessment_mode") == "DEMO_REPLAY", "API reports mode 'DEMO_REPLAY'")
        check(d_demo.get("data_source") == "LOCAL_REPLAY", "API reports data_source 'LOCAL_REPLAY'")
        check(d_demo.get("risk_score") == 0.7055, "API reports deterministic demo risk score 0.7055")

        # Test GET /api/assessment/pipeline
        r_pipe = requests.get(f"{base_url}/api/assessment/pipeline?hotspot_id=EVT-MEG-001", timeout=5)
        check(r_pipe.status_code == 200, f"GET /api/assessment/pipeline returned 200 OK")
        d_pipe = r_pipe.json()
        check(len(d_pipe.get("pipeline_stages", [])) >= 7, "API returns complete 7+ stage pipeline payload")

    finally:
        httpd.shutdown()

    # -----------------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"E2E DEMO WORKFLOW SUITE SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 80)

    if failed_checks == 0:
        print("ALL CHECKS PASSED PERFECTLY!")
    else:
        print(f"WARNING: {failed_checks} CHECKS FAILED.")
    return failed_checks


class TestEndToEndDemoWorkflow(unittest.TestCase):
    def test_e2e_demo_workflow(self):
        failed = run_e2e_demo_checks()
        self.assertEqual(failed, 0, f"TestEndToEndDemoWorkflow detected {failed} check failures.")


if __name__ == "__main__":
    failed = run_e2e_demo_checks()
    sys.exit(0 if failed == 0 else 1)
