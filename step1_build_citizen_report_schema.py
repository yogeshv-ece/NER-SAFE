#!/usr/bin/env python3
"""
NER-SAFE — COMPONENT 13: STEP 1
Citizen Ground Hazard Reporting Schema & Synthetic Benchmark Dataset Generator
Authoritative Point-in-Polygon AOI Validation using Survey of India / geoBoundaries Phase 1 Data
Nearest Settlement Association using Phase 1 Verified Settlement Catalog
Author: NER-SAFE Research & Development Team
Date: September 2026
"""

import os
import json
import csv
import math
from datetime import datetime
from shapely.geometry import Point, shape

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
C13_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_13")
SCHEMA_DIR = os.path.join(C13_DIR, "schema")
DATA_DIR = os.path.join(C13_DIR, "data")
META_DIR = os.path.join(C13_DIR, "metadata")
REPORTS_DIR = os.path.join(C13_DIR, "reports")
APP_DIR = os.path.join(C13_DIR, "app")

os.makedirs(SCHEMA_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(APP_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 13: STEP 1 — CITIZEN REPORT SCHEMA & BENCHMARK GENERATOR")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. LOAD AUTHORITATIVE PHASE 1 ADMINISTRATIVE & SETTLEMENT LAYERS
# -----------------------------------------------------------------------------
ADMIN_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE", "administrative")
SETTLE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE", "settlements")

states_fp = os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_states.geojson")
districts_fp = os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_districts.geojson")
settlements_fp = os.path.join(SETTLE_DIR, "NER_SAFE_Phase1_settlements.geojson")

with open(states_fp, "r", encoding="utf-8") as f:
    states_data = json.load(f)
with open(districts_fp, "r", encoding="utf-8") as f:
    districts_data = json.load(f)
with open(settlements_fp, "r", encoding="utf-8") as f:
    settlements_data = json.load(f)

print(f"Loaded {len(states_data['features'])} state boundaries, {len(districts_data['features'])} districts, and {len(settlements_data['features'])} settlements.")

state_polygons = []
for feat in states_data["features"]:
    state_name = feat["properties"].get("state_name") or feat["properties"].get("shapeName") or feat["properties"].get("name")
    geom = shape(feat["geometry"])
    state_polygons.append({"name": state_name, "geom": geom})

district_polygons = []
for feat in districts_data["features"]:
    dist_name = feat["properties"].get("shapeName") or feat["properties"].get("district") or feat["properties"].get("name")
    parent_state = feat["properties"].get("state") or feat["properties"].get("shapeGroup") or ""
    geom = shape(feat["geometry"])
    district_polygons.append({"district": dist_name, "state": parent_state, "geom": geom})

settlement_points = []
for feat in settlements_data["features"]:
    s_props = feat["properties"]
    s_name = s_props.get("name") or s_props.get("place") or "Settlement"
    coords = feat["geometry"]["coordinates"]
    s_dist = s_props.get("district", "")
    s_state = s_props.get("state", "")
    settlement_points.append({
        "name": s_name,
        "lon": coords[0],
        "lat": coords[1],
        "district": s_dist,
        "state": s_state
    })

def validate_point_in_phase1(lon, lat):
    """Authoritative point-in-polygon validation against Survey of India / geoBoundaries Phase 1 boundaries"""
    pt = Point(lon, lat)
    found_state = None
    found_district = None
    
    for sp in state_polygons:
        if sp["geom"].contains(pt):
            found_state = sp["name"]
            break
            
    if found_state:
        for dp in district_polygons:
            if dp["geom"].contains(pt):
                found_district = dp["district"]
                break
                
    return found_state, found_district

def find_nearest_settlement(lon, lat, state_hint=None):
    """Derives nearest settlement from verified Phase 1 settlement catalog using spherical distance"""
    best_name = "Unknown"
    min_dist_km = 999999.0
    best_dist = ""
    
    for s in settlement_points:
        dlat = math.radians(s["lat"] - lat)
        dlon = math.radians(s["lon"] - lon)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(s["lat"])) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_km = 6371.0 * c
        
        if dist_km < min_dist_km:
            min_dist_km = dist_km
            best_name = s["name"]
            best_dist = s["district"]
            
    return best_name, round(min_dist_km, 2)

# -----------------------------------------------------------------------------
# 2. GENERATE FORMAL CITIZEN REPORT JSON SCHEMA
# -----------------------------------------------------------------------------
report_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "NER-SAFE Citizen Ground Hazard Observation Report",
    "description": "Standardized schema for crowdsourced community landslide hazard observations in Phase 1 (Meghalaya & Mizoram)",
    "type": "object",
    "required": [
        "report_id", "record_type", "timestamp_utc", "reporter", "location",
        "observation_details", "media", "system_state"
    ],
    "properties": {
        "report_id": {
            "type": "string",
            "pattern": "^REP-\\d{8}-[A-Z]{3}-\\d{3}$"
        },
        "record_type": {
            "type": "string",
            "enum": ["CITIZEN_OBSERVATION", "SYNTHETIC_DEMONSTRATION", "FIELD_VERIFIED_OBSERVATION"]
        },
        "timestamp_utc": {
            "type": "string",
            "format": "date-time"
        },
        "reporter": {
            "type": "object",
            "required": ["role", "anonymous_id", "contact_provided"],
            "properties": {
                "role": {"type": "string", "enum": ["CITIZEN", "FIELD_OFFICIAL_PROTOTYPE"]},
                "anonymous_id": {"type": "string"},
                "contact_provided": {"type": "boolean"}
            }
        },
        "location": {
            "type": "object",
            "required": ["latitude", "longitude", "accuracy_m", "state", "district", "nearest_settlement", "within_phase1_aoi"],
            "properties": {
                "latitude": {"type": "number", "minimum": 21.0, "maximum": 27.0},
                "longitude": {"type": "number", "minimum": 89.0, "maximum": 94.0},
                "accuracy_m": {"type": "number", "minimum": 0.0},
                "state": {"type": "string", "enum": ["Meghalaya", "Mizoram"]},
                "district": {"type": "string"},
                "nearest_settlement": {"type": "string"},
                "settlement_distance_km": {"type": "number"},
                "within_phase1_aoi": {"type": "boolean", "const": True}
            }
        },
        "observation_details": {
            "type": "object",
            "required": [
                "category", "displacement_width", "water_seepage",
                "seepage_flow_type", "nearby_structures_count", "corridor_proximity"
            ],
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "SURFACE_TENSION_CRACK",
                        "SLOPE_BULGE_HEAVE",
                        "WATER_SEEPAGE_SPRING",
                        "ROCKFALL_MINOR_SLUMP",
                        "ROAD_SCARP_SETTLEMENT"
                    ]
                },
                "displacement_width": {
                    "type": "string",
                    "enum": ["LESS_THAN_5_CM", "5_TO_15_CM", "15_TO_50_CM", "GREATER_THAN_50_CM"]
                },
                "water_seepage": {"type": "boolean"},
                "seepage_flow_type": {
                    "type": "string",
                    "enum": ["DRY", "DAMP_SOIL", "CLEAR_TRICKLE", "MUDDY_TURBID_FLOW"]
                },
                "nearby_structures_count": {
                    "type": "string",
                    "enum": ["NONE_0", "FEW_1_TO_5", "MODERATE_6_TO_15", "DENSE_GREATER_THAN_15"]
                },
                "corridor_proximity": {"type": "string"},
                "user_notes": {"type": "string"}
            }
        },
        "media": {
            "type": "object",
            "required": ["has_attachment", "attachment_type", "media_source"],
            "properties": {
                "has_attachment": {"type": "boolean"},
                "attachment_type": {"type": "string", "enum": ["PHOTO", "VIDEO", "NONE"]},
                "media_source": {"type": "string", "enum": ["USER_CAPTURE", "SIMULATED_DEMO_MEDIA", "LOCAL_BENCHMARK"]},
                "media_hash_sha256": {"type": "string"},
                "caption": {"type": "string"}
            }
        },
        "spatial_context": {
            "type": "object",
            "properties": {
                "intersects_c11_runout": {"type": "boolean"},
                "nearest_c11_event_id": {"type": "string"},
                "distance_to_runout_m": {"type": "number"},
                "intersected_corridor_tier": {"type": "string"}
            }
        },
        "clustering_and_dedup": {
            "type": "object",
            "properties": {
                "cluster_id": {"type": "string"},
                "is_cluster_primary": {"type": "boolean"},
                "cluster_member_count": {"type": "integer", "minimum": 1},
                "deduplication_heuristic": {"type": "string"}
            }
        },
        "system_state": {
            "type": "object",
            "required": ["sync_status", "verification_status"],
            "properties": {
                "sync_status": {
                    "type": "string",
                    "enum": ["OFFLINE_QUEUED", "SYNC_PENDING", "SYNCHRONIZED_LOCAL"]
                },
                "sync_definition": {
                    "type": "string",
                    "const": "Report successfully incorporated into local prototype observation catalog."
                },
                "verification_status": {
                    "type": "string",
                    "enum": ["UNVERIFIED_OBSERVATION", "FIELD_VERIFIED", "REJECTED_FALSE_ALARM"]
                },
                "verified_by": {"type": ["string", "null"]},
                "verification_notes": {"type": "string"}
            }
        }
    }
}

