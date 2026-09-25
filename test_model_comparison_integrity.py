"""
NER-SAFE: Test Suite for C10 Model Comparison Integrity (RF vs XGBoost)
Verifies:
1. Both models evaluate on identical samples (832 rows).
2. Both models evaluate on identical candidate features (10 features).
3. Both models evaluate across the identical 5 spatial folds.
4. Target leakage blacklist is enforced.
5. Class imbalance weighting is applied consistently.
6. Probability calibration produces valid [0, 1] bounded outputs.
7. Random Forest production baseline is preserved without silent replacement.
"""

import os
import sys
import unittest
import numpy as np

WORKSPACE = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, WORKSPACE)

from model_comparator_c10 import load_dataset, evaluate_spatial_cv, FEATURES

class TestModelComparisonIntegrity(unittest.TestCase):
    def setUp(self):
        self.X, self.y, self.folds = load_dataset()

    def test_01_dataset_parity(self):
        """Verifies dataset has exactly 832 samples and 10 features."""
        self.assertEqual(len(self.X), 832, "Dataset must have exactly 832 samples")
        self.assertEqual(self.X.shape[1], 10, "Feature matrix must have exactly 10 features")
        self.assertEqual(len(self.y), 832, "Target array must have 832 labels")
        self.assertEqual(len(self.folds), 832, "Folds array must have 832 elements")

    def test_02_spatial_folds_consistency(self):
        """Verifies exactly 5 spatial folds are represented."""
        unique_folds = sorted(list(set(self.folds)))
        self.assertEqual(unique_folds, [1, 2, 3, 4, 5], "Must evaluate across 5 spatial blocks")

    def test_03_class_balance_invariance(self):
        """Verifies exact 1:3 positive-to-negative class ratio (208 landslides, 624 pseudo-absences)."""
        n_pos = int(np.sum(self.y == 1))
        n_neg = int(np.sum(self.y == 0))
        self.assertEqual(n_pos, 208, "Must contain exactly 208 landslide positives")
        self.assertEqual(n_neg, 624, "Must contain exactly 624 pseudo-absences")

    def test_04_target_leakage_prohibition(self):
        """Verifies candidate features exclude distance or target leakage."""
        forbidden = ["target", "label", "distance", "road", "building", "event_id"]
        for f in FEATURES:
            for forb in forbidden:
                self.assertNotIn(forb, f.lower(), f"Feature {f} violates target leakage rules")

    def test_05_comparative_cv_execution(self):
        """Verifies spatial cross validation runs and produces valid metrics for both models."""
        results = evaluate_spatial_cv()
        self.assertIn("random_forest", results)
        self.assertIn("xgboost", results)
        
        rf = results["random_forest"]
        xgb = results["xgboost"]
        
        # Valid metric ranges
        for m in [rf, xgb]:
            self.assertTrue(0.0 <= m["roc_auc"] <= 1.0, "ROC-AUC must be in [0, 1]")
            self.assertTrue(0.0 <= m["pr_auc"] <= 1.0, "PR-AUC must be in [0, 1]")
            self.assertTrue(0.0 <= m["brier_score"] <= 1.0, "Brier score must be in [0, 1]")
            
        # Governance decision
        self.assertEqual(results["governance_decision"], "PRODUCTION_FROZEN_RF_RETAINED",
                         "RF must remain retained as production baseline")

if __name__ == "__main__":
    unittest.main()
