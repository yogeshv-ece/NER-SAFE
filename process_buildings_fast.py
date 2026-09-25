"""
NER-SAFE — Robust Building & Transport Processor
Uses binary SHX index to safely parse building polygons and skip corrupt shapes.
"""

import os
import sys
import json
import csv
import time
import struct
import shapefile
from shapely.geometry import shape, mapping, Point
from shapely.prepared import prep

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
ADMIN_DIR = os.path.join(EXPOSURE_DIR, "administrative")
BUILD_DIR = os.path.join(EXPOSURE_DIR, "buildings")
TRANS_DIR = os.path.join(EXPOSURE_DIR, "transport")
RAW_OSM_DIR = os.path.join(EXPOSURE_DIR, "raw", "osm_northeast_shp")

os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(TRANS_DIR, exist_ok=True)

def load_state_masks():
    print("Loading state boundary polygons for clipping...", flush=True)
    with open(os.path.join(ADMIN_DIR, "Meghalaya_state_boundary.geojson"), "r", encoding="utf-8") as f:
        ml_feat = json.load(f)["features"][0]
        ml_geom = shape(ml_feat["geometry"])
    with open(os.path.join(ADMIN_DIR, "Mizoram_state_boundary.geojson"), "r", encoding="utf-8") as f:
        mz_feat = json.load(f)["features"][0]
        mz_geom = shape(mz_feat["geometry"])
    return {
        "Meghalaya": (ml_geom, prep(ml_geom), ml_geom.bounds),
        "Mizoram": (mz_geom, prep(mz_geom), mz_geom.bounds)
    }

