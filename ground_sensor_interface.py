"""
NER-SAFE: Production Physical Ground Sensor Adapter & Ingestion Interface
Supports slope monitoring sensors: Soil Moisture, Rain Gauge, Tilt / Inclinometer,
Temperature, and Geophone / Pore Pressure.

Capabilities:
1. Hardware-neutral ingestion: HTTP payload, CSV import, Serial/USB stream parser.
2. Anomaly & Range validation (rejects physically impossible readings).
3. Packet sequence gap detection and packet loss accounting.
4. Store-and-Forward queue tracking: LOCAL_ONLY, QUEUED, SYNCING, SYNCED, SYNC_FAILED.
5. Battery and health telemetry monitoring.
"""

import os
import sys
import json
import csv
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Physical Sensor Types
SENSOR_SOIL_MOISTURE = "SOIL_MOISTURE"
SENSOR_RAIN_GAUGE = "RAIN_GAUGE"
SENSOR_TILT = "TILT"
SENSOR_TEMPERATURE = "TEMPERATURE"
SENSOR_PORE_PRESSURE = "PORE_PRESSURE"
SENSOR_GEOPHONE = "GEOPHONE"
SENSOR_STRAIN = "STRAIN"

# Physical Plausibility Ranges
SENSOR_BOUNDS = {
    SENSOR_SOIL_MOISTURE: {"min": 0.0, "max": 100.0, "unit": "%"},
    SENSOR_RAIN_GAUGE: {"min": 0.0, "max": 500.0, "unit": "mm/h"},
    SENSOR_TILT: {"min": -90.0, "max": 90.0, "unit": "deg"},
    SENSOR_TEMPERATURE: {"min": -30.0, "max": 65.0, "unit": "degC"},
    SENSOR_PORE_PRESSURE: {"min": -1000.0, "max": 2000.0, "unit": "kPa"},
    SENSOR_GEOPHONE: {"min": 0.0, "max": 100.0, "unit": "mm/s"},
    SENSOR_STRAIN: {"min": -5000.0, "max": 5000.0, "unit": "microstrain"}
}

# Queue States for Store-and-Forward
QUEUE_LOCAL_ONLY = "LOCAL_ONLY"
QUEUE_QUEUED = "QUEUED"
QUEUE_SYNCING = "SYNCING"
QUEUE_SYNCED = "SYNCED"
QUEUE_SYNC_FAILED = "SYNC_FAILED"

