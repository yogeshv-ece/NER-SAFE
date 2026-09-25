"""
=============================================================================
NER-SAFE: AUTOMATED TEST SUITE FOR LIVE MULTI-SOURCE SCHEDULER & SENSORS
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validate live multi-source registry, cadence scheduler, observation
         deduplication, decoupled timestamps, Mawiongrim field data ingestion,
         REST endpoints, and Level 4 zero-network local sensor alerts.
=============================================================================
"""

import os
import json
import time
import threading
import requests
import unittest
from datetime import datetime, timezone

from sensor_source_registry import (
    SensorSourceRegistry,
    SIGNAL_SPEED_FAST,
    SIGNAL_SPEED_MEDIUM,
    SIGNAL_SPEED_CONTEXT,
    STATUS_LIVE_STREAMING,
    STATUS_LIVE_READY,
    STATUS_AUTH_REQUIRED,
    STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
    STATUS_HISTORICAL_ONLY,
    STATUS_SOURCE_UNAVAILABLE,
    STATUS_HARDWARE_REQUIRED,
    sensor_source_registry
)
from ground_sensor_interface import (
    GroundSensorInterface,
    SENSOR_SOIL_MOISTURE,
    SENSOR_RAIN_GAUGE,
    SENSOR_TILT,
    SENSOR_TEMPERATURE,
    SENSOR_PORE_PRESSURE,
    SENSOR_GEOPHONE,
    SENSOR_STRAIN,
    SENSOR_BOUNDS,
    ground_sensor_adapter
)
from live_monitoring_scheduler import LiveMonitoringScheduler, live_monitoring_scheduler
from local_sensor_alert_engine import LocalSensorAlertEngine, ALERT_NORMAL, ALERT_CRITICAL
import server


class TestSensorSourceRegistry(unittest.TestCase):
    """Verify source registry catalog, metadata schema, and speed tiers."""

    def setUp(self):
        self.registry = SensorSourceRegistry()

    def test_registry_contains_nine_real_sources(self):
        sources = self.registry.list_sources()
        self.assertGreaterEqual(len(sources), 9)
        source_ids = [s["source_id"] for s in sources]
        self.assertIn("NIT_MEG_MAWIONGRIM_01", source_ids)
        self.assertIn("NEHU_SHILLONG_SLOPE_01", source_ids)
        self.assertIn("MIRSAC_AIZAWL_01", source_ids)
        self.assertIn("NASA_GPM_NRT_01", source_ids)
        self.assertIn("NASA_SMAP_L3_01", source_ids)
        self.assertIn("ESA_SENTINEL1_SAR_01", source_ids)
        self.assertIn("ESA_SENTINEL2_OPT_01", source_ids)
        self.assertIn("IMD_AWS_SHILLONG_01", source_ids)
        self.assertIn("LOCAL_ESP32_GATEWAY_01", source_ids)

    def test_speed_tier_categorization(self):
        fast_sources = self.registry.list_sources(speed_filter=SIGNAL_SPEED_FAST)
        medium_sources = self.registry.list_sources(speed_filter=SIGNAL_SPEED_MEDIUM)
        context_sources = self.registry.list_sources(speed_filter=SIGNAL_SPEED_CONTEXT)

        fast_ids = [s["source_id"] for s in fast_sources]
        medium_ids = [s["source_id"] for s in medium_sources]
        context_ids = [s["source_id"] for s in context_sources]

        # Fast: ground sensors and GPM NRT
        self.assertIn("NIT_MEG_MAWIONGRIM_01", fast_ids)
        self.assertIn("NASA_GPM_NRT_01", fast_ids)

        # Medium: Sentinel-1 SAR and SMAP
        self.assertIn("ESA_SENTINEL1_SAR_01", medium_ids)
        self.assertIn("NASA_SMAP_L3_01", medium_ids)

        # Context: Sentinel-2 optical
        self.assertIn("ESA_SENTINEL2_OPT_01", context_ids)

    def test_source_status_values_valid(self):
        valid_statuses = {
            STATUS_LIVE_STREAMING,
            STATUS_LIVE_READY,
            STATUS_AUTH_REQUIRED,
            STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
            STATUS_HISTORICAL_ONLY,
            STATUS_SOURCE_UNAVAILABLE,
            STATUS_HARDWARE_REQUIRED
        }
        for s in self.registry.list_sources():
            self.assertIn(s["status"], valid_statuses)


