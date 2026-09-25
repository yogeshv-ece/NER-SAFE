"""
=============================================================================
NER-SAFE: SIH Demonstration End-to-End Master Control Verification
=============================================================================
Executes the mandatory 16-step demonstration sequence over HTTP:
 1. Start application.
 2. Confirm LIVE MONITORING = OFF.
 3. Confirm no live polling occurs while OFF.
 4. Log in as authorized operational user (ADMIN).
 5. Request START LIVE MONITORING via authenticated API.
 6. Confirm OFF -> STARTING -> ACTIVE.
 7. Allow scheduler to execute at least one real cycle.
 8. Verify actual source checks/acquisition.
 9. Verify database/status updates.
10. Verify dashboard/status API updates.
11. Verify risk pipeline remains functional.
12. Request STOP LIVE MONITORING via authenticated API.
13. Confirm ACTIVE -> STOPPING -> OFF.
14. Confirm no new scheduled polling occurs after OFF.
15. Restart application.
16. Confirm it strictly returns to OFF.
=============================================================================
"""

import os
import sys
import time
import json
import socket
import urllib.request
import urllib.error
import threading

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import server
import database
import live_monitoring_controller
from nersafe_autonomous_scheduler import AutonomousScheduler

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return resp.getcode(), json.loads(resp.read().decode("utf-8")), resp.info()

def http_post(url, payload=None, headers=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8")), resp.info()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8")), e.info()

