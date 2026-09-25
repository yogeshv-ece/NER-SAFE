# NER-SAFE: JUDGE DEMONSTRATION RELEASE BASELINE MANIFEST

**Release Name**: NER-SAFE Judge Demonstration Release Baseline  
**Release Identifier**: `nersafe-judge-demo-baseline-1.0`  
**Release Version**: `1.0.0-judge-demo-freeze`  
**Release Date**: 2026-09-13  
**Freeze Status**: **FROZEN WITH WARNINGS**  
**Working Directory**: `E:\landslide - Copy\landslide - Copy`  

> [!IMPORTANT]
> **FREEZE VERDICT**: **FROZEN WITH WARNINGS**  
> Core scientific models, four-factor fusion, D8 flow-path routing, empirical runout corridors, infrastructure consequence intersections, CAP advisories, mode separation, and zero-emoji dashboard are 100% frozen and verified. Documented warnings address external authenticated satellite downloads (CDSE/Earthdata), pending institutional MoU for IMD weather, air-gapped basemap tile rendering, and unreachable legacy HTML artifacts.

---

## 1. REPOSITORY & ENVIRONMENT SNAPSHOT

### Repository State
* **Git Repository**: No (Non-git standalone project directory)
* **Git Branch**: `None`
* **Git Commit**: `None`
* **Working-Tree Status**: `BASELINE SNAPSHOT — NON-GIT WORKSPACE (Directory contains uncommitted/untracked development files; not initialized as git repo per preservation instructions)`

### Runtime Environment
* **Operating System**: `Windows-11-10.0.26200-SP0` (AMD64)
* **Python Executable**: `C:\Users\hp\AppData\Local\Python\pythoncore-3.14-64\python.exe`
* **Python Version**: `3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]`

### Installed Dependency Snapshot

| Package | Installed Version | Role in NER-SAFE Baseline |
| :--- | :--- | :--- |
| `pip` | `25.2` | Package Installer for Python |
| `numpy` | `2.5.2` | Core Numerical & Tensor Computations |
| `scipy` | `1.18.1` | Scientific Algorithms & Statistical Routines |
| `scikit-learn` | `1.9.0` | Calibrated Random Forest Susceptibility & Spatial CV |
| `h5py` | `3.16.0` | NASA SMAP L3 HDF5 Ingestion & Slicing |
| `xgboost` | `3.4.1` | Component 15 Comparative Gradient Boosting Engine |
| `rasterio` | `1.5.1` | GeoTIFF GDAL Raster I/O & Geospatial Reprojection |
| `shapely` | `2.1.2` | Planar Vector Geometries & Buffer Intersections |
| `requests` | `2.34.2` | HTTP Client for NASA CMR & ESA Copernicus STAC |
| `cryptography` | `50.0.1` | PBKDF2-HMAC-SHA256 Password Hashing & Token Crypto |

---

## 2. SERVER & USER INTERFACE BASELINE

