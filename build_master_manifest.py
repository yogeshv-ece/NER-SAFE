"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 9: Build Master Grid Manifest (MASTER_GRID_manifest.csv)
"""

import os
import glob
import csv
import rasterio

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
BASE_MASTER = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID")

MANIFEST_CSV = os.path.join(BASE_MASTER, "MASTER_GRID_manifest.csv")
MANIFEST_ROOT_CSV = os.path.join(PROJECT_ROOT, "MASTER_GRID_manifest.csv")

layers = []

def add_raster(layer_id, category, layer_type, data_leakage_safeguard, path, res_m, native_res, resamp_method, desc, source):
    if not os.path.exists(path):
        print(f"WARNING: File not found: {path}")
        return
    with rasterio.open(path) as src:
        crs = str(src.crs)
        w = src.width
        h = src.height
        nodata = src.nodata
        dtype = str(src.dtypes[0])
    sz_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
    rel_path = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
    
    layers.append({
        "layer_id": layer_id,
        "category": category,
        "layer_type": layer_type,
        "data_leakage_safeguard": data_leakage_safeguard,
        "file_path": rel_path,
        "format": "GeoTIFF",
        "crs": crs,
        "resolution_meters": res_m,
        "native_resolution": native_res,
        "resampling_method": resamp_method,
        "width": w,
        "height": h,
        "nodata_value": nodata,
        "dtype": dtype,
        "size_mb": sz_mb,
        "temporal_range": "2024-11-01 to 2025-04-30" if category in ["hydrology", "satellite"] else "Static Baseline / Historical",
        "description": desc,
        "source_authority": source
    })

def add_vector(layer_id, category, layer_type, data_leakage_safeguard, path, fmt, desc, source):
    if not os.path.exists(path):
        print(f"WARNING: File not found: {path}")
        return
    sz_mb = round(os.path.getsize(path) / (1024 * 1024), 3)
    rel_path = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
    layers.append({
        "layer_id": layer_id,
        "category": category,
        "layer_type": layer_type,
        "data_leakage_safeguard": data_leakage_safeguard,
        "file_path": rel_path,
        "format": fmt,
        "crs": "EPSG:4326",
        "resolution_meters": "Vector Geometry",
        "native_resolution": "Vector Point/Line/Polygon",
        "resampling_method": "Exact Vector Representation",
        "width": "N/A",
        "height": "N/A",
        "nodata_value": "N/A",
        "dtype": fmt,
        "size_mb": sz_mb,
        "temporal_range": "2007 to 2023" if category == "inventory" else "Static Baseline",
        "description": desc,
        "source_authority": source
    })

print("Cataloging Master Grid Layers...")

# 1. Authoritative Terrain Derivatives (Component 7)
terrain_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "TERRAIN", "derivatives")
add_raster("terrain_elevation_30m", "terrain", "predictor", "Environmental Predictor (Static)",
           os.path.join(terrain_dir, "elevation", "elevation.tif"), 30.89, "30m SRTM", "Native SRTM 1-arcsec",
           "Authoritative SRTM Digital Elevation Model (m) across Phase 1 AOI", "USGS / NASA SRTM")
add_raster("terrain_slope_30m", "terrain", "predictor", "Environmental Predictor (Static)",
           os.path.join(terrain_dir, "slope", "slope_degrees.tif"), 30.89, "30m SRTM", "Component 7 Derivative",
           "Authoritative topographic slope in degrees across Phase 1 AOI", "Component 7 Terrain Engine")
add_raster("terrain_aspect_30m", "terrain", "predictor", "Environmental Predictor (Static)",
           os.path.join(terrain_dir, "aspect", "aspect_degrees.tif"), 30.89, "30m SRTM", "Component 7 Derivative",
           "Authoritative topographic aspect in degrees across Phase 1 AOI", "Component 7 Terrain Engine")
add_raster("terrain_profile_curvature_30m", "terrain", "predictor", "Environmental Predictor (Static)",
           os.path.join(terrain_dir, "profile_curvature", "profile_curvature.tif"), 30.89, "30m SRTM", "Component 7 Derivative",
           "Authoritative profile curvature (m^-1) across Phase 1 AOI", "Component 7 Terrain Engine")
add_raster("terrain_twi_30m", "terrain", "predictor", "Environmental Predictor (Static)",
           os.path.join(terrain_dir, "twi", "twi.tif"), 30.89, "30m SRTM", "Component 7 Derivative",
           "Authoritative Topographic Wetness Index (TWI) across Phase 1 AOI", "Component 7 Terrain Engine")

# 2. Satellite Aligned 30m Rasters
sat_dir = os.path.join(BASE_MASTER, "aligned_features", "satellite")
add_raster("sentinel2_ndvi_30m", "satellite", "predictor", "Environmental Predictor (Dynamic Baseline)",
           os.path.join(sat_dir, "sentinel2_ndvi_30m.tif"), 30.89, "10.0 meters", "Bilinear continuous",
           "Spatially aligned 30m regional mosaic of Normalized Difference Vegetation Index", "ESA Copernicus Sentinel-2 MSI")
add_raster("sentinel2_ndwi_30m", "satellite", "predictor", "Environmental Predictor (Dynamic Baseline)",
           os.path.join(sat_dir, "sentinel2_ndwi_30m.tif"), 30.89, "10.0 meters", "Bilinear continuous",
           "Spatially aligned 30m regional mosaic of Normalized Difference Water Index", "ESA Copernicus Sentinel-2 MSI")
add_raster("sentinel2_ndmi_30m", "satellite", "predictor", "Environmental Predictor (Dynamic Baseline)",
           os.path.join(sat_dir, "sentinel2_ndmi_30m.tif"), 30.89, "10.0 meters", "Bilinear continuous",
           "Spatially aligned 30m regional mosaic of Normalized Difference Moisture Index", "ESA Copernicus Sentinel-2 MSI")
add_raster("sentinel2_scl_30m", "satellite", "predictor", "Environmental Predictor (Discrete Categorical Mask)",
           os.path.join(sat_dir, "sentinel2_scl_30m.tif"), 30.89, "20.0 meters", "STRICTLY Nearest-Neighbor",
           "Spatially aligned 30m Scene Classification Layer (categorical land cover classes preserved)", "ESA Copernicus Sentinel-2 MSI")

# 3. Hydrology Aligned 30m Rasters
hydro_dir = os.path.join(BASE_MASTER, "aligned_features", "hydrology")
gpm_features = [
    ("gpm_rainfall_r1d_max_mm_30m", "Peak 1-day daily precipitation rate (mm/day) across 6-month observation period"),
    ("gpm_rainfall_r1d_mean_mm_30m", "Mean 1-day daily precipitation rate (mm/day) across 6-month observation period"),
    ("gpm_rainfall_r3d_max_mm_30m", "Maximum 3-day cumulative rainfall (mm) representing short-term burst saturation"),
    ("gpm_rainfall_r3d_mean_mm_30m", "Mean 3-day cumulative rainfall (mm) across 6-month observation period"),
    ("gpm_rainfall_r7d_max_mm_30m", "Maximum 7-day cumulative rainfall (mm) representing medium-term slope saturation"),
    ("gpm_rainfall_r7d_mean_mm_30m", "Mean 7-day cumulative rainfall (mm) across 6-month observation period"),
    ("gpm_rainfall_r14d_max_mm_30m", "Maximum 14-day cumulative rainfall (mm) representing deep aquifer saturation"),
    ("gpm_rainfall_r14d_mean_mm_30m", "Mean 14-day cumulative rainfall (mm) across 6-month observation period"),
    ("gpm_rainfall_ari_max_mm_30m", "Maximum Antecedent Rainfall Index (alpha=0.85, 14-day memory)"),
    ("gpm_rainfall_ari_mean_mm_30m", "Mean Antecedent Rainfall Index across 6-month observation period")
]
for fid, desc in gpm_features:
    add_raster(fid, "hydrology", "predictor", "Dynamic Hydrological Trigger Predictor",
               os.path.join(hydro_dir, f"{fid}.tif"), 30.89, "0.1 degree (~10 km)", "Bilinear continuous",
               desc, "NASA GPM IMERG Final Daily (3B-DAY)")

smap_features = [
    ("smap_soil_moisture_mean_30m", "Spatially aligned mean volumetric soil moisture (cm3/cm3)", "Bilinear continuous"),
    ("smap_soil_moisture_max_30m", "Spatially aligned peak volumetric soil moisture (cm3/cm3)", "Bilinear continuous"),
    ("smap_soil_moisture_min_30m", "Spatially aligned minimum volumetric soil moisture (cm3/cm3)", "Bilinear continuous"),
    ("smap_soil_moisture_std_30m", "Spatially aligned volumetric soil moisture standard deviation (cm3/cm3)", "Bilinear continuous"),
    ("smap_valid_observations_count_30m", "Spatially aligned count of valid daily satellite observations (0-180)", "Nearest-Neighbor discrete"),
    ("smap_outage_flag_30m", "Spatially aligned NASA satellite outage flag (1=2025-03-18 payload safe hold unobserved)", "Nearest-Neighbor discrete")
]
for fid, desc, r_meth in smap_features:
    add_raster(fid, "hydrology", "predictor", "Dynamic Soil Moisture Predictor / Quality Flag",
               os.path.join(hydro_dir, f"{fid}.tif"), 30.89, "9008.055 m (~9 km EASE2)", r_meth,
               desc, "NASA SMAP L3 Enhanced Radiometer (L3_SM_P_E)")

# 4. Landslide Inventory (Target Labels & Derived Spatial Metric)
inv_aligned_dir = os.path.join(BASE_MASTER, "aligned_features", "inventory")
inv_dir = os.path.join(BASE_MASTER, "inventory")

add_vector("landslide_inventory_ground_truth_csv", "inventory", "target_label", "GROUND TRUTH ONLY (Target Label - Zero Leakage)",
           os.path.join(inv_dir, "NER_SAFE_standardized_landslide_inventory.csv"), "CSV",
           "Standardized Ground-Truth Historical Landslide Inventory (260 events, NASA GLC, GSI NLSM, ISRO Bhuvan)", "NASA / GSI / ISRO")
add_vector("landslide_inventory_ground_truth_geojson", "inventory", "target_label", "GROUND TRUTH ONLY (Target Label - Zero Leakage)",
           os.path.join(inv_dir, "NER_SAFE_standardized_landslide_inventory.geojson"), "GeoJSON",
           "Standardized Ground-Truth Historical Landslide Vector Points (260 events)", "NASA / GSI / ISRO")
add_raster("landslide_target_presence_30m", "inventory", "target_label", "GROUND TRUTH ONLY (Target Label - Zero Leakage)",
           os.path.join(inv_aligned_dir, "landslide_presence_30m.tif"), 30.89, "Vector Point", "Nearest-Neighbor binary rasterization",
           "Binary spatial occurrence raster (1 = documented landslide initiation/rupture point, 0 = non-occurrence)", "NASA / GSI / ISRO")
add_raster("landslide_distance_meters_30m", "inventory", "derived_spatial_metric", "Derived Spatial Metric Feature (Distance to Known Events)",
           os.path.join(inv_aligned_dir, "landslide_distance_meters_30m.tif"), 30.89, "Vector Point", "Euclidean Distance Transform",
           "Euclidean metric distance (meters) to nearest historical ground-truth landslide event", "Derived from Inventory")

# 5. Exposure & Infrastructure Registered Layers (17 layers for Component 10+)
exp_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "EXPOSURE")
exposure_layers = [
    ("exposure_roads_meghalaya", "roads/Meghalaya_roads.geojson", "Road network polylines for Meghalaya (OSM)"),
    ("exposure_roads_mizoram", "roads/Mizoram_roads.geojson", "Road network polylines for Mizoram (OSM)"),
    ("exposure_roads_phase1_combined", "roads/NER_SAFE_Phase1_roads.geojson", "Complete Phase 1 road network polylines (Meghalaya & Mizoram)"),
    ("exposure_settlements_meghalaya", "settlements/Meghalaya_settlements.geojson", "Settlements and populated places points/polygons for Meghalaya"),
    ("exposure_settlements_mizoram", "settlements/Mizoram_settlements.geojson", "Settlements and populated places points/polygons for Mizoram"),
    ("exposure_settlements_phase1_combined", "settlements/NER_SAFE_Phase1_settlements.geojson", "Complete Phase 1 settlements layer (Meghalaya & Mizoram)"),
    ("exposure_buildings_meghalaya", "buildings/Meghalaya_buildings.geojson", "Building footprints for Meghalaya (OSM)"),
    ("exposure_buildings_mizoram", "buildings/Mizoram_buildings.geojson", "Building footprints for Mizoram (OSM)"),
    ("exposure_buildings_phase1_combined", "buildings/NER_SAFE_Phase1_buildings.geojson", "Complete Phase 1 building footprints layer"),
    ("exposure_admin_meghalaya_districts", "administrative/Meghalaya_districts.geojson", "District administrative boundaries for Meghalaya (geoBoundaries)"),
    ("exposure_admin_meghalaya_state", "administrative/Meghalaya_state_boundary.geojson", "State boundary polygon for Meghalaya"),
    ("exposure_admin_mizoram_districts", "administrative/Mizoram_districts.geojson", "District administrative boundaries for Mizoram (geoBoundaries)"),
    ("exposure_admin_mizoram_state", "administrative/Mizoram_state_boundary.geojson", "State boundary polygon for Mizoram"),
    ("exposure_admin_phase1_districts", "administrative/NER_SAFE_Phase1_districts.geojson", "Complete Phase 1 district boundaries"),
    ("exposure_admin_phase1_states", "administrative/NER_SAFE_Phase1_states.geojson", "Complete Phase 1 state boundaries"),
    ("exposure_transport_lifelines", "transport/NER_SAFE_Phase1_transport.geojson", "Transport lifelines, bus terminals, helipads, and stations"),
    ("exposure_population_demographics", "population/NER_SAFE_Phase1_district_demographics.csv", "District-level population and census demographics summary")
]

for lid, rel_p, desc in exposure_layers:
    full_p = os.path.join(exp_dir, rel_p.replace("/", os.sep))
    fmt = "CSV" if rel_p.endswith(".csv") else "GeoJSON"
    add_vector(lid, "exposure", "exposure_infrastructure", "Exposure Asset (Component 10+ Downstream Impact)",
               full_p, fmt, desc, "OpenStreetMap / geoBoundaries / Census India")

# 6. Preserved Native Collections
native_gpm_dir = os.path.join(BASE_MASTER, "temporal", "rainfall_native_01deg")
for fp in sorted(glob.glob(os.path.join(native_gpm_dir, "*.tif"))):
    bn = os.path.splitext(os.path.basename(fp))[0]
    add_raster(f"native_{bn}", "hydrology_native", "native_observation", "Original Native Resolution Collection",
               fp, 11132.0, "0.1 degree (~10 km)", "Native IMERG NetCDF4 Grid",
               f"Original native 0.1-degree GPM IMERG rainfall raster: {bn}", "NASA GPM IMERG")

native_smap_dir = os.path.join(BASE_MASTER, "temporal", "smap_native_9km")
for fp in sorted(glob.glob(os.path.join(native_smap_dir, "*.tif"))):
    bn = os.path.splitext(os.path.basename(fp))[0]
    add_raster(f"native_{bn}", "hydrology_native", "native_observation", "Original Native Resolution Collection",
               fp, 9008.055, "9008.055 m (EASE-Grid 2.0)", "Native SMAP HDF5 Grid (EPSG:6933)",
               f"Original native ~9km SMAP soil moisture raster: {bn}", "NASA SMAP L3 Enhanced")

print(f"\nTotal Cataloged Master Grid Layers: {len(layers)}")

# Write CSV Manifest
fieldnames = [
    "layer_id", "category", "layer_type", "data_leakage_safeguard",
    "file_path", "format", "crs", "resolution_meters", "native_resolution",
    "resampling_method", "width", "height", "nodata_value", "dtype",
    "size_mb", "temporal_range", "description", "source_authority"
]

with open(MANIFEST_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(layers)

print(f"Saved {MANIFEST_CSV}")

with open(MANIFEST_ROOT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(layers)

print(f"Saved {MANIFEST_ROOT_CSV}")
print("Manifest generation complete!")
