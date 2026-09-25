# Product Requirements Document (PRD) — NER-SAFE
## AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India

**Document Version:** PRD v2.1 — Current System Specification  
**Document Status:** CURRENT / IMPLEMENTATION-ALIGNED  
**Authoritative Date:** September 23, 2026  
**System Baseline:** `v1.2.0-PROD` (Release Lineage: `nersafe-judge-demo-baseline-1.0` + Real 3D Topographic GIS & Census Demographic Exposure)  
**Project Owner:** NER-SAFE Engineering Team / Ministry of Development of North Eastern Region (MDoNER)  
**Related Problem Statement:** Smart India Hackathon 2026 — Problem Statement ID: 26001 (Disaster Management)  
**Operational Target Geography:** All 8 North Eastern Region (NER) States (Phase 1 Validated Operational Scope: Meghalaya and Mizoram)  
**UX & Accessibility Standard:** Government of India UX4G 3.0 Standard (100% SVG Vector Iconography, Strictly Zero Emojis)

---

## 1. Executive Summary & Problem Definition

### 1.1 The Regional Challenge
In the mountainous and high-rainfall terrain of Northeast India, landslides, flash floods, and slope failures cause frequent road blockages, destruction of civil infrastructure, economic isolation of remote villages, and loss of life. Traditional monitoring has been predominantly **reactive** — disaster management authorities and civil protection agencies typically learn of slope failures hours or days after they occur via emergency phone calls, field surveys, or social media, severely hindering life-saving evacuations and emergency lifeline management.

### 1.2 The SIH 26001 Mandate
Smart India Hackathon 2026 Problem Statement 26001, posed by the Ministry of Development of North Eastern Region (MDoNER), mandates the development of an **AI-Based Early Warning and Landslide Risk Monitoring System** tailored to the unique geomorphology, extreme precipitation regimes, and sparse infrastructure of the North Eastern Region.

**Critical Architectural Scope:** NER-SAFE is **not** a generic machine learning toy or a standalone landslide classifier. It is an end-to-end, multi-source disaster decision-support platform integrating:
$$\text{Earth Observation Data Acquisition} + \text{Environmental Monitoring} + \text{Static Terrain Analysis} + \text{Satellite Radar/Optical Observation}$$
$$+ \text{Calibrated AI Susceptibility} + \text{D8 Runout/Flow-Path Analysis} + \text{Infrastructure Exposure Assessment}$$
$$+ \text{External Intelligence Ingestion} + \text{Multi-Channel Alerting} + \text{Crowdsourced Citizen Ground Hazard Reporting}$$
$$+ \text{Modern GIS Web Operations Console} + \text{Offline/Zero-Network Resilient Protocols}$$

---

## 2. Target Users & Stakeholders

| User / Stakeholder Group | Primary Operational Needs | Implemented System Touchpoint |
| :--- | :--- | :--- |
| **Citizens & Local Residents** | Submit geotagged danger signs (tension cracks, slope seepage, road blockages) even during complete cellular blackouts. Receive timely, multilingual warning alerts in native regional dialects. | Offline-capable Citizen Mobile Web App (`ner_safe_citizen_app.html`), SMS/Push notification subscriber interface. |
| **Field Officers (SDRF, PWD, Police, Forest Guards)** | Receive prioritized task lists of at-risk road lifelines and settlements. Review and physically verify or reject citizen hazard submissions directly on map pins. | In-situ Field Verification Desk within Live Dashboard, CAP v1.2 incident dispatch payloads, situation bulletins. |
| **District Disaster Management Authorities (DDMA)** | Monitor district-wide fused risk hotspots in near-real-time. Inspect flow-path runout envelopes, identify threatened highway segments (NH-06, NH-54), and trigger targeted civil evacuation directives. | Live Unified Operations Center (`ner_safe_live_dashboard.html`), Hotspot Runout Inspector, district situational bulletins. |
| **State Disaster Management Authorities (SDMA) & MDoNER** | Regional situational awareness across state boundaries, cross-agency coordination, resource staging, external intelligence corroboration (GSI, NDMA SACHET, IMD). | Multi-District GIS Console, external intelligence evidence panels, CAP v1.2 XML/JSON feeds, cloud backup archives. |

---

## 3. Status Taxonomy & Verification Governance

To ensure rigorous engineering honesty and prevent marketing exaggeration, all capabilities, datasets, and models throughout this PRD are classified under an explicit status taxonomy:

- **`IMPLEMENTED`**: Code, pipeline, schema, or interface is written and functional in the repository.
- **`VALIDATED`**: Statistically evaluated and passing formal automated acceptance gates without regressions.
- **`LIVE_VERIFIED`**: Actively tested and successfully retrieving real, authentic external data from live servers.
- **`AUTO_UPDATE_VERIFIED`**: Autonomous background scheduler verified polling, ingesting, and updating downstream risk states without human intervention. (Distinct from `LIVE_VERIFIED`: reachability does not imply automated scheduling).
- **`PARTIALLY_IMPLEMENTED`**: Foundational code or adapter exists, but full feature breadth remains incomplete.
- **`PENDING_ACCESS`**: Platform architecture ready; waiting for external credential approval or server provisioning.
- **`AUTH_REQUIRED`**: Source requires user-configured API keys or tokens in host environment configuration.
- **`INSTITUTIONAL_ACCESS_REQUIRED`**: Access requires official administrative MoUs or institutional authorization from government ministries or universities.
- **`ACCESS_LIMITED`**: Source imposes strict rate limits, regional restrictions, or token barriers.
- **`NOT_AUTOMATED`**: Pipeline requires manual invocation or batch processing.
- **`RESEARCH_ONLY`**: Experimental module retained for scientific benchmarking; prohibited from modifying production risk scores.
- **`SHADOW_MODE`**: Model executes concurrently in background to evaluate candidate metrics without serving live production risk.
- **`NOT_SCIENTIFICALLY_VALIDATED`**: Capability lacks sufficient empirical ground-truth labels to support statistically sound validation.
- **`DEFERRED`**: Intentionally scheduled for future engineering phases.
- **`BLOCKED`**: Progress halted by external dependencies or insurmountable technical barriers.
- **`OUT_OF_SCOPE`**: Explicitly excluded from project mandate.
- **`PLANNED`**: Formally specified architecture scheduled for future development phases.

---

## 4. Geographic Scope & Phased Rollout Architecture

### 4.1 Target Scope: The North Eastern Region
The ultimate target operational scope encompasses all **8 North Eastern States**:
1. Assam
2. Arunachal Pradesh
3. Manipur
4. Meghalaya
5. Mizoram
6. Nagaland
7. Sikkim
8. Tripura

### 4.2 Engineering Phasing Reality & Data Heterogeneity
Simultaneous Day-One AI deployment across all 8 states is scientifically invalid due to extreme disparities in historical inventory density, published geological mapping, and sensor coverage. NER-SAFE enforces a disciplined phased rollout:

```
+--------------------------------------------------------------------------------------------------+
| PHASE 1: VALIDATED OPERATIONAL SCOPE (CURRENT)                                                  |
| Target States : Meghalaya and Mizoram (AOI: 21.0°N – 27.0°N, 89.0°E – 94.0°E)                   |
| Status        : IMPLEMENTED & VALIDATED across 48 Hotspots, 16 SRTM Tiles, 17 Exposure Layers   |
| Ground Truth  : 260 Georeferenced Landslide Events, 48 Monitored D8 Runout Envelopes            |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PHASE 2: REGIONAL SCALE-OUT — MODERATE DATA DENSITY (PLANNED)                                    |
| Target States : Assam (Hill Corridors / Dima Hasao), Sikkim, Tripura                            |
| Rationale     : Established GSI susceptibility mappings exist; moderate highway corridor density|
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PHASE 3: REGIONAL FRONTIER — HIGH RISK / SPARSE DATA (PLANNED)                                   |
| Target States : Arunachal Pradesh, Manipur, Nagaland                                            |
| Scientific Gap: Nagaland has India's highest landslide susceptibility (55%), but the thinnest   |
|                 historical baseline data. Requires targeted satellite mapping and ground surveys|
+--------------------------------------------------------------------------------------------------+
```

---

## 5. Current Data Architecture (Validated Repositories)

The table below replaces all historical sourcing drafts with the actual, verified data layers currently stored and active in `NER_SAFE_DATA`:

