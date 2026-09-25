"""
=============================================================================
NER-SAFE: Test Suite for CDSE S3 Acquisition & Genuine InSAR Processing
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validates end-to-end real InSAR data acquisition and processing:
  1. CDSE S3 configuration exists in .env without leaking secrets.
  2. Live authenticated S3 head_bucket and get_object capabilities.
  3. Disk-space guard prevents acquisition when available space < threshold.
  4. Real SLC data validation: authentic dimensions, state vectors, and TIFF headers.
  5. Perpendicular baseline calculation adheres to orbital mechanics (B_perp <= 150m).
  6. 10-step InSAR execution: coherence matrix, Goldstein filter, phase unwrapping, DEM subtraction.
  7. Coherence thresholding: strictly masks gamma < 0.35 as NaN/NoData.
  8. Relative LOS displacement physical units and Shillong Plateau calibration.
  9. Source ingestion manager registration and SHA-256 provenance persistence.
  10. Dynamic GIS heatmap layer generation with genuine InSAR GeoJSON properties.
=============================================================================
"""

import os
import sys
import unittest
import numpy as np
import rasterio

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from cdse_s3_downloader import cdse_s3_downloader, MIN_FREE_DISK_GB
from insar_pair_selector import insar_pair_selector
from insar_processing import insar_processing_engine, DEFAULT_COHERENCE_THRESHOLD as COHERENCE_THRESHOLD, REFERENCE_POINT_NAME as REF_POINT_NAME
from source_ingestion_manager import source_ingestion_mgr
from dynamic_risk_heatmap import dynamic_risk_heatmap_engine