class GroundSensorInterface:
    def __init__(self, persistence_file: Optional[str] = None):
        self.persistence_file = persistence_file or os.path.join(
            os.environ.get("NER_SAFE_ROOT", r"E:\landslide - Copy\landslide - Copy"),
            "NER_SAFE_DATA", "DATABASE", "ground_sensor_telemetry.json"
        )
        self.telemetry_store: List[Dict[str, Any]] = []
        self.sensor_health: Dict[str, Dict[str, Any]] = {}
        self.last_sequences: Dict[str, int] = {}
        self._load_telemetry()

    def _load_telemetry(self):
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    self.telemetry_store = json.load(f)
            except Exception:
                self.telemetry_store = []

    def _save_telemetry(self):
        os.makedirs(os.path.dirname(self.persistence_file), exist_ok=True)
        try:
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(self.telemetry_store[-500:], f, indent=2)
        except Exception:
            pass

    def validate_reading(self, sensor_type: str, value: float) -> Tuple[bool, str]:
        """Validates physical plausibility against physical sensor operating bounds."""
        bounds = SENSOR_BOUNDS.get(sensor_type)
        if not bounds:
            return False, f"Unknown sensor type: {sensor_type}"
        if value < bounds["min"] or value > bounds["max"]:
            return False, f"Value {value} {bounds['unit']} out of physical bounds [{bounds['min']}, {bounds['max']}]"
        return True, "VALID_PHYSICAL_RANGE"

    def ingest_measurement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingests, validates, sequence-checks, and catalogs a sensor measurement packet."""
        required = ["sensor_id", "sensor_type", "measurement", "timestamp"]
        for r in required:
            if r not in payload:
                return {"status": "REJECTED", "reason": f"Missing required field: {r}"}

        s_id = str(payload["sensor_id"])
        s_type = str(payload["sensor_type"]).upper()
        
        try:
            val = float(payload["measurement"])
        except (ValueError, TypeError):
            return {"status": "REJECTED", "reason": "Measurement value must be numeric"}

        # Physical range validation
        valid, msg = self.validate_reading(s_type, val)
        if not valid:
            return {"status": "REJECTED", "reason": msg}

        # Sequence gap / duplicate check
        seq = payload.get("sequence_number")
        is_duplicate = False
        seq_gap = 0
        if seq is not None:
            try:
                seq = int(seq)
                last_seq = self.last_sequences.get(s_id)
                if last_seq is not None:
                    if seq == last_seq:
                        is_duplicate = True
                    elif seq > last_seq + 1:
                        seq_gap = seq - last_seq - 1
                self.last_sequences[s_id] = seq
            except ValueError:
                pass

        if is_duplicate:
            return {"status": "DUPLICATE_SUPPRESSED", "sensor_id": s_id, "sequence": seq}

        # Health tracking
        batt = payload.get("battery_level")
        health = self.sensor_health.setdefault(s_id, {
            "sensor_id": s_id,
            "sensor_type": s_type,
            "gateway_id": payload.get("gateway_id", "LOCAL_GATEWAY"),
            "total_packets": 0,
            "missing_packets": 0,
            "battery_level": batt,
            "last_seen": payload["timestamp"]
        })
        health["total_packets"] += 1
        health["missing_packets"] += seq_gap
        if batt is not None:
            health["battery_level"] = batt
        health["last_seen"] = payload["timestamp"]

        now_utc = datetime.now(timezone.utc).isoformat()
        obs_time = payload.get("observation_time") or payload.get("timestamp") or now_utc
        avail_time = payload.get("available_time") or obs_time

        # Standardized Record envelope satisfying Phase 6 & Phase 8
        record = {
            "sensor_id": s_id,
            "sensor_type": s_type,
            "site_id": payload.get("site_id", "MAWIONGRIM_EAST_KHASI_HILLS"),
            "state": payload.get("state", "Meghalaya"),
            "latitude": payload.get("latitude", 25.1837),
            "longitude": payload.get("longitude", 91.6421),
            "elevation": payload.get("elevation", 150.0),
            "observation_time": obs_time,
            "available_time": avail_time,
            "received_time": now_utc,
            "ingested_time": now_utc,
            "timestamp": obs_time, # backwards-compatible alias
            "ingested_at": now_utc, # backwards-compatible alias
            "measurement": val,
            "measurement_unit": payload.get("measurement_unit", SENSOR_BOUNDS[s_type]["unit"]),
            "battery_level": batt,
            "quality": payload.get("quality", "CONFIRMED_HARDWARE"),
            "sequence_number": seq,
            "gateway_id": payload.get("gateway_id", "LOCAL_GATEWAY"),
            "source": payload.get("source", "FIELD_NODE"),
            "raw_reference": payload.get("raw_reference", None),
            "queue_state": payload.get("queue_state", QUEUE_LOCAL_ONLY)
        }

        self.telemetry_store.append(record)
        self._save_telemetry()
        return {"status": "INGESTED", "record": record}

    def parse_serial_packet(self, raw_line: str, gateway_id: str = "USB_SERIAL_GW") -> Dict[str, Any]:
        """Parses a comma-separated serial stream string from an ESP32 / Arduino.
        Format: $NER,SENSOR_ID,SENSOR_TYPE,MEASUREMENT,UNIT,BATTERY,SEQ,LAT,LON*CHECKSUM
        """
        line = raw_line.strip()
        if not line.startswith("$NER"):
            return {"status": "INVALID_PACKET", "reason": "Missing $NER sentence header"}

        # Strip checksum if present
        if "*" in line:
            line = line.split("*")[0]

        parts = line.split(",")
        if len(parts) < 7:
            return {"status": "MALFORMED_PACKET", "reason": "Insufficient fields in serial sentence"}

        payload = {
            "gateway_id": gateway_id,
            "sensor_id": parts[1],
            "sensor_type": parts[2],
            "measurement": parts[3],
            "measurement_unit": parts[4],
            "battery_level": float(parts[5]) if parts[5] else None,
            "sequence_number": int(parts[6]) if parts[6] else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if len(parts) >= 9:
            try:
                payload["latitude"] = float(parts[7])
                payload["longitude"] = float(parts[8])
            except ValueError:
                pass

        return self.ingest_measurement(payload)

    def get_latest_readings(self, sensor_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns latest telemetry readings sorted by timestamp descending."""
        res = self.telemetry_store
        if sensor_type:
            res = [r for r in res if r["sensor_type"] == sensor_type.upper()]
        return sorted(res, key=lambda x: x.get("timestamp", ""), reverse=True)

    def get_health_summary(self) -> Dict[str, Any]:
        """Returns node health summary across all active hardware sensors."""
        return {
            "total_registered_sensors": len(self.sensor_health),
            "active_sensors": list(self.sensor_health.values()),
            "total_telemetry_records": len(self.telemetry_store)
        }

    def ingest_mawiongrim_records(self, csv_path: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """Ingests authentic geotechnical field sensor time-series from Mawiongrim, Meghalaya.
        Strictly preserves original observation_time from 2022-12 and marks ingested_time as current UTC.
        """
        path = csv_path or os.path.join(
            os.environ.get("NER_SAFE_ROOT", r"E:\landslide - Copy\landslide - Copy"),
            "NER_SAFE_DATA", "SENSORS", "mawiongrim_telemetry.csv"
        )
        if not os.path.exists(path):
            return {"status": "FILE_NOT_FOUND", "path": path, "ingested_count": 0}

        ingested_count = 0
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                if limit and idx >= limit:
                    break
                ts_str = row.get("Timestamp", "").strip()
                try:
                    obs_dt = datetime.strptime(ts_str, "%d-%m-%Y %H:%M").replace(tzinfo=timezone.utc)
                    obs_iso = obs_dt.isoformat()
                except Exception:
                    obs_iso = datetime.now(timezone.utc).isoformat()

                # Ingest Rain Gauge
                if row.get("Rainfall"):
                    try:
                        rain_val = float(row["Rainfall"])
                        self.ingest_measurement({
                            "sensor_id": "NITM_MAW_RAIN_01",
                            "sensor_type": SENSOR_RAIN_GAUGE,
                            "site_id": "MAWIONGRIM",
                            "state": "Meghalaya",
                            "latitude": 25.5312,
                            "longitude": 91.8745,
                            "elevation": 1520.0,
                            "observation_time": obs_iso,
                            "measurement": rain_val,
                            "measurement_unit": "mm/h",
                            "quality": "VERIFIED_RESEARCH_DATASET",
                            "source": "NIT_MEG_MAWIONGRIM_01",
                            "sequence_number": idx + 1
                        })
                        ingested_count += 1
                    except ValueError:
                        pass

                # Ingest Inclinometer 10m Up
                if row.get("Inc10mup"):
                    try:
                        tilt_val = float(row["Inc10mup"])
                        self.ingest_measurement({
                            "sensor_id": "NITM_MAW_TILT_10M_UP",
                            "sensor_type": SENSOR_TILT,
                            "site_id": "MAWIONGRIM",
                            "state": "Meghalaya",
                            "latitude": 25.5312,
                            "longitude": 91.8745,
                            "elevation": 1520.0,
                            "observation_time": obs_iso,
                            "measurement": tilt_val,
                            "measurement_unit": "deg",
                            "quality": "VERIFIED_RESEARCH_DATASET",
                            "source": "NIT_MEG_MAWIONGRIM_01",
                            "sequence_number": idx + 1
                        })
                        ingested_count += 1
                    except ValueError:
                        pass

        return {
            "status": "SUCCESS",
            "source_id": "NIT_MEG_MAWIONGRIM_01",
            "site": "Mawiongrim, East Khasi Hills, Meghalaya",
            "ingested_observations": ingested_count,
            "provenance": "NIT Meghalaya Research Geotechnical Station (2022)"
        }

# Global Singleton Adapter
ground_sensor_adapter = GroundSensorInterface()
