"""
NER-SAFE — High-Performance Phase 1 Exposure Spatial Harmonizer
Filters OSM Roads, Settlements, Buildings, and Transport Lifelines
to Meghalaya and Mizoram boundaries using Shapely prepared geometries.
"""

import os
import sys
import json
import csv
import time
import shapefile
from shapely.geometry import shape, mapping, Point, LineString, Polygon
from shapely.prepared import prep

BASE_DIR = r"E:\landslide - Copy\landslide - Copy"
EXPOSURE_DIR = os.path.join(BASE_DIR, "NER_SAFE_DATA", "EXPOSURE")
ADMIN_DIR = os.path.join(EXPOSURE_DIR, "administrative")
ROADS_DIR = os.path.join(EXPOSURE_DIR, "roads")
SETTLE_DIR = os.path.join(EXPOSURE_DIR, "settlements")
BUILD_DIR = os.path.join(EXPOSURE_DIR, "buildings")
TRANS_DIR = os.path.join(EXPOSURE_DIR, "transport")
RAW_OSM_DIR = os.path.join(EXPOSURE_DIR, "raw", "osm_northeast_shp")

for d in [ROADS_DIR, SETTLE_DIR, BUILD_DIR, TRANS_DIR]:
    os.makedirs(d, exist_ok=True)

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

