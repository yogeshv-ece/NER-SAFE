# NER-SAFE — FORENSIC AUDIT OF SMAP SOIL MOISTURE SUBSYSTEM
**Audit Date**: 2026-09-17  
**Project**: AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India (NER-SAFE)  
**Version**: v1.2.x  
**Working Directory**: `E:\landslide - Copy\landslide - Copy`  
**Audit Type**: Read-Only Pre-Implementation Forensic Audit  

---

## 1. EXECUTIVE AUDIT SUMMARY

This forensic audit evaluates the current state of NASA SMAP (Soil Moisture Active Passive) data handling, storage, quality control, anomaly derivation, and risk pipeline integration across the NER-SAFE codebase.

### Key Audit Findings
1. **Historical Baseline Preserved & Intact**:
   - The historical archive in `NER_SAFE_DATA/SMAP/raw/` contains 181 files covering 180 valid dates from 2024-11-01 through 2025-04-30 (plus one file on 2025-05-01).
   - The documented missing date **2025-03-18** (NASA payload safe hold outage) is strictly absent and preserved as NaN in all derived baseline rasters (`smap_outage_flag_native9km.tif`). Zero fabrication or synthetic interpolation was performed.
2. **Current Product in Use**:
   - The historical baseline uses **SPL3SMP_E.006** (SMAP L3 Radiometer Global Daily 9 km EASE-Grid Soil Moisture).
   - Format: HDF5 (.h5).
   - Grid: EASE-Grid 2.0 (`EPSG:6933`), native resolution 9008.055 m.
   - Primary Variable: `Soil_Moisture_Retrieval_Data_AM/soil_moisture` and PM `soil_moisture_pm`.
3. **Critical Gap in Existing "Live" Ingestion**:
   - In `live_ingestion.py` (lines 305–351), `fetch_latest_smap()` queried the NASA CMR REST API for `SPL3SMP_E` metadata, but **did NOT download the HDF5 raster**, and instead substituted a hardcoded heuristic `feature_value = 0.58` (monsoon) or `0.30` (dry season).
   - In `live_assessment_service.py` (lines 314–317), SMAP input was set to a static contextual placeholder `0.58` labeled `VALID_CONTEXTUAL_BASELINE`.
   - The system is therefore **NOT LIVE_VERIFIED** for SMAP. Real live operationalization requires authentic NRT HDF5 acquisition, AOI extraction, quality filtering, and anomaly computation.
4. **NASA Earthdata Authentication Operational**:
   - Active, valid credentials for `urs.earthdata.nasa.gov` exist in `C:\Users\hp\.netrc`.
   - `earthaccess` (v0.19.0) authentication strategy `netrc` was verified live and connected cleanly to NASA NSIDC Cumulus Cloud archive.
5. **Target Product SPL2SMP_NRT Verified Live**:
   - Product: `SPL2SMP_NRT` (Version 107), "Near Real-time SMAP L2 Radiometer Half-Orbit 36 km EASE-Grid Soil Moisture".
   - NASA CMR search for NER AOI (21.0°N–27.0°N, 89.0°E–94.0°E) successfully discovered real fresh half-orbit granules (e.g., `SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_002.h5` observed on 2026-09-17T00:36:27Z with file size ~1.60 MB).
   - A real test granule was acquired and parsed: group `Soil_Moisture_Retrieval_Data` contains 1D swath arrays of `soil_moisture`, `latitude`, `longitude`, `retrieval_qual_flag`, and `surface_flag`. 67 AOI cells were extracted with genuine volumetric soil moisture values (0.095 to 0.503 cm³/cm³).
6. **2026 NASA SMAP Geolocation Issue Inspected**:
   - NASA documented a geolocation error affecting observations between 14 May 2026 and 28 July 2026.
   - The live operational validation observations targeted in this upgrade are from **September 2026**, strictly **post-28-July-2026**, completely free of the documented geolocation issue.

---

## 2. INVENTORY OF SMAP SCRIPTS, PIPELINES, & ARTIFACTS

