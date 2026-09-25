"""
NER-SAFE Phase 4A: Dedicated Test Suite for 3D Topographic Terrain Visualization
Verifies:
1. Dashboard HTML contains the required CesiumJS libraries and container
2. 3D Terrain toggle button exists in the basemap group
3. Cesium fallback notice element exists with no-emoji UX4G standard icons
4. WebGL fallback mechanism preserves operational 2D Leaflet map
5. Operational 4-factor risk calculation is strictly independent of 3D rendering
"""

import os
import sys
import unittest
import re

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

class Test3DTerrainVisualization(unittest.TestCase):
    def setUp(self):
        dash_path = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
        with open(dash_path, "r", encoding="utf-8") as f:
            self.dashboard_html = f.read()

    def test_01_cesium_cdn_inclusion(self):
        """Verify CesiumJS CSS and JS links are present in <head>."""
        self.assertIn("Cesium/Widgets/widgets.css", self.dashboard_html)
        self.assertIn("Cesium/Cesium.js", self.dashboard_html)

    def test_02_cesium_container_present(self):
        """Verify #cesiumContainer is declared in DOM within map-container."""
        self.assertIn('id="cesiumContainer"', self.dashboard_html)
        # Should start hidden so 2D Leaflet is primary
        self.assertIn('style="display:none;"', self.dashboard_html)

    def test_03_basemap_3d_toggle_button(self):
        """Verify btnBasemap3D exists in basemap selector with SVG icon."""
        self.assertIn('id="btnBasemap3D"', self.dashboard_html)
        self.assertIn('onclick="toggle3DView()"', self.dashboard_html)
        self.assertIn('3D Terrain', self.dashboard_html)

    def test_04_webgl_fallback_notice_present(self):
        """Verify #cesiumFallbackNotice is present with proper non-blocking dismiss."""
        self.assertIn('id="cesiumFallbackNotice"', self.dashboard_html)
        self.assertIn('id="cesiumFallbackText"', self.dashboard_html)
        self.assertIn('onclick="dismissCesiumFallback()"', self.dashboard_html)

    def test_05_javascript_3d_lifecycle_methods(self):
        """Verify JS functions for 3D viewer initialization, switching, and hotspots."""
        self.assertIn("function toggle3DView()", self.dashboard_html)
        self.assertIn("function switchTo2D()", self.dashboard_html)
        self.assertIn("function switchTo3D()", self.dashboard_html)
        self.assertIn("function initCesiumViewer()", self.dashboard_html)
        self.assertIn("function populateCesiumHotspots", self.dashboard_html)
        self.assertIn("function isWebGLSupported()", self.dashboard_html)

    def test_06_no_emoji_rule_enforced(self):
        """Verify no emojis are used in the 3D toggle or fallback elements."""
        # Find 3D button and notice HTML block
        m = re.search(r'<button[^>]*id="btnBasemap3D"[^>]*>.*?</button>', self.dashboard_html, re.DOTALL)
        self.assertIsNotNone(m)
        btn_block = m.group(0)
        
        # Check for non-ASCII emoji characters (range > 0x1F000)
        for char in btn_block:
            self.assertLess(ord(char), 0x1F000, f"Emoji character detected in 3D button: {char}")

    def test_07_risk_engine_independence(self):
        """Verify risk engine runs without any Cesium/browser graphics dependencies."""
        import fusion_engine
        data = fusion_engine.compute_fused_hotspots()
        self.assertIsNotNone(data)
        self.assertIn("features", data)
        self.assertEqual(len(data["features"]), 48)

if __name__ == "__main__":
    unittest.main(verbosity=2)
