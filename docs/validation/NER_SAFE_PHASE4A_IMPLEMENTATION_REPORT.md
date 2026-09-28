# NER-SAFE PHASE 4A: CONTROLLED OPERATIONAL IMPLEMENTATION REPORT
## GSMaP_NOW Primary Ingestion + 3D Topographic Terrain + Citizen Video Moderation Pipeline

**Document Reference**: `NER_SAFE_PHASE4A_IMPLEMENTATION_REPORT.md`  
**Execution Timestamp**: `2026-09-21T19:58:30+05:30` (UTC: `2026-09-21T14:28:30Z`)  
**Repository Working Copy**: `E:\landslide - Copy\landslide - Copy`  
**External Storage Quarantine**: `G:\` strictly untouched, unqueried, and isolated  
**Authoritative Operational Authority**: Smart India Hackathon (SIH) 2024 — Problem Statement 26001  

---

## 1. Pre-Implementation State & Architectural Baseline

Prior to Phase 4A, the NER-SAFE live system operated under the Phase 3 approved architectural blueprint with the following characteristics:
1. **Rainfall Pipeline**: The system used NASA GPM IMERG Early NRT (`GPM_3IMERGHHE.07`) as a simulated/direct query with a 4.0-hour source latency. No automated connection existed to JAXA GSMaP_NOW, although Phase 2 forensic verification confirmed that JAXA GSMaP_NOW Version 8 regional South Asia subset (`/now/txt/05_AsiaSS`) publishes half-hourly data with ~31-minute measured latency.
2. **Terrain Visualization**: The interactive live dashboard (`ner_safe_live_dashboard.html`) provided 2D Leaflet mapping with OSM, Esri Satellite, and CARTO Positron Light basemaps, but lacked a 3D topographic terrain viewer for visualizing geomorphic elevation profiles, slope angles, and runout corridors.
3. **Citizen Multimedia**: Crowdsourced ground reports supported geotagged static photos (`.jpg`, `.png`), but lacked an isolated quarantine and validation pipeline for field video submissions, leaving citizen video unhandled.
4. **Security Vulnerability**: In `NER_SAFE_PHASE2_JAXA_GSMAP_NOW_FORENSIC_VERIFICATION.md`, the FTP credential was present in plaintext at lines 19 and 306, and `.env` was not formally tracked in `.gitignore`.

---

## 2. Files Inspected

Before implementing any code or modifying schemas, the following repository files were systematically inspected:
- `NER_SAFE_PHASE1_FORENSIC_AUDIT_REPORT.md`: Validated locked model paths, XGBoost SHA-256, and 4-factor risk formula.
- `NER_SAFE_PHASE2_JAXA_GSMAP_NOW_FORENSIC_VERIFICATION.md`: Examined JAXA endpoint, directory structure, CSV format, and Meghalaya/Mizoram coverage.
- `NER_SAFE_PHASE3_FINAL_REALTIME_ARCHITECTURE.md`: Analyzed primary/fallback state transitions, latency definitions, and invariant rules.
- `NER_SAFE_PHASE3_DATA_FLOW_MAP.md`: Reviewed end-to-end data pipelines from source ingestion to CAP alert dispatch.
- `NER_SAFE_PHASE3_EXECUTION_TIMELINE.md`: Validated phase staging and operational safeguards.
- `server.py`: Evaluated HTTP routing, authentication sessions, and REST endpoints.
- `ner_safe_live_dashboard.html`: Inspected Leaflet map container, floating search bar, basemap selector, and telemetry provenance cards.
- `database.py`: Inspected SQLite database schema, table definitions, and index strategies.
- `live_assessment_service.py`: Examined live assessment execution, anomaly derivation, and SQLite persistence.
- `weather_provider.py`: Reviewed multi-source weather providers and failover orchestration.
- `sensor_source_registry.py`: Inspected sensor latency registries and metadata catalogs.
- `live_ingestion.py`: Reviewed scheduled polling loops and CMR query bridges.
- `fusion_engine.py`: Validated 4-factor risk weights ($0.40, 0.30, 0.20, 0.10$) and 48 hotspot coordinates.

---

## 3. Files Created and Modified

### Created Files:
1. `gsmap_now_engine.py`: Dedicated JAXA GSMaP_NOW Version 8 operational ingestion engine (FTP connection, atomic download, ZIP verification, CSV parsing, NER AOI extraction, rainfall statistics, anomaly calculation, and publication lag telemetry).
2. `video_integrity_analyzer.py`: Citizen video intake pipeline (path sanitization, MIME validation, ISO BMFF atom parser, SHA-256 digest, FFmpeg transcode worker, keyframe extraction, 8x8 pHash perceptual hashing, and SQLite persistence).
3. `test_phase4a_gsmap_failover.py`: Unit and integration test suite covering GSMaP FTP acquisition, parsing, anomaly parity, stale detection, failover to GPM, and dual-failure degraded mode.
4. `test_phase4a_video_pipeline.py`: Comprehensive test suite covering video upload validation, traversal security, ISO BMFF metadata, FFmpeg transcode, duplicate detection, and moderation state machine.
5. `test_phase4a_3d_terrain.py`: Test suite verifying CesiumJS library inclusion, DOM container, 3D basemap toggle, WebGL fallback notice, and risk engine decoupling.
6. `NER_SAFE_PHASE4A_LIVE_GSMAP_VALIDATION.json`: Authoritative JSON provenance artifact documenting the genuine JAXA GSMaP_NOW live acquisition.
7. `.gitignore`: Root Git exclusion rules safeguarding `.env`, credential files, tokens, temporary ZIP downloads, and keyframe caches.

### Modified Files:
1. `NER_SAFE_PHASE2_JAXA_GSMAP_NOW_FORENSIC_VERIFICATION.md`: Sanitized plaintext credentials at lines 19 and 306, replacing with environment variable references.
2. `database.py`: Added `citizen_videos` table definition and performance indexes (`idx_videos_status`, `idx_videos_sha256`) to SQLite schema initialization.
3. `server.py`: Added routes for citizen video intake (`POST /api/videos/upload`), video listing (`GET /api/videos`), video details (`GET /api/videos/<id>`), thumbnail delivery (`GET /videos/thumbnails/<filename>`), and moderation status update (`PATCH /api/videos/<id>/moderate`). Increased max JSON payload size for video base64 streams to 60 MB.
4. `ner_safe_live_dashboard.html`:
   - Updated precipitation telemetry card to display `JAXA GSMaP_NOW (Primary)` vs `NASA GPM Early (Fallback)`, active source status, observation time, source age, processing latency, and historical baseline.
   - Added CesiumJS CSS/JS to `<head>` and `#cesiumContainer` with `#cesiumFallbackNotice` in `.map-container`.
   - Added `3D Terrain` button (`#btnBasemap3D`) to the basemap selector with zero-emoji SVG icon.
   - Added JavaScript 3D lifecycle methods (`toggle3DView`, `switchTo2D`, `switchTo3D`, `initCesiumViewer`, `populateCesiumHotspots`) with automatic WebGL detection and non-blocking fallback to 2D Leaflet.
