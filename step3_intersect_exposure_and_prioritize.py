"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 11: Step 3 — Exposure Intersection & Impact Prioritization Engine

Intersects the 48 empirical runout corridors with Component 9 exposure layers:
1. Roads (45,315 segments): Classifies intersected highways (NH/SH/MDR), computes exposed length.
2. Buildings (296,690 footprints): Counts intersected structures and aggregate building area.
3. Settlements (976 populated places): Identifies intersected/proximal communities and population.
4. Transport Lifelines (75 facilities): Identifies critical helipads, airstrips, bus terminals.

Computes multi-criteria Impact Priority (CRITICAL, HIGH, MODERATE, LOW)
and derives comprehensive confidence metrics (Hazard, Flow-path, Runout, Impact, Overall).

Exports:
- event_records.csv
- event_records.geojson
- exposure_intersections.geojson
- impact_summary.csv
"""

import os
import json
import csv
import numpy as np
from shapely.geometry import shape, mapping, Point, LineString, Polygon, MultiPolygon
from shapely.strtree import STRtree

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE")
C11_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11")

CORRS_DIR = os.path.join(C11_DIR, "runout_corridors")
EVENTS_DIR = os.path.join(C11_DIR, "events")
EXP_OUT_DIR = os.path.join(C11_DIR, "exposure")
META_DIR = os.path.join(C11_DIR, "metadata")
os.makedirs(EXP_OUT_DIR, exist_ok=True)
os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 11: STEP 3 — EXPOSURE INTERSECTION & IMPACT ENGINE")
print("=" * 80)

# 1. Load Runout Corridors
corr_json_fp = os.path.join(CORRS_DIR, "runout_corridors.geojson")
with open(corr_json_fp, "r", encoding="utf-8") as f:
    corridors_data = json.load(f)

corridor_list = []
for feat in corridors_data["features"]:
    corridor_list.append({
        "event_id": feat["id"],
        "props": feat["properties"],
        "geom": shape(feat["geometry"])
    })

print(f"Loaded {len(corridor_list)} runout corridor polygons.")

# 2. Load & Index Roads
print("\nLoading and spatial-indexing roads (45,315 segments)...")
roads_fp = os.path.join(EXPOSURE_DIR, "roads", "NER_SAFE_Phase1_roads.geojson")
with open(roads_fp, "r", encoding="utf-8") as f:
    roads_data = json.load(f)

road_geoms = []
road_records = []
for idx, feat in enumerate(roads_data["features"]):
    g = shape(feat["geometry"])
    road_geoms.append(g)
    road_records.append({
        "idx": idx,
        "name": feat["properties"].get("name") or "Unnamed Road",
        "ref": feat["properties"].get("ref") or "",
        "fclass": feat["properties"].get("fclass") or "road",
        "geom": g
    })
road_tree = STRtree(road_geoms)
print(f"Road spatial index ready with {len(road_geoms)} elements.")

# 3. Load & Index Buildings
print("\nLoading and spatial-indexing buildings (296,690 footprints)...")
bldgs_fp = os.path.join(EXPOSURE_DIR, "buildings", "NER_SAFE_Phase1_buildings.geojson")
with open(bldgs_fp, "r", encoding="utf-8") as f:
    bldgs_data = json.load(f)

bldg_geoms = []
bldg_records = []
for idx, feat in enumerate(bldgs_data["features"]):
    g = shape(feat["geometry"])
    bldg_geoms.append(g)
    bldg_records.append({
        "idx": idx,
        "type": feat["properties"].get("type") or "building",
        "area_m2": feat["properties"].get("area_m2") or 85.0,
        "geom": g
    })
bldg_tree = STRtree(bldg_geoms)
print(f"Building spatial index ready with {len(bldg_geoms)} elements.")

# 4. Load & Index Settlements
print("\nLoading settlements (976 populated places)...")
settlements_fp = os.path.join(EXPOSURE_DIR, "settlements", "NER_SAFE_Phase1_settlements.geojson")
with open(settlements_fp, "r", encoding="utf-8") as f:
    settlements_data = json.load(f)

settlement_records = []
settlement_geoms = []
for idx, feat in enumerate(settlements_data["features"]):
    g = shape(feat["geometry"])
    settlement_geoms.append(g)
    settlement_records.append({
        "name": feat["properties"].get("name") or "Settlement",
        "fclass": feat["properties"].get("fclass") or "village",
        "pop": feat["properties"].get("population") or 0,
        "geom": g
    })
settlement_tree = STRtree(settlement_geoms)

# 5. Load Critical Transport Lifelines
print("\nLoading critical transport facilities (75 assets)...")
transport_fp = os.path.join(EXPOSURE_DIR, "transport", "NER_SAFE_Phase1_transport.geojson")
with open(transport_fp, "r", encoding="utf-8") as f:
    transport_data = json.load(f)

transport_records = []
transport_geoms = []
for idx, feat in enumerate(transport_data["features"]):
    g = shape(feat["geometry"])
    transport_geoms.append(g)
    transport_records.append({
        "name": feat["properties"].get("name") or "Transport Facility",
        "fclass": feat["properties"].get("fclass") or "transport",
        "geom": g
    })
transport_tree = STRtree(transport_geoms)

# 6. Execute Exposure Intersection
print("\nExecuting Spatial Exposure Intersection across all 48 runout corridors...")

event_final_records = []
exposure_geojson_features = []

for c_entry in corridor_list:
    event_id = c_entry["event_id"]
    props = c_entry["props"]
    c_poly = c_entry["geom"]
    
    # A. Intersect Roads
    cand_road_indices = road_tree.query(c_poly)
    roads_exposed_count = 0
    roads_exposed_length_m = 0.0
    highest_road_class = "None"
    road_names = set()
    has_nh = False
    has_sh = False
    has_mdr = False
    
    for r_idx in cand_road_indices:
        r_rec = road_records[r_idx]
        if c_poly.intersects(r_rec["geom"]):
            roads_exposed_count += 1
            fclass = r_rec["fclass"].lower()
            ref_str = r_rec["ref"].upper()
            name_str = r_rec["name"]
            
            if "NH" in ref_str or fclass in ["trunk", "primary", "motorway"]:
                has_nh = True
                highest_road_class = "National Highway"
            elif fclass == "secondary" and not has_nh:
                has_sh = True
                highest_road_class = "State Highway"
            elif fclass == "tertiary" and not (has_nh or has_sh):
                has_mdr = True
                highest_road_class = "Major District Road"
            elif highest_road_class == "None":
                highest_road_class = "Local / Rural Road"
                
            if name_str and name_str != "Unnamed Road":
                road_names.add(name_str)
            elif ref_str:
                road_names.add(ref_str)
                
            # Intersected road geometry for visualization
            inter_line = c_poly.intersection(r_rec["geom"])
            if not inter_line.is_empty:
                # Approximate length in meters (~111,000 m/deg)
                roads_exposed_length_m += inter_line.length * 111000.0
                exposure_geojson_features.append({
                    "type": "Feature",
                    "properties": {
                        "event_id": event_id,
                        "asset_type": "Road",
                        "name": r_rec["name"],
                        "fclass": r_rec["fclass"],
                        "ref": r_rec["ref"]
                    },
                    "geometry": mapping(inter_line)
                })
                
    roads_exposed_length_m = round(roads_exposed_length_m, 1)
    
    # B. Intersect Buildings
    cand_bldg_indices = bldg_tree.query(c_poly)
    buildings_exposed_count = 0
    buildings_exposed_area_m2 = 0.0
    
    for b_idx in cand_bldg_indices:
        b_rec = bldg_records[b_idx]
        if c_poly.intersects(b_rec["geom"]):
            buildings_exposed_count += 1
            buildings_exposed_area_m2 += b_rec["area_m2"]
            exposure_geojson_features.append({
                "type": "Feature",
                "properties": {
                    "event_id": event_id,
                    "asset_type": "Building",
                    "bldg_type": b_rec["type"],
                    "area_m2": round(b_rec["area_m2"], 1)
                },
                "geometry": mapping(b_rec["geom"])
            })
            
    buildings_exposed_area_m2 = round(buildings_exposed_area_m2, 1)
    
    # C. Intersect Settlements (Corridor or within 200m buffer)
    c_poly_buf = c_poly.buffer(200.0 / 111000.0)
    cand_settle_indices = settlement_tree.query(c_poly_buf)
    settlements_exposed_count = 0
    settlement_names_set = set()
    est_population_exposed = 0
    
    for s_idx in cand_settle_indices:
        s_rec = settlement_records[s_idx]
        if c_poly_buf.intersects(s_rec["geom"]):
            settlements_exposed_count += 1
            settlement_names_set.add(s_rec["name"])
            if s_rec["pop"] > 0:
                est_population_exposed += int(s_rec["pop"])
            exposure_geojson_features.append({
                "type": "Feature",
                "properties": {
                    "event_id": event_id,
                    "asset_type": "Settlement",
                    "name": s_rec["name"],
                    "fclass": s_rec["fclass"]
                },
                "geometry": mapping(s_rec["geom"])
            })
            
    # Population proxy from building footprints if census settlement population was null
    if est_population_exposed == 0 and buildings_exposed_count > 0:
        # Census average household size in Northeast is 4.6 persons per occupied household
        est_population_exposed = int(round(buildings_exposed_count * 4.6))
        
    # D. Intersect Critical Transport Facilities
    cand_trans_indices = transport_tree.query(c_poly_buf)
    crit_transport_count = 0
    crit_transport_names = set()
    
    for t_idx in cand_trans_indices:
        t_rec = transport_records[t_idx]
        if c_poly_buf.intersects(t_rec["geom"]):
            crit_transport_count += 1
            crit_transport_names.add(t_rec["name"])
            exposure_geojson_features.append({
                "type": "Feature",
                "properties": {
                    "event_id": event_id,
                    "asset_type": "Transport_Lifeline",
                    "name": t_rec["name"],
                    "fclass": t_rec["fclass"]
                },
                "geometry": mapping(t_rec["geom"])
            })
            
    # -------------------------------------------------------------------------
    # 7. Impact Prioritization Formulation
    # -------------------------------------------------------------------------
    # Consequence Score calculation (0 to 100 points)
    consequence_pts = 0.0
    
    # Road weight (up to 40 pts)
    if has_nh:
        consequence_pts += 40.0
    elif has_sh:
        consequence_pts += 25.0
    elif has_mdr:
        consequence_pts += 15.0
    elif roads_exposed_count > 0:
        consequence_pts += 8.0
        
    # Building weight (up to 30 pts)
    consequence_pts += min(30.0, buildings_exposed_count * 4.0)
    
    # Settlement & Population weight (up to 20 pts)
    if settlements_exposed_count > 0:
        consequence_pts += 10.0
    if est_population_exposed > 50:
        consequence_pts += 10.0
    elif est_population_exposed > 0:
        consequence_pts += 5.0
        
    # Critical Transport weight (up to 10 pts)
    if crit_transport_count > 0:
        consequence_pts += 10.0
        
    consequence_score = round(min(1.0, consequence_pts / 100.0), 3)
    
    # Combined Impact Priority Score: 50% Hazard Risk + 50% Consequence
    hazard_score = props["combined_risk_score"]
    impact_score = round(0.50 * hazard_score + 0.50 * consequence_score, 3)
    
    # Priority Tiers
    if impact_score >= 0.50 or has_nh or buildings_exposed_count >= 10:
        impact_priority = "CRITICAL"
    elif impact_score >= 0.38 or has_sh or buildings_exposed_count >= 3:
        impact_priority = "HIGH"
    elif impact_score >= 0.28 or roads_exposed_count > 0 or buildings_exposed_count > 0:
        impact_priority = "MODERATE"
    else:
        impact_priority = "LOW"
        
    # -------------------------------------------------------------------------
    # 8. Multi-Component Confidence Evaluation
    # -------------------------------------------------------------------------
    hazard_conf = round(max(0.40, 1.0 - props["uncertainty"]), 2)
    flow_path_conf = props["flow_path_confidence"]
    runout_conf = props["runout_confidence"]
    impact_conf = round(min(1.0, 0.65 + 0.20 * (1 if roads_exposed_count > 0 else 0) + 0.15 * (1 if buildings_exposed_count > 0 else 0)), 2)
    overall_conf = round(0.30 * hazard_conf + 0.30 * flow_path_conf + 0.20 * runout_conf + 0.20 * impact_conf, 2)
    
    rec = {
        "event_id": event_id,
        "state": props["state"],
        "district": props["district"],
        "latitude": props["latitude"],
        "longitude": props["longitude"],
        "risk_score": props["combined_risk_score"],
        "risk_class": props["risk_class"],
        "susceptibility": props["susceptibility"],
        "dynamic_trigger": props["dynamic_trigger"],
        "uncertainty": props["uncertainty"],
        "elevation_init_m": props["elevation_init_m"],
        "elevation_end_m": props["elevation_end_m"],
        "elevation_drop_m": props["elevation_drop_m"],
        "path_length_m": props["path_length_m"],
        "runout_area_m2": props["runout_area_m2"],
        "stopping_reason": props["stopping_reason"],
        "roads_exposed": roads_exposed_count,
        "roads_exposed_length_m": roads_exposed_length_m,
        "highest_road_class": highest_road_class,
        "exposed_road_names": "; ".join(sorted(list(road_names))) if road_names else "None",
        "buildings_exposed": buildings_exposed_count,
        "buildings_exposed_area_m2": buildings_exposed_area_m2,
        "settlements_exposed": settlements_exposed_count,
        "exposed_settlement_names": "; ".join(sorted(list(settlement_names_set))) if settlement_names_set else "None",
        "population_exposed": est_population_exposed,
        "critical_infrastructure_exposed": crit_transport_count,
        "consequence_score": consequence_score,
        "impact_score": impact_score,
        "impact_priority": impact_priority,
        "hazard_confidence": hazard_conf,
        "flow_path_confidence": flow_path_conf,
        "runout_confidence": runout_conf,
        "impact_confidence": impact_conf,
        "overall_confidence": overall_conf,
        "model_version": "Component 11 (v1.0.0-MVP)",
        "nearest_settlement": props["nearest_settlement"],
        "settlement_distance_km": props["settlement_distance_km"]
    }
    event_final_records.append(rec)

print(f"\nExposure intersection complete across all {len(event_final_records)} events.")

# Sort by impact score descending
event_final_records.sort(key=lambda x: x["impact_score"], reverse=True)

# 9. Priority Breakdown Summary
from collections import Counter
p_counts = Counter(r["impact_priority"] for r in event_final_records)
print(f"\nImpact Priority Distribution:")
for p_level in ["CRITICAL", "HIGH", "MODERATE", "LOW"]:
    print(f" - {p_level:<10}: {p_counts.get(p_level, 0)} events")

# 10. Write Event Records CSV
csv_fp = os.path.join(EVENTS_DIR, "event_records.csv")
with open(csv_fp, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(event_final_records[0].keys()))
    writer.writeheader()
    writer.writerows(event_final_records)
print(f"\nSaved structured event records table to {csv_fp}")

# 11. Write Event Records GeoJSON (Points)
event_geojson_features = []
for r in event_final_records:
    event_geojson_features.append({
        "type": "Feature",
        "id": r["event_id"],
        "properties": r,
        "geometry": {
            "type": "Point",
            "coordinates": [r["longitude"], r["latitude"]]
        }
    })

event_geojson = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Phase1_Landslide_Event_Records",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": event_geojson_features
}
event_geojson_fp = os.path.join(EVENTS_DIR, "event_records.geojson")
with open(event_geojson_fp, "w", encoding="utf-8") as f:
    json.dump(event_geojson, f, indent=2)
print(f"Saved event records GeoJSON to {event_geojson_fp}")

# 12. Write Exposure Intersections GeoJSON
exp_inter_geojson = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Phase1_Exposed_Infrastructure",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": exposure_geojson_features
}
exp_inter_fp = os.path.join(EXP_OUT_DIR, "exposure_intersections.geojson")
with open(exp_inter_fp, "w", encoding="utf-8") as f:
    json.dump(exp_inter_geojson, f, indent=2)
print(f"Saved {len(exposure_geojson_features)} exposed asset geometries to {exp_inter_fp}")

# 13. Write Impact Summary CSV
district_summary = {}
for r in event_final_records:
    key = (r["state"], r["district"])
    if key not in district_summary:
        district_summary[key] = {
            "state": r["state"],
            "district": r["district"],
            "total_events": 0,
            "critical_events": 0,
            "high_events": 0,
            "moderate_events": 0,
            "low_events": 0,
            "total_buildings_exposed": 0,
            "total_road_length_m_exposed": 0.0,
            "total_pop_exposed": 0,
            "mean_risk_score": 0.0
        }
    ds = district_summary[key]
    ds["total_events"] += 1
    if r["impact_priority"] == "CRITICAL": ds["critical_events"] += 1
    elif r["impact_priority"] == "HIGH": ds["high_events"] += 1
    elif r["impact_priority"] == "MODERATE": ds["moderate_events"] += 1
    else: ds["low_events"] += 1
    ds["total_buildings_exposed"] += r["buildings_exposed"]
    ds["total_road_length_m_exposed"] += r["roads_exposed_length_m"]
    ds["total_pop_exposed"] += r["population_exposed"]
    ds["mean_risk_score"] += r["risk_score"]

summary_rows = []
for key, ds in sorted(district_summary.items()):
    ds["mean_risk_score"] = round(ds["mean_risk_score"] / ds["total_events"], 3)
    ds["total_road_length_m_exposed"] = round(ds["total_road_length_m_exposed"], 1)
    summary_rows.append(ds)

summary_csv_fp = os.path.join(EXP_OUT_DIR, "impact_summary.csv")
with open(summary_csv_fp, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
    writer.writeheader()
    writer.writerows(summary_rows)
print(f"Saved impact summary table to {summary_csv_fp}")

# Mirror deliverables to project root
import shutil
shutil.copy(csv_fp, os.path.join(PROJECT_ROOT, "event_records.csv"))
shutil.copy(event_geojson_fp, os.path.join(PROJECT_ROOT, "event_records.geojson"))
shutil.copy(exp_inter_fp, os.path.join(PROJECT_ROOT, "exposure_intersections.geojson"))
shutil.copy(summary_csv_fp, os.path.join(PROJECT_ROOT, "impact_summary.csv"))

print("=" * 80)
print("STEP 3 COMPLETE: Exposure Intersection & Impact Prioritization Finished!")
print("=" * 80)