| Component | File / Path | Role / Content | Audit Status |
| :--- | :--- | :--- | :--- |
| **Audit Script** | `audit_smap.py` | Inspects `NER_SAFE_DATA/SMAP/raw`, counts cells, checks valid ranges | Read-only audit script |
| **Validation Script** | `smap_validator.py` | Validates historical archive against `SMAP_manifest.csv` | Validated historical files |
| **Historical Processing** | `process_smap_soil_moisture.py` | Composites AM/PM 9 km EASE-Grid, computes mean/min/max/std, reprojects to 30m grid | Authoritative baseline generator |
| **Harmony Pipeline** | `smap_production_pipeline.py` | Batch download pipeline using NASA Harmony OGC Coverages API | Historical download tool |
| **Daily Downloader** | `smap_daily_downloader.py` | Scans raw H5 files, validates headers, writes manifest | Reusable utility functions |
| **Auth Test Scripts** | `smap_auth_test.py`, `smap_fix_auth.py`, `smap_setup_netrc.py` | Earthdata credentials verification | Verified auth operational |
| **Live Ingestion** | `live_ingestion.py` | IngestionManager querying CMR for GPM, SMAP, Sentinel-2 | Gaps identified: heuristic 0.58 score |
| **Live Assessment** | `live_assessment_service.py` | Operational risk reassessment engine (0.40/0.30/0.20/0.10) | Uses static 0.58 SMAP placeholder |
| **Scheduler** | `live_monitoring_scheduler.py` | Event-driven polling engine | Polling loop exists; needs NRT binary pipeline |
| **Registry** | `sensor_source_registry.py` | Source metadata for `NASA_SMAP_L3_01` | Listed as `LIVE_READY`; update to `LIVE_VERIFIED` upon test |
| **Server Extension** | `live_sensor_server_extension.py` | REST API routes for live telemetry, sources, assessments | Ready for `/api/smap/latest` extension |
| **Dashboard** | `ner_safe_live_dashboard.html` | UX4G UI with SMAP card (`valSmapGranule`, `valSmapAge`, etc.) | Card present, ready for live stats |
| **Historical Raw Data** | `NER_SAFE_DATA/SMAP/raw/` | 181 `.h5` files (180 dates + 2025-05-01) | Protected historical record |
| **Derived 9km Rasters** | `NER_SAFE_DATA/MASTER_GRID/temporal/smap_native_9km/` | `smap_soil_moisture_mean_native9km.tif`, min, max, std, outage | Authoritative historical climatology |
| **Derived 30m Rasters** | `NER_SAFE_DATA/MASTER_GRID/aligned_features/hydrology/` | Reprojected 30m representations (EPSG:4326) | Spatially aligned modeling layers |
| **Database** | `NER_SAFE_DATA/DATABASE/ner_safe_shared.db` | SQLite `observations`, `live_assessments` | Parameterized schema ready for SMAP NRT |

---

## 3. TECHNICAL SPECIFICATIONS: HISTORICAL BASELINE VS. NRT TARGET

| Specification | Historical SMAP Baseline | Live Operational Target (SPL2SMP_NRT) |
| :--- | :--- | :--- |
| **NASA Short Name** | `SPL3SMP_E` | `SPL2SMP_NRT` |
| **Version** | `006` | `107` |
| **Processing Level** | Level 3 (Global Daily Composite) | Level 2 (Half-Orbit Swath) |
| **Spatial Resolution** | 9 km (Enhanced Backus-Gilbert) | 36 km (Standard Radiometer Grid) |
| **Grid & Projection** | EASE-Grid 2.0 (`EPSG:6933`) | EASE-Grid 2.0 (`EPSG:6933`) |
| **Format** | HDF5 (`.h5`) | HDF5 (`.h5`) |
| **Primary Variable** | `Soil_Moisture_Retrieval_Data_AM/soil_moisture` | `Soil_Moisture_Retrieval_Data/soil_moisture` |
| **Units** | $\text{cm}^3/\text{cm}^3$ | $\text{cm}^3/\text{cm}^3$ |
| **Valid Range** | $0.02 \text{ to } 0.50 \text{ (fill } -9999.0\text{)}$ | $0.02 \text{ to } 0.50 \text{ (fill } -9999.0\text{)}$ |
| **Quality Flags** | `retrieval_qual_flag` | `retrieval_qual_flag` (bit 0 = recommended) |
| **Surface Flags** | `surface_flag` | `surface_flag` (bits 5-8 = snow/ice/frost) |
| **Temporal Frequency** | Daily composite | Half-orbit passes (~1-2 passes/day over AOI) |
| **Latency** | Historical archive (days/months) | Near-real-time (<3 hours after observation) |
| **Purpose** | Climatological baseline & variability | Immediate dynamic saturation anomaly |