| Data Layer | Authoritative Dataset & Product | Source Authority | Target Resolution | Validated Volume / Coverage | Operational Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Terrain / DEM** | SRTM 1 Arc-Second Global | USGS EarthExplorer | ~30 m (1 arc-sec) | 16 GeoTIFF tiles, 0 NoData voids | `VALIDATED` |
| **Terrain Derivatives** | Elevation, Slope, Aspect, Profile Curvature, TWI | Validated SRTM Mosaic | ~30 m ($18001 \times 21601$) | 5 Rasters (2.835 GB, 388.8M cells) | `VALIDATED` |
| **GPM Rainfall (Archive)** | GPM IMERG Final V07 (`3IMERGDF`) | NASA GES DISC | 0.1° (~10 km) | 181 NetCDF4 daily files (2024-11-01 to 2025-04-30) | `VALIDATED` |
| **GPM Rainfall (Live)** | GPM IMERG Early NRT Half-Hourly | NASA Earthdata CMR | 0.1° (~10 km) | Half-hourly HDF5 streaming granules | `LIVE_VERIFIED` / `AUTO_UPDATE_VERIFIED` |
| **SMAP Soil Moisture** | SMAP L3 Radiometer (`SPL3SMP_E.006`) | NASA NSIDC DAAC | ~9 km EASE-Grid 2.0 | 180 Daily HDF5 files (1.616 GB, Documented Outage Gap) | `VALIDATED` (With Gap) |
| **Sentinel-2 Optical** | Sentinel-2 MSI Level-2A Surface Reflectance | ESA Copernicus | 10 m native / 30 m grid | 13 MGRS Scenes, 91/91 Bands, 39 Index Rasters (9.8 GB) | `VALIDATED` |
| **Sentinel-1 SAR Amplitude**| Sentinel-1 Level-1 GRD Dual-Pol (VV/VH) | ESA Copernicus CDSE | 20 m native / 30 m grid | Radar backscatter change ($\Delta \sigma^0$) | `IMPLEMENTED` |
| **Sentinel-1 InSAR Phase** | Sentinel-1 Level-1 IW SLC Repeat-Pass | ESA CDSE S3 (`eodata`) | 56m $\times$ 59m multi-looked | Track 150 Descending (3 repeat scenes, 1 pair validated) | `VALIDATED` (Single Pair) / `RESEARCH_ONLY` (PSI) |
| **Landslide Ground Truth** | NASA GLC, GSI Bhukosh, Bhuvan Atlas | Multi-Agency Catalogs | Georeferenced Points | 260 Validated Events (Meghalaya, Mizoram, Corridors) | `VALIDATED` |
| **Exposure & Infrastructure**| geoBoundaries, Survey of India, OSM, Census | SOI / OSM / Census 2011 | Multi-Scale Vector | 17 Datasets (342,080 features: roads, buildings, places) | `VALIDATED` |
| **Master Modeling Grid** | Regional Harmonized Feature Stack | Multi-Source Fusion | 1 arc-sec (EPSG:4326) | 62 Cataloged Layers (Manifest + Validation Report) | `VALIDATED` |
| **3D Terrain Elevation Tiles** | USGS SRTM 1 Arc-Second DEM | USGS / NER-SAFE GIS Engine | 30 m ($65 \times 65$ Float32) | Dynamic binary tiles (16,900 bytes/tile, EPSG:4326) | `VALIDATED` / `LIVE_VERIFIED` |
| **Demographic Population** | Census of India 2011 (ADM2 Districts) | Registrar General & Census Commissioner | District (ADM2) Polygon | 22 Districts (Meghalaya & Mizoram, 4.56M population) | `VALIDATED` |
| **3D Lifeline Infrastructure** | OSM Major Roads & Building Footprints | OpenStreetMap Contributors | Vector LineString / Polygon | 2,865 Clamped Roads + 1,200 Extruded Buildings | `VALIDATED` |

### 5.1 Detailed Data Layer Specifications & Invariants

#### A. Terrain & Geomorphology (Component 7)
- **Source**: 16 USGS SRTM 1 Arc-Second DEM tiles seamlessly mosaicked across $21.0^\circ\text{N} - 27.0^\circ\text{N}, 89.0^\circ\text{E} - 94.0^\circ\text{E}$ (388,839,601 cells; 207,399,601 valid land cells).
- **Derived Layers**:
  1. `elevation.tif`: EGM96 vertical geoid datum, range $-42.0$ m to $4068.0$ m (mean $478.21$ m).
  2. `slope_degrees.tif`: Horn (1981) 8-neighbor weighted finite-difference gradient dynamically scaled by latitude ($\Delta y = 30.8875$ m, $\Delta x(\phi) = \Delta y \cos\phi$). Range $0.00^\circ$ to $89.91^\circ$ (mean $12.96^\circ$).
  3. `aspect_degrees.tif`: Azimuth clockwise from North ($0^\circ - 360^\circ$). Slopes $<0.1^\circ$ assigned $-1.0$ (1.54% flat terrain).
  4. `profile_curvature.tif`: Zevenbergen & Thorne (1987) rate of slope change along steepest gradient flowline. Full unclipped floating dynamic range ($-0.1714\text{ m}^{-1}$ to $+7.1581\text{ m}^{-1}$).
  5. `twi.tif`: Topographic Wetness Index $\ln(a / \tan\beta)$, where specific catchment area $a = (\text{accum} + 1) \cdot \Delta y$ rigorously cancels longitudinal width scaling. Slope floored at $\beta_{\text{floor}} = 0.1^\circ$ to prevent division-by-zero. Range $-2.28$ to $+17.24$ (mean $6.92$).
- **Invariant**: Static geomorphic derivatives serve as foundational susceptibility predictors; they are computed once and remain strictly immutable.

#### B. Satellite Precipitation (GPM IMERG)
- **Historical Baseline**: NASA GES DISC daily NetCDF4 (`3IMERGDF`), 181 continuous daily files (2024-11-01 to 2025-04-30), 0 missing dates, 0 corruption.
- **Live Dynamic Trigger**: NASA Earthdata CMR queries stream half-hourly early run granules (`GPM_3IMERGHHE_V07`), providing near-real-time precipitation rates and multi-horizon antecedent accumulations ($1\text{h}, 3\text{h}, 6\text{h}, 24\text{h}, 72\text{h}$, and 7-day).
- **Invariant**: Satellite precipitation provides regional synoptic coverage (~10 km resolution). IMD ground station observations corroborate GPM; they do **not** replace GPM.

#### C. Satellite Soil Moisture (SMAP) & The Documented Outage Gap
- **Dataset**: NASA NSIDC DAAC enhanced 9 km radiometer product (`SPL3SMP_E.006`), top-5cm volumetric soil moisture ($cm^3/cm^3$) from AM descending passes.
- **The Documented Gap Condition**: Out of 181 expected daily files (2024-11-01 to 2025-04-30), exactly **180 files** were successfully acquired and validated. Comprehensive NASA Earthdata archive queries confirmed that on **March 18, 2025**, the SMAP satellite payload entered an instrument safe hold / operational outage; zero observation granules exist worldwide in the NASA archive for that date.
- **Scientific Invariant**: In accordance with anti-fabrication standards, the system generates an explicit `outage_flag=1.0` and **never interpolates, fabricates, duplicates, or synthesizes** missing soil moisture data. SMAP is treated as a coarse regional antecedent saturation signal, not a local slope pore-pressure sensor.

#### D. Optical Multispectral Indices (Sentinel-2 Level-2A)
- **Source**: Official Copernicus Sentinel-2 MSI Level-2A surface reflectance (Baseline 05.11), 13 MGRS scene footprints ($10,980 \times 10,980$ cells per tile).
- **Band Completeness**: 91/91 source GeoTIFFs validated ($B02, B03, B04, B08, B11, B12, SCL$).
- **Index Formulation**: Native 10m NDVI $(\rho_{B08} - \rho_{B04})/(\rho_{B08} + \rho_{B04})$, native 10m NDWI $(\rho_{B03} - \rho_{B08})/(\rho_{B03} + \rho_{B08})$, and 10m NDMI $(\rho_{B08} - \rho_{B11})/(\rho_{B08} + \rho_{B11})$ (SWIR1 resampled via bilinear interpolation).
- **Cloud Masking**: Native 20m Scene Classification Layer (SCL) resampled to 10m/30m strictly via **nearest-neighbor interpolation ONLY** (`Resampling.nearest`) to preserve discrete categorical classes. SCL classes `0` (NoData), `1` (Defective), `3` (Cloud Shadow), `8` (Med Prob Cloud), `9` (High Prob Cloud), and `10` (Cirrus) are masked to NoData.
- **Invariant**: Sentinel-2 optical indices observe vegetation vigor loss and surficial canopy moisture changes. They **never** measure ground deformation or displacement.

#### E. Synthetic Aperture Radar Amplitude (Sentinel-1 GRD)
- **Source**: Copernicus Level-1 Ground Range Detected (GRD) dual-polarization (VV/VH) products.
- **Application**: All-weather radar backscatter intensity change detection ($\Delta \sigma^0$), penetrating persistent monsoonal cloud decks to detect surface disruption, scarp scouring, and vegetative stripping.
- **Role**: Drives the 10% Satellite Surface Change Flag ($w_4$) in the locked operational risk fusion formula.

#### F. Synthetic Aperture Radar Interferometry (Sentinel-1 SLC / InSAR)
- **Acquisition**: Copernicus Data Space Ecosystem (CDSE) S3 authenticated pipeline ingesting Level-1 Single Look Complex (IW SLC) complex $I/Q$ measurement TIFFs on Track 150 Descending (`S1D_IW_SLC__1SDV_20260913...` and `S1D_IW_SLC__1SDV_20260901...`).
- **Processing Engine (`corrected_insar_engine.py`)**:
  1. Subswath & Burst Subsetting: Bursts 2 to 6 of Subswath IW1 covering Shillong, Cherrapunji, and Southern Meghalaya escarpments ($7,480\text{ lines} \times 21,282\text{ samples}$).
  2. TOPSAR Co-Registration & Enhanced Spectral Diversity (ESD): Integer cross-correlation ($\Delta\text{az} = -2\text{ px}, \Delta\text{rg} = -27\text{ px}$) plus double-difference phase in 154-line burst overlap seams, achieving residual misregistration of $0.100\text{ px}$.
  3. Spatial Coherence Estimation: Normalized complex cross-correlation over $5 \times 5$ window.
  4. 2D Coherence-Aware Connected-Component Unwrapping: BFS flood-fill unwrapping strictly confined within 329 isolated components ($\ge 20$ px). **Never bridges across decorrelated noise corridors**, preventing phase drift propagation.
  5. Topographic Phase Removal: USGS SRTM 30m DEM phase synthesis ($k_{\text{topo}} = -0.0565\text{ rad/m}$, perpendicular baseline $B_\perp = 117.11$ m).
  6. Authentic Bedrock Reference Anchor: In-swath stable Precambrian granitic gneiss reference station (`SHILLONG_PLATEAU_NORTH_BEDROCK_REF`, $25.7416^\circ\text{N}, 90.8500^\circ\text{E}$, elevation 1,042 m, coherence $\gamma = 0.8413$). Relative LOS displacement $d_{\text{LOS}} \equiv 0.00$ mm.
  7. 2D Orbital Planar Ramp Removal: First-order planar trend fitted over high-coherence bedrock ($\gamma \ge 0.50$) and subtracted to eliminate baseline tilt.
  8. Relative LOS Displacement Conversion: $d_{\text{LOS}} = -\frac{\lambda}{4\pi} \psi_{\text{unwrapped}}$ ($\lambda = 55.4657$ mm).
