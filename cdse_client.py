"""
=============================================================================
NER-SAFE: Copernicus Data Space Ecosystem (CDSE) Authenticated Client
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Manages authenticated interactions with the official Copernicus Data
         Space Ecosystem (CDSE) and Sentinel Hub services for SIH 26001:
         1. OAuth2 client credentials token exchange via Keycloak.
         2. Sentinel Hub STAC Catalog discovery & Process API data acquisition
            (Sentinel-2 L2A optical and Sentinel-1 GRD C-band radar).
         3. CDSE OData catalogue discovery of Sentinel-1 Level-1 IW SLC scenes.
         4. Strict security perimeter: NEVER exposes, prints, or logs secrets.
         5. Strict anti-fabrication: records authentic acquisition metrics,
            timestamps, byte sizes, and cryptographic SHA-256 checksums.
=============================================================================
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# CDSE Service Endpoints
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
SH_BASE_URL = "https://sh.dataspace.copernicus.eu"
SH_CATALOG_URL = f"{SH_BASE_URL}/api/v1/catalog/1.0.0"
SH_PROCESS_URL = f"{SH_BASE_URL}/api/v1/process"
CDSE_ODATA_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_ZIPPER_URL = "https://zipper.dataspace.copernicus.eu/odata/v1/Products"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

# Default AOI for North Eastern Region (Meghalaya & Mizoram)
DEFAULT_AOI_WKT = "SRID=4326;POLYGON((89.0 21.0, 94.0 21.0, 94.0 27.0, 89.0 27.0, 89.0 21.0))"
SHELLA_BBOX = [91.60, 25.15, 91.65, 25.20]  # East Khasi Hills hotspot corridor


class CDSEClient:
    """Authenticates and interfaces with Copernicus Data Space Ecosystem APIs."""

    def __init__(self, env_path: Optional[str] = None):
        self.env_path = env_path or os.path.join(PROJECT_ROOT, ".env")
        self._cached_token: Optional[str] = None
        self._token_expiry_utc: Optional[datetime] = None
        self._client_id, self._client_secret = self._read_credentials()

    def _read_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Reads credentials from os.environ or .env file without printing or leaking."""
        cid = os.environ.get("CDSE_CLIENT_ID")
        sec = os.environ.get("CDSE_CLIENT_SECRET")
        if not cid or not sec:
            if os.path.exists(self.env_path):
                try:
                    with open(self.env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                k_str = k.strip()
                                v_str = v.strip().strip("'").strip('"')
                                if k_str == "CDSE_CLIENT_ID" and not cid:
                                    cid = v_str
                                elif k_str == "CDSE_CLIENT_SECRET" and not sec:
                                    sec = v_str
                except Exception:
                    pass
        return cid, sec

    def check_credentials_configured(self) -> bool:
        """Returns True if authentic non-placeholder credentials exist."""
        placeholder_vals = {"", "YOUR_CLIENT_ID", "<YOUR_CLIENT_ID>", "YOUR_CLIENT_SECRET", "<YOUR_CLIENT_SECRET>"}
        return bool(
            self._client_id and self._client_id not in placeholder_vals and not self._client_id.isspace() and
            self._client_secret and self._client_secret not in placeholder_vals and not self._client_secret.isspace()
        )

    def get_auth_token(self, force_refresh: bool = False) -> str:
        """
        Obtains or returns valid OAuth2 Bearer token from CDSE Keycloak.
        Raises RuntimeError if unconfigured or if authentication fails.
        """
        if not self.check_credentials_configured():
            raise RuntimeError("CDSE_CLIENT_ID or CDSE_CLIENT_SECRET unconfigured or placeholder in .env.")

        now_utc = datetime.now(timezone.utc)
        if not force_refresh and self._cached_token and self._token_expiry_utc and now_utc < self._token_expiry_utc:
            return self._cached_token

        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret
        }).encode("utf-8")

        req = urllib.request.Request(
            CDSE_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                token = res.get("access_token")
                expires_in = int(res.get("expires_in", 1800))
                if not token:
                    raise RuntimeError("CDSE token endpoint returned no access_token.")
                self._cached_token = token
                self._token_expiry_utc = now_utc + timedelta(seconds=max(expires_in - 60, 60))
                return token
        except urllib.error.HTTPError as e:
            try:
                err_json = json.loads(e.read().decode("utf-8"))
                msg = err_json.get("error_description") or err_json.get("error") or str(e)
            except Exception:
                msg = str(e)
            raise RuntimeError(f"CDSE OAuth authentication failed (HTTP {e.code}): {msg}")

    def test_sentinel_hub_connectivity(self) -> Dict[str, Any]:
        """Tests authenticated connectivity to Sentinel Hub STAC collections."""
        token = self.get_auth_token()
        url = f"{SH_CATALOG_URL}/collections"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            col_ids = [c.get("id") for c in data.get("collections", [])]
            return {
                "status": "PASS",
                "http_code": resp.status,
                "collections_count": len(col_ids),
                "collections": col_ids
            }

    def discover_sentinel2_l2a(self, bbox: List[float] = SHELLA_BBOX, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries STAC catalog for authentic Sentinel-2 L2A optical scenes."""
        token = self.get_auth_token()
        url = f"{SH_CATALOG_URL}/search"
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=45)
        dt_str = f"{start_utc.strftime('%Y-%m-%dT00:00:00Z')}/{now_utc.strftime('%Y-%m-%dT23:59:59Z')}"

        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": dt_str,
            "limit": limit
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            features = data.get("features", [])
            discovered = []
            for f in features:
                props = f.get("properties", {})
                discovered.append({
                    "product_id": f.get("id"),
                    "datetime": props.get("datetime"),
                    "cloud_cover_percent": props.get("eo:cloud_cover"),
                    "platform": props.get("platform"),
                    "bbox": f.get("bbox")
                })
            return discovered

    def acquire_sentinel2_sample(self, bbox: List[float] = SHELLA_BBOX, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Acquires authentic Sentinel-2 L2A multi-spectral data (B04, B08, B03, SCL)
        via Sentinel Hub Process API. Returns real file path, size, and SHA-256.
        """
        token = self.get_auth_token()
        out_dir = output_dir or os.path.join(PROJECT_ROOT, "test_data_cdse")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "sentinel2_l2a_meghalaya_test.tif")

        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=45)
        payload = {
            "input": {
                "bounds": {"bbox": bbox},
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_utc.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": now_utc.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "maxCloudCoverage": 80
                    }
                }]
            },
            "output": {
                "width": 64,
                "height": 64,
                "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
            },
            "evalscript": """//VERSION=3
function setup() {
    return {
        input: ["B04", "B08", "B03", "SCL"],
        output: { bands: 4, sampleType: "FLOAT32" }
    };
}
function evaluatePixel(sample) {
    return [sample.B04, sample.B08, sample.B03, sample.SCL];
}"""
        }

        req = urllib.request.Request(
            SH_PROCESS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "image/tiff"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            with open(out_path, "wb") as f:
                f.write(content)
            sha = hashlib.sha256(content).hexdigest()
            return {
                "status": "LIVE_VERIFIED",
                "file_path": out_path,
                "size_bytes": len(content),
                "sha256": sha,
                "content_type": resp.headers.get("Content-Type"),
                "acquired_at_utc": now_utc.isoformat()
            }

    def discover_sentinel1_grd(self, bbox: List[float] = SHELLA_BBOX, limit: int = 5) -> List[Dict[str, Any]]:
        """Queries STAC catalog for authentic Sentinel-1 GRD scenes."""
        token = self.get_auth_token()
        url = f"{SH_CATALOG_URL}/search"
        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=30)
        payload = {
            "collections": ["sentinel-1-grd"],
            "bbox": bbox,
            "datetime": f"{start_utc.strftime('%Y-%m-%dT00:00:00Z')}/{now_utc.strftime('%Y-%m-%dT23:59:59Z')}",
            "limit": limit
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            features = data.get("features", [])
            discovered = []
            for f in features:
                props = f.get("properties", {})
                discovered.append({
                    "product_id": f.get("id"),
                    "datetime": props.get("datetime"),
                    "polarization": props.get("polarization"),
                    "orbit_direction": props.get("sat:orbit_state"),
                    "bbox": f.get("bbox")
                })
            return discovered

    def acquire_sentinel1_grd_sample(self, bbox: List[float] = SHELLA_BBOX, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Acquires authentic Sentinel-1 C-SAR GRD radar backscatter data (VV, VH)
        via Sentinel Hub Process API. Returns real file path, size, and SHA-256.
        """
        token = self.get_auth_token()
        out_dir = output_dir or os.path.join(PROJECT_ROOT, "test_data_cdse")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "sentinel1_grd_meghalaya_test.tif")

        now_utc = datetime.now(timezone.utc)
        start_utc = now_utc - timedelta(days=30)
        payload = {
            "input": {
                "bounds": {"bbox": bbox},
                "data": [{
                    "type": "sentinel-1-grd",
                    "dataFilter": {
                        "timeRange": {
                            "from": start_utc.strftime("%Y-%m-%dT00:00:00Z"),
                            "to": now_utc.strftime("%Y-%m-%dT23:59:59Z")
                        },
                        "acquisitionMode": "IW",
                        "polarization": "DV"
                    },
                    "processing": {
                        "orthorectify": True,
                        "backCoeff": "GAMMA0_ELLIPSOID"
                    }
                }]
            },
            "output": {
                "width": 64,
                "height": 64,
                "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]
            },
            "evalscript": """//VERSION=3
function setup() {
    return {
        input: ["VV", "VH"],
        output: { bands: 2, sampleType: "FLOAT32" }
    };
}
function evaluatePixel(sample) {
    return [sample.VV, sample.VH];
}"""
        }

        req = urllib.request.Request(
            SH_PROCESS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "image/tiff"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            with open(out_path, "wb") as f:
                f.write(content)
            sha = hashlib.sha256(content).hexdigest()
            return {
                "status": "LIVE_VERIFIED",
                "file_path": out_path,
                "size_bytes": len(content),
                "sha256": sha,
                "content_type": resp.headers.get("Content-Type"),
                "acquired_at_utc": now_utc.isoformat()
            }

    def discover_sentinel1_slc_odata(self, top: int = 15) -> List[Dict[str, Any]]:
        """Queries official CDSE OData API for authentic Sentinel-1 IW SLC scenes intersecting NER AOI."""
        token = self.get_auth_token()
        filter_expr = f"Collection/Name eq 'SENTINEL-1' and contains(Name,'SLC') and OData.CSC.Intersects(area=geography'{DEFAULT_AOI_WKT}')"
        params = {
            "$filter": filter_expr,
            "$top": str(top),
            "$orderby": "ContentDate/Start desc"
        }
        url = f"{CDSE_ODATA_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("value", [])

    def test_slc_download_access(self, product_id: str) -> Dict[str, Any]:
        """
        Tests authentic CDSE bulk product zipper endpoint with HTTP Range request.
        Reports exact status and error code without synthetic simulation.
        """
        token = self.get_auth_token()
        zip_url = f"{CDSE_ZIPPER_URL}({product_id})/$value"
        req = urllib.request.Request(zip_url, headers={
            "Authorization": f"Bearer {token}",
            "Range": "bytes=0-1023"
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                chunk = resp.read()
                return {
                    "download_status": "DOWNLOAD_READY",
                    "http_code": resp.status,
                    "bytes_received": len(chunk)
                }
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                code = err_body.get("code", "UNKNOWN")
                msg = err_body.get("message", str(e))
            except Exception:
                code = "HTTP_ERROR"
                msg = str(e)
            return {
                "download_status": "AUTHENTICATED_BUT_ACQUISITION_FAILED",
                "http_code": e.code,
                "error_code": code,
                "error_message": msg,
                "diagnostic": "Sentinel Hub OAuth credentials (sh-*) are authorized for Process API, STAC, and OData metadata, but bulk ZIP archive download requires CDSE download role or user password flow."
            }


cdse_client = CDSEClient()

if __name__ == "__main__":
    print("Testing CDSE Client...")
    print("Credentials configured:", cdse_client.check_credentials_configured())
    sh_res = cdse_client.test_sentinel_hub_connectivity()
    print("Sentinel Hub test:", sh_res["status"])
    s2_res = cdse_client.acquire_sentinel2_sample()
    print("Sentinel-2 sample:", s2_res["status"], s2_res["size_bytes"], "bytes")
    s1_res = cdse_client.acquire_sentinel1_grd_sample()
    print("Sentinel-1 GRD sample:", s1_res["status"], s1_res["size_bytes"], "bytes")
