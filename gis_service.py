r"""
NER-SAFE: High-Performance Local GIS Service
Provides:
1. SRTM 30m Terrain Elevation Tiles (Cesium.GeographicTilingScheme compatible)
2. Census 2011 Demographic Population Exposure Layer (ADM2 Districts)
3. Genuine OpenStreetMap Major Road Network (Clamped to Terrain)
4. Genuine OpenStreetMap Building Footprint Extrusions (Exposure Only)

Strict Production Invariants:
- All datasets originate from local verified NER_SAFE_DATA
- Population is an EXPOSURE layer (0.00 risk weight)
- Production AI model (Calibrated XGBoost v1.1) and risk formula are strictly protected
- External backup archive is never accessed
"""

import os
import io
import json
import math
import struct
import threading
import numpy as np
from typing import Dict, Any, Optional, Tuple

try:
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA")

# Dataset Paths
DEM_PATH = os.path.join(DATA_DIR, "TERRAIN", "derivatives", "elevation", "elevation.tif")
POPULATION_GEOJSON_PATH = os.path.join(DATA_DIR, "EXPOSURE", "population", "NER_SAFE_Phase1_district_demographics.geojson")
POPULATION_CSV_PATH = os.path.join(DATA_DIR, "EXPOSURE", "population", "NER_SAFE_Phase1_district_demographics.csv")
ROADS_PATH = os.path.join(DATA_DIR, "EXPOSURE", "roads", "NER_SAFE_Phase1_roads.geojson")
BUILDINGS_MEGHALAYA_PATH = os.path.join(DATA_DIR, "EXPOSURE", "buildings", "Meghalaya_buildings.geojson")
BUILDINGS_MIZORAM_PATH = os.path.join(DATA_DIR, "EXPOSURE", "buildings", "Mizoram_buildings.geojson")
EXPOSURE_INTERSECTIONS_PATH = os.path.join(DATA_DIR, "COMPONENT_11", "exposure", "exposure_intersections.geojson")

# SRTM AOI Bounding Box
AOI_WEST = 89.0
AOI_SOUTH = 21.0
AOI_EAST = 94.0
AOI_NORTH = 27.0


