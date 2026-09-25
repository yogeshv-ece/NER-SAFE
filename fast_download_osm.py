"""
NER-SAFE — High-Speed Parallel Chunk Downloader for Geofabrik OSM Package
Uses concurrent HTTP range requests across 8 workers to download and unpack the dataset.
"""

import os
import sys
import time
import zipfile
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
RAW_DIR = os.path.join(EXPOSURE_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

ZIP_URL = "https://download.geofabrik.de/asia/india/north-eastern-zone-260903-free.shp.zip"
TARGET_ZIP = os.path.join(RAW_DIR, "north-eastern-zone-latest-free.shp.zip")
UNPACK_DIR = os.path.join(RAW_DIR, "osm_northeast_shp")

headers = {"User-Agent": "NER-SAFE-Landslide-Exposure/1.0 (contact: research@ner-safe.org)"}

def download_chunk(url, start, end, chunk_index, temp_file):
    expected_size = end - start + 1
    if os.path.exists(temp_file) and os.path.getsize(temp_file) == expected_size:
        print(f"  Chunk {chunk_index+1}/8 already downloaded ({expected_size/1024/1024:.1f} MB).", flush=True)
        return chunk_index, expected_size

    chunk_headers = {**headers, "Range": f"bytes={start}-{end}"}
    for attempt in range(5):
        try:
            print(f"  Starting chunk {chunk_index+1}/8 ({expected_size/1024/1024:.1f} MB)...", flush=True)
            r = requests.get(url, headers=chunk_headers, stream=True, timeout=120)
            if r.status_code in [200, 206]:
                with open(temp_file, "wb") as f:
                    downloaded = 0
                    for c in r.iter_content(chunk_size=1024*1024):
                        if c:
                            f.write(c)
                            downloaded += len(c)
                print(f"  --> Chunk {chunk_index+1}/8 completed ({downloaded/1024/1024:.1f} MB)", flush=True)
                return chunk_index, downloaded
            else:
                print(f"  Chunk {chunk_index+1} HTTP error {r.status_code}, retrying...", flush=True)
        except Exception as e:
            print(f"  Chunk {chunk_index+1} error ({e}), retrying {attempt+1}/5...", flush=True)
            time.sleep(2)
    raise RuntimeError(f"Failed to download chunk {chunk_index} ({start}-{end})")

def fast_parallel_download():
    # If valid zip already exists, verify
    if os.path.exists(TARGET_ZIP):
        try:
            with zipfile.ZipFile(TARGET_ZIP, "r") as z:
                if z.testzip() is None:
                    print(f"Zip file already fully downloaded and valid: {TARGET_ZIP}")
                    return TARGET_ZIP
        except Exception:
            print("Existing zip incomplete or corrupt. Re-downloading with parallel streams...")

    head = requests.head(ZIP_URL, headers=headers, allow_redirects=True)
    total_size = int(head.headers.get("content-length", 0))
    print(f"Remote file size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")

    num_workers = 8
    chunk_size = (total_size + num_workers - 1) // num_workers
    temp_files = []
    futures = []

    print(f"Launching {num_workers} parallel download workers ({chunk_size/1024/1024:.2f} MB per chunk)...")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        for i in range(num_workers):
            start = i * chunk_size
            end = min(start + chunk_size - 1, total_size - 1)
            temp_path = os.path.join(RAW_DIR, f"chunk_{i}.part")
            temp_files.append(temp_path)
            f = executor.submit(download_chunk, ZIP_URL, start, end, i, temp_path)
            futures.append(f)

        downloaded_bytes = 0
        for f in as_completed(futures):
            idx, b_len = f.result()
            downloaded_bytes += b_len
            print(f"  Chunk {idx+1}/{num_workers} completed ({b_len/1024/1024:.1f} MB, total {downloaded_bytes/1024/1024:.1f} MB)")

    print("Stitching chunks into final zip...")
    with open(TARGET_ZIP, "wb") as out_f:
        for temp_path in temp_files:
            with open(temp_path, "rb") as in_f:
                while True:
                    buf = in_f.read(4*1024*1024)
                    if not buf:
                        break
                    out_f.write(buf)
            try:
                os.remove(temp_path)
            except Exception:
                pass

    elapsed = time.time() - t0
    final_size = os.path.getsize(TARGET_ZIP)
    print(f"Download complete: {final_size:,} bytes in {elapsed:.1f}s ({final_size/elapsed/1024/1024:.2f} MB/s)")
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
            
    print(f"\nSuccessfully extracted files to: {UNPACK_DIR}")

if __name__ == "__main__":
    z_file = fast_parallel_download()
    extract_layers(z_file)
