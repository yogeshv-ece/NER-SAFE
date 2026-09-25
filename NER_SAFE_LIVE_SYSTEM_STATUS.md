# NER-SAFE: COMPREHENSIVE LIVE SYSTEM STATUS

**Document Purpose**: Authoritative Status of All Environmental Observation Sources, Dynamic Trigger Pipelines, AI Models, and Operational Boundaries  
**Project**: NER-SAFE (SIH 26001)  
**Date**: September 2026  
**Operational Standard**: Zero-Simulation Policy — Exact Operational Classifications  

---

## 1. MULTI-SOURCE & MODEL OPERATIONAL CLASSIFICATION TABLE

| Observation / Model Source | Category / Sensor | Signal Speed | Data Provider | Current Classification | Provenance & Evidence | Technical / Operational Limitation |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **NASA GPM IMERG NRT** | Satellite Precipitation | **FAST** | NASA GES DISC / CMR | **LIVE-OPERATIONAL** | Automated CMR discovery + authenticated HDF5 streaming via `~/.netrc` (Granule `20260913-S123000`). | $\sim 10\text{ km}$ spatial resolution; nominal latency $4\text{–}6\text{ hours}$. Satellite proxy, not slope gauge. |
| **NASA SMAP L3 Enhanced** | Radiometer Soil Moisture | **SLOW** | NASA NSIDC DAAC / CMR | **LIVE-READY / BANDWIDTH RESTRICTED** | CMR discovery active (Granule `20260912`); CloudFront auth verified (HTTP 200). | Global HDF5 array is **683.2 MB**; full download per 30m cycle is bandwidth-prohibitive on laptop. Ingested on 24h daily cycle. |
| **Copernicus Sentinel-1 SAR** | C-Band SAR Radar (GRD) | **MEDIUM** | ESA / Copernicus CDSE | **LIVE-READY / AUTH_REQUIRED** | OData scene discovery active; all-weather surface change engine implemented. | Automated binary download requires user-configured `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`. Backscatter amplitude change only. |
| **Sentinel-1 InSAR Deformation** | Repeat-Pass IW SLC InSAR | **MEDIUM** | ESA / Copernicus CDSE | **AUTH_REQUIRED / WAITING_FOR_COMPATIBLE_PAIR** | 10-step processing pipeline (`insar_processing.py`) and pair selector (`insar_pair_selector.py`) implemented; coherence masking ($\gamma \ge 0.35$); Shillong bedrock reference ($25.572^\circ\text{ N}, 91.881^\circ\text{ E}$). | Requires CDSE credentials; local laptop 8 GB RAM requires burst subsetting. Zero SLC data currently in workspace; zero fabricated deformation arrays. |
| **Copernicus Sentinel-2** | MSI Optical Multispectral | **SLOW** | Element84 STAC / CDSE | **LIVE-READY** | STAC discovery and automated cloud-screening engine operational. | Frequent monsoon cloud occlusion ($>80\%$). Cloud occlusion strictly never interpreted as low landslide risk. |
| **Production Susceptibility Model** | Calibrated Random Forest | **STATIC ANCHOR** | Component 10 Frozen Engine | **PRODUCTION FROZEN** | PR-AUC = 0.3151, ROC-AUC = 0.5654, Brier = 0.2035. Anchors operational four-factor fusion at 40% weight. | 101/101 SHA-256 release artifacts locked. Retained as production baseline. |
| **Recommended Next Tabular Model** | XGBoost Gradient Boosting | **ANALYTICAL** | Component 10 Extension | **RECOMMENDED NEXT MODEL** | PR-AUC = 0.3608, ROC-AUC = 0.5603, Brier = 0.1984 (+14.5% PR improvement). | Recommended next candidate; zero silent promotion; requires technical committee sign-off before production swap. |
| **PyTorch Spatial CNN** | Deep Learning Conv2D | **EXPERIMENTAL** | PyTorch 2.14.0+cpu Engine | **EXPERIMENTAL CANDIDATE** | $32 \times 32$ spatial context patches (8 bands), 5-fold geographic cross-validation (PR-AUC 0.3087, ROC-AUC 0.5487, Brier 0.1870). Generated `cnn_susceptibility_probability.tif` (1.48 GB). | Spatial susceptibility pattern learning only; strictly does NOT forecast failure time. Production model remains frozen RF. |
| **Dynamic GIS Risk Heatmaps** | Real-Time GIS Heatmap Engine | **FAST** | `dynamic_risk_heatmap.py` | **LIVE-OPERATIONAL** | 11 distinct GIS layers served via `/api/heatmap/*` and visualized on `#liveMap`. Zero-stale rule: returns `NOT_AVAILABLE` when live assessment absent. | Renders data-driven GeoJSON points and corridors; no decorative blurs. |
| **Meghalaya Ground Sensors** | Rain, Piezometer, Inclinometers, Suction | **FAST** | NIT Meghalaya (Mawiongrim) | **SOFTWARE READY / INSTITUTIONAL ACCESS REQUIRED** | 696 continuous hourly field records ingested (`mawiongrim_telemetry.csv`); adapter schema validated. | Field hardware communicates over closed cellular WSN link to NIT Meghalaya internal lab. Live streaming requires institutional MoU. |
| **Mizoram Ground Sensors** | Borehole Tilt, Extensometers, Rain | **FAST / MEDIUM** | MIRSAC / SILAAS (Aizawl) | **SOFTWARE READY / INSTITUTIONAL ACCESS REQUIRED** | SILAAS municipal hazard bulletins and GIS shapefiles cataloged. | Raw geotechnical sensors are maintained on Mizoram State Government intranet. Live machine-to-machine streaming requires SDMA MoU. |
| **IMD Automatic Weather** | Surface Weather Stations | **FAST** | India Meteorological Department | **LIVE-READY / INSTITUTIONAL ACCESS REQUIRED** | Weather provider framework implemented (`weather_provider.py`). | Real-time AWS machine-to-machine REST streaming requires formal Ministry of Earth Sciences (MoES) agreement. |
| **Local Reference Node** | Soil Moisture, Tilt, Rain | **FAST** | Local Edge Gateway (ESP32) | **FIRMWARE CREATED / HARDWARE VALIDATION REQUIRED** | Reference C++ firmware (`esp32_reference_gateway.ino`) and host adapter implemented. | User preference is to consume existing NER field sensors rather than DIY ESP32 deployment. Unflashed unless hardware connected. |
| **Temporal Event Forecasting** | Time-to-Failure Prediction | **ANALYTICAL** | C15 Engine | **NOT YET SCIENTIFICALLY VALIDATED** | Temporal label validator audited historical inventory (0% temporal overlap) and Mawiongrim (no collapse labels). | Exact time-to-failure forecasting strictly disclaimed until time-aligned failure datasets become scientifically available. |

