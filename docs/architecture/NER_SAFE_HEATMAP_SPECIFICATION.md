# NER-SAFE — Dynamic GIS Heatmap Architecture & Specification
**Module**: Component 11 / GIS Heatmap & Multi-Model Visualization Subsystem  
**Implementation**: `dynamic_risk_heatmap.py`  
**API Endpoints**: `/api/heatmap/layers`, `/api/heatmap/current`, `/api/heatmap/cnn`, `/api/heatmap/insar`  
**Dashboard Integration**: `ner_safe_live_dashboard.html` (`#liveMap`, Leaflet 1.9.4)  
**Date**: September 2026  

---

## 1. Architectural Philosophy: Data-Driven GIS vs. Decorative Gradients
NER-SAFE strictly rejects static decorative color gradients or synthetic Gaussian blurs. Every visualization layer on the dashboard is **100% data-driven**, generated directly from verified geospatial observations, empirical runout corridors, or mathematical model outputs.

### The Zero-Stale / Non-Fabrication Rule
- The **Current Operational Risk Heatmap** is derived exclusively from the latest qualifying live assessment (`ASM-LIVE-*`).
- If no fresh live assessment is available in `NER_SAFE_DATA/LIVE_ASSESSMENTS/current_assessment.json`, the API returns:
  ```json
  {
    "layer_id": "current_operational_risk",
    "status": "NOT_AVAILABLE",
    "current_risk_available": false,
    "reason": "No qualifying fresh operational assessment active."
  }
  ```
- **Historical Replay Isolation**: Historical demo assessments are explicitly tagged `HISTORICAL` and cannot masquerade as current operational risk.
- **Experimental Tagging**: Experimental models are explicitly labeled `EXPERIMENTAL CNN` and `EXPERIMENTAL XGBOOST`.

---

## 2. Supported 11 GIS Risk Layers

| Index | Layer ID | Category | Status | Native Resolution | Description |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `current_operational_risk` | OPERATIONAL_FUSION | ACTIVE_LIVE | Dynamic Point / Grid | Real-time four-factor fusion score derived from latest active assessment. |
| **2** | `rf_susceptibility` | MODEL_PRODUCTION | FROZEN_BASELINE | 30m USGS SRTM grid | Calibrated Random Forest baseline initiation probability (40% fusion anchor). |
| **3** | `xgboost_susceptibility` | MODEL_EXPERIMENTAL | EXPERIMENTAL_TABULAR| 30m grid extractions | XGBoost gradient boosted trees experimental probability (PR-AUC 0.3608). |
| **4** | `cnn_susceptibility` | MODEL_EXPERIMENTAL | EXPERIMENTAL_DL | $32 \times 32$ spatial patches | PyTorch Spatial CNN experimental probability surface (Brier 0.1870). |
| **5** | `rainfall_trigger` | OBSERVATION_TRIGGER | LIVE_OPERATIONAL | 0.1° (~10km) GPM IMERG | 24h/72h cumulative precipitation anomaly relative to regional thresholds. |
| **6** | `soil_moisture` | OBSERVATION_CONTEXT | LIVE_READY_24H | ~9km Enhanced SMAP grid | Antecedent volumetric soil moisture saturation field. |
| **7** | `sar_change` | OBSERVATION_SAR | LIVE_READY | 20m Sentinel-1 IW GRD | Calibrated radar backscatter coefficient amplitude disturbance flag. |
| **8** | `insar_deformation` | OBSERVATION_INSAR | AUTH_REQUIRED | Repeat-pass IW SLC | Differential phase unwrapped relative LOS crustal deformation ($\gamma \ge 0.35$). |
| **9** | `exposure_infrastructure`| CONSEQUENCE_EXPOSURE| AUTHENTIC_BASELINE | Vector Footprints | Critical buildings, settlements, and populations in runout zones. |
| **10**| `road_vulnerability` | CONSEQUENCE_EXPOSURE| AUTHENTIC_BASELINE | OSM Highway Vectors | Lifeline transport corridors (NH-06, NH-54) subject to flow severance. |
| **11**| `regional_hotspots` | OPERATIONAL_GRID | ACTIVE_MONITORING | 48 Discrete Coordinates | Monitored slope sites across Meghalaya (28 sites) and Mizoram (20 sites). |

