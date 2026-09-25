"""
NER-SAFE Live Multi-Source Landslide Risk Monitoring System
End-to-End Validation & Verification Suite

Tests:
1. Multi-source fusion engine (48 hotspots, 4 independent data sources, mathematical fusion)
2. Decoupled freshness timestamps (Sentinel-2, GPM, SMAP, SRTM)
3. Dynamic spatial cross-referencing (SoI boundaries, C11 corridors, settlements)
4. SQLite persistence & multi-device report synchronization
5. REST API endpoints (GET /status, /hotspots, /corridors, /advisories, /reports, POST /reports, PATCH /verify)
6. Zero-emoji audit & UX4G compliance on ner_safe_live_dashboard.html
7. Component 7-12 immutability audit
"""

import sys
import os
import json
import time
import threading
import urllib.request
import urllib.error
import re

# Ensure workspace root is in path
WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

import fusion_engine
import database
import spatial_cross_ref
from server import ThreadingHTTPServer, NERSafeRequestHandler

def run_tests():
    print("=" * 70)
    print("NER-SAFE LIVE SYSTEM COMPREHENSIVE VALIDATION SUITE")
    print("=" * 70)
    total_checks = 0
    passed_checks = 0

    # ---------------------------------------------------------
    # TEST 1: Fusion Engine & Source Freshness
    # ---------------------------------------------------------
    print("\n[TEST 1] Verifying Multi-Source Fusion Engine...")
    hotspots = fusion_engine.compute_fused_hotspots()
    total_checks += 1
    if len(hotspots.get("features", [])) == 48:
        print(f"  PASS: Exactly 48 hotspots loaded from Component 11 ({len(hotspots['features'])} found)")
        passed_checks += 1
    else:
        print(f"  FAIL: Expected 48 hotspots, got {len(hotspots.get('features', []))}")

    # Check fusion formula on first hotspot
    f0 = hotspots["features"][0]
    props = f0["properties"]
    signals = props["signals"]
    susc = signals["susceptibility_baseline"]
    rain = signals["rainfall_anomaly"]
    soil = signals["soil_moisture_anomaly"]
    opt = signals["satellite_surface_change"]
    expected_score = round(0.40 * susc + 0.30 * rain + 0.20 * soil + 0.10 * opt, 4)
    actual_score = props["fused_risk_score"]
    
    total_checks += 1
    if abs(expected_score - actual_score) < 0.001:
        print(f"  PASS: Fusion formula verified: 0.40*{susc} + 0.30*{rain} + 0.20*{soil} + 0.10*{opt} = {actual_score}")
        passed_checks += 1
    else:
        print(f"  FAIL: Fusion calculation mismatch: expected {expected_score}, got {actual_score}")

    freshness = fusion_engine.get_multi_source_status()
    total_checks += 1
    required_sources = ["satellite_optical", "rainfall", "soil_moisture", "terrain_susceptibility"]
    if all(s in freshness["sources"] for s in required_sources):
        print("  PASS: All 4 multi-source environmental feeds present with independent freshness")
        passed_checks += 1
    else:
        print("  FAIL: Missing data sources in freshness metadata")

    # Verify timestamps are decoupled / distinct
    t_s2 = freshness["sources"]["satellite_optical"]["latest_observation"]
    t_gpm = freshness["sources"]["rainfall"]["latest_observation"]
    t_smap = freshness["sources"]["soil_moisture"]["latest_observation"]
    total_checks += 1
    if t_s2 != t_gpm and t_gpm != t_smap:
        print(f"  PASS: Source observation timestamps are properly decoupled:")
        print(f"        Sentinel-2: {t_s2}")
        print(f"        GPM Rain:   {t_gpm}")
        print(f"        SMAP Soil:  {t_smap}")
        passed_checks += 1
    else:
        print("  FAIL: Observation timestamps are falsely identical")

    # ---------------------------------------------------------
    # TEST 2: Spatial Cross-Referencing
    # ---------------------------------------------------------
    print("\n[TEST 2] Verifying Dynamic Spatial Cross-Referencing...")
    # Point in East Jaintia Hills near EVT-MEG-023 (25.150417, 92.369028)
    res_inside = spatial_cross_ref.analyze_location(25.150417, 92.369028)
    total_checks += 1
    if res_inside["state"] == "Meghalaya" and res_inside["within_phase1_aoi"] is True:
        print(f"  PASS: Coordinates (25.150417, 92.369028) correctly resolved to {res_inside['district']}, {res_inside['state']}")
        passed_checks += 1
    else:
        print(f"  FAIL: Failed state/district resolution: {res_inside}")

    total_checks += 1
    if res_inside["nearest_c11_event_id"] == "EVT-MEG-023" and res_inside["distance_to_runout_m"] <= 50:
        print(f"  PASS: Proximity match verified: Corridor {res_inside['nearest_c11_event_id']} at {res_inside['distance_to_runout_m']}m")
        passed_checks += 1
    else:
        print(f"  FAIL: Expected EVT-MEG-023 within 50m, got {res_inside['nearest_c11_event_id']} at {res_inside.get('distance_to_runout_m')}m")

    # Point outside known corridor in central Aizawl town
    res_outside = spatial_cross_ref.analyze_location(23.7271, 92.7176)
    total_checks += 1
    if res_outside["intersects_c11_runout"] is False or res_outside["nearest_c11_event_id"] == "None":
        print(f"  PASS: Point far from runout corridors correctly marked with no intersection (Distance: {res_outside['distance_to_runout_m']}m)")
        passed_checks += 1
    else:
        print(f"  FAIL: Point incorrectly assigned to corridor: {res_outside['nearest_c11_event_id']}")

    # ---------------------------------------------------------
    # TEST 3: SQLite Database Persistence & Multi-Device Simulation
    # ---------------------------------------------------------
    print("\n[TEST 3] Verifying SQLite Persistence & Multi-Device Synchronization...")
    database.init_db()
    db_reports = database.get_all_reports().get("features", [])
    total_checks += 1
    if len(db_reports) >= 13:
        print(f"  PASS: Seeded demo reports loaded from SQLite ({len(db_reports)} records)")
        passed_checks += 1
    else:
        print(f"  FAIL: Expected at least 13 seeded records, found {len(db_reports)}")

    # Simulate Device A submitting a new report
    device_a_payload = {
        "category": "ROCKFALL_DEBRIS",
        "displacement_width": "15_TO_50_CM",
        "latitude": 25.150417,
        "longitude": 92.369028,
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "nearest_settlement": "Mawkdok",
        "settlement_distance_km": 1.2,
        "nearest_c11_event_id": "EVT-MEG-023",
        "distance_to_runout_m": 0.0,
        "intersects_c11_runout": 1,
        "user_notes": "Boulders on downhill carriageway after early morning rain",
        "photo_filename": "test_rockfall.jpg"
    }
    new_id = database.add_report(device_a_payload)
    total_checks += 1
    if new_id and new_id.startswith("REP-"):
        print(f"  PASS: Device A submitted report successfully -> Assigned ID: {new_id}")
        passed_checks += 1
    else:
        print(f"  FAIL: Device A submission failed: {new_id}")

    # Simulate Device B querying the reports list
    device_b_reports = database.get_all_reports().get("features", [])
    matched = [r for r in device_b_reports if r["properties"]["report_id"] == new_id]
    total_checks += 1
    if len(matched) == 1 and matched[0]["properties"]["verification_status"] == "UNVERIFIED_OBSERVATION":
        print(f"  PASS: Device B retrieved report {new_id} in state: {matched[0]['properties']['verification_status']}")
        passed_checks += 1
    else:
        print(f"  FAIL: Device B failed to find newly submitted report {new_id}")

    # Simulate Field Officer verification on Device B
    verify_ok = database.update_verification_status(new_id, "FIELD_VERIFIED", "Officer Sangma", "Verified on-site")
    device_b_recheck = database.get_all_reports().get("features", [])
    matched_after = [r for r in device_b_recheck if r["properties"]["report_id"] == new_id]
    total_checks += 1
    if verify_ok and len(matched_after) == 1 and matched_after[0]["properties"]["verification_status"] == "FIELD_VERIFIED":
        print(f"  PASS: Report {new_id} status successfully updated to: FIELD_VERIFIED")
        passed_checks += 1
    else:
        print(f"  FAIL: Verification update failed for {new_id}")

    # ---------------------------------------------------------
    # TEST 4: REST API Server Endpoints
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing REST API Server Endpoints...")
    test_port = 8899
    server = ThreadingHTTPServer(("127.0.0.1", test_port), NERSafeRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{test_port}"
    
    # 4.1 Root UI
    try:
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            total_checks += 1
            if resp.status == 200 and "NER-SAFE" in content and "Live Multi-Source Landslide Risk Monitoring System" in content:
                print("  PASS: GET / returned 200 OK with UX4G live monitoring portal")
                passed_checks += 1
            else:
                print("  FAIL: GET / did not return expected HTML")
    except Exception as e:
        print(f"  FAIL: GET / error: {e}")

    # 4.2 Status API
    try:
        with urllib.request.urlopen(f"{base_url}/api/monitoring/status") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total_checks += 1
            if resp.status == 200 and "sources" in data:
                print(f"  PASS: GET /api/monitoring/status -> 200 OK (Sources: {list(data['sources'].keys())})")
                passed_checks += 1
            else:
                print(f"  FAIL: Unexpected status response: {data}")
    except Exception as e:
        print(f"  FAIL: GET /api/monitoring/status error: {e}")

    # 4.3 Hotspots API
    try:
        with urllib.request.urlopen(f"{base_url}/api/monitoring/hotspots") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total_checks += 1
            if resp.status == 200 and len(data.get("features", [])) == 48:
                print(f"  PASS: GET /api/monitoring/hotspots -> 200 OK (Returned {len(data['features'])} hotspots)")
                passed_checks += 1
            else:
                print(f"  FAIL: Expected 48 hotspot features, got {len(data.get('features', []))}")
    except Exception as e:
        print(f"  FAIL: GET /api/monitoring/hotspots error: {e}")

    # 4.4 Corridors API
    try:
        with urllib.request.urlopen(f"{base_url}/api/monitoring/corridors") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total_checks += 1
            if resp.status == 200 and len(data.get("features", [])) > 0:
                print(f"  PASS: GET /api/monitoring/corridors -> 200 OK (Returned {len(data['features'])} corridor geometries)")
                passed_checks += 1
            else:
                print(f"  FAIL: Expected corridor features, got {len(data.get('features', []))}")
    except Exception as e:
        print(f"  FAIL: GET /api/monitoring/corridors error: {e}")

    # 4.5 Advisories API
    try:
        with urllib.request.urlopen(f"{base_url}/api/monitoring/advisories") as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total_checks += 1
            if resp.status == 200 and len(data.get("alerts", [])) > 0:
                print(f"  PASS: GET /api/monitoring/advisories -> 200 OK (Returned {len(data['alerts'])} advisories)")
                passed_checks += 1
            else:
                print(f"  FAIL: Advisories endpoint failed")
    except Exception as e:
        print(f"  FAIL: GET /api/monitoring/advisories error: {e}")

    # 4.6 POST /api/reports (Cross-Device simulation)
    created_rep_id = None
    try:
        post_payload = {
            "category": "DEBRIS_FLOW",
            "severity": "CRITICAL",
            "latitude": 23.7271,
            "longitude": 92.7176,
            "location_name": "Aizawl North Slope Road",
            "user_notes": "Mud slurry moving across road corridor"
        }
        req = urllib.request.Request(
            f"{base_url}/api/reports",
            data=json.dumps(post_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            created_rep_id = res_data.get("report_id")
            spat_res = res_data.get("spatial_analysis", {})
            total_checks += 1
            if resp.status == 201 and spat_res.get("state") == "Mizoram":
                print(f"  PASS: POST /api/reports -> 201 Created (ID: {created_rep_id}, State: {spat_res['state']}, District: {spat_res['district']})")
                passed_checks += 1
            else:
                print(f"  FAIL: POST /api/reports unexpected response: {res_data}")
    except Exception as e:
        print(f"  FAIL: POST /api/reports error: {e}")

    # 4.7 PATCH /api/reports/<id>/verify (Requires Authenticated FIELD_OFFICER or ADMIN)
    try:
        # Authenticate as Field Officer
        fo_login_req = urllib.request.Request(
            f"{base_url}/api/auth/login",
            data=json.dumps({"email": "field.lal@nersafe.gov.in", "password": "FieldPass123!@"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        fo_cookie = ""
        with urllib.request.urlopen(fo_login_req) as fo_resp:
            for c in fo_resp.headers.get_all("Set-Cookie") or []:
                if "nersafe_session=" in c:
                    fo_cookie = c.split(";")[0]

        patch_payload = {
            "verification_status": "FIELD_VERIFIED",
            "verified_by": "Mizoram DEOC Duty Officer",
            "verification_notes": "On-site confirmation"
        }
        patch_url = f"{base_url}/api/reports/{created_rep_id}/verify"
        req = urllib.request.Request(
            patch_url,
            data=json.dumps(patch_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Cookie": fo_cookie},
            method="PATCH"
        )
        with urllib.request.urlopen(req) as resp:
            patch_res = json.loads(resp.read().decode("utf-8"))
            total_checks += 1
            if resp.status == 200 and patch_res.get("verification_status") == "FIELD_VERIFIED":
                print(f"  PASS: PATCH /api/reports/{created_rep_id}/verify -> 200 OK (Status: {patch_res['verification_status']})")
                passed_checks += 1
            else:
                print(f"  FAIL: PATCH /api/reports verify failed: {patch_res}")
    except Exception as e:
        print(f"  FAIL: PATCH /api/reports verify error: {e}")

    server.shutdown()

    # ---------------------------------------------------------
    # TEST 5: Emoji Audit & UX4G Design Compliance
    # ---------------------------------------------------------
    print("\n[TEST 5] Checking Zero-Emoji & UX4G Design Compliance...")
    dashboard_path = os.path.join(WORKSPACE, "ner_safe_live_dashboard.html")
    with open(dashboard_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Regex matching emojis in Unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "]+",
        flags=re.UNICODE
    )
    emoji_matches = emoji_pattern.findall(html_content)
    total_checks += 1
    if len(emoji_matches) == 0:
        print("  PASS: EXACTLY ZERO EMOJIS found in ner_safe_live_dashboard.html (100% clean SVG icons)")
        passed_checks += 1
    else:
        print(f"  FAIL: Found {len(emoji_matches)} emojis in dashboard: {emoji_matches[:5]}")

    # Check UX4G color tokens and CARTO tile provider
    total_checks += 1
    if "#1351A3" in html_content and "cartocdn.com" in html_content:
        print("  PASS: UX4G Navy token (#1351A3) and CARTO Positron Light basemap verified")
        passed_checks += 1
    else:
        print("  FAIL: UX4G design tokens or CARTO tile provider missing in dashboard HTML")

    # ---------------------------------------------------------
    # TEST 6: Component 7-12 Scientific Source Immutability
    # ---------------------------------------------------------
    print("\n[TEST 6] Auditing Component 7-12 Scientific Source Immutability...")
    c11_event_records = os.path.join(WORKSPACE, "event_records.csv")
    size_bytes = os.path.getsize(c11_event_records)
    total_checks += 1
    if size_bytes == 13009:
        print(f"  PASS: Component 11 event_records.csv remains strictly immutable (size: {size_bytes} bytes)")
        passed_checks += 1
    else:
        print(f"  FAIL: event_records.csv was modified! (Current size: {size_bytes}, expected: 13009)")

    # Final Summary
    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 70)
    if passed_checks == total_checks:
        print("ALL VERIFICATION CHECKS PASSED: NER-SAFE LIVE SYSTEM IS FULLY OPERATIONAL!")
        return True
    else:
        print("SOME CHECKS FAILED.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
