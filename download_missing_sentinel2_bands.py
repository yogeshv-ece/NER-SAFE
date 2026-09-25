"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 8: Sentinel-2 Level-2A Missing Optical Band Downloader
Source: Official Copernicus Sentinel-2 MSI Level-2A via Microsoft Planetary Computer STAC
Target: 13 MGRS Tiles across Phase 1 AOI (Meghalaya & Mizoram)
"""

import os
import sys
import time
import json
import requests
import rasterio

RAW_DIR = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SENTINEL\raw"

BAND_FILE_MAP = {
    "B02": "B02_Blue_10m.tif",
    "B03": "B03_Green_10m.tif",
    "B04": "B04_Red_10m.tif",
    "B08": "B08_NIR_10m.tif",
    "B11": "B11_SWIR1_20m.tif",
    "B12": "B12_SWIR2_20m.tif"
}

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
            resp = requests.get(sign_api, timeout=30)
            if resp.status_code == 200:
                return resp.json().get('href')
            time.sleep(1 + attempt * 2)
        except Exception as e:
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"Failed to sign URL after 5 attempts: {clean_url}")

def download_file(url, target_path):
    temp_path = target_path + ".tmp"
    headers = {"User-Agent": "NER-SAFE-Downloader/1.0"}
    
    for attempt in range(5):
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=60)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP Error {resp.status_code}")
            
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            t0 = time.time()
            
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1048576):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and (time.time() - t0 > 2.0):
                            pct = (downloaded / total_size) * 100.0
                            sys.stdout.write(f"\r   Downloading: {downloaded/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB ({pct:.1f}%)")
                            sys.stdout.flush()
                            t0 = time.time()
                            
            sys.stdout.write("\n")
            
            # Verify download completeness
            if total_size > 0 and downloaded < total_size:
                raise RuntimeError(f"Download incomplete: {downloaded}/{total_size} bytes")

            # Verify raster
            if is_valid_geotiff(temp_path):
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.replace(temp_path, target_path)
                return True
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise RuntimeError("Downloaded file failed rasterio validation")
                
        except Exception as e:
            print(f"\n   [Attempt {attempt+1}/5] Error: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            time.sleep(2 + attempt * 3)
            # Re-sign in case token expired
            try:
                url = sign_asset_url(url.split('?')[0])
            except Exception:
                pass
                
    return False

def complete_sentinel2_optical_bands():
    scenes = sorted([d for d in os.listdir(RAW_DIR) if os.path.isdir(os.path.join(RAW_DIR, d))])
    print("="*80)
    print(f"NER-SAFE — SENTINEL-2 OPTICAL SURFACE REFLECTANCE COMPLETION")
    print(f"Auditing & Downloading Missing Bands Across {len(scenes)} Scenes")
    print("="*80)

    total_needed = 0
    total_downloaded = 0
    total_skipped = 0
    failed_downloads = []

    for i, scene in enumerate(scenes, 1):
        scene_dir = os.path.join(RAW_DIR, scene)
        meta_path = os.path.join(scene_dir, "metadata.json")
        
        if not os.path.exists(meta_path):
            print(f"[{i}/{len(scenes)}] ERROR: No metadata.json for {scene}")
            continue
            
        with open(meta_path, "r", encoding="utf-8") as mf:
            meta = json.load(mf)
            
        assets = meta.get("assets", {})
        tile_id = meta.get("properties", {}).get("s2:mgrs_tile", scene.split("_")[5])
        
        print(f"\n[{i}/{len(scenes)}] Scene: {scene} (Tile: {tile_id})")
        
        for band_key, target_fname in BAND_FILE_MAP.items():
            target_path = os.path.join(scene_dir, target_fname)
            
            # Check if valid file already exists
            if is_valid_geotiff(target_path):
                sz_mb = os.path.getsize(target_path) / (1024 * 1024)
                print(f" - {band_key} ({target_fname}): VALID ({sz_mb:.1f} MB) -> Skipped")
                total_skipped += 1
                continue
                
            total_needed += 1
            if band_key not in assets:
                print(f" - {band_key}: NOT FOUND in metadata assets!")
                failed_downloads.append((scene, band_key, "Asset not in metadata"))
                continue
                
            raw_href = assets[band_key].get("href", "")
            if not raw_href:
                print(f" - {band_key}: Empty href in metadata!")
                failed_downloads.append((scene, band_key, "Empty href"))
                continue
                
            print(f" - {band_key} ({target_fname}): MISSING -> Fetching from Planetary Computer...")
            t0 = time.time()
            try:
                signed_url = sign_asset_url(raw_href)
                success = download_file(signed_url, target_path)
                if success:
                    sz_mb = os.path.getsize(target_path) / (1024 * 1024)
                    print(f"   SUCCESS: Downloaded {target_fname} ({sz_mb:.1f} MB in {time.time()-t0:.1f}s)")
                    total_downloaded += 1
                else:
                    print(f"   FAILED to download {target_fname}")
                    failed_downloads.append((scene, band_key, "Download failed"))
            except Exception as e:
                print(f"   EXCEPTION for {band_key}: {e}")
                failed_downloads.append((scene, band_key, str(e)))

    print("\n" + "="*80)
    print("COMPLETION SUMMARY")
    print("="*80)
    print(f"Total Bands Required Across All Scenes: {len(scenes) * len(BAND_FILE_MAP)}")
    print(f"Already Valid (Skipped)               : {total_skipped}")
    print(f"Successfully Downloaded               : {total_downloaded}")
    print(f"Failed Downloads                      : {len(failed_downloads)}")
    if failed_downloads:
        print("\nFailures:")
        for s, b, r in failed_downloads:
            print(f" - {s} | Band {b}: {r}")
    else:
        print("\nALL 13 SENTINEL-2 SCENES ARE NOW 100% COMPLETE WITH ALL OPTICAL BANDS!")
    print("="*80)

if __name__ == "__main__":
    complete_sentinel2_optical_bands()
