#!/usr/bin/env python3
"""
NER-SAFE — COMPONENT 13: STEP 2
Offline Synchronization, Configurable Prototype Deduplication & Spatial Hazard Cross-Referencing
Author: NER-SAFE Research & Development Team
Date: September 2026
"""

import os
import json
import csv
import math
import argparse
from datetime import datetime
from shapely.geometry import Point, shape

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
C11_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11")
C12_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_12")
C13_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_13")

DATA_DIR = os.path.join(C13_DIR, "data")
META_DIR = os.path.join(C13_DIR, "metadata")
os.makedirs(META_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 13: STEP 2 — SYNC, DEDUP & SPATIAL CONTEXTUALIZATION")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. LOAD READ-ONLY UPSTREAM DATA (COMPONENTS 11 & 12)
# -----------------------------------------------------------------------------
corridors_fp = os.path.join(C11_DIR, "runout_corridors", "runout_corridors.geojson")
events_fp = os.path.join(C11_DIR, "events", "event_records.geojson")
cap_fp = os.path.join(C12_DIR, "alerts", "cap_alerts.json")

with open(corridors_fp, "r", encoding="utf-8") as f:
    corridors_data = json.load(f)
with open(events_fp, "r", encoding="utf-8") as f:
    events_data = json.load(f)
with open(cap_fp, "r", encoding="utf-8") as f:
    cap_data = json.load(f)

print(f"Loaded {len(corridors_data['features'])} Component 11 runout corridors and {len(cap_data['alerts'])} Component 12 advisories (Read-Only).")

# Map Component 12 advisories by event_id
advisories_by_event = {}
for alt in cap_data["alerts"]:
    eid = alt.get("event_id") or alt["identifier"].replace("NER-SAFE-CAP-", "")
    info = alt["info"]
    params = {p["valueName"]: p["value"] for p in info.get("parameter", [])}
    advisories_by_event[eid] = {
        "tier": params.get("Prototype_Advisory_Level", alt.get("tier", "GREEN")),
        "headline": info["headline"]
    }

# Build Shapely polygons for Component 11 corridors
corridor_geoms = []
for feat in corridors_data["features"]:
    cid = feat["id"]
    poly = shape(feat["geometry"])
    p_props = feat["properties"]
    priority = p_props.get("impact_priority", "LOW")
    corridor_geoms.append({
        "event_id": cid,
        "priority": priority,
        "geom": poly
    })

# -----------------------------------------------------------------------------
# 2. LOAD COMPONENT 13 SYNTHETIC OBSERVATIONS
# -----------------------------------------------------------------------------
reports_json_fp = os.path.join(DATA_DIR, "synthetic_demonstration_reports.json")
with open(reports_json_fp, "r", encoding="utf-8") as f:
    reports = json.load(f)

print(f"Loaded {len(reports)} synthetic demonstration reports for processing.")

# -----------------------------------------------------------------------------
# 3. CONFIGURABLE PROTOTYPE DEDUPLICATION CLUSTERING (DEFAULT: 50m HEURISTIC)
# -----------------------------------------------------------------------------
CLUSTER_RADIUS_M = 50.0  # Configurable prototype heuristic distance

def compute_ground_distance_m(lat1, lon1, lat2, lon2):
    """Computes accurate geodesic ground distance in meters between two coordinates"""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    mean_lat = math.radians((lat1 + lat2) / 2.0)
    # WGS84 approximate local metric projection
    x = dlon * math.cos(mean_lat) * 6371000.0
    y = dlat * 6371000.0
    return math.sqrt(x*x + y*y)

# Perform pairwise clustering
clusters = []
assigned_cluster = {}

for i, rep in enumerate(reports):
    r_id = rep["report_id"]
    if r_id in assigned_cluster:
        continue
    
    lat1 = rep["location"]["latitude"]
    lon1 = rep["location"]["longitude"]
    state_code = "MEG" if rep["location"]["state"] == "Meghalaya" else "MIZ"
    
    current_cluster_id = f"CLUS-{state_code}-{len(clusters) + 1:03d}"
    members = [r_id]
    assigned_cluster[r_id] = current_cluster_id
    
    for j in range(i + 1, len(reports)):
        other_rep = reports[j]
        o_id = other_rep["report_id"]
        if o_id in assigned_cluster:
            continue
            
        lat2 = other_rep["location"]["latitude"]
        lon2 = other_rep["location"]["longitude"]
        
        dist_m = compute_ground_distance_m(lat1, lon1, lat2, lon2)
        if dist_m <= CLUSTER_RADIUS_M:
            members.append(o_id)
            assigned_cluster[o_id] = current_cluster_id
            
    clusters.append({
        "cluster_id": current_cluster_id,
        "primary_report_id": r_id,
        "member_count": len(members),
        "members": members,
        "heuristic_distance_m": CLUSTER_RADIUS_M
    })

print(f"Executed 50m Deduplication Heuristic: Formed {len(clusters)} distinct clusters from {len(reports)} observations.")

# -----------------------------------------------------------------------------
# 4. SPATIAL HAZARD CORRIDOR CROSS-REFERENCING (COMPONENT 11 & 12)
# -----------------------------------------------------------------------------
for rep in reports:
    r_id = rep["report_id"]
    lat = rep["location"]["latitude"]
    lon = rep["location"]["longitude"]
    pt = Point(lon, lat)
    
    # 1. Update Clustering Information
    c_id = assigned_cluster[r_id]
    cluster_info = next(c for c in clusters if c["cluster_id"] == c_id)
    rep["clustering_and_dedup"] = {
        "cluster_id": c_id,
        "is_cluster_primary": (r_id == cluster_info["primary_report_id"]),
        "cluster_member_count": cluster_info["member_count"],
        "deduplication_heuristic": f"{CLUSTER_RADIUS_M}m_prototype_heuristic"
    }
    
    # 2. Check spatial intersection with Component 11 runout corridors
    intersected_corridor = None
    min_dist_deg = 999999.0
    nearest_event_id = "NONE"
    
    for c_geom in corridor_geoms:
        poly = c_geom["geom"]
        if poly.contains(pt):
            intersected_corridor = c_geom
            min_dist_deg = 0.0
            nearest_event_id = c_geom["event_id"]
            break
        else:
            d = pt.distance(poly)
            if d < min_dist_deg:
                min_dist_deg = d
                nearest_event_id = c_geom["event_id"]
                
    # Approximate distance in meters
    dist_m = round(min_dist_deg * 111320.0, 1)
    
    if intersected_corridor:
        adv_info = advisories_by_event.get(nearest_event_id, {"tier": "TIER_1_HIGH"})
        rep["spatial_context"] = {
            "intersects_c11_runout": True,
            "nearest_c11_event_id": nearest_event_id,
            "distance_to_runout_m": 0.0,
            "intersected_corridor_tier": adv_info["tier"]
        }
    else:
        rep["spatial_context"] = {
            "intersects_c11_runout": False,
            "nearest_c11_event_id": nearest_event_id,
            "distance_to_runout_m": dist_m,
            "intersected_corridor_tier": "NONE"
        }
        
    # 3. Simulate Offline-to-Online Synchronization State Machine
    # Reports 1-10 are marked SYNCHRONIZED_LOCAL; 11-12 test the state transition
    if rep["system_state"]["sync_status"] == "OFFLINE_QUEUED":
        # Simulate synchronization event
        rep["system_state"]["sync_status"] = "SYNCHRONIZED_LOCAL"
        rep["system_state"]["sync_definition"] = "Report successfully incorporated into local prototype observation catalog."
        rep["system_state"]["sync_timestamp"] = now_str = "2026-09-07T17:25:00+05:30"
    else:
        rep["system_state"]["sync_definition"] = "Report successfully incorporated into local prototype observation catalog."
        rep["system_state"]["sync_timestamp"] = "2026-09-07T17:15:00+05:30"

# -----------------------------------------------------------------------------
# 5. PROTOTYPE FIELD VERIFICATION WORKFLOW SIMULATION
# -----------------------------------------------------------------------------
# Demonstrate human-in-the-loop review role for a subset of reports
# Report 1 (NH-06 Khliehriat cut) -> FIELD_VERIFIED
# Report 9 (Saiha residential slope) -> FIELD_VERIFIED
# Report 6 (Mawkyrwat roadside ditch) -> REJECTED_FALSE_ALARM
# Remaining 9 reports remain UNVERIFIED_OBSERVATION (the default)

reports[0]["system_state"]["verification_status"] = "FIELD_VERIFIED"
reports[0]["system_state"]["verified_by"] = "OFFICER-FIELD-MEG-04 (Prototype Field Role)"
reports[0]["system_state"]["verification_notes"] = "On-site visual inspection confirmed 12m tension crack with active surface water discharge along NH-06 cut."

reports[8]["system_state"]["verification_status"] = "FIELD_VERIFIED"
reports[8]["system_state"]["verified_by"] = "OFFICER-FIELD-MIZ-02 (Prototype Field Role)"
reports[8]["system_state"]["verification_notes"] = "Field verification confirmed outward soil toe displacement near Kaochao settlement road."

reports[5]["system_state"]["verification_status"] = "REJECTED_FALSE_ALARM"
reports[5]["system_state"]["verified_by"] = "OFFICER-FIELD-MEG-01 (Prototype Field Role)"
reports[5]["system_state"]["verification_notes"] = "Visual inspection confirmed shallow topsoil gravel wash from roadside drain, not deep-seated slope failure."

# -----------------------------------------------------------------------------
# 6. SAVE UPDATED OUTPUTS (GEOJSON & CSV)
# -----------------------------------------------------------------------------
geojson_features = []
csv_rows = []

for rep in reports:
    r_id = rep["report_id"]
    lon = rep["location"]["longitude"]
    lat = rep["location"]["latitude"]
    
    feat = {
        "type": "Feature",
        "id": r_id,
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "report_id": r_id,
            "record_type": "SYNTHETIC_DEMONSTRATION",
            "data_category": "CITIZEN_OBSERVATION",
            "timestamp": rep["timestamp_utc"],
            "category": rep["observation_details"]["category"],
            "displacement_width": rep["observation_details"]["displacement_width"],
            "water_seepage": rep["observation_details"]["water_seepage"],
            "seepage_flow_type": rep["observation_details"]["seepage_flow_type"],
            "structures_count": rep["observation_details"]["nearby_structures_count"],
            "corridor_proximity": rep["observation_details"]["corridor_proximity"],
            "slope_estimate_deg": 35.0,
            "crack_width_cm": 25.0,
            "gps_accuracy_m": 8.5,
            "state": rep["location"]["state"],
            "district": rep["location"]["district"],
            "nearest_settlement": rep["location"]["nearest_settlement"],
            "settlement_distance_km": rep["location"]["settlement_distance_km"],
            "cluster_id": rep["clustering_and_dedup"]["cluster_id"],
            "is_cluster_primary": rep["clustering_and_dedup"]["is_cluster_primary"],
            "cluster_member_count": rep["clustering_and_dedup"]["cluster_member_count"],
            "intersects_c11_runout": rep["spatial_context"]["intersects_c11_runout"],
            "nearest_c11_event_id": rep["spatial_context"]["nearest_c11_event_id"],
            "distance_to_runout_m": rep["spatial_context"]["distance_to_runout_m"],
            "sync_status": rep["system_state"]["sync_status"],
            "sync_definition": rep["system_state"]["sync_definition"],
            "verification_status": rep["system_state"]["verification_status"],
            "verified_by": rep["system_state"]["verified_by"],
            "media_attachments": [
                {
                    "attachment_id": f"ATT-{r_id}",
                    "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "mime_type": "image/jpeg",
                    "file_size_bytes": 1048576
                }
            ],
            "user_notes": rep["observation_details"]["user_notes"]
        }
    }
    geojson_features.append(feat)
    
    csv_rows.append({
        "report_id": r_id,
        "record_type": "SYNTHETIC_DEMONSTRATION",
        "data_category": "CITIZEN_OBSERVATION",
        "timestamp_utc": rep["timestamp_utc"],
        "latitude": lat,
        "longitude": lon,
        "state": rep["location"]["state"],
        "district": rep["location"]["district"],
        "nearest_settlement": rep["location"]["nearest_settlement"],
        "settlement_distance_km": rep["location"]["settlement_distance_km"],
        "category": rep["observation_details"]["category"],
        "displacement_width": rep["observation_details"]["displacement_width"],
        "water_seepage": rep["observation_details"]["water_seepage"],
        "seepage_flow_type": rep["observation_details"]["seepage_flow_type"],
        "nearby_structures_count": rep["observation_details"]["nearby_structures_count"],
        "corridor_proximity": rep["observation_details"]["corridor_proximity"],
        "slope_estimate_deg": 35.0,
        "crack_width_cm": 25.0,
        "gps_accuracy_m": 8.5,
        "cluster_id": rep["clustering_and_dedup"]["cluster_id"],
        "is_cluster_primary": rep["clustering_and_dedup"]["is_cluster_primary"],
        "cluster_member_count": rep["clustering_and_dedup"]["cluster_member_count"],
        "intersects_c11_runout": rep["spatial_context"]["intersects_c11_runout"],
        "nearest_c11_event_id": rep["spatial_context"]["nearest_c11_event_id"],
        "distance_to_runout_m": rep["spatial_context"]["distance_to_runout_m"],
        "sync_status": rep["system_state"]["sync_status"],
        "verification_status": rep["system_state"]["verification_status"]
    })