class GISService:
    def __init__(self):
        self._dem_src = None
        self._dem_lock = threading.Lock()
        self._tile_cache: Dict[Tuple[int, int, int, int, int], bytes] = {}
        self._cached_population = None
        self._cached_population_bytes = None
        self._cached_roads = None
        self._cached_roads_bytes = None
        self._cached_buildings = None
        self._cached_buildings_bytes = None
        self._dem_available = os.path.exists(DEM_PATH) and RASTERIO_AVAILABLE
        if self._dem_available:
            try:
                self._dem_src = rasterio.open(DEM_PATH)
            except Exception as e:
                print(f"[GIS_SERVICE] Warning: Could not open DEM: {e}")
                self._dem_available = False

    def is_dem_available(self) -> bool:
        return self._dem_available and self._dem_src is not None

    def get_dem_metadata(self) -> Dict[str, Any]:
        if not self.is_dem_available():
            return {"available": False, "source": "NONE"}
        return {
            "available": True,
            "source": "USGS SRTM 1 Arc-Second (30m) Global DEM",
            "crs": str(self._dem_src.crs),
            "bounds": {
                "west": self._dem_src.bounds.left,
                "south": self._dem_src.bounds.bottom,
                "east": self._dem_src.bounds.right,
                "north": self._dem_src.bounds.top
            },
            "shape": list(self._dem_src.shape),
            "resolution_deg": list(self._dem_src.res),
            "nodata": float(self._dem_src.nodata) if self._dem_src.nodata is not None else -9999.0
        }

    # =========================================================================
    # 1. 3D TERRAIN TILE GENERATION (Cesium.GeographicTilingScheme)
    # =========================================================================

    @staticmethod
    def get_tile_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
        """
        Calculates geographic bounds (W, S, E, N) in EPSG:4326 for GeographicTilingScheme.
        Level 0 has 2 tiles: x=0 [-180..0], x=1 [0..180], y=0 [-90..90].
        """
        n_x = 2 ** (z + 1)
        n_y = 2 ** z
        lon_per_tile = 360.0 / n_x
        lat_per_tile = 180.0 / n_y
        w = -180.0 + x * lon_per_tile
        e = w + lon_per_tile
        n = 90.0 - y * lat_per_tile
        s = n - lat_per_tile
        return w, s, e, n

    def get_terrain_tile_float32(self, z: int, x: int, y: int, width: int = 65, height: int = 65) -> bytes:
        """
        Returns a binary buffer of (width * height) float32 elevation values in row-major
        order (North to South, West to East), directly compatible with CesiumJS CustomHeightmapTerrainProvider.
        """
        cache_key = (z, x, y, width, height)
        if cache_key in self._tile_cache:
            return self._tile_cache[cache_key]

        empty_tile = np.zeros((height, width), dtype=np.float32).tobytes()

        if not self.is_dem_available():
            return empty_tile

        # For global/hemispheric zoom levels (z < 6), return flat base tile immediately.
        # This prevents massive multi-gigabyte window reads across the Eastern Hemisphere
        # and allows Cesium's root tiles to resolve in under 1 millisecond.
        if z < 6:
            self._tile_cache[cache_key] = empty_tile
            return empty_tile

        w, s, e, n = self.get_tile_bounds(z, x, y)

        # Fast rejection if tile does not intersect the NER AOI / DEM bounds
        if e <= AOI_WEST or w >= AOI_EAST or n <= AOI_SOUTH or s >= AOI_NORTH:
            self._tile_cache[cache_key] = empty_tile
            return empty_tile

        try:
            with self._dem_lock:
                win = from_bounds(w, s, e, n, self._dem_src.transform)
                data = self._dem_src.read(
                    1,
                    window=win,
                    out_shape=(height, width),
                    resampling=Resampling.bilinear,
                    boundless=True,
                    fill_value=0.0
                )

            # Clean nodata / fill tokens
            nodata_val = self._dem_src.nodata if self._dem_src.nodata is not None else -9999.0
            data[data == nodata_val] = 0.0
            data[data < -500.0] = 0.0
            data[data > 9000.0] = 0.0
            data[np.isnan(data)] = 0.0

            result = data.astype(np.float32).tobytes()
            # Cache tile if cache has reasonable size (< 2000 tiles ~ 32MB)
            if len(self._tile_cache) < 2000:
                self._tile_cache[cache_key] = result
            return result
        except Exception as err:
            print(f"[GIS_SERVICE] Tile extraction error z={z}, x={x}, y={y}: {err}")
            return empty_tile

    # =========================================================================
    # 2. 2D POPULATION EXPOSURE LAYER (Census 2011)
    # =========================================================================

    def get_population_exposure(self) -> Dict[str, Any]:
        """
        Loads and returns the authoritative Census 2011 demographic GeoJSON.
        Strictly labeled as EXPOSURE with 0.00 operational risk weight.
        """
        if self._cached_population:
            return self._cached_population

        if not os.path.exists(POPULATION_GEOJSON_PATH):
            return {
                "type": "FeatureCollection",
                "metadata": {
                    "source": "Census of India 2011 / MDoNER (Missing)",
                    "year": 2011,
                    "risk_weight": 0.00,
                    "status": "FILE_NOT_FOUND"
                },
                "features": []
            }

        with open(POPULATION_GEOJSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metadata"] = {
            "dataset_name": "NER-SAFE Administrative & Demographic Exposure Layer",
            "source": "Office of the Registrar General & Census Commissioner of India / MDoNER",
            "census_year": 2011,
            "administrative_level": "ADM2 (Districts)",
            "crs": "EPSG:4326 (WGS84)",
            "operational_risk_weight": 0.00,
            "role": "EXPOSURE / CONSEQUENCE CONTEXT ONLY (Does not modify risk formula)",
            "total_districts": len(data.get("features", [])),
            "states_covered": ["Meghalaya", "Mizoram"],
            "density_ranges": {
                "low": "< 75 persons/sqkm",
                "moderate": "75 - 150 persons/sqkm",
                "high": "150 - 300 persons/sqkm",
                "very_high": "> 300 persons/sqkm"
            }
        }
        self._cached_population = data
        return self._cached_population

    # =========================================================================
    # 3. 3D & 2D ROADS EXPOSURE LAYER (Genuine OpenStreetMap)
    # =========================================================================

    def get_roads_exposure(self, tier: str = "major") -> Dict[str, Any]:
        """
        Returns genuine OpenStreetMap road vectors.
        By default filters to major corridors (highways, primary, secondary, tertiary)
        to ensure rapid rendering on constrained hardware.
        """
        if self._cached_roads and tier == "major":
            return self._cached_roads

        if not os.path.exists(ROADS_PATH):
            return {"type": "FeatureCollection", "features": []}

        with open(ROADS_PATH, "r", encoding="utf-8") as f:
            raw_roads = json.load(f)

        MAJOR_FCLASSES = {
            "trunk", "trunk_link", "primary", "primary_link",
            "secondary", "secondary_link", "tertiary", "tertiary_link"
        }

        filtered_features = []
        for feat in raw_roads.get("features", []):
            fc = feat.get("properties", {}).get("fclass", "").lower()
            if tier == "all" or fc in MAJOR_FCLASSES:
                # Add 3D clamping and exposure metadata
                p = dict(feat.get("properties", {}))
                p["exposure_role"] = "LIFELINE_INFRASTRUCTURE"
                p["risk_weight"] = 0.00
                p["clamp_to_ground"] = True
                
                # Optimize coordinate precision to 5 decimal places (~1.1m precision)
                # to accelerate network transfer and browser parsing
                geom = feat.get("geometry", {})
                g_type = geom.get("type")
                coords = geom.get("coordinates", [])
                if g_type == "LineString":
                    opt_coords = [[round(pt[0], 5), round(pt[1], 5)] for pt in coords]
                elif g_type == "MultiLineString":
                    opt_coords = [[[round(pt[0], 5), round(pt[1], 5)] for pt in line] for line in coords]
                else:
                    opt_coords = coords

                filtered_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": g_type,
                        "coordinates": opt_coords
                    },
                    "properties": p
                })

        payload = {
            "type": "FeatureCollection",
            "name": "NER_SAFE_Road_Exposure_Network",
            "metadata": {
                "source": "OpenStreetMap / Geofabrik North-Eastern Zone",
                "filter_applied": tier,
                "feature_count": len(filtered_features),
                "clamping_required": True,
                "operational_risk_weight": 0.00
            },
            "features": filtered_features
        }

        if tier == "major":
            self._cached_roads = payload
            self._cached_roads_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        return payload

    def get_roads_exposure_bytes(self, tier: str = "major") -> bytes:
        """Returns pre-serialized compact JSON bytes for maximum transfer speed."""
        if tier == "major" and self._cached_roads_bytes:
            return self._cached_roads_bytes
        data = self.get_roads_exposure(tier=tier)
        return json.dumps(data, separators=(',', ':')).encode('utf-8')

    # =========================================================================
    # 4. 3D & 2D BUILDINGS EXPOSURE LAYER (Genuine OpenStreetMap)
    # =========================================================================

    def get_buildings_exposure(self, limit: int = 1500, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns genuine OpenStreetMap building footprint polygons.
        Provides a clearly labeled uniform visualization extrusion (10m)
        since surveyed building heights are not present in raw OSM.
        """
        if self._cached_buildings and state is None and limit == 1500:
            return self._cached_buildings

        features = []

        # First load exposed buildings intersecting runout corridors if available
        if os.path.exists(EXPOSURE_INTERSECTIONS_PATH):
            try:
                with open(EXPOSURE_INTERSECTIONS_PATH, "r", encoding="utf-8") as f:
                    exp_data = json.load(f)
                    for feat in exp_data.get("features", []):
                        if feat.get("geometry", {}).get("type") in ("Polygon", "MultiPolygon"):
                            p = dict(feat.get("properties", {}))
                            p["height_rule"] = "VISUALIZATION HEIGHT (NOT SURVEYED HEIGHT)"
                            p["visualization_height_m"] = 10.0
                            p["risk_weight"] = 0.00
                            features.append({
                                "type": "Feature",
                                "geometry": feat["geometry"],
                                "properties": p
                            })
            except Exception as e:
                print(f"[GIS_SERVICE] Warning reading exposure intersections: {e}")

        # Supplement with Meghalaya footprints up to limit
        if len(features) < limit and os.path.exists(BUILDINGS_MEGHALAYA_PATH):
            try:
                with open(BUILDINGS_MEGHALAYA_PATH, "r", encoding="utf-8") as f:
                    meg_data = json.load(f)
                    for feat in meg_data.get("features", []):
                        if len(features) >= limit:
                            break
                        p = dict(feat.get("properties", {}))
                        p["height_rule"] = "VISUALIZATION HEIGHT (NOT SURVEYED HEIGHT)"
                        p["visualization_height_m"] = 10.0
                        p["risk_weight"] = 0.00
                        features.append({
                            "type": "Feature",
                            "geometry": feat["geometry"],
                            "properties": p
                        })
            except Exception as e:
                print(f"[GIS_SERVICE] Warning reading Meghalaya buildings: {e}")

        payload = {
            "type": "FeatureCollection",
            "name": "NER_SAFE_Building_Exposure_Footprints",
            "metadata": {
                "source": "OpenStreetMap Digitized Building Footprints",
                "feature_count": len(features),
                "height_rule": "VISUALIZATION HEIGHT (NOT SURVEYED HEIGHT)",
                "default_visualization_extrusion_m": 10.0,
                "operational_risk_weight": 0.00,
                "scientific_note": "Building heights are visualization aids only and do NOT alter risk scores."
            },
            "features": features
        }

        if state is None and limit == 1500:
            self._cached_buildings = payload
            self._cached_buildings_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        return payload

    def get_buildings_exposure_bytes(self, limit: int = 1500, state: Optional[str] = None) -> bytes:
        """Returns pre-serialized compact JSON bytes for building footprints."""
        if state is None and limit == 1500 and self._cached_buildings_bytes:
            return self._cached_buildings_bytes
        data = self.get_buildings_exposure(limit=limit, state=state)
        return json.dumps(data, separators=(',', ':')).encode('utf-8')


# Global singleton instance
gis_service = GISService()

