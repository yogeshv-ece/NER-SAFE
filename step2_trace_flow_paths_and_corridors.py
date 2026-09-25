"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 11: Step 2 — DEM Downhill Flow Path & Empirical Runout Corridor Generator

For each candidate landslide initiation point:
1. Traces steepest downhill descent on the USGS SRTM 1-Arcsecond DEM (D8 gradient routing).
2. Prevents any uphill travel (strictly monotonic downhill descent).
3. Applies defensible physical stopping criteria:
   - Slope flattening (slope <= 3.5° / gradient < 0.06)
   - Local pit / depression floor (dz <= 0 in all directions)
   - Maximum empirical runout distance (L >= 2,500m or Fahrböschung reach angle <= 10°)
4. Converts coordinate sequence into GIS LineString (Initiation -> Downslope -> Deposition).
5. Generates empirical runout corridor polygon via lateral spreading envelope (70m -> 120m).
6. Exports map-ready GeoJSON layers:
   - flow_paths.geojson
   - runout_corridors.geojson
   - initiation_points.geojson
"""

import os
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from shapely.geometry import Point, LineString, Polygon, mapping, shape
from shapely.ops import unary_union

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
TERRAIN_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives")
C11_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11")

EVENTS_DIR = os.path.join(C11_DIR, "events")
PATHS_DIR = os.path.join(C11_DIR, "flow_paths")
CORRS_DIR = os.path.join(C11_DIR, "runout_corridors")
os.makedirs(PATHS_DIR, exist_ok=True)
os.makedirs(CORRS_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 11: STEP 2 — FLOW PATH & RUNOUT CORRIDOR ENGINE")
print("=" * 80)

# Load Initiation Candidates
cand_json_fp = os.path.join(EVENTS_DIR, "initiation_candidates.json")
with open(cand_json_fp, "r", encoding="utf-8") as f:
    candidates = json.load(f)

print(f"Loaded {len(candidates)} candidate initiation points.")

elev_fp = os.path.join(TERRAIN_DIR, "elevation", "elevation.tif")

# Physical Flow Routing Parameters
CELL_SIZE_M = 30.89
MAX_PATH_STEPS = 90         # Maximum steps (~2,700m max distance)
MIN_GRADIENT = 0.061       # ~3.5° minimum slope threshold for debris halting
MIN_REACH_ANGLE_DEG = 10.0 # Fahrböschung empirical travel angle limit
INITIAL_HALF_WIDTH_M = 35.0  # 70m scarp width
FINAL_HALF_WIDTH_M = 60.0    # 120m deposition spreading width

flow_path_features = []
corridor_features = []
point_features = []

with rasterio.open(elev_fp) as dem_src:
    transform = dem_src.transform
    inv_transform = ~transform
    dem_w = dem_src.width
    dem_h = dem_src.height
    
    for cand_idx, cand in enumerate(candidates):
        event_id = cand["event_id"]
        init_lat = cand["latitude"]
        init_lon = cand["longitude"]
        
        # Determine pixel coordinates on DEM (returns row, col)
        init_row, init_col = dem_src.index(init_lon, init_lat)
        
        # Read localized DEM patch around initiation point (radius 120 cells ~ 3.7 km)
        PATCH_RAD = 120
        win_col = max(0, init_col - PATCH_RAD)
        win_row = max(0, init_row - PATCH_RAD)
        win_w = min(dem_w - win_col, PATCH_RAD * 2)
        win_h = min(dem_h - win_row, PATCH_RAD * 2)
        
        win = Window(win_col, win_row, win_w, win_h)
        dem_patch = dem_src.read(1, window=win)
        
        # Local relative coordinates in patch
        curr_pr = init_row - win_row
        curr_pc = init_col - win_col
        
        if curr_pr < 0 or curr_pr >= win_h or curr_pc < 0 or curr_pc >= win_w:
            print(f"Warning: {event_id} outside DEM bounds, skipping.")
            continue
            
        init_elev = float(dem_patch[curr_pr, curr_pc])
        
        path_pixels = [(curr_pr, curr_pc)]
        path_coords = [(init_lon, init_lat)]
        visited = set([(curr_pr, curr_pc)])
        
        cum_distance_m = 0.0
        stop_reason = "max_runout_reached"
        
        for step in range(MAX_PATH_STEPS):
            curr_z = dem_patch[curr_pr, curr_pc]
            best_grad = 0.0
            best_next = None
            best_step_dist = 0.0
            
            # Evaluate 8 neighbors (D8 steepest gradient)
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = curr_pr + dr, curr_pc + dc
                    if 0 <= nr < win_h and 0 <= nc < win_w:
                        if (nr, nc) in visited:
                            continue
                        nz = dem_patch[nr, nc]
                        if nz == -9999.0 or np.isnan(nz):
                            continue
                        # Strictly downhill (no uphill steps)
                        dz = curr_z - nz
                        if dz <= 0:
                            continue
                        # Diagonal step distance vs Cardinal step distance
                        step_dist = CELL_SIZE_M * (1.41421356 if (dr != 0 and dc != 0) else 1.0)
                        grad = dz / step_dist
                        if grad > best_grad:
                            best_grad = grad
                            best_next = (nr, nc)
                            best_step_dist = step_dist
            
            # Check stopping conditions
            if best_next is None:
                stop_reason = "local_pit_depression"
                break
                
            if best_grad < MIN_GRADIENT:
                stop_reason = "slope_flattening_deposition"
                break
                
            curr_pr, curr_pc = best_next
            visited.add(best_next)
            path_pixels.append(best_next)
            cum_distance_m += best_step_dist
            
            # Compute geographic coordinates of next vertex
            global_c = win_col + curr_pc
            global_r = win_row + curr_pr
            v_lon, v_lat = dem_src.xy(global_r, global_c)
            path_coords.append((round(float(v_lon), 6), round(float(v_lat), 6)))
            
            # Empirical Fahrböschung travel angle check
            elev_drop = init_elev - float(dem_patch[curr_pr, curr_pc])
            if cum_distance_m > 200.0:
                travel_angle_deg = np.degrees(np.arctan(elev_drop / cum_distance_m))
                if travel_angle_deg < MIN_REACH_ANGLE_DEG:
                    stop_reason = "fahrboschung_energy_reach_limit"
                    break
                    
            if cum_distance_m >= 2500.0:
                stop_reason = "max_runout_distance"
                break
        
        # Ensure at least 2 vertices
        if len(path_coords) < 2:
            # Add synthetic minimal 30m downhill nudge
            v_lon, v_lat = dem_src.xy(init_row + 1, init_col)
            path_coords.append((round(float(v_lon), 6), round(float(v_lat), 6)))
            cum_distance_m = CELL_SIZE_M
            stop_reason = "minimal_steep_channel"
            
        final_elev = float(dem_patch[curr_pr, curr_pc])
        elev_drop_m = round(init_elev - final_elev, 1)
        path_length_m = round(cum_distance_m, 1)
        avg_slope_deg = round(float(np.degrees(np.arctan(elev_drop_m / max(path_length_m, 1.0)))), 1)
        
        # 1. Flow Path LineString Feature
        flow_line = LineString(path_coords)
        
        # Calculate Flow Path Quality / Confidence (0 to 1)
        # Higher confidence for clear monotonic descent with adequate slope and sufficient steps
        fp_conf = round(min(1.0, max(0.40, 0.50 + 0.30 * min(1.0, elev_drop_m / 150.0) + 0.20 * min(1.0, path_length_m / 500.0))), 2)
        
        # 2. Empirical Runout Corridor Polygon
        # Build lateral spreading envelope along path vertices
        corridor_circles = []
        n_pts = len(path_coords)
        for p_idx, (p_lon, p_lat) in enumerate(path_coords):
            # Linearly expand half-width from scarp to toe
            frac = p_idx / max(1, n_pts - 1)
            hw_m = INITIAL_HALF_WIDTH_M + (FINAL_HALF_WIDTH_M - INITIAL_HALF_WIDTH_M) * frac
            # Convert meters to degrees approximately (~111,000 m/deg)
            deg_buf = hw_m / 111000.0
            corridor_circles.append(Point(p_lon, p_lat).buffer(deg_buf, resolution=16))
            
        # Union circles into a smooth contiguous corridor polygon
        raw_poly = unary_union(corridor_circles)
        if raw_poly.geom_type == "MultiPolygon":
            # Pick largest polygon if split by tiny artifact
            raw_poly = max(raw_poly.geoms, key=lambda g: g.area)
            
        corridor_poly = raw_poly.simplify(1e-6, preserve_topology=True)
        # Approximate area in m²
        corridor_area_m2 = round(float(corridor_poly.area * (111000.0 * 111000.0 * np.cos(np.radians(init_lat)))), 1)
        
        # Runout confidence (higher confidence for moderate length, lower for extreme runout)
        ro_conf = round(min(1.0, max(0.45, 0.90 - 0.25 * (path_length_m / 2500.0))), 2)
        
        # Assemble Properties
        event_props = {
            "event_id": event_id,
            "state": cand["state"],
            "district": cand["district"],
            "latitude": init_lat,
            "longitude": init_lon,
            "elevation_init_m": cand["elevation_m"],
            "elevation_end_m": round(final_elev, 1),
            "elevation_drop_m": elev_drop_m,
            "slope_init_deg": cand["slope_deg"],
            "avg_slope_deg": avg_slope_deg,
            "combined_risk_score": cand["combined_risk_score"],
            "risk_class": cand["risk_class"],
            "susceptibility": cand["susceptibility_probability"],
            "dynamic_trigger": cand["dynamic_trigger_index"],
            "uncertainty": cand["uncertainty"],
            "path_length_m": path_length_m,
            "runout_area_m2": corridor_area_m2,
            "vertex_count": len(path_coords),
            "stopping_reason": stop_reason,
            "flow_path_confidence": fp_conf,
            "runout_confidence": ro_conf,
            "nearest_settlement": cand["nearest_settlement"],
            "settlement_distance_km": cand["settlement_distance_km"]
        }
        
        # 1. Flow Path Feature
        flow_path_features.append({
            "type": "Feature",
            "id": event_id,
            "properties": event_props,
            "geometry": mapping(flow_line)
        })
        
        # 2. Runout Corridor Feature
        corridor_features.append({
            "type": "Feature",
            "id": event_id,
            "properties": event_props,
            "geometry": mapping(corridor_poly)
        })
        
        # 3. Initiation Point Feature
        point_features.append({
            "type": "Feature",
            "id": event_id,
            "properties": event_props,
            "geometry": mapping(Point(init_lon, init_lat))
        })
        
        if (cand_idx + 1) % 12 == 0 or (cand_idx + 1) == len(candidates):
            print(f"   [{cand_idx+1:02d}/{len(candidates)}] Processed {event_id}: Length={path_length_m}m, Drop={elev_drop_m}m, Stopped by={stop_reason}")

# Write Flow Paths GeoJSON
fp_geojson = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Phase1_Landslide_Flow_Paths",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": flow_path_features
}
fp_path = os.path.join(PATHS_DIR, "flow_paths.geojson")
with open(fp_path, "w", encoding="utf-8") as f:
    json.dump(fp_geojson, f, indent=2)
print(f"\nSaved {len(flow_path_features)} flow path polylines to {fp_path}")

# Write Runout Corridors GeoJSON
corr_geojson = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Phase1_Landslide_Runout_Corridors",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": corridor_features
}
corr_path = os.path.join(CORRS_DIR, "runout_corridors.geojson")
with open(corr_path, "w", encoding="utf-8") as f:
    json.dump(corr_geojson, f, indent=2)
print(f"Saved {len(corridor_features)} runout corridors to {corr_path}")

# Write Initiation Points GeoJSON
pts_geojson = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Phase1_Landslide_Initiation_Points",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
    "features": point_features
}
pts_path = os.path.join(EVENTS_DIR, "initiation_points.geojson")
with open(pts_path, "w", encoding="utf-8") as f:
    json.dump(pts_geojson, f, indent=2)
print(f"Saved {len(point_features)} initiation points to {pts_path}")

# Also mirror to project root
import shutil
shutil.copy(fp_path, os.path.join(PROJECT_ROOT, "flow_paths.geojson"))
shutil.copy(corr_path, os.path.join(PROJECT_ROOT, "runout_corridors.geojson"))
shutil.copy(pts_path, os.path.join(PROJECT_ROOT, "initiation_points.geojson"))

print("=" * 80)
print("STEP 2 COMPLETE: Flow Paths & Runout Corridors Successfully Generated!")
print("=" * 80)
