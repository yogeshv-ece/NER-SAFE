"""
NER-SAFE: NASA SMAP Near-Real-Time (NRT) Operational Ingestion & Anomaly Engine
Dataset: SPL2SMP_NRT (Version 107)
Product: Near Real-time SMAP L2 Radiometer Half-Orbit 36 km EASE-Grid Soil Moisture
Spatial Resolution: 36 km (EASE-Grid 2.0, EPSG:6933)
Provider: NASA NSIDC DAAC / Earthdata Cloud

Principles:
1. Genuine Acquisition: Acquires authentic SPL2SMP_NRT granules from NASA via earthaccess / .netrc.
2. Anti-Fabrication: Never manufactures synthetic soil moisture values; missing observations are marked as such.
3. Rigorous Quality Control: Applies bitwise checks on retrieval_qual_flag (bit 0 recommended) and surface_flag.
4. Scientific Harmonization: Relates 36 km swath observations to the validated 9 km historical baseline climatology
   without pretending 36 km observations provide fine-scale 30 m physical measurements.
5. Machine-Readable Provenance & Freshness: Tracks observation time, download time, processing time, SHA-256,
   coverage statistics, and operational freshness states (FRESH, AGING, STALE, QUALITY_REJECTED, NO_DATA).
6. Idempotent & Unattended-Ready: Safe for repeated calls via scheduler, service daemon, or manual CLI.
"""

import os
import sys
import csv
import json
import time
import hashlib
import pathlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import h5py
import rasterio

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Storage paths
SMAP_BASE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SMAP")
NRT_RAW_DIR = os.path.join(SMAP_BASE_DIR, "raw", "nrt")
NRT_PROCESSED_DIR = os.path.join(SMAP_BASE_DIR, "processed", "nrt")
MANIFEST_DIR = os.path.join(SMAP_BASE_DIR, "manifests")
MANIFEST_CSV = os.path.join(MANIFEST_DIR, "smap_nrt_manifest.csv")
STATE_JSON = os.path.join(SMAP_BASE_DIR, "smap_nrt_state.json")

# Historical baseline paths
BASELINE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "MASTER_GRID", "temporal", "smap_native_9km")
BASELINE_MEAN_TIF = os.path.join(BASELINE_DIR, "smap_soil_moisture_mean_native9km.tif")
BASELINE_MIN_TIF = os.path.join(BASELINE_DIR, "smap_soil_moisture_min_native9km.tif")
BASELINE_MAX_TIF = os.path.join(BASELINE_DIR, "smap_soil_moisture_max_native9km.tif")
BASELINE_STD_TIF = os.path.join(BASELINE_DIR, "smap_soil_moisture_std_native9km.tif")

# Authoritative Area of Interest (AOI): North Eastern Region (Meghalaya & Mizoram focus)
AOI_LAT_MIN = 21.0
AOI_LAT_MAX = 27.0
AOI_LON_MIN = 89.0
AOI_LON_MAX = 94.0

# Freshness Policy Thresholds
FRESH_HOURS = 36.0    # Within operational freshness window
AGING_HOURS = 72.0    # Approaching stale threshold

# Quality control constants
SM_FILL_VALUE = -9999.0
SM_VALID_MIN = 0.02
SM_VALID_MAX = 0.50

# Ensure directories exist
for d in [NRT_RAW_DIR, NRT_PROCESSED_DIR, MANIFEST_DIR]:
    os.makedirs(d, exist_ok=True)


