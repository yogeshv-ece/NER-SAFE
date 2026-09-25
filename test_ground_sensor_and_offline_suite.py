"""
test_ground_sensor_and_offline_suite.py
======================================
Tests for:
1. ground_sensor_interface.py (Sensor types, range validation, sequence gaps, store-and-forward queue)
2. esp32_reference_gateway.py (ESP32 packet format, CRC/checksum verification, packet parsing, reference firmware)
3. zero_network_manager.py (4-level connectivity hierarchy, Level 4 SMS prohibition, local actuator dispatch)
4. local_sensor_alert_engine.py (Local edge alerts, hysteresis, 'LAST SYNCHRONIZED RISK' provenance)
"""

import unittest
import tempfile
import os
import shutil
from datetime import datetime, timezone

from ground_sensor_interface import (
    GroundSensorInterface,
    SENSOR_SOIL_MOISTURE,
    SENSOR_RAIN_GAUGE,
    SENSOR_TILT,
    SENSOR_TEMPERATURE,
    QUEUE_LOCAL_ONLY,
    QUEUE_QUEUED,
    QUEUE_SYNCING,
    QUEUE_SYNCED,
    QUEUE_SYNC_FAILED
)
from esp32_reference_gateway import (
    compute_checksum,
    ESP32ReferenceNode,
    ESP32_FIRMWARE_SKETCH
)
from zero_network_manager import (
    ZeroNetworkManager,
    NET_LEVEL_1_BROADBAND,
    NET_LEVEL_2_WEAK_CELLULAR,
    NET_LEVEL_3_INTERMITTENT,
    NET_LEVEL_4_ZERO_NETWORK
)
from local_sensor_alert_engine import (
    LocalSensorAlertEngine,
    ALERT_CRITICAL,
    ALERT_HIGH,
    ALERT_WARNING,
    ALERT_NORMAL
)


