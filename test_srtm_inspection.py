import os
import zipfile
import numpy as np

RAW_DIR = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SRTM_DEM\raw"

REQUIRED_TILES = [
    "N21E092", "N21E093",
    "N22E092", "N22E093",
    "N23E092", "N23E093",
    "N24E092", "N24E093",
    "N25E089", "N25E090", "N25E091", "N25E092",
    "N26E089", "N26E090", "N26E091", "N26E092"
]

print(f"Scanning 16 SRTM tiles in {RAW_DIR}...")
tile_stats = {}
for tile in REQUIRED_TILES:
    zip_name = f"{tile}.SRTMGL1.hgt.zip"
    zip_path = os.path.join(RAW_DIR, zip_name)
    if not os.path.exists(zip_path):
        print(f"MISSING: {zip_name}")
        continue
    with zipfile.ZipFile(zip_path, 'r') as z:
        hgt_name = [m for m in z.namelist() if m.endswith('.hgt')][0]
        data = z.read(hgt_name)
        arr = np.frombuffer(data, dtype='>i2').reshape((3601, 3601))
        # Parse tile origin
        lat_sign = 1 if tile[0] == 'N' else -1
        lat = lat_sign * int(tile[1:3])
        lon_sign = 1 if tile[3] == 'E' else -1
        lon = lon_sign * int(tile[4:7])
        tile_stats[tile] = {
            "lat": lat, "lon": lon,
            "min": int(np.min(arr)), "max": int(np.max(arr)),
            "mean": float(np.mean(arr)),
            "nodata_count": int(np.sum(arr == -32768))
        }
        print(f" - {tile}: Origin=({lat}N, {lon}E), Min={tile_stats[tile]['min']}m, Max={tile_stats[tile]['max']}m, Mean={tile_stats[tile]['mean']:.1f}m, NoData={tile_stats[tile]['nodata_count']}")

print(f"Total tiles successfully verified: {len(tile_stats)}/16")