class TestGroundSensorAdapterAndMawiongrim(unittest.TestCase):
    """Verify hardware-neutral schema, timestamp decoupling, and real Mawiongrim ingestion."""

    def setUp(self):
        self.adapter = GroundSensorInterface()

    def test_supported_sensor_types(self):
        types = list(SENSOR_BOUNDS.keys())
        self.assertIn(SENSOR_SOIL_MOISTURE, types)
        self.assertIn(SENSOR_RAIN_GAUGE, types)
        self.assertIn(SENSOR_TILT, types)
        self.assertIn(SENSOR_PORE_PRESSURE, types)
        self.assertIn(SENSOR_GEOPHONE, types)
        self.assertIn(SENSOR_STRAIN, types)

    def test_timestamp_decoupling(self):
        obs_time = "2026-09-13T10:00:00Z"
        payload = {
            "sensor_id": "NODE-TEST-01",
            "sensor_type": SENSOR_TILT,
            "site_id": "SITE-TEST",
            "state": "Meghalaya",
            "latitude": 25.57,
            "longitude": 91.88,
            "elevation": 1450.0,
            "timestamp": obs_time,
            "observation_time": obs_time,
            "available_time": "2026-09-13T10:05:00Z",
            "measurement": 2.85,
            "measurement_unit": "deg",
            "quality": "GOOD",
            "source": "TEST_FEED"
        }
        res = self.adapter.ingest_measurement(payload)
        self.assertEqual(res["status"], "INGESTED")
        record = res["record"]
        # Observation time must strictly preserve the physical event time
        self.assertEqual(record["observation_time"], obs_time)
        # Ingested time must be distinct (current processing time)
        self.assertIn("ingested_time", record)
        self.assertNotEqual(record["observation_time"], record["ingested_time"])

    def test_mawiongrim_real_telemetry_ingestion(self):
        mawiongrim_path = os.path.join(os.path.dirname(__file__), "NER_SAFE_DATA", "SENSORS", "mawiongrim_telemetry.csv")
        self.assertTrue(os.path.exists(mawiongrim_path), "Mawiongrim telemetry file must exist locally")

        result = self.adapter.ingest_mawiongrim_records(mawiongrim_path, limit=25)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertGreaterEqual(result["ingested_observations"], 10)
        self.assertEqual(result["source_id"], "NIT_MEG_MAWIONGRIM_01")
        self.assertGreater(len(self.adapter.telemetry_store), 0)


class TestLiveMonitoringScheduler(unittest.TestCase):
    """Verify autonomous cadence polling, observation deduplication, and health tracking."""

    def setUp(self):
        self.scheduler = LiveMonitoringScheduler()

    def test_single_poll_cycle_execution(self):
        cycle = self.scheduler.run_scheduled_cycle()
        self.assertIn("cycle_timestamp_utc", cycle)
        self.assertIn("sources_polled", cycle)
        self.assertIn("new_observations_ingested", cycle)
        self.assertIn("details", cycle)
        self.assertGreater(cycle["sources_polled"], 0)

    def test_deduplication_prevents_redundant_triggering(self):
        # First cycle polls available sources
        cycle1 = self.scheduler.run_scheduled_cycle()
        
        # Second immediate cycle must recognize that observations have not changed
        cycle2 = self.scheduler.run_scheduled_cycle()
        self.assertEqual(cycle2["new_observations_ingested"], 0, "Immediate second poll must identify observations as ALREADY_CURRENT")
        self.assertEqual(cycle2["reassessments_triggered"], 0, "No new assessment should be triggered on duplicate data")

    def test_source_health_reporting(self):
        self.scheduler.run_scheduled_cycle()
        health_list = self.scheduler.get_dashboard_source_health()
        self.assertGreaterEqual(len(health_list), 9)

        # Check that GPM NRT is tracked
        gpm_health = next((s for s in health_list if s["source_id"] == "NASA_GPM_NRT_01"), None)
        self.assertIsNotNone(gpm_health)
        self.assertIn("status", gpm_health)
        self.assertIn("last_poll_utc", gpm_health)


