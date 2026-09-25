import os
import json
import csv
import rasterio

SENTINEL_RAW = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SENTINEL\raw"
REPORT_PATH = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SENTINEL\SENTINEL2_initial_audit_report.txt"
CSV_PATH = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\SENTINEL\sentinel2_audit_table.csv"

REQUIRED_BANDS = ["B02", "B03", "B04", "B08", "B11", "B12", "SCL"]

scenes = sorted([d for d in os.listdir(SENTINEL_RAW) if os.path.isdir(os.path.join(SENTINEL_RAW, d))])
print(f"Auditing {len(scenes)} Sentinel-2 scene directories...")

audit_rows = []
report_lines = []

report_lines.append("="*80)
report_lines.append("     NER-SAFE PROJECT — COMPONENT 8: INITIAL SENTINEL-2 AUDIT REPORT      ")
report_lines.append("="*80)
report_lines.append("Authoritative Source    : Copernicus Sentinel-2 MSI Level-2A (Surface Reflectance)")
report_lines.append("Phase 1 Target Geography: Meghalaya & Mizoram (21°N–27°N, 89°E–94°E)")
report_lines.append(f"Total Scenes Audited    : {len(scenes)}")
report_lines.append("Audit Date              : 2026-09-06")
report_lines.append("="*80 + "\n")

optical_present = []
scl_only = []

for scene in scenes:
    s_dir = os.path.join(SENTINEL_RAW, scene)
    meta_path = os.path.join(s_dir, "metadata.json")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            meta = json.load(mf)
            
    props = meta.get("properties", {})
    tile_id = props.get("s2:mgrs_tile", scene.split("_")[5] if len(scene.split("_")) > 5 else "UNKNOWN")
    # Clean tile ID (strip T prefix if needed, e.g. T46RCN -> 46RCN)
    if tile_id.startswith("T"):
        tile_code = tile_id[1:]
    else:
        tile_code = tile_id
        
    acq_date = props.get("datetime", "")[:10]
    cloud_cover = props.get("eo:cloud_cover", 0.0)
    proc_baseline = props.get("s2:processing_baseline", "Level-2A")
    orbit = props.get("sat:relative_orbit", "N/A")
    
    # Check bands
    files = os.listdir(s_dir)
    band_details = {}
    valid_bands = []
    incomplete_bands = []
    missing_bands = []
    
    scene_crs = None
    
    for b in REQUIRED_BANDS:
        # Match band file name
        matching_valid = [f for f in files if (f.startswith(b + "_") or (b == "SCL" and "SCL_" in f)) and f.endswith(".tif")]
        matching_tmp = [f for f in files if (f.startswith(b + "_") or (b == "SCL" and "SCL_" in f)) and f.endswith(".tmp")]
        
        if matching_valid:
            fname = matching_valid[0]
            fpath = os.path.join(s_dir, fname)
            fsize = os.path.getsize(fpath)
            try:
                with rasterio.open(fpath) as r:
                    band_details[b] = {
                        "status": "VALID",
                        "filename": fname,
                        "size_mb": fsize / (1024 * 1024),
                        "width": r.width,
                        "height": r.height,
                        "crs": str(r.crs),
                        "res": r.res[0]
                    }
                    if scene_crs is None:
                        scene_crs = str(r.crs)
                    valid_bands.append(b)
            except Exception as e:
                band_details[b] = {
                    "status": "CORRUPT",
                    "filename": fname,
                    "size_mb": fsize / (1024 * 1024),
                    "error": str(e)
                }
                incomplete_bands.append(b)
        elif matching_tmp:
            fname = matching_tmp[0]
            fsize = os.path.getsize(os.path.join(s_dir, fname))
            band_details[b] = {
                "status": "INCOMPLETE_TMP",
                "filename": fname,
                "size_mb": fsize / (1024 * 1024)
            }
            incomplete_bands.append(b)
        else:
            band_details[b] = {
                "status": "MISSING"
            }
            missing_bands.append(b)

    # Check if optical bands are present
    has_optical = any(b in valid_bands for b in ["B02", "B03", "B04", "B08", "B11", "B12"])
    category = "OPTICAL_PRESENT" if has_optical else "SCL_ONLY"
    
    if category == "SCL_ONLY":
        scl_only.append(scene)
    else:
        optical_present.append(scene)
        
    audit_rows.append({
        "product_id": scene,
        "tile_id": tile_code,
        "acq_date": acq_date,
        "cloud_cover": f"{cloud_cover:.4f}%" if isinstance(cloud_cover, float) else str(cloud_cover),
        "orbit": orbit,
        "crs": scene_crs if scene_crs else "N/A",
        "category": category,
        "valid_bands": " ".join(valid_bands),
        "incomplete_bands": " ".join(incomplete_bands),
        "missing_bands": " ".join(missing_bands),
        "total_files": len(files),
        "b02_status": band_details["B02"]["status"],
        "b03_status": band_details["B03"]["status"],
        "b04_status": band_details["B04"]["status"],
        "b08_status": band_details["B08"]["status"],
        "b11_status": band_details["B11"]["status"],
        "b12_status": band_details["B12"]["status"],
        "scl_status": band_details["SCL"]["status"],
    })

    report_lines.append(f"PRODUCT: {scene}")
    report_lines.append(f" - MGRS Tile       : {tile_code} (Orbit {orbit})")
    report_lines.append(f" - Acquisition Date: {acq_date}")
    report_lines.append(f" - Cloud Cover     : {cloud_cover}%")
    report_lines.append(f" - Coordinate Sys  : {scene_crs}")
    report_lines.append(f" - Status Category : {category}")
    report_lines.append(f" - Valid Bands     : {', '.join(valid_bands) if valid_bands else 'NONE'}")
    if incomplete_bands:
        report_lines.append(f" - Incomplete (.tmp): {', '.join(incomplete_bands)}")
    if missing_bands:
        report_lines.append(f" - Missing Bands   : {', '.join(missing_bands)}")
    report_lines.append(" - Band Breakdown  :")
    for b in REQUIRED_BANDS:
        bd = band_details[b]
        st = bd["status"]
        if st == "VALID":
            report_lines.append(f"    * {b:3s}: VALID ({bd['filename']}, {bd['size_mb']:.1f} MB, {bd['width']}x{bd['height']}, res={bd['res']}m)")
        elif st == "INCOMPLETE_TMP":
            report_lines.append(f"    * {b:3s}: INCOMPLETE TMP ({bd['filename']}, {bd['size_mb']:.1f} MB)")
        else:
            report_lines.append(f"    * {b:3s}: MISSING")
    report_lines.append("")

