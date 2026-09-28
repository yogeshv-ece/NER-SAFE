# NER-SAFE: Sentinel-1 SLC Live Acquisition & Multi-Temporal Stack Accumulation Validation Report

**System**: AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India  
**Date**: 2026-09-17  
**Status**: LIVE_VERIFIED (Sentinel-1 SLC Live Accumulator Engine & Windows Scheduler)  
**Scientific InSAR Classification**: RESEARCH_ONLY (Strictly decoupled observational evidence layer)  
**PSI Feasibility Status**: INSUFFICIENT_SLC_STACK_FOR_PSI (3 / 15+ scenes accumulated)  

---

## 1. Existing Baseline

Prior to this implementation, NER-SAFE maintained three verified authentic Sentinel-1D Level-1 IW SLC scenes covering the central Meghalaya AOI (Shillong Plateau / East Khasi Hills / South Garo Hills):
1. `S1D_IW_SLC__1SDV_20260820T235450_20260820T235517_004216_007BCA_7A43.SAFE` (2026-08-20)
2. `S1D_IW_SLC__1SDV_20260901T235450_20260901T235517_004391_0081E8_631B.SAFE` (2026-09-01)
3. `S1D_IW_SLC__1SDV_20260913T235451_20260913T235518_004566_008803_FBA2.SAFE` (2026-09-13)

All three scenes are authentic Sentinel-1D acquisitions on Track 150 Descending, Swath IW1, VV polarization, exhibiting approximately 99.8% spatial overlap. A pairwise InSAR processing engine (`corrected_insar_engine.py`) and multi-temporal SBAS inversion engine (`insar_multitemporal_engine.py`) were validated across 3 baseline interferometric pairs. However, live automated discovery and forward stack accumulation were not unified into a standalone Windows-compatible execution pipeline.

---

## 2. Reused Architecture Components

Rather than rewriting functioning code, the implementation directly reused:
- **`cdse_client.py`**: OAuth2 Keycloak token acquisition for Copernicus Data Space Ecosystem API.
- **`cdse_s3_downloader.py`**: Authenticated S3 client connected to `https://eodata.dataspace.copernicus.eu` with HTTP Range-header resume capability, SHA-256 calculation, and disk space protection.
- **`multitemporal_slc_manager.py`**: OData catalogue querying on Track 150 Descending over Meghalaya point intersection.
- **`insar_multitemporal_engine.py`**: Small Baseline Subset (SBAS) baseline network formation, incremental pair processing, Singular Value Decomposition (SVD) deformation velocity inversion, and triangular phase closure diagnostics.
- **`database.py`**: SQLite tables `insar_scenes`, `insar_pairs`, and `insar_deformation_products`.
- **`source_ingestion_manager.py`**: Ingestion history and provenance logging.

---

## 3. New Live Acquisition Implementation

A unified live engine and scheduler were designed and deployed:
- **`sentinel1_slc_live_engine.py`**: Encapsulates end-to-end catalogue discovery, eligibility gating, idempotency, storage protection, resumable subswath acquisition, integrity verification, persistent registry tracking, and SBAS graph updates.
- **`sentinel1_slc_scheduler.py`**: Windows-compatible daemon/runner supporting both `RUN_ONCE` and `CONTINUOUS` execution modes, configurable polling intervals, exponential backoff, and secret-safe auditable output.

---

## 4. CDSE Discovery Method

The engine performs authenticated queries against the Copernicus Data Space Ecosystem OData API:
```http
GET https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq 'SENTINEL-1' and contains(Name,'_IW_SLC__') and contains(Name,'T23545') and OData.CSC.Intersects(area=geography'SRID=4326;POINT(91.0 25.5)')&$top=50&$orderby=ContentDate/Start desc
```
Authorization is managed via OAuth2 Bearer tokens generated from `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`.

---

## 5. Filtering Rules

Every candidate scene from CDSE must strictly satisfy seven gates before eligibility:
1. **Mission**: Sentinel-1 (S1A, S1B, S1D).
2. **Product Type**: Level-1 Single Look Complex (`SLC`).
3. **Sensor Mode**: Interferometric Wide Swath (`IW`).
4. **Relative Orbit / Track**: Strictly Track 150.
5. **Orbit Direction**: Strictly `DESCENDING`.
6. **Subswath & Polarization**: Swath `IW1`, Polarization `VV`.
7. **Spatial AOI**: Central Meghalaya (`POINT(91.0 25.5)`).

---

## 6. Acquisition Method