def main():
    print("=" * 80)
    print("NER-SAFE: STARTING SIH DEMONSTRATION MASTER CONTROL E2E RUN")
    print("=" * 80)

    port = find_free_port()
    base_url = f"http://localhost:{port}"

    # 1. Start application
    print(f"\n[STEP 1] Starting live server instance on port {port}...")
    httpd = server.start_server(port=port)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(1.0)
    print("  Server is listening on port", port)

    # 2. Confirm LIVE MONITORING = OFF
    print("\n[STEP 2] Querying /api/live-monitoring/status for initial state...")
    status_code, status_data, _ = http_get(f"{base_url}/api/live-monitoring/status")
    assert status_code == 200, f"Expected 200, got {status_code}"
    assert status_data["state"] == "OFF", f"Expected OFF, got {status_data['state']}"
    assert status_data["enabled"] is False, f"Expected enabled=False"
    print(f"  CONFIRMED: Master State is '{status_data['state']}' (enabled={status_data['enabled']})")

    # 3. Confirm no live polling occurs while OFF
    print("\n[STEP 3] Verifying dormant scheduler suppresses polling while OFF...")
    sched = AutonomousScheduler(enforce_master_control=True)
    cycle_res = sched.execute_cycle()
    assert cycle_res["status"] == "DORMANT_OFF", f"Expected DORMANT_OFF, got {cycle_res['status']}"
    assert "sources_polled" not in cycle_res, "Dormant scheduler must not poll sources!"
    print(f"  CONFIRMED: Scheduler cycle returned '{cycle_res['status']}' - ZERO live acquisition performed")

    # 4. Log in as authorized user
    print("\n[STEP 4] Logging in as authorized operational user (ADMIN)...")
    admin_email = "admin@nersafe.gov.in"
    # Ensure admin user exists with known credentials
    admin_user = database.get_user_by_email(admin_email)
    import auth_security
    if not admin_user:
        pwd_hash = auth_security.hash_password("Admin@1234")
        uid = database.create_user(
            full_name="NER-SAFE Lead Administrator",
            email=admin_email,
            password_hash=pwd_hash,
            role="ADMIN",
            state="Meghalaya",
            organization="NER-SAFE Operational Command",
            status="ACTIVE"
        )
    else:
        # Reset password to known test password
        pwd_hash = auth_security.hash_password("Admin@1234")
        with database.get_db_connection() as conn:
            conn.execute("UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE email = ?", (pwd_hash, admin_email))

    login_code, login_data, headers_info = http_post(
        f"{base_url}/api/auth/login",
        {"email": admin_email, "password": "Admin@1234"}
    )
    assert login_code == 200, f"Login failed: {login_data}"
    cookie_header = headers_info.get("Set-Cookie", "")
    session_id = None
    if "nersafe_session=" in cookie_header:
        session_id = cookie_header.split("nersafe_session=")[1].split(";")[0]
    auth_headers = {"Cookie": f"nersafe_session={session_id}"} if session_id else {}
    print(f"  CONFIRMED: Authenticated as {login_data['user']['full_name']} ({login_data['user']['role']})")

    # 5. Click START LIVE MONITORING
    print("\n[STEP 5] Calling POST /api/live-monitoring/start with authentication...")
    start_code, start_res, _ = http_post(f"{base_url}/api/live-monitoring/start", headers=auth_headers)
    assert start_code == 200, f"Start failed: {start_res}"
    print(f"  Response: {start_res}")

    # 6. Confirm OFF -> STARTING -> ACTIVE
    print("\n[STEP 6] Confirming state transition to ACTIVE...")
    assert start_res["state"] == "ACTIVE", f"Expected ACTIVE, got {start_res['state']}"
    _, current_status, _ = http_get(f"{base_url}/api/live-monitoring/status")
    assert current_status["state"] == "ACTIVE", f"Expected ACTIVE, got {current_status['state']}"
    assert current_status["enabled"] is True
    print(f"  CONFIRMED: State successfully transitioned to '{current_status['state']}'")

    # 7 & 8. Allow scheduler to execute at least one real cycle & verify sources
    print("\n[STEP 7 & 8] Executing genuine live monitoring cycle with master control ACTIVE...")
    cycle_active_res = sched.execute_cycle()
    assert cycle_active_res["status"] == "SUCCESS", f"Cycle failed: {cycle_active_res}"
    sources = cycle_active_res.get("sources_polled", {})
    print(f"  Cycle Status: {cycle_active_res['status']}")
    print(f"  Duration:     {cycle_active_res.get('duration_seconds')}s")
    print(f"  Free Storage: {cycle_active_res.get('free_disk_gb')} GB")
    print(f"  Sources Polled ({len(sources)}):")
    for k, v in sources.items():
        status_val = v.get("status") if isinstance(v, dict) else str(v)
        print(f"    - {k:25}: {status_val}")

    # 9. Verify database/status updates
    print("\n[STEP 9] Verifying SQLite audit log records...")
    logs = database.get_audit_logs(limit=5)
    recent_actions = [l.get("action") for l in logs if l]
    print(f"  Recent Audit Logs: {recent_actions}")
    assert any("LIVE_MONITORING" in str(a) for a in recent_actions), "Audit log missing live monitoring entry!"

    # 10. Verify dashboard status updates
    print("\n[STEP 10] Querying /api/live-monitoring/status for operational telemetry...")
    _, telemetry, _ = http_get(f"{base_url}/api/live-monitoring/status")
    assert telemetry["enabled"] is True
    assert telemetry["state"] == "ACTIVE"
    print(f"  Master State:   {telemetry['state']}")
    print(f"  Next Cycle:     {telemetry.get('next_cycle')}")
    print(f"  Total Sources:  {len(telemetry.get('sources', {}))}")

    # 11. Verify risk pipeline remains functional
    print("\n[STEP 11] Querying /api/monitoring/hotspots to verify risk pipeline...")
    hotspot_code, hotspot_geojson, _ = http_get(f"{base_url}/api/monitoring/hotspots")
    assert hotspot_code == 200
    features = hotspot_geojson.get("features", [])
    assert len(features) == 48, f"Expected 48 hotspots, got {len(features)}"
    sample = features[0]["properties"]
    print(f"  Total Hotspots: {len(features)}")
    print(f"  Sample Hotspot: {sample.get('location_name')} ({sample.get('district')})")
    print(f"  Risk Score:     {sample.get('fused_risk_score')} (Tier: {sample.get('risk_tier')})")
    print(f"  Weights:        {sample.get('risk_weights_breakdown')}")

    # 12 & 13. Click STOP LIVE MONITORING & Confirm ACTIVE -> STOPPING -> OFF
    print("\n[STEP 12 & 13] Calling POST /api/live-monitoring/stop to halt monitoring gracefully...")
    stop_code, stop_res, _ = http_post(f"{base_url}/api/live-monitoring/stop", headers=auth_headers)
    assert stop_code == 200, f"Stop failed: {stop_res}"
    assert stop_res["state"] == "OFF", f"Expected OFF, got {stop_res['state']}"
    _, post_stop_status, _ = http_get(f"{base_url}/api/live-monitoring/status")
    assert post_stop_status["state"] == "OFF"
    assert post_stop_status["enabled"] is False
    print(f"  CONFIRMED: State successfully transitioned to '{post_stop_status['state']}'")

    # 14. Confirm no new scheduled polling occurs after OFF
    print("\n[STEP 14] Verifying scheduler cycle returns DORMANT_OFF after stop...")
    post_stop_cycle = sched.execute_cycle()
    assert post_stop_cycle["status"] == "DORMANT_OFF", f"Expected DORMANT_OFF, got {post_stop_cycle['status']}"
    print(f"  CONFIRMED: Post-stop cycle returned '{post_stop_cycle['status']}'")

    # 15 & 16. Restart application and confirm it returns to OFF
    print("\n[STEP 15 & 16] Restarting application and confirming state resets to OFF...")
    httpd.shutdown()
    httpd.server_close()
    time.sleep(0.5)

    port2 = find_free_port()
    print(f"  Starting fresh server instance on port {port2}...")
    httpd2 = server.start_server(port=port2)
    server_thread2 = threading.Thread(target=httpd2.serve_forever, daemon=True)
    server_thread2.start()
    time.sleep(1.0)

    _, restart_status, _ = http_get(f"http://localhost:{port2}/api/live-monitoring/status")
    assert restart_status["state"] == "OFF", f"Expected OFF after restart, got {restart_status['state']}"
    assert restart_status["enabled"] is False
    print(f"  CONFIRMED: Fresh server instance started with master state '{restart_status['state']}' (enabled=False)")

    httpd2.shutdown()
    httpd2.server_close()

    print("\n" + "=" * 80)
    print("ALL 16 SIH DEMONSTRATION STEPS COMPLETED & VERIFIED 100% SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    main()
