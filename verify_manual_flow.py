"""
NER-SAFE: End-to-End System Flow Verification
Simulates the exact user sequence requested:
1. Register as new Public User with request for Field Officer (Dariti Marbaniang)
2. Sign in as Administrator (admin@nersafe.gov.in)
3. Approve the role request in Admin Console
4. Re-check user session and verify user now possesses FIELD_OFFICER role
5. Verify Field Officer can verify reports on the verification desk
6. Verify zero emojis across the DOM
"""

import sys
import os
import json
import re
import urllib.request
import urllib.error

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
BASE_URL = "http://127.0.0.1:8000"

def run_flow():
    print("=" * 70)
    print("STARTING END-TO-END MANUAL / SYSTEM WORKFLOW VERIFICATION")
    print("=" * 70)

    # 1. Register as new Public User with request for Field Officer
    print("\n[STEP 1] Registering new user requesting Field Officer role...")
    reg_payload = {
        "full_name": "Dariti Marbaniang",
        "email": "dariti.marbaniang@sdma.meghalaya.gov.in",
        "password": "SecureField2026!#",
        "state": "Meghalaya",
        "organization": "East Khasi Hills Field Inspection Unit",
        "requested_role": "FIELD_OFFICER"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/register",
        data=json.dumps(reg_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"  PASS: Registration succeeded -> ID: {data['user']['id']}, Role: {data['user']['role']}")
            print(f"        Message: {data['message']}")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print("  INFO: Account already registered. Proceeding.")
        else:
            print(f"  FAIL: Registration failed: {e}")
            return False

    # 2. Sign in as Administrator
    print("\n[STEP 2] Signing in as Administrator...")
    admin_login_payload = {
        "email": "admin@nersafe.gov.in",
        "password": "AdminSecurePass123!#"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps(admin_login_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    admin_cookie = ""
    with urllib.request.urlopen(req) as resp:
        admin_data = json.loads(resp.read().decode("utf-8"))
        for c in resp.headers.get_all("Set-Cookie") or []:
            if "nersafe_session=" in c:
                admin_cookie = c.split(";")[0]
        print(f"  PASS: Signed in as {admin_data['user']['full_name']} (Role: {admin_data['user']['role']})")

    # 3. Approve role request in Admin Console
    print("\n[STEP 3] Approving role request in Admin Console...")
    req = urllib.request.Request(
        f"{BASE_URL}/api/admin/role-requests",
        headers={"Cookie": admin_cookie}
    )
    with urllib.request.urlopen(req) as resp:
        reqs_data = json.loads(resp.read().decode("utf-8"))
        target_req = None
        for r in reqs_data.get("role_requests", []):
            if r["email"] == "dariti.marbaniang@sdma.meghalaya.gov.in" and r["status"] == "PENDING":
                target_req = r
                break
    
    if target_req:
        req_id = target_req["id"]
        approve_req = urllib.request.Request(
            f"{BASE_URL}/api/admin/role-requests/{req_id}/approve",
            headers={"Cookie": admin_cookie},
            method="PATCH"
        )
        with urllib.request.urlopen(approve_req) as resp:
            app_data = json.loads(resp.read().decode("utf-8"))
            print(f"  PASS: Request #{req_id} approved -> {app_data['message']}")
    else:
        print("  INFO: No pending request found (may have already been approved).")

    # 4. Sign in as Dariti Marbaniang & Re-check user session for FIELD_OFFICER role
    print("\n[STEP 4] Signing in as Dariti Marbaniang and re-checking user session...")
    dariti_login = {
        "email": "dariti.marbaniang@sdma.meghalaya.gov.in",
        "password": "SecureField2026!#"
    }
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps(dariti_login).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    dariti_cookie = ""
    with urllib.request.urlopen(req) as resp:
        dariti_data = json.loads(resp.read().decode("utf-8"))
        for c in resp.headers.get_all("Set-Cookie") or []:
            if "nersafe_session=" in c:
                dariti_cookie = c.split(";")[0]

    # Call GET /api/auth/me
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/me",
        headers={"Cookie": dariti_cookie}
    )
    with urllib.request.urlopen(req) as resp:
        me_data = json.loads(resp.read().decode("utf-8"))
        current_role = me_data["user"]["role"]
        print(f"  PASS: GET /api/auth/me verified: Name: '{me_data['user']['full_name']}', Role: '{current_role}'")
        assert current_role == "FIELD_OFFICER", f"Expected FIELD_OFFICER, got {current_role}"

    # 5. Verify Field Officer can verify reports on the verification desk
    print("\n[STEP 5] Verifying report on verification desk with Field Officer credentials...")
    # Fetch reports to find an unverified report
    req = urllib.request.Request(f"{BASE_URL}/api/reports")
    with urllib.request.urlopen(req) as resp:
        reps_data = json.loads(resp.read().decode("utf-8"))
        unverified_rep = None
        for f in reps_data.get("features", []):
            if f["properties"]["verification_status"] == "UNVERIFIED_OBSERVATION":
                unverified_rep = f
                break

    if not unverified_rep:
        # Create an observation first
        post_obs = urllib.request.Request(
            f"{BASE_URL}/api/reports",
            data=json.dumps({
                "latitude": 25.150417, "longitude": 92.369028,
                "category": "ROCKFALL_DEBRIS", "user_notes": "Field Officer Verification Test Report"
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(post_obs) as resp:
            new_rep = json.loads(resp.read().decode("utf-8"))
            target_rep_id = new_rep["report_id"]
    else:
        target_rep_id = unverified_rep["properties"]["report_id"]

    # Verify the report
    verify_req = urllib.request.Request(
        f"{BASE_URL}/api/reports/{target_rep_id}/verify",
        data=json.dumps({
            "verification_status": "FIELD_VERIFIED",
            "verification_notes": "Inspected on site by Field Officer Dariti Marbaniang"
        }).encode("utf-8"),
        headers={"Content-Type": "application/json", "Cookie": dariti_cookie},
        method="PATCH"
    )
    with urllib.request.urlopen(verify_req) as resp:
        ver_resp = json.loads(resp.read().decode("utf-8"))
        print(f"  PASS: Report {target_rep_id} verified successfully -> Status: {ver_resp['verification_status']}")

    # 6. Verify zero emojis across the DOM
    print("\n[STEP 6] Auditing ner_safe_live_dashboard.html DOM for emojis...")
    with open(os.path.join(WORKSPACE, "ner_safe_live_dashboard.html"), "r", encoding="utf-8") as f:
        html = f.read()

    emoji_pat = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF]+"
    )
    emojis = emoji_pat.findall(html)
    print(f"  PASS: Total emojis in ner_safe_live_dashboard.html: {len(emojis)} (EXACTLY ZERO EMOJIS, 100% SVG)")
    assert len(emojis) == 0

    print("\n" + "=" * 70)
    print("ALL MANUAL / SYSTEM VERIFICATION FLOWS SUCCEEDED PERFECTLY!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = run_flow()
    sys.exit(0 if success else 1)
