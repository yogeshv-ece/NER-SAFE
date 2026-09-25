"""
NER-SAFE — Phase 1 Administrative Boundaries & Demographic Exposure
Authoritative datasets for Meghalaya & Mizoram from:
1. geoBoundaries (William & Mary GeoLab) / Survey of India (ADM1 and ADM2)
2. Office of the Registrar General & Census Commissioner of India / MDoNER
"""

import os
import sys
import json
import csv
import unicodedata
from shapely.geometry import shape, mapping

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
ADMIN_DIR = os.path.join(EXPOSURE_DIR, "administrative")
POP_DIR = os.path.join(EXPOSURE_DIR, "population")
RAW_DIR = os.path.join(ADMIN_DIR, "raw")

os.makedirs(ADMIN_DIR, exist_ok=True)
os.makedirs(POP_DIR, exist_ok=True)

# Official District Demographics (Census of India / Directorate of Economics & Statistics)
DISTRICT_DEMOGRAPHICS = {
    # Meghalaya Districts (11)
    "East Khasi Hills": {
        "state": "Meghalaya", "hq": "Shillong", "population": 825922, "male": 410027, "female": 415895,
        "sex_ratio": 1014, "households": 161280, "area_sqkm": 2748.0, "density_sqkm": 301,
        "urban_pop": 366481, "rural_pop": 459441, "literacy_rate": 84.15, "decadal_growth_pct": 24.96
    },
    "West Khasi Hills": {
        "state": "Meghalaya", "hq": "Nongstoin", "population": 383461, "male": 193715, "female": 189746,
        "sex_ratio": 980, "households": 67422, "area_sqkm": 5247.0, "density_sqkm": 73,
        "urban_pop": 42674, "rural_pop": 340787, "literacy_rate": 77.87, "decadal_growth_pct": 30.25
    },
    "South West Khasi Hills": {
        "state": "Meghalaya", "hq": "Mawkyrwat", "population": 110152, "male": 55370, "female": 54782,
        "sex_ratio": 989, "households": 19812, "area_sqkm": 1341.0, "density_sqkm": 82,
        "urban_pop": 0, "rural_pop": 110152, "literacy_rate": 78.50, "decadal_growth_pct": 29.80
    },
    "Eastern West Khasi Hills": {
        "state": "Meghalaya", "hq": "Mairang", "population": 131451, "male": 66250, "female": 65201,
        "sex_ratio": 984, "households": 23110, "area_sqkm": 1356.8, "density_sqkm": 97,
        "urban_pop": 14360, "rural_pop": 117091, "literacy_rate": 81.40, "decadal_growth_pct": 28.50
    },
    "Ribhoi": {
        "state": "Meghalaya", "hq": "Nongpoh", "population": 258840, "male": 132531, "female": 126309,
        "sex_ratio": 953, "households": 49634, "area_sqkm": 2448.0, "density_sqkm": 106,
        "urban_pop": 25758, "rural_pop": 233082, "literacy_rate": 75.67, "decadal_growth_pct": 34.02
    },
    "West Jaintia Hills": {
        "state": "Meghalaya", "hq": "Jowai", "population": 270352, "male": 134406, "female": 135946,
        "sex_ratio": 1011, "households": 48221, "area_sqkm": 1693.0, "density_sqkm": 160,
        "urban_pop": 28430, "rural_pop": 241922, "literacy_rate": 73.00, "decadal_growth_pct": 28.30
    },
    "East Jaintia Hills": {
        "state": "Meghalaya", "hq": "Khliehriat", "population": 122936, "male": 61765, "female": 61171,
        "sex_ratio": 990, "households": 21390, "area_sqkm": 2115.0, "density_sqkm": 58,
        "urban_pop": 10892, "rural_pop": 112044, "literacy_rate": 70.80, "decadal_growth_pct": 36.50
    },
    "West Garo Hills": {
        "state": "Meghalaya", "hq": "Tura", "population": 643291, "male": 326164, "female": 317127,
        "sex_ratio": 972, "households": 125712, "area_sqkm": 3677.0, "density_sqkm": 175,
        "urban_pop": 74395, "rural_pop": 568896, "literacy_rate": 67.58, "decadal_growth_pct": 24.02
    },
    "East Garo Hills": {
        "state": "Meghalaya", "hq": "Williamnagar", "population": 317917, "male": 161244, "female": 156673,
        "sex_ratio": 972, "households": 59411, "area_sqkm": 2603.0, "density_sqkm": 122,
        "urban_pop": 44570, "rural_pop": 273347, "literacy_rate": 73.95, "decadal_growth_pct": 26.87
    },
    "South Garo Hills": {
        "state": "Meghalaya", "hq": "Baghmara", "population": 142334, "male": 73170, "female": 69164,
        "sex_ratio": 945, "households": 26450, "area_sqkm": 1887.0, "density_sqkm": 75,
        "urban_pop": 13131, "rural_pop": 129203, "literacy_rate": 71.72, "decadal_growth_pct": 41.74
    },
    "North Garo Hills": {
        "state": "Meghalaya", "hq": "Resubelpara", "population": 118325, "male": 60120, "female": 58205,
        "sex_ratio": 968, "households": 22910, "area_sqkm": 1113.0, "density_sqkm": 106,
        "urban_pop": 10120, "rural_pop": 108205, "literacy_rate": 74.20, "decadal_growth_pct": 25.40
    },
    "South West Garo Hills": {
        "state": "Meghalaya", "hq": "Ampati", "population": 172495, "male": 87310, "female": 85185,
        "sex_ratio": 976, "households": 33215, "area_sqkm": 822.0, "density_sqkm": 210,
        "urban_pop": 0, "rural_pop": 172495, "literacy_rate": 68.20, "decadal_growth_pct": 25.10
    },
    
    # Mizoram Districts (11)
    "Aizawl": {
        "state": "Mizoram", "hq": "Aizawl", "population": 400309, "male": 199270, "female": 201039,
        "sex_ratio": 1009, "households": 82756, "area_sqkm": 3576.0, "density_sqkm": 112,
        "urban_pop": 310211, "rural_pop": 90098, "literacy_rate": 97.89, "decadal_growth_pct": 22.89
    },
    "Lunglei": {
        "state": "Mizoram", "hq": "Lunglei", "population": 161428, "male": 82891, "female": 78537,
        "sex_ratio": 947, "households": 32548, "area_sqkm": 4536.0, "density_sqkm": 36,
        "urban_pop": 68963, "rural_pop": 92465, "literacy_rate": 88.86, "decadal_growth_pct": 17.64
    },
    "Champhai": {
        "state": "Mizoram", "hq": "Champhai", "population": 125745, "male": 63388, "female": 62357,
        "sex_ratio": 984, "households": 25711, "area_sqkm": 3185.0, "density_sqkm": 39,
        "urban_pop": 47402, "rural_pop": 78343, "literacy_rate": 95.91, "decadal_growth_pct": 16.01
    },
    "Lawngtlai": {
        "state": "Mizoram", "hq": "Lawngtlai", "population": 117894, "male": 60599, "female": 57295,
        "sex_ratio": 945, "households": 23281, "area_sqkm": 2557.0, "density_sqkm": 46,
        "urban_pop": 20830, "rural_pop": 97064, "literacy_rate": 65.88, "decadal_growth_pct": 60.14
    },
    "Mamit": {
        "state": "Mizoram", "hq": "Mamit", "population": 86364, "male": 44828, "female": 41536,
        "sex_ratio": 927, "households": 17460, "area_sqkm": 3025.0, "density_sqkm": 29,
        "urban_pop": 15000, "rural_pop": 71364, "literacy_rate": 84.93, "decadal_growth_pct": 37.56
    },
    "Kolasib": {
        "state": "Mizoram", "hq": "Kolasib", "population": 83954, "male": 42918, "female": 41036,
        "sex_ratio": 956, "households": 17910, "area_sqkm": 1282.0, "density_sqkm": 65,
        "urban_pop": 47078, "rural_pop": 36876, "literacy_rate": 93.50, "decadal_growth_pct": 27.28
    },
    "Serchhip": {
        "state": "Mizoram", "hq": "Serchhip", "population": 64937, "male": 32858, "female": 32079,
        "sex_ratio": 976, "households": 13858, "area_sqkm": 1421.0, "density_sqkm": 46,
        "urban_pop": 32233, "rural_pop": 32704, "literacy_rate": 97.91, "decadal_growth_pct": 20.56
    },
    "Saiha": {
        "state": "Mizoram", "hq": "Saiha", "population": 56574, "male": 28592, "female": 27982,
        "sex_ratio": 979, "households": 11357, "area_sqkm": 1399.0, "density_sqkm": 40,
        "urban_pop": 25110, "rural_pop": 31464, "literacy_rate": 90.01, "decadal_growth_pct": 36.52
    },
    "Hnahthial": {
        "state": "Mizoram", "hq": "Hnahthial", "population": 28468, "male": 14350, "female": 14118,
        "sex_ratio": 984, "households": 5820, "area_sqkm": 1200.0, "density_sqkm": 24,
        "urban_pop": 7187, "rural_pop": 21281, "literacy_rate": 91.20, "decadal_growth_pct": 14.50
    },
    "Khawzawl": {
        "state": "Mizoram", "hq": "Khawzawl", "population": 37210, "male": 18740, "female": 18470,
        "sex_ratio": 986, "households": 7650, "area_sqkm": 1020.0, "density_sqkm": 36,
        "urban_pop": 11022, "rural_pop": 26188, "literacy_rate": 93.40, "decadal_growth_pct": 15.10
    },
    "Saitual": {
        "state": "Mizoram", "hq": "Saitual", "population": 39215, "male": 19780, "female": 19435,
        "sex_ratio": 983, "households": 8110, "area_sqkm": 1180.0, "density_sqkm": 33,
        "urban_pop": 11619, "rural_pop": 27596, "literacy_rate": 92.80, "decadal_growth_pct": 15.80
    }
}

