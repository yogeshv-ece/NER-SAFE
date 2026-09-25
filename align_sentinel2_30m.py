"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 9: Step 4 — Sentinel-2 Regional 30m Alignment

SCIENTIFIC SAFEGUARDS:
1. Validated 10m NDVI/NDWI/NDMI products in NER_SAFE_DATA/SENTINEL2/indices/ are 100% UNTOUCHED.
2. Continuous optical indices (NDVI, NDWI, NDMI) use Bilinear resampling.
3. SCL (Scene Classification Layer) contains discrete categorical classes (0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11)
   and is STRICTLY resampled using Nearest-Neighbor interpolation (zero decimal smoothing or artificial classes).
4. Windowed reprojection is used to guarantee low memory usage and high computational throughput.
5. All outputs match the Master 30m Grid exactly (EPSG:4326, 18001x21601, nodata=-9999.0 for indices, 0 for SCL).
"""

import os
import glob
import json
import gc
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds
from rasterio.windows import transform as window_transform

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
BASE_MASTER = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID")
S2_INDICES_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL2", "indices")
S2_RAW_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL", "raw")
REF_DEM = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives", "elevation", "elevation.tif")

SATELLITE_OUT = os.path.join(BASE_MASTER, "aligned_features", "satellite")
os.makedirs(SATELLITE_OUT, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 9: SENTINEL-2 30M REGIONAL ALIGNMENT & MOSAICKING")
print("=" * 80)

# 1. Read Master 30m Grid Profile
with rasterio.open(REF_DEM) as src_dem:
    profile_30m = src_dem.profile.copy()
    bounds_30m = src_dem.bounds
    res_30m = src_dem.res
    width_30m = src_dem.width
    height_30m = src_dem.height
    transform_30m = src_dem.transform
    crs_30m = src_dem.crs

print(f"Master 30m Regional Grid Profile:")
print(f" - Dimensions : {width_30m} cols x {height_30m} rows")
print(f" - CRS        : {crs_30m}")
print(f" - Resolution : {res_30m[0]:.8f}, {res_30m[1]:.8f} degrees (~30.89 m)")
print(f" - Bounds     : Lon [{bounds_30m.left:.4f}, {bounds_30m.right:.4f}], Lat [{bounds_30m.bottom:.4f}, {bounds_30m.top:.4f}]")

# 2. Discover the 13 scenes
scene_dirs = sorted([d for d in glob.glob(os.path.join(S2_RAW_DIR, "*")) if os.path.isdir(d)])
print(f"\nDiscovered {len(scene_dirs)} Sentinel-2 raw scene directories.")
if len(scene_dirs) != 13:
    raise RuntimeError(f"Expected 13 scenes, found {len(scene_dirs)}")

# Discover all index files per scene
scenes_info = []
for sd in scene_dirs:
    sname = os.path.basename(sd)
    parts = sname.split("_")
    tile_id = parts[5]
    acq_date = parts[2][:8] # YYYYMMDD
    
    ndvi_fp = os.path.join(S2_INDICES_DIR, "NDVI", f"{sname}_NDVI_10m.tif")
    ndwi_fp = os.path.join(S2_INDICES_DIR, "NDWI", f"{sname}_NDWI_10m.tif")
    ndmi_fp = os.path.join(S2_INDICES_DIR, "NDMI", f"{sname}_NDMI_10m.tif")
    scl_fp = os.path.join(sd, "SCL_Classification_20m.tif")
    
    for p in [ndvi_fp, ndwi_fp, ndmi_fp, scl_fp]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing required raster: {p}")
            
    scenes_info.append({
        "scene_name": sname,
        "tile": tile_id,
        "date": acq_date,
        "NDVI": ndvi_fp,
        "NDWI": ndwi_fp,
        "NDMI": ndmi_fp,
        "SCL": scl_fp
    })

print(f"Verified all 13 scenes have valid NDVI, NDWI, NDMI (10m) and SCL (20m) rasters.")

# Sort scenes chronologically so that later observations take precedence in overlap zones
scenes_info.sort(key=lambda x: x["date"])
print("\nChronological order of scene integration:")
for s in scenes_info:
    print(f" - Tile {s['tile']}: Date {s['date']} ({s['scene_name'][:30]}...)")

# Helper function to align and mosaic a feature across the 13 scenes using windowed reprojection
def mosaic_and_align_feature(feature_key, out_filename, resampling_method, dtype, nodata_val, desc):
    print(f"\nProcessing {feature_key} -> {out_filename} (Resampling: {resampling_method.name}, dtype: {dtype})...")
    
    # Initialize regional canvas
    canvas = np.full((height_30m, width_30m), nodata_val, dtype=dtype)
    
    out_profile = profile_30m.copy()
    predictor = 1 if np.issubdtype(np.dtype(dtype), np.integer) else 2
    out_profile.update({
        "driver": "GTiff",
        "dtype": dtype,
        "nodata": nodata_val,
        "count": 1,
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "deflate",
        "predictor": predictor
    })
    
    out_fp = os.path.join(SATELLITE_OUT, out_filename)
    
    for s_idx, s in enumerate(scenes_info):
        src_path = s[feature_key]
        with rasterio.open(src_path) as src:
            src_arr = src.read(1)
            src_nodata = src.nodata if src.nodata is not None else (0 if feature_key == "SCL" else -9999.0)
            
            # Compute tile bounds in EPSG:4326
            tb = transform_bounds(src.crs, crs_30m, *src.bounds)
            
            # Compute intersection window in master grid
            win = window_from_bounds(*tb, transform=transform_30m).round_lengths().round_offsets()
            col_off = max(0, int(win.col_off))
            row_off = max(0, int(win.row_off))
            win_w = min(int(win.width), width_30m - col_off)
            win_h = min(int(win.height), height_30m - row_off)
            
            if win_w <= 0 or win_h <= 0:
                continue
                
            win_clamped = rasterio.windows.Window(col_off, row_off, win_w, win_h)
            win_tf = window_transform(win_clamped, transform_30m)
            
            # Reproject only into the window
            win_dest = np.full((win_h, win_w), nodata_val, dtype=dtype)
            
            reproject(
                source=src_arr,
                destination=win_dest,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=win_tf,
                dst_crs=crs_30m,
                src_nodata=src_nodata,
                dst_nodata=nodata_val,
                resampling=resampling_method
            )
            
            # Update canvas where window has valid data
            canvas_slice = canvas[row_off:row_off + win_h, col_off:col_off + win_w]
            valid_mask = (win_dest != nodata_val)
            canvas_slice[valid_mask] = win_dest[valid_mask]
            
        print(f"   [{s_idx+1}/13] Integrated Tile {s['tile']} ({s['date']}) - window ({win_w}x{win_h})")
        gc.collect()
        
    # Write final master GeoTIFF
    print(f"Writing {out_filename} to disk...")
    with rasterio.open(out_fp, "w", **out_profile) as dst:
        dst.write(canvas, 1)
        dst.update_tags(
            DESCRIPTION=desc,
            RESAMPLING=resampling_method.name,
            SOURCE_SENSOR="Sentinel-2 MSI Level-2A (ESA / Copernicus)",
            RESOLUTION="30.89 meters (1 arc-sec EPSG:4326)",
            SAFEGUARD="Native 10m validated index products remain untouched."
        )
        
    sz_mb = os.path.getsize(out_fp) / (1024 * 1024)
    valid_cells = np.sum(canvas != nodata_val)
    valid_pct = (valid_cells / canvas.size) * 100.0
    print(f"SUCCESS: {out_filename} ({sz_mb:.2f} MB, {valid_cells:,} valid cells, {valid_pct:.1f}% AOI coverage)")
    
    del canvas
    gc.collect()

# 3. Align NDVI, NDWI, NDMI using Bilinear continuous resampling
mosaic_and_align_feature(
    feature_key="NDVI",
    out_filename="sentinel2_ndvi_30m.tif",
    resampling_method=Resampling.bilinear,
    dtype=np.float32,
    nodata_val=-9999.0,
    desc="Spatially aligned 30m Normalized Difference Vegetation Index (NDVI) mosaic across Phase 1 AOI"
)

mosaic_and_align_feature(
    feature_key="NDWI",
    out_filename="sentinel2_ndwi_30m.tif",
    resampling_method=Resampling.bilinear,
    dtype=np.float32,
    nodata_val=-9999.0,
    desc="Spatially aligned 30m Normalized Difference Water Index (NDWI) mosaic across Phase 1 AOI"
)

mosaic_and_align_feature(
    feature_key="NDMI",
    out_filename="sentinel2_ndmi_30m.tif",
    resampling_method=Resampling.bilinear,
    dtype=np.float32,
    nodata_val=-9999.0,
    desc="Spatially aligned 30m Normalized Difference Moisture Index (NDMI) mosaic across Phase 1 AOI"
)

# 4. Align SCL using STRICTLY Nearest-Neighbor resampling to preserve discrete categorical classes
mosaic_and_align_feature(
    feature_key="SCL",
    out_filename="sentinel2_scl_30m.tif",
    resampling_method=Resampling.nearest,
    dtype=np.uint8,
    nodata_val=0,
    desc="Spatially aligned 30m Scene Classification Layer (SCL) mosaic (strictly nearest-neighbor categorical classes)"
)

print("\n" + "=" * 80)
print("STEP 4 COMPLETE: Sentinel-2 Regional 30m Alignment Successful!")
print("=" * 80)