- **Quantitative Result**: Corrected relative LOS displacement bounded to $-272.13$ mm to $+271.42$ mm (mean $-4.68$ mm, median $-6.56$ mm), eliminating a $+3,177.8$ mm 1D integration drift defect.

> [!WARNING]
> **Mandatory Scientific Caveats Regarding InSAR**  
> 1. **Phase Conflation**: Differential interferometric phase observes a composite scalar projection: $\Delta\phi = \Delta\phi_{\text{defo}} + \Delta\phi_{\text{tropo}} + \Delta\phi_{\text{iono}} + \Delta\phi_{\text{orb}} + \Delta\phi_{\text{topo}} + \Delta\phi_{\text{noise}}$. In tropical monsoonal escarpments, atmospheric water vapor gradients can introduce $5\text{ to }15\text{ cm}$ of apparent delay. Single-pair InSAR is officially classified as **`RELATIVE LOS INTERFEROMETRIC OBSERVATION`** and must **never** be presented as a direct, unpolluted ground displacement map.  
> 2. **Vegetative Decorrelation**: In subtropical jungle, **93.43% of pixels exhibit low coherence ($\gamma < 0.35$)** and are masked as `NaN`. Low coherence indicates radar decorrelation, **never zero slope movement**.  
> 3. **Relative LOS Nature**: Measurements represent scalar projections along radar Line-of-Sight; vertical or slope-parallel vectors cannot be resolved without multi-geometry (ascending + descending) combinations.  
> 4. **Orbit Ephemerides Latency**: ESA Precise Orbit Ephemerides (`AUX_POEORB`) have a 20–25 day latency. Near-real-time InSAR operates on Restituted Orbit state vectors (`AUX_RESORB`, ~10 cm accuracy).  
> 5. **Multi-Temporal PSI Stack Limitation**: Current archives contain 2–3 repeat-pass scenes on Track 150 Descending. This is scientifically classified as **`INSUFFICIENT_SLC_STACK_FOR_PSI`** (Persistent Scatterer Interferometry requires 15–20+ scenes over multi-year baselines). Full time-series PSI inversion is `RESEARCH_ONLY`.

#### G. Real 3D Topographic Terrain & Web-GIS Integration (Phase 4A)
- **Source**: 16 validated USGS SRTM 1 Arc-Second DEM tiles (~30 m resolution, EPSG:4326).
- **Service Endpoint**: `GET /api/gis/terrain/tile?z={z}&x={x}&y={y}&w=65&h=65`
- **Output Encoding**: Pure binary IEEE 754 Float32Array ($65 \times 65$ grid cells = 4,225 floats = exactly 16,900 bytes per tile).
- **Tiling Scheme**: `Cesium.GeographicTilingScheme` (EPSG:4326, 2 root tiles at level 0, width=65, height=65 with 1-pixel overlap border for crack-free tile stitching).
- **Subdivision Depth**: Levels 6 through 13 active in scene graph (`tileCount`: 31 tiles loaded, resolving 24m sub-tile spacing and SRTM 30m grid).
- **Physical Elevation Validation**: Ray-cast pick proof at scene center $(92.0220^\circ\text{E}, 25.2114^\circ\text{N})$ returns $+294\text{ m}$ elevation above WGS84 ellipsoid; regional peak at $+1,890.4\text{ m}$ (Shillong Peak).
- **3D Infrastructure Draping & Extrusion**:
  - Roads: 2,865 genuine OSM major road segments clamped to ground (`clampToGround: true`, `arcType: Cesium.ArcType.GEODESIC`, width 5.0, material `#F59E0B`).
  - Buildings: 1,200 genuine OSM building footprints extruded relative to ground (`heightReference: RELATIVE_TO_GROUND`, `extrudedHeight: 25.0`, `extrudedHeightReference: RELATIVE_TO_GROUND`) with mandatory attribution label `VISUALIZATION EXTRUSION — NOT SURVEYED HEIGHT`.
- **Deduplication Invariant**: Strict entity deduplication enforces exactly 4,113 entities (2,865 roads + 1,200 buildings + 48 hotspots), preventing GPU memory bloat or z-fighting.

#### H. 2D Demographic Population Exposure Layer (Census 2011)
- **Source**: Census of India 2011 official administrative district population figures.
- **Service Endpoint**: `GET /api/gis/population`
- **Spatial Coverage**: 22 ADM2 districts across Meghalaya (11 districts) and Mizoram (11 districts), representing 4,568,123 citizens.
- **Attributes**: `district_name`, `state`, `population_total`, `density_persons_per_sqkm`, `area_sqkm`, `census_year: 2011`.
- **Visualization**: 4-tier demographic choropleth density styling ($>300$, $150-300$, $75-150$, $<75$ persons/km$^2$).
- **Scientific Invariant**: Population exposure operates strictly as **contextual consequence data with an operational risk weight of $0.00$**. It does **NOT** modify or add weights to the locked 4-factor physical risk formula ($0.40S + 0.30R + 0.20M + 0.10C$).

---

## 6. Production AI Model Architecture & Validation

```
+--------------------------------------------------------------------------------------------------+
| NER-SAFE PRODUCTION AI INFERENCE ARCHITECTURE                                                    |
+--------------------------------------------------------------------------------------------------+
                                  |
         +------------------------+------------------------+
         |                                                 |
         v                                                 v
+-------------------------------+               +-------------------------------+
| PRIMARY PRODUCTION MODEL      |               | AUTOMATIC FALLBACK MODEL      |
| Calibrated XGBoost Classifier | (Failure Trap)| Calibrated Random Forest      |
| Status: PRODUCTION_OFFICIAL   | ------------> | Status: PRODUCTION_FROZEN     |
| Path: calibrated_xgboost_...  |               | Path: calibrated_random_...   |
| Latency: 0.18 ms (48 pts)     |               | Latency: 0.23 ms (48 pts)     |
+-------------------------------+               +-------------------------------+
         |                                                 |
         +------------------------+------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------------------------------+
| PARALLEL SHADOW RESEARCH MODEL                                                                   |
| PyTorch Spatial 2D CNN (Corridor Patches)                                                        |
| Status: SHADOW_MODE (Evaluates spatial feature representations; zero production influence)        |
+--------------------------------------------------------------------------------------------------+
```