5. `weather_provider.py`: Added `GSMaPWeatherProvider`, operational state constants (`STATE_GSMAP_PRIMARY`, `STATE_GPM_FALLBACK`, `STATE_RAIN_DEGRADED`, etc.), and `get_primary_rainfall()` method with automatic failover logic.
6. `sensor_source_registry.py`: Registered `JAXA_GSMAP_NOW_01` as primary live precipitation feed with 0.52h publication lag; updated NASA GPM NRT as secondary fallback.
7. `live_ingestion.py`: Updated `fetch_latest_gpm()` to poll GSMaP_NOW primary before failing over to NASA CMR GPM Early.
8. `live_assessment_service.py`: Added `discover_and_acquire_gsmap_now()` and `acquire_operational_rainfall()`. Updated SQLite schema with `rainfall_source`, `rainfall_product`, `source_age_seconds`, and `processing_latency_seconds`.
9. `test_judge_demo_smoke.py`: Updated assertion in Section 2 to recognize both active live observation mode (`CURRENT_ASSESSMENT_ACTIVE`) and dormant clean-start mode.

---

## 4. JAXA GSMaP_NOW Primary Live Rainfall Ingestion

The dedicated ingestion worker `gsmap_now_engine.py` interfaces directly with the JAXA Earth Observation Research Center (EORC) passive FTP endpoint:
- **Host**: `ftp.eorc.jaxa.jp`
- **User**: Read from `JAXA_GSMAP_USER` (default: `rainmap`)
- **Password**: Read strictly from `JAXA_GSMAP_PASSWORD` in `.env`
- **Target Remote Directory**: `/now/txt/05_AsiaSS` (Regional South Asia subset)

