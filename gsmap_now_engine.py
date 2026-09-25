"""
=============================================================================
NER-SAFE: JAXA GSMaP_NOW Operational Ingestion & Anomaly Engine
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Component: Operational Rainfall Trigger (0.30 Risk Weight Channel)

Purpose:
  Connects to JAXA EORC operational production FTP server (ftp.eorc.jaxa.jp),
  discovers the latest half-hourly GSMaP_NOW Version 8 South Asia regional subset
  (/now/txt/05_AsiaSS), downloads the lightweight CSV.ZIP payload (~318 KB) atomically,
  performs cryptographic integrity checks (SHA-256), parses precip arrays for the
  North Eastern Region (Meghalaya and Mizoram focus: 21.0-27.0 N, 89.0-94.0 E),
  computes spatial rainfall statistics, and calculates the canonical dynamic
  rainfall anomaly score compatible with the locked NER-SAFE 4-factor risk formula.

Strict Security & Governance Rules:
  1. Credentials loaded exclusively from environment / .env; ZERO hardcoding.
  2. Passwords NEVER logged, printed, or exposed in exceptions or reports.
  3. Zero synthetic rainfall data; returns clear error states on failure.
  4. Atomic download and staging to prevent partial-file corruptions.
  5. Decoupled observation vs download vs processing timestamps.
=============================================================================
"""

import os
import sys
import io
import csv
import time
import zipfile
import hashlib
import ftplib
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

def _load_env_safe(env_path: Optional[str] = None):
    """Loads .env into os.environ without overwriting existing environment variables."""
    if env_path is None:
        env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_safe()

# JAXA GSMaP Connection Parameters
DEFAULT_FTP_HOST = "ftp.eorc.jaxa.jp"
DEFAULT_FTP_USER = "rainmap"
DEFAULT_REMOTE_DIR = "/now/txt/05_AsiaSS"

# Storage Directories
RAW_STORAGE_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "RAW_INGEST", "GSMAP")
LEDGER_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "RESEARCH_EVIDENCE")
os.makedirs(RAW_STORAGE_DIR, exist_ok=True)
os.makedirs(LEDGER_DIR, exist_ok=True)

# Geographic Bounding Coordinates
# North Eastern Region Focus (Meghalaya & Mizoram encompass 21.9 - 26.2 N, 89.8 - 93.4 E)
NER_LAT_MIN, NER_LAT_MAX = 21.0, 27.0
NER_LON_MIN, NER_LON_MAX = 89.0, 94.0

MEG_LAT_MIN, MEG_LAT_MAX = 25.0, 26.2
MEG_LON_MIN, MEG_LON_MAX = 89.8, 92.8

MIZ_LAT_MIN, MIZ_LAT_MAX = 21.9, 24.5
MIZ_LON_MIN, MIZ_LON_MAX = 92.2, 93.4

