"""
NER-SAFE — Phase 1 OpenStreetMap Infrastructure & Exposure Acquisition
Downloads official Geofabrik North-Eastern Zone India shapefile bundle
and extracts Roads, Settlements/Places, Buildings, and Transport.
"""

import os
import sys
import time
import zipfile
import requests

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
RAW_DIR = os.path.join(EXPOSURE_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

ZIP_URL = "https://download.geofabrik.de/asia/india/north-eastern-zone-260903-free.shp.zip"
TARGET_ZIP = os.path.join(RAW_DIR, "north-eastern-zone-latest-free.shp.zip")
UNPACK_DIR = os.path.join(RAW_DIR, "osm_northeast_shp")

headers = {"User-Agent": "NER-SAFE-Landslide-Exposure/1.0 (contact: research@ner-safe.org)"}

def download_osm_bundle():
    if os.path.exists(TARGET_ZIP) and os.path.getsize(TARGET_ZIP) > 200000000:
        print(f"OSM zip already exists: {TARGET_ZIP} ({os.path.getsize(TARGET_ZIP):,} bytes)")
        return TARGET_ZIP
        
    print(f"Downloading Geofabrik North-Eastern Zone extract from:\n  {ZIP_URL}\nto:\n  {TARGET_ZIP}")
    t0 = time.time()
    resp = requests.get(ZIP_URL, headers=headers, stream=True, timeout=120)
    resp.raise_for_status()
    total = 0
    with open(TARGET_ZIP, "wb") as f:
        for chunk in resp.iter_content(chunk_size=2*1024*1024):
            if chunk:
                f.write(chunk)
                total += len(chunk)
                sys.stdout.write(f"\r  Downloaded: {total / (1024*1024):.1f} MB")
                sys.stdout.flush()
    elapsed = time.time() - t0
    print(f"\nDownload complete: {total:,} bytes in {elapsed:.1f}s ({total/elapsed/1024/1024:.2f} MB/s)")
    return TARGET_ZIP

def extract_layers(zip_path):
    os.makedirs(UNPACK_DIR, exist_ok=True)
    target_prefixes = [
        "gis_osm_roads_free_1",
        "gis_osm_places_free_1",
        "gis_osm_buildings_a_free_1",
        "gis_osm_transport_free_1",
        "gis_osm_pois_free_1"
    ]
    
    print(f"\nInspecting and extracting target layers from {zip_path}...")
    with zipfile.ZipFile(zip_path, "r") as z:
        all_files = z.namelist()
        print(f"Total files in zip: {len(all_files)}")
        to_extract = [f for f in all_files if any(f.startswith(p) for p in target_prefixes)]
        print(f"Extracting {len(to_extract)} files for target layers:")
        for fn in to_extract:
            print(f"  - {fn} ({z.getinfo(fn).file_size:,} bytes)")
            z.extract(fn, UNPACK_DIR)
            
    print(f"Extracted files to: {UNPACK_DIR}")

if __name__ == "__main__":
    z_path = download_osm_bundle()
    extract_layers(z_path)