schema_fp = os.path.join(SCHEMA_DIR, "citizen_report_schema.json")
with open(schema_fp, "w", encoding="utf-8") as f:
    json.dump(report_schema, f, indent=2)
print(f"Saved formal schema: {schema_fp}")

# -----------------------------------------------------------------------------
# 3. GENERATE SYNTHETIC DEMONSTRATION OBSERVATION DATASET
# -----------------------------------------------------------------------------
# Benchmark test locations across vulnerable Phase 1 hill districts
# Coordinates designed to test both proximate clusters (within 50m) and isolated sites
CANDIDATE_COORDS = [
    # Meghalaya: East Jaintia Hills (within EVT-MEG-023 runout corridor near NH-06)
    {"lat": 25.150417, "lon": 92.369028, "cat": "SURFACE_TENSION_CRACK", "w": "15_TO_50_CM", "seep": True, "st": "MUDDY_TURBID_FLOW", "b": "FEW_1_TO_5", "road": "NH-06 Khliehriat Cut", "notes": "Longitudinal tension crack developing on cut slope above highway"},
    {"lat": 25.150550, "lon": 92.369150, "cat": "SURFACE_TENSION_CRACK", "w": "5_TO_15_CM", "seep": True, "st": "CLEAR_TRICKLE", "b": "FEW_1_TO_5", "road": "NH-06 Khliehriat Bypass", "notes": "Duplicate report: Tension crack 18m north of first scarp"},
    # Meghalaya: East Khasi Hills (Pynursla / Sohra ridge)
    {"lat": 25.2950, "lon": 91.8980, "cat": "WATER_SEEPAGE_SPRING", "w": "LESS_THAN_5_CM", "seep": True, "st": "MUDDY_TURBID_FLOW", "b": "MODERATE_6_TO_15", "road": "Pynursla-Dawki Road", "notes": "Sudden muddy spring emerged from retaining wall weeping holes"},
    {"lat": 25.2952, "lon": 91.8982, "cat": "SLOPE_BULGE_HEAVE", "w": "5_TO_15_CM", "seep": True, "st": "DAMP_SOIL", "b": "MODERATE_6_TO_15", "road": "Pynursla-Dawki Road", "notes": "Duplicate observation: Toe of slope showing visible bulging adjacent to muddy spring"},
    # Meghalaya: West Jaintia Hills (Jowai slopes)
    {"lat": 25.4410, "lon": 92.2050, "cat": "ROAD_SCARP_SETTLEMENT", "w": "15_TO_50_CM", "seep": False, "st": "DRY", "b": "FEW_1_TO_5", "road": "Old Jowai Road", "notes": "Outward road shoulder settlement and asphalt tearing along curve"},
    # Meghalaya: South West Khasi Hills (Mawkyrwat hill slope)
    {"lat": 25.3520, "lon": 91.4550, "cat": "ROCKFALL_MINOR_SLUMP", "w": "LESS_THAN_5_CM", "seep": False, "st": "DRY", "b": "NONE_0", "road": "Mawkyrwat Hill Road", "notes": "Shale boulders and loose gravel deposited onto roadside drainage ditch"},
    
    # Mizoram: Kolasib (near NH-54 corridor)
    {"lat": 24.2250, "lon": 92.6820, "cat": "SURFACE_TENSION_CRACK", "w": "5_TO_15_CM", "seep": True, "st": "CLEAR_TRICKLE", "b": "FEW_1_TO_5", "road": "NH-54 Bilkhawthlir Cut", "notes": "Fresh tension fissure visible on upper garden terrace overlooking road"},
    {"lat": 24.2252, "lon": 92.6822, "cat": "SURFACE_TENSION_CRACK", "w": "5_TO_15_CM", "seep": True, "st": "CLEAR_TRICKLE", "b": "FEW_1_TO_5", "road": "NH-54 Bilkhawthlir Cut", "notes": "Duplicate report: Second neighbor reporting same scarp fissure 30m away"},
    # Mizoram: Saiha (within EVT-MIZ-018 runout corridor near Kaochao 'E')
    {"lat": 22.402083, "lon": 92.954583, "cat": "SLOPE_BULGE_HEAVE", "w": "GREATER_THAN_50_CM", "seep": True, "st": "MUDDY_TURBID_FLOW", "b": "DENSE_GREATER_THAN_15", "road": "Kaochao Approach Road", "notes": "Significant downslope bulging above residential houses following continuous rain"},
    {"lat": 22.402200, "lon": 92.954650, "cat": "SURFACE_TENSION_CRACK", "w": "15_TO_50_CM", "seep": True, "st": "MUDDY_TURBID_FLOW", "b": "DENSE_GREATER_THAN_15", "road": "Kaochao Approach Road", "notes": "Duplicate observation: 15m away along upper crown of same scarp"},
    # Mizoram: Lunglei (Ridge road)
    {"lat": 22.8870, "lon": 92.7350, "cat": "ROAD_SCARP_SETTLEMENT", "w": "15_TO_50_CM", "seep": False, "st": "DAMP_SOIL", "b": "FEW_1_TO_5", "road": "Lunglei Bypass", "notes": "Road foundation cracking and tilt on downhill culvert headwall"},
    # Mizoram: Mamit (Forested cut slope)
    {"lat": 23.9280, "lon": 92.4880, "cat": "ROCKFALL_MINOR_SLUMP", "w": "LESS_THAN_5_CM", "seep": False, "st": "DRY", "b": "NONE_0", "road": "Mamit-Zawlnuam Corridor", "notes": "Minor debris slump blocking half of single-lane earth road"},
    # Mizoram: Lawngtlai (Southern hills)
    {"lat": 22.5250, "lon": 92.8950, "cat": "SURFACE_TENSION_CRACK", "w": "5_TO_15_CM", "seep": True, "st": "DAMP_SOIL", "b": "NONE_0", "road": "Southern Border Connector", "notes": "Arcuate ground fissure across agricultural terrace"}
]

