"""
=============================================================================
NER-SAFE Test Suite: End-to-End Sentinel-1 SLC Live Acquisition & Automation
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Verifies the automated discovery, S3 acquisition, integrity validation,
         Google Drive cloud archival, provenance cataloging, SBAS stack expansion,
         and deduplication enforcement for Sentinel-1 IW SLC repeat passes.
Standards: Strict zero fabrication, authentic CDSE data, UX4G zero emoji.
=============================================================================
"""

import os
import sys
import json
import hashlib
import unittest
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from live_monitoring_scheduler import LiveMonitoringScheduler
from multitemporal_slc_manager import multitemporal_slc_manager
from source_ingestion_manager import source_ingestion_mgr
from google_drive_archive import google_drive_archiver

TARGET_SCENE = "S1D_IW_SLC__1SDV_20260820T235450_20260820T235517_004216_007BCA_7A43.SAFE"


class TestSentinel1SLCLiveAcquisitionScheduler(unittest.TestCase):
    """Verifies end-to-end automated SLC acquisition lifecycle and deduplication."""

    @classmethod
    def setUpClass(cls):
        cls.scheduler = LiveMonitoringScheduler()
        cls.slc_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "SLC")
        cls.target_dir = os.path.join(cls.slc_dir, TARGET_SCENE)
        cls.manifest_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "archive_manifest.json")

    def test_01_catalogue_scene_discovery(self):
        """Verifies candidate scene discovery on Track 150 Descending."""
        inv = multitemporal_slc_manager.fetch_cdse_inventory(force_refresh=False)
        self.assertIsInstance(inv, list)
        self.assertGreater(len(inv), 0)

        # Confirm target scene is an authentic Sentinel-1D repeat pass on Track 150
        target = next((x for x in inv if x["granule_name"] == TARGET_SCENE), None)
        self.assertIsNotNone(target, f"Target scene {TARGET_SCENE} must be present in CDSE catalogue.")
        self.assertEqual(target["platform"], "Sentinel-1D")
        self.assertEqual(target["relative_orbit"], 150)
        self.assertEqual(target["orbit_direction"], "DESCENDING")
        self.assertTrue(target["sensing_start_utc"].startswith("2026-08-20"))

    def test_02_slc_disk_integrity(self):
        """Verifies physical directory layout, measurement TIFF, and XML annotations."""
        self.assertTrue(os.path.isdir(self.target_dir), f"Directory {self.target_dir} must exist.")

        # Check measurement directory and TIFF file
        meas_dir = os.path.join(self.target_dir, "measurement")
        self.assertTrue(os.path.isdir(meas_dir))
        tiffs = [f for f in os.listdir(meas_dir) if f.endswith(".tiff")]
        self.assertGreater(len(tiffs), 0, "Measurement TIFF must be present.")
        tiff_path = os.path.join(meas_dir, tiffs[0])
        tiff_sz = os.path.getsize(tiff_path)
        self.assertGreater(tiff_sz, 1000 * 1024 * 1024, "Measurement TIFF must exceed 1000 MB.")

        # Verify TIFF header (II*\0 for little-endian TIFF)
        with open(tiff_path, "rb") as f:
            header = f.read(4)
        self.assertEqual(header, b"II*\x00", "Must have valid little-endian TIFF magic bytes.")

        # Check annotation directory and XML files
        annot_dir = os.path.join(self.target_dir, "annotation")
        self.assertTrue(os.path.isdir(annot_dir))
        annot_xmls = [f for f in os.listdir(annot_dir) if f.endswith(".xml")]
        self.assertGreater(len(annot_xmls), 0, "Main annotation XML must be present.")

        # Check calibration subdirectories
        cal_dir = os.path.join(annot_dir, "calibration")
        self.assertTrue(os.path.isdir(cal_dir))
        self.assertTrue(any(f.startswith("calibration-") for f in os.listdir(cal_dir)))
        self.assertTrue(any(f.startswith("noise-") for f in os.listdir(cal_dir)))

        # Check manifest.safe
        manifest_safe = os.path.join(self.target_dir, "manifest.safe")
        self.assertTrue(os.path.isfile(manifest_safe))
        self.assertGreater(os.path.getsize(manifest_safe), 10000)

    def test_03_google_drive_cloud_archival(self):
        """Verifies that all scene components are archived to Google Drive."""
        self.assertTrue(os.path.isfile(self.manifest_path))
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        records = manifest.get("archived_records", {})
        archived_target_files = {k: v for k, v in records.items() if TARGET_SCENE in k}
        self.assertGreaterEqual(
            len(archived_target_files), 5,
            f"At least 5 files from {TARGET_SCENE} must be recorded in Google Drive archive manifest."
        )

        for path, rec in archived_target_files.items():
            self.assertIn("remote_file_id", rec)
            self.assertTrue(rec["remote_file_id"])
            self.assertEqual(rec.get("retention_policy"), "KEEP")

    def test_04_provenance_catalog_ingestion(self):
        """Verifies ingestion record creation and metadata persistence."""
        ing_path = os.path.join(self.target_dir, "ingestion_record.json")
        self.assertTrue(os.path.isfile(ing_path), "Ingestion record JSON must be saved in product directory.")

        with open(ing_path, "r", encoding="utf-8") as f:
            rec = json.load(f)

        self.assertEqual(rec.get("source"), "SENTINEL1_SLC")
        self.assertEqual(rec.get("product_id"), TARGET_SCENE)
        self.assertEqual(rec.get("swath"), "IW1")
        self.assertEqual(rec.get("polarization"), "VV")
        self.assertEqual(rec.get("quality_status"), "ACQUISITION_VERIFIED")
        self.assertEqual(rec.get("retention_policy"), "KEEP")
        self.assertIn("observation_time", rec)
        self.assertIn("ingested_time", rec)
        self.assertIn("files_sha256", rec)

    def test_05_sbas_network_expansion(self):
        """Verifies that the SBAS stack contains the 3 repeat-pass nodes and valid edges."""
        local_scenes = [d for d in os.listdir(self.slc_dir) if d.endswith(".SAFE")]
        self.assertGreaterEqual(len(local_scenes), 3, "Stack must contain at least 3 repeat-pass scenes.")

        net = multitemporal_slc_manager.generate_sbas_network()
        self.assertIsInstance(net, dict)
        self.assertEqual(net.get("network_type"), "SBAS_SMALL_BASELINE_NETWORK")
        self.assertGreaterEqual(net.get("number_of_interferometric_edges", 0), 2)

        # Check edge pairs (12-day pairs)
        edges = net.get("edges", [])
        temp_baselines = [e["temporal_baseline_days"] for e in edges]
        self.assertIn(12.0, temp_baselines, "12-day repeat pass baseline must exist in SBAS network.")

    def test_06_scheduler_deduplication(self):
        """Verifies that polling an already acquired and ingested scene returns ALREADY_CURRENT."""
        res = self.scheduler.poll_source("ESA_SENTINEL1_INSAR_01")
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("source_id"), "ESA_SENTINEL1_INSAR_01")
        self.assertEqual(res.get("poll_result"), "ALREADY_CURRENT")
        self.assertFalse(res.get("new_observation_ingested"))
        self.assertFalse(res.get("reassessment_triggered"))
        self.assertEqual(res.get("status"), "NO_NEW_PRODUCT")

    def test_07_frozen_baseline_invariants(self):
        """Verifies that operational risk formula weights and model files remain strictly untouched."""
        from fusion_engine import get_multi_source_status
        status = get_multi_source_status()
        weights = status.get("weights", {})
        self.assertEqual(weights.get("w1_susceptibility"), 0.40)
        self.assertEqual(weights.get("w2_rainfall_anomaly"), 0.30)
        self.assertEqual(weights.get("w3_soil_moisture_anomaly"), 0.20)
        self.assertEqual(weights.get("w4_satellite_surface_change"), 0.10)


if __name__ == "__main__":
    unittest.main()