---

## 4. CURRENT RISKS, GAPS, & DEFICIENCIES IDENTIFIED

1. **Heuristic Substitution in Live Ingestion**:
   `live_ingestion.py` was returning a hardcoded `soil_saturation_score = 0.58` (if monsoon) without downloading or processing the observation array.
2. **Product Resolution Mismatch**:
   Historical baseline is on a 9 km grid, while SPL2SMP_NRT is a 36 km swath grid. Simply treating them as identical without explicit harmonization is scientifically invalid.
3. **Missing Database Persistence for SMAP Observations**:
   While `live_assessments` recorded a `soil_moisture_score`, there was no granular record storing the raw NRT granule filename, SHA-256 hash, valid cell counts, AOI statistics, and retrieval latency.
4. **Scheduler Automation Status**:
   `live_monitoring_scheduler.py` has a polling method for SMAP, but because `fetch_latest_smap()` did not ingest real data, the scheduler never acquired actual files.
5. **No Dedicated Test Suite for SMAP NRT**:
   Existing tests (`test_smap_download.py`) only checked `SPL3SMP_E`. No unit or integration tests existed for `SPL2SMP_NRT` swath extraction, bitwise quality filtering, and resolution harmonization.

---

## 5. RESOLUTION HARMONIZATION & OPERATIONAL ANOMALY DESIGN

### Spatial Harmonization Strategy
- Both products natively share **EASE-Grid 2.0 (EPSG:6933)**.
- 36 km EASE-Grid 2.0 cell dimensions ($36032.22\text{ m}$) are an exact $4 \times 4$ multiple of the 9 km EASE-Grid 2.0 cells ($9008.055\text{ m}$).
- Harmonization Method:
  1. Extract all 36 km NRT cells intersecting the NER AOI ($21.0^\circ\text{N} \le \text{lat} \le 27.0^\circ\text{N}$, $89.0^\circ\text{E} \le \text{lon} \le 94.0^\circ\text{E}$).
  2. For each valid NRT cell, sample the co-located historical baseline parameters (mean, min, max, std) from `smap_soil_moisture_mean_native9km.tif`, `smap_soil_moisture_min_native9km.tif`, and `smap_soil_moisture_max_native9km.tif`.
  3. Compute the relative saturation anomaly per cell and aggregate across the AOI:
     $$\text{Saturation Index} = \frac{\text{SM}_{\text{obs}} - \text{SM}_{\text{min, baseline}}}{\text{SM}_{\text{max, baseline}} - \text{SM}_{\text{min, baseline}}}$$
     $$\text{Standardized Anomaly } (Z) = \frac{\text{SM}_{\text{obs}} - \text{SM}_{\text{mean, baseline}}}{\text{SM}_{\text{std, baseline}}}$$
  4. Bounded operational soil moisture anomaly for the 4-factor risk engine:
     $$\text{soil\_moisture\_anomaly} = \text{clip}\left(\text{Saturation Index}, 0.0, 1.0\right)$$
  5. Preserve scientific honesty: clearly document in metadata that the 36 km NRT observation provides regional contextual saturation and does not represent fine-scale 30 m physical measurements.

---

## 6. QUALITY CONTROL & FILTERING RULES

From inspection of the official `SPL2SMP_NRT` Version 107 metadata:
- **Variable**: `Soil_Moisture_Retrieval_Data/soil_moisture`
- **Fill Value**: `-9999.0`
- **Physical Valid Bounds**: $0.02 \le \text{SM} \le 0.50\text{ cm}^3/\text{cm}^3$
- **Bitwise Quality Flag (`retrieval_qual_flag`)**:
  - Bit 0 (mask `0x0001`): `0 = Recommended`, `1 = Not Recommended`.
  - Bit 1 (mask `0x0002`): `0 = Attempted`, `1 = Not Attempted`.
  - Bit 2 (mask `0x0004`): `0 = Successful`, `1 = Not Successful`.
- **Bitwise Surface Flag (`surface_flag`)**:
  - Mask `0x0020` (bit 5): Snow/ice.
  - Mask `0x0040` (bit 6): Permanent snow/ice.
  - Mask `0x0080` (bit 7): Radiometer frozen ground.
  - Mask `0x0100` (bit 8): Model frozen ground.
  - Exclude any cells with active snow, ice, or frozen ground flags.
