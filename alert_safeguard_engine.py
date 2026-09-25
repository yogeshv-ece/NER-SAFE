"""
NER-SAFE: Alert Safeguards, Fatigue Mitigation & Delivery State Machine
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Safeguards Implemented:
1. Multi-Tier Probability Thresholds with Hysteresis (prevents rapid toggling between tiers)
2. Alert Fatigue Suppression: Suppresses duplicate alerts within minimum re-alert window (e.g. 4 hours)
   unless severity escalates to CRITICAL.
3. Alert Expiry: Strict lifetime on advisories (e.g. 12-24 hours).
4. Human / Field Officer Verification Requirement for High/Critical civilian warnings.
5. Strict Delivery States:
   - GENERATED: Alert created by system logic.
   - QUEUED: Held in server dispatch buffer.
   - SENT: Dispatched to gateway/carrier.
   - DELIVERED: Verifiably received by device (where protocol supports delivery receipts).
   - WAITING_FOR_NETWORK: Device/location has no cellular/internet connection.
   - FAILED: Gateway or carrier rejection.
   - EXPIRED: Horizon elapsed without re-trigger.
"""

import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Alert Delivery States
STATE_GENERATED = "GENERATED"
STATE_QUEUED = "QUEUED"
STATE_SENT = "SENT"
STATE_DELIVERED = "DELIVERED"
STATE_WAITING_FOR_NETWORK = "WAITING_FOR_NETWORK"
STATE_FAILED = "FAILED"
STATE_EXPIRED = "EXPIRED"

# Alert Tiers
TIER_WATCH = "WATCH"
TIER_MODERATE = "MODERATE"
TIER_HIGH = "HIGH"
TIER_CRITICAL = "CRITICAL"

class AlertSafeguardEngine:
    def __init__(self):
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        # Hysteresis margins: Rising threshold vs Falling threshold
        self.thresholds = {
            TIER_CRITICAL: {"rise": 0.70, "fall": 0.60},
            TIER_HIGH:     {"rise": 0.52, "fall": 0.44},
            TIER_MODERATE: {"rise": 0.35, "fall": 0.28},
            TIER_WATCH:    {"rise": 0.00, "fall": 0.00}
        }
        self.suppression_window_hours = 4.0

    def evaluate_alert_tier_with_hysteresis(
        self,
        probability: float,
        previous_tier: Optional[str] = None
    ) -> str:
        """
        Determines alert tier using hysteresis to prevent rapid flickering around threshold boundaries.
        """
        if previous_tier == TIER_CRITICAL:
            if probability >= self.thresholds[TIER_CRITICAL]["fall"]:
                return TIER_CRITICAL
        elif probability >= self.thresholds[TIER_CRITICAL]["rise"]:
            return TIER_CRITICAL

        if previous_tier == TIER_HIGH:
            if probability >= self.thresholds[TIER_HIGH]["fall"]:
                return TIER_HIGH
        elif probability >= self.thresholds[TIER_HIGH]["rise"]:
            return TIER_HIGH

        if previous_tier == TIER_MODERATE:
            if probability >= self.thresholds[TIER_MODERATE]["fall"]:
                return TIER_MODERATE
        elif probability >= self.thresholds[TIER_MODERATE]["rise"]:
            return TIER_MODERATE

        return TIER_WATCH

    def process_alert_candidate(
        self,
        hotspot_id: str,
        forecast_probability: float,
        uncertainty_entropy: float,
        likely_zone: str,
        network_available: bool = True,
        reference_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Applies fatigue safeguards, hysteresis, deduplication, and delivery state tracking.
        """
        ref_time = reference_time_utc or datetime.now(timezone.utc)
        prev_alert = self.active_alerts.get(hotspot_id)
        prev_tier = prev_alert.get("tier") if prev_alert else None

        # Evaluate tier
        tier = self.evaluate_alert_tier_with_hysteresis(forecast_probability, prev_tier)
        
        # Check active alert suppression
        if prev_alert and prev_alert["status"] not in [STATE_EXPIRED, STATE_FAILED]:
            prev_time = datetime.fromisoformat(prev_alert["generated_at_utc"].replace("Z", "+00:00"))
            age_hours = (ref_time - prev_time).total_seconds() / 3600.0

            # Suppress if within window and tier has not escalated
            tier_ranks = {TIER_WATCH: 0, TIER_MODERATE: 1, TIER_HIGH: 2, TIER_CRITICAL: 3}
            if age_hours < self.suppression_window_hours and tier_ranks[tier] <= tier_ranks[prev_alert["tier"]]:
                return {
                    "action": "SUPPRESSED_REPEAT_ALERT",
                    "reason": f"Alert fatigue prevention: Active alert issued {age_hours:.1f}h ago with tier {prev_alert['tier']}.",
                    "active_alert_id": prev_alert["alert_id"],
                    "current_tier": tier
                }

        # Check uncertainty check: High uncertainty reduces uncalibrated broadcast
        requires_field_verification = (tier in [TIER_HIGH, TIER_CRITICAL]) or (uncertainty_entropy > 0.85)

        # Initial delivery state
        if not network_available:
            initial_delivery_state = STATE_WAITING_FOR_NETWORK
        else:
            initial_delivery_state = STATE_GENERATED

        alert_id = f"ALT-{hotspot_id}-{int(ref_time.timestamp())}"
        alert_record = {
            "alert_id": alert_id,
            "hotspot_id": hotspot_id,
            "tier": tier,
            "forecast_probability": forecast_probability,
            "uncertainty_entropy": uncertainty_entropy,
            "likely_zone": likely_zone,
            "requires_field_verification": requires_field_verification,
            "generated_at_utc": ref_time.isoformat(),
            "expires_at_utc": (ref_time + timedelta(hours=12)).isoformat(),
            "delivery_state": initial_delivery_state,
            "status": initial_delivery_state,
            "hysteresis_applied": prev_tier is not None,
            "statutory_authority_disclaimer": "Advisory only. Official statutory evacuation orders issued solely by SDMA/DDMA."
        }

        self.active_alerts[hotspot_id] = alert_record
        self.alert_history.append(alert_record)
        return alert_record

    def update_delivery_state(
        self,
        alert_id: str,
        new_state: str,
        verification_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transitions alert delivery state: GENERATED -> QUEUED -> SENT -> DELIVERED.
        """
        valid_transitions = [
            STATE_GENERATED, STATE_QUEUED, STATE_SENT,
            STATE_DELIVERED, STATE_WAITING_FOR_NETWORK, STATE_FAILED, STATE_EXPIRED
        ]
        if new_state not in valid_transitions:
            return False

        for h_id, rec in self.active_alerts.items():
            if rec["alert_id"] == alert_id:
                rec["delivery_state"] = new_state
                rec["status"] = new_state
                rec["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
                if verification_metadata:
                    rec["delivery_metadata"] = verification_metadata
                return True
        return False

alert_safeguards = AlertSafeguardEngine()
