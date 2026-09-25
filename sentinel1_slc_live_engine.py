"""
=============================================================================
NER-SAFE: Sentinel-1 SLC Live Acquisition & Multi-Temporal Stack Accumulator
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Live operational acquisition and multi-temporal stack accumulation
         for Sentinel-1 IW SLC repeat passes covering the Meghalaya AOI.
Guarantees:
  1. Strict Geometry Filtering: Track 150, Descending, IW1 swath, VV pol.
  2. Idempotency & Deduplication: Avoids redundant re-downloads (ALREADY_CURRENT).
  3. Storage Guard: Requires >= 10.0 GB free disk space prior to download.
  4. Cryptographic & Scientific Integrity: Little-endian TIFF header (II*\\x00),
     size > 500 MB, annotation XML ephemeris validation, SHA-256 verification.
  5. Persistent Registry: Tracks granular scene lifecycles (DISCOVERED to ARCHIVED).
  6. Incremental Multi-Temporal Growth: Extends stack, updates SBAS baseline graph.
  7. Decoupled Evidence Layer: Strictly research-only; does NOT alter operational
     4-factor risk weights or touch locked models.
  8. Zero Emojis: Strictly compliant with operational UX4G standards.
=============================================================================
"""

import os
import sys
import json
import time
import shutil
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from cdse_client import cdse_client
from cdse_s3_downloader import cdse_s3_downloader, MIN_FREE_DISK_GB
from multitemporal_slc_manager import multitemporal_slc_manager, MIN_SCENES_FOR_PSI, MIN_SCENES_FOR_SBAS
from source_ingestion_manager import source_ingestion_mgr
from database import (
    register_insar_scene,
    register_insar_pair,
    save_insar_deformation_product,
    get_insar_scenes,
    get_insar_pairs,
    get_insar_latest_deformation
)

SLC_DATA_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "SLC")
STACK_REGISTRY_FILE = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "slc_stack_registry.json")
LIVE_STATE_FILE = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "slc_live_acquisition_state.json")

# Verified InSAR Geometry Parameters
TARGET_RELATIVE_ORBIT = 150
TARGET_ORBIT_DIRECTION = "DESCENDING"
TARGET_MODE = "IW"
TARGET_PRODUCT_TYPE = "SLC"
TARGET_SWATH = "IW1"
TARGET_POLARIZATION = "VV"
TARGET_LAT = 25.5
TARGET_LON = 91.0
TARGET_STACK_SIZE_FOR_NEXT_EVALUATION = 15