### 6.1 Official Production Susceptibility Model: Calibrated XGBoost
- **Promotion Status**: Officially promoted to production on September 14, 2026 (`XGBOOST_PRODUCTION_PROMOTION_VALIDATED`, Release `v1.1.0-PROD`).
- **Artifact Path**: `NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib`
- **Serialization**: `joblib` (`CalibratedClassifierCV` wrapping `XGBClassifier`, 539.3 KB)
- **SHA-256 Digest**: `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
- **Base Estimator Configuration**: `n_estimators=100`, `max_depth=4`, `learning_rate=0.05`, `scale_pos_weight=3.0`, `random_state=42`, `eval_metric='logloss'`.
- **Calibration Engine**: Platt sigmoid scaling fitted via 3-fold internal cross-validation (`method='sigmoid'`, `cv=3`).

### 6.2 Production 10-Feature Contract
The production XGBoost model consumes an exact 10-feature vector with 100% schema parity against the baseline Random Forest:

| Feature Index | Feature Name | Description / Source Layer | Range / Physical Units |
| :---: | :--- | :--- | :--- |
| 0 | `elevation` | USGS SRTM 1 Arc-Second DEM | Meters [0, 4000] |
| 1 | `slope` | Horn 8-neighbor gradient | Degrees [0, 90] |
| 2 | `aspect_sin` | Sine of aspect azimuth | Dimensionless [-1.0, 1.0] |
| 3 | `aspect_cos` | Cosine of aspect azimuth | Dimensionless [-1.0, 1.0] |
| 4 | `profile_curvature` | Zevenbergen-Thorne second derivative | $\text{m}^{-1}$ [-0.05, 0.05] |
| 5 | `twi` | Topographic Wetness Index $\ln(a / \tan\beta)$ | Dimensionless [2.0, 25.0] |
| 6 | `ndvi_imputed` | Sentinel-2 L2A Normalized Difference Veg Index | Dimensionless [-1.0, 1.0] |
| 7 | `ndwi_imputed` | Sentinel-2 L2A Normalized Difference Water Index| Dimensionless [-1.0, 1.0] |
| 8 | `ndmi_imputed` | Sentinel-2 L2A Normalized Difference Moisture | Dimensionless [-1.0, 1.0] |
| 9 | `sentinel_observed_flag`| SCL Cloud Mask (0 = Cloud-Imputed, 1 = Valid) | Binary {0.0, 1.0} |

### 6.3 Spatial Block Cross-Validation Metrics (832 Samples, 5 Geographic Folds)

Validation was conducted on the authoritative Component 10 dataset (832 balanced samples: 208 landslide occurrences + 624 non-landslide points, 1:3 ratio) using **5-Fold Geographic Spatial Block Partitioning** across distinct physiographic blocks (zero random pixel splitting):

| Metric | Random Forest Baseline | Calibrated XGBoost (Production) | Evaluation Delta | Statistical Significance |
| :--- | :---: | :---: | :---: | :--- |
| **Spatial PR-AUC** | 0.3151 | **0.3608** | **+0.0457 (+14.5%)** | Superior precision-recall trade-off |
| **Spatial ROC-AUC** | **0.5654** | **0.5603** | -0.0051 | Equally matched discrimination |
| **Brier Score** | 0.2035 | **0.1984** | **-0.0051** | Lower error; sharper probabilistic calibration |
| **Expected Calibration Error (ECE)** | 0.1259 | **0.1065 – 0.1092** | **-0.0167** | Significantly better calibrated probabilities |
| **Inference Latency (48 Hotspots)** | 0.23 ms | **0.18 ms** | **-21.7%** | 0.0037 ms per evaluation point |
| **RAM Footprint** | 48.2 MB | **14.6 MB** | **-69.7%** | Compact memory footprint |

> [!NOTE]
> **Understanding the Modest Spatial ROC-AUC (0.5603)**  
> Random pixel-splitting cross-validation in geospatial applications artificially inflates ROC-AUC scores (often $>0.85$) through spatial autocorrelation leakage. NER-SAFE enforces strict **Geographic Block Partitioning**, where models are trained on four geographic quadrants and tested on an entirely unseen mountain block (e.g., training on Khasi Hills and evaluating on Garo Hills or Mizoram). The modest ROC-AUC reflects realistic out-of-region terrain transferability; it must not be conflated with poor model design.

### 6.4 Model Governance, Fault Injection & Rollback Controls
- **Automated Fallback**: If the XGBoost model encounters missing files, corrupted headers, column mismatches, unhandled NaNs, or memory exhaustion, `XGBoostProvider` catches the exception and immediately falls back to `RFProductionProvider`.
- **Non-Silent Fallback Rule**: Every fallback event logs `fallback_triggered: true` and writes the root cause to `provider_manager.last_fallback_reason`.
- **Instant Zero-Code Rollback**: Setting `$env:SUSCEPTIBILITY_MODEL = "rf"` in the environment instantly switches active inference back to Random Forest without code changes or restarts.
- **Parallel Shadow CNN**: PyTorch Spatial CNN evaluates $64 \times 64$ patch representations in parallel shadow mode (`PyTorchCNNProvider`), but has zero authority over production risk tiers.

---

## 7. Locked Four-Factor Operational Risk Fusion Architecture

The core operational risk score is computed through an invariant, mathematically locked four-factor fusion equation evaluated across all 48 monitored failure initiation points:

$$\text{Risk\_Score} = 0.40 \cdot \text{Susceptibility} + 0.30 \cdot \text{Rainfall\_Anomaly} + 0.20 \cdot \text{Soil\_Moisture\_Anomaly} + 0.10 \cdot \text{Satellite\_Change\_Flag}$$

### 7.1 Factor Lineage & Formulations
1. **Static Geomorphic Susceptibility ($w_1 = 0.40$)**: Calibrated XGBoost probability $P(\text{Landslide} \mid \mathbf{x}) \in [0.0, 1.0]$ on 30m SRTM DEM derivatives.
2. **Antecedent Rainfall Anomaly ($w_2 = 0.30$)**: 3-day cumulative precipitation anomaly from NASA GPM IMERG Early NRT normalized relative to regional monsoon climatology.
3. **Soil Moisture Saturation Anomaly ($w_3 = 0.20$)**: NASA SMAP L3 top-5cm volumetric soil moisture mapped to relative saturation index $[0.0, 1.0]$.
4. **Satellite Surface Change Flag ($w_4 = 0.10$)**: Sentinel-1 SAR amplitude change ($\Delta \sigma^0$) and Sentinel-2 optical bi-temporal NDVI/NDWI loss.

### 7.2 Operational Threat Matrix
- 🔴 **Critical Tier**: $\text{Risk\_Score} \ge 0.65$
- 🟠 **High Tier**: $0.48 \le \text{Risk\_Score} < 0.65$
- 🟡 **Moderate Tier**: $0.32 \le \text{Risk\_Score} < 0.48$
- 🟢 **Watch Tier**: $\text{Risk\_Score} < 0.32$

### 7.3 Governance Invariants (Strict Anti-Corruption Rules)
1. **No Fifth Weight**: IMD weather is **never** added as a fifth weight; it serves exclusively as independent ground corroboration.
2. **External Sources Excluded from Weighting**: GSI Bhusanket, NDMA SACHET, ISRO Bhuvan, OSINT, and OSIRIS are **never** injected into the risk formula. They provide additive situational evidence.
3. **Exposure Excluded from Hazard Score**: Infrastructure exposure (roads, buildings, population) affects consequence triage; it **never** artificially inflates the physical AI risk score.

---

## 8. Scientific Forecasting Claims & Temporal Event Limitations

### 8.1 Scientifically Defensible Claim
NER-SAFE is formally defined and defended as:
> **"A platform forecasting the probability of elevated landslide risk within defined spatial zones and future operational monitoring windows."**

### 8.2 Explicit Scientific Disclaimers
The system explicitly disclaims:
- Deterministic prediction of exact failure time (hour/minute/second).
- Pin-point exact failure coordinates down to sub-meter scale.
- Guaranteed prediction of every slope failure.
- Claims of 100% forecasting accuracy.
- Interpretation of InSAR phase as direct, unpolluted millimeter ground displacement.

### 8.3 Temporal Event Forecasting Governance
An empirical audit of the 260 historical landslide events in Northeast India confirmed:
- Historical landslide records record dates of discovery or reporting; **zero records contain sensor-coincident time-of-day timestamps**.
- Historical landslide events (2007–2023) have **0.0% temporal overlap** with operational satellite feeds (2024–2025).
- In adherence to scientific integrity, **temporal event forecasting is classified as `NOT_SCIENTIFICALLY_VALIDATED / AWAITING_TEMPORAL_LABELS`**. Synthetic event timestamps will never be fabricated to train temporal machine learning models.

---

## 9. Flow-Path, Runout & Infrastructure Exposure Consequence Engine

The consequence modeling subsystem (Component 11) decouples physical hazard probability from downstream consequence:

```
+--------------------------------------------------------------------------------------------------+
| COMPONENT 11: FLOW-PATH, RUNOUT & EXPOSURE ENGINE                                               |
+--------------------------------------------------------------------------------------------------+
   Initiation Point (Lat/Lon)
         |
         v
   D8 Steepest Downhill Descent Routing on 30m SRTM DEM (Zero Uphill Steps Enforced)
         |
         +--> D8 Flow Path Streamline (Length: mean 324.9 m, Drop: mean 87.4 m)
         |
         v
   Fahrböschung Reach Angle (<10°) & Lateral Spreading Envelope (70m Scarp to 120m Deposition)
         |
         +--> 48 GIS Runout Corridor Envelopes (Mean Area: 38,240 m²)
         |
         v
   Spatial STRtree Intersection with Exposure Layer (roads, buildings, settlements)
         |
         +--> 2,275.4 m Road Network (NH-06, NH-54 Lifelines)
         +--> 30 Building Footprints
         +--> 138 Estimated Exposed Citizens
         |
         v
   Consequence Prioritization Matrix (10 Critical, 2 High, 6 Moderate, 30 Low)
```

- **Road Connectivity States**: Modeled as `OPEN`, `AT_RISK` (corridor intersection), `BLOCKED` (field-verified failure), or `UNKNOWN`.
- **Consequence Triage**: Directs emergency tasking to corridors intersecting critical lifelines without modifying the physical risk score.

---

## 10. External Intelligence Subsystems

NER-SAFE integrates external government and intelligence repositories strictly as independent corroboration, situational context, and validation benchmarks:

| External Source | Upstream Authority | Access Mechanism | Current Status | Role in NER-SAFE Platform |
| :--- | :--- | :--- | :--- | :--- |
| **GSI Bhusanket WebAPI** | Geological Survey of India | REST JSON (`Referer` Header) | `LIVE_VERIFIED` | 109 active landslide bulletins & highway blockade notices |
| **GSI Bhusanket ArcGIS** | GSI NLFC | Hosted FeatureServer | `INSTITUTIONAL_ACCESS_REQUIRED` | Pan-India Landslide FeatureServer (HTTP 499 Token Required) |
| **GSI Bhukosh Catalog** | GSI Bhukosh Portal | Standardized GIS Points | `VALIDATED` | 185 independent test landslide events |
| **NDMA SACHET CAP** | NDMA / C-DAC | CAP 1.2 REST JSON | `LIVE_VERIFIED` | Real-time public multi-hazard warning feeds |
| **ISRO / Bhuvan WMS** | ISRO / NRSC | OGC WMS GetCapabilities | `LIVE_VERIFIED` | Geospatial disaster management overlays (7.5 MB XML) |
| **ISRO Landslide Atlas** | NRSC / ISRO | District Geodatabase | `VALIDATED` | District vulnerability baselines across 147 districts |
| **OSINT News Intelligence**| Local Media / RSS Feeds | Multi-Scale NLP Scraper | `LIVE_VERIFIED` | Ground outcome discovery & lead-time verification |
| **OSIRIS AI Platform** | Open-Source (`simplifaisoul`) | Public REST Feeds | `LIVE_VERIFIED` (Partial) | Secondary USGS seismic triggers & GDACS macro alerts |

### 10.1 External Concordance Audit
Evaluated against 9 published GSI bulletins across Meghalaya and Mizoram:
- **Full Agreement (`AGREE`)**: **6 / 9 (66.7%)**
- **Partial Agreement (`PARTIAL_AGREEMENT`)**: **3 / 9 (33.3%)**
- **Outright Conflict (`DISAGREE`)**: **0 / 9 (0.0%)**
- **Reporting Rule**: Accurately reported as **6/9 full matches, 3/9 partial matches, 0 conflicts** (never exaggerated as "100% concordance").

---

## 11. Open Source Intelligence (OSINT) Subsystem

The OSINT Event Intelligence Subsystem (`osint_intelligence_engine.py`) crawls regional media to discover ground-truth failure reports and evaluate advance warning lead times:

### 11.1 Multi-Scale Spatial Matching Hierarchy
To prevent spatial inflation where distant events are claimed as slope-scale hits, NER-SAFE enforces a strict four-tier matching hierarchy:

```
+--------------------------------------------------------------------------------------------------+
| Match Scale       | Distance Threshold           | Physical Meaning & Model Qualification        |
+--------------------------------------------------------------------------------------------------+
| SITE_MATCH        | distance <= 2.0 km           | Direct hillslope / scarp validation. Valid    |
|                   |                              | true positive for 30m DEM hotspot models.     |
+--------------------------------------------------------------------------------------------------+
| CORRIDOR_MATCH    | 2.0 km < distance <= 5.0 km  | Linear transportation lifeline or runout      |
|                   | OR D8 corridor overlap       | deposition zone. Valid corridor hit.          |
+--------------------------------------------------------------------------------------------------+
| REGIONAL_MATCH    | 5.0 km < distance <= 45.0 km | Broad district / regional elevated risk.      |
|                   |                              | NOT a site-level model hit.                   |
+--------------------------------------------------------------------------------------------------+
| NO_MATCH          | distance > 45.0 km           | Outside regional evaluation buffer.           |
+--------------------------------------------------------------------------------------------------+
```

### 11.2 Early Operational Validation Metrics
Evaluated across 12 canonical events and 20 prediction windows (16 resolved outcomes, 4 unknown coverage):
- **Calibrated XGBoost (Production)**: 11 evaluated outcomes $\to$ 4 Site True Positives ($\le 2$ km, mean error 0.95 km), 2 Regional True Positives ($5-45$ km), 1 False Positive, 1 False Negative, 3 Unknown Coverage.
  - **Site Precision**: **80.0%** | **Site Recall**: **80.0%** | **Site F1**: **80.0%**
  - **Operational Hit Rate**: **54.5%** (6/11)
  - **Median Advance Lead Time**: **28.00 hours** ($P_{05} = 24.31\text{h}, P_{95} = 31.42\text{h}$)
- **Governance Rule**: OSINT outcome metrics represent **early operational validation** on 20 outcomes; they are reported separately and **never merged** with historical susceptibility validation (832 samples).

---

## 12. OSIRIS Open-Source Intelligence Platform Integration

NER-SAFE integrates an audited adapter (`osiris_adapter.py`) connecting to the public OSIRIS AI platform (`simplifaisoul/osiris`):
- **Platform Identity**: OSIRIS is an open-source Next.js/MapLibre web intelligence dashboard. It is **not** a drone platform.
- **Approved Operational Routes**:
  1. `/api/earthquakes` (USGS M2.5+ feed): Ingested as secondary seismic triggering context for slope instability.
  2. `/api/gdelt` (Actually queries the GDACS XML RSS feed): Ingested for regional macro-disaster alerts.
- **Rejected / Non-Applicable Routes**:
  - `/api/cctv`: **REJECTED** (OSIRIS has 17,240 cameras globally, but **0 in India** and **0 in NER**).
  - `/api/weather`: **REJECTED** (US National Weather Service alerts only; zero India coverage).
  - `/api/news`: **REJECTED** (Indexes international conflict zones; zero local Northeast vernacular news).
  - `/api/sentinel`: **REJECTED** (Duplicate of NER-SAFE's direct CDSE S3 pipeline).
  - `/api/fires`, `/api/arcgis`, `/api/region-dossier`, `/api/ai/briefing`: Classified as `RESEARCH_ONLY`.
- **Governance Invariant**: OSIRIS data is additive contextual intelligence; it **never** alters risk scores or weights.

---

## 13. India Meteorological Department (IMD) Integration Status

### 13.1 Official Gateway & Registration Architecture
- **Official Portal**: `https://api.imd.gov.in/api/v1/` (21 REST endpoints mapped in `imd_api_client.py`).
- **Authentication Discovery**: Dual-Header authentication verified via live challenge (`X-Api-Key` + `Authorization: Bearer <JWT>`).
- **Target Stations Mapped**: Shillong Observatory (`42516`), Cherrapunji/Sohra (`42515`), Aizawl Observatory (`42619`).
- **Current Official Status**: **`PENDING INSTITUTIONAL AUTHORIZATION / ACCESS APPROVAL` (`IMD_AUTH_REQUIRED`)**. Access requires an institutional Memorandum of Understanding (MoU) under Ministry of Earth Sciences (MoES) data policies.