### Ingestion Lifecycle:
1. **Directory Discovery**: Passive FTP directory traversal retrieves candidate `.csv.zip` files sorted chronologically.
2. **Timestamp Parsing**: File names following `gsmap_now.YYYYMMDD.HHMM_hhnn.05_AsiaSS.csv.zip` are parsed to extract start and end UTC observation timestamps.
3. **Atomic Staging**: Files are streamed into a temporary PID-tagged buffer (`.tmp.<pid>`) in `NER_SAFE_DATA/RAW_INGEST/GSMAP/` and validated for size (> 10 KB) and ZIP integrity (`zipfile.testzip()`). Only uncorrupted archives are atomically committed.
4. **AOI Regional Extraction**: The zipped CSV is extracted in-memory. Every row is parsed and filtered against the North Eastern Region geographic bounding box ($21.0^\circ\text{N} \le \text{Lat} \le 27.0^\circ\text{N}$, $89.0^\circ\text{E} \le \text{Lon} \le 94.0^\circ\text{E}$).
5. **Quality Assurance**: Invalid cells, non-numeric values, and fill tokens are excluded. Summary statistics are computed:
   - Cell count (NER total)
   - Valid cell count
   - Missing cell count
   - Spatial mean rain rate ($\text{mm/h}$)
   - Regional max rain rate ($\text{mm/h}$)
   - 90th percentile rain rate ($p_{90}$)
   - State-specific coverage for Meghalaya and Mizoram

---

## 5. Secondary/Fallback Architecture: NASA GPM Early NRT

The precipitation manager enforces explicit failover states:
- `GSMAP_PRIMARY`: JAXA GSMaP_NOW is operational and fresh ($\text{age} \le 120\text{ min}$).
- `GPM_FALLBACK`: GSMaP_NOW is stale or unreachable; NASA GPM IMERG Early NRT (`GPM_3IMERGHHE.07`) is acquired via NASA Earthdata CMR.
- `RAIN_DEGRADED`: Both GSMaP and GPM feeds are temporarily unavailable; the engine holds the last valid observation with explicit degradation flags.
- `RAIN_STALE`: Observations exceed the 24-hour validity threshold; neutral climatological baseline ($0.35$) is supplied with strict provenance warnings.
- `RAIN_UNAVAILABLE`: Total telemetry blackout.

**Critical Invariant**: GSMaP and GPM precipitation rates are **NEVER summed together**.

---

## 6. Rainfall Anomaly Compatibility & Parity

To prevent architectural divergence, GSMaP_NOW precipitation rates are mapped into the canonical NER-SAFE rainfall anomaly feature ($A_{\text{rain}} \in [0.0, 1.0]$) using the identical mathematical adapter established in `live_assessment_service.py`:

$$\text{Anomaly} = \min\left(1.0, \max\left(0.15, \frac{\text{Mean}}{8.0} \times 0.40 + \frac{\text{Max}}{25.0} \times 0.40 + 0.20\right)\right)$$

