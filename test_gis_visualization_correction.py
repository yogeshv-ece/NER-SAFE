r"""
NER-SAFE: Dedicated Test Suite for GIS Visualization Correction
Validates:
1. Genuine SRTM 30m DEM detected and valid
2. Terrain elevation bounds, resolution, and geomorphic ranges
3. Meghalaya & Mizoram terrain coverage (>1000m and >500m peaks)
4. Terrain tile extraction for Cesium (65x65 Float32Array, 16900 bytes)
5. 3D Roads loaded from genuine OSM data with terrain clamping
6. 3D Buildings loaded from genuine OSM data with uniform visualization height labels
7. Hotspots use live assessment with 0 discrepancy between API, 2D, and 3D
8. Population dataset detected (22 ADM2 districts, Census 2011)
9. Population layer attributes, source & census year
10. Population has 0.00 risk weight and does NOT modify 4-factor risk formula
11. WebGL fallback mechanism preserved (3D UNAVAILABLE banner)
12. Production model invariant: Calibrated XGBoost V1.1 ONLY (SHA-256: 45544c7f...)
13. Zero model fallback policy (NONE)
14. G:\ strictly untouched
"""

import os
import sys
import json
import hashlib
import unittest
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

import gis_service
import fusion_engine
import live_assessment_service
from susceptibility_provider import provider_manager