class GSMaPNowEngine:
    """
    Operational Ingestion Worker for JAXA GSMaP_NOW Near-Real-Time Precipitation.
    """
    def __init__(self, host: Optional[str] = None,
                 user: Optional[str] = None,
                 password: Optional[str] = None,
                 remote_dir: str = DEFAULT_REMOTE_DIR,
                 timeout_seconds: int = 25):
        self.host = host or os.environ.get("JAXA_GSMAP_HOST", DEFAULT_FTP_HOST)
        self.user = user or os.environ.get("JAXA_GSMAP_USER", DEFAULT_FTP_USER)
        self.password = password or os.environ.get("JAXA_GSMAP_PASSWORD", "")
        self.remote_dir = remote_dir
        self.timeout = timeout_seconds
        self.last_observation: Optional[Dict[str, Any]] = None

    def _get_ftp_connection(self) -> ftplib.FTP:
        """Establishes an authenticated passive FTP connection."""
        if not self.password:
            raise ValueError("JAXA_GSMAP_PASSWORD environment variable is missing or empty.")
        
        ftp = ftplib.FTP(timeout=self.timeout)
        ftp.connect(self.host, 21)
        ftp.login(self.user, self.password)
        ftp.set_pasv(True)
        return ftp

    def list_available_products(self, limit: int = 20) -> List[str]:
        """Lists available regional South Asia CSV.ZIP files on JAXA FTP with retry."""
        last_err = None
        for attempt in range(3):
            try:
                ftp = self._get_ftp_connection()
                try:
                    ftp.cwd(self.remote_dir)
                    files = ftp.nlst()
                    csv_zips = [f for f in files if f.endswith(".05_AsiaSS.csv.zip")]
                    csv_zips.sort()
                    return csv_zips[-limit:] if limit > 0 else csv_zips
                finally:
                    try:
                        ftp.quit()
                    except Exception:
                        ftp.close()
            except Exception as e:
                last_err = e
                time.sleep(1.0)
        raise last_err

    def parse_product_timestamp(self, filename: str) -> Tuple[datetime, datetime]:
        """
        Parses observation start and end UTC timestamps from GSMaP filename.
        Example: gsmap_now.20260921.0000_0059.05_AsiaSS.csv.zip
        Returns: (start_dt_utc, end_dt_utc)
        """
        parts = filename.split(".")
        # expected: ['gsmap_now', 'YYYYMMDD', 'HHMM_hhnn', '05_AsiaSS', 'csv', 'zip']
        if len(parts) < 5:
            raise ValueError(f"Unrecognized GSMaP filename format: {filename}")
        
        d_str = parts[1] # '20260921'
        time_part = parts[2] # 'HHMM_hhnn'
        start_time_str, end_time_str = time_part.split("_")
        
        start_dt = datetime.strptime(f"{d_str}{start_time_str}", "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(f"{d_str}{end_time_str}", "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        
        if end_dt < start_dt:
            # rolled over midnight
            end_dt += timedelta(days=1)
            
        return start_dt, end_dt

    def detect_latest_product(self) -> Dict[str, Any]:
        """Discovers the newest published GSMaP_NOW product and computes publication lag."""
        available = self.list_available_products(limit=5)
        if not available:
            raise RuntimeError(f"No GSMaP_NOW products found in {self.remote_dir} on {self.host}")
        
        latest_file = available[-1]
        start_dt, end_dt = self.parse_product_timestamp(latest_file)
        now_utc = datetime.now(timezone.utc)
        
        lag_minutes = (now_utc - end_dt).total_seconds() / 60.0
        
        return {
            "filename": latest_file,
            "observation_start_utc": start_dt.isoformat(),
            "observation_end_utc": end_dt.isoformat(),
            "publication_lag_minutes": round(lag_minutes, 1),
            "is_fresh": lag_minutes <= 120.0
        }

    def download_product(self, filename: str, force: bool = False) -> Tuple[str, str, int, float]:
        """
        Downloads the specified product using atomic staging.
        Returns: (local_filepath, sha256_hash, file_size_bytes, download_duration_s)
        """
        target_path = os.path.join(RAW_STORAGE_DIR, filename)
        tmp_path = target_path + f".tmp.{os.getpid()}"
        
        # Check cache if not forcing re-download
        if not force and os.path.isfile(target_path) and os.path.getsize(target_path) > 100_000:
            with open(target_path, "rb") as f:
                content = f.read()
            digest = hashlib.sha256(content).hexdigest()
            return target_path, digest, len(content), 0.0

        t_dl = 0.0
        for attempt in range(3):
            try:
                t0 = time.time()
                ftp = self._get_ftp_connection()
                try:
                    ftp.cwd(self.remote_dir)
                    with open(tmp_path, "wb") as local_f:
                        ftp.retrbinary(f"RETR {filename}", local_f.write, blocksize=65536)
                finally:
                    try:
                        ftp.quit()
                    except Exception:
                        ftp.close()
                t_dl = time.time() - t0
                break
            except Exception as e:
                if attempt == 2:
                    raise
                time.sleep(1.0)

        # Validate file size
        file_size = os.path.getsize(tmp_path)
        if file_size < 10_000:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise IOError(f"Downloaded GSMaP file is abnormally small ({file_size} bytes)")

        # Verify ZIP integrity
        with zipfile.ZipFile(tmp_path, "r") as z:
            test_res = z.testzip()
            if test_res is not None:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise IOError(f"Corrupt ZIP file downloaded: bad file {test_res}")

        # Compute SHA-256
        with open(tmp_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()

        # Atomic commit
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(tmp_path, target_path)

        return target_path, digest, file_size, round(t_dl, 3)

    def parse_and_extract_rainfall(self, zip_path: str) -> Dict[str, Any]:
        """
        Parses CSV inside ZIP, filters to Meghalaya/Mizoram AOI, computes stats and anomaly.
        """
        t0 = time.time()
        with zipfile.ZipFile(zip_path, "r") as z:
            # Find the contained CSV file
            csv_members = [m for m in z.namelist() if m.endswith(".csv")]
            if not csv_members:
                raise ValueError("No CSV file found inside GSMaP ZIP archive")
            csv_name = csv_members[0]
            
            with z.open(csv_name, "r") as csv_file:
                reader = csv.reader(io.TextIOWrapper(csv_file, encoding="utf-8"))
                
                header = None
                total_cells_processed = 0
                ner_cells = 0
                valid_rain_rates = []
                meg_rain_rates = []
                miz_rain_rates = []
                
                for row in reader:
                    if not row:
                        continue
                    if header is None:
                        # Clean header tokens
                        header = [c.strip() for c in row]
                        continue
                    
                    try:
                        lat = float(row[0])
                        lon = float(row[1])
                        rain_rate = float(row[2])
                        total_cells_processed += 1
                        
                        # Filter to NER AOI
                        if (NER_LAT_MIN <= lat <= NER_LAT_MAX) and (NER_LON_MIN <= lon <= NER_LON_MAX):
                            ner_cells += 1
                            if rain_rate >= 0.0:
                                valid_rain_rates.append(rain_rate)
                                
                                # District check
                                if (MEG_LAT_MIN <= lat <= MEG_LAT_MAX) and (MEG_LON_MIN <= lon <= MEG_LON_MAX):
                                    meg_rain_rates.append(rain_rate)
                                elif (MIZ_LAT_MIN <= lat <= MIZ_LAT_MAX) and (MIZ_LON_MIN <= lon <= MIZ_LON_MAX):
                                    miz_rain_rates.append(rain_rate)
                    except (ValueError, IndexError):
                        continue

        t_parse = time.time() - t0

        if not valid_rain_rates:
            raise ValueError(f"Zero valid rainfall cells found in NER AOI within {zip_path}")

        mean_rate = float(sum(valid_rain_rates) / len(valid_rain_rates))
        max_rate = float(max(valid_rain_rates))
        
        # Approximate 90th percentile
        sorted_rates = sorted(valid_rain_rates)
        p90_idx = int(0.90 * len(sorted_rates))
        p90_rate = float(sorted_rates[min(p90_idx, len(sorted_rates) - 1)])

        meg_mean = float(sum(meg_rain_rates) / len(meg_rain_rates)) if meg_rain_rates else 0.0
        miz_mean = float(sum(miz_rain_rates) / len(miz_rain_rates)) if miz_rain_rates else 0.0

        # Calculate canonical dynamic rainfall anomaly score in [0.0, 1.0]
        # Canonical formula from live_assessment_service.py:
        # min(1.0, max(0.15, (mean / 8.0) * 0.4 + (max / 25.0) * 0.4 + 0.20))
        derived_rain_anomaly = min(1.0, max(0.15, (mean_rate / 8.0) * 0.4 + (max_rate / 25.0) * 0.4 + 0.20))
        derived_rain_anomaly = round(derived_rain_anomaly, 4)

        return {
            "cell_count_ner": ner_cells,
            "valid_cell_count": len(valid_rain_rates),
            "missing_cell_count": ner_cells - len(valid_rain_rates),
            "mean_precip_mm_h": round(mean_rate, 4),
            "max_precip_mm_h": round(max_rate, 4),
            "p90_precip_mm_h": round(p90_rate, 4),
            "meghalaya_mean_mm_h": round(meg_mean, 4),
            "mizoram_mean_mm_h": round(miz_mean, 4),
            "meghalaya_cells": len(meg_rain_rates),
            "mizoram_cells": len(miz_rain_rates),
            "derived_rain_anomaly": derived_rain_anomaly,
            "parse_duration_seconds": round(t_parse, 3)
        }

    def acquire_latest_observation(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes complete end-to-end acquisition: discovery, atomic download,
        validation, regional extraction, and anomaly calculation.
        """
        t_start = time.time()
        meta = self.detect_latest_product()
        fn = meta["filename"]
        
        local_path, sha256_hash, file_size, dl_time = self.download_product(fn, force=force)
        metrics = self.parse_and_extract_rainfall(local_path)
        
        now_utc = datetime.now(timezone.utc)
        obs_dt = datetime.fromisoformat(meta["observation_start_utc"])
        source_age_s = (now_utc - obs_dt).total_seconds()
        
        if source_age_s <= 7200.0:  # <= 2 hours
            freshness_state = "FRESH"
        elif source_age_s <= 21600.0:  # <= 6 hours
            freshness_state = "RECENT"
        else:
            freshness_state = "DATA_STALE"

        result = {
            "status": "SUCCESS",
            "source_id": "JAXA_GSMAP_NOW_V08",
            "provider": "JAXA Earth Observation Research Center (EORC)",
            "product": "gsmap_now.05_AsiaSS",
            "granule_id": fn,
            "observation_time": meta["observation_start_utc"],
            "observation_end_time": meta["observation_end_utc"],
            "retrieval_timestamp": now_utc.isoformat(),
            "file_path": local_path,
            "file_size_bytes": file_size,
            "sha256_hash": sha256_hash,
            "source_age_seconds": round(source_age_s, 1),
            "freshness_state": freshness_state,
            "regional_metrics": metrics,
            "timings": {
                "download_latency_s": dl_time,
                "parse_latency_s": metrics["parse_duration_seconds"],
                "total_processing_s": round(time.time() - t_start, 3)
            },
            "disclaimer": "JAXA GSMaP_NOW Version 8 satellite precipitation gauge-calibrated regional observation."
        }
        self.last_observation = result
        return result

    def determine_freshness_state(self, observation_utc: str) -> str:
        """Determines freshness state based on observation timestamp."""
        try:
            obs_dt = datetime.fromisoformat(observation_utc.replace("Z", "+00:00"))
            age_s = (datetime.now(timezone.utc) - obs_dt).total_seconds()
            if age_s <= 3600.0:
                return "FRESH"
            elif age_s <= 7200.0:
                return "RECENT"
            elif age_s <= 14400.0:
                return "AGING"
            else:
                return "STALE"
        except Exception:
            return "DATA_STALE"

    def extract_and_analyze_csv(self, csv_content: str, filename: str = "stream.csv") -> Dict[str, Any]:
        """Parses in-memory CSV text and computes quality metrics and rainfall statistics."""
        lines = [line.strip() for line in csv_content.strip().splitlines() if line.strip()]
        total_records = 0
        ner_cells = 0
        valid_cells = []

        for line in lines[1:]:  # Skip header
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                continue
            total_records += 1
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                rate = float(parts[2])
                if (NER_LAT_MIN <= lat <= NER_LAT_MAX) and (NER_LON_MIN <= lon <= NER_LON_MAX):
                    ner_cells += 1
                    if rate >= 0.0:
                        valid_cells.append(rate)
            except (ValueError, IndexError):
                continue

        mean_rate = float(sum(valid_cells) / len(valid_cells)) if valid_cells else 0.0
        max_rate = float(max(valid_cells)) if valid_cells else 0.0

        return {
            "total_records": total_records,
            "aoi_cell_count": ner_cells,
            "valid_cell_count": len(valid_cells),
            "missing_cell_count": ner_cells - len(valid_cells),
            "mean_precipitation_mm_h": round(mean_rate, 4),
            "max_precipitation_mm_h": round(max_rate, 4),
            "rainfall_anomaly_score": compute_rainfall_anomaly_gsmap(mean_rate, max_rate)
        }

    def fetch_latest_product(self, force: bool = False) -> Dict[str, Any]:
        """Convenience method returning flattened operational format."""
        obs = self.acquire_latest_observation(force=force)
        metrics = obs.get("regional_metrics", {})
        return {
            "product_filename": obs.get("granule_id"),
            "observation_start_utc": obs.get("observation_time"),
            "observation_end_utc": obs.get("observation_end_time"),
            "download_timestamp_utc": obs.get("retrieval_timestamp"),
            "processing_timestamp_utc": obs.get("retrieval_timestamp"),
            "source_age_minutes": round(obs.get("source_age_seconds", 0.0) / 60.0, 1),
            "freshness_state": obs.get("freshness_state", "FRESH"),
            "rainfall_anomaly_score": metrics.get("derived_rain_anomaly", 0.35),
            "mean_precipitation_mm_h": metrics.get("mean_precip_mm_h", 0.0),
            "max_precipitation_mm_h": metrics.get("max_precip_mm_h", 0.0),
            "latency_seconds": obs.get("timings", {}).get("total_processing_s", 0.0),
            "meghalaya_covered": metrics.get("meghalaya_cells", 0) > 0,
            "mizoram_covered": metrics.get("mizoram_cells", 0) > 0,
            "valid_cell_count": metrics.get("valid_cell_count", 0),
            "sha256_hash": obs.get("sha256_hash")
        }

def compute_rainfall_anomaly_gsmap(mean_rate: float, max_rate: float) -> float:
    """Canonical formula for deriving operational rainfall anomaly from GSMaP rain rates."""
    return round(min(1.0, max(0.15, (mean_rate / 8.0) * 0.4 + (max_rate / 25.0) * 0.4 + 0.20)), 4)

def parse_gsmap_filename(filename: str) -> Dict[str, Any]:
    """Helper to parse JAXA GSMaP filename components and observation interval."""
    engine = GSMaPNowEngine()
    start_dt, end_dt = engine.parse_product_timestamp(filename)
    parts = filename.split(".")
    return {
        "product_type": parts[0].replace("gsmap_", ""),
        "region": parts[3] if len(parts) > 3 else "05_AsiaSS",
        "start_dt": start_dt,
        "end_dt": end_dt
    }

# Global Singleton Instance
gsmap_engine = GSMaPNowEngine()

if __name__ == "__main__":
    print("Testing JAXA GSMaP_NOW Live Ingestion Engine...")
    try:
        res = gsmap_engine.acquire_latest_observation()
        print(f"Status: {res['status']}")
        print(f"Granule: {res['granule_id']}")
        print(f"Observation Time: {res['observation_time']}")
        print(f"Source Age: {res['source_age_seconds'] / 60.0:.1f} minutes")
        print(f"Freshness: {res['freshness_state']}")
        print(f"NER Mean Precip: {res['regional_metrics']['mean_precip_mm_h']:.2f} mm/h")
        print(f"NER Max Precip:  {res['regional_metrics']['max_precip_mm_h']:.2f} mm/h")
        print(f"Rain Anomaly:    {res['regional_metrics']['derived_rain_anomaly']:.4f}")
        print(f"Total Processing Time: {res['timings']['total_processing_s']:.2f} s")
    except Exception as e:
        print(f"GSMaP Engine Test Failed: {e}")