class TestLocalSensorAlertEngine(unittest.TestCase):
    """Verify Level 4 zero-network local sensor alert engine (no SMS, conservative thresholds)."""

    def setUp(self):
        self.engine = LocalSensorAlertEngine()

    def test_normal_readings_stay_normal(self):
        # Ingest normal baseline reading
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_TILT_NORM",
            "sensor_type": SENSOR_TILT,
            "measurement": 0.1,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_SOIL_NORM",
            "sensor_type": SENSOR_SOIL_MOISTURE,
            "measurement": 30.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_RAIN_NORM",
            "sensor_type": SENSOR_RAIN_GAUGE,
            "measurement": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        alert = self.engine.evaluate_local_slope_state("TEST-SLOPE-01")
        self.assertIn(alert["evaluated_tier"], [ALERT_NORMAL, "WATCH"])
        self.assertEqual(alert["mode"], "LOCAL_EDGE_MODE")

    def test_critical_confluence_triggers_local_siren(self):
        # Ingest critical reading into ground adapter
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_TILT_CRIT",
            "sensor_type": SENSOR_TILT,
            "measurement": 4.5,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_SOIL_CRIT",
            "sensor_type": SENSOR_SOIL_MOISTURE,
            "measurement": 95.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        ground_sensor_adapter.ingest_measurement({
            "sensor_id": "TEST_RAIN_CRIT",
            "sensor_type": SENSOR_RAIN_GAUGE,
            "measurement": 55.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        alert = self.engine.evaluate_local_slope_state("TEST-SLOPE-01")
        self.assertEqual(alert["evaluated_tier"], ALERT_CRITICAL)
        self.assertEqual(alert["alert_type"], "LOCAL SENSOR ALERT")
        self.assertIsNotNone(alert["actuator_event"])
        self.assertEqual(alert["actuator_event"]["status"], "DISPATCHED")
        self.assertEqual(alert["actuator_event"]["event"]["actuator_type"], "LOCAL_SIREN_TRIGGER")
        self.assertEqual(alert["central_risk_status"]["label"], "LAST SYNCHRONIZED RISK")


class TestServerLiveEndpoints(unittest.TestCase):
    """Verify REST routes for sensor catalog, health, readings, and poll trigger."""

    @classmethod
    def setUpClass(cls):
        cls.test_port = 8029
        from live_sensor_server_extension import start_extended_server
        cls.httpd = start_extended_server(cls.test_port)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.4)
        cls.base_url = f"http://127.0.0.1:{cls.test_port}"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.httpd.shutdown()
        except Exception:
            pass

    def test_get_sensor_sources(self):
        res = requests.get(f"{self.base_url}/api/sensors/sources", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("NIT_MEG_MAWIONGRIM_01", data)
        self.assertIn("NASA_GPM_NRT_01", data)

    def test_get_monitoring_sources_health(self):
        res = requests.get(f"{self.base_url}/api/monitoring/sources/health", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("sources", data)
        self.assertGreaterEqual(len(data["sources"]), 9)

    def test_get_mawiongrim_records(self):
        res = requests.get(f"{self.base_url}/api/sensors/mawiongrim?limit=5", timeout=5)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("source", data)
        self.assertEqual(data["source"], "NIT_MEG_MAWIONGRIM_01")
        self.assertIn("readings", data)

    def test_post_sensor_reading(self):
        payload = {
            "sensor_id": "TEST_NODE_HTTP_01",
            "sensor_type": "SOIL_MOISTURE",
            "site_id": "TEST_SITE",
            "state": "Meghalaya",
            "latitude": 25.57,
            "longitude": 91.88,
            "elevation": 1450.0,
            "observation_time": "2026-09-13T12:00:00Z",
            "measurement": 42.5,
            "measurement_unit": "%",
            "quality": "GOOD",
            "timestamp": "2026-09-13T12:00:00Z"
        }
        res = requests.post(f"{self.base_url}/api/sensors/reading", json=payload, timeout=5)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "INGESTED")

    def test_post_monitoring_poll(self):
        res = requests.post(f"{self.base_url}/api/monitoring/poll", timeout=60)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("cycle_timestamp_utc", data)
        self.assertIn("sources_polled", data)


if __name__ == "__main__":
    unittest.main()