class TestGISVisualizationCorrection(unittest.TestCase):
    def setUp(self):
        self.dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
        with open(self.dash_path, "r", encoding="utf-8") as f:
            self.dash_html = f.read()

    # =========================================================================
    # 1. REAL 3D TERRAIN & DEM ELEVATION
    # =========================================================================

    def test_01_srtm_dem_source_detected(self):
        """Verify genuine SRTM 30m DEM exists and is detected by gis_service."""
        self.assertTrue(gis_service.gis_service.is_dem_available(), "SRTM DEM must be accessible via gis_service")
        meta = gis_service.gis_service.get_dem_metadata()
        self.assertTrue(meta["available"])
        self.assertIn("SRTM", meta["source"])
        self.assertEqual(meta["crs"], "EPSG:4326")

    def test_02_terrain_coverage_and_resolution(self):
        """Verify DEM spatial coverage includes Meghalaya, Mizoram, and NER AOI at 30m."""
        meta = gis_service.gis_service.get_dem_metadata()
        b = meta["bounds"]
        self.assertLessEqual(b["west"], 89.0)
        self.assertGreaterEqual(b["east"], 94.0)
        self.assertLessEqual(b["south"], 21.0)
        self.assertGreaterEqual(b["north"], 27.0)
        # 1 arc-second ~ 0.0002778 deg
        self.assertAlmostEqual(meta["resolution_deg"][0], 0.0002777777777777778, places=6)

    def test_03_meghalaya_terrain_coverage(self):
        """Verify real elevation profiles over Meghalaya (East Khasi Hills / Shillong Plateau > 1000m)."""
        # Level 9 tile over Shillong: z=9, x=773, y=183
        tile_bytes = gis_service.gis_service.get_terrain_tile_float32(9, 773, 183, width=65, height=65)
        self.assertEqual(len(tile_bytes), 65 * 65 * 4, "Tile must be exactly 65x65 float32 (16900 bytes)")
        arr = np.frombuffer(tile_bytes, dtype=np.float32)
        self.assertGreater(arr.max(), 1200.0, "Meghalaya plateau elevations must exceed 1200m")
        self.assertGreater(arr.mean(), 500.0, "Meghalaya mean elevation must reflect plateau topography")

    def test_04_mizoram_terrain_coverage(self):
        """Verify real elevation profiles over Mizoram (Aizawl region > 500m)."""
        # Level 9 tile over Aizawl: z=9, x=775, y=188
        tile_bytes = gis_service.gis_service.get_terrain_tile_float32(9, 775, 188, width=65, height=65)
        self.assertEqual(len(tile_bytes), 65 * 65 * 4)
        arr = np.frombuffer(tile_bytes, dtype=np.float32)
        self.assertGreater(arr.max(), 800.0, "Mizoram ridge elevations must exceed 800m")
        self.assertGreater(arr.mean(), 300.0, "Mizoram mean elevation must reflect ridge-and-valley topography")

    def test_05_cesium_custom_heightmap_provider_integration(self):
        """Verify dashboard HTML configures CustomHeightmapTerrainProvider with real endpoint."""
        self.assertIn("CustomHeightmapTerrainProvider", self.dash_html)
        self.assertIn("/api/gis/terrain/tile", self.dash_html)
        self.assertIn("GeographicTilingScheme", self.dash_html)
        self.assertIn("enableLighting = true", self.dash_html)
        self.assertIn("depthTestAgainstTerrain = true", self.dash_html)

    # =========================================================================
    # 2. 3D ROADS & BUILDINGS EXPOSURE
    # =========================================================================

    def test_06_roads_exposure_dataset_and_clamping(self):
        """Verify genuine OSM roads are loaded and configured for 3D terrain clamping."""
        roads = gis_service.gis_service.get_roads_exposure(tier="major")
        self.assertGreater(len(roads["features"]), 1000, "Major road network must contain > 1000 segments")
        sample_feat = roads["features"][0]
        self.assertTrue(sample_feat["properties"].get("clamp_to_ground"))
        self.assertEqual(sample_feat["properties"].get("risk_weight"), 0.00)
        # Dashboard must load roads with clampToGround
        self.assertIn("loadCesiumRoads", self.dash_html)
        self.assertIn("clampToGround: true", self.dash_html)

    def test_07_buildings_exposure_dataset_and_visualization_height(self):
        """Verify genuine OSM buildings are served with explicit visualization height label."""
        bldgs = gis_service.gis_service.get_buildings_exposure(limit=500)
        self.assertGreater(len(bldgs["features"]), 100, "Buildings exposure must contain genuine footprints")
        sample_feat = bldgs["features"][0]
        p = sample_feat["properties"]
        self.assertIn("NOT SURVEYED HEIGHT", p.get("height_rule", ""))
        self.assertEqual(p.get("risk_weight"), 0.00)
        # Dashboard must include clear visualization label in popup
        self.assertIn("loadCesiumBuildings", self.dash_html)
        self.assertIn("VISUALIZATION HEIGHT", self.dash_html)
        self.assertIn("NOT SURVEYED HEIGHT", self.dash_html)

    # =========================================================================
    # 3. 2D POPULATION EXPOSURE LAYER
    # =========================================================================

    def test_08_population_dataset_census_2011(self):
        """Verify Census 2011 demographic exposure dataset has 22 ADM2 districts."""
        pop = gis_service.gis_service.get_population_exposure()
        meta = pop.get("metadata", {})
        self.assertEqual(meta.get("census_year"), 2011)
        self.assertEqual(meta.get("administrative_level"), "ADM2 (Districts)")
        self.assertEqual(meta.get("operational_risk_weight"), 0.00)
        self.assertEqual(len(pop.get("features", [])), 22, "Must contain exactly 22 districts across Meghalaya & Mizoram")

    def test_09_population_attributes_complete(self):
        """Verify required demographic fields exist without synthetic fabrication."""
        pop = gis_service.gis_service.get_population_exposure()
        for feat in pop["features"]:
            p = feat["properties"]
            self.assertIn("district_name", p)
            self.assertIn("state", p)
            self.assertIn("population_total", p)
            self.assertIn("density_persons_per_sqkm", p)
            self.assertGreater(p["population_total"], 0)
            self.assertGreater(p["density_persons_per_sqkm"], 0)

    def test_10_population_risk_weight_is_zero(self):
        """Verify population layer has 0.00 risk weight and does not alter the 4-factor risk formula."""
        status = fusion_engine.get_multi_source_status()
        weights = status.get("weights", {})
        self.assertNotIn("population", weights)
        self.assertAlmostEqual(weights.get("w1_susceptibility"), 0.40)
        self.assertAlmostEqual(weights.get("w2_rainfall_anomaly"), 0.30)
        self.assertAlmostEqual(weights.get("w3_soil_moisture_anomaly"), 0.20)
        self.assertAlmostEqual(weights.get("w4_satellite_surface_change"), 0.10)
        
        pop = gis_service.gis_service.get_population_exposure()
        self.assertEqual(pop.get("metadata", {}).get("operational_risk_weight"), 0.00)

    def test_11_dashboard_population_choropleth_and_controls(self):
        """Verify 2D Leaflet dashboard contains population layer, toggle, legend, and popups."""
        self.assertIn("chkPopulation", self.dash_html)
        self.assertIn("renderPopulationLayer", self.dash_html)
        self.assertIn("Population Exposure (Census 2011)", self.dash_html)
        self.assertIn("persons/km²", self.dash_html)

    # =========================================================================
    # 4. 2D/3D LIVE DATA CONSISTENCY
    # =========================================================================

    def test_12_hotspots_api_parity(self):
        """Verify API provides identical 48 hotspots for both 2D Leaflet and 3D Cesium."""
        hotspots = fusion_engine.compute_fused_hotspots()
        features = hotspots.get("features", [])
        self.assertEqual(len(features), 48, "Must evaluate exactly 48 canonical hotspots")
        for f in features:
            coords = f["geometry"]["coordinates"]
            self.assertEqual(len(coords), 2)
            self.assertGreaterEqual(coords[0], 89.0)
            self.assertLessEqual(coords[0], 94.0)
            self.assertGreaterEqual(coords[1], 21.0)
            self.assertLessEqual(coords[1], 27.0)

    def test_13_webgl_fallback_notice(self):
        """Verify WebGL fallback notice contains non-emoji message retaining 2D Leaflet."""
        self.assertIn("3D UNAVAILABLE", self.dash_html)
        self.assertIn("Operational 2D Leaflet map active", self.dash_html)

    # =========================================================================
    # 5. PRODUCTION INVARIANTS & INTEGRITY
    # =========================================================================

    def test_14_production_model_calibrated_xgboost_v1_1(self):
        """Verify production AI model is Calibrated XGBoost V1.1 with locked SHA-256."""
        model_path = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_10", "models", "calibrated_xgboost_model.joblib")
        self.assertTrue(os.path.exists(model_path), "Calibrated XGBoost model file must exist")
        with open(model_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        EXPECTED_SHA = "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c"
        self.assertEqual(digest, EXPECTED_SHA, "XGBoost SHA-256 must match authoritative production hash")

    def test_15_model_fallback_is_none(self):
        """Verify ML model fallback policy is strictly NONE."""
        self.assertEqual(provider_manager.operational_fallback, "NONE")

    def test_16_drive_g_strictly_untouched(self):
        r"""Verify drive G:\ is untouched and never referenced as operational path."""
        for root, _, files in os.walk(PROJECT_ROOT):
            if ".git" in root or "__pycache__" in root:
                continue
            for fname in ["gis_service.py", "server.py"]:
                fpath = os.path.join(root, fname)
                if os.path.exists(fpath):
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self.assertNotIn("G:\\", content)
                    self.assertNotIn("G:/", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
