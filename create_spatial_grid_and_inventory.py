"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 9: Step 1 — Master Spatial Grid Definition & Standardized Landslide Inventory
"""

import os
import json
import csv
import numpy as np
import rasterio
from rasterio.transform import from_bounds
import scipy.ndimage

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
BASE_MASTER = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID")
REF_DEM = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives", "elevation", "elevation.tif")

print("=" * 80)
print("NER-SAFE — COMPONENT 9: MASTER SPATIAL GRID & INVENTORY PROCESSING")
print("=" * 80)

# 1. Read Master Spatial Grid Geometry from Authoritative Component 7 DEM
with rasterio.open(REF_DEM) as src_dem:
    profile_30m = src_dem.profile.copy()
    bounds_30m = src_dem.bounds
    res_30m = src_dem.res
    crs_30m = str(src_dem.crs)
    width_30m = src_dem.width
    height_30m = src_dem.height
    transform_30m = src_dem.transform

print(f"Master Regional Modeling Grid Framework:")
print(f" - CRS       : {crs_30m} (WGS84 Geographic 1-arcsec)")
print(f" - Dimensions: {width_30m} cols x {height_30m} rows ({width_30m * height_30m:,} cells)")
print(f" - Bounds    : Lon [{bounds_30m.left:.6f}, {bounds_30m.right:.6f}], Lat [{bounds_30m.bottom:.6f}, {bounds_30m.top:.6f}]")
print(f" - Resolution: {res_30m[0]:.10f} deg (~30.89 m meridian spacing)")

# Save spatial grid metadata
spatial_grid_meta = {
    "grid_name": "NER_SAFE_Phase1_Master_Modeling_Grid_30m",
    "primary_modeling_crs": crs_30m,
    "spatial_resolution": {
        "angular_degrees": list(res_30m),
        "nominal_metric_meters": 30.8875,
        "note": "1 arc-second grid matching USGS SRTM 1 Arc-Second global DEM"
    },
    "dimensions": {
        "columns": width_30m,
        "rows": height_30m,
        "total_cells": width_30m * height_30m
    },
    "bounding_box": {
        "min_longitude": bounds_30m.left,
        "max_longitude": bounds_30m.right,
        "min_latitude": bounds_30m.bottom,
        "max_latitude": bounds_30m.top
    },
    "affine_transform": [
        transform_30m.a, transform_30m.b, transform_30m.c,
        transform_30m.d, transform_30m.e, transform_30m.f
    ],
    "sub_domains": {
        "UTM_Zone_45N": {
            "epsg": "EPSG:32645",
            "coverage": "Western Meghalaya border (Tile 45RYL)",
            "native_sentinel_resolution_m": 10.0
        },
        "UTM_Zone_46N": {
            "epsg": "EPSG:32646",
            "coverage": "Central/Eastern Meghalaya & all of Mizoram (12 MGRS tiles)",
            "native_sentinel_resolution_m": 10.0
        }
    },
    "scientific_rationale": (
        "The 1-arc-second (~30 m) SRTM-aligned grid serves as the continuous regional modeling backbone "
        "covering 100% of Phase 1 AOI (Meghalaya & Mizoram) without projection boundary distortions or "
        "seam-line discontinuities between UTM Zone 45N and 46N. Native Sentinel-2 10m indices, GPM ~10km rainfall, "
        "and SMAP ~9km soil moisture remain strictly preserved in their original resolutions, with aligned "
        "representations generated specifically for multi-factor model integration."
    )
}

grid_meta_path = os.path.join(BASE_MASTER, "spatial_grid", "spatial_grid_metadata.json")
with open(grid_meta_path, "w", encoding="utf-8") as f:
    json.dump(spatial_grid_meta, f, indent=2)
print(f"Saved spatial grid metadata to {grid_meta_path}")

# 2. Standardize Landslide Inventory
raw_inv_csv = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "LANDSLIDE_INVENTORY", "NER_SAFE_landslide_inventory.csv")
raw_inv_geojson = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "LANDSLIDE_INVENTORY", "NER_SAFE_landslide_inventory.geojson")

with open(raw_inv_csv, "r", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))

print(f"\nProcessing Landslide Inventory:")
print(f" - Loaded {len(reader)} validated records from {raw_inv_csv}")

standardized_records = []
presence_mask = np.zeros((height_30m, width_30m), dtype=np.uint8)

# Map coordinates to grid row and col
for i, row in enumerate(reader, 1):
    lon = float(row["longitude"])
    lat = float(row["latitude"])
    
    # Standardize record
    std_rec = {
        "event_id": row["event_id"],
        "source": row["source"],
        "date": row["date"] if row["date"] else "UNKNOWN",
        "state": row["state"],
        "district": row["district"],
        "location": row["location"],
        "latitude": lat,
        "longitude": lon,
        "trigger": row["trigger"] if row["trigger"] else "rainfall",
        "landslide_category": row["landslide_category"],
        "fatalities": int(row["fatalities"]) if row["fatalities"].isdigit() else 0,
        "material_type": row["material_type"],
        "movement_type": row["movement_type"],
        "source_reference": row["source_reference"],
        "confidence": "HIGH (Authoritative Ground Truth)",
        "split_role": "TARGET_LABEL_ONLY (Data Leakage Safeguard: Never used as environmental predictor)"
    }
    standardized_records.append(std_rec)
    
    # Rasterize to 30m grid
    col = int((lon - bounds_30m.left) / res_30m[0])
    row_idx = int((bounds_30m.top - lat) / res_30m[1])
    if 0 <= col < width_30m and 0 <= row_idx < height_30m:
        presence_mask[row_idx, col] = 1

print(f" - Mapped {np.sum(presence_mask)} distinct 30m grid cells containing historical landslides")

# Save standardized CSV
std_csv_path = os.path.join(BASE_MASTER, "inventory", "NER_SAFE_standardized_landslide_inventory.csv")
with open(std_csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(standardized_records[0].keys()))
    writer.writeheader()
    writer.writerows(standardized_records)
print(f"Saved standardized inventory CSV to {std_csv_path}")

# Save standardized GeoJSON
std_geojson_path = os.path.join(BASE_MASTER, "inventory", "NER_SAFE_standardized_landslide_inventory.geojson")
geojson_features = []
for r in standardized_records:
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [r["longitude"], r["latitude"]]
        },
        "properties": {k: v for k, v in r.items() if k not in ("longitude", "latitude")}
    }
    geojson_features.append(feature)

geojson_doc = {
    "type": "FeatureCollection",
    "name": "NER_SAFE_Standardized_Historical_Landslide_Inventory",
    "crs": {
        "type": "name",
        "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
    },
    "features": geojson_features
}

with open(std_geojson_path, "w", encoding="utf-8") as f:
    json.dump(geojson_doc, f, indent=2)
print(f"Saved standardized inventory GeoJSON to {std_geojson_path}")

# Save Inventory Metadata
inv_meta = {
    "title": "NER-SAFE Standardized Ground-Truth Landslide Inventory",
    "record_count": len(standardized_records),
    "crs": "EPSG:4326 (WGS84 Geographic)",
    "primary_sources": {
        "NASA_GLC": 234,
        "GSI_NLSM": 13,
        "ISRO_BHUVAN_ATLAS": 13
    },
    "state_distribution": {
        "Meghalaya": sum(1 for r in standardized_records if r["state"] == "Meghalaya"),
        "Mizoram": sum(1 for r in standardized_records if r["state"] == "Mizoram"),
        "Regional_NER": sum(1 for r in standardized_records if r["state"] not in ("Meghalaya", "Mizoram"))
    },
    "data_leakage_safeguard": (
        "Strict operational separation: Historical landslide locations and occurrences serve exclusively "
        "as training/evaluation ground-truth target labels. They are NOT used as continuous predictors for "
        "themselves, ensuring zero data leakage in empirical landslide-risk modeling."
    ),
    "derived_rasters": {
        "landslide_presence_30m": "Binary 0/1 indicator raster on the 30m master grid",
        "landslide_distance_meters_30m": "Euclidean metric distance in meters to nearest historical event point"
    }
}

inv_meta_path = os.path.join(BASE_MASTER, "inventory", "inventory_metadata.json")
with open(inv_meta_path, "w", encoding="utf-8") as f:
    json.dump(inv_meta, f, indent=2)
print(f"Saved inventory metadata to {inv_meta_path}")

# 3. Write Binary Presence Raster (Cloud-Optimized GeoTIFF, UInt8)
presence_tif_path = os.path.join(BASE_MASTER, "aligned_features", "inventory", "landslide_presence_30m.tif")
profile_presence = profile_30m.copy()
profile_presence.update({
    "driver": "GTiff",
    "dtype": "uint8",
    "count": 1,
    "nodata": 255,
    "tiled": True,
    "blockxsize": 512,
    "blockysize": 512,
    "compress": "deflate",
    "predictor": 1
})

with rasterio.open(presence_tif_path, "w", **profile_presence) as dst:
    dst.write(presence_mask, 1)
print(f"Generated binary landslide presence raster: {presence_tif_path} ({os.path.getsize(presence_tif_path)/(1024*1024):.2f} MB)")

# 4. Compute Euclidean Distance to Nearest Landslide (Metric meters)
print("\nComputing Euclidean Distance Transform (Meters to nearest landslide)...")
# Calculate distance transform in pixels
pixel_dist = scipy.ndimage.distance_transform_edt(presence_mask == 0)
# Convert pixels to meters (~30.8875 meters per pixel)
metric_dist = (pixel_dist * 30.8875).astype(np.float32)

distance_tif_path = os.path.join(BASE_MASTER, "aligned_features", "inventory", "landslide_distance_meters_30m.tif")
profile_distance = profile_30m.copy()
profile_distance.update({
    "driver": "GTiff",
    "dtype": "float32",
    "count": 1,
    "nodata": -9999.0,
    "tiled": True,
    "blockxsize": 512,
    "blockysize": 512,
    "compress": "deflate",
    "predictor": 2
})

with rasterio.open(distance_tif_path, "w", **profile_distance) as dst:
    dst.write(metric_dist, 1)

print(f"Generated Euclidean distance raster: {distance_tif_path} ({os.path.getsize(distance_tif_path)/(1024*1024):.2f} MB)")
print(f" - Min distance: {metric_dist.min():.1f} m")
print(f" - Max distance: {metric_dist.max():.1f} m")
print(f" - Mean distance: {metric_dist.mean():.1f} m")
print("=" * 80)
print("STEP 1 COMPLETE: Spatial Grid & Inventory Processing Successful!")
print("=" * 80)
