"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 8: Sentinel-2 Surface Reflectance Indices Generation
Calculates: NDVI (10m), NDWI (10m), NDMI (10m) for all 13 Phase 1 Scenes

Verified Level-2A Radiometric Scaling (from ESA MTD_MSIL2A.xml metadata):
  BOA_QUANTIFICATION_VALUE = 10000.0
  BOA_ADD_OFFSET = -1000.0
  Surface Reflectance rho = (DN - 1000.0) / 10000.0 (for DN > 0)
"""

import os
import sys
import time
import json
import rasterio
from rasterio.windows import Window, from_bounds
from rasterio.enums import Resampling
import numpy as np

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
RAW_SENTINEL = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL", "raw")
OUT_BASE = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL2", "indices")

NDVI_DIR = os.path.join(OUT_BASE, "NDVI")
NDWI_DIR = os.path.join(OUT_BASE, "NDWI")
NDMI_DIR = os.path.join(OUT_BASE, "NDMI")

for d in [NDVI_DIR, NDWI_DIR, NDMI_DIR]:
    os.makedirs(d, exist_ok=True)

NODATA_VAL = -9999.0

# Verified ESA Level-2A radiometric scaling constants
BOA_QUANTIFICATION_VALUE = 10000.0
BOA_ADD_OFFSET = -1000.0

# SCL Masking Policy:
# 0 = NO_DATA
# 1 = SATURATED_OR_DEFECTIVE
# 3 = CLOUD_SHADOWS
# 8 = CLOUD_MEDIUM_PROBABILITY
# 9 = CLOUD_HIGH_PROBABILITY
# 10 = THIN_CIRRUS
SCL_INVALID_CLASSES = {0, 1, 3, 8, 9, 10}

def dn_to_reflectance(dn_arr):
    """
    Converts raw Level-2A digital numbers to physical surface reflectance (0.0 to ~1.0)
    using the verified ESA baseline parameters: (DN - 1000) / 10000.
    Pixels with DN == 0 are instrument NoData.
    Physical surface reflectance is constrained to the physical lower bound rho >= 0.0,
    eliminating atmospheric correction over-subtraction artifacts that distort denominators.
    """
    valid = (dn_arr > 0)
    refl = np.full_like(dn_arr, np.nan, dtype=np.float32)
    raw_refl = (dn_arr[valid].astype(np.float32) + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
    refl[valid] = np.maximum(0.0, raw_refl)
    return refl, valid

def process_scene_indices(scene_name):
    scene_dir = os.path.join(RAW_SENTINEL, scene_name)
    b04_path = os.path.join(scene_dir, "B04_Red_10m.tif")
    b08_path = os.path.join(scene_dir, "B08_NIR_10m.tif")
    b03_path = os.path.join(scene_dir, "B03_Green_10m.tif")
    b11_path = os.path.join(scene_dir, "B11_SWIR1_20m.tif")
    scl_path = os.path.join(scene_dir, "SCL_Classification_20m.tif")

    for p in [b04_path, b08_path, b03_path, b11_path, scl_path]:
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            raise FileNotFoundError(f"Missing required band file: {p}")

    ndvi_out = os.path.join(NDVI_DIR, f"{scene_name}_NDVI_10m.tif")
    ndwi_out = os.path.join(NDWI_DIR, f"{scene_name}_NDWI_10m.tif")
    ndmi_out = os.path.join(NDMI_DIR, f"{scene_name}_NDMI_10m.tif")

    # Skip if all three valid index GeoTIFFs already exist
    if (os.path.exists(ndvi_out) and os.path.exists(ndwi_out) and os.path.exists(ndmi_out) and
        os.path.getsize(ndvi_out) > 50000000 and os.path.getsize(ndwi_out) > 50000000 and os.path.getsize(ndmi_out) > 50000000):
        print(f"\nScene: {scene_name} -> Indices already generated and valid. Skipping.")
        return

    # Read reference profile from B08 (10m master grid)
    with rasterio.open(b08_path) as src_b08:
        profile = src_b08.profile.copy()
        width = src_b08.width
        height = src_b08.height
        crs = src_b08.crs

    profile.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": NODATA_VAL,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": 2
    })

    print(f"\nProcessing Scene: {scene_name}")
    print(f" - Grid Dimensions: {width} x {height} ({width*height:,} pixels at 10m)")
    print(f" - CRS: {crs}")
    t0 = time.time()

    dst_ndvi = rasterio.open(ndvi_out, "w", **profile)
    dst_ndwi = rasterio.open(ndwi_out, "w", **profile)
    dst_ndmi = rasterio.open(ndmi_out, "w", **profile)

    chunk_size = 2048

    with rasterio.open(b04_path) as src_b04, \
         rasterio.open(b08_path) as src_b08, \
         rasterio.open(b03_path) as src_b03, \
         rasterio.open(b11_path) as src_b11, \
         rasterio.open(scl_path) as src_scl:

        for r in range(0, height, chunk_size):
            r_len = min(chunk_size, height - r)
            win_10m = Window(0, r, width, r_len)

            # 1. Read 10m bands (raw DN uint16)
            raw_b04 = src_b04.read(1, window=win_10m)
            raw_b08 = src_b08.read(1, window=win_10m)
            raw_b03 = src_b03.read(1, window=win_10m)

            # Convert to physical surface reflectance using verified ESA Level-2A offset and scale
            refl_b04, v_b04 = dn_to_reflectance(raw_b04)
            refl_b08, v_b08 = dn_to_reflectance(raw_b08)
            refl_b03, v_b03 = dn_to_reflectance(raw_b03)

            # Calculate exact spatial bounds corresponding to the 10m window
            win_bounds = src_b08.window_bounds(win_10m)
            win_b11 = from_bounds(*win_bounds, transform=src_b11.transform)
            win_scl = from_bounds(*win_bounds, transform=src_scl.transform)

            # 2. Resample 20m B11 to 10m master grid via BILINEAR interpolation (continuous surface reflectance)
            raw_b11 = src_b11.read(
                1,
                window=win_b11,
                out_shape=(r_len, width),
                resampling=Resampling.bilinear
            )
            refl_b11, v_b11 = dn_to_reflectance(raw_b11)

            # 3. Resample 20m SCL to 10m master grid via NEAREST-NEIGHBOR ONLY (discrete categorical classes)
            scl = src_scl.read(
                1,
                window=win_scl,
                out_shape=(r_len, width),
                resampling=Resampling.nearest
            )

            # Quality mask: filter out clouds (8,9,10), shadows (3), defective (1), and nodata (0)
            scl_valid = np.ones((r_len, width), dtype=bool)
            for c in SCL_INVALID_CLASSES:
                scl_valid &= (scl != c)

            # -------------------------------------------------------------
            # 1. NDVI = (B08 - B04) / (B08 + B04)
            # -------------------------------------------------------------
            denom_ndvi = refl_b08 + refl_b04
            mask_ndvi = scl_valid & v_b08 & v_b04 & (denom_ndvi > 0)
            ndvi = np.full((r_len, width), NODATA_VAL, dtype=np.float32)
            ndvi[mask_ndvi] = (refl_b08[mask_ndvi] - refl_b04[mask_ndvi]) / denom_ndvi[mask_ndvi]

            # -------------------------------------------------------------
            # 2. NDWI = (B03 - B08) / (B03 + B08) [McFeeters 1996 / Gao]
            # -------------------------------------------------------------
            denom_ndwi = refl_b03 + refl_b08
            mask_ndwi = scl_valid & v_b03 & v_b08 & (denom_ndwi > 0)
            ndwi = np.full((r_len, width), NODATA_VAL, dtype=np.float32)
            ndwi[mask_ndwi] = (refl_b03[mask_ndwi] - refl_b08[mask_ndwi]) / denom_ndwi[mask_ndwi]

            # -------------------------------------------------------------
            # 3. NDMI = (B08 - B11) / (B08 + B11) [Gao 1996 Canopy Moisture]
            # -------------------------------------------------------------
            denom_ndmi = refl_b08 + refl_b11
            mask_ndmi = scl_valid & v_b08 & v_b11 & (denom_ndmi > 0)
            ndmi = np.full((r_len, width), NODATA_VAL, dtype=np.float32)
            ndmi[mask_ndmi] = (refl_b08[mask_ndmi] - refl_b11[mask_ndmi]) / denom_ndmi[mask_ndmi]

            # Write outputs (zero artificial clipping enforced)
            dst_ndvi.write(ndvi, 1, window=win_10m)
            dst_ndwi.write(ndwi, 1, window=win_10m)
            dst_ndmi.write(ndmi, 1, window=win_10m)

            sys.stdout.write(f"\r   Streaming rows {r:5d} to {r+r_len:5d} / {height} ({r/height*100:4.1f}%)")
            sys.stdout.flush()

    dst_ndvi.close()
    dst_ndwi.close()
    dst_ndmi.close()
    print(f"\n - Generated NDVI, NDWI, NDMI in {time.time()-t0:.1f}s")

def generate_all_indices():
    scenes = sorted([d for d in os.listdir(RAW_SENTINEL) if os.path.isdir(os.path.join(RAW_SENTINEL, d))])
    print("="*80)
    print("NER-SAFE — SENTINEL-2 MULTISPECTRAL INDICES GENERATION PIPELINE")
    print(f"Target: {len(scenes)} Scenes across Phase 1 AOI (Meghalaya & Mizoram)")
    print("="*80)

    t_total = time.time()
    success_count = 0
    failed_scenes = []

    for i, scene in enumerate(scenes, 1):
        print(f"\n[{i}/{len(scenes)}] Processing {scene}...")
        try:
            process_scene_indices(scene)
            success_count += 1
        except Exception as e:
            print(f"ERROR processing {scene}: {e}")
            failed_scenes.append((scene, str(e)))

    total_elapsed = time.time() - t_total
    print("\n" + "="*80)
    print("INDICES GENERATION PIPELINE COMPLETE")
    print(f"Successfully processed: {success_count} / {len(scenes)} scenes")
    print(f"Total time elapsed   : {total_elapsed:.1f}s ({total_elapsed/60:.2f} min)")
    if failed_scenes:
        print("Failures:")
        for s, err in failed_scenes:
            print(f" - {s}: {err}")
    print("="*80)

if __name__ == "__main__":
    generate_all_indices()
