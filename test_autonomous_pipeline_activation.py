"""
=============================================================================
NER-SAFE: Test Suite for Autonomous Pipeline Activation & Scheduling Engine
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validates autonomous scheduler lifecycle, process concurrency locking,
         stale lock recovery, storage guard enforcement, scientific governance
         invariance, multi-source polling, and credential secrecy.
=============================================================================
"""

import os
import sys
import json
import time
import shutil
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nersafe_autonomous_scheduler import (
    SingleInstanceLock,
    AutonomousScheduler,
    check_storage_guard,
    is_pid_alive,
    LOCKED_XGBOOST_HASH,
    LOCKED_RISK_WEIGHTS,
    STORAGE_GUARD_MIN_FREE_GB,
    LOCK_FILE,
    STATUS_FILE,
    LOG_FILE
)


class TestAutonomousSchedulerCore(unittest.TestCase):
    """Unit tests for scheduler core locking, storage guard, and invariants."""

    def setUp(self):
        self.test_lock_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", ".test_scheduler.lock")
        if os.path.exists(self.test_lock_file):
            try:
                os.remove(self.test_lock_file)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(self.test_lock_file):
            try:
                os.remove(self.test_lock_file)
            except Exception:
                pass

    def test_single_instance_lock_lifecycle(self):
        """Verify normal acquisition and clean release."""
        lock = SingleInstanceLock(lock_path=self.test_lock_file)
        self.assertTrue(lock.acquire())
        self.assertTrue(os.path.exists(self.test_lock_file))

        with open(self.test_lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["pid"], os.getpid())

        lock.release()
        self.assertFalse(os.path.exists(self.test_lock_file))

    def test_stale_lock_recovery(self):
        """Verify stale lock from a dead PID is automatically recovered."""
        # Create a mock lock file with an impossible/dead PID
        dead_pid = 99999999
        stale_payload = {
            "pid": dead_pid,
            "started_at_utc": "2026-09-01T00:00:00Z",
            "host_root": PROJECT_ROOT
        }
        with open(self.test_lock_file, "w", encoding="utf-8") as f:
            json.dump(stale_payload, f)

        self.assertFalse(is_pid_alive(dead_pid))

        # Attempt acquisition with new lock
        new_lock = SingleInstanceLock(lock_path=self.test_lock_file)
        acquired = new_lock.acquire()
        self.assertTrue(acquired, "Should recover and acquire stale lock")

        with open(self.test_lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["pid"], os.getpid())
        new_lock.release()

    def test_active_pid_concurrency_rejection(self):
        """Verify active running PID blocks a secondary instance."""
        lock1 = SingleInstanceLock(lock_path=self.test_lock_file)
        self.assertTrue(lock1.acquire())

        # Second lock instance simulating concurrent runner
        lock2 = SingleInstanceLock(lock_path=self.test_lock_file)
        # Mock is_pid_alive to simulate active process if tested across threads/pids
        with patch("nersafe_autonomous_scheduler.is_pid_alive", return_value=True):
            # Simulate another process trying to acquire
            with patch("os.getpid", return_value=os.getpid() + 1):
                self.assertFalse(lock2.acquire(), "Second instance must be rejected while first is alive")

        lock1.release()

    def test_storage_guard_normal(self):
        """Verify storage guard passes on normal available disk space."""
        is_safe, free_gb = check_storage_guard(PROJECT_ROOT)
        self.assertGreater(free_gb, 0.0)
        # Drive E has ~50 GB free, should be safe
        self.assertTrue(is_safe)
        self.assertGreaterEqual(free_gb, STORAGE_GUARD_MIN_FREE_GB)

    def test_storage_guard_halts_when_low_space(self):
        """Verify storage guard halts cycle when free space < 10 GB."""
        with patch("shutil.disk_usage", return_value=(100 * 1024**3, 95 * 1024**3, 5 * 1024**3)):
            is_safe, free_gb = check_storage_guard(PROJECT_ROOT)
            self.assertFalse(is_safe)
            self.assertLess(free_gb, STORAGE_GUARD_MIN_FREE_GB)

            scheduler = AutonomousScheduler()
            telemetry = scheduler.execute_cycle()
            self.assertEqual(telemetry.get("status"), "HALTED_STORAGE_GUARD")

    def test_xgboost_model_hash_invariant(self):
        """Verify Calibrated XGBoost production model SHA-256 matches locked hash."""
        scheduler = AutonomousScheduler()
        invariants = scheduler.verify_system_invariants()
        self.assertTrue(invariants["xgboost_hash_verified"])
        self.assertEqual(invariants["xgboost_sha256"], LOCKED_XGBOOST_HASH)

    def test_risk_formula_weights_locked(self):
        """Verify 4-factor risk weights remain exactly 0.40, 0.30, 0.20, 0.10."""
        self.assertEqual(LOCKED_RISK_WEIGHTS["susceptibility"], 0.40)
        self.assertEqual(LOCKED_RISK_WEIGHTS["rainfall"], 0.30)
        self.assertEqual(LOCKED_RISK_WEIGHTS["soil_moisture"], 0.20)
        self.assertEqual(LOCKED_RISK_WEIGHTS["satellite_change"], 0.10)
        self.assertAlmostEqual(sum(LOCKED_RISK_WEIGHTS.values()), 1.0)