### Properties:
- In dry conditions ($\text{Mean} = 0$, $\text{Max} = 0$), the anomaly settles at the baseline minimum of $0.20$.
- In moderate rainfall ($\text{Mean} = 2.0\text{ mm/h}$, $\text{Max} = 10.0\text{ mm/h}$), the anomaly yields $0.46$.
- In extreme monsoon events ($\text{Mean} \ge 12.0\text{ mm/h}$, $\text{Max} \ge 40.0\text{ mm/h}$), the value saturates cleanly at $1.00$.
- The historical rainfall baseline continues to be anchored to NASA GPM IMERG Final Daily V07 ($p_{90}$ static climatology).

---

## 7. 3D Topographic Terrain Implementation

In compliance with Phase 3 architecture:
1. **Engine**: CesiumJS (v1.119) integrated alongside 2D Leaflet in `ner_safe_live_dashboard.html`.
2. **Terrain Elevation Baseline**: Built upon the existing SRTM 1 arc-second (30m) geomorphic DEM. The DEM is treated as a static topographic boundary condition (not claimed to be real-time).
3. **Overlays Rendered**:
   - 48 Fused risk hotspots positioned as 3D elevation cylinders extruded proportionately to risk scores.
   - Dynamic tier coloring (Critical: Red `#DC2626`, High: Orange `#EA580C`, Moderate: Amber `#F59E0B`, Watch: Blue `#3B82F6`).
   - Interactive selection cards displaying district, state, coordinates, 4-factor contributions, and morphometrics.
   - Seamless basemap switcher integration: toggling `3D Terrain` hides Leaflet and flies the camera to Meghalaya/Mizoram coordinates ($92.0^\circ\text{E}, 24.5^\circ\text{N}$, altitude $250\text{ km}$, pitch $-55^\circ$).
4. **WebGL Graceful Fallback**: If WebGL hardware acceleration is absent or Cesium fails to load, `isWebGLSupported()` detects the condition and renders an unobtrusive banner:
   > *"WebGL acceleration unavailable. Operational 2D Leaflet map active."*
   The operational 2D Leaflet map remains fully functional and unaffected.

---

## 8. Citizen Video Ingestion & Moderation Pipeline

The citizen video pipeline in `video_integrity_analyzer.py` handles field video submissions with full security isolation:
1. **Upload & Quarantine**: Video bytes are written to `NER_SAFE_DATA/UPLOADS/videos/quarantine/` with a deterministic, collision-resistant identifier: `VID-YYYYMMDDHHMMSS-<sha256[:8]>`.
2. **Container Validation**: Magic bytes are inspected (ISO BMFF `ftyp` for MP4, `\x1A\x45\xDF\xA3` for WebM/Matroska). Text, executables, or shell scripts disguised as videos are rejected.
3. **Resource Limits**:
   - Maximum upload size: $50\text{ MB}$.
   - Maximum allowed duration: $60\text{ seconds}$.
   - Processing timeout: $30\text{ seconds}$ with `stdin=subprocess.DEVNULL`.
   - Keyframe extraction limit: 10 frames.
4. **Metadata Extraction**: A native ISO BMFF atom parser extracts duration, timescale, creation timestamp, and track configurations directly from the binary stream without external tools.
5. **Transcode Worker**: FFmpeg transcodes uploads into an optimized 720p H.264 working copy in `NER_SAFE_DATA/UPLOADS/videos/transcoded/`.
6. **Keyframe Extraction & pHash**: Keyframes are extracted at 1 fps into `NER_SAFE_DATA/UPLOADS/videos/keyframes/<video_id>/`. An 8x8 average perceptual hash (pHash) is generated for each frame to detect duplicate or recycled footage.
7. **Human Moderation Workflow**: State machine enforces transitions:
   - `SUBMITTED` $\rightarrow$ `QUARANTINED` $\rightarrow$ `PROCESSING` $\rightarrow$ `READY_FOR_REVIEW` $\rightarrow$ `VERIFIED` / `REJECTED`.
8. **Decoupled Risk Weight Invariant**:
   - Operational Risk Weight: **Strictly 0.00**.
   - Citizen video evidence is categorized exclusively as `CONTEXTUAL_EVIDENCE_ONLY` and cannot alter the automated 4-factor risk score.

---

## 9. Security Controls & Sanitization

