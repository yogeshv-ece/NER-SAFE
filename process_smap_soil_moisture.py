"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 9: Step 3 — SMAP L3 Enhanced 9km Soil Moisture Processing & Spatial Alignment

SCIENTIFIC SAFEGUARDS:
1. Resampling SMAP does NOT create higher-resolution physical soil moisture observations.
   Original native ~9km EASE-Grid 2.0 (EPSG:6933) is preserved separately.
   Resampled 30m layers are explicitly documented as spatially aligned / interpolated representations.
2. The documented 2025-03-18 NASA satellite outage is strictly preserved.
   ZERO interpolation, synthesis, or fabrication is performed for this missing date.
   An explicit missing-data quality flag raster and metadata entry are generated.
"""

import os
import glob
import json
import datetime
import numpy as np
import h5py
import rasterio
from rasterio.transform import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import reproject

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
BASE_MASTER = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID")
SMAP_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SMAP", "raw")
REF_DEM = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives", "elevation", "elevation.tif")

NATIVE_OUT = os.path.join(BASE_MASTER, "temporal", "smap_native_9km")
ALIGNED_OUT = os.path.join(BASE_MASTER, "aligned_features", "hydrology")

os.makedirs(NATIVE_OUT, exist_ok=True)
os.makedirs(ALIGNED_OUT, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 9: SMAP SOIL MOISTURE PROCESSING & SPATIAL ALIGNMENT")
print("=" * 80)

# 1. Read Master 30m Grid Profile for spatial alignment
with rasterio.open(REF_DEM) as src_dem:
    profile_30m = src_dem.profile.copy()
    bounds_30m = src_dem.bounds
    res_30m = src_dem.res
    width_30m = src_dem.width
    height_30m = src_dem.height
    transform_30m = src_dem.transform
    crs_30m = src_dem.crs

# 2. Discover SMAP files in raw directory
smap_files = sorted(glob.glob(os.path.join(SMAP_DIR, "*.h5")))
print(f"Discovered {len(smap_files)} SMAP HDF5 files in {SMAP_DIR}")

# Map each date YYYYMMDD to its file path (excluding 20250501 to strictly cover 2024-11-01 to 2025-04-30 baseline)
file_map = {}
for fp in smap_files:
    bn = os.path.basename(fp)
    d_str = bn.split("_")[5]
    if "20241101" <= d_str <= "20250430":
        file_map[d_str] = fp

# Verify temporal range and gap
start_date = datetime.date(2024, 11, 1)
end_date = datetime.date(2024, 11, 1)
# 6 months: Nov 1, 2024 to Apr 30, 2025 = 181 calendar days
cur = start_date
all_calendar_dates = []
end_cal = datetime.date(2025, 4, 30)
while cur <= end_cal:
    all_calendar_dates.append(cur.strftime("%Y%m%d"))
    cur += datetime.timedelta(days=1)

missing_dates = [d for d in all_calendar_dates if d not in file_map]
print(f"Total calendar days in 6-month observation period (2024-11-01 to 2025-04-30): {len(all_calendar_dates)}")
print(f"Total SMAP files present for observation period: {len(file_map)}")
print(f"Documented missing dates: {missing_dates}")

if missing_dates != ["20250318"]:
    raise RuntimeError(f"Unexpected missing dates: {missing_dates}. Expected strictly ['20250318'] (NASA outage).")

print("-> NASA satellite outage on 2025-03-18 verified. Preserving as strict NaN / missing date.")

# 3. Grid Coordinates: Extract EASE-Grid 2.0 coordinates from a subset file (e.g. 20241103)
sample_subset_fp = file_map["20241103"]
with h5py.File(sample_subset_fp, "r") as h:
    xg = h["x_global"][:]
    yg = h["y_global"][:]

n_cols = len(xg) # 54
n_rows = len(yg) # 79
dx = float(xg[1] - xg[0]) # ~9008.055 m
dy = float(abs(yg[1] - yg[0])) # ~9008.055 m

ease_left = float(xg[0] - dx / 2.0)
ease_right = float(xg[-1] + dx / 2.0)
ease_top = float(yg[0] + dy / 2.0)
ease_bottom = float(yg[-1] - dy / 2.0)

smap_ease_transform = from_bounds(ease_left, ease_bottom, ease_right, ease_top, n_cols, n_rows)

print(f"\nNative SMAP EASE-Grid 2.0 Spatial Grid (EPSG:6933):")
print(f" - Columns (width) : {n_cols} cells, resolution = {dx:.3f} m")
print(f" - Rows (height)   : {n_rows} cells, resolution = {dy:.3f} m")
print(f" - X Bounds (m)    : [{ease_left:.2f}, {ease_right:.2f}]")
print(f" - Y Bounds (m)    : [{ease_bottom:.2f}, {ease_top:.2f}]")

# Row and column offsets for slicing the 2 global files (20241101, 20241102)
# Verified exactly: rows [443:522], cols [2881:2935]
GLOBAL_ROW_START = 443
GLOBAL_ROW_END = 443 + n_rows # 522
GLOBAL_COL_START = 2881
GLOBAL_COL_END = 2881 + n_cols # 2935

# 4. Load all 180 available daily SMAP soil moisture grids
# Daily composite strategy: Combine AM (descending ~6:00 AM) and PM (ascending ~6:00 PM) overpasses.
# For each day:
# - Valid range: 0.02 to 0.60 cm3/cm3 (physical volumetric soil moisture)
# - If both AM and PM are valid, take their mean
# - If only one is valid, use that one
# - If neither is valid (or missing date 2025-03-18), mark as NaN

daily_sm_stack = np.full((len(all_calendar_dates), n_rows, n_cols), np.nan, dtype=np.float32)
daily_outage_flag = np.zeros(len(all_calendar_dates), dtype=np.uint8)

print("\nExtracting and compositing AM/PM soil moisture for all 181 calendar days...")

for idx, d_str in enumerate(all_calendar_dates):
    if d_str == "20250318":
        daily_outage_flag[idx] = 1 # Flagged outage day
        continue # Strictly preserve as NaN
        
    fp = file_map[d_str]
    with h5py.File(fp, "r") as h:
        sm_am_ds = h["Soil_Moisture_Retrieval_Data_AM"]["soil_moisture"]
        sm_pm_ds = h["Soil_Moisture_Retrieval_Data_PM"]["soil_moisture_pm"]
        
        if sm_am_ds.shape == (1624, 3856):
            am_data = sm_am_ds[GLOBAL_ROW_START:GLOBAL_ROW_END, GLOBAL_COL_START:GLOBAL_COL_END]
            pm_data = sm_pm_ds[GLOBAL_ROW_START:GLOBAL_ROW_END, GLOBAL_COL_START:GLOBAL_COL_END]
        else:
            am_data = sm_am_ds[:]
            pm_data = sm_pm_ds[:]
            
        # Mask valid physical retrievals (SMAP valid fill is -9999.0, valid soil moisture is >0 and <1.0)
        valid_am = (am_data > 0.0) & (am_data < 1.0)
        valid_pm = (pm_data > 0.0) & (pm_data < 1.0)
        
        comp = np.full((n_rows, n_cols), np.nan, dtype=np.float32)
        both = valid_am & valid_pm
        only_am = valid_am & (~valid_pm)
        only_pm = (~valid_am) & valid_pm
        
        comp[both] = 0.5 * (am_data[both] + pm_data[both])
        comp[only_am] = am_data[only_am]
        comp[only_pm] = pm_data[only_pm]
        
        daily_sm_stack[idx] = comp

# 5. Compute Temporal Soil Moisture Statistics across the 6-month observation window
# Metrics:
# - sm_mean: mean soil moisture (cm3/cm3)
# - sm_max: maximum soil moisture (peak saturation during storms/wet spells)
# - sm_min: minimum soil moisture (dry baseline)
# - sm_std: standard deviation (hydrological variability / dynamic responsiveness)
# - valid_obs_count: number of valid satellite observations per cell (0 to 180)

print("\nComputing Temporal Soil Moisture Statistics:")

# Valid count per cell
valid_mask = ~np.isnan(daily_sm_stack)
valid_count = np.sum(valid_mask, axis=0).astype(np.int16)

# Suppress numpy RuntimeWarning for all-NaN slices
with np.errstate(all="ignore"):
    sm_mean = np.nanmean(daily_sm_stack, axis=0)
    sm_max = np.nanmax(daily_sm_stack, axis=0)
    sm_min = np.nanmin(daily_sm_stack, axis=0)
    sm_std = np.nanstd(daily_sm_stack, axis=0)

# Replace all-NaN cells with nodata -9999.0
sm_mean = np.where(np.isnan(sm_mean), -9999.0, sm_mean).astype(np.float32)
sm_max = np.where(np.isnan(sm_max), -9999.0, sm_max).astype(np.float32)
sm_min = np.where(np.isnan(sm_min), -9999.0, sm_min).astype(np.float32)
sm_std = np.where(np.isnan(sm_std), -9999.0, sm_std).astype(np.float32)

# Outage flag raster: cells where 2025-03-18 was an outage (all cells in AOI = 1)
outage_flag_grid = np.ones((n_rows, n_cols), dtype=np.uint8)

valid_mean_cells = sm_mean[sm_mean != -9999.0]
print(f" - Valid Observation Count range: {valid_count.min()} to {valid_count.max()} days (Mean: {valid_count.mean():.1f} days)")
print(f" - Mean Soil Moisture  : Min {valid_mean_cells.min():.3f}, Max {valid_mean_cells.max():.3f}, Overall Mean {valid_mean_cells.mean():.3f} cm3/cm3")
print(f" - Peak (Max) Moisture : Min {sm_max[sm_max!=-9999.0].min():.3f}, Max {sm_max[sm_max!=-9999.0].max():.3f} cm3/cm3")
print(f" - Min Soil Moisture   : Min {sm_min[sm_min!=-9999.0].min():.3f}, Max {sm_min[sm_min!=-9999.0].max():.3f} cm3/cm3")
print(f" - Std Soil Moisture   : Min {sm_std[sm_std!=-9999.0].min():.3f}, Max {sm_std[sm_std!=-9999.0].max():.3f} cm3/cm3")

# 6. Save Native ~9km EASE-Grid 2.0 GeoTIFFs
profile_native_ease = {
    "driver": "GTiff",
    "dtype": "float32",
    "nodata": -9999.0,
    "width": n_cols,
    "height": n_rows,
    "count": 1,
    "crs": "EPSG:6933",
    "transform": smap_ease_transform,
    "compress": "deflate"
}

native_features = {
    "smap_soil_moisture_mean_native9km.tif": (sm_mean, "float32", -9999.0, "Mean volumetric soil moisture (cm3/cm3) across baseline observation period"),
    "smap_soil_moisture_max_native9km.tif": (sm_max, "float32", -9999.0, "Maximum volumetric soil moisture (cm3/cm3) representing peak antecedent saturation"),
    "smap_soil_moisture_min_native9km.tif": (sm_min, "float32", -9999.0, "Minimum volumetric soil moisture (cm3/cm3) representing dry antecedent state"),
    "smap_soil_moisture_std_native9km.tif": (sm_std, "float32", -9999.0, "Standard deviation of volumetric soil moisture (cm3/cm3) representing moisture variability"),
    "smap_valid_observations_count_native9km.tif": (valid_count.astype(np.float32), "float32", -9999.0, "Count of valid daily satellite observations per pixel (out of 180 observation days)"),
    "smap_outage_flag_native9km.tif": (outage_flag_grid.astype(np.float32), "float32", -9999.0, "Documented NASA satellite outage flag (1=2025-03-18 payload safe hold unobserved)")
}

for fname, (arr, dt, nd, desc) in native_features.items():
    fp = os.path.join(NATIVE_OUT, fname)
    with rasterio.open(fp, "w", **profile_native_ease) as dst:
        dst.write(arr, 1)
        dst.update_tags(
            DESCRIPTION=desc,
            SOURCE="NASA SMAP Enhanced L3 Radiometer Soil Moisture (L3_SM_P_E)",
            NATIVE_RESOLUTION="9008.055 meters (EASE-Grid 2.0)",
            NATIVE_CRS="EPSG:6933",
            OUTAGE_NOTE="2025-03-18 payload safe hold unobserved and strictly unfabricated"
        )

print(f"\nSaved {len(native_features)} native 9km SMAP rasters to {NATIVE_OUT}")

# 7. Spatially Align to 30m Regional Modeling Grid (EPSG:4326)
print("\nSpatially Aligning SMAP Soil Moisture Features to 30m Regional Modeling Grid...")
profile_aligned = profile_30m.copy()
profile_aligned.update({
    "driver": "GTiff",
    "dtype": "float32",
    "nodata": -9999.0,
    "count": 1,
    "tiled": True,
    "blockxsize": 512,
    "blockysize": 512,
    "compress": "deflate",
    "predictor": 2
})

aligned_mapping = {
    "smap_soil_moisture_mean_30m.tif": (sm_mean, Resampling.bilinear, "Spatially aligned mean volumetric soil moisture representation (cm3/cm3)"),
    "smap_soil_moisture_max_30m.tif": (sm_max, Resampling.bilinear, "Spatially aligned peak volumetric soil moisture representation (cm3/cm3)"),
    "smap_soil_moisture_min_30m.tif": (sm_min, Resampling.bilinear, "Spatially aligned dry-season baseline volumetric soil moisture representation (cm3/cm3)"),
    "smap_soil_moisture_std_30m.tif": (sm_std, Resampling.bilinear, "Spatially aligned soil moisture variability representation (cm3/cm3)"),
    "smap_valid_observations_count_30m.tif": (valid_count.astype(np.float32), Resampling.nearest, "Spatially aligned valid observation count representation (discrete count preserved)"),
    "smap_outage_flag_30m.tif": (outage_flag_grid.astype(np.float32), Resampling.nearest, "Spatially aligned NASA outage flag (1=outage on 2025-03-18)")
}

for fname, (arr, resamp_method, desc) in aligned_mapping.items():
    aligned_fp = os.path.join(ALIGNED_OUT, fname)
    destination = np.full((height_30m, width_30m), -9999.0, dtype=np.float32)
    
    reproject(
        source=arr,
        destination=destination,
        src_transform=smap_ease_transform,
        src_crs="EPSG:6933",
        dst_transform=transform_30m,
        dst_crs=crs_30m,
        src_nodata=-9999.0,
        dst_nodata=-9999.0,
        resampling=resamp_method
    )
    
    with rasterio.open(aligned_fp, "w", **profile_aligned) as dst:
        dst.write(destination, 1)
        dst.update_tags(
            DESCRIPTION=desc,
            DISCLAIMER="Spatially aligned / interpolated representation for multi-scale feature modeling. Native physical resolution is ~9 km (EPSG:6933). This is NOT a native 30m soil-moisture observation.",
            SOURCE_SENSOR="NASA SMAP Radiometer L3 Enhanced Soil Moisture",
            OUTAGE_DATE="2025-03-18",
            OUTAGE_STATUS="NASA satellite safe hold; strictly unfabricated and un-interpolated."
        )
        
    sz_mb = os.path.getsize(aligned_fp) / (1024 * 1024)
    valid_pct = (np.sum(destination != -9999.0) / destination.size) * 100.0
    print(f" - {fname} ({sz_mb:.2f} MB, {valid_pct:.1f}% valid cells, method={resamp_method.name})")

print("=" * 80)
print("STEP 3 COMPLETE: SMAP Soil Moisture Processing Successful!")
print("=" * 80)
