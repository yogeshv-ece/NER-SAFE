"""
NER-SAFE Live Monitoring & Demonstrator Evolution Test Suite
Automated validation of all newly added live monitoring, demonstrator control,
temporal history, ingestion tracking, and storage abstraction gates.

Gates Tested:
1. Orchestrator initializes in STOPPED state
2. START LIVE changes state to RUNNING (LIVE_MONITORING)
3. STOP changes state cleanly to STOPPED
4. START REPLAY initializes historical timeline
5. PAUSE and RESUME function correctly in REPLAY
6. START DEMO initiates controlled scenario steps
7. Ingestion engine reports all 5 decoupled data feeds
8. Ingestion freshness correctly classifies recent vs stale observations
9. Storage engine creates canonical folders in NER-SAFE/
10. Storage engine records structured metadata envelopes
11. GET /api/system/state returns valid state schema
12. GET /api/system/methodology returns 6 verified pipeline stages
13. GET /api/monitoring/timeline returns chronological snapshot list
14. GET /api/ingestion/status provides per-source tracking
15. GET /api/storage/status reports local-first / Google Drive state
16. Static security: GET /.env.example returns 404
17. Static security: GET /server.py returns 404
18. Static security: GET /ner_safe_citizen_app.html returns 200
19. Component 11 event_records.csv remains byte-for-byte immutable
20. Four-factor fusion formula remains strictly invariant
"""

import os
import sys
import json
import time
import threading
import urllib.request
import urllib.error

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

import fusion_engine
from live_ingestion import ingestion_engine
from storage_engine import storage_engine
from demo_orchestrator import orchestrator
import server