### 13.2 Live Public Ingestion & GPM Corroboration Engine
- **Live Mausam Nowcast Feed (`LIVE_OPERATIONAL`)**: Ingests open real-time severe weather nowcasts (`mausam.imd.gov.in/responsive/nowcast.geojson`) for East Khasi Hills, Aizawl, and surrounding districts without credentials.
- **GPM Ground Corroboration Engine**: Automatically evaluates spatial separation (3.91 km at Shillong), timestamp delta, and rainfall difference between GPM satellite grids and IMD station points.
- **Zero-Fabrication Invariant**: The system refuses to force mathematical agreement between sensors. IMD rainfall functions as independent ground corroboration; credentials are never hardcoded or exposed.

---

## 14. Institutional Ground Sensor Availability

- **Target Modalities**: Multi-depth vibrating-wire piezometers (pore water pressure), borehole MEMS inclinometers (shear plane displacement), tipping-bucket rain gauges, and soil suction tensiometers.
- **Identified Institutional Stations**: NIT Meghalaya Mawiongrim slope station (696 hourly records cached in `NER_SAFE_DATA/SENSORS/mawiongrim_telemetry.csv`), NEHU experimental research station, MIRSAC Aizawl SILAAS municipal network.
- **Operational Status**: **`INSTITUTIONAL_ACCESS_REQUIRED`**.
- **Governance Invariant**: The NER-SAFE team has **not** deployed physical hardware on Himalayan slopes. Do-it-yourself (DIY) or maker ESP32 hardware is **strictly excluded** from the production architecture. The system provides a hardware-neutral schema to ingest institutional sensor telemetry when administrative data-sharing agreements are executed.

---

## 15. Multi-Channel Alert & Decision-Support System

### 15.1 Standards Compliance & Schemas
- **ITU-T CAP v1.2**: Full compliance with OASIS / ITU-T Common Alerting Protocol XML and JSON schemas.
- **NDMA SACHET Format**: Interoperable JSON payloads mapped to national disaster management standards.

### 15.2 Alert Dissemination Channels & Safeguards
- **SMS Broadcast Simulation**: Formatted strictly within telecom $\le 160$ character limits with certified regional language templates.
- **Push Notifications & Webhooks**: High-priority JSON payloads formatted for District Emergency Operation Centers (DEOC).
- **Hysteresis Thresholds**: Prevents rapid alert toggling (Critical entry 0.70 / exit 0.60; High entry 0.52 / exit 0.44).
- **Alert Fatigue Deduplication**: Suppresses redundant advisory broadcasts within a 4-hour moving window.
- **Delivery Lifecycle States**: `GENERATED` $\to$ `QUEUED` $\to$ `SENT` $\to$ `DELIVERED` $\to$ `FAILED` $\to$ `WAITING_FOR_NETWORK` $\to$ `EXPIRED`.

### 15.3 Multilingual Localization
Alert payloads are dynamically generated in **English**, **Hindi**, **Khasi**, and **Mizo** using certified regional emergency templates:
- **Khasi Example**: *"KHYNDEW KHLYNKEP JINGMAHUR (RED ALERT): Ka jaka [Location] ka don ha ka jingmahur kaba khraw..."*
- **Mizo Example**: *"LEI MIN HLAUHAWM (RED ALERT): [Location] ah lei min hlauhawm a sang hle..."*

---

## 16. Four-Level Connectivity & Zero-Network Operational Architecture

To operate reliably in remote Himalayan valleys prone to total infrastructural collapse, NER-SAFE enforces a four-level network state machine (`network_state_manager.py`):

| Connectivity Level | Network State | Available Infrastructure | Operational Behavior & Alerts |
| :--- | :--- | :--- | :--- |
| **Level 1: High** | `ONLINE_BROADBAND` | Full Internet (Fiber / 4G) | Real-time satellite polling, live GIS map tiles, cloud sync, full API access |
| **Level 2: Weak** | `CELLULAR_LIMITED` | Edge 2G/3G Cellular | Compressed JSON payloads, static vector basemaps, SMS broadcast priority |
| **Level 3: Intermittent**| `INTERMITTENT_LINK` | Sporadic Packets | Store-and-forward outbox queues with exponential backoff retry |
| **Level 4: Blackout** | `ZERO_NETWORK` | Complete Blackout | **Local Edge Server Mode**. Telecom SMS explicitly disclaimed. Relies on local cached risk, displays **`LAST SYNCHRONIZED RISK: [Score]`**, and triggers software siren protocols. |

---

## 17. Crowdsourced Citizen Ground Hazard Reporting Subsystem

- **Responsive Client**: Single-page mobile HTML5/CSS3 application (`ner_safe_citizen_app.html`, 679 KB) optimized for low-end mobile devices.
- **Geospatial Schema**: RFC 7946 GeoJSON with Point-in-Polygon validation against Survey of India boundaries, GPS horizontal accuracy bounds ($\le 100$ m), crack displacement width measurements, and water seepage classifications.
- **Offline Persistence**: Client-side `localStorage` queue with deterministic `PENDING_LOCAL` $\to$ `SYNCHRONIZED_LOCAL` transitions.
- **50-Meter Proximity Clustering**: Spatial deduplication algorithm grouping nearby incident reports within a 50m radius to prevent scarp reporting floods.
- **Verification Workflow**: Role-restricted moderation (`UNVERIFIED_OBSERVATION` $\to$ `UNDER_REVIEW` $\to$ `FIELD_VERIFIED` or `REJECTED_FALSE_ALARM`).
- **Integrity Invariant**: Citizen submissions are strictly tagged (`record_type: "SYNTHETIC_DEMONSTRATION"` for demo records). They are strictly isolated from machine learning models; **zero automated model retraining occurs on citizen inputs**.

---

## 18. Operations Dashboard & Modern Web GIS

The Unified Operations Portal (`ner_safe_live_dashboard.html`, `ner_safe_live_dashboard_extended.html`) is an existing, fully operational component conforming to Government of India UX4G 3.0 guidelines and featuring a dual-mode Web-GIS operational architecture.

### 18.1 Dual-Mode 2D/3D Web-GIS Architecture
- **Primary Operational 2D Map (Leaflet 1.9.4)**:
  - Default road-oriented basemap: OpenStreetMap Standard tiles revealing dynamic street, settlement, and village names.
  - Basemap Switcher: Instant switching between OpenStreetMap, Esri World Imagery Satellite, and Positron Light GIS.
  - Google-Maps-Style Floating Search: Autocomplete querying 48 hotspots, districts, lifelines (NH-06, NH-54, NH-206), and settlements with smooth camera flyTo.
  - Interactive Hotspot Runout Inspector: Displays flow path distance ($136.4\text{ m}$), elevation drop ($\Delta Z = 32\text{ m}$), Fahrböschung reach angle ($10.0^\circ$), and exposed asset counts.
  - Census 2011 Population Choropleth: Toggleable 4-tier demographic density layer across 22 ADM2 districts with zero operational risk weight.
