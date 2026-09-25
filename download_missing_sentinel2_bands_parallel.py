"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 8: High-Throughput Concurrent Sentinel-2 Level-2A Band Downloader
Features:
 - 4 Concurrent Worker Threads (ThreadPoolExecutor)
 - Connection-pooled requests.Session()
 - Automatic Microsoft Planetary Computer SAS Token Signing & Refresh
 - Robust Retry Logic with Exponential Backoff
 - Strict Byte-Completeness (downloaded == total_size) & Rasterio GeoTIFF Validation
 - Zero-Redownload & Safe Atomic Replacement (never overwrites valid files)
"""

import os
import sys
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import rasterio

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
RAW_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL", "raw")
MAX_WORKERS = 4

BAND_FILE_MAP = {
    "B02": "B02_Blue_10m.tif",
    "B03": "B03_Green_10m.tif",
    "B04": "B04_Red_10m.tif",
    "B08": "B08_NIR_10m.tif",
    "B11": "B11_SWIR1_20m.tif",
    "B12": "B12_SWIR2_20m.tif"
}

print_lock = threading.Lock()

def log(msg):
    with print_lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sys.stdout.flush()

def create_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(
        pool_connections=MAX_WORKERS * 2,
        pool_maxsize=MAX_WORKERS * 2,
        max_retries=retries
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "NER-SAFE-HighThroughputDownloader/2.0"})
    return session

SHARED_SESSION = create_session()

def is_valid_geotiff(path):
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 10000:
        return False
    try:
        with rasterio.open(path) as src:
            if src.width > 0 and src.height > 0:
                return True
    except Exception:
        return False
    return False

def sign_asset_url(raw_href):
    clean_url = raw_href.split('?')[0]
    sign_api = f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={clean_url}"
    for attempt in range(5):
        try:
            resp = SHARED_SESSION.get(sign_api, timeout=30)
            if resp.status_code == 200:
                return resp.json().get('href')
            time.sleep(1 + attempt * 2)
        except Exception:
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"Failed to sign URL after 5 attempts: {clean_url}")

def download_single_band(task_info):
    scene, tile_id, band_key, target_fname, target_path, raw_href = task_info
    
    # Pre-check: skip if already valid on disk
    if is_valid_geotiff(target_path):
        sz_mb = os.path.getsize(target_path) / (1024 * 1024)
        log(f"SKIP (Already Valid): {tile_id} {band_key} ({sz_mb:.1f} MB)")
        return True, tile_id, band_key, 0.0

    temp_path = target_path + ".tmp"
    url = None

    for attempt in range(5):
        try:
            if url is None:
                url = sign_asset_url(raw_href)
            
            t0 = time.time()
            resp = SHARED_SESSION.get(url, stream=True, timeout=60)
            
            # If token expired or auth issue, re-sign
            if resp.status_code in (401, 403):
                url = sign_asset_url(raw_href)
                resp = SHARED_SESSION.get(url, stream=True, timeout=60)

            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code} for {band_key}")

            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            
            log(f"START: {tile_id} {band_key} -> {total_size/(1024*1024):.1f} MB (Worker active)")
            
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1048576):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

            # Strict completeness verification
            if total_size > 0 and downloaded != total_size:
                raise RuntimeError(f"Incomplete download: {downloaded}/{total_size} bytes")

            # Rasterio GeoTIFF integrity verification
            if is_valid_geotiff(temp_path):
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.replace(temp_path, target_path)
                dt = time.time() - t0
                speed = (downloaded / (1024 * 1024)) / dt if dt > 0 else 0
                log(f"SUCCESS: {tile_id} {band_key} ({downloaded/(1024*1024):.1f} MB in {dt:.1f}s, {speed:.2f} MB/s)")
                return True, tile_id, band_key, speed
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise RuntimeError("File corrupted or invalid GeoTIFF")

        except Exception as e:
            log(f"RETRY [{attempt+1}/5] {tile_id} {band_key}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            time.sleep(2 + attempt * 3)
            url = None  # Force re-sign on next attempt

    log(f"FAILED permanently: {tile_id} {band_key}")
    return False, tile_id, band_key, 0.0

def run_concurrent_download(max_workers=MAX_WORKERS):
    scenes = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))])
    
    print("=" * 80)
    print("NER-SAFE — HIGH-THROUGHPUT CONCURRENT SENTINEL-2 BAND DOWNLOADER")
    print(f"Workers: {max_workers} Parallel Threads | Target: 13 Scenes (Phase 1 AOI)")
    print("=" * 80)

    # 1. Audit and assemble list of missing bands
    download_queue = []
    total_skipped = 0

    for scene in scenes:
        scene_dir = os.path.join(RAW_DIR, scene)
        meta_path = os.path.join(scene_dir, "metadata.json")
        if not os.path.exists(meta_path):
            continue
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        tile_id = meta.get("properties", {}).get("s2:mgrs_tile", scene.split("_")[4])
        assets = meta.get("assets", {})

        for band_key, fname in BAND_FILE_MAP.items():
            target_path = os.path.join(scene_dir, fname)
            if is_valid_geotiff(target_path):
                total_skipped += 1
                continue
            if band_key in assets and assets[band_key].get("href"):
                raw_href = assets[band_key]["href"]
                download_queue.append((scene, tile_id, band_key, fname, target_path, raw_href))
            else:
                log(f"WARNING: Asset {band_key} missing in metadata for {scene}")

    print(f"Audit Complete: {total_skipped} bands already valid. {len(download_queue)} bands to download.")
    if not download_queue:
        print("\nAll required optical bands are already 100% complete and validated on disk!")
        print("=" * 80)
        return

    print(f"Launching {max_workers} concurrent download workers across {len(download_queue)} remaining bands...\n")
    t_start = time.time()
    completed_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(download_single_band, task): task for task in download_queue}
        for future in as_completed(future_map):
            success, tile_id, band_key, speed = future.result()
            if success:
                completed_count += 1
            else:
                failed_count += 1
            progress_pct = (completed_count + failed_count) / len(download_queue) * 100.0
            log(f"PROGRESS: {completed_count + failed_count}/{len(download_queue)} bands processed ({progress_pct:.1f}%)")

    total_time = time.time() - t_start
    print("\n" + "=" * 80)
    print("CONCURRENT DOWNLOAD COMPLETE")
    print(f"Successfully downloaded: {completed_count} bands")
    print(f"Failed downloads       : {failed_count} bands")
    print(f"Total time elapsed     : {total_time:.1f}s ({total_time/60:.2f} min)")
    print("=" * 80)

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else MAX_WORKERS
    run_concurrent_download(workers)