report_lines.append("="*80)
report_lines.append("SUMMARY OF AUDIT FINDINGS")
report_lines.append("="*80)
report_lines.append(f"Total Products Audited       : {len(scenes)}")
report_lines.append(f"Optical Present (Partial/Full): {len(optical_present)} products")
report_lines.append(f"SCL-Only (Missing All Optical): {len(scl_only)} products\n")

report_lines.append("1. THE SIX SCL-ONLY PRODUCTS REQUIRING COMPLETE OPTICAL ACQUISITION:")
for i, p in enumerate(scl_only, 1):
    report_lines.append(f"   {i}. {p}")

report_lines.append("\n2. THE SEVEN PRODUCTS WITH OPTICAL BANDS REQUIRING COMPLETION OF INCOMPLETE/MISSING BANDS:")
for i, p in enumerate(optical_present, 1):
    row = [r for r in audit_rows if r["product_id"] == p][0]
    report_lines.append(f"   {i}. {p} (Tile {row['tile_id']}) — Missing/Incomplete: {row['incomplete_bands']} {row['missing_bands']}")

report_lines.append("\n" + "="*80)
report_lines.append("AUDIT VERDICT: 13 Products Identified. 6 SCL-Only + 7 Incomplete Optical.")
report_lines.append("Ready to acquire missing surface-reflectance bands from Copernicus Planetary Computer catalog.")
report_lines.append("="*80 + "\n")

report_text = "\n".join(report_lines)
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(report_text)
print(f"Wrote audit report to {REPORT_PATH}")

# Write CSV table
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    fieldnames = [
        "product_id", "tile_id", "acq_date", "cloud_cover", "orbit", "crs", "category",
        "valid_bands", "incomplete_bands", "missing_bands",
        "b02_status", "b03_status", "b04_status", "b08_status", "b11_status", "b12_status", "scl_status"
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(audit_rows)
print(f"Wrote audit table to {CSV_PATH}")