- **Toggleable 3D Topographic Terrain Globe (CesiumJS 1.119+)**:
  - Activated via the `3D Terrain` basemap button (`#btnBasemap3D`).
  - Seamlessly transitions viewport from 2D Leaflet (`#liveMap`) to 3D Cesium globe (`#cesiumContainer`).
  - Automated WebGL Fallback: If hardware WebGL initialization fails, the system automatically presents a non-blocking UX4G-compliant notice (`#cesiumFallbackNotice`) and safely retains the fully operational 2D Leaflet interface without crashing.

### 18.2 Dynamic 3D Terrain Elevation Engine
- **Endpoint**: `GET /api/gis/terrain/tile?z={z}&x={x}&y={y}&w=65&h=65`
- **Terrain Provider**: `Cesium.CustomHeightmapTerrainProvider` with `Cesium.GeographicTilingScheme` (EPSG:4326).
- **Physical Tile Payload**: Pure binary IEEE 754 Float32Array ($65 \times 65$ floats = 16,900 bytes per tile) extracted directly from the validated 16-tile USGS SRTM 30m mosaic.
- **Level of Detail (LOD) Subdivision**: Reaches Level 13 in active camera frustum (`tileCount`: 31 active tiles, sub-tile spatial resolution $\approx 24\text{ m}$).
- **Elevation Ray-Cast Pick Proof**: Center ray-cast pick at $(92.0220^\circ\text{E}, 25.2114^\circ\text{N})$ returns $+294\text{ m}$ ground elevation, accurately reflecting the West Jaintia Hills / Shillong Plateau escarpment.

### 18.3 3D Infrastructure Draping & Extrusions
- **3D Lifeline Roads Network**:
  - 2,865 genuine OSM major road segments draped onto terrain.
  - Configured with `clampToGround: true`, `arcType: Cesium.ArcType.GEODESIC`, width 5.0, and high-visibility `#F59E0B` gold material.
- **3D Building Footprints**:
  - 1,200 genuine OSM digitized building footprints.
  - Configured with `height: 0.0, heightReference: RELATIVE_TO_GROUND, extrudedHeight: 25.0, extrudedHeightReference: RELATIVE_TO_GROUND`, ensuring buildings sit precisely upon the SRTM terrain surface rather than sinking into bedrock.
  - Mandatory Attribution Label: Explicitly tagged `25m (VISUALIZATION EXTRUSION — NOT SURVEYED HEIGHT)`.
- **Entity Deduplication**: Strict asynchronous loading guards enforce an exact entity budget of **4,113 entities** (2,865 roads + 1,200 buildings + 48 hotspots), eliminating GPU draw-call inflation and z-fighting.

### 18.4 Single Source of Truth Parity Matrix
To ensure 100% mathematical and operational synchronization, all spatial, mathematical, and exposure metrics for monitored hotspots are identical across backend API, 2D Leaflet, and 3D Cesium (verified on focal event `EVT-MEG-012`):

| Metric / Dimension | Backend API (`/api/monitoring/hotspots`) | 2D Leaflet Map (`#liveMap`) | 3D Cesium Globe (`#cesiumContainer`) | Consistency Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Event ID** | `EVT-MEG-012` | `EVT-MEG-012` | `EVT-MEG-012` | **100% IDENTICAL** |
| **Spatial Coordinates** | $[92.027083^\circ\text{E}, 25.185694^\circ\text{N}]$ | $[92.027083^\circ\text{E}, 25.185694^\circ\text{N}]$ | $[92.027083^\circ\text{E}, 25.185694^\circ\text{N}]$ | **100% IDENTICAL** |
| **Fused Risk Score** | `0.7716` | `0.7716` | `0.7716` | **100% IDENTICAL** |
| **Operational Threat Tier** | `CRITICAL` | `CRITICAL` | `CRITICAL` | **100% IDENTICAL** |
| **Susceptibility ($w_1=0.40$)**| `0.6779` | `0.6779` | `0.6779` | **100% IDENTICAL** |
| **Rainfall Anomaly ($w_2=0.30$)**| `0.8551` | `0.8551` | `0.8551` | **100% IDENTICAL** |
| **Soil Moisture ($w_3=0.20$)**| `0.7192` | `0.7192` | `0.7192` | **100% IDENTICAL** |
| **Surface Change ($w_4=0.10$)**| `1.0000` | `1.0000` | `1.0000` | **100% IDENTICAL** |
| **Exposed Highway Segments** | 3 segments ($325.4\text{ m}$ on NH-206) | 3 segments ($325.4\text{ m}$ on NH-206) | 3 segments ($325.4\text{ m}$ on NH-206) | **100% IDENTICAL** |
| **Exposed Building Footprints**| 10 footprints | 10 footprints | 10 footprints | **100% IDENTICAL** |

### 18.5 Authoritative Visual Acceptance Verification
- **Automated CDP Runtime Inspection**: Verified using headless Chrome runtime connected via Chrome DevTools Protocol (`run_final_visual_acceptance.js`).
- **Telemetry Artifact**: `FINAL_VISUAL_ACCEPTANCE_DATA.json` (0 console errors, 0 local network failures, `tilesLoaded: true`).
- **Verified Visual Render Artifacts**:
  1. `cesium_real_terrain_render.png` ($1920 \times 1080$): Proves real 3D topographic relief of the Shillong Plateau / West Jaintia Hills escarpment, 48 live risk hotspots, NH-206 highway corridor, and D8 flowpath corridors.
  2. `cesium_hotspot_closeup_render.png` ($1920 \times 1080$): Proves dead-center framing of `EVT-MEG-012` at $(x=632, y=393)$ on canvas, visible slope gradient ($\Delta Z = 32\text{ m}$), 10 visible building footprints, draped highway corridor, and interactive sidebar risk inspector.
- **Formal Status**:
```
================================================================================
3D_REAL_RENDERING: VERIFIED
================================================================================
```
- **UX4G Compliance**: 100% SVG vector iconography; **strictly zero emojis** across all controls, badges, and popups.

---

## 19. Live Monitoring Cadence & Scheduler Architecture

The autonomous live monitoring scheduler (`live_monitoring_scheduler.py`) manages multi-source data ingestion on precise, decoupled cadences:
- **NASA GPM IMERG Early NRT**: Half-hourly polling cadence (~4-hour NASA processing latency).
- **NASA SMAP Soil Moisture**: Daily polling cadence (~24-hour satellite orbit cycle).
- **Sentinel-1 SAR / InSAR**: 12-day repeat-pass cycle per track (Track 150 Descending).
- **Sentinel-2 Optical**: 5-day constellation revisit (10–12 day cloud-free revisit).
- **IMD Mausam Nowcasts**: 3-hour moving window refresh.
- **Timestamp Decoupling**: Explicitly separates physical `observation_time` from system `ingested_time` to prevent false claims of zero-latency synchronization.
- **Freshness Governance**: Feeds exceeding latency cutoffs transition to `DATA_STALE` or `AWAITING_FRESH_DATA`; synthetic default scores are strictly prohibited.

---

## 20. Cloud & Server Infrastructure Architecture

### 20.1 Planned College Server Allocation
- **Compute (vCPU)**: 4 cores / 4 vCPU
- **Memory (RAM)**: 16 GB
- **System Storage**: 100 GB SSD/NVMe
- **Operating System**: Ubuntu Server 22.04 LTS or Ubuntu Server 24.04 LTS
- **Access Architecture**: Authorized non-root SSH project account with key-based authentication (root privileges retained by institutional sysadmin).
- **Current Operational Status**: **`CLOUD/SERVER ACCESS PENDING INSTITUTIONAL APPROVAL / PROVISIONING`**.

### 20.2 Server Responsibilities
The 100 GB server is designated as an **operational processing and API gateway node**:
- Python multi-threaded REST API server (`server.py`) and background scheduler (`live_monitoring_scheduler.py`).
- Shared relational SQLite database (`ner_safe_shared.db`).
- Static web server for GIS operations dashboards and citizen reporting web client.
- Production AI inference engine executing Calibrated XGBoost and Random Forest fallback.
- Controlled external API polling daemon (NASA CMR, CDSE OData, IMD Mausam, SACHET).
- Audit log rotation and system health monitoring.

---

## 21. Tiered Storage Strategy

```
+--------------------------------------------------------------------------------------------------+
| TIERED STORAGE ARCHITECTURE                                                                      |
+--------------------------------------------------------------------------------------------------+
| TIER 1: ACTIVE LOCAL COMPUTE (Local Disk / 100 GB Server)                                        |
| Scope    : Operational SQLite database, model artifacts, aligned 30m feature cache, logs         |
| Capacity : Strictly maintained under 40 GB working set footprint                                |
+--------------------------------------------------------------------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------------------------------+
| TIER 2: REMOTE CLOUD ARCHIVE (Google Drive API v3 / 5 TB Cloud Storage)                          |
| Scope    : Multi-gigabyte Level-1 IW SLC scenes (7.18 GB each), raw 10m Sentinel-2 rasters (9.8 GB), |
|            full-resolution terrain derivatives (2.8 GB), and timestamped prediction snapshots    |
| Protocol : Authenticated OAuth2 multipart upload pipeline (`google_drive_archive.py`)            |
+--------------------------------------------------------------------------------------------------+
                                  |
                                  v
+--------------------------------------------------------------------------------------------------+
| TIER 3: PROTECTED OFFLINE BACKUP (External HDD)                                                  |
| Scope    : Master immutable archive of historical datasets and baseline code freezes             |
| Rule     : Protected offline cold backup; STRICTLY FORBIDDEN to be modified by automated scripts|
+--------------------------------------------------------------------------------------------------+
```