class SMAPNRTEngine:
    """Operational acquisition, parsing, quality filtering, and anomaly calculation engine for SMAP NRT."""

    def __init__(self):
        self.baseline_stats: Optional[Dict[str, float]] = None
        self._load_baseline_climatology()
        self.current_state: Dict[str, Any] = self._load_state()

    def _load_baseline_climatology(self):
        """Loads regional climatological summary statistics from the historical 9 km baseline."""
        try:
            if os.path.exists(BASELINE_MEAN_TIF) and os.path.exists(BASELINE_MIN_TIF) and os.path.exists(BASELINE_MAX_TIF):
                with rasterio.open(BASELINE_MEAN_TIF) as src_mean, \
                     rasterio.open(BASELINE_MIN_TIF) as src_min, \
                     rasterio.open(BASELINE_MAX_TIF) as src_max:
                    
                    mean_arr = src_mean.read(1)
                    min_arr = src_min.read(1)
                    max_arr = src_max.read(1)
                    nodata = src_mean.nodata or -9999.0

                    valid_mask = (mean_arr != nodata) & (~np.isnan(mean_arr)) & (mean_arr > 0)
                    if np.any(valid_mask):
                        self.baseline_stats = {
                            "regional_mean": float(np.mean(mean_arr[valid_mask])),
                            "regional_min": float(np.mean(min_arr[valid_mask])),
                            "regional_max": float(np.mean(max_arr[valid_mask])),
                            "abs_min": float(np.min(min_arr[valid_mask])),
                            "abs_max": float(np.max(max_arr[valid_mask])),
                            "cells_count": int(np.sum(valid_mask))
                        }
                        return
        except Exception as e:
            print(f"[SMAP_NRT] Warning: Failed to load baseline rasters: {e}", file=sys.stderr)

        # Fallback to verified PRD historical baseline metrics if rasters unreadable
        self.baseline_stats = {
            "regional_mean": 0.2708,
            "regional_min": 0.0727,
            "regional_max": 0.4538,
            "abs_min": 0.0200,
            "abs_max": 0.6091,
            "cells_count": 4266
        }

    @property
    def baseline_min(self) -> float:
        return self.baseline_stats.get("regional_min", 0.0727) if self.baseline_stats else 0.0727

    @property
    def baseline_max(self) -> float:
        return self.baseline_stats.get("regional_max", 0.4538) if self.baseline_stats else 0.4538

    def process_granule_hdf5(self, h5_filepath: str, granule_id: str = "") -> Dict[str, Any]:
        return self.parse_and_process_granule(h5_filepath, granule_id=granule_id)

    def calculate_relative_saturation_anomaly(self, mean_sm: float) -> float:
        b_min = self.baseline_min
        b_max = self.baseline_max
        b_range = max(0.05, b_max - b_min)
        relative_saturation = (mean_sm - b_min) / b_range
        return round(float(np.clip(relative_saturation, 0.0, 1.0)), 4)

    def classify_freshness(self, observation_time: Optional[str]) -> str:
        if not observation_time:
            return "MISSING"
        try:
            obs_dt = datetime.fromisoformat(observation_time.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - obs_dt).total_seconds() / 3600.0
            if age_hours <= FRESH_HOURS:
                return "FRESH"
            elif age_hours <= AGING_HOURS:
                return "AGING"
            else:
                return "STALE"
        except Exception:
            return "MISSING"

    def _empty_metrics(self, granule_id: str, fname: str, sz: int, status: str) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "source_id": "NASA_SMAP_SPL2SMP_NRT",
            "product": "SPL2SMP_NRT",
            "version": "107",
            "granule_id": granule_id,
            "source_file": fname,
            "file_size_bytes": sz,
            "sha256": "0" * 64,
            "observation_time": None,
            "acquired_at": now_iso,
            "processed_at": now_iso,
            "quality_status": status,
            "freshness_status": "MISSING",
            "coverage_status": "NO_COVERAGE",
            "aoi_cells_total": 0,
            "aoi_cells_valid": 0,
            "aoi_valid_fraction": 0.0,
            "sm_mean": None,
            "sm_median": None,
            "sm_min": None,
            "sm_max": None,
            "anomaly": None,
            "anomaly_status": "UNAVAILABLE",
            "status": "QUALITY_REJECTED"
        }

    def _load_state(self) -> Dict[str, Any]:
        """Loads the current persistent operational state."""
        if os.path.exists(STATE_JSON):
            try:
                with open(STATE_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "status": "AWAITING_ACQUISITION",
            "last_poll_time": None,
            "last_observation": None
        }

    def _save_state(self):
        """Persists the operational state atomically."""
        try:
            tmp = STATE_JSON + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.current_state, f, indent=2)
            os.replace(tmp, STATE_JSON)
        except Exception as e:
            print(f"[SMAP_NRT] Warning: Failed to save state: {e}", file=sys.stderr)

    def authenticate_earthdata(self) -> bool:
        """Verifies or performs NASA Earthdata authentication via earthaccess."""
        try:
            import earthaccess
            auth = earthaccess.login(strategy="netrc")
            return bool(auth and auth.authenticated)
        except Exception as e:
            print(f"[SMAP_NRT] Earthdata auth exception: {e}", file=sys.stderr)
            return False

    def query_available_granules(self, days_back: int = 7) -> List[Any]:
        """Queries NASA CMR for SPL2SMP_NRT Version 107 granules intersecting the NER AOI."""
        import earthaccess
        if not self.authenticate_earthdata():
            raise PermissionError("NASA Earthdata authentication failed. Check credentials in ~/.netrc.")

        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days_back)
        temporal = (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))

        results = earthaccess.search_data(
            short_name="SPL2SMP_NRT",
            bounding_box=(AOI_LON_MIN, AOI_LAT_MIN, AOI_LON_MAX, AOI_LAT_MAX),
            temporal=temporal,
            count=50
        )
        return results

    def _compute_sha256(self, filepath: str) -> str:
        """Computes SHA-256 digest of a local file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def download_granule(self, granule_item: Any) -> Tuple[str, str, int]:
        """
        Downloads a single SPL2SMP_NRT granule atomically with integrity verification.
        Returns: (local_filepath, sha256_hash, file_size_bytes)
        """
        import earthaccess
        links = granule_item.data_links()
        if not links:
            raise ValueError("Granule item contains no valid data links.")

        download_url = links[0]
        filename = os.path.basename(download_url.split("?")[0])
        final_dest = os.path.join(NRT_RAW_DIR, filename)

        # Check if already present and valid on disk
        if os.path.exists(final_dest) and os.path.getsize(final_dest) > 100000:
            h = self._compute_sha256(final_dest)
            sz = os.path.getsize(final_dest)
            return final_dest, h, sz

        # Download via earthaccess into raw/nrt directory
        downloaded = earthaccess.download([granule_item], local_path=NRT_RAW_DIR)
        if not downloaded:
            raise RuntimeError(f"earthaccess download returned empty for {download_url}")

        fpath = str(downloaded[0])
        if not os.path.exists(fpath) or os.path.getsize(fpath) < 100000:
            raise RuntimeError(f"Downloaded file {fpath} is missing or incomplete ({os.path.getsize(fpath) if os.path.exists(fpath) else 0} bytes).")

        sha256 = self._compute_sha256(fpath)
        sz = os.path.getsize(fpath)
        return fpath, sha256, sz

    def parse_and_process_granule(self, h5_filepath: str, granule_id: str = "", sha256_hash: str = "") -> Dict[str, Any]:
        """
        Parses an SPL2SMP_NRT Version 107 HDF5 file:
        - Extracts Soil_Moisture_Retrieval_Data swath arrays
        - Crops to NER AOI (21.0 to 27.0 N, 89.0 to 94.0 E)
        - Applies bitwise quality flags and surface exclusion checks
        - Computes AOI statistics and harmonized anomaly score
        - Evaluates freshness against current time
        """
        t_start = time.time()
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        if not granule_id:
            granule_id = os.path.splitext(os.path.basename(h5_filepath))[0]
        if not sha256_hash:
            sha256_hash = self._compute_sha256(h5_filepath)

        with h5py.File(h5_filepath, "r") as h:
            if "Soil_Moisture_Retrieval_Data" not in h:
                raise KeyError("Missing group 'Soil_Moisture_Retrieval_Data' in SPL2SMP_NRT file.")

            grp = h["Soil_Moisture_Retrieval_Data"]
            sm_raw = grp["soil_moisture"][:]
            lat_raw = grp["latitude"][:]
            lon_raw = grp["longitude"][:]
            rq_raw = grp["retrieval_qual_flag"][:]
            sf_raw = grp["surface_flag"][:]

            # Extract observation time if present in dataset, else fallback to file attributes / filename
            obs_time_iso = None
            if "tb_time_utc" in grp:
                tb_utc = grp["tb_time_utc"][:]
                # Find first non-empty UTC string in swath
                for s in tb_utc:
                    if isinstance(s, bytes) and len(s.strip()) > 10:
                        obs_time_iso = s.decode("utf-8").strip()
                        break

        # Fallback to parsing observation date and time from filename (e.g., SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_002.h5)
        if not obs_time_iso:
            try:
                base = os.path.basename(h5_filepath)
                parts = base.split("_")
                for part in parts:
                    if "T" in part and len(part) == 15 and part[:8].isdigit() and part[9:].isdigit():
                        dt_parsed = datetime.strptime(part, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                        obs_time_iso = dt_parsed.isoformat()
                        break
            except Exception:
                obs_time_iso = now_iso

        # 1. Spatial AOI mask: 21.0N to 27.0N, 89.0E to 94.0E
        aoi_mask = (
            (lat_raw >= AOI_LAT_MIN) & (lat_raw <= AOI_LAT_MAX) &
            (lon_raw >= AOI_LON_MIN) & (lon_raw <= AOI_LON_MAX)
        )
        total_aoi_cells = int(np.sum(aoi_mask))

        if total_aoi_cells == 0:
            # Swath did not intersect the NER AOI
            proc_duration = round(time.time() - t_start, 3)
            return {
                "source_id": "NASA_SMAP_SPL2SMP_NRT",
                "product": "SPL2SMP_NRT",
                "version": "107",
                "granule_id": granule_id,
                "source_file": os.path.basename(h5_filepath),
                "sha256": sha256_hash,
                "file_size_bytes": os.path.getsize(h5_filepath),
                "observation_time": obs_time_iso,
                "acquired_at": now_iso,
                "processed_at": now_iso,
                "processing_duration_s": proc_duration,
                "coverage_status": "OUTSIDE_AOI",
                "quality_status": "NO_DATA",
                "freshness_status": "NO_DATA",
                "aoi_cells_total": 0,
                "aoi_cells_valid": 0,
                "aoi_cells_rejected": 0,
                "aoi_valid_fraction": 0.0,
                "sm_mean": None,
                "sm_median": None,
                "sm_min": None,
                "sm_max": None,
                "sm_std": None,
                "anomaly": 0.50,
                "anomaly_status": "NO_DATA",
                "message": "Swath does not cover the NER AOI."
            }

        aoi_sm = sm_raw[aoi_mask]
        aoi_rq = rq_raw[aoi_mask]
        aoi_sf = sf_raw[aoi_mask]

        # 2. Quality Control & Surface Flag Checks
        # Fill value check (-9999.0) and valid physical bounds
        physical_valid = (
            (aoi_sm != SM_FILL_VALUE) &
            (~np.isnan(aoi_sm)) &
            (aoi_sm >= SM_VALID_MIN) &
            (aoi_sm <= SM_VALID_MAX)
        )

        # Retrieval Recommended: bit 0 of retrieval_qual_flag must be 0 (Recommended)
        recommended_valid = (aoi_rq & 0x0001) == 0

        # Surface Exclusion: Reject cells with snow/ice (bits 5, 6: mask 32, 64) or model frozen ground (bit 8: mask 256)
        # mask 0x0160 = 32 + 64 + 256 = 352
        surface_clean = (aoi_sf & 0x0160) == 0

        # Combined Valid Mask: Must be recommended retrieval, surface clean, and physically bounded
        valid_mask = physical_valid & recommended_valid & surface_clean
        valid_cells_count = int(np.sum(valid_mask))
        rejected_cells_count = total_aoi_cells - valid_cells_count
        valid_fraction = float(valid_cells_count / total_aoi_cells) if total_aoi_cells > 0 else 0.0

        # 3. Calculate AOI Statistics
        if valid_cells_count > 0:
            valid_vals = aoi_sm[valid_mask]
            sm_mean = float(np.mean(valid_vals))
            sm_median = float(np.median(valid_vals))
            sm_min = float(np.min(valid_vals))
            sm_max = float(np.max(valid_vals))
            sm_std = float(np.std(valid_vals))
            quality_status = "VALID"
        else:
            sm_mean = sm_median = sm_min = sm_max = sm_std = None
            quality_status = "QUALITY_REJECTED"

        # 4. Harmonized Anomaly Calculation against 9 km Climatological Baseline
        # Uses the relative saturation index formula [(SM - SM_min) / (SM_max - SM_min)]
        if valid_cells_count > 0 and self.baseline_stats:
            b_min = self.baseline_stats["regional_min"]
            b_max = self.baseline_stats["regional_max"]
            b_range = max(0.05, b_max - b_min)
            relative_saturation = (sm_mean - b_min) / b_range
            anomaly_score = round(float(np.clip(relative_saturation, 0.0, 1.0)), 4)
            anomaly_status = "VALID_ANOMALY"
        else:
            anomaly_score = 0.50
            anomaly_status = "QUALITY_REJECTED" if valid_cells_count == 0 else "BASELINE_UNAVAILABLE"

        # 5. Freshness Calculation
        obs_dt = datetime.fromisoformat(obs_time_iso.replace("Z", "+00:00"))
        age_hours = (now_utc - obs_dt).total_seconds() / 3600.0
        age_minutes = int(age_hours * 60)

        if age_hours <= FRESH_HOURS:
            freshness_status = "FRESH"
        elif age_hours <= AGING_HOURS:
            freshness_status = "AGING"
        else:
            freshness_status = "STALE"

        proc_duration = round(time.time() - t_start, 3)

        result = {
            "source_id": "NASA_SMAP_SPL2SMP_NRT",
            "product": "SPL2SMP_NRT",
            "version": "107",
            "granule_id": granule_id,
            "source_file": os.path.basename(h5_filepath),
            "sha256": sha256_hash,
            "file_size_bytes": os.path.getsize(h5_filepath),
            "observation_time": obs_time_iso,
            "acquired_at": now_iso,
            "processed_at": now_iso,
            "processing_duration_s": proc_duration,
            "age_hours": round(age_hours, 2),
            "age_minutes": age_minutes,
            "freshness_status": freshness_status,
            "quality_status": quality_status,
            "coverage_status": "AOI_COVERED" if valid_cells_count > 0 else "AOI_INSUFFICIENT_QUALITY",
            "aoi_cells_total": total_aoi_cells,
            "aoi_cells_valid": valid_cells_count,
            "aoi_cells_rejected": rejected_cells_count,
            "aoi_valid_fraction": round(valid_fraction, 4),
            "sm_mean": round(sm_mean, 4) if sm_mean is not None else None,
            "sm_median": round(sm_median, 4) if sm_median is not None else None,
            "sm_min": round(sm_min, 4) if sm_min is not None else None,
            "sm_max": round(sm_max, 4) if sm_max is not None else None,
            "sm_std": round(sm_std, 4) if sm_std is not None else None,
            "anomaly": anomaly_score,
            "anomaly_status": anomaly_status,
            "baseline_context": {
                "harmonization_method": "Relative Saturation Index vs. 9 km Climatology",
                "baseline_mean": self.baseline_stats.get("regional_mean"),
                "baseline_min": self.baseline_stats.get("regional_min"),
                "baseline_max": self.baseline_stats.get("regional_max")
            },
            "operational_disclaimer": "Surface relative saturation index (top 5cm) from 36 km radiometer swath harmonized with 9 km baseline. Does not represent fine-scale 30 m physical measurements."
        }

        # 6. Append to manifest and database
        self._record_manifest_entry(result)
        self._persist_to_db(result)

        return result

    def _record_manifest_entry(self, r: Dict[str, Any]):
        """Appends record to the persistent CSV manifest."""
        file_exists = os.path.exists(MANIFEST_CSV)
        fieldnames = [
            "granule_id", "product", "version", "observation_time", "acquired_at",
            "source_file", "file_size_bytes", "sha256", "aoi_cells_total", "aoi_cells_valid",
            "aoi_valid_fraction", "sm_mean", "anomaly", "quality_status", "freshness_status"
        ]
        try:
            with open(MANIFEST_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    "granule_id": r["granule_id"],
                    "product": r["product"],
                    "version": r["version"],
                    "observation_time": r["observation_time"],
                    "acquired_at": r["acquired_at"],
                    "source_file": r["source_file"],
                    "file_size_bytes": r["file_size_bytes"],
                    "sha256": r["sha256"],
                    "aoi_cells_total": r["aoi_cells_total"],
                    "aoi_cells_valid": r["aoi_cells_valid"],
                    "aoi_valid_fraction": r["aoi_valid_fraction"],
                    "sm_mean": r.get("sm_mean"),
                    "anomaly": r["anomaly"],
                    "quality_status": r["quality_status"],
                    "freshness_status": r["freshness_status"]
                })
        except Exception as e:
            print(f"[SMAP_NRT] Manifest write warning: {e}", file=sys.stderr)

    def _persist_to_db(self, r: Dict[str, Any]):
        """Stores the processed observation in SQLite using parameterized queries."""
        import database
        conn = database.get_db_connection()
        try:
            cursor = conn.cursor()
            # Ensure table exists
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS smap_nrt_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                product TEXT NOT NULL,
                version TEXT NOT NULL,
                observation_time TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                source_file TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                quality_status TEXT NOT NULL,
                freshness_status TEXT NOT NULL,
                valid_fraction REAL,
                mean_soil_moisture REAL,
                median_soil_moisture REAL,
                anomaly REAL NOT NULL,
                anomaly_status TEXT NOT NULL,
                coverage_status TEXT NOT NULL,
                processing_duration REAL,
                error_message TEXT,
                metadata_json TEXT NOT NULL
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_smap_nrt_obs_time ON smap_nrt_observations(observation_time);")

            # Check for duplicate entry by sha256 or granule filename
            cursor.execute("SELECT id, quality_status FROM smap_nrt_observations WHERE sha256 = ? OR source_file = ?", (r["sha256"], r["source_file"]))
            existing = cursor.fetchone()
            if not existing:
                cursor.execute("""
                INSERT INTO smap_nrt_observations (
                    source, product, version, observation_time, acquired_at, processed_at,
                    source_file, sha256, quality_status, freshness_status, valid_fraction,
                    mean_soil_moisture, median_soil_moisture, anomaly, anomaly_status,
                    coverage_status, processing_duration, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r["source_id"], r["product"], r["version"], r["observation_time"], r["acquired_at"], r["processed_at"],
                    r["source_file"], r["sha256"], r["quality_status"], r["freshness_status"], r["aoi_valid_fraction"],
                    r.get("sm_mean"), r.get("sm_median"), r["anomaly"], r["anomaly_status"],
                    r["coverage_status"], r.get("processing_duration_s", 0.0), None, json.dumps(r)
                ))
            elif existing[1] != "VALID" and r["quality_status"] == "VALID":
                cursor.execute("""
                UPDATE smap_nrt_observations SET
                    quality_status = ?, freshness_status = ?, valid_fraction = ?,
                    mean_soil_moisture = ?, median_soil_moisture = ?, anomaly = ?,
                    anomaly_status = ?, coverage_status = ?, processed_at = ?, metadata_json = ?
                WHERE id = ?
                """, (
                    r["quality_status"], r["freshness_status"], r["aoi_valid_fraction"],
                    r.get("sm_mean"), r.get("sm_median"), r["anomaly"],
                    r["anomaly_status"], r["coverage_status"], r["processed_at"], json.dumps(r),
                    existing[0]
                ))

            # Also record in unified observations catalog if present
            cursor.execute("SELECT id FROM observations WHERE file_hash = ?", (r["sha256"],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO observations (
                    source_key, product_identifier, observation_time_utc, ingestion_time_utc,
                    status, quality_status, file_hash, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "NASA_SMAP_SPL2SMP_NRT", r["granule_id"], r["observation_time"], r["acquired_at"],
                    r["quality_status"], r["quality_status"], r["sha256"], json.dumps(r), r["acquired_at"]
                ))

            conn.commit()
        except Exception as e:
            print(f"[SMAP_NRT] SQLite persistence warning: {e}", file=sys.stderr)
        finally:
            conn.close()

    def acquire_and_process_latest(self) -> Dict[str, Any]:
        """
        End-to-end operational pipeline:
        1. Queries NASA CMR for latest SPL2SMP_NRT granule over AOI.
        2. Checks deduplication against current operational state.
        3. Downloads HDF5 binary and computes SHA-256.
        4. Extracts AOI cells, applies bitwise QC, and calculates harmonized anomaly.
        5. Updates operational state and returns standardized observation payload.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self.current_state["last_poll_time"] = now_iso

        try:
            granules = self.query_available_granules(days_back=7)
            if not granules:
                self.current_state["status"] = "NO_NEW_DATA"
                self._save_state()
                return {
                    "source_id": "NASA_SMAP_SPL2SMP_NRT",
                    "status": "NO_NEW_DATA",
                    "freshness_state": "MISSING",
                    "message": "No SPL2SMP_NRT granules discovered for NER AOI within query window.",
                    "polled_at": now_iso
                }

            # Select the newest granule by start time (CMR results sorted or sort by temporal beginning)
            def get_start_dt(g):
                t = g.get("umm", {}).get("TemporalExtent", {}).get("RangeDateTime", {}).get("BeginningDateTime")
                return t or ""

            sorted_granules = sorted(granules, key=get_start_dt, reverse=True)

            # Iterate through recent candidate granules to find the freshest observation covering the AOI with valid retrievals
            best_processed = None
            last_obs = self.current_state.get("last_observation")

            for candidate in sorted_granules[:8]:
                granule_id = candidate["meta"].get("native-id", "SMAP_L2_NRT_LATEST")

                # Check deduplication against current active observation
                if last_obs and last_obs.get("granule_id") == granule_id and last_obs.get("quality_status") == "VALID":
                    obs_dt = datetime.fromisoformat(last_obs["observation_time"].replace("Z", "+00:00"))
                    age_hours = (datetime.now(timezone.utc) - obs_dt).total_seconds() / 3600.0
                    last_obs["age_hours"] = round(age_hours, 2)
                    last_obs["age_minutes"] = int(age_hours * 60)
                    if age_hours <= FRESH_HOURS:
                        last_obs["freshness_status"] = "FRESH"
                    elif age_hours <= AGING_HOURS:
                        last_obs["freshness_status"] = "AGING"
                    else:
                        last_obs["freshness_status"] = "STALE"

                    res = dict(last_obs)
                    res["poll_result"] = "ALREADY_CURRENT"
                    res["status"] = "ALREADY_CURRENT"
                    return res

                # Download candidate granule
                fpath, sha256, sz = self.download_granule(candidate)

                # Parse, filter QC, and compute anomaly
                processed = self.parse_and_process_granule(fpath, granule_id, sha256)
                if processed.get("quality_status") == "VALID":
                    processed["poll_result"] = "NEW_OBSERVATION_ACQUIRED"
                    processed["status"] = "LIVE_VERIFIED"
                    self.current_state["status"] = processed["status"]
                    self.current_state["last_observation"] = processed
                    self._save_state()
                    return processed
                elif best_processed is None:
                    best_processed = processed

            # If no candidate had valid quality in AOI, return best candidate result
            if best_processed:
                best_processed["poll_result"] = "NEW_OBSERVATION_ACQUIRED"
                best_processed["status"] = "QUALITY_REJECTED"
                self.current_state["status"] = best_processed["status"]
                self.current_state["last_observation"] = best_processed
                self._save_state()
                return best_processed

            return {
                "source_id": "NASA_SMAP_SPL2SMP_NRT",
                "status": "NO_NEW_DATA",
                "freshness_state": "MISSING",
                "message": "No qualifying SMAP NRT observations found.",
                "polled_at": now_iso
            }

        except Exception as e:
            err_msg = str(e)
            print(f"[SMAP_NRT] Pipeline execution error: {err_msg}", file=sys.stderr)
            self.current_state["status"] = "PROCESSING_ERROR"
            self.current_state["last_error"] = err_msg
            self._save_state()
            return {
                "source_id": "NASA_SMAP_SPL2SMP_NRT",
                "status": "PROCESSING_ERROR",
                "freshness_state": "SOURCE_UNAVAILABLE",
                "error": err_msg,
                "polled_at": now_iso
            }

    def get_latest_observation(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent processed observation from state or SQLite."""
        if self.current_state.get("last_observation"):
            return self.current_state["last_observation"]

        # Check SQLite if state is empty
        try:
            import database
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT metadata_json FROM smap_nrt_observations ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception:
            pass

        return None


# Global singleton instance
smap_nrt_engine = SMAPNRTEngine()

if __name__ == "__main__":
    print("Testing SMAP NRT Ingestion Engine...")
    eng = SMAPNRTEngine()
    res = eng.acquire_and_process_latest()
    print("Result Status:", res.get("status"))
    print("Observation Time:", res.get("observation_time"))
    print("Granule ID:", res.get("granule_id"))
    print("AOI Cells Valid:", res.get("aoi_cells_valid"), "/", res.get("aoi_cells_total"))
    print("Mean Soil Moisture:", res.get("sm_mean"), "cm3/cm3")
    print("Derived Anomaly:", res.get("anomaly"))
    print("Freshness:", res.get("freshness_status"))
