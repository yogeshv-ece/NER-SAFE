"""
NER-SAFE: Judge Demonstration Reproducibility & Mode Separation Automated Verification Suite
Problem Statement: SIH 26001 (AI-Based Early Warning and Landslide Risk Monitoring System in NER)

Verifies the 16+ core requirements for the Final Demo Readiness / Judge Demonstration:
1. Deterministic demo score (EVT-MEG-001 = 0.7055)
2. Deterministic demo classification (CRITICAL)
3. Explicit DEMO / REPLAY mode identity
4. Explicit LOCAL REPLAY data source identity
5. Authentic historical observation timestamp preserved (2024-05-28T06:00:00Z)
6. Distinct replay execution timestamp (replay_generated_time != observation_time)
7. Operational current risk remains unavailable when qualifying fresh data absent
8. Demo risk score does not masquerade as operational current risk
9. EVT-MEG-001 hotspot correctly identified (Shella, East Khasi Hills, Meghalaya)
10. Expected D8 flow path & empirical runout metadata verified (267.4m path, 73.0m drop, 29264.6 m^2)
11. Expected infrastructure consequence metadata verified (2 road assets, 208.4m exposed)
12. CAP advisory context clearly marked DEMO / LOCAL TEST (zero broadcast delivery claimed)
13. Citizen report marked as supporting qualitative evidence isolated from ML
14. Demo execution strictly does NOT trigger ML retraining (model_retraining_triggered == False)
15. Strict Zero-Emoji compliance in ner_safe_live_dashboard.html
16. REST API mode separation verified (/api/assessment/current, /api/assessment/demo, /api/assessment/pipeline)
17. Four-factor operational fusion weights locked (0.40, 0.30, 0.20, 0.10)
18. Scientific disclaimers on No-InSAR and No-Exact-Trajectory strictly verified
19. Immutability of protected baseline artifacts (event_records.csv invariant at 13009 bytes)
"""

import os
import sys
import json
import re
import threading
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

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