---

## 3. Resolution Honesty Standards
The system maintains strict transparency regarding observation versus presentation scale:
- **Precipitation**: NASA GPM IMERG native grid is **0.1° (~10 km)**. The dashboard displays the discrete grid cell anomaly and does **NOT** falsely claim 30m micro-topographic rainfall measurements.
- **Soil Moisture**: NASA SMAP native radiometer grid is **~9 km**. It is represented as a regional saturation context layer, not localized slope pore pressure.
- **Topography & Susceptibility**: SRTM native elevation and geomorphic derivatives are **30 meters** (1-arcsecond).
- **Radar InSAR**: Repeat-pass Sentinel-1 C-SAR interferometry provides **millimeter-scale relative Line-of-Sight deformation**, but is restricted to areas with coherence $\gamma \ge 0.35$. Low coherence is masked as `NO_DATA` and never interpreted as zero movement.

---

## 4. Automatic Live Update Pipeline
When a genuine new observation arrives (e.g. fresh NASA GPM IMERG HDF5 granule):
```text
NASA GPM NRT Ingestion
         ↓
HDF5 SHA-256 Checksum & QC Validation
         ↓
Freshness Timestamp Verification (< 36 hours)
         ↓
Precipitation Feature Grid Update
         ↓
Four-Factor Risk Fusion Engine (ASM-LIVE Reassessment)
         ↓
SQLite DB Transaction (`live_assessments` table)
         ↓
Update `NER_SAFE_DATA/LIVE_ASSESSMENTS/current_assessment.json`
         ↓
Dynamic Heatmap Engine (`dynamic_risk_heatmap.py`)
         ↓
Fast Incremental GeoJSON Serialization
         ↓
Live Dashboard Auto-Refresh (`GET /api/heatmap/current`)
         ↓
Hotspot Inspector & Visual Alert Tiers Dynamically Synchronized
```

---

## 5. Hotspot Inspector Data Schema
Clicking any hotspot on `#liveMap` triggers an integrated multi-source query displaying:
- **Assessment Metadata**: Assessment ID (`ASM-LIVE-*`), generation timestamp, evaluation mode (`OPERATIONAL`).
- **Operational Risk**: Fused risk score $\in [0.0, 1.0]$, risk class (`CRITICAL`, `HIGH`, `MODERATE`, `WATCH`), runout eligibility flag.
- **Observation Evidence**:
  - Susceptibility Baseline: $0.40$ weight.
  - NASA GPM Rainfall Anomaly: $0.30$ weight.
  - SMAP Soil Moisture Anomaly: $0.20$ weight.
  - Sentinel-1 SAR Surface Change: $0.10$ weight.
- **Radar InSAR Evidence**:
  - Relative LOS Displacement: `AUTH_REQUIRED (Waiting for local SLC pair)`.
  - Interferometric Coherence: `MASKED (< 0.35 threshold)`.
- **AI Multi-Model Susceptibility Comparison**:
  - Production Calibrated Random Forest: e.g. `0.6540` (PR-AUC 0.3151).
  - Recommended Next XGBoost: e.g. `0.6571` (PR-AUC 0.3608).
  - Experimental PyTorch CNN: e.g. `0.6667` (PR-AUC 0.3087, Brier 0.1870).
- **Consequence & Infrastructure**:
  - Intersected road names (NH-06, NH-54, SH-12).
  - Exposed road length (meters).
  - Buildings exposed, nearest settlement, and administrative district.
  - D8 flow path reach angle $\alpha$ (Fahrböschung) and elevation drop $\Delta Z$.