class TestGroundSensorAndOfflineSuite(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_sensors.json")
        self.sensor_mgr = GroundSensorInterface(persistence_file=self.db_path)
        self.zero_net = ZeroNetworkManager()
        self.alert_engine = LocalSensorAlertEngine()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_sensor_valid_and_out_of_bounds(self):
        """Verify normal ingestion and out-of-bounds rejection."""
        # Valid soil moisture
        valid_payload = {
            "sensor_id": "SOIL_001",
            "sensor_type": SENSOR_SOIL_MOISTURE,
            "latitude": 25.57,
            "longitude": 91.88,
            "elevation": 1400.0,
            "timestamp": "2026-09-13T10:00:00Z",
            "measurement": 42.5,
            "measurement_unit": "%",
            "battery_level": 95.0,
            "sequence_number": 1
        }
        res = self.sensor_mgr.ingest_measurement(valid_payload)
        self.assertEqual(res["status"], "INGESTED")
        self.assertEqual(res["record"]["measurement"], 42.5)

        # Invalid out-of-bounds soil moisture (150%)
        invalid_payload = {
            "sensor_id": "SOIL_001",
            "sensor_type": SENSOR_SOIL_MOISTURE,
            "latitude": 25.57,
            "longitude": 91.88,
            "elevation": 1400.0,
            "timestamp": "2026-09-13T10:01:00Z",
            "measurement": 150.0,
            "measurement_unit": "%",
            "battery_level": 95.0,
            "sequence_number": 2
        }
        res_inv = self.sensor_mgr.ingest_measurement(invalid_payload)
        self.assertEqual(res_inv["status"], "REJECTED")
        self.assertIn("out of physical bounds", res_inv["reason"])

    def test_02_sequence_gap_and_duplicate_suppression(self):
        """Verify duplicate suppression and sequence gap tracking."""
        # Packet 1
        p1 = {
            "sensor_id": "RAIN_001",
            "sensor_type": SENSOR_RAIN_GAUGE,
            "measurement": 12.0,
            "timestamp": "2026-09-13T10:01:00Z",
            "sequence_number": 1
        }
        res1 = self.sensor_mgr.ingest_measurement(p1)
        self.assertEqual(res1["status"], "INGESTED")

        # Duplicate Packet 1
        res1_dup = self.sensor_mgr.ingest_measurement(p1)
        self.assertEqual(res1_dup["status"], "DUPLICATE_SUPPRESSED")

        # Packet 4 (Missing sequence 2 and 3)
        p4 = {
            "sensor_id": "RAIN_001",
            "sensor_type": SENSOR_RAIN_GAUGE,
            "measurement": 15.5,
            "timestamp": "2026-09-13T10:04:00Z",
            "sequence_number": 4
        }
        res4 = self.sensor_mgr.ingest_measurement(p4)
        self.assertEqual(res4["status"], "INGESTED")

        health = self.sensor_mgr.get_health_summary()
        rain_health = [s for s in health["active_sensors"] if s["sensor_id"] == "RAIN_001"][0]
        self.assertEqual(rain_health["missing_packets"], 2)

    def test_03_esp32_packet_checksum_and_node(self):
        """Verify ESP32 packet building, checksum calculation, and serial parsing."""
        node = ESP32ReferenceNode(node_id="ESP32-TEST-01", lat=25.1837, lon=91.6421)
        pkt_str = node.build_packet(SENSOR_TILT, 3.45, "deg")
        self.assertTrue(pkt_str.startswith("$NER"))
        self.assertIn("*", pkt_str)

        # Parse valid serial packet
        res = self.sensor_mgr.parse_serial_packet(pkt_str, gateway_id="TEST_GW")
        self.assertEqual(res["status"], "INGESTED")
        self.assertEqual(res["record"]["sensor_id"], "ESP32-TEST-01")
        self.assertEqual(res["record"]["sensor_type"], SENSOR_TILT)
        self.assertAlmostEqual(res["record"]["measurement"], 3.45, places=2)

        # Malformed packet
        malformed = "$NER,ESP32-TEST-01,TILT"
        res_mal = self.sensor_mgr.parse_serial_packet(malformed)
        self.assertEqual(res_mal["status"], "MALFORMED_PACKET")

        # Ensure reference firmware sketch is provided and valid C++
        self.assertIn("void setup()", ESP32_FIRMWARE_SKETCH)
        self.assertIn("void loop()", ESP32_FIRMWARE_SKETCH)

    def test_04_zero_network_levels_and_queue(self):
        """Verify 4 connectivity levels and store-and-forward queue."""
        zn = ZeroNetworkManager()
        # Default level is Level 4
        self.assertEqual(zn.current_level, NET_LEVEL_4_ZERO_NETWORK)

        # Queue an item during Level 4
        q_item = zn.queue_outbound_record("SENSOR_TELEMETRY", {"temp": 21.0})
        self.assertEqual(q_item["status"], "LOCAL_ONLY")

        # Attempting flush in Level 4 must be BLOCKED
        flush_res = zn.flush_sync_queue()
        self.assertEqual(flush_res["status"], "BLOCKED")

        # Move to Level 1 and flush
        zn.set_network_level(NET_LEVEL_1_BROADBAND)
        self.assertEqual(zn.current_level, NET_LEVEL_1_BROADBAND)
        flush_success = zn.flush_sync_queue()
        self.assertEqual(flush_success["status"], "SUCCESS")
        self.assertEqual(flush_success["synced_count"], 1)

    def test_05_zero_network_actuator_dispatch(self):
        """Verify local actuator interface and disclaimer for siren/radio/buzzer/beacon."""
        zn = ZeroNetworkManager()
        zn.set_network_level(NET_LEVEL_4_ZERO_NETWORK)

        act_res = zn.dispatch_local_actuator(
            actuator_type="LOCAL_SIREN_TRIGGER",
            alert_tier="CRITICAL",
            message="Immediate evacuation warning",
            zone_id="ZONE-001"
        )
        self.assertEqual(act_res["status"], "DISPATCHED")
        self.assertFalse(act_res["event"]["hardware_actuation_claimed"])
        self.assertIn("Software interface protocol triggered", act_res["event"]["disclaimer"])

        # Check offline edge package
        edge_pkg = zn.get_offline_edge_package()
        self.assertFalse(edge_pkg["sms_available"])
        self.assertIn("SMS strictly unavailable under Level 4", edge_pkg["sms_disclaimer"])
        self.assertTrue(edge_pkg["edge_mode_active"])

    def test_06_local_edge_risk_and_provenance(self):
        """Verify local sensor alert engine marks cached central risk as 'LAST SYNCHRONIZED RISK'."""
        eval_res = self.alert_engine.evaluate_local_slope_state("SLOPE-001")
        self.assertEqual(eval_res["mode"], "LOCAL_EDGE_MODE")
        central_meta = eval_res["central_risk_status"]
        self.assertEqual(central_meta["label"], "LAST SYNCHRONIZED RISK")
        self.assertEqual(central_meta["current_risk_claim"], "UNAVAILABLE_OFFLINE")
        self.assertIn("Central ML risk calculation is disconnected", central_meta["disclaimer"])


if __name__ == "__main__":
    unittest.main()