- **Explicit Processing States**:
  - `VALID`: Valid physical retrieval within AOI passing all QC flags.
  - `QUALITY_REJECTED`: Cell attempted retrieval but failed recommendation bit or surface QC flags.
  - `NO_DATA`: Cell contains fill value `-9999.0` or ocean/unobserved swath gap.
  - `FRESH`: Observation age $\le 36\text{ hours}$.
  - `AGING`: Observation age $36\text{ to } 72\text{ hours}$.
  - `STALE`: Observation age $> 72\text{ hours}$.
  - `PROCESSING_ERROR`: File corruption, truncated download, or HDF5 parse error.

---

## 7. PROVENANCE & FRESHNESS MODEL

Every ingested observation will produce machine-readable provenance metadata:
```json
{
  "source_id": "NASA_SMAP_SPL2SMP_NRT",
  "product": "SPL2SMP_NRT",
  "version": "107",
  "granule_id": "SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_002.h5",
  "observation_timestamp": "2026-09-17T00:36:27Z",
  "download_timestamp": "2026-09-17T10:32:00Z",
  "processing_timestamp": "2026-09-17T10:32:05Z",
  "file_size_bytes": 1673298,
  "sha256_hash": "...",
  "aoi_cells_total": 67,
  "aoi_cells_valid": 52,
  "aoi_cells_rejected": 15,
  "aoi_valid_fraction": 0.776,
  "sm_mean_cm3_cm3": 0.2882,
  "sm_min_cm3_cm3": 0.0948,
  "sm_max_cm3_cm3": 0.5027,
  "sm_std_cm3_cm3": 0.0614,
  "derived_anomaly_score": 0.565,
  "quality_status": "VALID",
  "freshness_status": "FRESH",
  "age_hours": 9.9
}
```

---

## 8. EXACT IMPLEMENTATION PLAN

1. **Phase 1: Dedicated NRT Ingestion & Quality Engine** (`smap_nrt_engine.py`):
   - Authenticate via NASA Earthdata (`earthaccess` / `.netrc`).
   - Query NASA CMR for latest `SPL2SMP_NRT.107` covering NER AOI.
   - Atomic download with temporary file protection and SHA-256 calculation.
   - HDF5 swath parsing, coordinate validation, and AOI cell extraction.
   - Full bitwise quality filtering (`retrieval_qual_flag`, `surface_flag`).
   - Resolution harmonization with 9 km historical baseline.
   - Normalized relative saturation anomaly computation.
   - Idempotency & deduplication by granule ID and SHA-256.

2. **Phase 2: Database Schema Extension & Persistence**:
   - Create `smap_nrt_observations` table in `NER_SAFE_DATA/DATABASE/ner_safe_shared.db` using parameterized SQL.
   - Record observation provenance in unified `observations` table.

3. **Phase 3: Risk Engine & Assessment Service Integration**:
   - Wire live SMAP observation into `live_assessment_service.py` to replace static `0.58` with genuine dynamic anomaly.
   - Update `live_ingestion.py` `fetch_latest_smap()` to call the real acquisition engine.
   - Keep 4-factor fusion weights locked ($0.40 / 0.30 / 0.20 / 0.10$).

4. **Phase 4: Scheduler & Automation Wiring**:
   - Wire SMAP polling in `live_monitoring_scheduler.py` to query, acquire, deduplicate, and trigger reassessment cleanly.

5. **Phase 5: REST API & Dashboard Exposure**:
   - Add `/api/smap/latest` and `/api/smap/history` in `live_sensor_server_extension.py`.
   - Update `ner_safe_live_dashboard.html` SMAP card to show real granule ID, observation time, AOI mean, anomaly, and freshness pill without emojis.

6. **Phase 6: Testing & Live Evidence Validation**:
   - Create comprehensive unit and integration test suite `test_smap_nrt_pipeline.py`.
   - Execute real live acquisition test demonstrating genuine NASA provider data.
   - Run complete NER-SAFE regression test suite (`test_judge_demo_smoke.py`, `test_xgboost_production_promotion.py`, `test_live_system.py`).
   - Verify protected release manifest immutability.
   - Generate `NER_SAFE_SMAP_NRT_LIVE_VALIDATION.md`.

---
*Audit completed by Antigravity Agentic AI — Proceeding to user plan approval before execution.*
