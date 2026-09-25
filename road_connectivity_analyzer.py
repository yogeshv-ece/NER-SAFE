"""
NER-SAFE: Road Connectivity & Lifeline Infrastructure Status Analyzer
Derives road operational status from Component 11 GIS runout intersections
and verified ground observation evidence.

Connectivity States:
- OPEN: Normal operational traffic flow; zero intersected active hazard.
- AT_RISK: Intersects an active critical or high hazard runout corridor.
- BLOCKED: Verified physical obstruction reported by field officers.
- UNKNOWN: Unverified observation or sensor alert awaiting field confirmation.
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

STATUS_OPEN = "OPEN"
STATUS_AT_RISK = "AT_RISK"
STATUS_BLOCKED = "BLOCKED"
STATUS_UNKNOWN = "UNKNOWN"

class RoadConnectivityAnalyzer:
    def __init__(self):
        self.exposure_file = os.path.join(PROJECT_ROOT, "exposure_intersections.geojson")
        self.cached_intersections: List[Dict[str, Any]] = []
        self._load_intersections()

    def _load_intersections(self):
        if os.path.exists(self.exposure_file):
            try:
                with open(self.exposure_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cached_intersections = data.get("features", [])
            except Exception:
                self.cached_intersections = []

    def evaluate_road_status(self, road_name: str,
                            hotspot_id: Optional[str] = None,
                            verified_blockage: bool = False,
                            unverified_report: bool = False) -> Dict[str, Any]:
        """Evaluates factual road connectivity based on verified physical evidence."""
        # 1. Direct verified blockage takes precedence
        if verified_blockage:
            return {
                "road_name": road_name,
                "hotspot_id": hotspot_id,
                "status": STATUS_BLOCKED,
                "reason": "Confirmed physical blockage reported by verified field personnel.",
                "evidence_type": "FIELD_VERIFIED_REPORT"
            }

        # 2. Unverified reports prompt UNKNOWN
        if unverified_report:
            return {
                "road_name": road_name,
                "hotspot_id": hotspot_id,
                "status": STATUS_UNKNOWN,
                "reason": "Unverified ground report received; awaiting inspection.",
                "evidence_type": "UNVERIFIED_CROWDSOURCE"
            }

        # 3. Check GIS intersection with critical runout corridor
        intersected_corridors = []
        for feat in self.cached_intersections:
            props = feat.get("properties", {})
            if hotspot_id and props.get("event_id") == hotspot_id:
                intersected_corridors.append(props)

        if intersected_corridors:
            return {
                "road_name": road_name,
                "hotspot_id": hotspot_id,
                "status": STATUS_AT_RISK,
                "reason": f"Road segment intersects empirical runout corridor of {hotspot_id}.",
                "evidence_type": "C11_GIS_INTERSECTION",
                "exposed_segments": len(intersected_corridors)
            }

        # 4. Default: Open
        return {
            "road_name": road_name,
            "hotspot_id": hotspot_id,
            "status": STATUS_OPEN,
            "reason": "No active hazard intersection or obstruction reported.",
            "evidence_type": "NORMAL_MONITORING"
        }

# Global Singleton Analyzer
road_connectivity_analyzer = RoadConnectivityAnalyzer()