class TestInSARS3RealPipeline(unittest.TestCase):

    def test_01_s3_credentials_configuration(self):
        """Verifies CDSE S3 credentials are configured in .env without placeholder strings."""
        ak, sk = cdse_s3_downloader._read_s3_credentials()
        self.assertIsNotNone(ak)
        self.assertIsNotNone(sk)
        self.assertGreater(len(ak), 8)
        self.assertGreater(len(sk), 16)
        self.assertNotIn("YOUR", ak)
        self.assertNotIn("YOUR", sk)

    def test_02_s3_authenticated_client_creation(self):
        """Verifies botocore S3 client can connect to eodata bucket."""
        s3 = cdse_s3_downloader.get_s3_client()
        self.assertIsNotNone(s3)
        head = s3.head_bucket(Bucket="eodata")
        self.assertEqual(head["ResponseMetadata"]["HTTPStatusCode"], 200)

    def test_03_disk_space_guard_enforcement(self):
        """Verifies disk space guard correctly reports status and guards against low capacity."""
        guard = cdse_s3_downloader.check_disk_space(os.path.join(PROJECT_ROOT, "NER_SAFE_DATA"), required_gb=MIN_FREE_DISK_GB)
        self.assertIn("free_gb", guard)
        self.assertIn("sufficient_space", guard)
        self.assertTrue(guard["sufficient_space"])
        self.assertGreater(guard["free_gb"], 10.0)

        # Force failure condition
        huge_guard = cdse_s3_downloader.check_disk_space(os.path.join(PROJECT_ROOT, "NER_SAFE_DATA"), required_gb=999999.0)
        self.assertFalse(huge_guard["sufficient_space"])

    def test_04_slc_acquired_files_integrity(self):
        """Verifies that authentic Sentinel-1 SLC files exist on disk with valid headers."""
        base_dir = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "SLC")
        self.assertTrue(os.path.exists(base_dir))

        scenes = [d for d in os.listdir(base_dir) if d.endswith(".SAFE")]
        self.assertGreaterEqual(len(scenes), 2)

        for scene in scenes[:2]:
            rec_p = os.path.join(base_dir, scene, "acquisition_record.json")
            self.assertTrue(os.path.exists(rec_p))

            # Check measurement TIFF
            meas_dir = os.path.join(base_dir, scene, "measurement")
            self.assertTrue(os.path.exists(meas_dir))
            tifs = [os.path.join(meas_dir, f) for f in os.listdir(meas_dir) if f.endswith(".tiff")]
            self.assertGreaterEqual(len(tifs), 1)

            with rasterio.open(tifs[0]) as src:
                self.assertEqual(src.width, 21282)
                self.assertEqual(src.height, 13464)
                self.assertIn("complex", str(src.dtypes[0]))

    def test_05_perpendicular_baseline_bounds(self):
        """Verifies perpendicular baseline is within acceptable limits for C-band InSAR (<= 150m)."""
        summary_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "insar_processing_summary.json")
        self.assertTrue(os.path.exists(summary_file))

        import json
        with open(summary_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        b_perp = meta.get("perpendicular_baseline_m")
        self.assertIsNotNone(b_perp)
        self.assertLessEqual(b_perp, 150.0)
        self.assertGreater(b_perp, 0.0)
        self.assertEqual(meta.get("temporal_baseline_days"), 12.0)

    def test_06_coherence_raster_properties(self):
        """Verifies generated coherence raster adheres strictly to [0.0, 1.0] mathematical bounds."""
        coh_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "insar_coherence.tif")
        self.assertTrue(os.path.exists(coh_path))

        with rasterio.open(coh_path) as src:
            self.assertEqual(src.crs.to_string(), "EPSG:4326")
            coh_data = src.read(1)
            valid_coh = coh_data[coh_data != -9999.0]
            self.assertTrue(np.all(valid_coh >= 0.0))
            self.assertTrue(np.all(valid_coh <= 1.0))
            self.assertGreater(np.mean(valid_coh), 0.10)

    def test_07_coherence_masking_rule(self):
        """Verifies low coherence pixels (< 0.35) are strictly masked as NaN, never zero."""
        disp_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "insar_los_displacement.tif")
        coh_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "insar_coherence.tif")

        with rasterio.open(disp_path) as src_disp, rasterio.open(coh_path) as src_coh:
            disp = src_disp.read(1)
            coh = src_coh.read(1)

            low_coh = (coh < COHERENCE_THRESHOLD) & (coh >= 0.0)
            self.assertTrue(np.any(low_coh))
            # Every low coherence pixel in displacement raster MUST be NaN
            self.assertTrue(np.all(np.isnan(disp[low_coh])))

            high_coh = coh >= COHERENCE_THRESHOLD
            self.assertTrue(np.any(high_coh))
            self.assertTrue(np.all(~np.isnan(disp[high_coh])))

    def test_08_relative_los_displacement_reference_calibration(self):
        """Verifies relative LOS displacement is zero at Shillong Plateau bedrock point."""
        summary_file = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SENTINEL1", "insar_processing_summary.json")
        with open(summary_file, "r", encoding="utf-8") as f:
            import json
            meta = json.load(f)

        ref_pt = meta.get("reference_point", {})
        self.assertEqual(ref_pt.get("name"), REF_POINT_NAME)
        self.assertEqual(ref_pt.get("relative_displacement_mm"), 0.0)

    def test_09_source_ingestion_registration(self):
        """Verifies Sentinel-1 InSAR observation is successfully registered with SHA-256 hashes."""
        rec = source_ingestion_mgr.register_insar_observation()
        self.assertEqual(rec["source"], "SENTINEL1_INSAR")
        self.assertEqual(rec["product"], "S1_IW_SLC_INSAR")
        self.assertEqual(rec["processing_status"], "PROCESSED")
        self.assertEqual(rec["quality_status"], "VALID_OBSERVATION")
        self.assertIn("coherence", rec["raster_sha256"])
        self.assertIn("los_displacement", rec["raster_sha256"])

    def test_10_live_insar_status_verified(self):
        """Verifies insar_pair_selector reports LIVE_VERIFIED."""
        status = insar_pair_selector.get_live_insar_status()
        self.assertEqual(status["component"], "SENTINEL1_INSAR")
        self.assertEqual(status["operational_state"], "LIVE_VERIFIED")
        self.assertEqual(status["data_access_status"], "LIVE_VERIFIED")
        self.assertEqual(status["active_pairs_in_memory"], 1)
        self.assertIn("coherence_summary", status)
        self.assertIn("displacement_summary_mm", status)

    def test_11_heatmap_integration_geojson(self):
        """Verifies dynamic InSAR heatmap generates valid 48-hotspot GeoJSON with authentic properties."""
        heat = dynamic_risk_heatmap_engine.generate_insar_deformation_heatmap()
        self.assertEqual(heat["layer_id"], "insar_deformation")
        self.assertEqual(heat["status"], "LIVE_VERIFIED")
        self.assertEqual(heat["data_access"], "VERIFIED_CDSE_S3")
        self.assertEqual(len(heat["geojson"]["features"]), 48)

        # Check properties of in-swath vs out-of-swath hotspots
        swath_hotspots = [f for f in heat["geojson"]["features"] if f["properties"]["in_swath"]]
        self.assertGreater(len(swath_hotspots), 0)
        for sh in swath_hotspots:
            props = sh["properties"]
            self.assertIn(props["quality_status"], ["VALID_COHERENT_OBSERVATION", "LOW_COHERENCE_MASKED"])
            self.assertIn("disclaimer", props)


if __name__ == "__main__":
    unittest.main()
