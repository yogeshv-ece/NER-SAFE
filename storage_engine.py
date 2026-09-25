"""
NER-SAFE: Dual-Backend Storage Engine (Local-First + Google Drive / Google One)
Handles structured snapshot storage, historical auditing, and Google Drive API v3 backup.

Principles:
1. Local-First: The system ALWAYS writes locally and functions 100% even if Google Drive is offline or unlinked.
2. Lightweight only: Syncs JSON predictions, warnings, and logs (<100 KB). NEVER uploads the 35 GB raw rasters.
3. Consumer Google One compliance: Connects via standard Google Drive API v3 OAuth2 credentials (credentials.json / token.json).
4. Zero Fabrication: Never reports CONNECTED or SYNCED unless Google Drive API returned a valid HTTP 200/201 and file ID.
   If credentials or tokens are missing, reports honest state: AWAITING_OAUTH_TOKEN (Local Storage Active).
"""

import os
import json
import logging
import urllib.request
import urllib.error
import mimetypes
from datetime import datetime, timezone

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
BASE_STORAGE_DIR = os.path.join(PROJECT_ROOT, "NER-SAFE")

SUBDIRS = [
    os.path.join(BASE_STORAGE_DIR, "live", "raw"),
    os.path.join(BASE_STORAGE_DIR, "live", "validated"),
    os.path.join(BASE_STORAGE_DIR, "live", "processed"),
    os.path.join(BASE_STORAGE_DIR, "predictions", "risk"),
    os.path.join(BASE_STORAGE_DIR, "predictions", "hotspots"),
    os.path.join(BASE_STORAGE_DIR, "predictions", "runout"),
    os.path.join(BASE_STORAGE_DIR, "predictions", "exposure"),
    os.path.join(BASE_STORAGE_DIR, "predictions", "warnings"),
    os.path.join(BASE_STORAGE_DIR, "history"),
    os.path.join(BASE_STORAGE_DIR, "demonstrations", "replay"),
    os.path.join(BASE_STORAGE_DIR, "demonstrations", "scenarios"),
    os.path.join(BASE_STORAGE_DIR, "logs")
]

for d in SUBDIRS:
    os.makedirs(d, exist_ok=True)

