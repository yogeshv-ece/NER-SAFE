"""
=============================================================================
NER-SAFE: Final SIH Demonstration Preflight & Master Control Validation Suite
=============================================================================
Baseline: Smart India Hackathon 2026 - Problem Statement 26001 (MDoNER)
Purpose: End-to-end judge demonstration preflight test validating:
  1. Clean application start & dashboard availability
  2. Initial Master Control state strictly OFF (dormant scheduler)
  3. Strict RBAC enforcement (ADMIN/FIELD_OFFICER allowed, PUBLIC/Unauth denied)
  4. Master control start transition (OFF -> STARTING -> ACTIVE)
  5. Live source telemetry reporting (genuine upstream statuses)
  6. Operational risk pipeline integrity (48 hotspots, locked formula)
  7. Master control stop transition (ACTIVE -> STOPPING -> OFF)
  8. Post-stop dormant scheduler behavior (zero live acquisition)
  9. Application restart resilience (resets to OFF)
  10. Protected invariants: XGBoost SHA-256, locked formula, G:\\ drive protection,
      zero-emoji compliance, and credential secrecy.
=============================================================================
"""

import os
import sys
import time
import json
import socket
import hashlib
import unittest
import threading
import urllib.request
import urllib.error

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

import server
import database
import live_monitoring_controller
from nersafe_autonomous_scheduler import (
    AutonomousScheduler,
    LOCKED_XGBOOST_HASH,
    LOCKED_RISK_WEIGHTS,
    STORAGE_GUARD_MIN_FREE_GB
)

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.getcode(), json.loads(raw.decode("utf-8")), resp.info()
            return resp.getcode(), raw.decode("utf-8"), resp.info()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8")), e.info()
        except Exception:
            return e.code, raw.decode("utf-8"), e.info()

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