# Save updated JSON
with open(reports_json_fp, "w", encoding="utf-8") as f:
    json.dump(reports, f, indent=2)

# Save updated GeoJSON
geojson_collection = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Citizen_Ground_Observations",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": geojson_features
}
geojson_fp = os.path.join(DATA_DIR, "citizen_reports.geojson")
with open(geojson_fp, "w", encoding="utf-8") as f:
    json.dump(geojson_collection, f, indent=2)
print(f"Saved updated GeoJSON: {geojson_fp}")

# Save updated CSV
csv_fp = os.path.join(DATA_DIR, "citizen_reports.csv")
with open(csv_fp, "w", newline="", encoding="utf-8") as f:
    fieldnames = list(csv_rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in csv_rows:
        writer.writerow(r)
print(f"Saved updated CSV: {csv_fp}")

# Save Summary Metadata
summary = {
    "metadata": {
        "title": "NER-SAFE Component 13 Ingestion, Clustering & Verification Summary",
        "timestamp": "2026-09-07T17:25:00+05:30",
        "deduplication_model": {
            "parameter": "cluster_radius_meters",
            "distance_threshold_m": CLUSTER_RADIUS_M,
            "cluster_count": len(clusters),
            "status": "PROTOTYPE HEURISTIC ONLY (Non-Operational Standard)"
        },
        "offline_synchronization_model": {
            "storage_backend": "BROWSER_LOCALSTORAGE",
            "initial_queue_count": len(reports),
            "synchronized_local_count": len([r for r in reports if r["system_state"]["sync_status"] == "SYNCHRONIZED_LOCAL"]),
            "exact_state_definition": "Report successfully incorporated into local prototype observation catalog (Zero external network/government server transmission)."
        },
        "total_records": len(reports),
        "record_type_breakdown": {
            "SYNTHETIC_DEMONSTRATION": len(reports),
            "REAL_CITIZEN_REPORTS": 0
        },
        "sync_state_breakdown": {
            "SYNCHRONIZED_LOCAL": len([r for r in reports if r["system_state"]["sync_status"] == "SYNCHRONIZED_LOCAL"]),
            "OFFLINE_QUEUED": 0,
            "definition": "Report successfully incorporated into local prototype observation catalog (Zero external network/government server transmission)."
        },
        "verification_workflow": {
            "status_distribution": {
                "UNVERIFIED_OBSERVATION": len([r for r in reports if r["system_state"]["verification_status"] == "UNVERIFIED_OBSERVATION"]),
                "FIELD_VERIFIED": len([r for r in reports if r["system_state"]["verification_status"] == "FIELD_VERIFIED"]),
                "REJECTED_FALSE_ALARM": len([r for r in reports if r["system_state"]["verification_status"] == "REJECTED_FALSE_ALARM"])
            },
            "role_disclaimer": "PROTOTYPE WORKFLOW ROLE ONLY (No real government or statutory authority)"
        },
        "spatial_contextualization": {
            "intersecting_c11_corridor_count": len([r for r in reports if r["spatial_context"]["intersects_c11_runout"]]),
            "outside_corridor_count": len([r for r in reports if not r["spatial_context"]["intersects_c11_runout"]]),
            "average_distance_to_nearest_corridor_m": round(sum(r["spatial_context"]["distance_to_runout_m"] for r in reports) / len(reports), 1)
        },
        "clustering_results": clusters
    }
}

summary_fp = os.path.join(META_DIR, "report_ingestion_summary.json")
with open(summary_fp, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"Saved ingestion summary: {summary_fp}")

print("=" * 80)
print("STEP 2 COMPLETE: Deduplication clustering, spatial hazard overlay & verification states applied.")
print(f"  - Configurable Clustering Radius: {CLUSTER_RADIUS_M}m")
print(f"  - Total Clusters: {len(clusters)} (from {len(reports)} observations)")
print(f"  - Intersecting Component 11 Runouts: {summary['metadata']['spatial_contextualization']['intersecting_c11_corridor_count']}")
print(f"  - Verification Status: {summary['metadata']['verification_workflow']['status_distribution']['FIELD_VERIFIED']} Verified, {summary['metadata']['verification_workflow']['status_distribution']['REJECTED_FALSE_ALARM']} Rejected, {summary['metadata']['verification_workflow']['status_distribution']['UNVERIFIED_OBSERVATION']} Unverified")
print("=" * 80)