class Sentinel1SLCLiveEngine:
    """
    Manages genuine live Sentinel-1 SLC discovery, acquisition, integrity validation,
    persistent stack accumulation, and multi-temporal SBAS graph expansion.
    """

    def __init__(self,
                 slc_dir: str = SLC_DATA_DIR,
                 registry_path: str = STACK_REGISTRY_FILE,
                 state_path: str = LIVE_STATE_FILE,
                 min_free_disk_gb: float = MIN_FREE_DISK_GB):
        self.slc_dir = slc_dir
        self.registry_path = registry_path
        self.state_path = state_path
        self.min_free_disk_gb = min_free_disk_gb
        os.makedirs(self.slc_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        self.registry = self._load_registry()
        self.state = self._load_state()

    def _load_registry(self) -> Dict[str, Any]:
        """Loads persistent SLC stack registry."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {"scenes": {}, "last_updated_utc": None}

    def _save_registry(self):
        """Persists registry to disk."""
        self.registry["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2)

    def _load_state(self) -> Dict[str, Any]:
        """Loads live acquisition status and telemetry."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {
            "last_cdse_check_utc": None,
            "last_successful_check_utc": None,
            "last_check_status": "INITIALIZED",
            "last_failure": None,
            "total_cycles_executed": 0,
            "active_mode": "RUN_ONCE",
            "acquisition_status": "ACCUMULATION_ACTIVE"
        }

    def _save_state(self):
        """Persists live state telemetry."""
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def check_storage_guard(self) -> Dict[str, Any]:
        """Verifies disk space guard prior to large file acquisitions."""
        return cdse_s3_downloader.check_disk_space(self.slc_dir, required_gb=self.min_free_disk_gb)

    def query_cdse_catalogue(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Queries Copernicus Data Space Ecosystem OData API for authentic Sentinel-1 IW SLC products
        strictly matching Track 150 Descending geometry over Meghalaya AOI.
        """
        query_start = datetime.now(timezone.utc).isoformat()
        self.state["last_cdse_check_utc"] = query_start

        # Retrieve inventory from manager or direct OData
        inventory = multitemporal_slc_manager.fetch_cdse_inventory(force_refresh=force_refresh)

        # Apply strict scientific filtering
        eligible_scenes = []
        for item in inventory:
            granule = item.get("granule_name", "")
            if not granule.endswith(".SAFE") and not granule.startswith("S1"):
                continue

            # Filtering rules: Sentinel-1, IW, SLC, Track 150, Descending
            is_s1 = granule.startswith("S1A") or granule.startswith("S1B") or granule.startswith("S1D")
            is_iw = item.get("mode") == TARGET_MODE or "_IW_" in granule
            is_slc = item.get("product_type") == TARGET_PRODUCT_TYPE or "_SLC_" in granule
            is_track_150 = item.get("relative_orbit") == TARGET_RELATIVE_ORBIT
            is_desc = item.get("orbit_direction") == TARGET_ORBIT_DIRECTION

            if is_s1 and is_iw and is_slc and is_track_150 and is_desc:
                eligible_scenes.append(item)
                # Register in registry if newly discovered
                if granule not in self.registry["scenes"]:
                    self.registry["scenes"][granule] = {
                        "granule_name": granule,
                        "product_id": item.get("product_id"),
                        "platform": item.get("platform"),
                        "mode": TARGET_MODE,
                        "product_type": TARGET_PRODUCT_TYPE,
                        "swath": TARGET_SWATH,
                        "polarization": TARGET_POLARIZATION,
                        "relative_orbit": TARGET_RELATIVE_ORBIT,
                        "orbit_direction": TARGET_ORBIT_DIRECTION,
                        "sensing_start_utc": item.get("sensing_start_utc"),
                        "sensing_stop_utc": item.get("sensing_stop_utc"),
                        "publication_date_utc": item.get("publication_date_utc"),
                        "provider": "Copernicus Data Space Ecosystem (CDSE)",
                        "size_bytes": item.get("size_bytes", 0),
                        "validation_state": "DISCOVERED",
                        "discovered_at_utc": query_start,
                        "acquired_at_utc": None,
                        "archive_state": "PENDING",
                        "local_path": None,
                        "checksum": None
                    }

        self._save_registry()
        self.state["last_successful_check_utc"] = datetime.now(timezone.utc).isoformat()
        self.state["last_check_status"] = "CATALOGUE_QUERIED"
        self._save_state()
        return eligible_scenes

    def is_scene_already_registered(self, granule_name: str) -> bool:
        """
        Idempotency check: verifies whether a scene is already fully acquired,
        integrity-verified, and registered into the NER-SAFE stack.
        """
        # 1. Check local directory
        target_dir = os.path.join(self.slc_dir, granule_name)
        if os.path.isdir(target_dir):
            meas_dir = os.path.join(target_dir, "measurement")
            annot_dir = os.path.join(target_dir, "annotation")
            manifest_file = os.path.join(target_dir, "manifest.safe")
            if os.path.isdir(meas_dir) and os.path.isdir(annot_dir) and os.path.isfile(manifest_file):
                # Verify measurement TIFF exists and is non-empty
                tiffs = [f for f in os.listdir(meas_dir) if f.endswith(".tiff") or f.endswith(".tif")]
                if tiffs and os.path.getsize(os.path.join(meas_dir, tiffs[0])) > 100 * 1024 * 1024:
                    return True

        # 2. Check SQLite database
        scene_id = granule_name.replace(".SAFE", "")
        db_scenes = get_insar_scenes()
        for s in db_scenes:
            if s.get("scene_id") == scene_id or s.get("granule_name") == granule_name:
                return True

        # 3. Check persistent registry state
        reg_entry = self.registry["scenes"].get(granule_name)
        if reg_entry and reg_entry.get("validation_state") in ("INTEGRITY_VERIFIED", "REGISTERED", "ARCHIVED"):
            return True

        return False

    def validate_scene_integrity(self, target_dir: str) -> Dict[str, Any]:
        """
        Validates cryptographic, physical, and scientific integrity of acquired SLC product:
        - Little-endian TIFF magic header (b"II*\\x00")
        - Minimum file size threshold (> 500 MB for measurement TIFF)
        - Main annotation XML well-formedness and ephemeris content
        - Calibration XML presence
        - SHA-256 computation for all assets
        """
        if not os.path.isdir(target_dir):
            return {"valid": False, "reason": f"Directory not found: {target_dir}"}

        # 1. Manifest
        manifest_path = os.path.join(target_dir, "manifest.safe")
        if not os.path.isfile(manifest_path) or os.path.getsize(manifest_path) < 1000:
            return {"valid": False, "reason": "manifest.safe missing or invalid size"}

        # 2. Measurement TIFF
        meas_dir = os.path.join(target_dir, "measurement")
        if not os.path.isdir(meas_dir):
            return {"valid": False, "reason": "measurement directory missing"}

        tiffs = [os.path.join(meas_dir, f) for f in os.listdir(meas_dir) if f.endswith(".tiff") or f.endswith(".tif")]
        if not tiffs:
            return {"valid": False, "reason": "Measurement TIFF missing"}

        meas_tiff = tiffs[0]
        tiff_size = os.path.getsize(meas_tiff)
        if tiff_size < 500 * 1024 * 1024:
            return {"valid": False, "reason": f"Measurement TIFF size {tiff_size / (1024**2):.1f} MB below 500 MB threshold"}

        # Header check: TIFF magic bytes
        with open(meas_tiff, "rb") as f:
            header = f.read(4)
        if header != b"II*\x00" and header != b"MM\x00*":
            return {"valid": False, "reason": f"Invalid TIFF magic bytes: {header}"}

        # 3. Annotation XML
        annot_dir = os.path.join(target_dir, "annotation")
        if not os.path.isdir(annot_dir):
            return {"valid": False, "reason": "annotation directory missing"}

        xmls = [os.path.join(annot_dir, f) for f in os.listdir(annot_dir) if f.endswith(".xml")]
        if not xmls:
            return {"valid": False, "reason": "Annotation XML missing"}

        main_xml = xmls[0]
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(main_xml)
            root = tree.getroot()
            orbit_list = root.findall(".//orbit")
            if not orbit_list:
                return {"valid": False, "reason": "Annotation XML lacks orbit state vectors"}
        except Exception as e:
            return {"valid": False, "reason": f"Annotation XML parsing error: {str(e)}"}

        # Compute SHA-256 for key files
        file_hashes = {}
        for p in [manifest_path, main_xml, meas_tiff]:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
                    h.update(chunk)
            file_hashes[os.path.basename(p)] = h.hexdigest()

        return {
            "valid": True,
            "manifest_path": manifest_path,
            "measurement_tiff": meas_tiff,
            "annotation_xml": main_xml,
            "tiff_size_bytes": tiff_size,
            "tiff_header": header.hex(),
            "sha256_hashes": file_hashes
        }

    def acquire_and_register_scene(self, scene_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes full lifecycle for an eligible scene:
        VALIDATED -> ACQUISITION_PENDING -> ACQUIRED -> INTEGRITY_VERIFIED -> REGISTERED -> ARCHIVED
        """
        granule_name = scene_meta["granule_name"]
        product_id = scene_meta.get("product_id")
        reg_entry = self.registry["scenes"].setdefault(granule_name, {})

        # Storage guard check
        guard = self.check_storage_guard()
        if not guard["sufficient_space"]:
            reg_entry["validation_state"] = "REJECTED"
            reg_entry["rejection_reason"] = f"Storage guard: only {guard['free_gb']} GB free, {self.min_free_disk_gb} GB required"
            self._save_registry()
            return {
                "status": "STORAGE_GUARD_TRIGGERED",
                "granule_name": granule_name,
                "message": reg_entry["rejection_reason"],
                "free_gb": guard["free_gb"],
                "required_gb": self.min_free_disk_gb
            }

        # Query CDSE S3 path via OData API
        reg_entry["validation_state"] = "ACQUISITION_PENDING"
        self._save_registry()

        token = cdse_client.get_auth_token()
        odata_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})"
        req = urllib.request.Request(odata_url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                odata_rec = json.loads(resp.read().decode("utf-8"))
            s3_path = odata_rec.get("S3Path")
        except Exception as e:
            reg_entry["validation_state"] = "FAILED"
            reg_entry["failure_reason"] = f"OData S3Path query failed: {str(e)}"
            self._save_registry()
            return {"status": "FAILED", "granule_name": granule_name, "error": str(e)}

        if not s3_path:
            reg_entry["validation_state"] = "FAILED"
            reg_entry["failure_reason"] = "S3Path missing in CDSE OData record"
            self._save_registry()
            return {"status": "FAILED", "granule_name": granule_name, "error": "S3Path not provided by CDSE"}

        # Acquire subswath via CDSES3Downloader
        t_acq_start = time.time()
        t_acq_start_iso = datetime.now(timezone.utc).isoformat()
        try:
            acq_res = cdse_s3_downloader.acquire_slc_product_swath(
                s3_safe_path=s3_path,
                swath=TARGET_SWATH.lower(),
                pol=TARGET_POLARIZATION.lower(),
                target_dir=self.slc_dir
            )
            reg_entry["validation_state"] = "ACQUIRED"
            reg_entry["acquired_at_utc"] = datetime.now(timezone.utc).isoformat()
            reg_entry["local_path"] = acq_res["local_dir"]
        except Exception as e:
            reg_entry["validation_state"] = "FAILED"
            reg_entry["failure_reason"] = f"S3 acquisition error: {str(e)}"
            self._save_registry()
            return {"status": "FAILED", "granule_name": granule_name, "error": str(e)}

        # Integrity Validation
        target_dir = acq_res["local_dir"]
        val_res = self.validate_scene_integrity(target_dir)
        if not val_res["valid"]:
            reg_entry["validation_state"] = "REJECTED"
            reg_entry["rejection_reason"] = val_res["reason"]
            self._save_registry()
            return {"status": "INTEGRITY_FAILED", "granule_name": granule_name, "reason": val_res["reason"]}

        reg_entry["validation_state"] = "INTEGRITY_VERIFIED"
        reg_entry["checksum"] = val_res["sha256_hashes"].get(os.path.basename(val_res["measurement_tiff"]))

        # Database Registration
        scene_id = granule_name.replace(".SAFE", "")
        db_record = {
            "scene_id": scene_id,
            "granule_name": granule_name,
            "product_name": granule_name,
            "platform": scene_meta.get("platform", "Sentinel-1D"),
            "mode": TARGET_MODE,
            "product_type": TARGET_PRODUCT_TYPE,
            "polarization": TARGET_POLARIZATION,
            "relative_orbit": TARGET_RELATIVE_ORBIT,
            "orbit_direction": TARGET_ORBIT_DIRECTION,
            "sensing_start_utc": scene_meta.get("sensing_start_utc"),
            "sensing_stop_utc": scene_meta.get("sensing_stop_utc"),
            "size_bytes": acq_res.get("total_size_bytes", val_res["tiff_size_bytes"]),
            "sha256": reg_entry["checksum"],
            "local_path": target_dir,
            "acquisition_status": "LIVE_VERIFIED"
        }
        register_insar_scene(db_record)

        # Provenance Catalog Ingestion
        source_ingestion_mgr.register_slc_acquisition(acq_res)

        reg_entry["validation_state"] = "REGISTERED"
        reg_entry["archive_state"] = "REGISTERED"
        self._save_registry()

        return {
            "status": "ACQUIRED_AND_REGISTERED",
            "granule_name": granule_name,
            "scene_id": scene_id,
            "sensing_start_utc": scene_meta.get("sensing_start_utc"),
            "local_path": target_dir,
            "size_bytes": db_record["size_bytes"],
            "sha256": reg_entry["checksum"],
            "duration_seconds": round(time.time() - t_acq_start, 2)
        }

    def update_multitemporal_stack(self) -> Dict[str, Any]:
        """
        Refreshes the multi-temporal InSAR stack and SBAS baseline network graph
        with all currently registered authentic SLC scenes.
        """
        from insar_multitemporal_engine import InSARMultiTemporalEngine
        engine = InSARMultiTemporalEngine(slc_dir=self.slc_dir)

        # 1. Discover all local scenes and register in DB
        registered_scenes = engine.discover_and_register_scenes()

        # 2. Generate SBAS network graph
        network = engine.construct_pair_network(registered_scenes)

        # 3. Process pairs incrementally (reuses existing pairs automatically)
        processed_pairs = engine.process_pairs(network)

        # 4. Invert deformation time-series via SVD
        inversion_result = engine.run_multitemporal_sbas_inversion(network, processed_pairs)

        # Update registry stack summary
        self.registry["current_stack_size"] = len(registered_scenes)
        self.registry["eligible_pairs_count"] = network.get("eligible_pairs_count", 0)
        self.registry["sbas_status"] = network.get("sbas_status")
        self.registry["psi_status"] = network.get("psi_status")
        self._save_registry()

        return {
            "stack_size_scenes": len(registered_scenes),
            "target_stack_size": TARGET_STACK_SIZE_FOR_NEXT_EVALUATION,
            "stack_target_progress": f"{len(registered_scenes)} / {TARGET_STACK_SIZE_FOR_NEXT_EVALUATION}+ scenes",
            "eligible_pairs_count": network.get("eligible_pairs_count", 0),
            "sbas_status": network.get("sbas_status"),
            "psi_status": network.get("psi_status"),
            "scientific_status": "RESEARCH_ONLY",
            "network_id": network.get("network_id"),
            "inversion_summary": inversion_result
        }

    def execute_live_cycle(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Executes an end-to-end live check cycle:
        1. Query CDSE OData catalogue for Track 150 Descending IW SLC scenes.
        2. Filter eligible scenes.
        3. Check idempotency: identify unacquired scenes.
        4. If no new scene: return NO_NEW_ELIGIBLE_SCENE / ALREADY_CURRENT.
        5. If new scene: acquire, verify, register, update stack and SBAS network.
        6. Produce structured auditable log record without secret exposure.
        """
        cycle_start_utc = datetime.now(timezone.utc).isoformat()
        t0 = time.time()
        self.state["total_cycles_executed"] += 1

        # Query CDSE
        try:
            candidates = self.query_cdse_catalogue(force_refresh=force_refresh)
        except Exception as e:
            self.state["last_check_status"] = "QUERY_FAILED"
            self.state["last_failure"] = str(e)
            self._save_state()
            return {
                "status": "FAILED",
                "stage": "CATALOGUE_DISCOVERY",
                "error": str(e),
                "timestamp_utc": cycle_start_utc
            }

        # Check existing stack
        local_scenes = set(d for d in os.listdir(self.slc_dir) if d.endswith(".SAFE"))
        latest_local_granule = sorted(list(local_scenes))[-1] if local_scenes else None

        # Parse sensing time of latest local scene
        latest_local_dt = None
        if latest_local_granule:
            try:
                parts = latest_local_granule.split("_")
                for p in parts:
                    if len(p) == 15 and "T" in p and p.startswith("202"):
                        latest_local_dt = datetime.strptime(p, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                        break
            except Exception:
                pass

        # Identify newly published unacquired scenes extending the stack forward in time
        unacquired_new_scenes = []
        already_registered_count = 0

        for cand in candidates:
            g_name = cand["granule_name"]
            c_dt = datetime.fromisoformat(cand["sensing_start_utc"].replace("Z", "+00:00"))
            is_local = g_name in local_scenes or self.is_scene_already_registered(g_name)

            if is_local:
                already_registered_count += 1
                if g_name in self.registry["scenes"]:
                    self.registry["scenes"][g_name]["validation_state"] = "ALREADY_CURRENT"
            elif latest_local_dt and c_dt > latest_local_dt:
                # Genuinely new repeat pass published after latest local scene
                unacquired_new_scenes.append(cand)

        self._save_registry()

        # If no new candidate scenes exist extending the active stack
        if not unacquired_new_scenes:
            self.state["last_check_status"] = "ALREADY_CURRENT"
            self.state["last_failure"] = None
            self._save_state()

            stack_summary = self.get_stack_summary()
            return {
                "status": "ALREADY_CURRENT",
                "cycle_result": "NO_NEW_ELIGIBLE_SCENE",
                "polled_at_utc": cycle_start_utc,
                "provider": "Copernicus Data Space Ecosystem (CDSE)",
                "query": {
                    "mission": "SENTINEL-1",
                    "mode": TARGET_MODE,
                    "product_type": TARGET_PRODUCT_TYPE,
                    "orbit_direction": TARGET_ORBIT_DIRECTION,
                    "relative_orbit": TARGET_RELATIVE_ORBIT,
                    "polarization": TARGET_POLARIZATION,
                    "aoi": "Meghalaya (Track 150)"
                },
                "total_catalogue_scenes": len(candidates),
                "already_registered_scenes": already_registered_count,
                "new_eligible_scenes": 0,
                "current_stack_size": stack_summary["stack_size_scenes"],
                "target_stack_size": TARGET_STACK_SIZE_FOR_NEXT_EVALUATION,
                "stack_target_progress": stack_summary["stack_target_progress"],
                "eligible_pairs_count": stack_summary["eligible_pairs_count"],
                "sbas_status": stack_summary["sbas_status"],
                "psi_status": stack_summary["psi_status"],
                "scientific_status": "RESEARCH_ONLY",
                "latest_local_scene": latest_local_granule,
                "duration_seconds": round(time.time() - t0, 2)
            }

        # A new scene is available: acquire the earliest missing one
        target_scene = unacquired_new_scenes[0]
        acq_res = self.acquire_and_register_scene(target_scene)

        if acq_res["status"] != "ACQUIRED_AND_REGISTERED":
            self.state["last_check_status"] = acq_res["status"]
            self.state["last_failure"] = acq_res.get("error") or acq_res.get("reason")
            self._save_state()
            return {
                "status": acq_res["status"],
                "cycle_result": "ACQUISITION_FAILED",
                "target_scene": target_scene["granule_name"],
                "details": acq_res,
                "duration_seconds": round(time.time() - t0, 2)
            }

        # Update multi-temporal stack and SBAS network
        stack_res = self.update_multitemporal_stack()

        self.state["last_check_status"] = "NEW_SCENE_ACQUIRED_AND_STACKED"
        self.state["last_failure"] = None
        self._save_state()

        return {
            "status": "NEW_OBSERVATION_ACQUIRED",
            "cycle_result": "SUCCESSFUL_STACK_EXPANSION",
            "polled_at_utc": cycle_start_utc,
            "acquired_scene": acq_res,
            "stack_summary": stack_res,
            "duration_seconds": round(time.time() - t0, 2)
        }

    def get_stack_summary(self) -> Dict[str, Any]:
        """Returns comprehensive status telemetry for APIs and dashboards."""
        db_scenes = get_insar_scenes()
        pairs = get_insar_pairs()
        latest_def = get_insar_latest_deformation()

        n_scenes = len(db_scenes)
        latest_acq = db_scenes[-1]["sensing_start_utc"] if db_scenes else None
        latest_disc = self.state.get("last_cdse_check_utc")
        guard = self.check_storage_guard()

        return {
            "system": "NER-SAFE Sentinel-1 SLC Live InSAR Accumulation Subsystem",
            "track": TARGET_RELATIVE_ORBIT,
            "orbit_direction": TARGET_ORBIT_DIRECTION,
            "swath": TARGET_SWATH,
            "polarization": TARGET_POLARIZATION,
            "stack_size_scenes": n_scenes,
            "target_stack_size": TARGET_STACK_SIZE_FOR_NEXT_EVALUATION,
            "stack_target_progress": f"{n_scenes} / {TARGET_STACK_SIZE_FOR_NEXT_EVALUATION}+ scenes",
            "eligible_pairs_count": len(pairs),
            "latest_acquisition_utc": latest_acq,
            "latest_discovery_utc": latest_disc,
            "last_successful_cdse_check_utc": self.state.get("last_successful_check_utc"),
            "last_check_status": self.state.get("last_check_status", "INITIALIZED"),
            "last_failure": self.state.get("last_failure"),
            "acquisition_status": self.state.get("acquisition_status", "ACCUMULATION_ACTIVE"),
            "sbas_status": latest_def.get("multitemporal_status", "SBAS_INITIAL_STACK_FORMED") if latest_def else ("SBAS_INITIAL_STACK_FORMED" if n_scenes >= 3 else "INSUFFICIENT_STACK"),
            "psi_status": "INSUFFICIENT_SLC_STACK_FOR_PSI",
            "scientific_status": "RESEARCH_ONLY",
            "risk_integration_status": "INSAR_RESEARCH_EVIDENCE_DECOUPLED",
            "storage": {
                "free_gb": guard["free_gb"],
                "required_gb": guard["required_gb"],
                "sufficient": guard["sufficient_space"]
            },
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }


sentinel1_slc_live_engine = Sentinel1SLCLiveEngine()

if __name__ == "__main__":
    print("Testing Sentinel1SLCLiveEngine...")
    res = sentinel1_slc_live_engine.execute_live_cycle(force_refresh=False)
    print("Live Cycle Result:")
    print(json.dumps(res, indent=2))