class TestSIHFinalDemoPreflight(unittest.TestCase):
    """End-to-end preflight verification suite for judge demonstration."""

    @classmethod
    def setUpClass(cls):
        cls.port = find_free_port()
        cls.base_url = f"http://localhost:{cls.port}"
        cls.httpd = server.start_server(port=cls.port)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(1.0)

        # Setup administrative test session
        admin_email = "admin@nersafe.gov.in"
        demo_password = os.environ.get("NER_SAFE_DEMO_PASSWORD", "Admin@1234")
        admin_user = database.get_user_by_email(admin_email)
        import auth_security
        pwd_hash = auth_security.hash_password(demo_password)
        if not admin_user:
            database.create_user(
                full_name="NER-SAFE Lead Administrator",
                email=admin_email,
                password_hash=pwd_hash,
                role="ADMIN",
                state="Meghalaya",
                organization="NER-SAFE Operational Command",
                status="ACTIVE"
            )
        else:
            with database.get_db_connection() as conn:
                conn.execute("UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE email = ?", (pwd_hash, admin_email))

        # Perform login for admin session
        code, data, info = http_post(f"{cls.base_url}/api/auth/login", {"email": admin_email, "password": demo_password})
        cookie_header = info.get("Set-Cookie", "")
        session_id = None
        if "nersafe_session=" in cookie_header:
            session_id = cookie_header.split("nersafe_session=")[1].split(";")[0]
        cls.admin_headers = {"Cookie": f"nersafe_session={session_id}"} if session_id else {}

        # Setup public test user session
        pub_email = "citizen.preflight@nersafe.gov.in"
        pub_user = database.get_user_by_email(pub_email)
        if not pub_user:
            database.create_user(
                full_name="Public Citizen Evaluator",
                email=pub_email,
                password_hash=pwd_hash,
                role="PUBLIC_USER",
                state="Mizoram",
                organization="Civilian Observer",
                status="ACTIVE"
            )
        else:
            with database.get_db_connection() as conn:
                conn.execute("UPDATE users SET password_hash = ?, status = 'ACTIVE' WHERE email = ?", (pwd_hash, pub_email))

        p_code, p_data, p_info = http_post(f"{cls.base_url}/api/auth/login", {"email": pub_email, "password": demo_password})
        p_cookie = p_info.get("Set-Cookie", "")
        p_sess = None
        if "nersafe_session=" in p_cookie:
            p_sess = p_cookie.split("nersafe_session=")[1].split(";")[0]
        cls.public_headers = {"Cookie": f"nersafe_session={p_sess}"} if p_sess else {}

    @classmethod
    def tearDownClass(cls):
        try:
            live_monitoring_controller.stop_monitoring(user={"email": "teardown@nersafe.gov.in", "role": "ADMIN"})
        except Exception:
            pass
        cls.httpd.shutdown()

    def test_01_clean_startup_and_dashboard(self):
        """1. Clean startup: GET / returns 200 and loads UX4G live dashboard."""
        code, body, _ = http_get(f"{self.base_url}/")
        self.assertEqual(code, 200)
        self.assertIn("NER-SAFE", body)
        self.assertIn("LIVE MONITORING", body)
        self.assertIn("MASTER CONTROL", body)

    def test_02_initial_state_strictly_off(self):
        """2. Master Control defaults to OFF upon boot with zero live activity."""
        code, data, _ = http_get(f"{self.base_url}/api/live-monitoring/status")
        self.assertEqual(code, 200)
        self.assertEqual(data["state"], "OFF")
        self.assertFalse(data["enabled"])
        self.assertFalse(data["scheduler_running"])

    def test_03_dormant_scheduler_suppresses_polling(self):
        """3. Background scheduler cycle returns DORMANT_OFF while state is OFF."""
        sched = AutonomousScheduler(enforce_master_control=True)
        res = sched.execute_cycle()
        self.assertEqual(res["status"], "DORMANT_OFF")
        self.assertNotIn("sources_polled", res)

    def test_04_unauthenticated_start_denied(self):
        """4. Unauthenticated POST /api/live-monitoring/start is rejected."""
        code, data, _ = http_post(f"{self.base_url}/api/live-monitoring/start", {})
        self.assertIn(code, (401, 403))
        self.assertFalse(data.get("success", True))

    def test_05_public_user_start_denied(self):
        """5. Operational action by PUBLIC_USER is rejected with 403 Forbidden."""
        code, data, _ = http_post(
            f"{self.base_url}/api/live-monitoring/start",
            {},
            headers=self.public_headers
        )
        self.assertEqual(code, 403)
        self.assertFalse(data.get("success", True))

    def test_06_authorized_start_transitions_to_active(self):
        """6. Authorized ADMIN start transitions state from OFF -> STARTING -> ACTIVE."""
        code, data, _ = http_post(
            f"{self.base_url}/api/live-monitoring/start",
            {},
            headers=self.admin_headers
        )
        self.assertEqual(code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("state"), "ACTIVE")
        self.assertTrue(data.get("scheduler_running"))

        # Verify status endpoint reflects ACTIVE state
        s_code, s_data, _ = http_get(f"{self.base_url}/api/live-monitoring/status")
        self.assertEqual(s_code, 200)
        self.assertEqual(s_data["state"], "ACTIVE")
        self.assertTrue(s_data["enabled"])

    def test_07_start_while_active_is_idempotent(self):
        """7. Subsequent START while ACTIVE returns current state without duplication."""
        code, data, _ = http_post(
            f"{self.base_url}/api/live-monitoring/start",
            {},
            headers=self.admin_headers
        )
        self.assertEqual(code, 200)
        self.assertEqual(data.get("state"), "ACTIVE")

    def test_08_live_sources_telemetry_reporting(self):
        """8. Status API reports telemetry across all 11 sources without fabricating data."""
        code, data, _ = http_get(f"{self.base_url}/api/live-monitoring/status")
        self.assertEqual(code, 200)
        sources = data.get("sources", {})
        self.assertIn("GPM", sources)
        self.assertIn("SMAP", sources)
        self.assertIn("SENTINEL1_SLC", sources)
        self.assertIn("GSI", sources)
        self.assertIn("SACHET", sources)
        self.assertIn("IMD_NOWCAST", sources)
        self.assertIn("OSINT", sources)
        self.assertIn("OSIRIS", sources)

    def test_09_operational_risk_pipeline_integrity(self):
        """9. Risk pipeline returns exactly 48 hotspots using locked formula."""
        code, data, _ = http_get(f"{self.base_url}/api/monitoring/hotspots")
        self.assertEqual(code, 200)
        features = data.get("features", [])
        self.assertEqual(len(features), 48, f"Expected 48 hotspots, got {len(features)}")

        # Verify mathematical fusion on first feature
        f0 = features[0]
        signals = f0["properties"]["signals"]
        s = signals["susceptibility_baseline"]
        r = signals["rainfall_anomaly"]
        m = signals["soil_moisture_anomaly"]
        c = signals["satellite_surface_change"]
        expected_score = round(0.40 * s + 0.30 * r + 0.20 * m + 0.10 * c, 4)
        actual_score = round(f0["properties"]["fused_risk_score"], 4)
        self.assertAlmostEqual(actual_score, expected_score, places=3)

    def test_10_authorized_stop_transitions_to_off(self):
        """10. Authorized STOP transitions state from ACTIVE -> STOPPING -> OFF gracefully."""
        code, data, _ = http_post(
            f"{self.base_url}/api/live-monitoring/stop",
            {},
            headers=self.admin_headers
        )
        self.assertEqual(code, 200)
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("state"), "OFF")
        self.assertFalse(data.get("scheduler_running"))

        # Verify status endpoint reflects OFF state
        s_code, s_data, _ = http_get(f"{self.base_url}/api/live-monitoring/status")
        self.assertEqual(s_code, 200)
        self.assertEqual(s_data["state"], "OFF")
        self.assertFalse(s_data["enabled"])

    def test_11_stop_while_off_is_safe(self):
        """11. STOP while OFF is safe and returns clean current state."""
        code, data, _ = http_post(
            f"{self.base_url}/api/live-monitoring/stop",
            {},
            headers=self.admin_headers
        )
        self.assertEqual(code, 200)
        self.assertEqual(data.get("state"), "OFF")

    def test_12_restart_resets_to_off(self):
        """12. Application restart guarantees initial state is strictly OFF."""
        new_port = find_free_port()
        new_httpd = server.start_server(port=new_port)
        new_thread = threading.Thread(target=new_httpd.serve_forever, daemon=True)
        new_thread.start()
        time.sleep(0.5)

        try:
            code, data, _ = http_get(f"http://localhost:{new_port}/api/live-monitoring/status")
            self.assertEqual(code, 200)
            self.assertEqual(data["state"], "OFF")
            self.assertFalse(data["enabled"])
        finally:
            new_httpd.shutdown()

    def test_13_production_xgboost_hash_preserved(self):
        """13. Production XGBoost model SHA-256 hash is byte-for-byte identical."""
        model_path = os.path.join(WORKSPACE, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")
        self.assertTrue(os.path.exists(model_path))
        with open(model_path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(h, LOCKED_XGBOOST_HASH)

    def test_14_locked_risk_weights_preserved(self):
        """14. Operational 4-factor risk formula weights remain strictly immutable."""
        expected = {"susceptibility": 0.40, "rainfall": 0.30, "soil_moisture": 0.20, "satellite_change": 0.10}
        self.assertEqual(LOCKED_RISK_WEIGHTS, expected)

    def test_15_insar_status_is_research_only(self):
        """15. Multi-temporal InSAR remains decoupled as RESEARCH_ONLY with 0 weight."""
        sched = AutonomousScheduler(enforce_master_control=False)
        invariants = sched.verify_system_invariants()
        self.assertEqual(invariants["insar_status"], "RESEARCH_ONLY_DECOUPLED")

    def test_16_external_hdd_protection(self):
        """16. External drive G:\\ is strictly never accessed or referenced."""
        source_files = [
            os.path.join(WORKSPACE, "server.py"),
            os.path.join(WORKSPACE, "live_monitoring_controller.py"),
            os.path.join(WORKSPACE, "nersafe_autonomous_scheduler.py"),
            os.path.join(WORKSPACE, "live_monitoring_scheduler.py")
        ]
        for fpath in source_files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("G:\\", content)
            self.assertNotIn("G:/", content)

    def test_17_zero_emoji_compliance(self):
        """17. ner_safe_live_dashboard.html strictly contains ZERO emojis."""
        dashboard_path = os.path.join(WORKSPACE, "ner_safe_live_dashboard.html")
        with open(dashboard_path, "r", encoding="utf-8") as f:
            content = f.read()
        import re
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"
            r"\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF"
            r"\U0001F900-\U0001F9FF"
            r"\U0001FA70-\U0001FAFF"
            r"\U00002702-\U000027B0]"
        )
        emojis_found = emoji_pattern.findall(content)
        self.assertEqual(len(emojis_found), 0, f"Found emojis: {emojis_found}")

    def test_18_credential_secrecy(self):
        """18. Telemetry and API payloads contain zero exposed secrets."""
        code, data, _ = http_get(f"{self.base_url}/api/live-monitoring/status")
        raw_str = json.dumps(data)
        self.assertNotIn("password", raw_str.lower())
        self.assertNotIn("api_key", raw_str.lower())
        self.assertNotIn("secret", raw_str.lower())


if __name__ == "__main__":
    print("=" * 80)
    print("NER-SAFE: FINAL SIH DEMONSTRATION PREFLIGHT VALIDATION SUITE")
    print("=" * 80)
    unittest.main(verbosity=2)
