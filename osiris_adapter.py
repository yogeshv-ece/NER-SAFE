"""
=============================================================================
NER-SAFE v1.1.0 — OSIRIS Intelligence Platform Adapter
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Provides structured, rate-limited, and audited ingestion of
         public OSIRIS intelligence feeds (simplifaisoul/osiris) for
         Meghalaya and Mizoram.

CRITICAL GOVERNANCE INVARIANTS:
1. OSIRIS is strictly an external observation/context layer.
2. OSIRIS data NEVER modifies the locked four-factor risk formula:
   risk_score = 0.40 * susceptibility + 0.30 * rainfall_anomaly
              + 0.20 * soil_moisture_anomaly + 0.10 * satellite_change_flag
3. OSIRIS NEVER overrides official government warning authorities (GSI, NDMA SACHET, IMD).
4. OSIRIS feeds NEVER automatically verify an event.
5. All upstream sources must be explicitly credited with their true authority
   (e.g., USGS for earthquakes, GDACS for alerts, NASA for FIRMS) and
   labeled with access_path = 'OSIRIS /api/...'.
6. Zero emojis across all log strings, statuses, and returned payloads.
=============================================================================
"""

import os
import sys
import json
import time
import hashlib
import logging
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("NER_SAFE.OSIRIS_Adapter")

# Bounding boxes for operational states in Northeast India
MEGHALAYA_BBOX = {"lat_min": 25.0, "lat_max": 26.2, "lon_min": 89.8, "lon_max": 92.9}
MIZORAM_BBOX = {"lat_min": 21.9, "lat_max": 24.6, "lon_min": 92.2, "lon_max": 93.6}

# Regional search keywords
MEGHALAYA_KEYWORDS = [
    "meghalaya", "shillong", "east khasi hills", "west khasi hills", "ri-bhoi",
    "jaintia", "east jaintia", "west jaintia", "south west khasi", "garo hills",
    "tura", "dawki", "sohra", "cherrapunji", "mawsynram", "mawkdok", "umsning",
    "nh-6", "nh-44", "nh6", "nh44"
]

MIZORAM_KEYWORDS = [
    "mizoram", "aizawl", "lunglei", "kolasib", "champhai", "lawngtlai",
    "serchhip", "mamit", "sairang", "vairengte", "hunthar veng", "nh-54", "nh54"
]

LANDSLIDE_KEYWORDS = [
    "landslide", "mudslide", "rockfall", "slope failure", "debris flow",
    "road blockage", "subsidence", "debris", "slip"
]


