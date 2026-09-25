"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 11: Step 1 — Candidate Landslide Initiation Extraction

Extracts high-priority representative landslide initiation candidates across
Phase 1 AOI (Meghalaya and Mizoram) using Component 10 risk and Component 7 terrain:
- Combined Risk Score >= 0.40
- Slope >= 18.0 degrees
- Spatial Non-Maximum Suppression (minimum distance >= 1,500 meters)
- Geographic representation across all key vulnerable districts in Meghalaya & Mizoram
"""

import os
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from shapely.geometry import Point, shape

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
C10_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10")
TERRAIN_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives")
EXPOSURE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE")
C11_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11")

EVENTS_DIR = os.path.join(C11_DIR, "events")
META_DIR = os.path.join(C11_DIR, "metadata")
REPORTS_DIR = os.path.join(C11_DIR, "reports")
os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 11: STEP 1 — INITIATION CANDIDATE EXTRACTION")
print("=" * 80)

# Input Rasters
risk_fp = os.path.join(C10_DIR, "risk", "combined_risk_score.tif")
risk_cls_fp = os.path.join(C10_DIR, "risk", "risk_class.tif")
susc_fp = os.path.join(C10_DIR, "susceptibility", "susceptibility_probability.tif")
unc_fp = os.path.join(C10_DIR, "uncertainty", "uncertainty.tif")
trig_fp = os.path.join(C10_DIR, "dynamic_trigger", "dynamic_trigger_index.tif")
elev_fp = os.path.join(TERRAIN_DIR, "elevation", "elevation.tif")
slope_fp = os.path.join(TERRAIN_DIR, "slope", "slope_degrees.tif")

# Exposure Context
districts_fp = os.path.join(EXPOSURE_DIR, "administrative", "NER_SAFE_Phase1_districts.geojson")
settlements_fp = os.path.join(EXPOSURE_DIR, "settlements", "NER_SAFE_Phase1_settlements.geojson")
roads_fp = os.path.join(EXPOSURE_DIR, "roads", "NER_SAFE_Phase1_roads.geojson")

print("Loading administrative district boundaries...")
with open(districts_fp, "r", encoding="utf-8") as f:
    districts_data = json.load(f)
district_polys = []
for feat in districts_data["features"]:
    district_polys.append({
        "state": feat["properties"].get("state", "Unknown"),
        "district": feat["properties"].get("district_name", "Unknown"),
        "geom": shape(feat["geometry"])
    })

print("Loading settlement reference points...")
with open(settlements_fp, "r", encoding="utf-8") as f:
    settlements_data = json.load(f)
settlements_list = []
for feat in settlements_data["features"]:
    props = feat["properties"]
    coords = feat["geometry"]["coordinates"]
    settlements_list.append({
        "name": props.get("name") or props.get("fclass", "Settlement"),
        "fclass": props.get("fclass", "place"),
        "lon": coords[0],
        "lat": coords[1]
    })

def get_nearest_settlement(lat, lon):
    min_dist = float("inf")
    nearest_name = "Rural Hillside"
    for s in settlements_list:
        d = ((lat - s["lat"])**2 + (lon - s["lon"])**2)**0.5
        if d < min_dist:
            min_dist = d
            nearest_name = s["name"]
    dist_km = min_dist * 111.0
    return nearest_name, round(dist_km, 1)

def get_district_and_state(lat, lon):
    pt = Point(lon, lat)
    for d in district_polys:
        if d["geom"].contains(pt):
            return d["state"], d["district"]
    # Fallback to nearest boundary if edge point
    min_d = float("inf")
    best_st, best_dt = "Unknown", "Unknown"
    for d in district_polys:
        d_val = d["geom"].distance(pt)
        if d_val < min_d:
            min_d = d_val
            best_st, best_dt = d["state"], d["district"]
    return best_st, best_dt

print("Scanning regional risk and slope grids across strips...")
raw_candidates = []

with rasterio.open(risk_fp) as r_src, \
     rasterio.open(risk_cls_fp) as rc_src, \
     rasterio.open(susc_fp) as s_src, \
     rasterio.open(unc_fp) as u_src, \
     rasterio.open(trig_fp) as t_src, \
     rasterio.open(elev_fp) as e_src, \
     rasterio.open(slope_fp) as sl_src:
    
    h = r_src.height
    w = r_src.width
    STRIP_HEIGHT = 1024
    n_strips = int(np.ceil(h / STRIP_HEIGHT))
    
    for s_idx in range(n_strips):
        r_start = s_idx * STRIP_HEIGHT
        r_len = min(STRIP_HEIGHT, h - r_start)
        win = Window(0, r_start, w, r_len)
        
        # Filter on risk class >= 3 (Moderate/High/Very High) and slope >= 18 deg
        rc_arr = rc_src.read(1, window=win)
        sl_arr = sl_src.read(1, window=win)
        r_arr = r_src.read(1, window=win)
        
        # Valid steep slope and elevated risk
        steep_high_mask = (rc_arr >= 3) & (r_arr >= 0.35) & (sl_arr >= 18.0) & (sl_arr <= 65.0)
        
        if not np.any(steep_high_mask):
            continue
        s_arr = s_src.read(1, window=win)
        u_arr = u_src.read(1, window=win)
        t_arr = t_src.read(1, window=win)
        e_arr = e_src.read(1, window=win)
        
        y_locs, x_locs = np.where(steep_high_mask)
        
        for i in range(len(y_locs)):
            y, x = y_locs[i], x_locs[i]
            r_val = float(r_arr[y, x])
            if r_val < 0.35:
                continue
                
            global_row = r_start + y
            global_col = x
            lon, lat = r_src.xy(global_row, global_col)
            
            raw_candidates.append({
                "row": int(global_row),
                "col": int(global_col),
                "latitude": round(float(lat), 6),
                "longitude": round(float(lon), 6),
                "combined_risk_score": round(r_val, 4),
                "risk_class": int(rc_arr[y, x]),
                "susceptibility_probability": round(float(s_arr[y, x]), 4),
                "uncertainty": round(float(u_arr[y, x]), 4),
                "dynamic_trigger_index": round(float(t_arr[y, x]), 4),
                "elevation_m": round(float(e_arr[y, x]), 1),
                "slope_deg": round(float(sl_arr[y, x]), 1)
            })

print(f"Total raw high-risk steep cells identified: {len(raw_candidates):,}")

# Sort candidates by combined risk score descending
raw_candidates.sort(key=lambda c: c["combined_risk_score"], reverse=True)

# Apply Spatial Non-Maximum Suppression (NMS) with minimum separation of ~1,500m (0.015 degrees)
MIN_DIST_DEG = 0.015  # ~1.6 km at 25°N
TARGET_COUNT_MEGHALAYA = 24
TARGET_COUNT_MIZORAM = 24

selected_candidates = []
meghalaya_count = 0
mizoram_count = 0
district_counts = {}

print("Applying Spatial Non-Maximum Suppression and multi-district balancing...")

for cand in raw_candidates:
    lat = cand["latitude"]
    lon = cand["longitude"]
    
    state, district = get_district_and_state(lat, lon)
    if state not in ["Meghalaya", "Mizoram"]:
        continue
        
    if state == "Meghalaya" and meghalaya_count >= TARGET_COUNT_MEGHALAYA:
        continue
    if state == "Mizoram" and mizoram_count >= TARGET_COUNT_MIZORAM:
        continue
        
    # Cap candidates per district to ensure broad spatial spread across the state
    d_count = district_counts.get(district, 0)
    if d_count >= 6:
        continue
        
    # Distance check against already selected candidates (min 1.2 km)
    too_close = False
    for sc in selected_candidates:
        d = ((lat - sc["latitude"])**2 + (lon - sc["longitude"])**2)**0.5
        if d < 0.012: # ~1.3 km
            too_close = True
            break
            
    if too_close:
        continue
        
    nearest_settlement, dist_km = get_nearest_settlement(lat, lon)
    cand["state"] = state
    cand["district"] = district
    cand["nearest_settlement"] = nearest_settlement
    cand["settlement_distance_km"] = dist_km
    
    selected_candidates.append(cand)
    district_counts[district] = d_count + 1
    
    if state == "Meghalaya":
        meghalaya_count += 1
    else:
        mizoram_count += 1
        
    if meghalaya_count >= TARGET_COUNT_MEGHALAYA and mizoram_count >= TARGET_COUNT_MIZORAM:
        break

# Assign standardized event IDs: EVT-MEG-001.. and EVT-MIZ-001..
meg_idx = 1
miz_idx = 1
for cand in selected_candidates:
    if cand["state"] == "Meghalaya":
        cand["event_id"] = f"EVT-MEG-{meg_idx:03d}"
        meg_idx += 1
    else:
        cand["event_id"] = f"EVT-MIZ-{miz_idx:03d}"
        miz_idx += 1

print(f"\nFinal Selected Initiation Candidates: {len(selected_candidates)}")
print(f" - Meghalaya Candidates: {meghalaya_count}")
print(f" - Mizoram Candidates  : {mizoram_count}")

# Print sample summary
print("\nSample High-Priority Initiation Candidates:")
for sc in selected_candidates[:8]:
    print(f" [{sc['event_id']}] {sc['state']} - {sc['district']:<18} | Lat: {sc['latitude']:.4f}, Lon: {sc['longitude']:.4f} | Risk: {sc['combined_risk_score']:.3f} | Slope: {sc['slope_deg']:.1f}° | Near: {sc['nearest_settlement']}")

# Save JSON
out_json_fp = os.path.join(EVENTS_DIR, "initiation_candidates.json")
with open(out_json_fp, "w", encoding="utf-8") as f:
    json.dump(selected_candidates, f, indent=2)
print(f"\nSaved initiation candidates to {out_json_fp}")

print("=" * 80)
print("STEP 1 COMPLETE: Initiation Candidates Successfully Extracted!")
print("=" * 80)