---

## 2. OPERATIONAL STATE MACHINE STATUS

The NER-SAFE runtime operates under the authoritative state machine:

```
[STARTING]
    ↓
[MONITORING] ←──────────────────────┐
    ↓                               │
[NEW_OBSERVATION DETECTED]          │
    ↓                               │
[PROCESSING & INTEGRITY CHECK]      │
    ↓                               │
[DYNAMIC FEATURE UPDATE]            │
    ↓                               │
[ASSESSMENT_UPDATED] (ASM-LIVE-...) │
    ↓                               │
[HEATMAP_REGENERATED] (/api/...)    │
    ↓                               │
[WAITING_FOR_DATA] (Cadence Sleep) ─┘
```

* **Current Active System State**: `MONITORING / CURRENT_ASSESSMENT_ACTIVE`
* **Active Assessment ID**: `ASM-LIVE-20260913174122-49fc8aaa`
* **Triggering Granule**: `GPM_3IMERGHHE.07:3B-HHR-E.MS.MRG.3IMERG.20260913-S123000-E125959.0750.V07C.HDF5`
* **Observation Time**: `2026-09-13T12:30:00.000Z`
* **Ingested Time**: `2026-09-13T17:41:22.652Z`
* **Maximum Regional Risk Score**: `0.5636` (HIGH)
* **Risk Tier Distribution**: 48 Hotspots evaluated (0 Critical, 48 High, 0 Moderate, 0 Watch)
* **Mode Isolation**: 100% Isolated. Deterministic demo replay (`EVT-MEG-001`, `0.7055`) remains strictly separated.