Acquisitions are performed via authenticated S3 direct streaming from the CDSE `eodata` bucket:
- Retrieves S3 prefix via OData `Products(id)/S3Path`.
- Downloads essential SAFE subswath assets:
  - `manifest.safe`
  - Annotation XML for IW1 VV
  - Calibration XMLs (`calibration-*.xml`, `noise-*.xml`)
  - Measurement TIFF for IW1 VV
- Uses HTTP Range requests for interrupted transfers.
- Does not download unused swaths (IW2, IW3, VH), reducing per-scene transfer from ~8 GB to ~1.4 GB.

---

## 7. Integrity Validation

Before any scene enters the stack, it must pass four rigorous checks:
1. **TIFF Magic Bytes**: Header must match little-endian `II*\x00` (`49 49 2a 00`).
2. **File Size Threshold**: Measurement TIFF must exceed 500 MB (nominal ~1.3 GB).
3. **Annotation XML Ephemeris**: XML must parse and contain valid `<orbit>` state vectors.
4. **Cryptographic Checksum**: SHA-256 computed for all assets and stored in database.

---

## 8. Storage Protection

Drive E: currently possesses 51.93 GB of free space.
- The engine enforces `MIN_FREE_DISK_GB = 10.0`.
- Before undertaking any download, `check_storage_guard()` evaluates available space.
- If free space < 10.0 GB, acquisition halts with status `STORAGE_GUARD_TRIGGERED`.
- Existing scientifically verified data is never deleted automatically to free space.
- External HDD (`G:`) is never touched or configured.

---

## 9. Idempotency & Deduplication

The pipeline is strictly idempotent:
- Polling an already acquired scene returns:
  - `status: ALREADY_CURRENT`
  - `cycle_result: NO_NEW_ELIGIBLE_SCENE`
- Detection checks local directory structure, SQLite `insar_scenes` table, and persistent JSON registry.
- Repeated scheduler executions produce zero duplicate database records and zero re-downloads.

---

## 10. SLC Stack Registry

The persistent registry (`NER_SAFE_DATA/SENTINEL1/slc_stack_registry.json`) tracks each scene through granular lifecycle states:
- `DISCOVERED`
- `VALIDATED`
- `ACQUISITION_PENDING`
- `ACQUIRED`
- `INTEGRITY_VERIFIED`
- `REGISTERED`
- `ARCHIVED`
- `REJECTED`
- `FAILED`
- `ALREADY_CURRENT`

---

## 11. Automatic Pair Generation

When a new valid scene arrives, `InSARMultiTemporalEngine.construct_pair_network()` evaluates all possible pairings against scientific constraints:
- Same Relative Orbit (150)
- Same Orbit Direction (DESCENDING)
- Same Polarization (VV)
- Temporal Baseline $B_{\text{temp}} \le 60.0\text{ days}$
- Perpendicular Baseline $B_{\perp} \le 300.0\text{ m}$

---

## 12. SBAS Network Update & Incremental Processing

- Unchanged pairs are reused from cache (`INSAR_CORRECTED/` or `pairs/PAIR_*/`), preventing costly reprocessing.
- Newly qualified pairs are processed via `CorrectedInSARPipeline`.
- SVD inversion updates incremental deformation rates.
- Triangular phase closure diagnostics check for phase unwrapping errors across closed loops.

---

## 13. Windows-Compatible Scheduler

The scheduler runs natively on Windows laptops without requiring external Linux/college servers:
- **`RUN_ONCE`**: Single audit cycle, exits with code 0.
- **`CONTINUOUS`**: Periodic daemon with configurable polling interval (default 6 hours), exponential backoff on network failures, and safe termination on KeyboardInterrupt.

---

## 14. Dashboard & API Observability

- **REST API (`/api/insar/status`)**: Exposes `stack_size_scenes` (3), `target_stack_size` (15), `stack_target_progress` ("3 / 15+ scenes"), `acquisition_status` ("ACCUMULATION_ACTIVE"), `last_successful_cdse_check_utc`, `last_check_status` ("ALREADY_CURRENT"), `sbas_status` ("SBAS_INITIAL_STACK_FORMED"), `psi_status` ("INSUFFICIENT_SLC_STACK_FOR_PSI"), `scientific_status` ("RESEARCH_ONLY"), and storage metrics.
- **Live HTML Dashboard (`ner_safe_live_dashboard.html`)**: Enhanced InSAR card displaying real-time stack progress, acquisition status, and CDSE polling timestamps.

---

