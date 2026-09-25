"""
NER-SAFE: Local Edge Risk Mode & Ground Sensor Alert Engine
Operates during Level 4 communications loss where central servers and ML models are disconnected.

Core Scientific Rules:
1. Cached central risk is strictly marked 'LAST SYNCHRONIZED RISK' (with timestamp);
   never masquerades as 'CURRENT RISK'.
2. Local sensor alerts are generated from real slope readings and explicitly tagged
   'LOCAL SENSOR ALERT'.
3. Implements hysteresis and persistence to prevent alert toggling.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from ground_sensor_interface import ground_sensor_adapter, SENSOR_TILT, SENSOR_SOIL_MOISTURE, SENSOR_RAIN_GAUGE
from zero_network_manager import zero_network_manager

# Alert Tiers
ALERT_CRITICAL = "CRITICAL"
ALERT_HIGH = "HIGH"
ALERT_WARNING = "WARNING"
ALERT_NORMAL = "NORMAL"

class LocalSensorAlertEngine:
    def __init__(self):
        self.active_alert_tier = ALERT_NORMAL
        self.last_trigger_time: Optional[datetime] = None
        self.cooldown_minutes = 15
        self.alert_history: List[Dict[str, Any]] = []

    def evaluate_local_slope_state(self, zone_id: str = "SLOPE-MEG-001") -> Dict[str, Any]:
        """Evaluates local ground sensor telemetry to detect rapid physical slope movement.
        Enforces conservative heuristic trigger thresholds.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Inspect recent tilt readings
        tilt_readings = ground_sensor_adapter.get_latest_readings(SENSOR_TILT)
        soil_readings = ground_sensor_adapter.get_latest_readings(SENSOR_SOIL_MOISTURE)
        rain_readings = ground_sensor_adapter.get_latest_readings(SENSOR_RAIN_GAUGE)

        latest_tilt = tilt_readings[0]["measurement"] if tilt_readings else 0.0
        latest_soil = soil_readings[0]["measurement"] if soil_readings else 0.0
        latest_rain = rain_readings[0]["measurement"] if rain_readings else 0.0

        trigger_reasons = []
        tier = ALERT_NORMAL

        # Rule A: Rapid Slope Tilt (Kinematic Displacement)
        if latest_tilt >= 2.5:
            tier = ALERT_CRITICAL
            trigger_reasons.append(f"Critical slope tilt detected: {latest_tilt:.2f}° (Threshold >= 2.5°)")
        elif latest_tilt >= 1.2:
            tier = ALERT_HIGH if tier != ALERT_CRITICAL else tier
            trigger_reasons.append(f"Significant slope tilt displacement: {latest_tilt:.2f}° (Threshold >= 1.2°)")
        elif latest_tilt >= 0.5:
            tier = ALERT_WARNING if tier == ALERT_NORMAL else tier
            trigger_reasons.append(f"Minor slope creep tilt: {latest_tilt:.2f}° (Threshold >= 0.5°)")

        # Rule B: Severe Soil Hydrologic Saturation
        if latest_soil >= 92.0:
            tier = ALERT_CRITICAL if latest_tilt >= 1.0 else ALERT_HIGH
            trigger_reasons.append(f"Near-complete soil saturation: {latest_soil:.1f}% (Threshold >= 92%)")
        elif latest_soil >= 85.0:
            tier = ALERT_HIGH if tier != ALERT_CRITICAL else tier
            trigger_reasons.append(f"High soil saturation: {latest_soil:.1f}% (Threshold >= 85%)")

        # Rule C: Extreme Precipitation Intensity
        if latest_rain >= 40.0:
            tier = ALERT_CRITICAL if tier in (ALERT_HIGH, ALERT_CRITICAL) else ALERT_HIGH
            trigger_reasons.append(f"Extreme localized rainfall rate: {latest_rain:.1f} mm/h")

        # Apply Hysteresis: Maintain active alert until cooldown expires
        if self.last_trigger_time and tier < self.active_alert_tier:
            elapsed = (now - self.last_trigger_time).total_seconds() / 60.0
            if elapsed < self.cooldown_minutes:
                tier = self.active_alert_tier
                trigger_reasons.append(f"Hysteresis lock active ({self.cooldown_minutes - elapsed:.1f} min remaining)")

        # Update state
        if tier != ALERT_NORMAL:
            self.last_trigger_time = now
            self.active_alert_tier = tier
        else:
            self.active_alert_tier = ALERT_NORMAL

        # Actuator dispatch on Critical/High
        actuator_dispatch = None
        if tier == ALERT_CRITICAL:
            actuator_dispatch = zero_network_manager.dispatch_local_actuator(
                actuator_type="LOCAL_SIREN_TRIGGER",
                alert_tier=tier,
                message=f"EVACUATION WARNING: Slope {zone_id} critical movement. Tilt: {latest_tilt:.2f}°, Soil: {latest_soil:.1f}%.",
                zone_id=zone_id
            )
        elif tier == ALERT_HIGH:
            actuator_dispatch = zero_network_manager.dispatch_local_actuator(
                actuator_type="LOCAL_BEACON",
                alert_tier=tier,
                message=f"HAZARD WATCH: Slope {zone_id} high hydrologic saturation. Tilt: {latest_tilt:.2f}°, Soil: {latest_soil:.1f}%.",
                zone_id=zone_id
            )

        edge_alert = {
            "mode": "LOCAL_EDGE_MODE",
            "alert_type": "LOCAL SENSOR ALERT" if tier != ALERT_NORMAL else "NORMAL_MONITORING",
            "zone_id": zone_id,
            "evaluated_tier": tier,
            "reasons": trigger_reasons,
            "timestamp_utc": now.isoformat(),
            "sensor_telemetry_snapshot": {
                "tilt_deg": latest_tilt,
                "soil_moisture_pct": latest_soil,
                "rainfall_rate_mm_h": latest_rain
            },
            "actuator_event": actuator_dispatch,
            "central_risk_status": {
                "label": "LAST SYNCHRONIZED RISK",
                "last_synchronized_timestamp": zero_network_manager.last_central_sync_utc,
                "current_risk_claim": "UNAVAILABLE_OFFLINE",
                "disclaimer": "Central ML risk calculation is disconnected. Showing last verified baseline."
            }
        }

        self.alert_history.append(edge_alert)
        return edge_alert

# Global Singleton Alert Engine
local_sensor_alert_engine = LocalSensorAlertEngine()
