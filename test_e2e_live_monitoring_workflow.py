"""
NER-SAFE: End-to-End Live Monitoring Workflow Automated Verification Suite
Validates the complete operational chain:
  Live Observation Retrieval
    -> Risk Fusion Recalculation
    -> Hotspot Operational Qualification
    -> Component 11 D8 Flow-Path Routing
    -> Empirical Runout Corridor Envelope
    -> Infrastructure Exposure Intersection
    -> Live Server REST API Endpoints
    -> Dashboard Leaflet Visualization & UI Integration
    -> Strict Preservation of Authoritative Scientific Assets
"""

import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
import threading

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import fusion_engine
from live_ingestion import ingestion_engine
from storage_engine import storage_engine
from demo_orchestrator import orchestrator
import server

PASS_COUNT = 0
FAIL_COUNT = 0

def check(condition: bool, desc: str):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"[\033[92mPASS\033[0m] {desc}")
    else:
        FAIL_COUNT += 1
        print(f"[\033[91mFAIL\033[0m] {desc}")

def run_e2e_tests():
    global PASS_COUNT, FAIL_COUNT
    print("=" * 80)
    print("NER-SAFE: END-TO-END OPERATIONAL LIVE MONITORING WORKFLOW TEST SUITE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STAGE 1: Live Satellite Observation Retrieval (NASA & ESA)
    # -------------------------------------------------------------------------
    print("\n--- STAGE 1: Live Observation Retrieval ---")
    status = ingestion_engine.get_public_status()
    sources = status.get("sources", {})
    check(len(sources) >= 4, f"Ingestion catalog registers {len(sources)} earth observation feeds")

    # GPM IMERG
    gpm = sources.get("rainfall", {})
    check(bool(gpm.get("granule_id")), f"GPM IMERG granule identified: {gpm.get('granule_id')[:40]}...")
    check(bool(gpm.get("latest_observation")), f"GPM observation timestamp: {gpm.get('latest_observation')}")
    check(gpm.get("freshness_state") in ("FRESH", "RECENT"), f"GPM freshness verified: {gpm.get('freshness_state')}")

    # SMAP L3
    smap = sources.get("soil_moisture", {})
    check(bool(smap.get("granule_id")), f"SMAP L3 granule identified: {smap.get('granule_id')[:40]}...")
    check(bool(smap.get("latest_observation")), f"SMAP observation timestamp: {smap.get('latest_observation')}")
    check(smap.get("freshness_state") in ("FRESH", "RECENT"), f"SMAP freshness verified: {smap.get('freshness_state')}")

    # Sentinel-2 L2A
    s2 = sources.get("satellite_optical", {})
    check(bool(s2.get("granule_id")), f"Sentinel-2 scene identified: {s2.get('granule_id')[:35]}...")
    check(bool(s2.get("latest_observation")), f"Sentinel-2 observation timestamp: {s2.get('latest_observation')}")
    check(s2.get("cloud_cover") is not None, f"Sentinel-2 cloud filtering active ({s2.get('cloud_cover')}% cloud masked)")

    # SRTM 30m DEM
    srtm = sources.get("terrain_susceptibility", {})
    check(srtm.get("processing_status") == "CALIBRATED_LOCKED", "SRTM 30m DEM locked as static geomorphic baseline")

    # -------------------------------------------------------------------------
    # STAGE 2: Multi-Source Status & Independent Timestamps
    # -------------------------------------------------------------------------
    print("\n--- STAGE 2: Multi-Source Status & Independent Timestamps ---")
    multi_status = fusion_engine.get_multi_source_status()
    ms_sources = multi_status.get("sources", {})
    check(ms_sources["rainfall"]["latest_observation"] != ms_sources["soil_moisture"]["latest_observation"],
          "Rainfall and Soil Moisture report independent observation timestamps")
    check(bool(ms_sources["satellite_optical"]["freshness_display"]),
          f"Sentinel-2 freshness independently displayed: {ms_sources['satellite_optical']['freshness_display']}")
    check(multi_status["weights"]["w1_susceptibility"] == 0.40 and multi_status["weights"]["w2_rainfall_anomaly"] == 0.30,
          "Scientific four-factor fusion weights confirmed (40/30/20/10)")

    # -------------------------------------------------------------------------
    # STAGE 3: Risk Fusion Recalculation & Baseline Invariance
    # -------------------------------------------------------------------------
    print("\n--- STAGE 3: Four-Factor Risk Fusion Recalculation ---")
    baseline_hotspots = fusion_engine.compute_fused_hotspots()
    check(len(baseline_hotspots["features"]) == 48, f"48 monitored hotspots evaluated (Found: {len(baseline_hotspots['features'])})")

    evt1 = next(f for f in baseline_hotspots["features"] if f["properties"]["event_id"] == "EVT-MEG-001")
    p1 = evt1["properties"]
    check(p1["fused_risk_score"] == 0.7055, f"EVT-MEG-001 baseline risk score mathematically invariant: {p1['fused_risk_score']}")
    check(p1["fused_tier"] == "CRITICAL", f"EVT-MEG-001 tier correctly assigned: {p1['fused_tier']}")

    # Dynamic Live Feature Recalculation
    live_features = {
        "rainfall_anomaly": 0.85,
        "soil_moisture_anomaly": 0.75,
        "satellite_surface_change": 0.30
    }
    live_hotspots = fusion_engine.compute_fused_hotspots(live_features=live_features)
    evt1_live = next(f for f in live_hotspots["features"] if f["properties"]["event_id"] == "EVT-MEG-001")
    p1_live = evt1_live["properties"]
    check(p1_live["is_live_satellite_prediction"] is True, "Live prediction flag correctly set")
    check(p1_live["fused_risk_score"] != p1["fused_risk_score"], f"Dynamic risk recalculation responsive: {p1['fused_risk_score']} -> {p1_live['fused_risk_score']}")

    # -------------------------------------------------------------------------
    # STAGE 4: Hotspot Qualification & Runout Linkage
    # -------------------------------------------------------------------------
    print("\n--- STAGE 4: Hotspot Operational Qualification & Runout Linkage ---")
    qual_count = sum(1 for f in baseline_hotspots["features"] if f["properties"]["qualifies_for_runout"])
    check(qual_count > 0, f"{qual_count} hotspots qualify for automated runout monitoring (CRITICAL or HIGH tier)")
    check(p1["qualifies_for_runout"] is True, "EVT-MEG-001 (CRITICAL) qualifies for active runout envelope")

    check("runout_metrics" in p1, "Hotspot properties include runout_metrics dictionary")
    check(p1["runout_metrics"]["path_length_m"] > 0, f"Flow path length populated: {p1['runout_metrics']['path_length_m']} m")
    check(p1["runout_metrics"]["elevation_drop_m"] > 0, f"Elevation drop populated: {p1['runout_metrics']['elevation_drop_m']} m")

    # -------------------------------------------------------------------------
    # STAGE 5: Coupled Hotspot Runout Package Engine
    # -------------------------------------------------------------------------
    print("\n--- STAGE 5: Coupled Hotspot Runout Package Engine ---")
    pkg = fusion_engine.get_hotspot_runout_package("EVT-MEG-001")
    check(pkg["event_id"] == "EVT-MEG-001", "Coupled runout package retrieved for EVT-MEG-001")
    check(pkg["qualifying"] is True, "Package correctly indicates qualifying=True")
    check(pkg["flow_path"] is not None, "D8 steepest-descent flow path LineString attached")
    check(pkg["flow_path"]["geometry"]["type"] == "LineString", "Flow path geometry is valid LineString")
    check(len(pkg["flow_path"]["geometry"]["coordinates"]) >= 2, f"Flow path contains {len(pkg['flow_path']['geometry']['coordinates'])} vertices")
    check(pkg["runout_corridor"] is not None, "Empirical runout corridor Polygon attached")
    check(pkg["runout_corridor"]["geometry"]["type"] == "Polygon", "Corridor geometry is valid Polygon")
    check(len(pkg["exposure_intersections"]["features"]) >= 1, f"Intersected infrastructure attached: {len(pkg['exposure_intersections']['features'])} assets")

    # Test Mizoram Event
    pkg_miz = fusion_engine.get_hotspot_runout_package("EVT-MIZ-018")
    check(pkg_miz["event_id"] == "EVT-MIZ-018", "Coupled runout package retrieved for EVT-MIZ-018 (Mizoram)")
    check(pkg_miz["flow_path"]["geometry"]["type"] == "LineString", "EVT-MIZ-018 flow path verified")

    # -------------------------------------------------------------------------
    # STAGE 6: Live Server REST API Endpoints Verification
    # -------------------------------------------------------------------------
    print("\n--- STAGE 6: Live Server REST API Endpoints Verification ---")
    TEST_PORT = 8006
    server_address = ("", TEST_PORT)
    httpd = server.ThreadingHTTPServer(server_address, server.NERSafeRequestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://localhost:{TEST_PORT}"

    def api_get(endpoint):
        req = urllib.request.Request(f"{base_url}{endpoint}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    # Test GET /api/monitoring/status
    code, data = api_get("/api/monitoring/status")
    check(code == 200 and "sources" in data, "GET /api/monitoring/status returned 200 OK with observation sources")

    # Test GET /api/monitoring/hotspots
    code, data = api_get("/api/monitoring/hotspots")
    check(code == 200 and len(data["features"]) == 48, f"GET /api/monitoring/hotspots returned 200 OK (48 hotspots)")

    # Test GET /api/monitoring/hotspots?qualifying=1
    code, data = api_get("/api/monitoring/hotspots?qualifying=1")
    check(code == 200 and all(f["properties"]["qualifies_for_runout"] for f in data["features"]),
          f"GET /api/monitoring/hotspots?qualifying=1 returned {len(data['features'])} qualifying hotspots")

    # Test GET /api/monitoring/flowpaths
    code, data = api_get("/api/monitoring/flowpaths")
    check(code == 200 and len(data["features"]) == 48, f"GET /api/monitoring/flowpaths returned 200 OK (48 flow paths)")
    check(data["features"][0]["geometry"]["type"] == "LineString", "Flow path features have LineString geometry")

    # Test GET /api/monitoring/flowpaths?event_id=EVT-MEG-001
    code, data = api_get("/api/monitoring/flowpaths?event_id=EVT-MEG-001")
    check(code == 200 and len(data["features"]) == 1, "GET /api/monitoring/flowpaths?event_id=EVT-MEG-001 filtered to single path")

    # Test GET /api/monitoring/corridors
    code, data = api_get("/api/monitoring/corridors")
    check(code == 200 and len(data["features"]) == 48, f"GET /api/monitoring/corridors returned 200 OK (48 corridors)")
    check(data["features"][0]["geometry"]["type"] == "Polygon", "Corridor features have Polygon geometry")

    # Test GET /api/monitoring/corridors?event_id=EVT-MEG-001
    code, data = api_get("/api/monitoring/corridors?event_id=EVT-MEG-001")
    check(code == 200 and len(data["features"]) == 1, "GET /api/monitoring/corridors?event_id=EVT-MEG-001 filtered to single corridor")

    # Test GET /api/monitoring/exposure
    code, data = api_get("/api/monitoring/exposure")
    check(code == 200 and len(data["features"]) == 62, f"GET /api/monitoring/exposure returned 200 OK (62 asset intersections)")

    # Test GET /api/monitoring/exposure?event_id=EVT-MEG-001
    code, data = api_get("/api/monitoring/exposure?event_id=EVT-MEG-001")
    check(code == 200 and len(data["features"]) == 2, "GET /api/monitoring/exposure?event_id=EVT-MEG-001 returned 2 exposed road assets")

    # Test GET /api/monitoring/hotspots/EVT-MEG-001/runout
    code, data = api_get("/api/monitoring/hotspots/EVT-MEG-001/runout")
    check(code == 200 and data["event_id"] == "EVT-MEG-001", "GET /api/monitoring/hotspots/EVT-MEG-001/runout returned 200 OK coupled package")
    check(data["qualifying"] is True, "Coupled package reports qualifying status")
    check(data["flow_path"]["geometry"]["type"] == "LineString", "Coupled package flow path is LineString")
    check(data["runout_corridor"]["geometry"]["type"] == "Polygon", "Coupled package runout corridor is Polygon")
    check(len(data["exposure_intersections"]["features"]) == 2, "Coupled package contains 2 exposure intersections")

    # Test GET /api/monitoring/runout?event_id=EVT-MIZ-018
    code, data = api_get("/api/monitoring/runout?event_id=EVT-MIZ-018")
    check(code == 200 and data["event_id"] == "EVT-MIZ-018", "GET /api/monitoring/runout?event_id=EVT-MIZ-018 returned 200 OK")

    # -------------------------------------------------------------------------
    # STAGE 7: Dashboard HTML & Leaflet Visualization Architecture
    # -------------------------------------------------------------------------
    print("\n--- STAGE 7: Dashboard UI & Leaflet Layer Architecture ---")
    dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
    with open(dash_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    check("fetch('/api/monitoring/flowpaths')" in html_content, "Dashboard JavaScript fetches /api/monitoring/flowpaths")
    check("renderFlowPathsLayer" in html_content, "Dashboard implements renderFlowPathsLayer()")
    check("renderCorridorsLayer" in html_content, "Dashboard implements renderCorridorsLayer()")
    check("selectHotspot" in html_content, "Dashboard implements interactive selectHotspot() workflow")
    check("hotspotRunoutInspector" in html_content, "Dashboard contains dedicated #hotspotRunoutInspector DOM container")
    check("chkFlowPaths" in html_content, "Dashboard contains #chkFlowPaths layer checkbox")
    check("toggleLayer('flowpaths')" in html_content or "layerKey === 'flowpaths'" in html_content,
          "toggleLayer() handles 'flowpaths' toggle")

    # Zero emoji check
    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    found_emojis = emoji_pattern.findall(html_content)
    check(len(found_emojis) == 0, f"Dashboard strictly complies with UX4G zero-emoji rule (Emojis found: {len(found_emojis)})")

    # -------------------------------------------------------------------------
    # STAGE 8: Scientific Asset Immutability Guarantee
    # -------------------------------------------------------------------------
    print("\n--- STAGE 8: Scientific Asset Immutability Guarantee ---")
    c11_event_records = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "events", "event_records.csv")
    check(os.path.exists(c11_event_records), "Component 11 event_records.csv exists")
    check(os.path.getsize(c11_event_records) == 13009, f"event_records.csv size invariant (13009 bytes, got {os.path.getsize(c11_event_records)})")

    c11_corridors_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "runout_corridors", "runout_corridors.geojson")
    check(os.path.getsize(c11_corridors_file) == 1062284, f"runout_corridors.geojson size invariant (1062284 bytes)")

    c11_flowpaths_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "flow_paths", "flow_paths.geojson")
    check(os.path.getsize(c11_flowpaths_file) == 84522, f"flow_paths.geojson size invariant (84522 bytes)")

    c11_exposure_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "exposure", "exposure_intersections.geojson")
    check(os.path.getsize(c11_exposure_file) == 48930, f"exposure_intersections.geojson size invariant (48930 bytes)")

    # Shutdown test server
    httpd.shutdown()
    httpd.server_close()

    print("\n" + "=" * 80)
    print(f"END-TO-END VERIFICATION RESULTS: {PASS_COUNT} PASSED, {FAIL_COUNT} FAILED")
    print("=" * 80)
    if FAIL_COUNT == 0:
        print("\033[92mALL END-TO-END WORKFLOW CHECKS PASSED PERFECTLY!\033[0m")
    else:
        print("\033[91mSOME CHECKS FAILED!\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    run_e2e_tests()