---

## 22. Production Security & RBAC Governance

- **Password Cryptography**: NIST PBKDF2-HMAC-SHA256 with 100,000 iterations, 16-byte cryptographically secure random salt, and constant-time verification (`hmac.compare_digest`).
- **Session Architecture**: Server-side session store in SQLite with high-entropy 32-byte tokens (`secrets.token_urlsafe(32)`), 7-day sliding expiration, and `HttpOnly`, `SameSite=Lax` cookie flags.
- **Four-Tier RBAC**:
  - `PUBLIC_USER`: Browse public maps, view advisories, submit citizen reports.
  - `FIELD_OFFICER`: In-situ verification desk access (`FIELD_VERIFIED`, `REJECTED_FALSE_ALARM`).
  - `ANALYST`: Advanced analytics, raster layers, and raw environmental telemetry.
  - `ADMIN`: User management, role elevation approvals, and security audit log review.
- **Administrative Safeguards**: Prevention of self-approval for role elevation; strict prevention of demoting the final active administrator.
- **Credential Governance**: All credentials managed exclusively via `.env`; zero secrets committed to version control, documentation, or client-side bundles.

---

## 23. Verification Philosophy & Test Suites

The platform enforces a test-driven verification philosophy across 18 dedicated validation and regression test suites:

| Test Suite / Validation Scope | Acceptance Checks | Verification Result | Focus Area |
| :--- | :---: | :---: | :--- |
| **Component 10 AI Validation Suite** | 23 Gates | **PASS (23/23)** | Spatial Block CV, Leakage Audit (8/8 rules), Calibration Brier Score |
| **Component 11 Flow-Path Suite** | 16 Gates | **PASS (16/16)** | D8 Steepest-Descent, STRtree exposure intersection, lifeline corridors |
| **Component 12 Alert Dispatch Suite** | 16 Gates | **PASS (16/16)** | ITU-T CAP v1.2 XML/JSON, SMS character limits ($\le 160$), DEOC webhooks |
| **Component 13 Citizen Reporting Suite**| 18 Gates | **PASS (18/18)** | GeoJSON RFC 7946, SoI PIP boundary check, 50m clustering heuristic |
| **Security, RBAC & Persistence Suite** | 38 Checks | **PASS (38/38)** | NIST PBKDF2 hashing, session expiry, RBAC enforcement, SQLi resilience |
| **Live Multi-Source Fusion Suite** | 21 Checks | **PASS (21/21)** | Locked 4-factor fusion, decoupled freshness timestamps, REST endpoints |
| **Satellite Provenance & Cloud Suite** | 41 Checks | **PASS (41/41)** | Genuine NASA CMR queries, Google Drive API v3 upload, provenance schemas |
| **InSAR Scientific Pipeline Suite** | 27 Checks | **PASS (27/27)** | Corrected ESD co-registration, 2D BFS unwrapping, bedrock anchor |
| **Live GIS Website Validation Suite** | 15 Checks | **PASS (15/15)** | Real DEM tiles, clamped roads, extruded buildings, Census 2011 population |
| **GIS Visualization Correction Suite** | 16 Gates | **PASS (16/16)** | DEM coverage, tile Float32 arrays, OSM 3D layers, risk weight invariance |
| **Operational Website Sync Suite** | 18 Gates | **PASS (18/18)** | 2D/3D parity, UI elements, API synchrony, zero-emoji compliance |
| **Phase 4A 3D Terrain Suite** | 7 Gates | **PASS (7/7)** | CesiumJS DOM, 3D toggle, WebGL fallback notice, risk independence |
| **Judge Demonstration Smoke Suite** | 38 Checks | **PASS (38/38)** | E2E demo pipeline, replay isolation, zero-emoji audit, artifact hashes |
| **Automated CDP Visual Acceptance** | Verified | **PASS (100%)** | Real Chrome runtime, ray-cast pick proof (+294m), 0 console errors |
| **Extended Regression Suite** | 204 Tests | **PASS (204/204)** | End-to-end multi-source scheduler, models, and API regression |
| **Protected Release Baseline Manifest**| 101 Files | **101/101 MATCH** | SHA-256 bit-level invariance of frozen release baseline |

---

## 24. SIH 26001 Requirement Traceability Matrix

| SIH 26001 Requirement | NER-SAFE Capability | Current Implementation | Repository Evidence | Status | Remaining Gap |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Rainfall Monitoring** | Synoptic satellite rainfall | GPM IMERG 181-day archive & live half-hourly NRT ingestion | `NER_SAFE_DATA/GPM/`, `gpm_validator.py` | `LIVE_VERIFIED` / `AUTO_UPDATE_VERIFIED` | 10 km grid resolution; IMD ground stations pending MoU |
| **Soil Moisture Sensing** | Satellite soil saturation | SMAP L3 9km enhanced radiometer archive (180/181 files) | `NER_SAFE_DATA/SMAP/raw/`, `audit_smap.py` | `VALIDATED` (With Gap) | Coarse 9 km grid; 2025-03-18 NASA satellite outage gap |
| **Satellite Imagery** | Optical surface vigor | Sentinel-2 L2A 10m/30m NDVI, NDWI, NDMI with SCL masking | `NER_SAFE_DATA/SENTINEL2/`, `validate_sentinel2_indices.py` | `VALIDATED` | Cloud cover requires median imputation during monsoon |
| **Terrain & Slope Analysis** | High-res geomorphology | USGS SRTM 30m DEM + 5 full derivatives (388.8M cells) + Real 3D Terrain Tile Service (`/api/gis/terrain/tile`) | `NER_SAFE_DATA/TERRAIN/derivatives/`, `gis_service.py` | `VALIDATED` | 30m DEM cannot resolve sub-meter road cut anomalies |
| **Historical Landslides** | Ground-truth event catalog | 260 standardized georeferenced events (GLC, Bhukosh, Bhuvan) | `NER_SAFE_DATA/LANDSLIDE_INVENTORY/` | `VALIDATED` | Lacks exact time-of-day timestamps |
| **AI/ML Susceptibility** | Spatial susceptibility model| Calibrated XGBoost primary (PR-AUC 0.3608) + RF fallback | `NER_SAFE_DATA/COMPONENT_10/models/` | `VALIDATED` | Modest ROC-AUC (0.5603) under spatial block CV |
| **High-Risk Identification** | 4-tier operational threat matrix| Locked 4-factor fusion (0.40/0.30/0.20/0.10) on 48 hotspots | `fusion_engine.py`, `dynamic_risk_heatmap.py` | `VALIDATED` | Prototype operational thresholds pending SDMA calibration |
| **Early Warning Protocol** | Multi-channel standardized alerts| ITU-T CAP v1.2 XML/JSON + simulated SMS ($\le 160$ chars) | `NER_SAFE_DATA/COMPONENT_12/`, `cap_alerts.json` | `VALIDATED` | Live telecom SMS requires national SMS gateway access |
| **GIS Hazard Mapping** | Interactive Web GIS | Dual-Mode 2D Leaflet + 3D CesiumJS 1.119+ real SRTM terrain globe, clamped roads & buildings, search, inspector | `ner_safe_live_dashboard.html`, `test_phase4a_3d_terrain.py` | `VALIDATED` / `OPERATIONAL` | Road network based on OSM vector baseline |
| **Roads & Lifelines** | Infrastructure exposure | 45,315 road segments (NH-06, NH-54); 4-state connectivity | `NER_SAFE_DATA/EXPOSURE/roads/` | `VALIDATED` | Real road closure requires verified ground observation |
| **Settlements & Buildings** | Consequence analysis | 976 settlements, 296,690 building footprints intersected | `NER_SAFE_DATA/EXPOSURE/buildings/` | `VALIDATED` | Building footprints mapped primarily in municipal zones |
| **Demographic Exposure** | Population impact estimates | Census 2011 demographics across 22 districts (4,568,123 citizens), 2D choropleth (`/api/gis/population`), strict 0.00 risk weight | `NER_SAFE_DATA/EXPOSURE/population/`, `gis_service.py` | `VALIDATED` | District-level census downscaled by building distribution |
| **Citizen Ground Reports** | Mobile crowdsourced reports | Responsive HTML5 web app, offline queue, 50m clustering | `ner_safe_citizen_app.html`, `database.py` | `VALIDATED` | Field verification desk requires designated officers |
| **Geotagged Media** | Media upload with integrity | SHA-256 digests, EXIF metadata, Laplacian blur analysis | `media_integrity_analyzer.py` | `IMPLEMENTED` | Deep learning vision forensics hardware-constrained on i3 |
| **Multilingual Alerts** | Native language warnings | Certified emergency templates in English, Hindi, Khasi, Mizo | `NER_SAFE_DATA/COMPONENT_12/` | `VALIDATED` | Remaining 4 NER state languages planned for Phase 2 |
| **Low Connectivity / Offline**| Resilient edge operation | 4-tier network state machine; Level 4 Zero Network mode | `network_state_manager.py` | `IMPLEMENTED` | Level 4 physical siren requires hardware relay |
| **Automated Data Ingestion** | Cadence scheduling daemon | Autonomous multi-source polling scheduler with dedup | `live_monitoring_scheduler.py` | `AUTO_UPDATE_VERIFIED` | Subject to host system power/network uptime |
| **Disaster Prioritization** | Incident triage ranking | Consequence ranking sorting highest exposed lifeline first | `step3_intersect_exposure_and_prioritize.py` | `VALIDATED` | Automated guidance for human incident commanders |
| **Weather APIs (IMD)** | National weather integration | 21 endpoints mapped, dual-header auth tested, live nowcast | `imd_api_client.py` | `PENDING_ACCESS` (`IMD_AUTH_REQUIRED`) | Official gridded station API requires institutional MoU |
| **Scalable Cloud Backend** | Production deployment | SQLite relational backend, 4 vCPU 16GB server architecture | `database.py`, `server.py` | `PENDING_ACCESS` (Server Provisioning) | College server VM allocation awaiting provisioning |