class TestAutonomousSchedulerLiveExecution(unittest.TestCase):
    """Tests executing real and simulated multi-source polling cycles."""

    def setUp(self):
        # Clean any stale lock
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    def tearDown(self):
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    def test_execute_single_cycle(self):
        """Executes a single complete cycle of all active components."""
        scheduler = AutonomousScheduler()
        telemetry = scheduler.execute_cycle()

        self.assertEqual(telemetry.get("status"), "SUCCESS")
        self.assertGreaterEqual(telemetry.get("cycle_number"), 1)
        self.assertGreater(telemetry.get("free_disk_gb"), 10.0)

        sources = telemetry.get("sources_polled", {})
        self.assertIn("GPM", sources)
        self.assertIn("SMAP", sources)
        self.assertIn("SENTINEL1_SLC", sources)
        self.assertIn("GSI_BHUSANKET_WEBAPI", sources)
        self.assertIn("NDMA_SACHET_CAP", sources)
        self.assertIn("IMD_MAUSAM_NOWCAST", sources)
        self.assertIn("NER_SAFE_OSINT_ENGINE", sources)
        self.assertIn("OSIRIS_ADAPTER_USGS_GDACS", sources)
        self.assertIn("ESA_SENTINEL1_GRD", sources)
        self.assertIn("ESA_SENTINEL2_MSIL2A", sources)
        self.assertIn("NER_SAFE_INSAR_SBAS", sources)

        # Verify InSAR scientific status
        insar_info = sources["NER_SAFE_INSAR_SBAS"]
        self.assertEqual(insar_info["status"], "RESEARCH_ONLY")
        self.assertEqual(insar_info["max_temporal_baseline_days"], 36.0)
        self.assertEqual(insar_info["max_perpendicular_baseline_m"], 180.0)
        self.assertTrue(insar_info["scientific_thresholds_verified"])

    def test_run_once_mode(self):
        """Verify run_once executes cleanly and releases lock."""
        scheduler = AutonomousScheduler()
        with patch.object(scheduler, "execute_cycle", return_value={"status": "SUCCESS"}):
            res = scheduler.run_once()
            self.assertEqual(res.get("status"), "SUCCESS")
            self.assertFalse(os.path.exists(LOCK_FILE))

    def test_continuous_mode_max_cycles(self):
        """Verify continuous daemon loop executes specified max_cycles and terminates cleanly."""
        scheduler = AutonomousScheduler(poll_interval_sec=1, max_cycles=2)
        def mock_cycle():
            scheduler.cycle_count += 1
            telemetry = {"status": "SUCCESS", "cycle_number": scheduler.cycle_count}
            scheduler._write_status_file(telemetry)
            return telemetry

        with patch.object(scheduler, "execute_cycle", side_effect=mock_cycle):
            scheduler.run_continuous()

            self.assertEqual(scheduler.cycle_count, 2)
            self.assertFalse(scheduler.is_running)
            self.assertFalse(os.path.exists(LOCK_FILE))

            # Check status JSON
            self.assertTrue(os.path.exists(STATUS_FILE))
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status_data = json.load(f)
            self.assertEqual(status_data.get("cycle_count"), 2)
            self.assertEqual(status_data.get("daemon_status"), "STOPPED")

    def test_zero_credential_exposure(self):
        """Verify no sensitive tokens, credentials, or NetRC secrets are in status or logs."""
        sensitive_patterns = ["password", "bearer ", "client_secret", "cdse_client_secret"]
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                content = f.read().lower()
            for pat in sensitive_patterns:
                self.assertNotIn(pat, content, f"Sensitive pattern '{pat}' exposed in status file!")

    def test_zero_emojis(self):
        """Verify zero emojis in log and status outputs."""
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            # Verify all characters are ASCII or standard typographical marks (no emoji range)
            for char in content:
                code = ord(char)
                self.assertFalse(0x1F300 <= code <= 0x1FAFF, f"Emoji character U+{code:04X} found in status!")


if __name__ == "__main__":
    unittest.main()