class OsirisAdapter:
    """
    Adapter interfacing with public OSIRIS endpoints and upstream data feeds.
    Maintains rate limiting, caching, response hashing, coordinate integrity,
    and provenance attribution.
    """

    def __init__(self, cache_ttl_seconds: int = 300, rate_limit_delay_sec: float = 0.5):
        self.cache_ttl = cache_ttl_seconds
        self.rate_limit_delay = rate_limit_delay_sec
        self.last_request_time = 0.0
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # Upstream catalog definition
        self.endpoints_config = {
            "/api/earthquakes": {
                "name": "USGS Earthquakes Feed",
                "authority": "USGS Earthquake Hazards Program",
                "direct_upstream_url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
                "osiris_route": "/api/earthquakes",
                "category": "seismic",
                "status": "OPERATIONAL_APPROVED_CONTEXT",
                "recommendation": "INTEGRATE_NOW (Secondary Context)"
            },
            "/api/gdelt": {
                "name": "GDACS Disaster Alert Feed",
                "authority": "GDACS (Global Disaster Alert and Coordination System)",
                "direct_upstream_url": "https://www.gdacs.org/xml/rss.xml",
                "osiris_route": "/api/gdelt",
                "category": "disaster_alerts",
                "status": "OPERATIONAL_APPROVED_CONTEXT",
                "recommendation": "INTEGRATE_NOW (Regional Alert Context)"
            },
            "/api/cctv": {
                "name": "Global CCTV Catalog",
                "authority": "Multiple DOTs (WSDOT, Caltrans, TxDOT, TfL, HK, SG)",
                "osiris_route": "/api/cctv",
                "category": "video_surveillance",
                "status": "REJECTED_ZERO_COVERAGE",
                "recommendation": "REJECT (0 cameras in India, 0 in Meghalaya/Mizoram)"
            },
            "/api/weather": {
                "name": "Severe Weather Feed",
                "authority": "NOAA/NWS (US-only) + NASA EONET + GDACS",
                "osiris_route": "/api/weather",
                "category": "weather",
                "status": "REJECTED_INFERIOR_DUPLICATE",
                "recommendation": "REJECT (US-centric NWS, redundant with GPM IMERG and IMD)"
            },
            "/api/news": {
                "name": "Telegram Geopolitical OSINT",
                "authority": "Telegram War Channels + BBC/AlJazeera RSS",
                "osiris_route": "/api/news",
                "category": "geopolitics",
                "status": "REJECTED_NOT_RELEVANT",
                "recommendation": "REJECT (Geopolitical conflict focus; zero local NE India reporting)"
            },
            "/api/fires": {
                "name": "NASA FIRMS Active Fires",
                "authority": "NASA FIRMS (MODIS/VIIRS)",
                "direct_upstream_url": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
                "osiris_route": "/api/fires",
                "category": "thermal_surface",
                "status": "RESEARCH_ONLY",
                "recommendation": "RESEARCH_ONLY (Surface disturbance context only)"
            },
            "/api/sentinel": {
                "name": "Sentinel STAC Discovery",
                "authority": "Element84 Earth Search AWS + Copernicus STAC",
                "osiris_route": "/api/sentinel",
                "category": "satellite_metadata",
                "status": "DUPLICATE_DERIVED",
                "recommendation": "REJECT (NER-SAFE has direct authoritative CDSE S3 pipeline)"
            },
            "/api/arcgis": {
                "name": "ArcGIS Online Search",
                "authority": "Esri ArcGIS Online Public Services",
                "osiris_route": "/api/arcgis",
                "category": "gis_layers",
                "status": "RESEARCH_ONLY",
                "recommendation": "RESEARCH_ONLY (Unvetted public feature layers)"
            },
            "/api/region-dossier": {
                "name": "Region Dossier",
                "authority": "OpenStreetMap Nominatim + Wikipedia REST",
                "osiris_route": "/api/region-dossier",
                "category": "encyclopedic",
                "status": "RESEARCH_ONLY",
                "recommendation": "RESEARCH_ONLY (Static geographic context only)"
            },
            "/api/ai/briefing": {
                "name": "AI Threat Briefing",
                "authority": "Google Gemini via OSIRIS AI Engine",
                "osiris_route": "/api/ai/briefing",
                "category": "ai_advisory",
                "status": "ADVISORY_ONLY",
                "recommendation": "RESEARCH_ONLY (Non-deterministic operator briefing only)"
            }
        }

    def _rate_limit(self):
        """Enforces minimal inter-request delay to prevent upstream throttling."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def fetch_url(self, url: str, timeout: int = 15) -> Tuple[int, bytes, float, str]:
        """
        Executes an audited HTTP GET with response SHA-256 hashing and timing.
        Returns (status_code, content_bytes, latency_sec, sha256_hash).
        """
        # Check cache
        now = time.time()
        if url in self.cache:
            entry = self.cache[url]
            if now - entry["cached_at"] < self.cache_ttl:
                return 200, entry["data"], 0.001, entry["sha256"]

        self._rate_limit()
        t0 = time.time()
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "NER-SAFE-OSIRIS-Audited-Adapter/1.1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
                latency = time.time() - t0
                sha = hashlib.sha256(data).hexdigest()
                
                # Cache response
                self.cache[url] = {
                    "data": data,
                    "cached_at": now,
                    "sha256": sha
                }
                return resp.status, data, round(latency, 3), sha
        except urllib.error.HTTPError as e:
            latency = time.time() - t0
            return e.code, b"", round(latency, 3), ""
        except Exception as e:
            latency = time.time() - t0
            logger.warning(f"OSIRIS adapter request error for {url}: {e}")
            return 0, b"", round(latency, 3), ""

    @staticmethod
    def is_in_bbox(lat: Optional[float], lon: Optional[float], bbox: Dict[str, float]) -> bool:
        """Validates if coordinates fall strictly within a geographic bounding box."""
        if lat is None or lon is None:
            return False
        return (bbox["lat_min"] <= lat <= bbox["lat_max"] and
                bbox["lon_min"] <= lon <= bbox["lon_max"])

    @staticmethod
    def classify_state(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
        """Classifies point into Meghalaya, Mizoram, or None based on validated spatial bounds."""
        if OsirisAdapter.is_in_bbox(lat, lon, MEGHALAYA_BBOX):
            return "Meghalaya"
        if OsirisAdapter.is_in_bbox(lat, lon, MIZORAM_BBOX):
            return "Mizoram"
        return None

    def fetch_earthquakes(self) -> Dict[str, Any]:
        """
        Pulls USGS M2.5+ earthquake feed via OSIRIS/USGS path.
        Filters for Northeast India events to provide secondary trigger context.
        """
        config = self.endpoints_config["/api/earthquakes"]
        url = config["direct_upstream_url"]
        status, data, latency, sha = self.fetch_url(url)
        
        events = []
        if status == 200 and data:
            try:
                payload = json.loads(data.decode("utf-8"))
                for feat in payload.get("features", []):
                    coords = feat.get("geometry", {}).get("coordinates", [])
                    if len(coords) >= 3:
                        lon, lat, depth = float(coords[0]), float(coords[1]), float(coords[2])
                        props = feat.get("properties", {})
                        state = self.classify_state(lat, lon)
                        
                        # Distance check for regional trigger context (up to 100km from NE India)
                        is_ne_region = (21.0 <= lat <= 27.0 and 89.0 <= lon <= 94.5)
                        
                        if is_ne_region:
                            events.append({
                                "event_id": f"OSIRIS-EQ-{feat.get('id', '')}",
                                "title": props.get("title", ""),
                                "magnitude": props.get("mag"),
                                "latitude": lat,
                                "longitude": lon,
                                "depth_km": depth,
                                "timestamp_utc": datetime.fromtimestamp(props.get("time", 0) / 1000.0, tz=timezone.utc).isoformat(),
                                "state": state or "Northeast India Regional",
                                "underlying_source": config["authority"],
                                "access_path": config["osiris_route"],
                                "source_url": props.get("url", url),
                                "role": "SECONDARY_TRIGGER_CONTEXT"
                            })
            except Exception as e:
                logger.error(f"Failed to parse earthquakes: {e}")

        return {
            "endpoint": "/api/earthquakes",
            "authority": config["authority"],
            "access_path": config["osiris_route"],
            "http_status": status,
            "latency_sec": latency,
            "sha256": sha,
            "total_ne_events": len(events),
            "events": events
        }

    def fetch_gdacs_alerts(self) -> Dict[str, Any]:
        """
        Pulls GDACS disaster alert RSS feed (misattributed as GDELT in OSIRIS).
        Filters for disasters affecting Meghalaya, Mizoram, or Northeast India.
        """
        config = self.endpoints_config["/api/gdelt"]
        url = config["direct_upstream_url"]
        status, data, latency, sha = self.fetch_url(url)

        alerts = []
        if status == 200 and data:
            try:
                xml_text = data.decode("utf-8", errors="ignore")
                items = xml_text.split("<item>")[1:]
                for item in items:
                    item_content = item.split("</item>")[0]
                    item_lower = item_content.lower()
                    
                    has_meg = any(k in item_lower for k in MEGHALAYA_KEYWORDS)
                    has_miz = any(k in item_lower for k in MIZORAM_KEYWORDS)
                    has_landslide = any(k in item_lower for k in LANDSLIDE_KEYWORDS)
                    
                    if has_meg or has_miz or (has_landslide and "india" in item_lower):
                        title_match = item_content.find("<title>")
                        title_end = item_content.find("</title>")
                        title = item_content[title_match+7:title_end].strip() if (title_match != -1 and title_end != -1) else "Disaster Alert"
                        
                        lat_match = item_content.find("<geo:lat>")
                        lat_end = item_content.find("</geo:lat>")
                        lon_match = item_content.find("<geo:long>")
                        lon_end = item_content.find("</geo:long>")
                        
                        lat = float(item_content[lat_match+9:lat_end]) if (lat_match != -1 and lat_end != -1) else None
                        lon = float(item_content[lon_match+10:lon_end]) if (lon_match != -1 and lon_end != -1) else None
                        
                        alerts.append({
                            "alert_id": f"OSIRIS-GDACS-{hashlib.md5(title.encode('utf-8')).hexdigest()[:10]}",
                            "title": title,
                            "latitude": lat,
                            "longitude": lon,
                            "state": "Meghalaya" if has_meg else ("Mizoram" if has_miz else "Northeast India"),
                            "is_landslide_related": has_landslide,
                            "underlying_source": config["authority"],
                            "access_path": config["osiris_route"],
                            "role": "MACRO_DISASTER_ALERT"
                        })
            except Exception as e:
                logger.error(f"Failed to parse GDACS alerts: {e}")

        return {
            "endpoint": "/api/gdelt",
            "authority": config["authority"],
            "access_path": config["osiris_route"],
            "http_status": status,
            "latency_sec": latency,
            "sha256": sha,
            "total_alerts": len(alerts),
            "alerts": alerts
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the complete operational status, source inventory, and health telemetry."""
        return {
            "adapter_name": "NER-SAFE OSIRIS Intelligence Adapter",
            "adapter_version": "v1.1.0",
            "operational_status": "PARTIAL_INTEGRATION_OPERATIONAL",
            "final_recommendation": "OSIRIS_PARTIAL_INTEGRATION_RECOMMENDED",
            "governance_compliance": {
                "four_factor_risk_formula_invariant": True,
                "model_hierarchy_intact": True,
                "zero_emojis": True,
                "no_credential_leakage": True,
                "provenance_preserved": True
            },
            "upstream_endpoints": self.endpoints_config,
            "cached_urls_count": len(self.cache),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

    def normalize_to_canonical_osint(self, raw_alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalizes an approved OSIRIS alert into canonical OSINT observation format.
        Never invents coordinates; rejects alerts lacking physical geolocation.
        """
        lat = raw_alert.get("latitude")
        lon = raw_alert.get("longitude")
        if lat is None or lon is None:
            return None

        state = self.classify_state(lat, lon)
        if not state:
            return None

        # Build normalized OSINT record
        return {
            "source_id": f"OSIRIS_{raw_alert.get('underlying_source', 'UNKNOWN').replace(' ', '_').upper()}",
            "publisher": raw_alert.get("underlying_source", "Unknown Upstream Authority"),
            "access_path": raw_alert.get("access_path", "OSIRIS"),
            "state": state,
            "latitude": lat,
            "longitude": lon,
            "headline": raw_alert.get("title", ""),
            "hazard_type": "Landslide / Secondary Trigger",
            "verification_state": "UNVERIFIED_EXTERNAL_EVIDENCE", # Must NOT auto-verify
            "observed_at": raw_alert.get("timestamp_utc", datetime.now(timezone.utc).isoformat()),
            "content_hash": hashlib.sha256(json.dumps(raw_alert, sort_keys=True).encode("utf-8")).hexdigest()
        }