synthetic_reports = []
geojson_features = []
csv_rows = []

now_str = "2026-09-07T17:15:00+05:30"

for idx, c in enumerate(CANDIDATE_COORDS):
    lat = c["lat"]
    lon = c["lon"]
    
    # Authoritative point-in-polygon validation against Survey of India / geoBoundaries
    val_state, val_dist = validate_point_in_phase1(lon, lat)
    if not val_state:
        print(f"Warning: Point {lat}, {lon} outside Phase 1 state boundaries; skipping.")
        continue
        
    # Nearest settlement derivation from verified Phase 1 settlement catalog
    near_settlement, dist_km = find_nearest_settlement(lon, lat, val_state)
    
    rep_num = idx + 1
    state_code = "MEG" if "Meghalaya" in val_state else "MIZ"
    rep_id = f"REP-20260907-{state_code}-{rep_num:03d}"
    anon_user = f"USER-anon-{idx*17 + 101:04x}"
    
    report_obj = {
        "report_id": rep_id,
        "record_type": "SYNTHETIC_DEMONSTRATION",
        "data_category": "CITIZEN_OBSERVATION",
        "timestamp_utc": now_str,
        "reporter": {
            "role": "CITIZEN",
            "anonymous_id": anon_user,
            "contact_provided": False
        },
        "location": {
            "latitude": lat,
            "longitude": lon,
            "accuracy_m": 8.5,
            "state": "Meghalaya" if "Meghalaya" in val_state else "Mizoram",
            "district": val_dist if val_dist else "Hill District",
            "nearest_settlement": near_settlement,
            "settlement_distance_km": dist_km,
            "within_phase1_aoi": True
        },
        "observation_details": {
            "category": c["cat"],
            "displacement_width": c["w"],
            "water_seepage": c["seep"],
            "seepage_flow_type": c["st"],
            "nearby_structures_count": c["b"],
            "corridor_proximity": c["road"],
            "slope_estimate_deg": 35.0,
            "crack_width_cm": 25.0,
            "user_notes": c["notes"]
        },
        "media": {
            "has_attachment": True,
            "attachment_type": "PHOTO",
            "media_source": "SIMULATED_DEMO_MEDIA",
            "media_hash_sha256": f"demo_sha256_hash_obs_{rep_num:03d}_{state_code.lower()}",
            "mime_type": "image/jpeg",
            "file_size_bytes": 1048576,
            "caption": f"Simulated ground photo showing {c['cat'].lower().replace('_', ' ')} near {c['road']}"
        },
        "spatial_context": {
            "intersects_c11_runout": False,
            "nearest_c11_event_id": "PENDING_CALCULATION",
            "distance_to_runout_m": 0.0,
            "intersected_corridor_tier": "NONE"
        },
        "clustering_and_dedup": {
            "cluster_id": "UNCLUSTERED",
            "is_cluster_primary": True,
            "cluster_member_count": 1,
            "deduplication_heuristic": "50m_prototype_heuristic"
        },
        "system_state": {
            "sync_status": "SYNCHRONIZED_LOCAL" if idx < 10 else "OFFLINE_QUEUED",
            "sync_definition": "Report successfully incorporated into local prototype observation catalog.",
            "verification_status": "UNVERIFIED_OBSERVATION",
            "verified_by": None,
            "verification_notes": "Initial crowdsourced submission. Pending field inspection."
        }
    }
    
    synthetic_reports.append(report_obj)
    
    # GeoJSON Feature representation
    feat = {
        "type": "Feature",
        "id": rep_id,
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat]
        },
        "properties": {
            "report_id": rep_id,
            "record_type": "SYNTHETIC_DEMONSTRATION",
            "data_category": "CITIZEN_OBSERVATION",
            "timestamp": now_str,
            "category": c["cat"],
            "displacement_width": c["w"],
            "water_seepage": c["seep"],
            "seepage_flow_type": c["st"],
            "structures_count": c["b"],
            "corridor_proximity": c["road"],
            "slope_estimate_deg": 35.0,
            "crack_width_cm": 25.0,
            "gps_accuracy_m": 8.5,
            "state": report_obj["location"]["state"],
            "district": report_obj["location"]["district"],
            "nearest_settlement": near_settlement,
            "settlement_distance_km": dist_km,
            "sync_status": report_obj["system_state"]["sync_status"],
            "verification_status": "UNVERIFIED_OBSERVATION",
            "media_attachments": [
                {
                    "attachment_id": f"ATT-{rep_id}",
                    "sha256_hash": f"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "mime_type": "image/jpeg",
                    "file_size_bytes": 1048576
                }
            ],
            "user_notes": c["notes"]
        }
    }
    geojson_features.append(feat)
    
    # CSV row representation
    csv_rows.append({
        "report_id": rep_id,
        "record_type": "SYNTHETIC_DEMONSTRATION",
        "data_category": "CITIZEN_OBSERVATION",
        "timestamp_utc": now_str,
        "latitude": lat,
        "longitude": lon,
        "state": report_obj["location"]["state"],
        "district": report_obj["location"]["district"],
        "nearest_settlement": near_settlement,
        "settlement_distance_km": dist_km,
        "category": c["cat"],
        "displacement_width": c["w"],
        "water_seepage": c["seep"],
        "seepage_flow_type": c["st"],
        "nearby_structures_count": c["b"],
        "corridor_proximity": c["road"],
        "slope_estimate_deg": 35.0,
        "crack_width_cm": 25.0,
        "gps_accuracy_m": 8.5,
        "sync_status": report_obj["system_state"]["sync_status"],
        "verification_status": "UNVERIFIED_OBSERVATION"
    })

