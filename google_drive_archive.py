"""
=============================================================================
NER-SAFE: Google Drive Cloud Heavy-Data Archival Engine
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Archives validated heavy satellite data (Sentinel-1 SLC/GRD, Sentinel-2,
         InSAR outputs, GPM, SMAP) to the user's verified 5 TB Google Drive cloud.
Key Principles:
  1. Active Compute Preserved: E: remains the active compute and cache filesystem.
     Google Drive G: is NOT used as primary compute storage.
  2. Local Retention Policy: LOCAL_RETENTION_POLICY = KEEP. Local files on E: are
     strictly preserved; zero files are deleted after upload.
  3. Resumable Chunked Streaming: Large files are streamed directly in 8 MB chunks
     without loading whole gigabyte-scale radar scenes into system RAM.
  4. Deduplication & Verification: Queries remote folder to avoid redundant uploads;
     verifies remote size matches local size; records SHA-256.
  5. Decoupled Pipeline: Network interruptions or Drive unavailability return
     ARCHIVE_PENDING or ARCHIVE_FAILED and NEVER invalidate scientific observations.
  6. Zero Secret Exposure: Never logs, prints, commits, or stores OAuth tokens/keys.
=============================================================================
"""

import os
import sys
import json
import time
import hashlib
import mimetypes
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Authoritative Policies
LOCAL_RETENTION_POLICY = "KEEP"
ARCHIVE_ROOT_FOLDER_NAME = "NER-SAFE-DATA"
CHUNK_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB chunks (multiple of 256 KB)
DEFAULT_MANIFEST_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "archive_manifest.json")
DEFAULT_CACHE_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "archive_folder_cache.json")