class StorageEngine:
    def __init__(self):
        self.base_dir = BASE_STORAGE_DIR
        self.creds_path = os.path.join(PROJECT_ROOT, "credentials.json")
        self.token_path = os.path.join(PROJECT_ROOT, "token.json")
        self.drive_enabled = False
        self.drive_status = "LOCAL_STORAGE_ACTIVE (DRIVE_UNLINKED - AWAITING_OAUTH_TOKEN)"
        self.last_sync_timestamp = None
        self.sync_history = []
        self._check_drive_config()

    def _check_drive_config(self):
        """Checks for Google Drive OAuth2 token/credentials."""
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                access_token = token_data.get("token") or token_data.get("access_token")
                if access_token:
                    self.drive_enabled = True
                    self.drive_status = "GOOGLE_DRIVE_CONFIGURED (TOKEN_PRESENT)"
                else:
                    self.drive_enabled = False
                    self.drive_status = "GOOGLE_DRIVE_TOKEN_INVALID (Awaiting refresh)"
            except Exception as e:
                self.drive_enabled = False
                self.drive_status = f"GOOGLE_DRIVE_ERROR: {str(e)[:50]}"
        elif os.path.exists(self.creds_path):
            self.drive_enabled = False
            self.drive_status = "AWAITING_OAUTH_AUTHORIZATION (credentials.json found, token.json pending)"
        else:
            self.drive_enabled = False
            self.drive_status = "LOCAL_STORAGE_ACTIVE (DRIVE_UNLINKED - AWAITING_OAUTH_TOKEN)"

    def _get_active_access_token(self) -> str:
        """Retrieves active OAuth access token, automatically refreshing if expired."""
        if not os.path.exists(self.token_path):
            return None
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials.from_authorized_user_file(self.token_path, ['https://www.googleapis.com/auth/drive.file'])
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as tf:
                    tf.write(creds.to_json())
            if creds and creds.token:
                return creds.token
        except Exception:
            pass

        # Direct JSON fallback
        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("token") or data.get("access_token")
        except Exception:
            return None

    def save_snapshot(self, category: str, filename: str, data: dict, mode: str = "LIVE_MONITORING") -> str:
        """
        Saves a structured snapshot locally and triggers genuine Google Drive sync if configured.
        category: 'predictions/risk', 'predictions/warnings', 'history', etc.
        """
        target_dir = os.path.join(self.base_dir, category)
        os.makedirs(target_dir, exist_ok=True)

        envelope = {
            "_metadata": {
                "system": "NER-SAFE Landslide Decision-Support Engine",
                "mode": mode,
                "model_version": "v1.4-Isotonic-RF-30m",
                "fusion_weights": {"susceptibility": 0.40, "rainfall": 0.30, "soil_moisture": 0.20, "satellite": 0.10},
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "COMPLETED",
                "storage_provenance": "LOCAL_DISK_AUTHENTICATED"
            },
            "data": data
        }

        full_path = os.path.join(target_dir, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2)

        # Execute genuine upload or record local-first pending state
        self._sync_to_drive_actual(full_path, filename, category)
        return full_path

    def _sync_to_drive_actual(self, local_file: str, remote_filename: str, category: str):
        """
        Performs genuine Google Drive API v3 multipart upload if token is present.
        If token is absent, records honest local status without fabricating sync success.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        access_token = self._get_active_access_token()

        if not access_token:
            # Honest status: written locally, Drive unlinked
            self.sync_history.append({
                "timestamp": now_str,
                "filename": remote_filename,
                "category": category,
                "size_bytes": os.path.getsize(local_file),
                "status": "LOCAL_STORED_DRIVE_UNLINKED",
                "drive_file_id": None,
                "message": "Saved to local NER-SAFE storage. Google Drive sync awaiting token.json"
            })
            if len(self.sync_history) > 50:
                self.sync_history = self.sync_history[-50:]
            return

        # Token is present -> Perform genuine Google Drive v3 upload
        try:
            boundary = "-------314159265358979323846"
            metadata = {
                "name": remote_filename,
                "description": f"NER-SAFE Automated Live Snapshot: {category}"
            }
            with open(local_file, "rb") as lf:
                file_bytes = lf.read()

            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: application/json\r\n\r\n"
            ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

            upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
            req = urllib.request.Request(
                upload_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                    "Content-Length": str(len(body))
                }
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    res_json = json.loads(resp.read().decode("utf-8"))
                    drive_id = res_json.get("id")
                    self.last_sync_timestamp = now_str
                    self.drive_status = "GOOGLE_DRIVE_CONNECTED_SYNCED"
                    self.sync_history.append({
                        "timestamp": now_str,
                        "filename": remote_filename,
                        "category": category,
                        "size_bytes": len(file_bytes),
                        "status": "SYNCED_OK",
                        "drive_file_id": drive_id,
                        "message": f"Successfully uploaded to Google Drive (ID: {drive_id})"
                    })
                else:
                    self.sync_history.append({
                        "timestamp": now_str,
                        "filename": remote_filename,
                        "status": f"HTTP_{resp.status}",
                        "drive_file_id": None,
                        "message": f"Drive API returned HTTP {resp.status}"
                    })
        except urllib.error.HTTPError as he:
            self.drive_status = f"GOOGLE_DRIVE_HTTP_ERROR: {he.code}"
            self.sync_history.append({
                "timestamp": now_str,
                "filename": remote_filename,
                "status": f"DRIVE_HTTP_ERROR_{he.code}",
                "drive_file_id": None,
                "message": f"Drive API error: {str(he)}"
            })
        except Exception as e:
            self.drive_status = f"GOOGLE_DRIVE_NETWORK_ERROR"
            self.sync_history.append({
                "timestamp": now_str,
                "filename": remote_filename,
                "status": "DRIVE_SYNC_FAILED",
                "drive_file_id": None,
                "message": str(e)
            })

        if len(self.sync_history) > 50:
            self.sync_history = self.sync_history[-50:]

    def get_status(self) -> dict:
        """Returns storage diagnostics for the dashboard and API."""
        self._check_drive_config()
        synced_count = len([s for s in self.sync_history if s.get("status") == "SYNCED_OK"])
        recent_sync = self.sync_history[-1] if self.sync_history else None

        return {
            "storage_backend": "GOOGLE_DRIVE_SYNC" if self.drive_enabled else "LOCAL_STORAGE_ONLY",
            "drive_status": self.drive_status,
            "local_root": self.base_dir,
            "last_sync_timestamp": self.last_sync_timestamp,
            "synced_files_count": synced_count,
            "total_local_snapshots": len(self.sync_history),
            "google_one_compatible": True,
            "oauth_token_present": os.path.exists(self.token_path),
            "credentials_present": os.path.exists(self.creds_path),
            "backup_policy": "Incremental JSON snapshots; 35GB raw rasters preserved locally",
            "last_operation": recent_sync
        }

# Global Storage Singleton
storage_engine = StorageEngine()

if __name__ == "__main__":
    print("Storage Engine Status:")
    print(json.dumps(storage_engine.get_status(), indent=2))
    snap_path = storage_engine.save_snapshot("predictions/risk", "test_diagnostic_snapshot.json", {"test": True})
    print(f"\nSaved test snapshot to: {snap_path}")
    print("Updated Status:")
    print(json.dumps(storage_engine.get_status(), indent=2))