1. **Credential Sanitization**: Removed all hardcoded JAXA passwords from markdown documentation. Verified zero plaintext credentials exist in codebase.
2. **Path Traversal Prevention**: Filenames are sanitized via `re.sub(r'[^a-zA-Z0-9_.-]', '_', os.path.basename(filename))`, stripping directory separators and `..` sequences.
3. **Subprocess Hardening**: All FFmpeg executions use discrete argument vectors (never `shell=True`) and redirect standard input to `subprocess.DEVNULL`.
4. **Repository Protection**: Created `.gitignore` excluding `.env`, `.netrc`, `.pem`, `.key`, raw video archives, and temporary artifacts.

---

## 10. Database Schema Changes

The SQLite database (`ner_safe_shared.db`) was extended with the `citizen_videos` table without altering or breaking existing tables:

```sql
CREATE TABLE IF NOT EXISTS citizen_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT UNIQUE NOT NULL,
    report_id TEXT,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    duration_seconds REAL DEFAULT 0.0,
    sha256_hash TEXT NOT NULL,
    gps_latitude REAL,
    gps_longitude REAL,
    capture_time_utc TEXT,
    quarantine_path TEXT NOT NULL,
    transcoded_path TEXT,
    keyframes_json TEXT,
    phash_list_json TEXT,
    moderation_status TEXT DEFAULT 'READY_FOR_REVIEW',
    verified_by TEXT,
    verification_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_videos_status ON citizen_videos(moderation_status);
CREATE INDEX IF NOT EXISTS idx_videos_sha256 ON citizen_videos(sha256_hash);
```

In `live_assessments`, the table schema was migrated to persist provenance fields:
- `rainfall_source`: (`GSMAP_PRIMARY`, `GPM_FALLBACK`, `RAIN_DEGRADED`)
- `rainfall_product`: Granule/product filename
- `source_age_seconds`: Age of the observation in seconds
- `processing_latency_seconds`: Ingestion and extraction runtime in seconds

---

## 11. REST API Changes

| Method | Endpoint | Description | Auth / Role |
|---|---|---|---|
| `GET` | `/api/videos` | List citizen videos in moderation queue (`?status=...`) | Public / Analyst |
| `GET` | `/api/videos/<id>` | Retrieve detailed metadata for a video submission | Public / Analyst |
| `GET` | `/videos/thumbnails/<filename>` | Serve generated keyframe image thumbnails | Public |
| `POST` | `/api/videos/upload` | Ingest video payload (Base64), validate, transcode, queue | Authenticated / Public |
| `PATCH` | `/api/videos/<id>/moderate` | Update status to `VERIFIED` or `REJECTED` | Field Officer / Admin |
| `GET` | `/api/assessment/current` | Returns live assessment with `rainfall_source` | Public |
| `GET` | `/api/weather/providers` | Lists active precipitation feeds and failover state | Public |

---

## 12. Dashboard UI Updates

In `ner_safe_live_dashboard.html`:
1. **Precipitation Telemetry Card**:
   - Header: `JAXA GSMaP_NOW (Primary)` or `NASA GPM Early (Fallback)`
   - Status Pill: `GSMAP_PRIMARY` / `GPM_FALLBACK` / `RAIN_DEGRADED`
   - Observation Time: Genuine observation UTC timestamp
   - Source Age: Formatted in minutes (e.g., `87.7 min age (FRESH)`)
   - Processing Latency: Recorded pipeline duration (e.g., `3.40s`)
   - Daily Baseline: Clarified as `NASA GPM Final Daily V07 (Static Climatology)`
2. **3D Topographic Terrain View**:
   - Toggle button added to floating basemap selector with clean SVG icon.
   - Cesium WebGL viewer initialized on demand.
   - Non-blocking notification banner for unsupported environments.
   - Strict adherence to UX4G zero-emoji design rules.

---

## 13. Automated Test Verification Summary

