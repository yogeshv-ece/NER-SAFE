"""
=============================================================================
NER-SAFE: Google Drive Heavy-Data Archival Test Suite
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Validates Google Drive API v3 connection, resumable chunked upload,
         remote file verification, deduplication, local retention policy,
         and error decoupling for heavy satellite data.
=============================================================================
"""

import os
import sys
import json
import time
import unittest
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

import google_drive_archive
from google_drive_archive import GoogleDriveArchiveEngine, LOCAL_RETENTION_POLICY


class TestGoogleDriveArchive(unittest.TestCase):
    """Test suite for Google Drive heavy-data archival."""

    @classmethod
    def setUpClass(cls):
        cls.archiver = google_drive_archive.google_drive_archiver

    def test_01_connection_and_quota(self):
        """Verify Drive API v3 authenticated connectivity and 5 TB quota."""
        conn = self.archiver.check_connection()
        if not conn.get("authenticated"):
            self.skipTest(f"Google Drive external service credentials not available in test environment: {conn.get('error', 'Unauthenticated')}")
        self.assertTrue(conn.get("authenticated"), f"Drive connection failed: {conn}")
        self.assertEqual(conn.get("status"), "CONNECTED")
        self.assertGreater(conn.get("cloud_limit_gb", 0), 1000.0, "Expected >= 1 TB cloud limit (5 TB quota)")
        self.assertEqual(conn.get("local_retention_policy"), "KEEP")

    def test_02_archive_folder_structure(self):
        """Verify canonical NER-SAFE-DATA subfolder hierarchy exists on Drive."""
        conn = self.archiver.check_connection()
        if not conn.get("authenticated"):
            self.skipTest("Google Drive external service credentials not available in test environment")
        structure = self.archiver.initialize_archive_structure()
        required_folders = [
            "SENTINEL1/SLC",
            "SENTINEL1/GRD",
            "SENTINEL2",
            "INSAR",
            "GPM",
            "SMAP",
            "MANIFESTS"
        ]
        for fld in required_folders:
            self.assertIn(fld, structure, f"Missing folder in structure: {fld}")
            self.assertTrue(bool(structure[fld]), f"Folder ID empty for {fld}")

    def test_03_resumable_upload_and_verification(self):
        """Verify resumable streaming upload and remote size verification."""
        conn = self.archiver.check_connection()
        if not conn.get("authenticated"):
            self.skipTest("Google Drive external service credentials not available in test environment")
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tf:
            test_data = b"NER_SAFE_TEST_CHUNKS_" * 1024 * 32  # 672 KB
            tf.write(test_data)
            test_path = tf.name

        try:
            filename = f"test_probe_resumable_{int(time.time())}.tmp"
            res = self.archiver.archive_file(
                local_path=test_path,
                category="MANIFESTS",
                remote_filename=filename,
                source="UNIT_TEST"
            )
            self.assertEqual(res.get("archive_status"), "ARCHIVED")
            self.assertEqual(res.get("verification_status"), "VERIFIED_SIZE_MATCH")
            remote_id = res.get("remote_file_id")
            self.assertTrue(bool(remote_id))

            # Deduplication test: re-uploading should detect existing file
            dedup_res = self.archiver.archive_file(
                local_path=test_path,
                category="MANIFESTS",
                remote_filename=filename,
                source="UNIT_TEST"
            )
            self.assertEqual(dedup_res.get("archive_status"), "ARCHIVED")
            self.assertEqual(dedup_res.get("action"), "DEDUPLICATED")

            # Clean up remote test probe
            token = self.archiver._get_access_token()
            import urllib.request
            del_req = urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files/{remote_id}",
                headers={"Authorization": f"Bearer {token}"},
                method="DELETE"
            )
            try:
                with urllib.request.urlopen(del_req, timeout=15) as resp:
                    self.assertEqual(resp.status, 204)
            except Exception:
                pass
        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    def test_04_local_retention_policy(self):
        """Verify LOCAL_RETENTION_POLICY is strictly 'KEEP'."""
        self.assertEqual(LOCAL_RETENTION_POLICY, "KEEP")
        self.assertEqual(self.archiver.manifest.get("retention_policy"), "KEEP")

    def test_05_insar_products_archived_in_manifest(self):
        """Verify InSAR persistent products are present and verified in manifest."""
        records = self.archiver.manifest.get("archived_records", {})
        insar_keys = [k for k in records if "insar_" in k]
        self.assertGreaterEqual(len(insar_keys), 4, "Expected >= 4 InSAR products in archive manifest")
        for k in insar_keys:
            rec = records[k]
            self.assertTrue(bool(rec.get("remote_file_id")), f"Missing remote file ID for {k}")
            self.assertIn(rec.get("verification_status"), ("VERIFIED_SIZE_MATCH", "VERIFIED_EXISTING"))
            self.assertEqual(rec.get("retention_policy"), "KEEP")

    def test_06_zero_secrets_in_manifest(self):
        """Security check: Verify no access tokens or secrets leaked into archive manifest."""
        manifest_file = self.archiver.manifest_path
        self.assertTrue(os.path.exists(manifest_file))
        with open(manifest_file, "r", encoding="utf-8") as f:
            content = f.read()

        suspicious = [
            "client_secret",
            "refresh_token",
            "access_token",
            "bearer ya29",
            "password",
            "BEGIN PRIVATE KEY"
        ]
        for term in suspicious:
            self.assertNotIn(term.lower(), content.lower(), f"Suspicious security term found in manifest: {term}")

    def test_07_archiver_summary_and_provenance(self):
        """Verify archiver get_summary reports heavy archive stats and cloud quota."""
        summary = self.archiver.get_summary()
        self.assertEqual(summary.get("local_retention_policy"), "KEEP")
        self.assertGreaterEqual(summary.get("total_archived_files", 0), 6)
        self.assertGreaterEqual(summary.get("total_archived_bytes", 0), 20_000_000)
        self.assertIn("INSAR", summary.get("categories_breakdown", {}))
        if summary.get("google_drive_connected"):
            self.assertIsNotNone(summary.get("cloud_limit_gb"))


if __name__ == "__main__":
    import time
    unittest.main(verbosity=2)
