"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 9: Step 2 — GPM IMERG Rainfall Time-Series Harmonization & Accumulation Features
"""

import os
import glob
import json
import numpy as np
import h5py
import rasterio
from rasterio.transform import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import reproject

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
BASE_MASTER = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID")
GPM_DIR = os.path.join(PROJECT_ROOT, "GPM_Rainfall")
REF_DEM = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives", "elevation", "elevation.tif")

NATIVE_OUT = os.path.join(BASE_MASTER, "temporal", "rainfall_native_01deg")
ALIGNED_OUT = os.path.join(BASE_MASTER, "aligned_features", "hydrology")

os.makedirs(NATIVE_OUT, exist_ok=True)
os.makedirs(ALIGNED_OUT, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 9: GPM IMERG RAINFALL PROCESSING & SPATIAL ALIGNMENT")
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

# 2. Discover and sort all 181 GPM IMERG daily files
gpm_files = sorted(glob.glob(os.path.join(GPM_DIR, "*.nc4")))
print(f"Discovered {len(gpm_files)} GPM IMERG Daily NetCDF4 files in {GPM_DIR}")
if len(gpm_files) != 181:
    raise RuntimeError(f"Expected 181 GPM files, found {len(gpm_files)}")

# Read coordinate grids from first file
with h5py.File(gpm_files[0], "r") as h5:
    lons = h5["lon"][:]
    lats = h5["lat"][:]

lon_res = float(lons[1] - lons[0])
lat_res = float(lats[1] - lats[0])
n_lons = len(lons)
n_lats = len(lats)

# Bounding box for native GPM grid (cell outer edges)
gpm_left = float(lons.min()) - lon_res / 2.0
gpm_right = float(lons.max()) + lon_res / 2.0
gpm_bottom = float(lats.min()) - lat_res / 2.0
gpm_top = float(lats.max()) + lat_res / 2.0

gpm_transform = from_bounds(gpm_left, gpm_bottom, gpm_right, gpm_top, n_lons, n_lats)

print(f"Native GPM IMERG Grid:")
print(f" - Lon range: [{gpm_left:.3f}, {gpm_right:.3f}] ({n_lons} cells, res={lon_res:.4f} deg)")
print(f" - Lat range: [{gpm_bottom:.3f}, {gpm_top:.3f}] ({n_lats} cells, res={lat_res:.4f} deg)")
print(f" - Grid Shape: {n_lats} rows x {n_lons} cols (~10 km resolution)")

# 3. Load entire 181-day time series into memory: shape (181, n_lats, n_lons)
# In GPM NetCDF4, shape is (1, lon=45, lat=55). We transpose to (lat, lon) = (55, 45).
# Also note that lats increase from South to North, but raster rows typically go from North to South.
daily_rain = np.zeros((len(gpm_files), n_lats, n_lons), dtype=np.float32)
observation_dates = []

for t_idx, fp in enumerate(gpm_files):
    fn = os.path.basename(fp)
    d_str = fn.split(".")[4][:8]
    date_iso = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
    observation_dates.append(date_iso)
    
    with h5py.File(fp, "r") as h5:
        # shape is (1, lon, lat)
        arr = h5["precipitation"][0] # (lon, lat)
        # transpose to (lat, lon) and flip vertically so row 0 is top (North)
        arr_latlon = arr.T # shape (55, 45)
        arr_flipped = np.flipud(arr_latlon) # row 0 is North
        # Clean fill values: negative values clamped to 0.0 mm/day
        arr_clean = np.where((arr_flipped < 0) | np.isnan(arr_flipped), 0.0, arr_flipped).astype(np.float32)
        daily_rain[t_idx] = arr_clean

print(f"Loaded all {len(observation_dates)} daily rainfall grids ({observation_dates[0]} to {observation_dates[-1]}).")
print(f" - Overall Min Daily Rainfall : {daily_rain.min():.2f} mm/day")
print(f" - Overall Max Daily Rainfall : {daily_rain.max():.2f} mm/day")
print(f" - Overall Mean Daily Rainfall: {daily_rain.mean():.2f} mm/day")

# 4. Compute Cumulative Accumulation Windows & Antecedent Rainfall Index (ARI)
print("\nComputing Landslide Triggering Hydrological Accumulation Features:")

# R1d (Daily Rainfall)
r1d_max = np.max(daily_rain, axis=0)
r1d_mean = np.mean(daily_rain, axis=0)

# R3d (3-Day Cumulative Rainfall: sum of t-2, t-1, t)
r3d_stack = np.zeros_like(daily_rain)
for t in range(len(gpm_files)):
    start_t = max(0, t - 2)
    r3d_stack[t] = np.sum(daily_rain[start_t:t+1], axis=0)
r3d_max = np.max(r3d_stack, axis=0)
r3d_mean = np.mean(r3d_stack, axis=0)

# R7d (7-Day Cumulative Rainfall: sum of t-6 to t)
r7d_stack = np.zeros_like(daily_rain)
for t in range(len(gpm_files)):
    start_t = max(0, t - 6)
    r7d_stack[t] = np.sum(daily_rain[start_t:t+1], axis=0)
r7d_max = np.max(r7d_stack, axis=0)
r7d_mean = np.mean(r7d_stack, axis=0)

# R14d (14-Day Cumulative Rainfall: sum of t-13 to t)
r14d_stack = np.zeros_like(daily_rain)
for t in range(len(gpm_files)):
    start_t = max(0, t - 13)
    r14d_stack[t] = np.sum(daily_rain[start_t:t+1], axis=0)
r14d_max = np.max(r14d_stack, axis=0)
r14d_mean = np.mean(r14d_stack, axis=0)

# ARI (Antecedent Rainfall Index with decay coefficient alpha = 0.85)
# ARI_t = sum_{k=0}^{14} (alpha^k * R_{t-k})
alpha = 0.85
weights = np.array([alpha**k for k in range(15)], dtype=np.float32)
weights = weights / np.sum(weights) # normalized decay kernel

ari_stack = np.zeros_like(daily_rain)
for t in range(len(gpm_files)):
    window_len = min(15, t + 1)
    # daily_rain slice backwards from t
    sub_slice = daily_rain[t - window_len + 1:t + 1][::-1] # [R_t, R_{t-1}, ...]
    w = weights[:window_len] / np.sum(weights[:window_len])
    ari_stack[t] = np.sum(sub_slice * w[:, None, None], axis=0)
ari_max = np.max(ari_stack, axis=0)
ari_mean = np.mean(ari_stack, axis=0)

print(f" - R1d  Max : {r1d_max.max():.2f} mm | Mean: {r1d_mean.mean():.2f} mm/day")
print(f" - R3d  Max : {r3d_max.max():.2f} mm | Mean: {r3d_mean.mean():.2f} mm")
print(f" - R7d  Max : {r7d_max.max():.2f} mm | Mean: {r7d_mean.mean():.2f} mm")
print(f" - R14d Max : {r14d_max.max():.2f} mm | Mean: {r14d_mean.mean():.2f} mm")
print(f" - ARI  Max : {ari_max.max():.2f} mm | Mean: {ari_mean.mean():.2f} mm")

# 5. Save Native 0.1 deg GeoTIFFs (Preserving original resolution)
feature_dict = {
    "rainfall_r1d_max_mm": (r1d_max, "Peak daily precipitation rate (mm/day) across baseline observation period"),
    "rainfall_r1d_mean_mm": (r1d_mean, "Mean daily precipitation rate (mm/day) across baseline observation period"),
    "rainfall_r3d_max_mm": (r3d_max, "Maximum 3-day cumulative rainfall (mm) representing short-term burst saturation"),
    "rainfall_r3d_mean_mm": (r3d_mean, "Mean 3-day cumulative rainfall (mm) across baseline observation period"),
    "rainfall_r7d_max_mm": (r7d_max, "Maximum 7-day cumulative rainfall (mm) representing medium-term slope saturation"),
    "rainfall_r7d_mean_mm": (r7d_mean, "Mean 7-day cumulative rainfall (mm) across baseline observation period"),
    "rainfall_r14d_max_mm": (r14d_max, "Maximum 14-day cumulative rainfall (mm) representing deep-seated aquifer saturation"),
    "rainfall_r14d_mean_mm": (r14d_mean, "Mean 14-day cumulative rainfall (mm) across baseline observation period"),
    "rainfall_ari_max_mm": (ari_max, "Maximum Antecedent Rainfall Index (alpha=0.85, 14-day memory)"),
    "rainfall_ari_mean_mm": (ari_mean, "Mean Antecedent Rainfall Index across baseline observation period")
}

profile_native = {
    "driver": "GTiff",
    "dtype": "float32",
    "nodata": -9999.0,
    "width": n_lons,
    "height": n_lats,
    "count": 1,
    "crs": "EPSG:4326",
    "transform": gpm_transform,
    "compress": "deflate"
}

for fname, (arr, desc) in feature_dict.items():
    native_fp = os.path.join(NATIVE_OUT, f"{fname}_native01deg.tif")
    with rasterio.open(native_fp, "w", **profile_native) as dst:
        dst.write(arr, 1)

print(f"\nSaved {len(feature_dict)} native 0.1-degree rainfall rasters to {NATIVE_OUT}")

# 6. Spatially Align to 30m Master Modeling Grid (Bilinear Continuous Resampling)
# IMPORTANT: Clearly mark in profile and metadata that this represents an aligned/interpolated representation.
print("\nSpatially Aligning Rainfall Features to 30m Regional Modeling Grid...")

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

for fname, (arr, desc) in feature_dict.items():
    aligned_fp = os.path.join(ALIGNED_OUT, f"gpm_{fname}_30m.tif")
    destination = np.full((height_30m, width_30m), -9999.0, dtype=np.float32)
    
    # Reproject / resample from GPM grid to 30m master grid via Bilinear Interpolation
    reproject(
        source=arr,
        destination=destination,
        src_transform=gpm_transform,
        src_crs="EPSG:4326",
        dst_transform=transform_30m,
        dst_crs=crs_30m,
        src_nodata=-9999.0,
        dst_nodata=-9999.0,
        resampling=Resampling.bilinear
    )
    
    with rasterio.open(aligned_fp, "w", **profile_aligned) as dst:
        dst.write(destination, 1)
        
    sz_mb = os.path.getsize(aligned_fp) / (1024 * 1024)
    valid_pct = (np.sum(destination != -9999.0) / destination.size) * 100.0
    print(f" - {os.path.basename(aligned_fp)} ({sz_mb:.2f} MB, {valid_pct:.1f}% valid cells)")

print("=" * 80)
print("STEP 2 COMPLETE: GPM IMERG Rainfall Processing Successful!")
print("=" * 80)