| Test Suite | Tests Run | Passed | Failed | Status |
|---|---|---|---|---|
| `test_phase4a_gsmap_failover.py` | 9 | 9 | 0 | **PASS** |
| `test_phase4a_video_pipeline.py` | 8 | 8 | 0 | **PASS** |
| `test_phase4a_3d_terrain.py` | 7 | 7 | 0 | **PASS** |
| `test_judge_demo_smoke.py` | 38 checks | 38 | 0 | **PASS** |
| `test_live_system.py` | 21 checks | 21 | 0 | **PASS** |
| `test_xgboost_production_promotion.py` | 1 | 1 | 0 | **PASS** |
| `test_canonical_model_evaluation.py` | 1 | 1 | 0 | **PASS** |
| `test_sih_final_demo_preflight.py` | 39 | 39 | 0 | **PASS** |

---

## 14. Genuine Live GSMaP Evidence

The following empirical evidence was obtained directly from JAXA EORC FTP during runtime execution:

```json
{
  "system": "NER-SAFE Operational Environmental Risk Engine",
  "status": "LIVE_VERIFIED",
  "rainfall_provenance": {
    "active_source": "GSMAP_PRIMARY",
    "provider": "JAXA Earth Observation Research Center (EORC)",
    "product_filename": "gsmap_now.20260921.1300_1359.05_AsiaSS.csv.zip",
    "file_size_bytes": 340393,
    "sha256_hash": "7d06342672cc84b5df46bb0813a57502063ac857c7879324319cc56f129b8e6e",
    "observation_start_utc": "2026-09-21T13:00:00+00:00",
    "observation_end_utc": "2026-09-21T13:59:00+00:00",
    "source_age_minutes": 87.72,
    "freshness_state": "FRESH",
    "regional_precipitation": {
      "mean_precip_mm_h": 0.0719,
      "max_precip_mm_h": 10.52,
      "p90_precip_mm_h": 0.0,
      "meghalaya_cells_covered": 360,
      "mizoram_cells_covered": 208,
      "derived_rainfall_anomaly": 0.3719
    }
  },
  "latency_telemetry": {
    "T_source": "2026-09-21T13:00:00+00:00",
    "T_available": "2026-09-21T13:59:00+00:00",
    "T_download": "2026-09-21T14:27:43.459025+00:00",
    "T_processed": "2026-09-21T14:27:43.459025+00:00",
    "T_risk_updated": "2026-09-21T14:27:43.459157+00:00",
    "T_dashboard_updated": "2026-09-21T14:27:59.017145+00:00",
    "source_age_minutes": 87.72,
    "download_latency_seconds": 0.0,
    "processing_latency_seconds": 3.399,
    "end_to_end_latency_seconds": 18.96
  },
  "live_assessment_record": {
    "assessment_id": "ASM-LIVE-20260921142743-dda6c5ab",
    "triggering_source": "JAXA_GSMAP_NOW_01",
    "rainfall_source": "GSMAP_PRIMARY",
    "rainfall_product": "gsmap_now.20260921.1300_1359.05_AsiaSS.csv.zip",
    "max_risk_score": 0.5769
  }
}
```

---

## 15. Failover Verification Evidence

In `test_phase4a_gsmap_failover.py`:
- When GSMaP encounters simulated FTP timeouts (`ConnectionError`), `UnifiedPrecipitationManager` automatically engages NASA GPM Early NRT, setting `rainfall_source = "GPM_FALLBACK"`.
- When both GSMaP and GPM are simultaneously disabled, the system transitions to `RAIN_DEGRADED` (or `RAIN_STALE`), preserving the last legitimate observation or supplying the neutral baseline ($0.35$). Synthetic rainfall values are **never fabricated**.
- Upon restoring GSMaP, the engine immediately re-promotes the feed to `GSMAP_PRIMARY`.

---

## 16. 3D Terrain Verification Evidence

In `test_phase4a_3d_terrain.py`:
- Confirmed CesiumJS widgets CSS and JS bundle links in `<head>`.
- Confirmed `#cesiumContainer` is present and positioned within `.map-container`.
- Confirmed 3D toggle button `#btnBasemap3D` exists in the basemap group.
- Verified `populateCesiumHotspots` constructs 3D cylinders with heights scaled to fused risk scores.
- Confirmed WebGL fallback notice `#cesiumFallbackNotice` renders with zero emojis.
- Confirmed operational 4-factor risk calculation executes independently of graphics hardware.