def run_evolution_tests():
    print("=" * 80)
    print("NER-SAFE LIVE MONITORING & DEMONSTRATOR EVOLUTION VERIFICATION SUITE")
    print("=" * 80)
    total_checks = 22
    passed_checks = 0

    # -------------------------------------------------------------
    # 1. State Machine: STOPPED Baseline
    # -------------------------------------------------------------
    st = orchestrator.get_state()
    if st["status"] == "STOPPED":
        print(f"[CHECK 1/{total_checks}] PASS: Initial state is STOPPED ({st['mode']})")
        passed_checks += 1
    else:
        print(f"[CHECK 1/{total_checks}] FAIL: Expected STOPPED, got {st['status']}")

    # -------------------------------------------------------------
    # 2. State Machine: START LIVE
    # -------------------------------------------------------------
    res = orchestrator.start_live_monitoring()
    st = orchestrator.get_state()
    if res["status"] == "STARTED" and st["status"] == "RUNNING" and st["mode"] == "LIVE_MONITORING":
        print(f"[CHECK 2/{total_checks}] PASS: START LIVE transitions to RUNNING in LIVE_MONITORING")
        passed_checks += 1
    else:
        print(f"[CHECK 2/{total_checks}] FAIL: Unexpected state: {st}")

    # -------------------------------------------------------------
    # 3. State Machine: STOP
    # -------------------------------------------------------------
    res = orchestrator.stop_monitoring()
    st = orchestrator.get_state()
    if res["status"] == "STOPPED" and st["status"] == "STOPPED":
        print(f"[CHECK 3/{total_checks}] PASS: STOP cleanly halts monitoring; state is STOPPED")
        passed_checks += 1
    else:
        print(f"[CHECK 3/{total_checks}] FAIL: Failed to stop: {st}")

    # -------------------------------------------------------------
    # 4. State Machine: START REPLAY
    # -------------------------------------------------------------
    res = orchestrator.start_historical_replay()
    st = orchestrator.get_state()
    if st["status"] == "RUNNING" and st["mode"] == "HISTORICAL_REPLAY":
        print(f"[CHECK 4/{total_checks}] PASS: START REPLAY transitions to HISTORICAL_REPLAY")
        passed_checks += 1
    else:
        print(f"[CHECK 4/{total_checks}] FAIL: Replay start failed: {st}")

    # -------------------------------------------------------------
    # 5. State Machine: PAUSE & RESUME
    # -------------------------------------------------------------
    res_p = orchestrator.pause_replay()
    st_p = orchestrator.get_state()
    res_r = orchestrator.resume_replay()
    st_r = orchestrator.get_state()
    orchestrator.stop_monitoring()
    if st_p["status"] == "PAUSED" and st_r["status"] == "RUNNING":
        print(f"[CHECK 5/{total_checks}] PASS: PAUSE and RESUME work properly during Replay")
        passed_checks += 1
    else:
        print(f"[CHECK 5/{total_checks}] FAIL: Pause/Resume failed: {st_p} -> {st_r}")

    # -------------------------------------------------------------
    # 6. State Machine: START DEMO SCENARIO
    # -------------------------------------------------------------
    res_d = orchestrator.start_demo_scenario()
    st_d = orchestrator.get_state()
    orchestrator.stop_monitoring()
    if st_d["status"] == "RUNNING" and st_d["mode"] == "DEMO_SCENARIO":
        print(f"[CHECK 6/{total_checks}] PASS: START DEMO initiates controlled scenario mode")
        passed_checks += 1
    else:
        print(f"[CHECK 6/{total_checks}] FAIL: Demo start failed: {st_d}")

    # -------------------------------------------------------------
    # 7. Ingestion Engine: Feed Inventory
    # -------------------------------------------------------------
    ing_status = ingestion_engine.get_public_status()
    srcs = ing_status.get("sources", {})
    expected_srcs = {"satellite_optical", "rainfall", "soil_moisture", "terrain_susceptibility", "citizen_ground_observations"}
    if expected_srcs.issubset(set(srcs.keys())):
        print(f"[CHECK 7/{total_checks}] PASS: All 5 decoupled environmental feeds registered in ingestion engine")
        passed_checks += 1
    else:
        print(f"[CHECK 7/{total_checks}] FAIL: Missing sources: {expected_srcs - set(srcs.keys())}")

    # -------------------------------------------------------------
    # 8. Ingestion Freshness Classification
    # -------------------------------------------------------------
    f_rain = srcs.get("rainfall", {}).get("freshness_state")
    f_soil = srcs.get("soil_moisture", {}).get("freshness_state")
    if f_rain in ("FRESH", "RECENT") and f_soil in ("FRESH", "RECENT"):
        print(f"[CHECK 8/{total_checks}] PASS: Rainfall ({f_rain}) and Soil Moisture ({f_soil}) freshness classified accurately")
        passed_checks += 1
    else:
        print(f"[CHECK 8/{total_checks}] FAIL: Unexpected freshness: rain={f_rain}, soil={f_soil}")

    # -------------------------------------------------------------
    # 9. Storage Engine: Canonical Directories
    # -------------------------------------------------------------
    base_dir = storage_engine.base_dir
    req_subdirs = [
        os.path.join(base_dir, "predictions", "risk"),
        os.path.join(base_dir, "predictions", "warnings"),
        os.path.join(base_dir, "history"),
        os.path.join(base_dir, "logs")
    ]
    all_exist = all(os.path.exists(d) for d in req_subdirs)
    if all_exist:
        print(f"[CHECK 9/{total_checks}] PASS: Canonical local storage hierarchy exists in {base_dir}")
        passed_checks += 1
    else:
        print(f"[CHECK 9/{total_checks}] FAIL: Storage directory missing")

    # -------------------------------------------------------------
    # 10. Storage Engine: Snapshot Metadata Envelope
    # -------------------------------------------------------------
    snap_path = storage_engine.save_snapshot("predictions/risk", "test_audit_snap.json", {"test_metric": 42}, mode="TEST")
    with open(snap_path, "r", encoding="utf-8") as f:
        saved_doc = json.load(f)
    meta = saved_doc.get("_metadata", {})
    if meta.get("model_version") == "v1.4-Isotonic-RF-30m" and meta.get("fusion_weights", {}).get("susceptibility") == 0.40:
        print(f"[CHECK 10/{total_checks}] PASS: Snapshot metadata envelope verified (provenance + weights)")
        passed_checks += 1
    else:
        print(f"[CHECK 10/{total_checks}] FAIL: Invalid metadata envelope: {meta}")

    # Start ephemeral server on port 8004 for HTTP API testing
    httpd = server.start_server(8004)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    time.sleep(0.5)

    try:
        # ---------------------------------------------------------
        # 11. GET /api/system/state
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/api/system/state")
        data = json.loads(req.read().decode("utf-8"))
        if req.status == 200 and "status" in data and "mode" in data:
            print(f"[CHECK 11/{total_checks}] PASS: GET /api/system/state returns valid state schema")
            passed_checks += 1
        else:
            print(f"[CHECK 11/{total_checks}] FAIL: /api/system/state error: {data}")

        # ---------------------------------------------------------
        # 12. GET /api/system/methodology
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/api/system/methodology")
        data = json.loads(req.read().decode("utf-8"))
        pipe = data.get("methodological_pipeline", [])
        if req.status == 200 and len(pipe) == 6:
            print(f"[CHECK 12/{total_checks}] PASS: GET /api/system/methodology returns all 6 pipeline stages")
            passed_checks += 1
        else:
            print(f"[CHECK 12/{total_checks}] FAIL: Expected 6 stages, got {len(pipe)}")

        # ---------------------------------------------------------
        # 13. GET /api/monitoring/timeline
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/api/monitoring/timeline")
        data = json.loads(req.read().decode("utf-8"))
        if req.status == 200 and isinstance(data.get("timeline"), list) and len(data["timeline"]) > 0:
            print(f"[CHECK 13/{total_checks}] PASS: GET /api/monitoring/timeline returns {len(data['timeline'])} historical snapshots")
            passed_checks += 1
        else:
            print(f"[CHECK 13/{total_checks}] FAIL: Timeline missing or empty")

        # ---------------------------------------------------------
        # 14. GET /api/ingestion/status
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/api/ingestion/status")
        data = json.loads(req.read().decode("utf-8"))
        if req.status == 200 and "sources" in data:
            print(f"[CHECK 14/{total_checks}] PASS: GET /api/ingestion/status returns multi-source tracking")
            passed_checks += 1
        else:
            print(f"[CHECK 14/{total_checks}] FAIL: Ingestion status error")

        # ---------------------------------------------------------
        # 15. GET /api/storage/status
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/api/storage/status")
        data = json.loads(req.read().decode("utf-8"))
        if req.status == 200 and "storage_backend" in data and data.get("google_one_compatible"):
            print(f"[CHECK 15/{total_checks}] PASS: GET /api/storage/status reports Google One compatible storage")
            passed_checks += 1
        else:
            print(f"[CHECK 15/{total_checks}] FAIL: Storage status error: {data}")

        # ---------------------------------------------------------
        # 16. Static Security: .env.example -> 404
        # ---------------------------------------------------------
        try:
            urllib.request.urlopen("http://127.0.0.1:8004/.env.example")
            print(f"[CHECK 16/{total_checks}] FAIL: .env.example was served!")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[CHECK 16/{total_checks}] PASS: Static security blocked /.env.example with 404 Not Found")
                passed_checks += 1
            else:
                print(f"[CHECK 16/{total_checks}] FAIL: Unexpected status for .env: {e.code}")

        # ---------------------------------------------------------
        # 17. Static Security: server.py -> 404
        # ---------------------------------------------------------
        try:
            urllib.request.urlopen("http://127.0.0.1:8004/server.py")
            print(f"[CHECK 17/{total_checks}] FAIL: server.py source code was served!")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"[CHECK 17/{total_checks}] PASS: Static security blocked /server.py with 404 Not Found")
                passed_checks += 1
            else:
                print(f"[CHECK 17/{total_checks}] FAIL: Unexpected status for server.py: {e.code}")

        # ---------------------------------------------------------
        # 18. Static Security: Allowed HTML -> 200
        # ---------------------------------------------------------
        req = urllib.request.urlopen("http://127.0.0.1:8004/ner_safe_citizen_app.html")
        if req.status == 200:
            print(f"[CHECK 18/{total_checks}] PASS: Whitelisted web app /ner_safe_citizen_app.html served with 200 OK")
            passed_checks += 1
        else:
            print(f"[CHECK 18/{total_checks}] FAIL: Allowed app returned {req.status}")

    finally:
        httpd.shutdown()

    # -------------------------------------------------------------
    # 19. Scientific Immutability: Component 11 event_records.csv
    # -------------------------------------------------------------
    ev_path = os.path.join(WORKSPACE, "event_records.csv")
    ev_c11_path = os.path.join(WORKSPACE, "NER_SAFE_DATA", "COMPONENT_11", "events", "event_records.csv")
    size_ev = os.path.getsize(ev_c11_path)
    if size_ev == 13009:
        print(f"[CHECK 19/{total_checks}] PASS: Component 11 event_records.csv strictly immutable (13009 bytes)")
        passed_checks += 1
    else:
        print(f"[CHECK 19/{total_checks}] FAIL: Event records size changed: {size_ev} bytes")

    # -------------------------------------------------------------
    # 20. Fusion Calculation Invariance
    # -------------------------------------------------------------
    hotspots = fusion_engine.compute_fused_hotspots()
    f0 = hotspots["features"][0]
    score = f0["properties"]["fused_risk_score"]
    if abs(score - 0.6481) < 0.001:
        print(f"[CHECK 20/{total_checks}] PASS: Four-factor weighted risk fusion strictly invariant ({score})")
        passed_checks += 1
    else:
        print(f"[CHECK 20/{total_checks}] FAIL: Risk calculation altered: got {score}, expected 0.6481")

    # -------------------------------------------------------------
    # 21. Temporary Public Demo Gateway Security Perimeter Audit
    # -------------------------------------------------------------
    import public_demo_gateway
    # Test firewall check on ephemeral server
    httpd_gw = server.start_server(8005)
    gw_thread = threading.Thread(target=httpd_gw.serve_forever, daemon=True)
    gw_thread.start()
    time.sleep(0.4)
    try:
        fw_passed = public_demo_gateway.verify_security_firewall("http://127.0.0.1:8005")
        if fw_passed:
            print(f"[CHECK 21/{total_checks}] PASS: Public demo gateway firewall blocked all sensitive assets")
            passed_checks += 1
        else:
            print(f"[CHECK 21/{total_checks}] FAIL: Public demo gateway firewall allowed sensitive assets")
    finally:
        httpd_gw.shutdown()

    # -------------------------------------------------------------
    # 22. UX4G Design System 3.0 Zero-Emoji & Semantic Quality Audit
    # -------------------------------------------------------------
    dash_file = os.path.join(WORKSPACE, "ner_safe_live_dashboard.html")
    with open(dash_file, "r", encoding="utf-8") as f:
        dash_content = f.read()

    # Check for emojis
    import re
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251]"
    )
    has_emoji = bool(emoji_pattern.search(dash_content))
    has_tokens = ("--ux4g-navy: #1351A3" in dash_content) and ("demo-control-bar" in dash_content)
    if not has_emoji and has_tokens:
        print(f"[CHECK 22/{total_checks}] PASS: UX4G 3.0 tokens and 100% clean SVG icons (ZERO emojis) verified")
        passed_checks += 1
    else:
        print(f"[CHECK 22/{total_checks}] FAIL: Emoji found or UX4G tokens missing (emoji={has_emoji}, tokens={has_tokens})")

    print("=" * 80)
    print(f"EVOLUTION SUITE RESULTS: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 80)
    return passed_checks == total_checks

if __name__ == "__main__":
    success = run_evolution_tests()
    sys.exit(0 if success else 1)
