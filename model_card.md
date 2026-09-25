# Model Card: NER-SAFE Phase 1 Landslide Susceptibility & Risk Engine (v1.0.0-MVP)

## Model Details
- **Developer**: Antigravity AI Engineering for MDoNER / SIH 26001
- **Model Date**: September 2026
- **Model Version**: 1.0.0-MVP (Research & Operational Prototype)
- **Model Type**: Calibrated Random Forest Classifier (150 trees, max_depth=8) with Platt Sigmoid Calibration
- **Spatial Resolution**: 1 arc-second (~30.89 meters ground resolution) matching USGS SRTM DEM
- **Spatial Coverage**: Phase 1 AOI — Meghalaya & Mizoram (21.0°N to 27.0°N, 89.0°E to 94.0°E)
- **License / Governance**: Government of India / Ministry of Development of North Eastern Region

## Intended Use
- **Primary Use**: Regional spatial decision-support mapping of terrain susceptibility and seasonal hydrological landslide risk across Meghalaya and Mizoram.
- **Intended Users**: State Disaster Management Authorities (SDMAs), MDoNER regional planners, district emergency response teams.
- **Out-of-Scope Uses**: 
  - Real-time IoT early-warning alarms (requires in-situ borehole piezometers/extensometers).
  - Site-specific geotechnical engineering slope design (requires borehole core logs).
  - Extrapolation outside Phase 1 (Meghalaya and Mizoram).

## Factors & Predictors
- **Terrain Morphometry (Component 7)**: Elevation, slope, sin(aspect), cos(aspect), profile curvature, Topographic Wetness Index (TWI).
- **Biophysical Context (Component 9)**: Sentinel-2 Level-2A NDVI, NDWI, NDMI with median baseline imputation and observation indicators.
- **Dynamic Triggers (Component 9)**: NASA GPM IMERG cumulative precipitation (R3d, ARI, R14d) and NASA SMAP volumetric soil moisture saturation.

## Target Leakage & Scientific Safeguards
- **Zero Label Leakage**: Historical landslide occurrence points (`landslide_presence_30m`) and metric Euclidean distances (`landslide_distance_meters_30m`) were strictly blacklisted from the predictor feature set.
- **Spatial Autocorrelation Protection**: Models were cross-validated using 5-Fold Geographic Spatial Blocks (not random pixel sampling).
- **Negative Sample Integrity**: Pseudo-absence samples were constrained to >1000m buffer distance from known landslides and stratified across slope and elevation domains.
- **Exposure Separation**: Roads, buildings, population, and settlements were strictly excluded from hazard/susceptibility probability estimation.

## Performance Metrics (5-Fold Spatial Block Cross-Validation)
- **Spatial PR-AUC**: 0.3151 (vs 0.2500 baseline prevalence)
- **Spatial ROC-AUC**: 0.5654
- **Spatial Recall**: 34.62% (72 / 208 documented landslides detected in completely held-out geographic blocks)
- **Spatial Precision**: 30.90%
- **Spatial F1-Score**: 0.3265
- **Calibrated Brier Score**: 0.2035 (significant calibration improvement over uncalibrated 0.2218)

## Known Limitations & Caveats
1. **Inventory Completeness**: Historical inventories primarily capture events affecting roads, settlements, and infrastructure; remote wilderness slope failures are under-represented.
2. **Temporal Supervision Boundary**: Historical landslide labels (2007-2023) and operational environmental predictors (2024-2025) lack exact temporal alignment. The dynamic trigger module is implemented as an empirical index rather than a fully supervised temporal predictor.
3. **Sensor Resolution Differences**: GPM (~10km) and SMAP (~9km) rasters are spatially aligned to 30m; they do NOT represent 30m native sensor observations.
4. **NASA SMAP 2025-03-18 Outage**: Preserved as an explicit missing-data quality flag without synthetic fabrication.