---

## 17. Citizen Video Verification Evidence

In `test_phase4a_video_pipeline.py`:
- Verified path traversal protection against `../../etc/passwd` and script injection.
- Validated binary container checks rejecting fake MP4 files.
- Confirmed rejection of files exceeding $50\text{ MB}$.
- Verified duration and timescale parsing from ISO BMFF atom headers.
- Tested FFmpeg transcode into 720p H.264 working copy.
- Confirmed keyframe generation at 1 fps and 8x8 average perceptual hash computation.
- Verified moderation transitions (`READY_FOR_REVIEW` $\rightarrow$ `VERIFIED` / `REJECTED`).
- Confirmed operational risk weight remains strictly **0.00**.

---

## 18. Performance and Resource Impact

- **GSMaP Ingestion Runtime**: ~3.40 seconds for regional CSV decompression and spatial filtering.
- **Memory Footprint**: ~35 MB transient memory during CSV parsing. Regional subset is ~340 KB compressed, avoiding massive global raster overhead.
- **Storage Impact**: ~340 KB per half-hourly cycle. Daily accumulation is ~16.3 MB, well within local storage constraints.
- **Client-Side Rendering**: 3D terrain loads asynchronously on demand. Leaflet 2D remains default, preventing resource exhaustion on lightweight client machines.

---

## 19. Remaining SIH Problem Statement 26001 Gaps

The following capabilities were explicitly excluded from Phase 4A scope and remain planned for subsequent operational phases:
1. **Official IMD REST Gateway**: Pending inter-departmental MoU and production API credentials from the Ministry of Earth Sciences (MoES).
2. **Physical IoT Ground Telemetry**: Field piezometer, tiltmeter, and rain gauge telemetry remains mocked via the simulated NIT Meghalaya sensor adapter.
3. **Public Cellular SMS Dispatch**: Awaiting cellular gateway credentials; alerts currently dispatch via CAP v1.2 JSON and local SSE push.
4. **Cloud / High-Availability Deployment**: Running locally on development workstation.
5. **Research Model Promotion**: CNN, InSAR SBAS, and C15 Temporal Forecasting remain strictly research/shadow components with 0.00 operational weight.

---

## 20. Production Invariants Independent Verification

The following production invariants were independently re-verified:

1. **Production XGBoost Model Artifact SHA-256**:
   - Path: `NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib`
   - Canonical Hash: `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
   - Computed Hash:  `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
   - **Verification**: **MATCH (100% BYTE-FOR-BYTE IDENTICAL)**

2. **Operational 4-Factor Risk Formula**:
   $$\text{Risk} = 0.40 \times \text{Susc} + 0.30 \times \text{Rain} + 0.20 \times \text{Soil} + 0.10 \times \text{Sat}$$
   - **Verification**: **UNCHANGED**

3. **Operational Severity Thresholds**:
   - `CRITICAL`: $\ge 0.65$
   - `HIGH`: $\ge 0.48 \text{ and } < 0.65$
   - `MODERATE`: $\ge 0.32 \text{ and } < 0.48$
   - `WATCH`: $< 0.32$
   - **Verification**: **UNCHANGED**

4. **External Backup Drive `G:\`**:
   - Access, mount, query, copy, or write: **ZERO (COMPLETELY UNTOUCHED)**

5. **Credential Exposure**:
   - Codebase, logs, frontend, reports, and Git: **ZERO EXPOSURE**

6. **Synthetic Rainfall Data**:
   - **ZERO FABRICATED RAINFALL**

7. **Research Component Operational Weights**:
   - Spatial CNN: $0.00$
   - Sentinel-1 InSAR: $0.00$
   - C15 Temporal Forecaster: $0.00$
   - Citizen Video Evidence: $0.00$
   - **Verification**: **STRICTLY PROTECTED**
