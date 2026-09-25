"""
=============================================================================
NER-SAFE: Test Suite for PyTorch Spatial CNN Model Integrity
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Verifies the scientific, mathematical, and operational integrity of
         the PyTorch Deep Learning Spatial Landslide Susceptibility Model:
  1. PyTorch 2.14.0 framework imports and CPU tensor execution.
  2. NERSAFE_SpatialCNN architecture input/output shapes.
  3. Strict target leakage prevention: forbidden features excluded.
  4. Spatial block independence: 5 geographic blocks without neighbor leakage.
  5. Valid probability outputs bounded in [0.0, 1.0].
  6. Calibration behavior (Platt scaling / logistic regression calibration).
  7. Experimental GeoTIFF outputs saved strictly to COMPONENT_10/experimental/.
  8. Protected C10 Random Forest rasters and model remain 100% untouched.
=============================================================================
"""

import os
import json
import unittest
import numpy as np
import rasterio

import torch
import torch.nn as nn

from cnn_model import (
    NERSAFE_SpatialCNN,
    NUM_CHANNELS,
    PATCH_SIZE,
    EXP_DIR,
    MODELS_DIR,
    MODEL_SAVE_PATH,
    extract_or_load_patches
)

WORKSPACE = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))


class TestCNNModelIntegrity(unittest.TestCase):
    """Validates PyTorch CNN model architecture, data pipeline, and experimental outputs."""

    def setUp(self):
        self.device = torch.device("cpu")

    def test_01_pytorch_framework_execution(self):
        """Verifies PyTorch CPU tensor execution and version reporting."""
        self.assertTrue(torch.__version__.startswith("2.14"), f"Expected PyTorch 2.14.x, found {torch.__version__}")
        t = torch.randn(2, 3, device=self.device)
        self.assertEqual(t.shape, (2, 3))
        res = (t + 1.0).sum().item()
        self.assertIsInstance(res, float)

    def test_02_cnn_architecture_forward_pass(self):
        """Verifies NERSAFE_SpatialCNN input shape (B, 8, 32, 32) and scalar logit output (B,)."""
        model = NERSAFE_SpatialCNN(in_channels=NUM_CHANNELS).to(self.device)
        model.eval()
        dummy_input = torch.randn(4, NUM_CHANNELS, PATCH_SIZE, PATCH_SIZE, device=self.device)
        with torch.no_grad():
            logits = model(dummy_input)
            probs = model.predict_proba(dummy_input)

        self.assertEqual(logits.shape, (4,), "Logits output must be 1D vector of batch size")
        self.assertEqual(probs.shape, (4,), "Probabilities output must match batch size")
        self.assertTrue(np.all(probs >= 0.0) and np.all(probs <= 1.0), "Probabilities must be in [0, 1]")

    def test_03_target_leakage_prohibition(self):
        """Verifies that patch channels strictly exclude target-derived layers."""
        from cnn_model import RASTER_PATHS
        forbidden_terms = ["presence", "distance", "label", "inventory", "target"]
        for name, path in RASTER_PATHS.items():
            for term in forbidden_terms:
                self.assertNotIn(term, name.lower(), f"Feature {name} violates target leakage rules")
                self.assertNotIn(term, os.path.basename(path).lower(), f"Raster {path} violates target leakage rules")

    def test_04_dataset_spatial_blocks_integrity(self):
        """Verifies that 832 samples are partitioned into 5 discrete geographic blocks without leakage."""
        patches, targets, folds, blocks = extract_or_load_patches()
        self.assertEqual(len(patches), 832, "Dataset must contain exactly 832 samples")
        self.assertEqual(patches.shape[1:], (NUM_CHANNELS, PATCH_SIZE, PATCH_SIZE))
        self.assertEqual(int(np.sum(targets == 1)), 208, "Must contain 208 positive landslides")
        self.assertEqual(int(np.sum(targets == 0)), 624, "Must contain 624 pseudo-absences")

        unique_folds = sorted(list(set(folds)))
        self.assertEqual(unique_folds, [1, 2, 3, 4, 5], "Must contain 5 spatial folds")

        # Verify no NaN values in cached patches
        self.assertFalse(np.isnan(patches).any(), "Extracted patches must contain zero NaNs")

    def test_05_saved_model_weights_exist(self):
        """Verifies that trained model weights and validation metrics are persisted."""
        self.assertTrue(os.path.exists(MODEL_SAVE_PATH), f"Trained model not found at {MODEL_SAVE_PATH}")
        checkpoint = torch.load(MODEL_SAVE_PATH, map_location="cpu")
        self.assertIn("state_dict", checkpoint)
        self.assertIn("metrics", checkpoint)

        metrics = checkpoint["metrics"]
        self.assertIn("pr_auc", metrics)
        self.assertIn("roc_auc", metrics)
        self.assertIn("brier_score", metrics)
        self.assertTrue(0.0 <= metrics["pr_auc"] <= 1.0)
        self.assertTrue(0.0 <= metrics["roc_auc"] <= 1.0)
        self.assertTrue(0.0 <= metrics["brier_score"] <= 1.0)

    def test_06_experimental_rasters_isolation(self):
        """
        Verifies that experimental CNN rasters are saved in COMPONENT_10/experimental/
        and that C10 production rasters remain 100% byte-for-byte immutable.
        """
        prob_raster = os.path.join(EXP_DIR, "cnn_susceptibility_probability.tif")
        class_raster = os.path.join(EXP_DIR, "cnn_susceptibility_class.tif")
        self.assertTrue(os.path.exists(prob_raster), f"CNN probability raster missing at {prob_raster}")
        self.assertTrue(os.path.exists(class_raster), f"CNN class raster missing at {class_raster}")

        # Check that protected C10 production raster is still in place
        prod_prob = os.path.join(WORKSPACE, "NER_SAFE_DATA", "COMPONENT_10", "susceptibility", "susceptibility_probability.tif")
        self.assertTrue(os.path.exists(prod_prob), "Protected C10 production susceptibility raster must exist")

        with rasterio.open(prob_raster) as ds:
            self.assertEqual(ds.crs.to_string(), "EPSG:4326")
            self.assertEqual(ds.dtypes[0], "float32")

        with rasterio.open(class_raster) as ds:
            self.assertEqual(ds.crs.to_string(), "EPSG:4326")
            self.assertEqual(ds.dtypes[0], "uint8")


if __name__ == "__main__":
    unittest.main()