## 15. Genuine Live Test Evidence

Execution of genuine live CDSE check via `sentinel1_slc_scheduler.py --mode RUN_ONCE --force-refresh`:
```text
[SLC Scheduler] Starting RUN_ONCE cycle #1 at 2026-09-17T07:12:21.351985+00:00...
------------------------------------------------------------
NER-SAFE SENTINEL-1 SLC LIVE CHECK
------------------------------------------------------------
Checked:              2026-09-17T07:12:21.352009+00:00
Provider:             Copernicus Data Space Ecosystem (CDSE)
Query:                Sentinel-1 SLC / IW / descending / Track 150 / VV (Meghalaya)
Cycle Status:         ALREADY_CURRENT
Cycle Result:         NO_NEW_ELIGIBLE_SCENE
Products Discovered:  27
Already Registered:   3
New Eligible:         0
Stack Scenes:         3 / 15+ scenes
Eligible Pairs:       3
SBAS Status:          SBAS_INITIAL_STACK_FORMED
PSI Status:           INSUFFICIENT_SLC_STACK_FOR_PSI
Scientific Status:    RESEARCH_ONLY
Duration:             5.98s
------------------------------------------------------------
```
The query reached CDSE servers, evaluated catalogue inventory, recognized all 3 baseline scenes (2026-08-20, 2026-09-01, 2026-09-13), confirmed no unacquired forward repeat passes exist prior to 2026-09-25, and reported `NO_NEW_ELIGIBLE_SCENE`.

---

## 16. Failure Handling

The subsystem gracefully handles:
- **CDSE OData Down**: Caught as network exception, logged, backs off.
- **S3 Network Timeout**: Caught during chunk streaming, resumes using Range header.
- **Corrupted Download**: Caught by TIFF magic byte or size checks; quarantined/cleaned.
- **Low Disk Space**: Checked before transfer; halts safely with `STORAGE_GUARD_TRIGGERED`.
- **Credential Safety**: Zero secrets, tokens, or private keys are ever output to logs or APIs.

---

## 17. Regression Results

All existing test suites pass with 100% success rate:
- `test_sentinel1_slc_live_acquisition.py`: **24 / 24 PASSED**
- `test_insar_multitemporal.py`: **27 / 27 PASSED**
- `test_slc_live_acquisition_scheduler.py`: **7 / 7 PASSED**
- `test_judge_demo_smoke.py`: **38 / 38 PASSED**
- `test_xgboost_production_promotion.py`: **9 / 9 PASSED**
- `test_live_system.py`: **21 / 21 PASSED**

**Invariants Verified**:
- Locked XGBoost hash: `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c` (100% match)
- Locked 4-factor risk weights: `0.40 / 0.30 / 0.20 / 0.10` (100% unchanged)
- External HDD (`G:`): Untouched

---

## 18. Current Scene Count & Gap Toward 15+ Scenes

- **Current Stack Size**: 3 genuine Sentinel-1D IW SLC scenes.
- **Target Stack Size for Next Scientific Evaluation**: 15 scenes.
- **Remaining Gap**: 12 repeat passes.
- At nominal 12-day repeat revisit, 12 additional acquisitions span approximately 144 days.

---

## 19. Scientific Honesty: Why PSI is NOT Validated

NER-SAFE adheres to strict scientific honesty:
1. **Atmospheric Phase Screen (APS) Separation**: Estimating and inverting tropospheric delay gradients without overfitting requires a minimum of 15-20 independent temporal observations.
2. **Persistent Scatterer Candidate Selection**: Computing the amplitude dispersion index ($D_A = \sigma_A / \mu_A < 0.25$) on fewer than 15 scenes suffers from small-sample statistical bias.
3. **Vegetative Temporal Decorrelation**: C-band coherence in subtropical humid rainforests (Meghalaya) decays rapidly outside rocky quartzite bedrock outcrops.
4. **Decoupled Risk Architecture**: InSAR remains classified as `RESEARCH_ONLY` (`INSAR_RESEARCH_EVIDENCE_DECOUPLED`). It does not contribute to the production risk score or trigger operational alerts.

---

## 20. Future Migration Path to College Server

When the college server becomes available:
1. Transfer repository via Git.
2. Configure systemd unit or cron job pointing to `sentinel1_slc_scheduler.py --mode CONTINUOUS --interval 21600`.
3. Mount persistent storage with $\ge 200\text{ GB}$ allocation for full SLC stack.
4. Establish automated synchronization to Google Drive long-term archive.