def process_buildings(masks):
    shp_path = os.path.join(RAW_OSM_DIR, "gis_osm_buildings_a_free_1.shp")
    shx_path = os.path.join(RAW_OSM_DIR, "gis_osm_buildings_a_free_1.shx")
    if not (os.path.exists(shp_path) and os.path.exists(shx_path)):
        print("Building files not found!", flush=True)
        return

    print("\n--- Scanning Building Footprints with Binary Spatial Index ---", flush=True)
    t0 = time.time()
    ml_geom, ml_prep, ml_bounds = masks["Meghalaya"]
    mz_geom, mz_prep, mz_bounds = masks["Mizoram"]

    with open(shx_path, "rb") as f:
        shx_bytes = f.read()

    num_records = (len(shx_bytes) - 100) // 8
    print(f"Total building records in Northeast extract: {num_records:,}", flush=True)

    candidates = []
    with open(shp_path, "rb") as f:
        for i in range(num_records):
            offset = struct.unpack(">i", shx_bytes[100 + i*8 : 100 + i*8 + 4])[0] * 2
            f.seek(offset + 8)
            header = f.read(36)
            if len(header) < 36:
                continue
            stype, xmin, ymin, xmax, ymax = struct.unpack("<i4d", header)
            if stype != 5: # Polygon
                continue

            in_ml = not (xmax < ml_bounds[0] or xmin > ml_bounds[2] or ymax < ml_bounds[1] or ymin > ml_bounds[3])
            in_mz = not (xmax < mz_bounds[0] or xmin > mz_bounds[2] or ymax < mz_bounds[1] or ymin > mz_bounds[3])

            if in_ml or in_mz:
                candidates.append((i, "Meghalaya" if in_ml else "Mizoram", (xmin, ymin, xmax, ymax)))

    print(f"Identified {len(candidates):,} candidate buildings within Phase 1 bounding boxes in {time.time() - t0:.2f}s!", flush=True)

    # Now safely extract candidates using shapefile.Reader with index access
    sf = shapefile.Reader(shp_path)
    ml_bldgs = []
    mz_bldgs = []
    skipped = 0

    t1 = time.time()
    for idx, (i, candidate_state, (xmin, ymin, xmax, ymax)) in enumerate(candidates):
        if idx % 50000 == 0 and idx > 0:
            print(f"  Processed {idx:,}/{len(candidates):,} candidate buildings (ML: {len(ml_bldgs):,}, MZ: {len(mz_bldgs):,})...", flush=True)

        c_x = (xmin + xmax) * 0.5
        c_y = (ymin + ymax) * 0.5
        pt = Point(c_x, c_y)

        state = None
        if candidate_state == "Meghalaya" and ml_prep.contains(pt):
            state = "Meghalaya"
        elif candidate_state == "Mizoram" and mz_prep.contains(pt):
            state = "Mizoram"

        if not state:
            continue

        try:
            s = sf.shape(i)
            if not s.points:
                skipped += 1
                continue
            rec = sf.record(i).as_dict()
            geom = shape(s)
            if geom.is_empty:
                skipped += 1
                continue

            area_sqm = round(geom.area * 111320 * 111320, 1)
            feat = {
                "type": "Feature",
                "properties": {
                    "osm_id": str(rec.get("osm_id", "")),
                    "name": rec.get("name") or "Building",
                    "type": rec.get("type", "building"),
                    "state": state,
                    "area_sqm": area_sqm,
                    "centroid_lon": round(c_x, 6),
                    "centroid_lat": round(c_y, 6)
                },
                "geometry": mapping(geom)
            }

            if state == "Meghalaya":
                ml_bldgs.append(feat)
            else:
                mz_bldgs.append(feat)

        except Exception:
            skipped += 1
            continue

    print(f"\nExtracted Buildings in {time.time() - t1:.1f}s (skipped {skipped} invalid records):", flush=True)
    print(f"  Meghalaya Buildings: {len(ml_bldgs):,}", flush=True)
    print(f"  Mizoram Buildings:   {len(mz_bldgs):,}", flush=True)
    print(f"  Total Phase 1:       {len(ml_bldgs) + len(mz_bldgs):,}", flush=True)

    print("Writing building GeoJSON files...", flush=True)
    with open(os.path.join(BUILD_DIR, "Meghalaya_buildings.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Meghalaya_Buildings", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": ml_bldgs}, f)

    with open(os.path.join(BUILD_DIR, "Mizoram_buildings.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Mizoram_Buildings", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": mz_bldgs}, f)

    combined_bldgs = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Buildings",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": ml_bldgs + mz_bldgs
    }
    with open(os.path.join(BUILD_DIR, "NER_SAFE_Phase1_buildings.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_bldgs, f)

    summary_path = os.path.join(BUILD_DIR, "NER_SAFE_Phase1_buildings_summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "total_buildings", "total_footprint_sqm", "avg_footprint_sqm"])
        for st, bldgs in [("Meghalaya", ml_bldgs), ("Mizoram", mz_bldgs)]:
            tot_area = sum(b["properties"]["area_sqm"] for b in bldgs)
            avg_area = round(tot_area / len(bldgs), 1) if bldgs else 0
            writer.writerow([st, len(bldgs), round(tot_area, 1), avg_area])
    print(f"Buildings summary saved to: {summary_path}", flush=True)

def process_transport(masks):
    shp_path = os.path.join(RAW_OSM_DIR, "gis_osm_transport_free_1.shp")
    if not os.path.exists(shp_path):
        return

    print("\n--- Processing Transport Lifelines (Helipads, Bus Stations, Terminals) ---", flush=True)
    t0 = time.time()
    ml_geom, ml_prep, ml_bounds = masks["Meghalaya"]
    mz_geom, mz_prep, mz_bounds = masks["Mizoram"]

    sf = shapefile.Reader(shp_path)
    ml_trans = []
    mz_trans = []

    for shape_rec in sf.iterShapeRecords():
        shp = shape_rec.shape
        rec = shape_rec.record.as_dict()
        pt_x, pt_y = shp.points[0]
        pt = Point(pt_x, pt_y)

        state = None
        if ml_prep.contains(pt):
            state = "Meghalaya"
        elif mz_prep.contains(pt):
            state = "Mizoram"

        if not state:
            continue

        props = {
            "osm_id": str(rec.get("osm_id", "")),
            "name": rec.get("name") or "Transport Facility",
            "fclass": rec.get("fclass", ""),
            "state": state,
            "longitude": round(pt_x, 6),
            "latitude": round(pt_y, 6)
        }

        feat = {
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Point", "coordinates": [round(pt_x, 6), round(pt_y, 6)]}
        }

        if state == "Meghalaya":
            ml_trans.append(feat)
        else:
            mz_trans.append(feat)

    print(f"Extracted Transport Facilities in {time.time() - t0:.1f}s:", flush=True)
    print(f"  Meghalaya Transport: {len(ml_trans):,}", flush=True)
    print(f"  Mizoram Transport:   {len(mz_trans):,}", flush=True)

    combined_trans = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Transport_Facilities",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": ml_trans + mz_trans
    }
    with open(os.path.join(TRANS_DIR, "NER_SAFE_Phase1_transport.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_trans, f, indent=2)

if __name__ == "__main__":
    masks = load_state_masks()
    process_buildings(masks)
    process_transport(masks)
    print("\nDone processing buildings and transport!")
