"""
NER-SAFE: Dynamic Spatial Cross-Referencing Utility
Performs:
1. Point-in-polygon validation against authoritative Phase 1 state/district boundaries.
2. Derivation of nearest settlement from verified Phase 1 settlement points.
3. Geodesic distance calculation to Component 11 runout corridors.
"""

import os
import json
import math
from shapely.geometry import Point, shape

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
ADMIN_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE", "administrative")
SETTLEMENTS_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE", "settlements", "NER_SAFE_Phase1_settlements.geojson")
CORRIDORS_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "runout_corridors", "runout_corridors.geojson")

# Cache geometry objects
_states_geoms = None
_districts_geoms = None
_settlements_list = None
_corridors_list = None

def _load_geometries():
    global _states_geoms, _districts_geoms, _settlements_list, _corridors_list
    
    if _states_geoms is None:
        st_path = os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_states.geojson")
        with open(st_path, "r", encoding="utf-8") as f:
            st_data = json.load(f)
        _states_geoms = [
            {"state": f["properties"].get("state_name") or f["properties"].get("shapeName"), "geom": shape(f["geometry"])}
            for f in st_data["features"]
        ]
        
    if _districts_geoms is None:
        dt_path = os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_districts.geojson")
        with open(dt_path, "r", encoding="utf-8") as f:
            dt_data = json.load(f)
        _districts_geoms = [
            {"district": f["properties"].get("district_name") or f["properties"].get("shapeName"), "geom": shape(f["geometry"])}
            for f in dt_data["features"]
        ]
        
    if _settlements_list is None:
        with open(SETTLEMENTS_PATH, "r", encoding="utf-8") as f:
            s_data = json.load(f)
        _settlements_list = []
        for f in s_data["features"]:
            coords = f["geometry"]["coordinates"]
            _settlements_list.append({
                "name": f["properties"].get("name") or "Settlement",
                "district": f["properties"].get("district", ""),
                "lon": coords[0],
                "lat": coords[1]
            })
            
    if _corridors_list is None:
        with open(CORRIDORS_PATH, "r", encoding="utf-8") as f:
            c_data = json.load(f)
        _corridors_list = [
            {"id": f["id"], "geom": shape(f["geometry"]), "priority": f["properties"].get("impact_priority", "MODERATE")}
            for f in c_data["features"]
        ]

def spherical_distance_km(lat1, lon1, lat2, lon2):
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return 6371.0 * c

def analyze_location(lat, lon):
    """
    Validates coordinates, identifies state and district, derives nearest settlement,
    and checks containment/proximity to Component 11 runout corridors.
    """
    _load_geometries()
    pt = Point(lon, lat)
    
    # 1. State & District point-in-polygon
    found_state = None
    found_district = None
    
    for s in _states_geoms:
        if s["geom"].contains(pt):
            found_state = s["state"]
            break
            
    if found_state:
        for d in _districts_geoms:
            if d["geom"].contains(pt):
                found_district = d["district"]
                break
                
    within_aoi = (found_state is not None)
    if not within_aoi:
        found_state = "Outside Phase 1 Boundary"
        found_district = "Unknown"
        
    # 2. Nearest Settlement
    best_settlement = "Unknown"
    min_dist_km = 999999.0
    for st in _settlements_list:
        d = spherical_distance_km(lat, lon, st["lat"], st["lon"])
        if d < min_dist_km:
            min_dist_km = d
            best_settlement = st["name"]
            
    # 3. Dynamic Component 11 Corridor Intersections
    # Geodesic ground distance to nearest corridor polygon
    intersects_corridor = False
    nearest_evt_id = "None"
    min_corridor_dist_m = 999999.0
    
    # Approx meters per degree at this latitude
    m_per_deg_lat = 111000.0
    m_per_deg_lon = 111000.0 * math.cos(math.radians(lat))
    
    for corr in _corridors_list:
        c_geom = corr["geom"]
        if c_geom.contains(pt):
            intersects_corridor = True
            nearest_evt_id = corr["id"]
            min_corridor_dist_m = 0.0
            break
        else:
            # Approximate distance
            deg_dist = c_geom.distance(pt)
            m_dist = deg_dist * math.sqrt((m_per_deg_lat**2 + m_per_deg_lon**2) / 2.0)
            if m_dist < min_corridor_dist_m:
                min_corridor_dist_m = m_dist
                nearest_evt_id = corr["id"]
                
    if min_corridor_dist_m <= 75.0:
        intersects_corridor = True
        
    return {
        "within_phase1_aoi": within_aoi,
        "state": found_state,
        "district": found_district,
        "nearest_settlement": best_settlement,
        "settlement_distance_km": round(min_dist_km, 2),
        "intersects_c11_runout": intersects_corridor,
        "nearest_c11_event_id": nearest_evt_id if intersects_corridor else "None",
        "distance_to_runout_m": round(min_corridor_dist_m, 1)
    }

if __name__ == "__main__":
    # Test point in East Jaintia Hills scarp EVT-MEG-023
    r1 = analyze_location(25.150417, 92.369028)
    print("Scarp Test (EVT-MEG-023):", r1)
    
    # Test point far outside in Aizawl town
    r2 = analyze_location(23.7271, 92.7176)
    print("Aizawl Town Test:", r2)
