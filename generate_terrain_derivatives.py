"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 7: Static Terrain Derivatives Generation Pipeline
Authoritative Source: Validated SRTM 1 Arc-Second DEM (~30 m, EPSG:4326)
Phase 1 AOI: Meghalaya & Mizoram (21.0°N–27.0°N, 89.0°E–94.0°E)
"""

import os
import sys
import time
import zipfile
import json
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window

# Define project directories
PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
RAW_DEM_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SRTM_DEM", "raw")
OUTPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN")
TOP_TERRAIN_DIR = os.path.join(PROJECT_ROOT, "TERRAIN")

RAW_REF_DIR = os.path.join(OUTPUT_BASE_DIR, "raw_reference")
DERIV_DIR = os.path.join(OUTPUT_BASE_DIR, "derivatives")
ELEV_DIR = os.path.join(DERIV_DIR, "elevation")
SLOPE_DIR = os.path.join(DERIV_DIR, "slope")
ASPECT_DIR = os.path.join(DERIV_DIR, "aspect")
CURV_DIR = os.path.join(DERIV_DIR, "profile_curvature")
TWI_DIR = os.path.join(DERIV_DIR, "twi")

for d in [RAW_REF_DIR, ELEV_DIR, SLOPE_DIR, ASPECT_DIR, CURV_DIR, TWI_DIR, TOP_TERRAIN_DIR]:
    os.makedirs(d, exist_ok=True)

# Grid specifications
MIN_LAT, MAX_LAT = 21.0, 27.0
MIN_LON, MAX_LON = 89.0, 94.0
CELL_SIZE = 1.0 / 3600.0  # 1 arc-second (~0.0002777777777777778 degrees)
N_ROWS = int(round((MAX_LAT - MIN_LAT) * 3600)) + 1  # 21,601
N_COLS = int(round((MAX_LON - MIN_LON) * 3600)) + 1  # 18,001
NODATA_VAL = -9999.0

# 16 Validated SRTM tiles
REQUIRED_TILES = [
    # Mizoram block (21–25°N, 92–94°E)
    "N21E092", "N21E093",
    "N22E092", "N22E093",
    "N23E092", "N23E093",
    "N24E092", "N24E093",
    # Meghalaya block (25–27°N, 89–93°E)
    "N25E089", "N25E090", "N25E091", "N25E092",
    "N26E089", "N26E090", "N26E091", "N26E092"
]

TRANSFORM = from_origin(MIN_LON, MAX_LAT, CELL_SIZE, CELL_SIZE)
CRS = "EPSG:4326"

RASTER_PROFILE = {
    "driver": "GTiff",
    "height": N_ROWS,
    "width": N_COLS,
    "count": 1,
    "dtype": "float32",
    "crs": CRS,
    "transform": TRANSFORM,
    "nodata": NODATA_VAL,
    "tiled": True,
    "blockxsize": 512,
    "blockysize": 512,
    "compress": "deflate",
    "predictor": 2
}

def step_1_mosaic_elevation():
    print("\n" + "="*80)
    print("STEP 1: UNPACKING SRTM TILES & BUILDING SEAMLESS ELEVATION MOSAIC")
    print("="*80)
    print(f"Grid Extent : Lon [{MIN_LON}°, {MAX_LON}°], Lat [{MIN_LAT}°, {MAX_LAT}°]")
    print(f"Dimensions  : {N_ROWS} rows x {N_COLS} cols ({N_ROWS * N_COLS:,} cells)")
    print(f"Resolution  : {CELL_SIZE:.10f}° (~30.89 m)")

    # Allocate mosaic in int16 with -32768 NoData (~777 MB RAM)
    elev_mosaic = np.full((N_ROWS, N_COLS), -32768, dtype=np.int16)
    tile_manifest = []

    for tile in REQUIRED_TILES:
        zip_path = os.path.join(RAW_DEM_DIR, f"{tile}.SRTMGL1.hgt.zip")
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Missing required tile archive: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            hgt_name = [m for m in z.namelist() if m.endswith('.hgt')][0]
            raw_bytes = z.read(hgt_name)
            arr = np.frombuffer(raw_bytes, dtype='>i2').reshape((3601, 3601))
            
            # Parse origin
            lat = int(tile[1:3]) * (1 if tile[0] == 'N' else -1)
            lon = int(tile[4:7]) * (1 if tile[3] == 'E' else -1)
            
            # Map into mosaic grid (Row 0 is MAX_LAT = 27.0)
            r_start = int(round((MAX_LAT - (lat + 1)) * 3600))
            r_end = r_start + 3601
            c_start = int(round((lon - MIN_LON) * 3600))
            c_end = c_start + 3601
            
            # Place tile seamlessly
            elev_mosaic[r_start:r_end, c_start:c_end] = arr
            
            tile_manifest.append({
                "tile": tile,
                "lat": lat,
                "lon": lon,
                "r_start": r_start, "r_end": r_end,
                "c_start": c_start, "c_end": c_end,
                "min_m": int(np.min(arr)),
                "max_m": int(np.max(arr)),
                "mean_m": float(np.mean(arr))
            })
            print(f" - Loaded {tile}: Bounds Lat [{lat}°, {lat+1}°], Lon [{lon}°, {lon+1}°], Min={np.min(arr)}m, Max={np.max(arr)}m")

    # Save reference tile manifest
    with open(os.path.join(RAW_REF_DIR, "srtm_tiles_manifest.json"), "w") as f:
        json.dump(tile_manifest, f, indent=2)

    valid_mask = (elev_mosaic != -32768)
    total_valid = int(np.sum(valid_mask))
    print(f"\nSeamless mosaic populated: {total_valid:,} valid cells ({total_valid / (N_ROWS * N_COLS) * 100:.2f}%)")
    print(f"Overall Elevation: Min={np.min(elev_mosaic[valid_mask])}m, Max={np.max(elev_mosaic[valid_mask])}m, Mean={np.mean(elev_mosaic[valid_mask]):.2f}m")

    # Write elevation.tif
    elev_tif_path = os.path.join(ELEV_DIR, "elevation.tif")
    print(f"Writing seamless {elev_tif_path}...")
    t0 = time.time()
    
    with rasterio.open(elev_tif_path, "w", **RASTER_PROFILE) as dst:
        chunk_size = 2048
        for r in range(0, N_ROWS, chunk_size):
            r_len = min(chunk_size, N_ROWS - r)
            sub = elev_mosaic[r:r+r_len, :].astype(np.float32)
            sub[sub == -32768] = NODATA_VAL
            dst.write(sub, 1, window=Window(0, r, N_COLS, r_len))
    print(f"Wrote elevation.tif in {time.time()-t0:.1f}s")
    
    return elev_mosaic, valid_mask

def step_2_compute_3x3_derivatives(elev_mosaic, valid_mask):
    print("\n" + "="*80)
    print("STEP 2: COMPUTING SLOPE, ASPECT & PROFILE CURVATURE (SEAMLESS CHUNK CONVOLUTION)")
    print("="*80)

    slope_tif_path = os.path.join(SLOPE_DIR, "slope_degrees.tif")
    aspect_tif_path = os.path.join(ASPECT_DIR, "aspect_degrees.tif")
    curv_tif_path = os.path.join(CURV_DIR, "profile_curvature.tif")

    profile = RASTER_PROFILE.copy()

    dst_slope = rasterio.open(slope_tif_path, "w", **profile)
    dst_aspect = rasterio.open(aspect_tif_path, "w", **profile)
    dst_curv = rasterio.open(curv_tif_path, "w", **profile)

    # Metric cell size in latitude direction (constant 1 arc-second on meridian)
    d_lat = (1.0 / 3600.0) * (np.pi / 180.0) * 6378137.0  # ~30.8875 m

    chunk_size = 2000
    t_start = time.time()

    print("Streaming seamless row chunks with 1-pixel overlap halo...")
    for r in range(0, N_ROWS, chunk_size):
        r_len = min(chunk_size, N_ROWS - r)
        
        # Load chunk with 1-pixel halo above and below
        r_top = max(0, r - 1)
        r_bottom = min(N_ROWS, r + r_len + 1)
        
        chunk = elev_mosaic[r_top:r_bottom, :].astype(np.float32)
        valid_chunk = (chunk != -32768)
        
        # Pad top or bottom if at absolute raster edge
        if r == 0:
            chunk = np.vstack([chunk[0:1, :], chunk])
            valid_chunk = np.vstack([valid_chunk[0:1, :], valid_chunk])
        if r + r_len == N_ROWS:
            chunk = np.vstack([chunk, chunk[-1:, :]])
            valid_chunk = np.vstack([valid_chunk, valid_chunk[-1:, :]])
            
        val_c = valid_chunk[1:r_len+1, :]
        z_c = chunk[1:r_len+1, :]
        
        # Pad east/west edges by 1 pixel
        chunk_padded = np.pad(chunk, ((0, 0), (1, 1)), mode='edge')
        
        # 3x3 neighbors on padded chunk
        z_n  = chunk_padded[0:r_len,   1:N_COLS+1]
        z_s  = chunk_padded[2:r_len+2, 1:N_COLS+1]
        z_w  = chunk_padded[1:r_len+1, 0:N_COLS]
        z_e  = chunk_padded[1:r_len+1, 2:N_COLS+2]
        z_nw = chunk_padded[0:r_len,   0:N_COLS]
        z_ne = chunk_padded[0:r_len,   2:N_COLS+2]
        z_sw = chunk_padded[2:r_len+2, 0:N_COLS]
        z_se = chunk_padded[2:r_len+2, 2:N_COLS+2]
        
        # Metric cell spacing for each row in chunk
        row_indices = np.arange(r, r + r_len)[:, None]
        lat_chunk = MAX_LAT - row_indices * CELL_SIZE
        d_lon = d_lat * np.cos(np.radians(lat_chunk))  # shape (r_len, 1)

        # -------------------------------------------------------------
        # 1. SLOPE (Horn 1981 weighted finite-difference gradient)
        # -------------------------------------------------------------
        # dz/dx: positive when elevation rises Eastward
        dz_dx = ((z_ne + 2.0 * z_e + z_se) - (z_nw + 2.0 * z_w + z_sw)) / (8.0 * d_lon)
        # dz/dy: positive when elevation rises Northward
        dz_dy = ((z_nw + 2.0 * z_n + z_ne) - (z_sw + 2.0 * z_s + z_se)) / (8.0 * d_lat)

        grad_sq = dz_dx**2 + dz_dy**2
        slope_rad = np.arctan(np.sqrt(grad_sq))
        slope_deg = np.degrees(slope_rad)
        slope_deg[~val_c] = NODATA_VAL

        # -------------------------------------------------------------
        # 2. ASPECT (Azimuth in degrees clockwise from North, 0–360°)
        # Downhill vector is (-dz_dx, -dz_dy).
        # Aspect = 180/pi * atan2(-dz_dx, -dz_dy)
        # -------------------------------------------------------------
        aspect_deg = np.degrees(np.arctan2(-dz_dx, -dz_dy))
        aspect_deg[aspect_deg < 0] += 360.0
        # USGS / GDAL convention: Flat terrain where slope < 0.1° is assigned -1.0
        flat_mask = (slope_deg >= 0.0) & (slope_deg < 0.1) & val_c
        aspect_deg[flat_mask] = -1.0
        aspect_deg[~val_c] = NODATA_VAL

        # -------------------------------------------------------------
        # 3. PROFILE CURVATURE (Zevenbergen & Thorne 1987)
        # Rate of slope change along the flow line. Units: m^-1.
        # Negative = Convex (accelerating flow)
        # Positive = Concave (decelerating flow)
        # -------------------------------------------------------------
        p = (z_e - z_w) / (2.0 * d_lon)
        q = (z_n - z_s) / (2.0 * d_lat)
        A = (z_e - 2.0 * z_c + z_w) / (2.0 * (d_lon**2))
        B = (z_n - 2.0 * z_c + z_s) / (2.0 * (d_lat**2))
        C = ((z_ne - z_nw) - (z_se - z_sw)) / (4.0 * d_lon * d_lat)

        denom = p**2 + q**2
        curv = np.zeros_like(chunk[1:r_len+1, :])
        steep = denom >= 1e-8
        curv[steep] = -2.0 * (A[steep] * p[steep]**2 + B[steep] * q[steep]**2 + C[steep] * p[steep] * q[steep]) / (denom[steep] * (1.0 + denom[steep])**1.5)
        curv[~val_c] = NODATA_VAL

        # Write window
        win = Window(0, r, N_COLS, r_len)
        dst_slope.write(slope_deg.astype(np.float32), 1, window=win)
        dst_aspect.write(aspect_deg.astype(np.float32), 1, window=win)
        dst_curv.write(curv.astype(np.float32), 1, window=win)
        
        sys.stdout.write(f"\rProcessed chunk {r:5d} to {r+r_len:5d} / {N_ROWS} rows ({r/N_ROWS*100:4.1f}%)")
        sys.stdout.flush()

    dst_slope.close()
    dst_aspect.close()
    dst_curv.close()
    print(f"\n3x3 derivatives generated in {time.time()-t_start:.1f}s")

def compute_block_flow_accumulation(elev_sub, valid_sub, origin_lat, d_lat):
    """
    Computes D8 flow direction and topological flow accumulation for a contiguous rectangular block.
    """
    H, W = elev_sub.shape
    lat_arr = origin_lat - np.arange(H) * CELL_SIZE
    d_lon_arr = d_lat * np.cos(np.radians(lat_arr))[:, None]  # shape (H, 1)

    max_drop = np.zeros((H, W), dtype=np.float32)
    target_r = np.full((H, W), -1, dtype=np.int32)
    target_c = np.full((H, W), -1, dtype=np.int32)
    rows_dst, cols_dst = np.indices((H, W), dtype=np.int32)

    # 8 neighbor shifts: (dr, dc)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]

    for dr, dc in directions:
        r_src = slice(max(0, -dr), min(H, H - dr))
        r_dst = slice(max(0, dr), min(H, H + dr))
        c_src = slice(max(0, -dc), min(W, W - dc))
        c_dst = slice(max(0, dc), min(W, W + dc))
        
        # Metric distance for each row in r_src
        d_lon_src = d_lon_arr[r_src]
        if dr == 0:
            dist = d_lon_src
        elif dc == 0:
            dist = d_lat
        else:
            dist = np.hypot(d_lat, d_lon_src)

        v_pair = valid_sub[r_src, c_src] & valid_sub[r_dst, c_dst]
        drop = np.where(v_pair, (elev_sub[r_src, c_src].astype(np.float32) - elev_sub[r_dst, c_dst].astype(np.float32)) / dist, -9999.0)
        better = (drop > max_drop[r_src, c_src]) & (drop > 0.0)
        
        np.copyto(max_drop[r_src, c_src], drop, where=better)
        np.copyto(target_r[r_src, c_src], rows_dst[r_dst, c_dst], where=better)
        np.copyto(target_c[r_src, c_src], cols_dst[r_dst, c_dst], where=better)

    # Flatten targets
    has_flow = (target_r >= 0) & valid_sub
    flat_target = np.full(H * W, -1, dtype=np.int32)
    target_linear = target_r[has_flow] * W + target_c[has_flow]
    flat_target[np.flatnonzero(has_flow)] = target_linear

    # Topological sort by elevation descending
    flat_elev = elev_sub.ravel()
    flat_valid = valid_sub.ravel()
    valid_indices = np.flatnonzero(flat_valid)
    
    order_in_valid = np.argsort(-flat_elev[valid_indices])
    order = valid_indices[order_in_valid]
    sorted_elev = flat_elev[order]
    
    change = np.where(sorted_elev[:-1] != sorted_elev[1:])[0] + 1
    splits = np.concatenate([[0], change, [len(order)]])

    # Accumulate flow
    accum = np.zeros(H * W, dtype=np.float32)
    accum[valid_indices] = 1.0  # Initial weight = 1 cell
    
    for k in range(len(splits) - 1):
        idx = order[splits[k]:splits[k+1]]
        tgt = flat_target[idx]
        val = tgt >= 0
        if np.any(val):
            np.add.at(accum, tgt[val], accum[idx[val]])

    return accum.reshape((H, W))

def step_3_compute_flow_and_twi(elev_mosaic, valid_mask):
    print("\n" + "="*80)
    print("STEP 3: COMPUTING FLOW ACCUMULATION & TOPOGRAPHIC WETNESS INDEX (TWI)")
    print("="*80)

    d_lat = (1.0 / 3600.0) * (np.pi / 180.0) * 6378137.0  # ~30.8875 m
    twi_tif_path = os.path.join(TWI_DIR, "twi.tif")
    
    # Block 1: Meghalaya (Lat 25.0°N to 27.0°N, Lon 89.0°E to 93.0°E)
    # Plus buffer down to Lat 24.9°N in Lon 92–93°E for seamless connection with Mizoram
    print("Computing flow accumulation on Meghalaya contiguous block (8 tiles + buffer)...")
    t0 = time.time()
    r_meg_end = 7201 + 360  # 0.1 degree buffer south
    c_meg_end = 14401
    elev_meg = elev_mosaic[0:r_meg_end, 0:c_meg_end]
    valid_meg = valid_mask[0:r_meg_end, 0:c_meg_end]
    accum_meg = compute_block_flow_accumulation(elev_meg, valid_meg, MAX_LAT, d_lat)
    print(f"Meghalaya block completed in {time.time()-t0:.1f}s | Max Accum: {accum_meg[:7201, :14401].max():.1f}")

    # Block 2: Mizoram (Lat 21.0°N to 25.0°N, Lon 92.0°E to 94.0°E)
    # Plus buffer up to Lat 25.1°N in Lon 92–93°E
    print("Computing flow accumulation on Mizoram contiguous block (8 tiles + buffer)...")
    t0 = time.time()
    r_miz_start = 7200 - 360  # 0.1 degree buffer north
    c_miz_start = 10800
    elev_miz = elev_mosaic[r_miz_start:N_ROWS, c_miz_start:N_COLS]
    valid_miz = valid_mask[r_miz_start:N_ROWS, c_miz_start:N_COLS]
    accum_miz = compute_block_flow_accumulation(elev_miz, valid_miz, MAX_LAT - r_miz_start * CELL_SIZE, d_lat)
    print(f"Mizoram block completed in {time.time()-t0:.1f}s | Max Accum: {accum_miz[360:, :].max():.1f}")

    # Assemble into full mosaic accumulation grid
    accum_full = np.zeros((N_ROWS, N_COLS), dtype=np.float32)
    # Insert Meghalaya (0:7200, 0:14401)
    accum_full[0:7200, 0:14401] = accum_meg[0:7200, 0:14401]
    # Insert Mizoram (7201:N_ROWS, 10800:18001)
    accum_full[7201:N_ROWS, 10800:N_COLS] = accum_miz[361:, :]
    # Shared boundary row 7200 (Lat 25.0°N) at lon 92–93°E (c from 10800 to 14401):
    accum_full[7200, 0:10800] = accum_meg[7200, 0:10800]
    accum_full[7200, 10800:14401] = np.maximum(accum_meg[7200, 10800:14401], accum_miz[360, 0:3601])
    accum_full[7200, 14401:N_COLS] = accum_miz[360, 3601:]

    # Compute TWI chunk by chunk using slope raster
    slope_tif_path = os.path.join(SLOPE_DIR, "slope_degrees.tif")
    print(f"\nComputing Topographic Wetness Index (TWI = ln(a / tan(beta))) and streaming to {twi_tif_path}...")
    t0 = time.time()
    
    beta_min_rad = np.radians(0.1)  # 0.1 degree floor (~0.001745 rad)
    tan_beta_min = np.tan(beta_min_rad)

    dst_twi = rasterio.open(twi_tif_path, "w", **RASTER_PROFILE)
    chunk_size = 2048

    with rasterio.open(slope_tif_path, "r") as src_slope:
        for r in range(0, N_ROWS, chunk_size):
            r_len = min(chunk_size, N_ROWS - r)
            win = Window(0, r, N_COLS, r_len)
            
            slope_chunk = src_slope.read(1, window=win)
            accum_chunk = accum_full[r:r+r_len, :]
            val_chunk = (slope_chunk != NODATA_VAL) & (accum_chunk > 0)
            
            # Specific catchment area a = (accum + 1) * cell_size (m)
            # cell_size = d_lat ~ 30.8875 m
            a = (accum_chunk + 1.0) * d_lat
            
            slope_rad = np.radians(np.maximum(slope_chunk, 0.0))
            tan_beta = np.maximum(np.tan(slope_rad), tan_beta_min)
            
            twi_chunk = np.full((r_len, N_COLS), NODATA_VAL, dtype=np.float32)
            twi_chunk[val_chunk] = np.log(a[val_chunk] / tan_beta[val_chunk])
            
            dst_twi.write(twi_chunk, 1, window=win)
            sys.stdout.write(f"\rStreaming TWI chunk {r:5d} to {r+r_len:5d} / {N_ROWS} rows")
            sys.stdout.flush()

    dst_twi.close()
    print(f"\nTWI generated in {time.time()-t0:.1f}s")

if __name__ == "__main__":
    t_start = time.time()
    print("================================================================================")
    print("NER-SAFE — STATIC TERRAIN DERIVATIVES GENERATION PIPELINE")
    print("================================================================================")
    elev_mosaic, valid_mask = step_1_mosaic_elevation()
    step_2_compute_3x3_derivatives(elev_mosaic, valid_mask)
    step_3_compute_flow_and_twi(elev_mosaic, valid_mask)
    total_sec = time.time() - t_start
    print("\n" + "="*80)
    print(f"TERRAIN DERIVATIVES GENERATION COMPLETE IN {total_sec:.1f}s ({total_sec/60:.2f} min)")
    print("================================================================================")