# Save synthetic benchmark records JSON
bench_fp = os.path.join(DATA_DIR, "synthetic_demonstration_reports.json")
with open(bench_fp, "w", encoding="utf-8") as f:
    json.dump(synthetic_reports, f, indent=2)
print(f"Saved synthetic reports benchmark JSON: {bench_fp} ({len(synthetic_reports)} records)")

# Save initial GeoJSON
geojson_collection = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Citizen_Ground_Observations",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": geojson_features
}
geojson_fp = os.path.join(DATA_DIR, "citizen_reports.geojson")
with open(geojson_fp, "w", encoding="utf-8") as f:
    json.dump(geojson_collection, f, indent=2)
print(f"Saved citizen reports GeoJSON: {geojson_fp}")

# Save initial CSV
csv_fp = os.path.join(DATA_DIR, "citizen_reports.csv")
with open(csv_fp, "w", newline="", encoding="utf-8") as f:
    fieldnames = list(csv_rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in csv_rows:
        writer.writerow(r)
print(f"Saved citizen reports CSV: {csv_fp}")

print("=" * 80)
print(f"STEP 1 COMPLETE: Schema and {len(synthetic_reports)} benchmark observations generated.")
print("  - All coordinates validated via authoritative point-in-polygon survey boundaries.")
print("  - Nearest settlements derived from verified Phase 1 settlement points.")
print("  - All records explicitly labeled record_type = 'SYNTHETIC_DEMONSTRATION'.")
print("=" * 80)
