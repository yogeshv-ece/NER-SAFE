import os
import json
import rasterio

SENTINEL_RAW = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SENTINEL\raw"

scenes = sorted(os.listdir(SENTINEL_RAW))
print(f"Total Sentinel-2 scene directories found: {len(scenes)}")

audit_data = []

REQUIRED_BANDS = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]

for scene in scenes:
    s_dir = os.path.join(SENTINEL_RAW, scene)
    if not os.path.isdir(s_dir):
        continue
    
    files = os.listdir(s_dir)
    meta_file = os.path.join(s_dir, "metadata.json")
    meta = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception as e:
            print(f"Error reading metadata for {scene}: {e}")
            
    props = meta.get("properties", {})
    tile_id = props.get("s2:mgrs_tile", "UNKNOWN")
    acq_date = props.get("datetime", props.get("date", "UNKNOWN"))[:10]
    cloud_cover = props.get("eo:cloud_cover", None)
    processing_level = props.get("s2:processing_baseline", "Level-2A")
    epsg = props.get("proj:epsg", None)

    # Check bands
    band_status = {}
    for b in REQUIRED_BANDS:
        # Check files matching band name
        matching = [f for f in files if f.startswith(b) or (b == "SCL" and "SCL" in f)]
        valid_file = None
        for mf in matching:
            if mf.endswith(".tif") and not mf.endswith(".tmp"):
                f_path = os.path.join(s_dir, mf)
                f_size = os.path.getsize(f_path)
                if f_size > 10000:
                    # Test opening with rasterio
                    try:
                        with rasterio.open(f_path) as r:
                            valid_file = {
                                "filename": mf,
                                "size_bytes": f_size,
                                "width": r.width,
                                "height": r.height,
                                "crs": str(r.crs),
                                "res": r.res
                            }
                    except Exception as e:
                        valid_file = {"filename": mf, "error": str(e), "size_bytes": f_size}
        band_status[b] = valid_file

    has_optical = any(band_status[b] is not None and "error" not in band_status[b] for b in ["B02", "B03", "B04", "B08", "B11", "B12"])
    has_scl = band_status["SCL"] is not None and "error" not in band_status["SCL"]

    audit_data.append({
        "product_id": scene,
        "tile_id": tile_id,
        "acq_date": acq_date,
        "cloud_cover": cloud_cover,
        "processing_level": processing_level,
        "epsg": epsg,
        "all_files": files,
        "band_status": band_status,
        "category": "OPTICAL_PRESENT" if has_optical else "SCL_ONLY"
    })

print("\n" + "="*80)
print("SENTINEL-2 EXISTING DATASET DETAILED AUDIT RESULTS")
print("="*80)
scl_only_count = 0
optical_count = 0

for item in audit_data:
    avail = [b for b, st in item["band_status"].items() if st is not None and "error" not in st]
    print(f"\nProduct : {item['product_id']}")
    print(f"Tile    : {item['tile_id']} | Date: {item['acq_date']} | Cloud: {item['cloud_cover']}% | EPSG: {item['epsg']}")
    print(f"Status  : {item['category']} | Available valid bands: {avail}")
    for b in REQUIRED_BANDS:
        st = item["band_status"][b]
        if st is not None:
            if "error" in st:
                print(f"   {b:4s}: CORRUPTED/ERROR ({st['filename']}) - {st['error']}")
            else:
                print(f"   {b:4s}: VALID ({st['filename']}, {st['size_bytes']/(1024*1024):.2f} MB, {st['width']}x{st['height']}, res={st['res']})")
        else:
            # Check if there is a .tmp file
            tmp_files = [f for f in item["all_files"] if (f.startswith(b) or (b == "SCL" and "SCL" in f)) and f.endswith(".tmp")]
            if tmp_files:
                print(f"   {b:4s}: INCOMPLETE (.tmp file exists: {tmp_files[0]})")
            else:
                print(f"   {b:4s}: MISSING")
    if item['category'] == 'SCL_ONLY':
        scl_only_count += 1
    else:
        optical_count += 1

print("\n" + "="*80)
print(f"SUMMARY: Total Scenes={len(audit_data)} | Optical Present={optical_count} | SCL-Only={scl_only_count}")
print("="*80)

with open("sentinel2_audit_summary.json", "w") as f:
    json.dump(audit_data, f, indent=2)
print("Saved audit details to sentinel2_audit_summary.json")