def process_roads(masks):
    shp_path = os.path.join(RAW_OSM_DIR, "gis_osm_roads_free_1.shp")
    if not os.path.exists(shp_path):
        print(f"Road shapefile not found at: {shp_path}", flush=True)
        return

    print("\n--- Processing Roads & Transportation Corridors ---", flush=True)
    t0 = time.time()
    ml_geom, ml_prep, ml_bounds = masks["Meghalaya"]
    mz_geom, mz_prep, mz_bounds = masks["Mizoram"]

    sf = shapefile.Reader(shp_path)
    total_recs = len(sf)
    print(f"Total road features in Northeast extract: {total_recs:,}", flush=True)

    ml_roads = []
    mz_roads = []

    for i, shape_rec in enumerate(sf.iterShapeRecords()):
        if i % 50000 == 0 and i > 0:
            print(f"  Processed {i:,}/{total_recs:,} roads... (found ML: {len(ml_roads):,}, MZ: {len(mz_roads):,})", flush=True)
            
        shp = shape_rec.shape
        bbox = shp.bbox # [minx, miny, maxx, maxy]

        # Spatial filter by bounding box
        in_ml_bbox = not (bbox[2] < ml_bounds[0] or bbox[0] > ml_bounds[2] or bbox[3] < ml_bounds[1] or bbox[1] > ml_bounds[3])
        in_mz_bbox = not (bbox[2] < mz_bounds[0] or bbox[0] > mz_bounds[2] or bbox[3] < mz_bounds[1] or bbox[1] > mz_bounds[3])

        if not (in_ml_bbox or in_mz_bbox):
            continue

        try:
            rec = shape_rec.record.as_dict()
            geom = shape(shp)
            if geom.is_empty:
                continue

            state = None
            if in_ml_bbox and (ml_prep.intersects(geom) or ml_geom.intersects(geom)):
                state = "Meghalaya"
            elif in_mz_bbox and (mz_prep.intersects(geom) or mz_geom.intersects(geom)):
                state = "Mizoram"

            if not state:
                continue

            length_km = round(geom.length * 111.32, 3)
            
            feat_props = {
                "osm_id": str(rec.get("osm_id", "")),
                "name": rec.get("name") or "Unnamed Road",
                "ref": rec.get("ref") or "",
                "fclass": rec.get("fclass", ""),
                "oneway": rec.get("oneway", ""),
                "maxspeed": rec.get("maxspeed", 0),
                "bridge": rec.get("bridge", "F"),
                "tunnel": rec.get("tunnel", "F"),
                "state": state,
                "length_km": length_km
            }

            feature = {
                "type": "Feature",
                "properties": feat_props,
                "geometry": mapping(geom)
            }

            if state == "Meghalaya":
                ml_roads.append(feature)
            else:
                mz_roads.append(feature)

        except Exception:
            continue

    print(f"Extracted Roads in {time.time() - t0:.1f}s:", flush=True)
    print(f"  Meghalaya Roads: {len(ml_roads):,}", flush=True)
    print(f"  Mizoram Roads:   {len(mz_roads):,}", flush=True)
    print(f"  Total Phase 1:   {len(ml_roads) + len(mz_roads):,}", flush=True)

    with open(os.path.join(ROADS_DIR, "Meghalaya_roads.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Meghalaya_Roads", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": ml_roads}, f)

    with open(os.path.join(ROADS_DIR, "Mizoram_roads.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Mizoram_Roads", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": mz_roads}, f)

    combined_roads = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Roads",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": ml_roads + mz_roads
    }
    with open(os.path.join(ROADS_DIR, "NER_SAFE_Phase1_roads.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_roads, f)

    # Summary CSV
    summary_path = os.path.join(ROADS_DIR, "NER_SAFE_Phase1_roads_summary.csv")
    type_counts = {}
    for r in ml_roads + mz_roads:
        p = r["properties"]
        key = (p["state"], p["fclass"])
        if key not in type_counts:
            type_counts[key] = {"count": 0, "total_km": 0.0}
        type_counts[key]["count"] += 1
        type_counts[key]["total_km"] += p["length_km"]

    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["state", "road_fclass", "segment_count", "total_length_km"])
        for (st, fc), stats in sorted(type_counts.items()):
            writer.writerow([st, fc, stats["count"], round(stats["total_km"], 2)])
    print(f"Road summary saved to: {summary_path}", flush=True)

def process_settlements(masks):
    shp_path = os.path.join(RAW_OSM_DIR, "gis_osm_places_free_1.shp")
    if not os.path.exists(shp_path):
        print(f"Places shapefile not found at: {shp_path}", flush=True)
        return

    print("\n--- Processing Settlements / Populated Places ---", flush=True)
    t0 = time.time()
    ml_geom, ml_prep, ml_bounds = masks["Meghalaya"]
    mz_geom, mz_prep, mz_bounds = masks["Mizoram"]

    sf = shapefile.Reader(shp_path)
    total_recs = len(sf)
    print(f"Total place features in Northeast extract: {total_recs:,}", flush=True)

    ml_places = []
    mz_places = []
    csv_rows = []

    for shape_rec in sf.iterShapeRecords():
        shp = shape_rec.shape
        rec = shape_rec.record.as_dict()
        pt_x, pt_y = shp.points[0]
        pt = Point(pt_x, pt_y)

        state = None
        if (ml_bounds[0] <= pt_x <= ml_bounds[2] and ml_bounds[1] <= pt_y <= ml_bounds[3]) and ml_prep.contains(pt):
            state = "Meghalaya"
        elif (mz_bounds[0] <= pt_x <= mz_bounds[2] and mz_bounds[1] <= pt_y <= mz_bounds[3]) and mz_prep.contains(pt):
            state = "Mizoram"

        if not state:
            continue

        props = {
            "osm_id": str(rec.get("osm_id", "")),
            "name": rec.get("name") or "Unnamed Settlement",
            "fclass": rec.get("fclass", ""),
            "population": rec.get("population", 0),
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
            ml_places.append(feat)
        else:
            mz_places.append(feat)
            
        csv_rows.append(props)

    print(f"Extracted Settlements in {time.time() - t0:.1f}s:", flush=True)
    print(f"  Meghalaya Settlements: {len(ml_places):,}", flush=True)
    print(f"  Mizoram Settlements:   {len(mz_places):,}", flush=True)
    print(f"  Total Phase 1:         {len(ml_places) + len(mz_places):,}", flush=True)

    with open(os.path.join(SETTLE_DIR, "Meghalaya_settlements.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Meghalaya_Settlements", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": ml_places}, f, indent=2)
    with open(os.path.join(SETTLE_DIR, "Mizoram_settlements.geojson"), "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "name": "Mizoram_Settlements", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": mz_places}, f, indent=2)

    combined_places = {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Phase1_Settlements",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": ml_places + mz_places
    }
    with open(os.path.join(SETTLE_DIR, "NER_SAFE_Phase1_settlements.geojson"), "w", encoding="utf-8") as f:
        json.dump(combined_places, f, indent=2)

    csv_path = os.path.join(SETTLE_DIR, "NER_SAFE_Phase1_settlements.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["osm_id", "name", "fclass", "population", "state", "longitude", "latitude"])
        writer.writeheader()
        for r in sorted(csv_rows, key=lambda x: (x["state"], x["fclass"], x["name"])):
            writer.writerow(r)
    print(f"Settlements CSV saved to: {csv_path}", flush=True)

def process_buildings(masks):
    shp_path = os.path.join(RAW_OSM_DIR, "gis_osm_buildings_a_free_1.shp")
    if not os.path.exists(shp_path):
        print(f"Buildings shapefile not found at: {shp_path}", flush=True)
        return

    print("\n--- Processing Buildings / Built-Up Footprints ---", flush=True)
    t0 = time.time()
    ml_geom, ml_prep, ml_bounds = masks["Meghalaya"]
    mz_geom, mz_prep, mz_bounds = masks["Mizoram"]

    sf = shapefile.Reader(shp_path)
    ml_bldgs = []
    mz_bldgs = []

    # Process Meghalaya buildings
    print("Extracting Meghalaya buildings with spatial bbox...", flush=True)
    for shape_rec in sf.iterShapeRecords(bbox=ml_bounds):
        try:
            shp = shape_rec.shape
            if not shp.points:
                continue
            bbox = shp.bbox
            c_x = (bbox[0] + bbox[2]) * 0.5
            c_y = (bbox[1] + bbox[3]) * 0.5
            pt = Point(c_x, c_y)
            if not ml_prep.contains(pt):
                continue

            rec = shape_rec.record.as_dict()
            geom = shape(shp)
            if geom.is_empty:
                continue

            area_sqm = round(geom.area * 111320 * 111320, 1)
            feat = {
                "type": "Feature",
                "properties": {
                    "osm_id": str(rec.get("osm_id", "")),
                    "name": rec.get("name") or "Building",
                    "type": rec.get("type", "building"),
                    "state": "Meghalaya",
                    "area_sqm": area_sqm,
                    "centroid_lon": round(c_x, 6),
                    "centroid_lat": round(c_y, 6)
                },
                "geometry": mapping(geom)
            }
            ml_bldgs.append(feat)
        except Exception:
            continue

    # Process Mizoram buildings
    print(f"Meghalaya buildings extracted: {len(ml_bldgs):,}. Extracting Mizoram buildings...", flush=True)
    for shape_rec in sf.iterShapeRecords(bbox=mz_bounds):
        try:
            shp = shape_rec.shape
            if not shp.points:
                continue
            bbox = shp.bbox
            c_x = (bbox[0] + bbox[2]) * 0.5
            c_y = (bbox[1] + bbox[3]) * 0.5
            pt = Point(c_x, c_y)
            if not mz_prep.contains(pt):
                continue

            rec = shape_rec.record.as_dict()
            geom = shape(shp)
            if geom.is_empty:
                continue

            area_sqm = round(geom.area * 111320 * 111320, 1)
            feat = {
                "type": "Feature",
                "properties": {
                    "osm_id": str(rec.get("osm_id", "")),
                    "name": rec.get("name") or "Building",
                    "type": rec.get("type", "building"),
                    "state": "Mizoram",
                    "area_sqm": area_sqm,
                    "centroid_lon": round(c_x, 6),
                    "centroid_lat": round(c_y, 6)
                },
                "geometry": mapping(geom)
            }
            mz_bldgs.append(feat)
        except Exception:
            continue

    print(f"Extracted Buildings in {time.time() - t0:.1f}s:", flush=True)
    print(f"  Meghalaya Buildings: {len(ml_bldgs):,}", flush=True)
    print(f"  Mizoram Buildings:   {len(mz_bldgs):,}", flush=True)
    print(f"  Total Phase 1:       {len(ml_bldgs) + len(mz_bldgs):,}", flush=True)

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

def run_pipeline():
    masks = load_state_masks()
    process_roads(masks)
    process_settlements(masks)
    process_buildings(masks)
    process_transport(masks)
    print("\n=======================================================", flush=True)
    print("All OSM exposure layers extracted and saved successfully!", flush=True)
    print("=======================================================", flush=True)

if __name__ == "__main__":
    run_pipeline()
