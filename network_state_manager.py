"""
NER-SAFE: Network State, Layered Connectivity & Offline Preparedness Manager
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Four-Level Connectivity Hierarchy:
LEVEL 1: Normal internet / mobile data -> Full live dashboard, fresh telemetry, push alerts.
LEVEL 2: Cellular/SMS only (No mobile internet) -> SMS alerts (<=160 chars), compact fallback.
LEVEL 3: Intermittent cellular -> Queued alerts, store-and-forward outbox, delayed sync.
LEVEL 4: NO MOBILE NETWORK AT ALL -> Local offline caching, cached risk maps, offline citizen reports.
         CRITICAL RULE: Server cannot remotely deliver a live alert to an offline device.
         Never claim live connectivity when offline.
         Strictly display: CURRENT RISK: NOT AVAILABLE / AWAITING FRESH DATA.
         LAST KNOWN ASSESSMENT: [Score] (Generated: [Timestamp]).
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Connectivity Levels
LEVEL_1_ONLINE = "ONLINE"
LEVEL_2_SMS_ONLY = "SMS_ONLY"
LEVEL_3_INTERMITTENT = "INTERMITTENT_QUEUED"
LEVEL_4_NO_NETWORK = "OFFLINE"

# Offline Sync States
SYNC_LOCAL_ONLY = "LOCAL_ONLY"
SYNC_QUEUED = "QUEUED"
SYNC_SYNCING = "SYNCING"
SYNC_SYNCED = "SYNCED"
SYNC_FAILED = "SYNC_FAILED"

class NetworkStateManager:
    def __init__(self):
        self.current_state = LEVEL_1_ONLINE
        self.offline_outbox: List[Dict[str, Any]] = []
        self.cached_assessments: Dict[str, Dict[str, Any]] = {}
        self.last_sync_timestamp_utc = datetime.now(timezone.utc).isoformat()

    def set_connectivity_level(self, level: str) -> Dict[str, Any]:
        """Sets simulated or detected connectivity level."""
        valid_levels = [LEVEL_1_ONLINE, LEVEL_2_SMS_ONLY, LEVEL_3_INTERMITTENT, LEVEL_4_NO_NETWORK]
        if level in valid_levels:
            self.current_state = level
        return self.get_connectivity_status()

    def get_connectivity_status(self) -> Dict[str, Any]:
        """Returns structured connectivity state with UI display parameters."""
        descriptions = {
            LEVEL_1_ONLINE: "High-speed mobile data / broadband. Full live stream active.",
            LEVEL_2_SMS_ONLY: "Mobile internet offline. Cellular voice/SMS fallback available.",
            LEVEL_3_INTERMITTENT: "Weak / fluctuating signal. Store-and-forward synchronization queue active.",
            LEVEL_4_NO_NETWORK: "Zero cellular and internet connectivity. Device in local offline mode."
        }

        return {
            "connectivity_level": self.current_state,
            "is_online": self.current_state == LEVEL_1_ONLINE,
            "supports_remote_alert_dispatch": self.current_state in [LEVEL_1_ONLINE, LEVEL_2_SMS_ONLY],
            "requires_offline_fallback": self.current_state in [LEVEL_3_INTERMITTENT, LEVEL_4_NO_NETWORK],
            "description": descriptions.get(self.current_state, ""),
            "pending_sync_count": len(self.offline_outbox),
            "last_successful_sync_utc": self.last_sync_timestamp_utc
        }

    def cache_last_known_assessment(self, hotspot_id: str, assessment_data: Dict[str, Any]):
        """Persists the last verified assessment with its authentic timestamp."""
        self.cached_assessments[hotspot_id] = {
            "hotspot_id": hotspot_id,
            "last_known_data": assessment_data,
            "cached_at_utc": datetime.now(timezone.utc).isoformat(),
            "original_generated_at_utc": assessment_data.get("generated_time_utc", datetime.now(timezone.utc).isoformat())
        }

    def get_display_assessment_for_device(self, hotspot_id: str, is_device_offline: bool) -> Dict[str, Any]:
        """
        Enforces Freshness Rule when device is offline:
        CURRENT RISK: NOT AVAILABLE.
        LAST KNOWN ASSESSMENT: [Score] (Generated: [Timestamp]).
        """
        cached = self.cached_assessments.get(hotspot_id)
        if is_device_offline or self.current_state == LEVEL_4_NO_NETWORK:
            return {
                "hotspot_id": hotspot_id,
                "current_risk": "NOT AVAILABLE",
                "current_risk_status": "WAITING_FOR_DATA_OR_CONNECTIVITY",
                "last_known_assessment": cached.get("last_known_data") if cached else None,
                "last_known_generated_utc": cached.get("original_generated_at_utc") if cached else None,
                "device_mode": "OFFLINE_LOCAL_PREPAREDNESS",
                "disclaimer": (
                    "Live risk assessment unavailable because device is offline. "
                    "Displaying last-known cached assessment with authentic timestamp. Never interpreted as current."
                )
            }
        
        return {
            "hotspot_id": hotspot_id,
            "current_risk": cached.get("last_known_data") if cached else None,
            "device_mode": "ONLINE_LIVE"
        }

    def queue_offline_citizen_report(self, report_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stores citizen reports locally on device when offline.
        Prevents duplicate reports during synchronization.
        """
        client_report_id = report_payload.get("client_report_id", f"OFF-{uuid.uuid4().hex[:8]}")
        
        # Check for existing report in outbox to prevent duplicates
        for item in self.offline_outbox:
            if item.get("client_report_id") == client_report_id:
                return {"status": "ALREADY_QUEUED", "item": item}

        entry = {
            "client_report_id": client_report_id,
            "payload": report_payload,
            "created_offline_at_utc": datetime.now(timezone.utc).isoformat(),
            "sync_status": SYNC_QUEUED
        }
        self.offline_outbox.append(entry)
        return entry

    def synchronize_offline_outbox(self, ingest_callback) -> Dict[str, Any]:
        """
        Synchronizes queued reports when network connectivity returns.
        Safe against duplicates.
        """
        if self.current_state == LEVEL_4_NO_NETWORK:
            return {
                "synchronized": 0,
                "failed": 0,
                "pending": len(self.offline_outbox),
                "message": "Cannot synchronize: Device remains in LEVEL 4 (Offline)."
            }

        synced_count = 0
        failed_count = 0

        for item in list(self.offline_outbox):
            item["sync_status"] = SYNC_SYNCING
            try:
                res = ingest_callback(item["payload"])
                if res.get("status") in ["SUCCESS", "ACCEPTED", "ALREADY_PROCESSED"]:
                    item["sync_status"] = SYNC_SYNCED
                    self.offline_outbox.remove(item)
                    synced_count += 1
                else:
                    item["sync_status"] = SYNC_FAILED
                    failed_count += 1
            except Exception:
                item["sync_status"] = SYNC_FAILED
                failed_count += 1

        self.last_sync_timestamp_utc = datetime.now(timezone.utc).isoformat()
        return {
            "synchronized": synced_count,
            "failed": failed_count,
            "remaining_in_outbox": len(self.offline_outbox),
            "synced_at_utc": self.last_sync_timestamp_utc
        }

network_manager = NetworkStateManager()