def run_reproducibility_checks() -> int:
    global total_checks, passed_checks, failed_checks
    total_checks = 0
    passed_checks = 0
    failed_checks = 0

    print("=" * 80)
    print("NER-SAFE: JUDGE DEMONSTRATION REPRODUCIBILITY & AUDIT TEST SUITE")
    print("=" * 80)

    from e2e_demo_engine import e2e_demo_engine

    # -----------------------------------------------------------------------------
    # 1. Clean-Start Reproducibility & In-Memory Mode Separation
    # -----------------------------------------------------------------------------
    print("\n--- 1. Clean-Start Reproducibility & Mode Separation ---")
    op_assess = e2e_demo_engine.run_operational_assessment()

    check(op_assess.get("assessment_mode") == "OPERATIONAL", "Operational assessment explicitly tagged 'OPERATIONAL'")
    check(op_assess.get("assessment_status") == "NOT_AVAILABLE", "Operational status is 'NOT_AVAILABLE' when fresh inputs absent")
    check(op_assess.get("current_risk_available") is False, "current_risk_available is strictly False")
    check(op_assess.get("reason") == "No qualifying fresh observations", "Rejection reason explicitly states 'No qualifying fresh observations'")
    check("last_known_assessment" in op_assess, "Last known historical baseline preserved separately for reference")
    check(op_assess.get("last_known_assessment", {}).get("historical_baseline_score") == 0.7055, "Historical baseline score matches 0.7055")
    check("disclaimer" in op_assess and "never present a previous risk score as the current" in op_assess["disclaimer"],
          "Operational mode includes explicit disclaimer prohibiting historical reuse as current risk")

    # -----------------------------------------------------------------------------
    # 2. Deterministic Demo / Replay Execution
    # -----------------------------------------------------------------------------
    print("\n--- 2. Deterministic Demo / Replay Execution ---")
    demo_assess = e2e_demo_engine.run_demo_assessment(hotspot_id="EVT-MEG-001", step=0)

    check(demo_assess.get("assessment_mode") == "DEMO_REPLAY", "Demo assessment explicitly tagged 'DEMO_REPLAY'")
    check(demo_assess.get("data_source") == "LOCAL_REPLAY", "Data source explicitly tagged 'LOCAL_REPLAY'")
    check(demo_assess.get("risk_score") == 0.7055, f"Deterministic demo fused risk score is 0.7055 (Got: {demo_assess.get('risk_score')})")
    check(demo_assess.get("risk_tier") == "CRITICAL", f"Deterministic demo risk tier is CRITICAL (Got: {demo_assess.get('risk_tier')})")
    check(demo_assess.get("hotspot_id") == "EVT-MEG-001", "Demo targets hotspot EVT-MEG-001")

    # -----------------------------------------------------------------------------
    # 3. Timestamp Decoupling & Integrity
    # -----------------------------------------------------------------------------
    print("\n--- 3. Timestamp Decoupling & Integrity ---")
    obs_time = demo_assess.get("replay_observation_time")
    gen_time = demo_assess.get("replay_generated_time")

    check(obs_time == "2024-05-28T06:00:00Z", f"Authentic historical observation timestamp preserved: {obs_time}")
    check(gen_time is not None and gen_time != obs_time, f"Replay execution timestamp distinct from observation timestamp: {gen_time}")
    check("disclaimer" in demo_assess and "Does not represent current live conditions" in demo_assess["disclaimer"],
          "Demo response carries explicit non-operational disclaimer")

    # -----------------------------------------------------------------------------
    # 4. End-to-End Pipeline Stages & Fusion Formula Verification
    # -----------------------------------------------------------------------------
    print("\n--- 4. Pipeline Stages & Four-Factor Fusion Formula ---")
    stages = demo_assess.get("pipeline_stages", [])
    check(len(stages) == 7, f"Pipeline includes all 7 formal demonstration stages (Found: {len(stages)})")

    stage_names = [s.get("stage_name") for s in stages]
    expected_stages = [
        "OBSERVATION_INGESTION_AND_QC",
        "FEATURE_EXTRACTION",
        "FOUR_FACTOR_RISK_FUSION",
        "HOTSPOT_QUALIFICATION",
        "RUNOUT_AND_EXPOSURE_COUPLING",
        "CAP_ADVISORY_DISPATCH",
        "CITIZEN_OBSERVATION_VERIFICATION"
    ]
    check(stage_names == expected_stages, "All 7 demonstration stages present in exact logical order")

    fusion_stg = next(s for s in stages if s.get("stage_name") == "FOUR_FACTOR_RISK_FUSION")
    weights = fusion_stg.get("weights", {})
    check(weights.get("susceptibility") == 0.40, "Weight 1 (Susceptibility) strictly locked at 0.40")
    check(weights.get("rainfall") == 0.30, "Weight 2 (Rainfall Anomaly) strictly locked at 0.30")
    check(weights.get("soil_moisture") == 0.20, "Weight 3 (Soil Moisture Anomaly) strictly locked at 0.20")
    check(weights.get("satellite") == 0.10, "Weight 4 (Satellite Change) strictly locked at 0.10")

    # -----------------------------------------------------------------------------
    # 5. Hotspot & C11 Consequence Coupling (D8 Flow Paths, Runout, Exposure)
    # -----------------------------------------------------------------------------
    print("\n--- 5. Hotspot & C11 Consequence Coupling ---")
    hotspot_stg = next(s for s in stages if s.get("stage_name") == "HOTSPOT_QUALIFICATION")
    check(hotspot_stg.get("state") == "Meghalaya", "Hotspot state verified as Meghalaya")
    check(hotspot_stg.get("district") == "East Khasi Hills", "Hotspot district verified as East Khasi Hills")
    check(hotspot_stg.get("nearest_settlement") == "Shella", "Hotspot nearest settlement verified as Shella")
    check(hotspot_stg.get("qualifies_for_runout") is True, "EVT-MEG-001 qualifies for runout analysis")

    consequence_stg = next(s for s in stages if s.get("stage_name") == "RUNOUT_AND_EXPOSURE_COUPLING")
    fp = consequence_stg.get("flow_path", {})
    check(fp.get("path_length_m") == 267.4, f"D8 flow path length verified at 267.4 m (Got: {fp.get('path_length_m')})")
    check(fp.get("elevation_drop_m") == 73.0, f"Flow path elevation drop verified at 73.0 m (Got: {fp.get('elevation_drop_m')})")
    check("disclaimer" in fp and "predicted flow path" in fp["disclaimer"].lower(),
          "Flow path disclaimer verified: describes predicted flow path, not exact future trajectory")

    rc = consequence_stg.get("runout_corridor", {})
    check(rc.get("runout_area_m2") == 29264.6, f"Runout corridor area verified at 29264.6 m^2 (Got: {rc.get('runout_area_m2')})")

    exp = consequence_stg.get("exposed_infrastructure", {})
    check(exp.get("roads_exposed_count") == 2, f"Exposed road asset count verified as 2 (Got: {exp.get('roads_exposed_count')})")
    check(exp.get("roads_exposed_length_m") == 208.4, f"Exposed road length verified as 208.4 m (Got: {exp.get('roads_exposed_length_m')})")

    # -----------------------------------------------------------------------------
    # 6. CAP Advisory (C12) & Citizen Observation (C13) Safeguards
    # -----------------------------------------------------------------------------
    print("\n--- 6. CAP Advisory & Citizen Observation Safeguards ---")
    adv_stg = next(s for s in stages if s.get("stage_name") == "CAP_ADVISORY_DISPATCH")
    check(adv_stg.get("notification_status") == "DEMO / LOCAL TEST", "Advisory status explicitly labeled 'DEMO / LOCAL TEST'")
    check("delivery_notice" in adv_stg and "Zero real SMS" in adv_stg["delivery_notice"],
          "Advisory delivery notice strictly denies real SMS or SACHET broadcast delivery")

    cit_stg = next(s for s in stages if s.get("stage_name") == "CITIZEN_OBSERVATION_VERIFICATION")
    gr = cit_stg.get("ground_report", {})
    check(bool(gr.get("report_id")), f"Citizen ground report cataloged: {gr.get('report_id')}")
    check(gr.get("model_retraining_triggered") is False, "Citizen report model_retraining_triggered is strictly False")
    check("scientific_safeguard" in gr and "strictly do NOT retrain" in gr["scientific_safeguard"],
          "Scientific safeguard verified: Citizen reports are observational evidence and strictly isolated from ML retraining")

    # -----------------------------------------------------------------------------
    # 7. Scientific Claims & Technical Limitation Disclaimers
    # -----------------------------------------------------------------------------
    print("\n--- 7. Scientific Claims & Limitation Disclaimers ---")
    obs_stg = next(s for s in stages if s.get("stage_name") == "OBSERVATION_INGESTION_AND_QC")
    inputs = obs_stg.get("inputs_cataloged", [])
    s1_input = next(i for i in inputs if i.get("source") == "SENTINEL1_C_SAR")
    check("disclaimer" in s1_input and "does not perform InSAR displacement measurement" in s1_input["disclaimer"],
          "Sentinel-1 SAR disclaimer verified: strictly denies InSAR displacement measurement")

    # -----------------------------------------------------------------------------
    # 8. UX4G Zero-Emoji Compliance
    # -----------------------------------------------------------------------------
    print("\n--- 8. UX4G Zero-Emoji Compliance ---")
    dash_path = os.path.join(WORKSPACE, "ner_safe_live_dashboard.html")
    with open(dash_path, "r", encoding="utf-8") as f:
        dash_html = f.read()

    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    emojis_found = emoji_pattern.findall(dash_html)
    check(len(emojis_found) == 0, f"ner_safe_live_dashboard.html strictly complies with Zero-Emoji rule (Emojis found: {len(emojis_found)})")
    check("e2eDemoWorkflowCard" in dash_html,
          "Live dashboard contains dedicated E2E Demonstration Workflow Card (#e2eDemoWorkflowCard)")

    # -----------------------------------------------------------------------------
    # 9. Protected Baseline File Immutability
    # -----------------------------------------------------------------------------
    print("\n--- 9. Protected Baseline File Immutability ---")
    c11_csv = os.path.join(WORKSPACE, "event_records.csv")
    check(os.path.exists(c11_csv), "Root event_records.csv exists")
    check(os.path.getsize(c11_csv) == 13009, f"event_records.csv size strictly invariant (Expected: 13009, Got: {os.path.getsize(c11_csv)})")

    # -----------------------------------------------------------------------------
    # 10. Live HTTP Server REST API Mode Separation
    # -----------------------------------------------------------------------------
    print("\n--- 10. Live Server REST API Mode Separation Endpoints ---")
    import server

    TEST_PORT = 8023
    httpd = server.start_server(TEST_PORT)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.4)
    base_url = f"http://127.0.0.1:{TEST_PORT}"

    try:
        # 1. /api/assessment/current
        r_curr = requests.get(f"{base_url}/api/assessment/current", timeout=5)
        check(r_curr.status_code == 200, "GET /api/assessment/current returned 200 OK")
        d_curr = r_curr.json()
        check(d_curr.get("assessment_mode") == "OPERATIONAL", "API /api/assessment/current reports mode 'OPERATIONAL'")
        check(d_curr.get("current_risk_available") is False, "API /api/assessment/current reports current_risk_available is False")
        check(d_curr.get("reason") == "No qualifying fresh observations", "API reports honest rejection reason")

        # 2. /api/assessment/demo
        r_demo = requests.get(f"{base_url}/api/assessment/demo?hotspot_id=EVT-MEG-001", timeout=5)
        check(r_demo.status_code == 200, "GET /api/assessment/demo returned 200 OK")
        d_demo = r_demo.json()
        check(d_demo.get("assessment_mode") == "DEMO_REPLAY", "API /api/assessment/demo reports mode 'DEMO_REPLAY'")
        check(d_demo.get("data_source") == "LOCAL_REPLAY", "API /api/assessment/demo reports data_source 'LOCAL_REPLAY'")
        check(d_demo.get("risk_score") == 0.7055, "API /api/assessment/demo returns deterministic score 0.7055")
        check(d_demo.get("risk_tier") == "CRITICAL", "API /api/assessment/demo returns deterministic tier CRITICAL")

        # 3. /api/assessment/pipeline
        r_pipe = requests.get(f"{base_url}/api/assessment/pipeline?hotspot_id=EVT-MEG-001", timeout=5)
        check(r_pipe.status_code == 200, "GET /api/assessment/pipeline returned 200 OK")
        d_pipe = r_pipe.json()
        check(len(d_pipe.get("pipeline_stages", [])) == 7, "API /api/assessment/pipeline returns all 7 demonstration stages")
        check(d_pipe.get("complete_chain_verified") is True, "API /api/assessment/pipeline reports complete_chain_verified is True")

    finally:
        httpd.shutdown()

    # -----------------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"JUDGE DEMO REPRODUCIBILITY SUITE SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 80)

    if failed_checks == 0:
        print("ALL CHECKS PASSED PERFECTLY!")
    else:
        print(f"WARNING: {failed_checks} CHECKS FAILED.")
    return failed_checks


class TestJudgeDemoReproducibility(unittest.TestCase):
    def test_judge_demo_reproducibility(self):
        failed = run_reproducibility_checks()
        self.assertEqual(failed, 0, f"TestJudgeDemoReproducibility detected {failed} check failures.")


if __name__ == "__main__":
    failed = run_reproducibility_checks()
    sys.exit(0 if failed == 0 else 1)