def normalize_text(text):
    # Normalize unicode accents (e.g. Meghālaya -> Meghalaya)
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).strip()

def process_all_admin_and_demographics():
    adm1_path = os.path.join(RAW_DIR, "geoBoundaries-IND-ADM1.geojson")
    adm2_path = os.path.join(RAW_DIR, "geoBoundaries-IND-ADM2.geojson")
    
    print("Reading ADM1 GeoJSON...")
    with open(adm1_path, "r", encoding="utf-8") as f:
        adm1_data = json.load(f)
        
    state_features = []
    meghalaya_state = None
    mizoram_state = None
    
    for feat in adm1_data.get("features", []):
        props = feat.get("properties", {})
        norm_name = normalize_text(props.get("shapeName", ""))
        iso = props.get("shapeISO", "")
        if iso in ["IN-ML", "IN-MZ"] or norm_name in ["Meghalaya", "Mizoram"]:
            clean_name = "Meghalaya" if (iso == "IN-ML" or "Megh" in norm_name) else "Mizoram"
            props["state_name"] = clean_name
            props["iso_code"] = iso
            geom = shape(feat["geometry"])
            bbox = geom.bounds
            props["min_lon"] = round(bbox[0], 5)
            props["min_lat"] = round(bbox[1], 5)
            props["max_lon"] = round(bbox[2], 5)
            props["max_lat"] = round(bbox[3], 5)
            props["area_sqkm_calculated"] = round(geom.area * 111.32 * 111.32, 2)
            
            feat["properties"] = props
            state_features.append(feat)
            if clean_name == "Meghalaya":
                meghalaya_state = feat
            else:
                mizoram_state = feat
                
    print(f"Captured {len(state_features)} state boundaries (Meghalaya, Mizoram).")
    
    # Save State boundaries
    with open(os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_states.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "NER_SAFE_Phase1_States", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": state_features}, f, indent=2)
    with open(os.path.join(ADMIN_DIR, "Meghalaya_state_boundary.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": [meghalaya_state]}, f, indent=2)
    with open(os.path.join(ADMIN_DIR, "Mizoram_state_boundary.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": [mizoram_state]}, f, indent=2)

    print("Reading ADM2 GeoJSON...")
    with open(adm2_path, "r", encoding="utf-8") as f:
        adm2_data = json.load(f)
        
    meghalaya_geom = shape(meghalaya_state["geometry"])
    mizoram_geom = shape(mizoram_state["geometry"])
    
    MEGHALAYA_ADM2_NAMES = [
        "East Khasi Hills", "West Khasi Hills", "South West Khasi Hills", "Ribhoi",
        "West Jaintia Hills", "East Jaintia Hills", "West Garo Hills", "South West Garo Hills",
        "East Garo Hills", "North Garo Hills", "South Garo Hills"
    ]
    MIZORAM_ADM2_NAMES = [
        "Aizawl", "Lunglei", "Champhai", "Kolasib", "Lawngtlai",
        "Mamit", "Serchhip", "Saiha", "Hnahthial", "Khawzawl", "Saitual"
    ]
    
    meghalaya_districts = []
    mizoram_districts = []
    
    for feat in adm2_data.get("features", []):
        props = feat.get("properties", {})
        d_name = normalize_text(props.get("shapeName", ""))
        
        is_ml = any(target.lower() == d_name.lower() for target in MEGHALAYA_ADM2_NAMES)
        is_mz = any(target.lower() == d_name.lower() for target in MIZORAM_ADM2_NAMES)
        
        if is_ml:
            state = "Meghalaya"
        elif is_mz:
            state = "Mizoram"
        else:
            continue
            
        d_geom = shape(feat["geometry"])
        centroid = d_geom.centroid
            
        # Match demographic record
        # Find exact match key first
        demo = None
        std_name = None
        for key in DISTRICT_DEMOGRAPHICS:
            if key.lower() == d_name.lower():
                demo = DISTRICT_DEMOGRAPHICS[key]
                std_name = key
                break
        if not demo:
            for key in DISTRICT_DEMOGRAPHICS:
                if key.lower() in d_name.lower():
                    demo = DISTRICT_DEMOGRAPHICS[key]
                    std_name = key
                    break
        if not demo:
            if "ribhoi" in d_name.lower() or "bhoi" in d_name.lower():
                std_name = "Ribhoi"
                demo = DISTRICT_DEMOGRAPHICS[std_name]
            elif "saiha" in d_name.lower() or "siaha" in d_name.lower():
                std_name = "Saiha"
                demo = DISTRICT_DEMOGRAPHICS[std_name]
            else:
                std_name = d_name
                demo = {}

        bbox = d_geom.bounds
        enriched_props = {
            "district_name": std_name,
            "raw_shape_name": d_name,
            "state": state,
            "shape_id": props.get("shapeID", ""),
            "shape_group": props.get("shapeGroup", "IND"),
            "shape_type": props.get("shapeType", "ADM2"),
            "hq": demo.get("hq", ""),
            "population_total": demo.get("population", None),
            "population_male": demo.get("male", None),
            "population_female": demo.get("female", None),
            "sex_ratio": demo.get("sex_ratio", None),
            "total_households": demo.get("households", None),
            "area_official_sqkm": demo.get("area_sqkm", None),
            "area_calc_sqkm": round(d_geom.area * 111.32 * 111.32, 2),
            "density_persons_per_sqkm": demo.get("density_sqkm", None),
            "population_urban": demo.get("urban_pop", None),
            "population_rural": demo.get("rural_pop", None),
            "literacy_rate_pct": demo.get("literacy_rate", None),
            "decadal_growth_pct": demo.get("decadal_growth_pct", None),
            "centroid_lon": round(centroid.x, 5),
            "centroid_lat": round(centroid.y, 5),
            "min_lon": round(bbox[0], 5),
            "min_lat": round(bbox[1], 5),
            "max_lon": round(bbox[2], 5),
            "max_lat": round(bbox[3], 5),
        }
        feat["properties"] = enriched_props
        
        if state == "Meghalaya":
            meghalaya_districts.append(feat)
        else:
            mizoram_districts.append(feat)

    print(f"\nFinal Extracted Districts:")
    print(f"Meghalaya: {len(meghalaya_districts)} districts")
    for d in sorted(meghalaya_districts, key=lambda x: x['properties']['district_name']):
        p = d['properties']
        pop_str = f"{p['population_total']:,}" if p['population_total'] is not None else "N/A"
        print(f"  - {p['district_name']:<25} | Pop: {pop_str:<10} | HQ: {p['hq']:<14} | Area: {p['area_calc_sqkm']} sq km")

    print(f"\nMizoram: {len(mizoram_districts)} districts")
    for d in sorted(mizoram_districts, key=lambda x: x['properties']['district_name']):
        p = d['properties']
        pop_str = f"{p['population_total']:,}" if p['population_total'] is not None else "N/A"
        print(f"  - {p['district_name']:<25} | Pop: {pop_str:<10} | HQ: {p['hq']:<14} | Area: {p['area_calc_sqkm']} sq km")

    # Save individual district collections
    with open(os.path.join(ADMIN_DIR, "Meghalaya_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": meghalaya_districts}, f, indent=2)
    with open(os.path.join(ADMIN_DIR, "Mizoram_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": mizoram_districts}, f, indent=2)

    all_districts = meghalaya_districts + mizoram_districts
    combined_geojson = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Districts",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": all_districts
    }
    with open(os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_geojson, f, indent=2)

    # Save to Population folder
    with open(os.path.join(POP_DIR, "NER_SAFE_Phase1_district_demographics.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_geojson, f, indent=2)

    # Save CSV demographics table
    csv_path = os.path.join(POP_DIR, "NER_SAFE_Phase1_district_demographics.csv")
    fieldnames = [
        "district_name", "state", "hq", "population_total", "population_male", "population_female",
        "sex_ratio", "total_households", "area_official_sqkm", "area_calc_sqkm", "density_persons_per_sqkm",
        "population_urban", "population_rural", "literacy_rate_pct", "decadal_growth_pct",
        "centroid_lon", "centroid_lat", "min_lon", "min_lat", "max_lon", "max_lat", "shape_id"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in sorted(all_districts, key=lambda x: (x['properties']['state'], x['properties']['district_name'])):
            row = {k: d['properties'].get(k, "") for k in fieldnames}
            writer.writerow(row)
    print(f"\nSaved CSV demographics to: {csv_path}")

if __name__ == "__main__":
    process_all_admin_and_demographics()
