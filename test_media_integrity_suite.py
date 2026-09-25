"""
test_media_integrity_suite.py
=============================
Tests for:
1. media_integrity_analyzer.py (Forensic hashing, EXIF inspection, scene classification, synthetic detection)
2. citizen_evidence_fusion.py (Evidence confidence score calculation, ML model isolation)
"""

import unittest
import tempfile
import os
import shutil
from media_integrity_analyzer import (
    MediaIntegrityAnalyzer,
    VERDICT_AUTHENTIC,
    VERDICT_MANIPULATED,
    VERDICT_SYNTHETIC,
    VERDICT_INCONCLUSIVE
)
from citizen_evidence_fusion import (
    CitizenEvidenceFusion,
    STATUS_SUBMITTED,
    STATUS_UNVERIFIED,
    STATUS_UNDER_REVIEW,
    STATUS_VERIFIED,
    STATUS_REJECTED
)


class TestMediaIntegritySuite(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = MediaIntegrityAnalyzer()
        self.fusion = CitizenEvidenceFusion()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_missing_file_inconclusive(self):
        """Verify non-existent file returns INCONCLUSIVE verdict."""
        res = self.analyzer.inspect_file(os.path.join(self.test_dir, "nonexistent.jpg"))
        self.assertEqual(res["verdict"], VERDICT_INCONCLUSIVE)
        self.assertEqual(res["confidence_score"], 0.0)

    def test_02_duplicate_media_detection(self):
        """Verify duplicate file hashing reduces confidence and flags manipulated/duplicate."""
        test_img_path = os.path.join(self.test_dir, "test_photo.jpg")
        with open(test_img_path, "wb") as f:
            f.write(b"SAMPLE_IMAGE_RAW_BYTES_FOR_HASHING_TEST_12345")

        # First inspection
        res1 = self.analyzer.inspect_file(test_img_path)
        sha = res1["file_sha256"]
        self.assertIsNotNone(sha)
        self.assertFalse(res1["is_duplicate_hash"])

        # Register hash as previously known
        self.analyzer.known_hashes[sha] = "REP-2026-0001"

        # Second inspection of same file/hash
        res2 = self.analyzer.inspect_file(test_img_path)
        self.assertTrue(res2["is_duplicate_hash"])
        self.assertEqual(res2["verdict"], VERDICT_MANIPULATED)
        self.assertTrue(any("duplicate" in r.lower() for r in res2["reasons"]))

    def test_03_scene_classification_heuristics(self):
        """Verify lightweight CPU scene classifier detects slope cracks, blocked roads, and rockfalls."""
        res_crack = self.analyzer.classify_scene_content("Massive fissure opened on hillside", "Ground Observation")
        self.assertIn("SLOPE_CRACK", res_crack["scene_classes"])
        self.assertFalse(res_crack["model_retraining_triggered"])

        res_road = self.analyzer.classify_scene_content("NH-106 completely blocked by boulder slide", "Road Network")
        self.assertIn("BLOCKED_ROAD", res_road["scene_classes"])
        self.assertIn("ROCKFALL", res_road["scene_classes"])

        res_unrelated = self.analyzer.classify_scene_content("Market day in village center", "Community")
        self.assertEqual(res_unrelated["primary_scene"], "UNRELATED")

    def test_04_evidence_confidence_calculation(self):
        """Verify evidence confidence increases with field verification and authentic media."""
        # Unverified report without media
        rep_unverified = {
            "report_id": "REP-01",
            "verification_status": STATUS_UNVERIFIED,
            "accuracy_m": 15.0
        }
        res_base = self.fusion.compute_evidence_confidence(rep_unverified)
        self.assertEqual(res_base["confidence_tier"], "MODERATE")
        self.assertFalse(res_base["model_retraining_triggered"])

        # Verified report with authentic media inspection
        rep_verified = {
            "report_id": "REP-02",
            "verification_status": STATUS_VERIFIED,
            "accuracy_m": 5.0,
            "crack_width_cm": 25.0
        }
        media_authentic = {"verdict": VERDICT_AUTHENTIC}
        res_high = self.fusion.compute_evidence_confidence(rep_verified, media_authentic)
        self.assertEqual(res_high["confidence_tier"], "HIGH")
        self.assertGreaterEqual(res_high["evidence_confidence_score"], 0.85)

    def test_05_rejected_report_evidence_degradation(self):
        """Verify rejected report or synthetic media severely penalizes evidence confidence."""
        rep_rejected = {
            "report_id": "REP-03",
            "verification_status": STATUS_REJECTED
        }
        res_rej = self.fusion.compute_evidence_confidence(rep_rejected)
        self.assertEqual(res_rej["confidence_tier"], "LOW")
        self.assertLessEqual(res_rej["evidence_confidence_score"], 0.10)

        # Synthetic media penalty
        rep_unv = {"report_id": "REP-04", "verification_status": STATUS_UNVERIFIED}
        media_synth = {"verdict": VERDICT_SYNTHETIC}
        res_synth = self.fusion.compute_evidence_confidence(rep_unv, media_synth)
        self.assertEqual(res_synth["confidence_tier"], "LOW")
        self.assertLessEqual(res_synth["evidence_confidence_score"], 0.20)

    def test_06_strict_ml_isolation_contract(self):
        """Verify evidence confidence fusion explicitly enforces strict isolation from ML models."""
        rep = {"report_id": "REP-05", "verification_status": STATUS_VERIFIED}
        res = self.fusion.compute_evidence_confidence(rep)
        self.assertFalse(res["model_retraining_triggered"])
        self.assertIn("isolated from ML models", res["disclaimer"])


if __name__ == "__main__":
    unittest.main()