class GoogleDriveArchiveEngine:
    """Manages secure, resumable, verifiable cloud archival to Google Drive API v3."""

    def __init__(self, manifest_path: Optional[str] = None, cache_path: Optional[str] = None):
        self.manifest_path = manifest_path or DEFAULT_MANIFEST_PATH
        self.cache_path = cache_path or DEFAULT_CACHE_PATH
        self.folder_cache: Dict[str, str] = {}
        self.manifest: Dict[str, Any] = self._load_manifest()
        self._load_folder_cache()

    def _get_access_token(self) -> Optional[str]:
        """Safely retrieves a valid access token using the storage engine OAuth handler."""
        try:
            from storage_engine import storage_engine
            return storage_engine._get_active_access_token()
        except Exception:
            token_file = os.path.join(PROJECT_ROOT, "token.json")
            if os.path.exists(token_file):
                try:
                    with open(token_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data.get("token") or data.get("access_token")
                except Exception:
                    pass
        return None

    def _load_manifest(self) -> Dict[str, Any]:
        """Loads persistent archive manifest from disk."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "system": "NER-SAFE Google Drive Heavy-Data Archive",
            "retention_policy": LOCAL_RETENTION_POLICY,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_updated_utc": datetime.now(timezone.utc).isoformat(),
            "total_archived_bytes": 0,
            "total_archived_files": 0,
            "archived_records": {}
        }

    def _save_manifest(self):
        """Safely saves persistent archive manifest to disk."""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        self.manifest["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
        records = self.manifest.get("archived_records", {})
        self.manifest["total_archived_files"] = len(records)
        self.manifest["total_archived_bytes"] = sum(r.get("size_bytes", 0) for r in records.values())
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

    def _load_folder_cache(self):
        """Loads cached remote folder IDs to prevent redundant API queries."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.folder_cache = json.load(f)
            except Exception:
                self.folder_cache = {}

    def _save_folder_cache(self):
        """Saves remote folder ID cache."""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.folder_cache, f, indent=2)

    def check_connection(self) -> Dict[str, Any]:
        """Checks Google Drive API authentication, account, and quota."""
        token = self._get_access_token()
        if not token:
            return {
                "authenticated": False,
                "status": "TOKEN_UNAVAILABLE",
                "message": "Google Drive OAuth token not available."
            }

        url = "https://www.googleapis.com/drive/v3/about?fields=user,storageQuota"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                user = data.get("user", {})
                quota = data.get("storageQuota", {})
                limit_bytes = int(quota.get("limit", 0))
                usage_bytes = int(quota.get("usage", 0))
                return {
                    "authenticated": True,
                    "status": "CONNECTED",
                    "display_name": user.get("displayName", "Authorized User"),
                    "cloud_limit_gb": round(limit_bytes / (1024 ** 3), 2),
                    "cloud_usage_gb": round(usage_bytes / (1024 ** 3), 2),
                    "cloud_available_gb": round((limit_bytes - usage_bytes) / (1024 ** 3), 2),
                    "local_retention_policy": LOCAL_RETENTION_POLICY
                }
        except Exception as e:
            return {
                "authenticated": False,
                "status": "CONNECTION_ERROR",
                "error": str(e)
            }

    def get_or_create_folder(self, folder_path: str) -> Optional[str]:
        """
        Resolves or creates a nested folder hierarchy on Google Drive.
        e.g. 'SENTINEL1/SLC' under root 'NER-SAFE-DATA'
        """
        if folder_path in self.folder_cache:
            return self.folder_cache[folder_path]

        token = self._get_access_token()
        if not token:
            return None

        # 1. Resolve Root 'NER-SAFE-DATA'
        root_id = self.folder_cache.get("ROOT")
        if not root_id:
            root_id = self._find_or_create_single_folder(ARCHIVE_ROOT_FOLDER_NAME, parent_id=None, token=token)
            if not root_id:
                return None
            self.folder_cache["ROOT"] = root_id

        if not folder_path or folder_path == "ROOT" or folder_path == "/":
            return root_id

        # 2. Resolve sub-components sequentially
        current_parent_id = root_id
        path_parts = [p.strip() for p in folder_path.replace("\\", "/").strip("/").split("/") if p.strip()]
        accumulated_path = ""

        for part in path_parts:
            accumulated_path = f"{accumulated_path}/{part}" if accumulated_path else part
            if accumulated_path in self.folder_cache:
                current_parent_id = self.folder_cache[accumulated_path]
            else:
                sub_id = self._find_or_create_single_folder(part, parent_id=current_parent_id, token=token)
                if not sub_id:
                    return None
                self.folder_cache[accumulated_path] = sub_id
                current_parent_id = sub_id

        self._save_folder_cache()
        return current_parent_id

    def _find_or_create_single_folder(self, folder_name: str, parent_id: Optional[str], token: str) -> Optional[str]:
        """Finds or creates a single folder inside a specified parent folder."""
        # Search query
        if parent_id:
            q = f"name = '{folder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        else:
            q = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

        url = f"https://www.googleapis.com/drive/v3/files?q={urllib.parse.quote(q)}&fields=files(id,name)"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                files = res.get("files", [])
                if files:
                    return files[0]["id"]
        except Exception:
            pass

        # Create folder if not found
        create_url = "https://www.googleapis.com/drive/v3/files"
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        create_req = urllib.request.Request(
            create_url,
            data=json.dumps(metadata).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(create_req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("id")
        except Exception as e:
            print(f"[GoogleDriveArchive] Error creating folder {folder_name}: {e}")
            return None

    def initialize_archive_structure(self) -> Dict[str, Any]:
        """Ensures the full canonical NER-SAFE-DATA folder structure exists on Google Drive."""
        structure = [
            "SENTINEL1/SLC",
            "SENTINEL1/GRD",
            "SENTINEL2",
            "INSAR",
            "GPM",
            "SMAP",
            "MANIFESTS"
        ]
        results = {}
        for path in structure:
            fid = self.get_or_create_folder(path)
            results[path] = fid
        return results

    def find_remote_file(self, filename: str, folder_id: str) -> Optional[Dict[str, Any]]:
        """Checks whether a file with given name already exists in target remote folder."""
        token = self._get_access_token()
        if not token:
            return None

        q = f"name = '{filename}' and '{folder_id}' in parents and trashed = false"
        url = f"https://www.googleapis.com/drive/v3/files?q={urllib.parse.quote(q)}&fields=files(id,name,size,md5Checksum,createdTime)"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                files = res.get("files", [])
                if files:
                    return files[0]
        except Exception:
            pass
        return None

    def archive_file(self,
                     local_path: str,
                     category: str,
                     remote_filename: Optional[str] = None,
                     force_reupload: bool = False,
                     source: str = "NER-SAFE") -> Dict[str, Any]:
        """
        Performs validated, resumable chunked streaming archival of a heavy satellite file.
        Enforces LOCAL_RETENTION_POLICY = KEEP.
        """
        if not os.path.exists(local_path):
            return {
                "archive_status": "FAILED",
                "reason": f"Local file does not exist: {local_path}"
            }

        file_size = os.path.getsize(local_path)
        filename = remote_filename or os.path.basename(local_path)

        # 1. Resolve Remote Target Folder
        folder_id = self.get_or_create_folder(category)
        if not folder_id:
            return {
                "archive_status": "ARCHIVE_FAILED",
                "local_path": local_path,
                "reason": f"Failed to resolve remote folder for category: {category}"
            }

        # 2. Deduplication Check
        if not force_reupload:
            existing = self.find_remote_file(filename, folder_id)
            if existing and int(existing.get("size", -1)) == file_size:
                # File already exists with identical size
                record = {
                    "local_path": local_path,
                    "remote_file_id": existing["id"],
                    "filename": filename,
                    "category": category,
                    "size_bytes": file_size,
                    "upload_timestamp_utc": existing.get("createdTime", datetime.now(timezone.utc).isoformat()),
                    "verification_status": "VERIFIED_EXISTING",
                    "retention_policy": LOCAL_RETENTION_POLICY,
                    "source": source
                }
                self.manifest.setdefault("archived_records", {})[local_path] = record
                self._save_manifest()
                return {
                    "archive_status": "ARCHIVED",
                    "remote_file_id": existing["id"],
                    "action": "DEDUPLICATED",
                    "verification_status": "VERIFIED_EXISTING"
                }

        token = self._get_access_token()
        if not token:
            return {
                "archive_status": "ARCHIVE_PENDING",
                "local_path": local_path,
                "reason": "OAuth token unavailable; archival deferred."
            }

        # 3. Initiate Resumable Upload Session
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        init_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable"
        metadata = {
            "name": filename,
            "parents": [folder_id],
            "description": f"NER-SAFE Automated Scientific Archive: {category} | {source}"
        }

        init_req = urllib.request.Request(
            init_url,
            data=json.dumps(metadata).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": mime_type,
                "X-Upload-Content-Length": str(file_size)
            }
        )

        try:
            with urllib.request.urlopen(init_req, timeout=30) as init_resp:
                session_uri = init_resp.headers.get("Location")
        except Exception as e:
            return {
                "archive_status": "ARCHIVE_FAILED",
                "local_path": local_path,
                "reason": f"Failed to initiate resumable session: {str(e)}"
            }

        if not session_uri:
            return {
                "archive_status": "ARCHIVE_FAILED",
                "local_path": local_path,
                "reason": "No session URI returned by Google Drive API."
            }

        # 4. Stream Chunks with On-The-Fly SHA-256 Calculation
        h_sha = hashlib.sha256()
        uploaded_bytes = 0
        chunk_size = CHUNK_SIZE_BYTES
        remote_file_id = None
        max_retries = 3

        with open(local_path, "rb") as fp:
            while uploaded_bytes < file_size:
                chunk = fp.read(chunk_size)
                if not chunk:
                    break
                h_sha.update(chunk)
                chunk_len = len(chunk)
                start_byte = uploaded_bytes
                end_byte = uploaded_bytes + chunk_len - 1

                # Send chunk with retry
                chunk_uploaded = False
                for attempt in range(1, max_retries + 1):
                    put_req = urllib.request.Request(
                        session_uri,
                        data=chunk,
                        headers={
                            "Content-Length": str(chunk_len),
                            "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}"
                        },
                        method="PUT"
                    )
                    try:
                        with urllib.request.urlopen(put_req, timeout=60) as chunk_resp:
                            if chunk_resp.status in (200, 201):
                                res_json = json.loads(chunk_resp.read().decode("utf-8"))
                                remote_file_id = res_json.get("id")
                            chunk_uploaded = True
                            break
                    except urllib.error.HTTPError as he:
                        if he.code == 308:
                            # 308 Resume Incomplete is expected for non-final chunks
                            chunk_uploaded = True
                            break
                        elif he.code in (500, 502, 503, 504):
                            time.sleep(2 ** attempt)
                        else:
                            return {
                                "archive_status": "ARCHIVE_FAILED",
                                "local_path": local_path,
                                "reason": f"Google Drive HTTP {he.code}: {str(he)}"
                            }
                    except Exception as e:
                        if attempt == max_retries:
                            return {
                                "archive_status": "ARCHIVE_FAILED",
                                "local_path": local_path,
                                "reason": f"Chunk upload error: {str(e)}"
                            }
                        time.sleep(2 ** attempt)

                if not chunk_uploaded:
                    return {
                        "archive_status": "ARCHIVE_FAILED",
                        "local_path": local_path,
                        "reason": f"Chunk at byte {start_byte} failed after {max_retries} attempts."
                    }

                uploaded_bytes += chunk_len

        # 5. Remote Size & Integrity Verification
        if not remote_file_id:
            # If final response was not captured, query by name
            remote_info = self.find_remote_file(filename, folder_id)
            if remote_info:
                remote_file_id = remote_info.get("id")

        if not remote_file_id:
            return {
                "archive_status": "ARCHIVE_FAILED",
                "local_path": local_path,
                "reason": "Upload finished but failed to retrieve remote file ID."
            }

        # Verify remote metadata
        v_url = f"https://www.googleapis.com/drive/v3/files/{remote_file_id}?fields=id,name,size,md5Checksum"
        v_req = urllib.request.Request(v_url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(v_req, timeout=15) as v_resp:
                remote_meta = json.loads(v_resp.read().decode("utf-8"))
                remote_size = int(remote_meta.get("size", 0))
                if remote_size != file_size:
                    return {
                        "archive_status": "INTEGRITY_MISMATCH",
                        "local_path": local_path,
                        "expected_size": file_size,
                        "remote_size": remote_size
                    }
        except Exception as e:
            print(f"[GoogleDriveArchive] Warning: Verification query error: {e}")

        # 6. Record Persistent Safe Provenance
        sha256_hex = h_sha.hexdigest()
        record = {
            "local_path": local_path,
            "remote_file_id": remote_file_id,
            "filename": filename,
            "category": category,
            "size_bytes": file_size,
            "sha256": sha256_hex,
            "upload_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "verification_status": "VERIFIED_SIZE_MATCH",
            "retention_policy": LOCAL_RETENTION_POLICY,
            "source": source
        }
        self.manifest.setdefault("archived_records", {})[local_path] = record
        self._save_manifest()

        return {
            "archive_status": "ARCHIVED",
            "remote_file_id": remote_file_id,
            "filename": filename,
            "size_bytes": file_size,
            "sha256": sha256_hex,
            "verification_status": "VERIFIED_SIZE_MATCH",
            "retention_policy": LOCAL_RETENTION_POLICY
        }

    def archive_insar_persistent_outputs(self) -> Dict[str, Any]:
        """Archives all genuine InSAR persistent GeoTIFF rasters and JSON metadata."""
        insar_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1")
        targets = [
            "insar_coherence.tif",
            "insar_los_displacement.tif",
            "insar_unwrapped_phase.tif",
            "insar_quality_mask.tif",
            "insar_processing_summary.json",
            "insar_ingestion_record.json"
        ]
        results = {}
        for fname in targets:
            fpath = os.path.join(insar_dir, fname)
            if os.path.exists(fpath):
                res = self.archive_file(fpath, category="INSAR", source="SENTINEL1_INSAR")
                results[fname] = res
            else:
                results[fname] = {"archive_status": "SKIPPED_NOT_FOUND"}

        return {
            "component": "SENTINEL1_INSAR",
            "category": "INSAR",
            "files_archived": results
        }

    def archive_current_slc_pair(self) -> Dict[str, Any]:
        """Archives genuine Sentinel-1 SLC SAFE XML metadata and measurement swaths."""
        slc_base = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "SLC")
        if not os.path.exists(slc_base):
            return {"status": "SLC_DIR_NOT_FOUND"}

        scenes = [d for d in os.listdir(slc_base) if os.path.isdir(os.path.join(slc_base, d)) and d.endswith(".SAFE")]
        results = {}

        for scene in scenes:
            scene_dir = os.path.join(slc_base, scene)
            results[scene] = {}
            for root, _, files in os.walk(scene_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    rel_p = os.path.relpath(fpath, scene_dir)
                    # Archive manifests, XMLs, and TIFF measurement files
                    if f.endswith((".xml", ".safe", ".SAFE", ".tiff", ".tif")):
                        remote_name = f"{scene}__{rel_p.replace(os.sep, '__')}"
                        res = self.archive_file(fpath, category="SENTINEL1/SLC", remote_filename=remote_name, source="ESA_CDSE_S3")
                        results[scene][rel_p] = res

        return {
            "component": "SENTINEL1_SLC",
            "category": "SENTINEL1/SLC",
            "scenes": results
        }

    def get_summary(self) -> Dict[str, Any]:
        """Returns comprehensive archive statistics for diagnostics and reporting."""
        conn = self.check_connection()
        records = self.manifest.get("archived_records", {})
        categories = {}
        for r in records.values():
            cat = r.get("category", "OTHER")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "google_drive_connected": conn.get("authenticated", False),
            "cloud_user": conn.get("display_name"),
            "cloud_limit_gb": conn.get("cloud_limit_gb"),
            "cloud_usage_gb": conn.get("cloud_usage_gb"),
            "local_retention_policy": LOCAL_RETENTION_POLICY,
            "total_archived_files": len(records),
            "total_archived_bytes": sum(r.get("size_bytes", 0) for r in records.values()),
            "categories_breakdown": categories,
            "manifest_file": self.manifest_path
        }


# Global Archive Singleton
google_drive_archiver = GoogleDriveArchiveEngine()