* **Server Script**: `server.py` (Python standard library `http.server.ThreadingHTTPServer`)
* **Startup Command (Shell)**: `py server.py`
* **Startup Command (PowerShell)**: `& "C:\Users\hp\AppData\Local\Python\bin\python.exe" server.py`
* **Default Port**: `8000`
* **Browser Access URL**: [http://localhost:8000](http://localhost:8000)
* **Live Dashboard**: `ner_safe_live_dashboard.html`
* **UX4G Zero-Emoji Compliance**: **100% PASS** (0 emojis detected in active dashboard markup)

### Unreachable Legacy Interfaces
The following legacy HTML files are cataloged as historical C12/C13 deliverables and are **NOT** reachable in the active judge demonstration workflow:
* `ner_safe_citizen_app.html`
* `ner_safe_early_warning_dashboard.html`

---

## 3. SCIENTIFIC CONFIGURATION & FUSION FORMULATION

### Component 10 Landslide Susceptibility Model
* **Algorithm**: `RandomForestClassifier with Platt Sigmoid Probability Calibration`
* **Framework**: `scikit-learn 1.9.0`
* **Hyperparameters**: `n_estimators=150, max_depth=8, min_samples_leaf=3, class_weight='balanced', random_state=42`
* **Spatial Validation**: `5-Fold Spatial Block Cross-Validation (Meghalaya & Mizoram blocks)`
* **Out-of-Fold (OOF) Spatial Validation Metrics**:
  * **spatial_roc_auc**: `0.5654`
  * **spatial_pr_auc**: `0.3151`
  * **brier_score_calibrated**: `0.2035`
  * **spatial_f1**: `0.3265`
  * **spatial_recall**: `0.3462`
  * **spatial_precision**: `0.309`

### Four-Factor Operational Risk Fusion Formulation
$$\text{Risk} = 0.40 \times \text{Susceptibility} + 0.30 \times \text{Rainfall Anomaly} + 0.20 \times \text{Soil Moisture Anomaly} + 0.10 \times \text{Satellite Change Flag}$$

| Factor | Weight | Source Sensor / Baseline | Operational Freshness Window |
| :--- | :---: | :--- | :--- |
| **Susceptibility Baseline** | `0.40` | C10 Calibrated Random Forest (30m SRTM) | Static Geomorphic Baseline |
| **Rainfall Anomaly** | `0.30` | NASA GPM IMERG V07 / IMD AWS | Nominal <6h; Stale >12h |
| **Soil Moisture Anomaly** | `0.20` | NASA SMAP L3 Enhanced (9km) | Nominal <24h; Stale >48h |
| **Satellite Surface Change** | `0.10` | Sentinel-2 Optical / Sentinel-1 C-SAR | Nominal <5d; Stale >12d |

### Operational Categorical Thresholds

| Risk Tier | Fused Score Range | Operational Meaning & Protocol |
| :--- | :---: | :--- |
| **CRITICAL** | `score >= 0.65` | Immediate automated D8 flow-path routing, runout envelope, and civil defense CAP bulletin |
| **HIGH** | `0.48 <= score < 0.65` | Qualifying runout envelope calculation and heightened lifeline infrastructure watch |
| **MODERATE** | `0.32 <= score < 0.48` | Advisory watch; multi-source observation tracking |
| **WATCH** | `score < 0.32` | Baseline environmental monitoring; regular polling |

> [!NOTE]
> **Threshold Nature**: Prototype / Heuristic Operational Thresholds (Subject to future empirical calibration with state disaster management authorities)

### Core Scientific Safeguards & Separation Rules
1. **C10 Dynamic Trigger Separation**: The C10 internal empirical dynamic trigger (Combined_Risk = Susceptibility * (0.25 + 0.75 * Dynamic_Trigger)) remains an offline raster derivation strictly separate from the live four-factor operational fusion.
2. **Consequence vs. ML Separation**: Exposure infrastructure (roads, buildings, settlements, population) represents consequence analysis and is strictly isolated from ML feature vectors.
3. **SAR Scientific Scope**: Strictly NO InSAR displacement measurement; backscatter amplitude change only.
4. **Hydraulic Flow Paths & Runout**: D8 steepest descent routing based on SRTM 30m DEM indicates predicted primary hydraulic drainage descent, and alpha-angle geometric envelopes define empirical runout corridors; strictly not guaranteed exact future landslide trajectories or failure moments.

---

## 4. DETERMINISTIC JUDGE DEMO BASELINE (EVT-MEG-001)

* **Hotspot Identifier**: `EVT-MEG-001`
* **Settlement**: `Shella`
* **District & State**: `East Khasi Hills, Meghalaya`
* **Coordinates**: `25.1837°N, 91.6421°E`
* **Historical Observation Timestamp**: `2024-05-28T06:00:00Z`

### Mathematical Deterministic Reconciliation
```
Factor 1: 0.40 * 0.6869 (Susceptibility)  = 0.27476
Factor 2: 0.30 * 0.9217 (Rainfall Anom)  = 0.27651
Factor 3: 0.20 * 0.7714 (Soil Moisture)  = 0.15428
Factor 4: 0.10 * 0.0000 (Sat Change)     = 0.00000
-------------------------------------------------
Fused Risk Score:                        = 0.70555 -> 0.7055 (CRITICAL)
```

### Downstream Consequence Outputs
* **D8 Steepest Descent Flow Path Length**: `267.4 m`
* **Elevation Drop**: `73.0 m`
* **Empirical Runout Corridor Area**: `29264.6 m²`
* **Exposed Road Assets**: `2 segments`
* **Exposed Road Length**: `208.4 m`
* **CAP Advisory Context**: `DEMO / LOCAL TEST`
* **CAP Delivery Safeguard**: `Local demonstration test advisory; strictly zero public SMS / SACHET broadcast transmission`
* **Citizen Ground Observation Evidence**: `REP-20260912-MEG-014 / REP-20260913-MEG-002` (Synthetic demonstration report cataloged as supporting qualitative ground observation)
* **Model Retraining Isolation**: `model_retraining_triggered == False` (Strict isolation)

---

## 5. OPERATIONAL FRESHNESS & ANTI-REPLAY SAFEGUARDS

When qualifying fresh observations are unavailable, operational assessment strictly returns assessment_mode='OPERATIONAL', assessment_status='NOT_AVAILABLE', current_risk_available=false, and reason='No qualifying fresh observations'.

```json
{
  "assessment_mode": "OPERATIONAL",
  "assessment_status": "NOT_AVAILABLE",
  "current_risk_available": false,
  "reason": "No qualifying fresh observations"
}
```

### Hard Invariant Safeguards
* Historical risk scores never masquerade as current risk.
* Demo replay outputs never contaminate operational endpoints.
* Missing observations never convert to low risk (0.0).
* Feeds in DATA_STALE state never convert to FRESH.

---

## 6. VERIFICATION TEST SUITES & RECONCILIATION

### Test Classification & Metrics

| Metric Layer | Suite Count | Total Checks | Results | Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Historical Validation Baseline** | 9 | 328 | **328 / 328 PASS (100%)** | Historical validation recorded September 12, 2026 |
| **Current Complete Reproduction** | 9 | 328 | **325 / 328 PASS (99.1%)** | 3 time-dependent checks failed as designed due to elapsed age |
| **Judge Demo Reproducibility Suite** | 1 | 53 | **53 / 53 PASS (100%)** | Clean-start, deterministic EVT-MEG-001 replay, and mode isolation |

### Suite-by-Suite Breakdown

| Suite Name | Test File | Checks | Historical Baseline | Current Rerun |
| :--- | :--- | :---: | :---: | :---: |
| **E2E Demo Workflow Suite** | `test_end_to_end_demo_workflow.py` | 44 | 44/44 PASS | 44/44 PASS |
| **Observation Integrity & Audit Suite** | `test_observation_integrity_audit.py` | 35 | 35/35 PASS | 35/35 PASS |
| **Real Observation Ingestion Suite** | `test_real_observation_ingestion_suite.py` | 23 | 23/23 PASS | 23/23 PASS |
| **C15 Temporal Forecasting Suite** | `test_c15_temporal_forecasting_suite.py` | 40 | 40/40 PASS | 40/40 PASS |
| **Authentication & RBAC Suite** | `test_authentication.py` | 38 | 38/38 PASS | 38/38 PASS |
| **Live System REST & Fusion Suite** | `test_live_system.py` | 21 | 21/21 PASS | 21/21 PASS |
| **Evolution & State Machine Suite** | `test_live_monitoring_evolution.py` | 22 | 22/22 PASS | 22/22 PASS |
| **Live Satellite Provenance Suite** | `test_live_satellite_provenance.py` | 41 | 41/41 PASS | 41/41 PASS |
| **End-to-End Runout Workflow Suite** | `test_e2e_live_monitoring_workflow.py` | 64 | 64/64 PASS | 61/64 PASS (3 elapsed freshness/STAC checks) |
| **Judge Demonstration Reproducibility Suite** | `test_judge_demo_reproducibility.py` | 53 | N/A (New baseline suite) | 53/53 PASS |

---

## 7. DOCUMENTED LIMITATIONS: WARNINGS & BLOCKED ITEMS

### Warnings
* **[WARN-01] Air-Gapped Basemap Tiles**: Online slippy tiles (OpenStreetMap / CartoDB Positron) require internet access. In air-gapped mode, vector flow paths, runout corridors, infrastructure intersections, and hotspot markers render accurately over a neutral cartographic grid.
* **[WARN-02] Legacy HTML Emoji Content**: ner_safe_citizen_app.html (5 emojis) and ner_safe_early_warning_dashboard.html (3 emojis) contain legacy Unicode characters. Both files are completely unreachable in the active judge demonstration workflow and are preserved as historical C12/C13 deliverables. Active dashboard ner_safe_live_dashboard.html has exactly ZERO emojis.

### Blocked External Dependencies
* **[BLOCKED-01] Sentinel-1 CDSE Radar SAFE Binary Download**: Copernicus Data Space Ecosystem (CDSE) unauthenticated OData API enables automated catalog scene discovery and metadata verification. Downloading full-resolution GRD binary archives requires user-configured OAuth2 credentials (CDSE_CLIENT_ID / CDSE_CLIENT_SECRET). System uses pre-staged local GRD rasters when offline.
* **[BLOCKED-02] NASA Earthdata Full Array Streaming**: NASA CMR enables unauthenticated metadata queries. Direct download/streaming of HDF5 GPM/SMAP arrays requires Earthdata Login (.netrc credentials). Pre-staged regional HDF5/GeoTIFF archives provide local offline execution.
* **[BLOCKED-03] IMD Live AWS Network Feeds**: Real-time telemetry from India Meteorological Department automatic weather stations requires an official institutional MoU / MoES data sharing agreement. Synthetic endpoints rejected; provider honestly reports AWAITING_INSTITUTIONAL_MOU.

---

## 8. EXCLUDED MUTABLE RUNTIME ITEMS

The following items represent environment-specific, dynamic, or secret data and are **strictly excluded** from the immutable release baseline:
* .env, .env.example (Environment variables and secrets)
* credentials.json, credentials.json.json, token.json (User / provider authentication keys)
* NER_SAFE_DATA/DATABASE/ner_safe_shared.db (SQLite dynamic user sessions and mutable report state)
* __pycache__/ (Bytecode caches)
* NER-SAFE/predictions/ (Runtime test snapshot output directories)
* Temporary files, browser session caches, and machine-specific directories

---

## 9. PROTECTED ARTIFACT INTEGRITY REGISTRY (101 FILES)

Total Protected Files: **101** | Total Protected Footprint: **2,372,908,958 bytes** (~2.37 GB)

### 1. Core Demonstration & Operational Modules (7 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `e2e_demo_engine.py` | `21,582` | `8d990d5e532601cfd391bfa1bbd3dc267eacf67dc1fa7862df97fd5a8b9c4787` | Core 10-stage end-to-end demonstration and operational separation engine |
| `server.py` | `64,257` | `6d34ee87ff23a636f06ed6ae06c5f92d714040ceb48c0b38204088e9ad681ca5` | Multi-threaded REST API server with RBAC authentication and mode separation |
| `ner_safe_live_dashboard.html` | `218,245` | `0dad344e6f642676380601aac143cb95917c19d7f05a59b0e1a642006ac91647` | Digital India UX4G 3.0 live monitoring and demonstration dashboard (Zero-Emoji) |
| `NER_SAFE_END_TO_END_DEMO.md` | `19,672` | `d4f7b5ee0a8f205ecf7ef607b97cfeffc1f5c74dec829d1441c82fdfd71d9004` | End-to-end demonstration protocol and architectural specification |
| `NER_SAFE_FINAL_DEMO_READINESS_AUDIT.md` | `17,529` | `754bb5d13eaa502bac7a1ea4583340010326180996241374d1a347a75f73a82c` | Final demo readiness and baseline reconciliation audit report |
| `test_end_to_end_demo_workflow.py` | `13,131` | `d7e657b585d92315aea53db2562fb040f714c8a5b5150d713b73f00b5246cdd8` | End-to-end demonstration workflow automated test suite (44 checks) |
| `test_judge_demo_reproducibility.py` | `14,763` | `9b94c8a4316c7af06a9ac84ba30d3f4b138fbbc763748f8d6fdf5628aea40228` | Judge demonstration reproducibility & mode separation suite (53 checks) |

### 2. Live Observation & Ingestion Modules (14 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `live_ingestion.py` | `28,529` | `42fba50588915223c5c9a91fc7c4ceb290cc8aabfa441ffff6601ebd9ad6bdbf` | Multi-source decoupled live ingestion and freshness classification engine |
| `weather_provider.py` | `7,940` | `f4765a246e2f51bc75902a96bf52b9867cef24b7d77cca4a3c7f270842ac9d6c` | Multi-source precipitation provider (NASA GPM IMERG and IMD AWS) |
| `sentinel1_sar_engine.py` | `10,684` | `ab15879eb77dcaf8cda869fdb91b9f8e614fd11c1977174a407b6a486df0539e` | Sentinel-1 C-band SAR backscatter radar engine (surface change only; no InSAR) |
| `observation_provenance.py` | `11,520` | `50e3b4f9bdab942a029b50b1b88d13dc296720550549a64f9c2d04a2b01a8680` | Observation provenance registry with cryptographic SHA-256 envelopes |
| `demo_orchestrator.py` | `11,596` | `5a7618eb5d4762ffb90f23f4ce4a3e647ffa0fe65a7253717403f2e4a2718c0b` | Operational state machine controlling LIVE, REPLAY, and DEMO modes |
| `storage_engine.py` | `11,558` | `b7ad40d6810c5ac63d2f37e2d8db0fa412c891509abf22f2cffcc00e969b791f` | Local-first storage engine with truthful cloud sync reporting |
| `public_demo_gateway.py` | `7,062` | `14f1378401ebc70f94aefe3ce29c21d3369b6d9c4f4d04a3de332848d2a8d43e` | Public demonstration gateway with asset protection and firewall rules |
| `local_ingestion_worker.py` | `8,056` | `e0c57e88690e0225f2ceb7c347314ebd74037e4b02e1dd9b2df0e596823c3646` | Local autonomous observation ingestion worker |
| `test_observation_integrity_audit.py` | `13,852` | `934ae273fed80c1089c4ee183dc1cf4654dbaccfff118bb2c7cbce40c0870149` | Observation integrity and scientific audit test suite (35 checks) |
| `test_real_observation_ingestion_suite.py` | `14,063` | `2b8c88037d1c4f3319e31440f85172eeff5bb195ad214b83b0961770c55573b1` | Real observation ingestion & sensor audit test suite (23 checks) |
| `test_live_satellite_provenance.py` | `12,225` | `3bb151194d078ccade2e7d967211af866970c38ba53766dde32149481504b9ac` | Live satellite provenance and data integrity suite (41 checks) |
| `test_live_monitoring_evolution.py` | `17,117` | `15a9e33bf019cf23f3fbcf8d06cc329970ffd7a2eafa7954088ca826f61d0331` | Live monitoring evolution and demonstrator state suite (22 checks) |
| `test_live_system.py` | `17,736` | `fcdc758f9468704daf79a56946918e858b8e4aee710f2370d93a0039b3eb3ae1` | Live multi-source system integration test suite (21 checks) |
| `test_e2e_live_monitoring_workflow.py` | `15,888` | `1642b43591a5ade8875f8c5e6543a05c80b3a2412de109659653fae2730962eb` | End-to-end runout and live monitoring workflow suite (64 checks) |

### 3. Scientific Models, Risk Fusion & Forecasting Logic (23 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `fusion_engine.py` | `20,779` | `eb3df16de10838b4726b768c80e73b13b62c75e308bd04882f136a25ccc00b8c` | Four-factor operational risk fusion calculation module (40/30/20/10) |
| `step1_extract_samples.py` | `17,081` | `d8f30b841f10f73cad44043e40374206efbab3ede2eae3e57efd5315b4d9f512` | Component 10 training sample extraction module |
| `step1_extract_initiation_candidates.py` | `9,442` | `3ed3b68d11e6b03ea63097d88dc56042f17cb1150b300766fbc65cbb5aa6bcb4` | Component 11 initiation candidate extraction module |
| `step2_train_and_validate_models.py` | `17,787` | `0ecc60457a4bca2a4917aa87a5c5d7062f15cd9f8c37554ec33077390a6c8376` | Component 10 Random Forest training and spatial cross-validation module |
| `generate_component10_rasters.py` | `15,465` | `9fb18aa6527faab51d353f9c41cb695c2042ca8f32730af1d0a9bdac5b5afec7` | Component 10 full-resolution GeoTIFF raster generator |
| `step4_leakage_and_quality_audit.py` | `25,422` | `68b6140c9a71014e414b5127485efdb6948c6ccce1717b66e780783714dd2000` | Component 10 spatial leakage and quality audit script |
| `step2_trace_flow_paths_and_corridors.py` | `12,993` | `172bf69baec6d89610ff72d7b8189b372611e123a9d31e444150b0ad94e60a9b` | Component 11 D8 flow-path routing and alpha-angle corridor tracer |
| `step3_intersect_exposure_and_prioritize.py` | `19,141` | `f5d3c712af50a2536f8c190be553409119833049d75619763816b5f32abc9162` | Component 11 infrastructure exposure intersection and prioritization |
| `step1_generate_cap_alerts.py` | `16,353` | `761ce83ab3f9e414c60decd8ddffa246e20398e4cb3eefbfef3487b78a85e1f0` | Component 12 Common Alerting Protocol (ITU-T CAP v1.2) alert generator |
| `step2_generate_sdma_bulletins.py` | `14,902` | `fcc14f18a56b79e0b17dfe8a78ec21c949e8633c9a4b8e435f417136da5931ab` | Component 12 SDMA situation report and bulletin generator |
| `step3_simulate_notification_dispatch.py` | `7,666` | `44eee7c7f4dadc636347c21035d617bb64d95953a7b11248b6fece7973e16802` | Component 12 notification dispatch and delivery state simulator |
| `step1_build_citizen_report_schema.py` | `22,262` | `a21b47b5d39dd95b9f38ea1415c57d97836c7205265cc1fe6cbc9d65dace8a09` | Component 13 citizen report schema generator and validator |
| `step2_simulate_offline_sync_and_clustering.py` | `18,204` | `3e884337d622644c4d9e1d05462342a77951000bcf4db9f3914d0fc13847a1fe` | Component 13 store-and-forward sync and spatial clustering engine |
| `step4_validate_component13.py` | `29,774` | `7a578c39d09449b13ec4e27857732d6874783fa184ec4f73c2f8156f97309276` | Component 13 citizen observation end-to-end validation module |
| `c15_forecasting_engine.py` | `9,200` | `a4ab8f14c27b503d191e973a47e7c88b0e0ff89616c43e7d1c3f30e3fd765a98` | Component 15 temporal forecasting engine with Shannon entropy uncertainty |
| `c15_model_comparator.py` | `9,897` | `541df02e0ade3d25844a095f30890e52e5a6a8f1c0f7bb8b0ebddfd92981c7ec` | Component 15 comparative evaluation framework (RF vs XGBoost) |
| `temporal_feature_engine.py` | `10,842` | `bc5fd01a97a6ba6451382fb0333b29c84f46d51255bbd250e829a585f648623b` | Multi-window temporal feature extraction engine (1h, 3h, 6h, 24h) |
| `temporal_label_validator.py` | `4,947` | `14c64c17a6ac8ed9eeaa84449290e9151bbddaae92cd07ede90044f4149523e8` | Temporal label feasibility and co-temporal mismatch validator |
| `temporal_replay_engine.py` | `2,649` | `a7cd472d8cacb24363b0fdb1494635b60153c603c72b49108fc2a0006f98bf42` | Time-series replay engine with historical timeline scrub |
| `alert_safeguard_engine.py` | `7,042` | `9ecee96ff69345e350639cb726fc8216e60182eb02fec6d2d6a7e4caea6a0ce6` | Operational alert safeguards, false-alarm hysteresis, and deduplication |
| `network_state_manager.py` | `7,311` | `655215670ca52ca53a180737fffeb043d39a56851c095c737809cc6b7dcffd0b` | Store-and-forward offline network state manager |
| `test_c15_temporal_forecasting_suite.py` | `18,049` | `c1955ef4d93587ed7e3cc8ce3b39346cbf4717c9183971c6356596e57e34bba6` | Component 15 pre-landslide temporal forecasting suite (40 gates) |
| `spatial_cross_ref.py` | `5,881` | `09087fba2a963b195d6db491e607d4cb8573d7c1c531176c7eb39fd9b5ea4589` | Spatial cross-referencing and reverse geocoding engine |

### 4. Scientific Metadata & Spatial Grid Configurations (11 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `model_metadata.json` | `3,385` | `e46e581153b852ed033ec33c637734caf1055e56d2b9294ae09954d75e08a994` | Component 10 Random Forest hyperparameters, spatial blocks, and OOF metrics |
| `spatial_grid_metadata.json` | `1,606` | `58cc1ba3091bef4e1e6d27b8d9f57779a5bfe4ad9167bb037aa229cfd826d0dd` | Master 30m WGS84 spatial grid bounding coordinates and grid dimensions |
| `temporal_alignment_metadata.json` | `4,533` | `5ad481254f5732dbfa7405edcc5a6296829037251c1e7ddc0fab3c3b3f2b95c3` | Multi-source temporal alignment configuration and timestamp resolution |
| `inventory_metadata.json` | `869` | `098dd30fa7cb1f491b9d0924db7d1aa4e76e016d26693d1047c56772fdaba4e7` | Landslide inventory metadata, source citations, and spatial distribution |
| `sentinel2_audit_summary.json` | `17,958` | `4746f863e7038775653fb35fc104168454606475d2da2a0452dfc4a4762f5e12` | Sentinel-2 optical archive audit, scene cloud coverage, and band registry |
| `feature_importance.csv` | `453` | `bbdceeb6d2f46262a9f02a7a564e668acd2ef97092c248873ffe3cab9e44b577` | Component 10 permutation feature importance rankings |
| `feature_manifest.csv` | `2,142` | `84d3287fed441a15883de94bb73452cca40383f78f3595234f0a9e53b6b58c0c` | Complete spatial feature manifest and normalization parameters |
| `MASTER_GRID_manifest.csv` | `25,727` | `795f9ebc8e5a2884b5d4b60e3dbee7bb3672a1cdb270637b269b848d353582d7` | Master spatial grid alignment and CRS registration manifest |
| `training_samples.csv` | `233,800` | `bdd3bcfe109b77a02e19353a82abd58f4192573a624dfc9414cc60e888483816` | Validated training samples (832 rows: 208 landslides, 624 pseudo-absences) |
| `validation_results.csv` | `1,438` | `84acb40300afa16548f753c7ed1fa5fee63aa433f40516253003544791b67f44` | Out-of-fold spatial cross-validation fold-by-fold results |
| `model_comparison.csv` | `673` | `77e57be1b6f0e215c0b3d3c3a286e8bb7a5051399b955b687ab4f9ba5c19eb16` | Comparative model evaluation metrics across algorithms |

### 5. Validated Scientific Raster, Vector & Alert Outputs (20 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `susceptibility_probability.tif` | `719,215,384` | `8676b624e75709c84882cb5384d2af840449c45e7f9592278d73de9224b56516` | Validated C10 calibrated landslide susceptibility probability raster (30m) |
| `susceptibility_class.tif` | `24,854,064` | `b0e9800b12de7785a55231e776ccbf73a998219d71fff98509541a7ddc638ca4` | Validated C10 susceptibility classification raster (5 tiers) |
| `uncertainty.tif` | `699,159,453` | `e6297bd814381194ee3ab2dbd24e9df4c8ccd22b7739aeaf0fe36f282c286551` | Validated C10 prediction uncertainty raster (Shannon entropy) |
| `dynamic_trigger_index.tif` | `185,034,065` | `ddc15932cad6f8666420d532e2b4b7e7c74f2e977975f6d229e26ef3211d5199` | Validated dynamic meteorological-hydrological trigger index raster |
| `combined_risk_score.tif` | `722,171,385` | `a153c258e0b5a33ea2f2494fbe442f3182027c680a38a7d0b0fe7803d2b6ffbc` | Validated combined hazard risk score raster |
| `risk_class.tif` | `19,199,628` | `3c75f33a077525de0c4f3e1f2e17ebb78193dd9084ead5d8d873563803c63632` | Validated categorical risk tier raster |
| `event_records.csv` | `13,009` | `f93d61668b9ddeae01b03796754aa423d6b7c220130ba994f70c2c198f0a24fe` | Component 11 primary monitored hotspot records (48 hotspots, 13009 bytes invariant) |
| `event_records.geojson` | `77,538` | `1614c504ef1d6009e0b21a4af96accffbb7965e8a3a713917928c30830814d8d` | Component 11 monitored hotspot point features GeoJSON |
| `flow_paths.geojson` | `84,522` | `0bd2637cb4c0cbac3825dd4d56fa4abc5547d060c52c8c2577a70a4658455a35` | Component 11 D8 steepest-descent predicted drainage flow paths GeoJSON |
| `runout_corridors.geojson` | `1,062,284` | `51b8fa6a0c263270be6d4c8514d18539d6b3c23b8789ed6dc589e70bca6c868e` | Component 11 empirical runout corridors polygon footprint GeoJSON |
| `exposure_intersections.geojson` | `48,930` | `4ed8d3060ab511c69c8a3bec713a92f823cd5bc1e69ef5f79a089c493d65207f` | Component 11 intersected infrastructure consequence assets GeoJSON |
| `initiation_points.geojson` | `50,983` | `b90b691c2e219709fc7dad4b9be351268dc4399566dcf884641e612b3b51097a` | Component 11 high-susceptibility initiation seed points GeoJSON |
| `impact_summary.csv` | `606` | `7ef16cafc47188710c38f1850d59caf061dd02aa3440cf3ae8521dae21a99d42` | Component 11 summary of exposed road segments and infrastructure consequence |
| `cap_alerts.json` | `197,671` | `c0a9d6a62dd40ff9b2f14b58c9a725b966ba4037c7c274cd139d156539d47037` | Component 12 Common Alerting Protocol (CAP v1.2) alert feed JSON |
| `cap_alerts.xml` | `201,448` | `3946e9d64c29bbe0e92af68a6222a031e189cdc335d54ce64e9b82e3a0f91368` | Component 12 ITU-T CAP v1.2 alert feed XML document |
| `dispatch_records.csv` | `15,808` | `32a2480325a3b7b441a908557fa96a13b2ff06c652bd532ba7f7a24327660c85` | Component 12 simulated multi-channel notification dispatch records |
| `dispatch_summary.json` | `984` | `5a642a363dfe79dd972eb5be4de23c46b9ee50110854984dc5bad8dafee795e9` | Component 12 dispatch summary statistics and channel breakdown |
| `Lifeline_Corridor_Advisories.md` | `3,998` | `0f3443b2c258a4c76feddc2e38b814e10003576d9704ec2ff82e8afce3743605` | Component 12 lifeline highway corridor civil defense advisories |
| `SDMA_Meghalaya_Situation_Report.md` | `4,199` | `129a5b329b93624559e624066b6e662e597e3410d824f3cf6a8cc8ed5a1c22f7` | Component 12 Meghalaya State Disaster Management Authority situation report |
| `SDMA_Mizoram_Situation_Report.md` | `3,846` | `e73e48e07edca97bde6993b1ed3249ba66f82543c6f0351153e9aa4739a9a860` | Component 12 Mizoram State Disaster Management Authority situation report |

### 6. Cryptographic Authentication & Security Modules (4 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `auth_security.py` | `4,807` | `2f0bb6273b98b851fa7be8ed582b8829a6af9cfa6a31332955681392e51ed62d` | Cryptographic authentication module (PBKDF2-HMAC-SHA256, session management, RBAC) |
| `database.py` | `34,008` | `c41e932470d1d2ec000a4985cb59e9a4c102ddc4575d0a4c0a54d647ba31bcd0` | SQLite database persistence module for users, sessions, roles, and audit logs |
| `bootstrap_admin.py` | `3,581` | `e0f57c14bb8f0453a91d2c29c1d2a033080d211e9b311f4bb99f6b31209486a4` | Deterministic administrative bootstrap and seed script |
| `test_authentication.py` | `29,187` | `b6ff76f5228d1e7eb0e05b8ad5e89c7c0c65fbfd7abb6c34ac8ad2485cb0d1e6` | Authentication, session isolation, and RBAC verification test suite (38 checks) |

### 7. Baseline Documentation, PRDs & Audit Reports (18 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `PRD_NER_SAFE.md` | `21,061` | `290795b0b04d014b07583ae544d87ccbd318b1639fb6da7e68277d451cdacb2f` | Product Requirements Document for NER-SAFE |
| `PRD_NER_SAFE_COMPLETED_WORK.md` | `58,981` | `cef2ed06c5eaaf207e65a1890db7319d36fad0dbc571d01d9b58b129ea23fb74` | Comprehensive record of completed scientific and operational deliverables |
| `NER_SAFE_REAL_OBSERVATION_INTEGRITY_AUDIT.md` | `23,651` | `fa9470b5948fb2e1872c150189f742aeea4f29ec6f12c9e5d2097f514c2c122b` | Audit report on real observation retrieval, CDSE, IMD, and four-factor fusion |
| `NER_SAFE_REAL_INGESTION_AUDIT.md` | `19,145` | `4a7aa4896c2b367d5b0ad972b8fef9731c12b457f9d462423db00aebf8b64723` | Audit report on live sensor ingestion, GPM, SMAP, and Sentinel feeds |
| `NER_SAFE_CHECKPOINT.md` | `16,470` | `279580aeae875ffb8c68fcc1bfbe33267f65f9fc182fff81f848dac4f7635a1a` | System technical checkpoint and architecture summary |
| `NER_SAFE_COMPONENT13_VALIDATION_REPORT.md` | `4,241` | `256e8e52b34efdd1095cd2a3654688a0688360cf12fbd650b1a8537363be5df8` | Component 13 citizen science and ground observation validation report |
| `COMPONENT_15_VALIDATION_REPORT.md` | `10,577` | `57c1a4a4b60bfb70f13ac7459f5f0408c83dae1ae40db8e8085543d4ca023a56` | Component 15 pre-landslide temporal forecasting validation report |
| `component11_report.md` | `3,963` | `846daa7e1961f291109ef4d34499bb0c39499fb3a0c09de049dc664402583936` | Component 11 flow-path and runout modelling methodology report |
| `component11_validation_report.md` | `5,532` | `fd84cd42e244d1595b8aa5721104652f2b11553a131d679261d3b9f43dd4e29f` | Component 11 consequence intersection validation report |
| `component12_validation_report.md` | `6,264` | `6f8924f15a53aa72b70cd1d4a642814b8f47cf301cdad492e90d77fd5593ff7c` | Component 12 CAP alert generation and notification validation report |
| `COMPONENT_10_VALIDATION_REPORT.txt` | `4,396` | `39357bcb1f78333119a51fc854d3c7d68c5e5d7665d2c5fdce709702e981e22d` | Component 10 susceptibility model training and spatial CV audit report |
| `COMPONENT_10_MODEL_READINESS_REPORT.txt` | `3,362` | `40ead19e82d50faf93254fa314ae1d9d8828b6af894a0c4d2d64ee7ae9d17498` | Component 10 model readiness and hyperparameter configuration audit |
| `MODEL_SELECTION_REPORT.txt` | `2,918` | `b06c6d3990e998a616ea00a66c888a98fa7a5479dbe3184980d010a15cdaf816` | Machine learning algorithm selection and comparative evaluation report |
| `LEAKAGE_AUDIT.txt` | `3,055` | `8ea32142e52f72e75e6a779ff311e1a31c686bb5d491a05b25561f3b618bea86` | Spatial block cross-validation leakage audit report |
| `MASTER_GRID_validation_report.txt` | `3,905` | `cf9cb7a51aa480b097e9f9ddc6ec612f1bfefefe97adc10f87c429228c78e660` | Master 30m geographic grid validation report |
| `model_card.md` | `3,647` | `604d4db5d2c60e309bc79a0a64073bc1919a3121db5ab23e980e14b90f776db1` | Model card documenting intended use, limitations, metrics, and ethical scope |
| `alert_protocol_methodology.md` | `4,261` | `a8c8d4940e5fba6f506839e279f47c97648ecbadd79c40f6aba4cd493bb1ed6d` | Operational alert protocol and notification delivery methodology |
| `flow_path_methodology.md` | `4,699` | `c92ddfc86f7e80cfa6680a2469b664eab8e00c91762f512a4a263587d7fe7c83` | D8 drainage flow-path routing and empirical runout methodology |

### 8. Reproducibility Fixtures & Schemas (4 files)

| Relative File Path | Size (Bytes) | SHA-256 Checksum | Description |
| :--- | :---: | :--- | :--- |
| `NER_SAFE_DATA/COMPONENT_13/data/synthetic_demonstration_reports.json` | `29,424` | `e3adb9c1544eb5a163c0e9470d3b989430bfc9bfdc8354ea86ca77b9ba652f1b` | Deterministic synthetic demonstration citizen reports fixture |
| `NER_SAFE_DATA/COMPONENT_13/schema/citizen_report_schema.json` | `6,382` | `662a7287c1f9a48832fbb900303f35eda0fa100c1cb7112b342e0619dbc54145` | JSON schema definition for qualitative citizen observations |
| `NER_SAFE_DATA/COMPONENT_13/data/citizen_reports.csv` | `4,707` | `0b1000e5e3a4de26e94a6ae29d4545610d6071c047e92f9c868a8ef91da55769` | Tabular export of demonstration citizen ground reports |
| `NER_SAFE_DATA/COMPONENT_13/data/citizen_reports.geojson` | `24,251` | `309013ab8750d4e27dbe7178e157242c7f92ecd2f7a77db6274c4696c61cf178` | GeoJSON export of demonstration citizen ground reports |

---

## 10. EXACT REPRODUCTION COMMANDS

```powershell
# Set active working directory
cd "E:\landslide - Copy\landslide - Copy"

# 1. Verify Judge Demo Reproducibility Suite (53/53 checks)
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_judge_demo_reproducibility.py

# 2. Verify End-to-End Demo Workflow Suite (44/44 checks)
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_end_to_end_demo_workflow.py

# 3. Launch Authenticated Multi-Source Monitoring Server
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" server.py

# 4. Open Live Dashboard in Browser
# URL: http://localhost:8000
```

---

## 11. FINAL RELEASE DECLARATION

**RELEASE IDENTIFIER**: `nersafe-judge-demo-baseline-1.0`  
**STATUS**: **FROZEN WITH WARNINGS**  
All protected source code, scientific models, calibrated rasters, vector flow paths, empirical runout corridors, CAP alerts, authentication subsystems, and zero-emoji dashboard interfaces are frozen and certified for controlled judge demonstration.