---

## 25. System Architecture Diagram

```
+--------------------------------------------------------------------------------------------------+
| NER-SAFE OPERATIONAL SYSTEM ARCHITECTURE                                                         |
+--------------------------------------------------------------------------------------------------+

  DATA SOURCES
  |
  +-- SATELLITE EO: NASA GPM IMERG NRT (Rainfall) + NASA SMAP (Soil Moisture)
  +-- SATELLITE RADAR: Sentinel-1 GRD (Backscatter) + Sentinel-1 SLC (InSAR Track 150)
  +-- SATELLITE OPTICAL: Sentinel-2 MSI L2A (10m NDVI, NDWI, NDMI with SCL Mask)
  +-- STATIC TERRAIN: USGS SRTM 1 Arc-Second DEM (Elevation, Slope, Aspect, Curvature, TWI)
  +-- GROUND TRUTH: 260 Georeferenced Landslide Events (NASA GLC, GSI Bhukosh, Bhuvan)
  +-- EXPOSURE: geoBoundaries, Survey of India, OSM (45k Roads, 296k Buildings, 976 Places)
  +-- EXTERNAL FEEDS: GSI Bhusanket WebAPI, NDMA SACHET CAP, ISRO Bhuvan WMS
  +-- METEOROLOGY: IMD Mausam Live Nowcasts (GeoJSON) [Station API: AUTH_REQUIRED]
  +-- OPEN INTELLIGENCE: OSINT Regional NLP Crawler + OSIRIS Platform (USGS M2.5+, GDACS)
  +-- INSTITUTIONAL SENSORS: NIT Meghalaya Mawiongrim [INSTITUTIONAL_ACCESS_REQUIRED]
  |
  v
  INGESTION & PROVENANCE LAYER (`live_monitoring_scheduler.py`, `observation_provenance.py`)
  |-- Autonomous Cadence Polling (Half-hourly GPM, Daily SMAP, 12-day S1 InSAR)
  |-- Cryptographic SHA-256 Integrity Verification & Observation Timestamp Decoupling
  |-- Source Freshness Tracking (`FRESH`, `RECENT`, `DATA_STALE`, `WAITING_FOR_DATA`)
  |
  v
  FEATURE GENERATION & HARMONIZATION (Component 9 Master Grid, 30m EPSG:4326)
  |-- 10-Feature Vector: elevation, slope, aspect_sin, aspect_cos, curvature, twi,
  |                      ndvi_imputed, ndwi_imputed, ndmi_imputed, sentinel_observed_flag
  |
  v
  AI SUSCEPTIBILITY INFERENCE LAYER
  |-- PRIMARY PRODUCTION: Calibrated XGBoost (`calibrated_xgboost_model.joblib`)
  |-- AUTOMATIC FALLBACK: Calibrated Random Forest (Non-silent fault recovery)
  |-- PARALLEL SHADOW   : PyTorch Spatial 2D CNN (Corridor patch research)
  |
  v
  LOCKED FOUR-FACTOR RISK FUSION ENGINE (`fusion_engine.py`)
  |-- Equation: 0.40 Susceptibility + 0.30 Rainfall + 0.20 Soil Moisture + 0.10 Satellite Change
  |-- Threat Tiers: Critical (>=0.65), High (0.48-0.65), Moderate (0.32-0.48), Watch (<0.32)
  |-- Strict Rule: Zero external sources modify risk formula or add weights
  |
  v
  CONSEQUENCE & RUNOUT MODELING (Component 11)
  |-- D8 Steepest Downhill Descent Routing on 30m DEM (Zero uphill steps)
  |-- Fahrböschung Reach Angle (<10°) + Lateral Runout Corridors (48 Hotspots)
  |-- STRtree Spatial Intersection with 62 Exposed Infrastructure Assets (NH-06, NH-54)
  |
  v
  DECISION SUPPORT & EXTERNAL INTELLIGENCE INTEGRATION
  |-- GSI Bhusanket Concordance Benchmark (6/9 Full, 3/9 Partial Matches)
  |-- NDMA SACHET CAP Overlay & OSIRIS Seismic/Disaster Context
  |-- OSINT Multi-Scale Validation (Site <=2km, Corridor <=5km, Regional <=45km)
  |
  v
  ALERT & DISSEMINATION ENGINE (Component 12)
  |-- ITU-T CAP v1.2 XML/JSON + Simulated SMS (<=160 chars) + DEOC Webhooks
  |-- Certified Multilingual Payloads: English, Hindi, Khasi, Mizo
  |-- Hysteresis Safeguards & 4-Hour Fatigue Deduplication
  |
  v
  FIELD & USER INTERFACES
  |-- UNIFIED OPERATIONS PORTAL (`ner_safe_live_dashboard.html`): OSM GIS, Search, Inspectors
  |-- CITIZEN REPORTING APP (`ner_safe_citizen_app.html`): Offline Queue, 50m Dedup, PIP
  |-- ZERO-NETWORK LEVEL 4 MODE: Disclaims SMS, Cached Risk, Software Siren Trigger
```

---

## 26. Transparent System Limitations

In strict adherence to scientific truth in advertising, the following limitations are explicitly documented:

1. **Absence of Co-Temporal Sensor Failure Labels**: Historical landslide inventories record dates of discovery, not sensor-coincident hour-of-failure. True machine learning temporal event prediction cannot be validated without continuous high-frequency slope failure telemetry.
2. **Spatial Partitions & Modest ROC-AUC**: Under rigorous geographic block cross-validation (holding out entire mountain regions), the production model achieves a spatial ROC-AUC of 0.5603. While PR-AUC (0.3608) and Brier calibration (0.1984) demonstrate operational value, the model is a probabilistic vulnerability index, not an infallible oracle.
3. **Severe Vegetative Radar Decorrelation**: Tropical monsoonal rainforests in Meghalaya and Mizoram cause **93.43% coherence loss ($\gamma < 0.35$)** in C-band Sentinel-1 interferograms. Single-pair InSAR measurements are restricted to rock quarries, urban clusters, and bare scarps.
4. **Atmospheric Phase Delay in InSAR**: Extreme moisture gradients across the Meghalaya escarpment introduce $5\text{ to }15\text{ cm}$ of apparent LOS phase delay. Current InSAR products represent **relative LOS observations**, not calibrated ground deformation.
5. **InSAR Stack Size**: Current repeat-pass archives on Track 150 contain 2–3 scenes, which is insufficient for multi-temporal Persistent Scatterer Interferometry (PSI requires 15–20+ scenes).
6. **Coarse Resolution of Satellite Hydrology**: NASA GPM (~10 km) and SMAP (~9 km) observe regional atmospheric and soil moisture regimes; they cannot resolve localized ditch blockages or sub-meter road drainage saturation.
7. **Optical Cloud Invalidation**: Monsoon cloud cover frequently obscures Sentinel-2 optical bands, forcing median imputation and reliance on static topography and radar backscatter.
8. **Institutional Access Prerequisites**: Production integration of IMD automatic weather stations, NIT Meghalaya Mawiongrim live telemetry, and MIRSAC SILAAS streams remains blocked pending administrative MoUs.
9. **College Server Provisioning Status**: Deployment on the dedicated 4 vCPU / 16 GB RAM institutional server VM is awaiting administrative network provisioning.
10. **State Data Disparities**: Operational validation is established for Phase 1 (Meghalaya and Mizoram). High-risk states such as Nagaland have severely limited historical records, requiring extensive field survey before operational rollout.

---

## 27. Phased Development Roadmap

```
+--------------------------------------------------------------------------------------------------+
| PHASE A: CURRENT VALIDATED BASELINE (COMPLETED)                                                 |
| - Complete EO data architecture (SRTM DEM, GPM rainfall, SMAP soil moisture, S2 optical)       |
| - Calibrated XGBoost production model with automated Random Forest fallback & Shadow CNN         |
| - Locked 4-factor risk fusion & D8 flow-path/runout consequence engine across 48 hotspots        |
| - Operations dashboard with OSM Standard default basemap, autocomplete search, and runout inspect|
| - Citizen reporting app with offline storage, 50m clustering, and media integrity analysis       |
| - External intelligence integrations (GSI Bhusanket, NDMA SACHET, ISRO Bhuvan, OSINT, OSIRIS)   |
| - Corrected Sentinel-1 InSAR single-pair processing with bedrock reference anchor                |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PHASE B: OPERATIONALIZATION & SERVER DEPLOYMENT (IMMEDIATE NEXT STEPS)                           |
| - Provision institutional Ubuntu Server VM (4 vCPU, 16 GB RAM, 100 GB storage)                  |
| - Secure non-root SSH project access and configure systemd daemons for server & scheduler        |
| - Execute administrative MoUs for official IMD station REST API credentials                      |
| - Establish university data agreements for live telemetry streaming (NIT Meghalaya Mawiongrim)   |
| - Connect physical 12V siren relay hardware to edge gateway GPIO for Level 4 zero-network mode   |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PHASE C: SCIENTIFIC EXPANSION & MULTI-TEMPORAL MONITORING                                        |
| - Ingest expanding 2026 post-monsoon verified landslide inventories from GSI                     |
| - Build multi-year Sentinel-1 SLC archive (15+ acquisitions on Track 150) for PSI time-series    |
| - Implement advanced atmospheric delay mitigation using ERA5 reanalysis or GACOS troposphere grids|
| - Deploy hardware-accelerated deep learning vision forensics for citizen media                   |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PHASE D: REGIONAL EXPANSION ACROSS REMAINING 6 NER STATES                                        |
| - Phase 2A: Mosaicing, exposure extraction, and hotspot setup for Assam, Sikkim, and Tripura     |
| - Phase 2B: Targeted remote sensing and inventory building for Arunachal Pradesh, Manipur,       |
|             and Nagaland (resolving the documented Nagaland research gap)                        |
| - Integration with State Emergency Operation Centers (SEOC) under Disaster Management Act 2005   |
+--------------------------------------------------------------------------------------------------+
```
