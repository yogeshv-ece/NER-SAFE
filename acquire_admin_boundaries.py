"""
NER-SAFE — Phase 1 Administrative Boundary Acquisition & Extraction
Acquires authoritative state and district boundaries for Meghalaya and Mizoram
from geoBoundaries (William & Mary GeoLab) / Survey of India aligned dataset.
"""

import os
import sys
import json
import time
import requests
from shapely.geometry import shape, mapping

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
ADMIN_DIR = os.path.join(EXPOSURE_DIR, "administrative")
RAW_DIR = os.path.join(ADMIN_DIR, "raw")

os.makedirs(RAW_DIR, exist_ok=True)

ADM1_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM1/geoBoundaries-IND-ADM1.geojson"
ADM2_URL = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson"

headers = {"User-Agent": "NER-SAFE-Landslide-Exposure/1.0 (contact: research@ner-safe.org)"}

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000000:
        print(f"File already exists: {target_path} ({os.path.getsize(target_path):,} bytes)")
        return target_path
    
    print(f"Downloading from {url} to {target_path}...")
    t0 = time.time()
    resp = requests.get(url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()
    total = 0
    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                total += len(chunk)
                print(f"  Downloaded {total / (1024*1024):.2f} MB...", end="\r")
    elapsed = time.time() - t0
    print(f"\nDownload completed: {total:,} bytes in {elapsed:.2f}s ({total/elapsed/1024/1024:.2f} MB/s)")
    return target_path

def process_boundaries():
    adm1_path = os.path.join(RAW_DIR, "geoBoundaries-IND-ADM1.geojson")
    adm2_path = os.path.join(RAW_DIR, "geoBoundaries-IND-ADM2.geojson")
    
    download_file(ADM1_URL, adm1_path)
    download_file(ADM2_URL, adm2_path)
    
    print("\nProcessing ADM1 (States)...")
    with open(adm1_path, "r", encoding="utf-8") as f:
        adm1_data = json.load(f)
        
    state_features = []
    meghalaya_state = None
    mizoram_state = None
    
    for feat in adm1_data.get("features", []):
        props = feat.get("properties", {})
        s_name = props.get("shapeName", "")
        if s_name in ["Meghalaya", "Mizoram"]:
            print(f"Found ADM1: {s_name}, ISO: {props.get('shapeISO')}, ID: {props.get('shapeID')}")
            geom = shape(feat["geometry"])
            bbox = geom.bounds  # (minx, miny, maxx, maxy)
            props["min_lon"] = round(bbox[0], 5)
            props["min_lat"] = round(bbox[1], 5)
            props["max_lon"] = round(bbox[2], 5)
            props["max_lat"] = round(bbox[3], 5)
            props["area_sqkm_approx"] = round(geom.area * 111.32 * 111.32, 2)
            state_features.append(feat)
            if s_name == "Meghalaya":
                meghalaya_state = feat
            elif s_name == "Mizoram":
                mizoram_state = feat

    # Save state files
    states_geojson = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_States",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": state_features
    }
    with open(os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_states.geojson"), "w", encoding="utf-8") as f:
        json.dump(states_geojson, f, indent=2)
    print(f"Saved {len(state_features)} state features to NER_SAFE_Phase1_states.geojson")
    
    if meghalaya_state:
        with open(os.path.join(ADMIN_DIR, "Meghalaya_state_boundary.geojson"), "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": [meghalaya_state]}, f, indent=2)
    if mizoram_state:
        with open(os.path.join(ADMIN_DIR, "Mizoram_state_boundary.geojson"), "w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": [mizoram_state]}, f, indent=2)

    print("\nProcessing ADM2 (Districts)...")
    with open(adm2_path, "r", encoding="utf-8") as f:
        adm2_data = json.load(f)
        
    meghalaya_geom = shape(meghalaya_state["geometry"]) if meghalaya_state else None
    mizoram_geom = shape(mizoram_state["geometry"]) if mizoram_state else None
    
    meghalaya_districts = []
    mizoram_districts = []
    
    for feat in adm2_data.get("features", []):
        props = feat.get("properties", {})
        d_geom = shape(feat["geometry"])
        centroid = d_geom.centroid
        
        # Check intersection with state geometry
        if meghalaya_geom and meghalaya_geom.contains(centroid):
            props["state"] = "Meghalaya"
            bbox = d_geom.bounds
            props["centroid_lon"] = round(centroid.x, 5)
            props["centroid_lat"] = round(centroid.y, 5)
            props["area_sqkm"] = round(d_geom.area * 111.32 * 111.32, 2)
            meghalaya_districts.append(feat)
        elif mizoram_geom and mizoram_geom.contains(centroid):
            props["state"] = "Mizoram"
            bbox = d_geom.bounds
            props["centroid_lon"] = round(centroid.x, 5)
            props["centroid_lat"] = round(centroid.y, 5)
            props["area_sqkm"] = round(d_geom.area * 111.32 * 111.32, 2)
            mizoram_districts.append(feat)

    print(f"Extracted {len(meghalaya_districts)} Meghalaya districts:")
    for d in meghalaya_districts:
        print(f" - {d['properties'].get('shapeName')}")

    print(f"Extracted {len(mizoram_districts)} Mizoram districts:")
    for d in mizoram_districts:
        print(f" - {d['properties'].get('shapeName')}")

    # Save individual and combined district GeoJSON files
    with open(os.path.join(ADMIN_DIR, "Meghalaya_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": meghalaya_districts}, f, indent=2)
    with open(os.path.join(ADMIN_DIR, "Mizoram_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": mizoram_districts}, f, indent=2)
        
    combined_districts = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Districts",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": meghalaya_districts + mizoram_districts
    }
    with open(os.path.join(ADMIN_DIR, "NER_SAFE_Phase1_districts.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_districts, f, indent=2)
    print(f"Saved total {len(combined_districts['features'])} districts to NER_SAFE_Phase1_districts.geojson")

if __name__ == "__main__":
    process_boundaries()
