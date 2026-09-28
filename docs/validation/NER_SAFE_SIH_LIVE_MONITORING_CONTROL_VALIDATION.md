# NER-SAFE — SIH DEMONSTRATION LIVE MONITORING MASTER CONTROL VALIDATION REPORT

**Project:** AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India (NER-SAFE)  
**Host Environment:** Windows 11 Local Demonstration Node  
**Working Directory:** `E:\landslide - Copy\landslide - Copy`  
**Evaluation Date:** 2026-09-17  
**Status:** Certified Operational Baseline & Production Invariant Compliant  

---

## 1. Executive Summary

This report certifies the successful design, implementation, and end-to-end verification of the **Authenticated Master Live Monitoring Control** for the Smart India Hackathon (SIH) demonstration. 

The NER-SAFE system previously possessed background autonomous schedulers and independent live acquisition pipelines across NASA (GPM, SMAP), Copernicus (Sentinel-1 SAR, Sentinel-1 InSAR SLC, Sentinel-2 Optical), and Government of India departmental feeds (GSI Bhusanket, NDMA SACHET, IMD Mausam). However, prior to this implementation, runtime live acquisition lacked a unified, single-source-of-truth master switch directly controllable from the operator dashboard.

The implemented architecture establishes a single authoritative runtime state:
```
LIVE_MONITORING_ENABLED = { OFF | STARTING | ACTIVE | STOPPING | ERROR }
Default after boot / server restart: OFF
```
Neither booting Windows, starting the API server, launching Windows Task Scheduler, nor opening the operator dashboard will automatically enable live data polling. The user must explicitly authenticate and confirm **`[ START LIVE MONITORING ]`** to activate live ingestion cycles.

---

## 2. State Distinction Architecture

To preserve strict scientific integrity and governance standards, the system explicitly decouples operational state from capability status:

| Concept | Dimension | Definition | Governance Rule |
| :--- | :--- | :--- | :--- |
| **`LIVE_MONITORING`** | **Runtime Control** | Operator-governed runtime switch (`OFF`, `STARTING`, `ACTIVE`, `STOPPING`, `ERROR`). | Strictly defaults to `OFF`. When `OFF`, all polling schedulers remain dormant and perform zero network requests or DB writes. |
| **`AUTO_UPDATE_VERIFIED`**| **Capability Status**| Evidence-based component status proving tested upstream ingestion capability. | Never claimed merely because the master switch is `ACTIVE`. Verified strictly via cryptographic hashes, schema validation, and storage guards. |

---

## 3. Files Created and Modified

### Created Files
1. **`live_monitoring_controller.py`**  
   Thread-safe authoritative singleton managing runtime state transitions, process file locks (`.nersafe_autonomous_scheduler.lock`), background worker orchestration, disk storage checks ($\ge 10.0$ GB), and SQLite audit logging.
2. **`test_live_monitoring_master_control.py`**  
   Comprehensive test suite testing all 20 SIH demonstration master control requirements.
3. **`verify_e2e_sih_master_control.py`**  
   Automated 16-step HTTP end-to-end demonstration verification running against a live server.

### Modified Files
1. **`server.py`**  
   - Added `POST /api/live-monitoring/start` (authenticated & authorized for `ADMIN`, `FIELD_OFFICER`, `ANALYST`).
   - Added `POST /api/live-monitoring/stop` (authenticated & authorized).
   - Added `GET /api/live-monitoring/status` (operational telemetry and per-source status).
   - Added `live_monitoring_controller.reset_for_restart()` inside `start_server()` ensuring restart defaults to `OFF`.
2. **`nersafe_autonomous_scheduler.py`**  
   - Added `enforce_master_control` parameter to `AutonomousScheduler` and CLI `--enforce-master-control`.
   - Before executing any cycle, checks `live_monitoring_controller.is_active()`. If `OFF`, halts cycle immediately with status `DORMANT_OFF`.
3. **`register_windows_task.ps1`**  
   - Appended `--enforce-master-control` to Windows Task Scheduler `$ActionArgs` so unattended launches remain dormant unless master control is enabled.
4. **`ner_safe_live_dashboard.html`**  
   - Integrated Master Live Control Bar with prominent state badge (`OFF`, `STARTING`, `ON`, `STOPPING`, `ERROR`).
   - Added buttons `[ START LIVE MONITORING ]` and `[ STOP LIVE MONITORING ]`.
   - Added modal dialogs with explicit confirmations explaining actions.
   - Added expandable Multi-Source Telemetry Drawer displaying live ingestion feeds.
   - Zero emojis used across all markup, icons (pure SVG), and scripts.

### Files Intentionally Untouched
- `NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib` (SHA-256 preserved).
- Locked 4-factor risk weights ($0.40 \times \text{Susc} + 0.30 \times \text{Rain} + 0.20 \times \text{Soil} + 0.10 \times \text{SatChange}$).
- Working source ingestion engines (`smap_nrt_engine.py`, `sentinel1_slc_live_engine.py`, `external_data_engine.py`, etc.).
- External Drive `G:\` (100% off-limits and untouched).

---

## 4. Operational State Machine & Transition Flow

```
                     [Server Boot / Restart]
                                |
                                v
                       +-----------------+
                       |    STATE: OFF   | <-------------------------+
                       +-----------------+                           |
                                |                                    |
                    Authenticated [START]                            |
                     (ADMIN / FIELD / ANALYST)                       |
                                |                                    |
                                v                                    |
                       +-----------------+                           |
                       | STATE: STARTING |                           |
                       +-----------------+                           |
                                |                                    |
                    Storage & Lock Guard Valid                       |
                                |                                    |
                                v                                    |
                       +-----------------+                           |
                       |  STATE: ACTIVE  |                           |
                       +-----------------+                           |
                                |                                    |
                    Authenticated [STOP]                             |
                                |                                    |
                                v                                    |
                       +-----------------+                           |
                       | STATE: STOPPING |                           |
                       +-----------------+                           |
                                |                                    |
                    In-flight downloads finish                       |
                    Process locks released cleanly                   |
                                |                                    |
                                +------------------------------------+
```

---

## 5. Security & RBAC Enforcement

The master control leverages the existing session and cookie-based authentication system (`server.py` + `database.py`):
1. **Unauthenticated Access:**
   `POST /api/live-monitoring/start` and `POST /api/live-monitoring/stop` return `401 Unauthorized` with `{"error": "UNAUTHORIZED", "message": "Authentication required."}`.
2. **Citizen / Public Accounts:**
   Accounts with role `PUBLIC_USER` receive `403 Forbidden` with `{"error": "FORBIDDEN", "message": "Insufficient privileges. Operational role required."}`.
3. **Operational Roles Permitted:**
   `ADMIN`, `FIELD_OFFICER`, and `ANALYST` are authorized to toggle monitoring state.
4. **Audit Trail:**
   Every transition logs actor ID, email, role, IP address, timestamp, previous state, and new state directly to the SQLite `audit_logs` table.

---

## 6. End-to-End SIH 16-Step Verification Evidence

The automated verification script `verify_e2e_sih_master_control.py` executed the full 16-step sequence against a live HTTP server:

```
================================================================================
NER-SAFE: STARTING SIH DEMONSTRATION MASTER CONTROL E2E RUN
================================================================================

[STEP 1] Starting live server instance on port 50707...
  Server is listening on port 50707

[STEP 2] Querying /api/live-monitoring/status for initial state...
  CONFIRMED: Master State is 'OFF' (enabled=False)

[STEP 3] Verifying dormant scheduler suppresses polling while OFF...
[INFO] [AutonomousScheduler] Master Live Monitoring is currently OFF or inactive. Autonomous scheduler cycle dormant.
  CONFIRMED: Scheduler cycle returned 'DORMANT_OFF' - ZERO live acquisition performed

[STEP 4] Logging in as authorized operational user (ADMIN)...
  CONFIRMED: Authenticated as NER-SAFE Lead Administrator (ADMIN)

[STEP 5] Calling POST /api/live-monitoring/start with authentication...
[INFO] [AutonomousScheduler] State transition: OFF -> STARTING (by NER-SAFE Lead Administrator [ADMIN])
[INFO] [AutonomousScheduler] Live monitoring worker thread entered main loop.
[INFO] [AutonomousScheduler] State transition: STARTING -> ACTIVE (by NER-SAFE Lead Administrator [ADMIN])
  Response: {'success': True, 'state': 'ACTIVE', 'message': 'Live monitoring started successfully. Background acquisition active.', 'scheduler_running': True, 'poll_interval_seconds': 30}

[STEP 6] Confirming state transition to ACTIVE...
  CONFIRMED: State successfully transitioned to 'ACTIVE'

[STEP 7 & 8] Executing genuine live monitoring cycle with master control ACTIVE...
  Cycle Status: SUCCESS
  Duration:     67.31s
  Free Storage: 51.97 GB
  Sources Polled (11):
    - GPM                      : NEW_OBSERVATION_ACQUIRED
    - SMAP                     : NEW_OBSERVATION_ACQUIRED
    - SENTINEL1_SLC            : ALREADY_CURRENT
    - GSI_BHUSANKET_WEBAPI     : SUCCESS
    - NDMA_SACHET_CAP          : SUCCESS
    - IMD_MAUSAM_NOWCAST       : OPERATIONAL
    - NER_SAFE_OSINT_ENGINE    : OPERATIONAL
    - OSIRIS_ADAPTER_USGS_GDACS: OPERATIONAL
    - ESA_SENTINEL1_GRD        : LIVE_VERIFIED
    - ESA_SENTINEL2_MSIL2A     : LIVE_VERIFIED
    - NER_SAFE_INSAR_SBAS      : RESEARCH_ONLY

[STEP 9] Verifying SQLite audit log records...
  Recent Audit Logs: ['LIVE_MONITORING_STATE_CHANGE', 'LIVE_MONITORING_STATE_CHANGE', 'LOGIN_SUCCESS', 'REPORT_VERIFIED']

[STEP 10] Querying /api/live-monitoring/status for operational telemetry...
  Master State:   ACTIVE
  Next Cycle:     2026-09-17T15:56:15.941330+00:00
  Total Sources:  11

[STEP 11] Querying /api/monitoring/hotspots to verify risk pipeline...
  Total Hotspots: 48
  Sample Hotspot: Hotspot #1 (Saiha)
  Risk Score:     0.6481 (Tier: HIGH)
  Weights:        0.40 Susceptibility + 0.30 Rain + 0.20 Soil + 0.10 Satellite Change

[STEP 12 & 13] Calling POST /api/live-monitoring/stop to halt monitoring gracefully...
[INFO] [AutonomousScheduler] State transition: ACTIVE -> STOPPING (by NER-SAFE Lead Administrator [ADMIN])
[INFO] [AutonomousScheduler] Live monitoring worker thread exited cleanly.
[INFO] [AutonomousScheduler] State transition: STOPPING -> OFF (by NER-SAFE Lead Administrator [ADMIN])
  CONFIRMED: State successfully transitioned to 'OFF'

[STEP 14] Confirming no new scheduled polling occurs after OFF...
[INFO] [AutonomousScheduler] Master Live Monitoring is currently OFF or inactive. Autonomous scheduler cycle dormant.
  CONFIRMED: Post-stop cycle returned 'DORMANT_OFF'

[STEP 15 & 16] Restarting application and confirming state resets to OFF...
  Starting fresh server instance on port 50797...
  CONFIRMED: Fresh server instance started with master state 'OFF' (enabled=False)

================================================================================
ALL 16 SIH DEMONSTRATION STEPS COMPLETED & VERIFIED 100% SUCCESSFULLY!
================================================================================
```

---

## 7. Full Regression Test Battery Results

| Test Suite | File | Checks / Tests | Result | Execution Time |
| :--- | :--- | :--- | :--- | :--- |
| **Master Control 20 Requirements** | `test_live_monitoring_master_control.py` | 20 / 20 | **PASS 100%** | 54.16s |
| **Judge Demo Smoke Test** | `test_judge_demo_smoke.py` | 38 / 38 | **PASS 100%** | 12.42s |
| **Live System Full Integration** | `test_live_system.py` | 21 / 21 | **PASS 100%** | 8.82s |
| **Autonomous Scheduler Activation** | `test_autonomous_pipeline_activation.py`| 12 / 12 | **PASS 100%** | 59.97s |
| **XGBoost Production Promotion** | `test_xgboost_production_promotion.py` | 9 / 9 | **PASS 100%** | 21.71s |
| **Multi-Temporal InSAR Suite** | `test_insar_multitemporal.py` | 27 / 27 | **PASS 100%** | 24.25s |
| **TOTAL REGRESSION BATTERY** | **6 Test Suites** | **127 / 127** | **PASS 100%** | **181.33s** |

---

## 8. Protected Scientific Invariants & System Safety

### 1. Calibrated XGBoost Production Model Hash
- **File:** `NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib`
- **Certified Expected SHA-256:** `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
- **Computed Post-Implementation SHA-256:** `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
- **Status:** **IDENTICAL & STRICTLY PRESERVED**

### 2. Locked 4-Factor Risk Formula
$$\text{Risk Score} = 0.40 \times \text{Susceptibility} + 0.30 \times \text{Rainfall Anomaly} + 0.20 \times \text{Soil Moisture Anomaly} + 0.10 \times \text{Satellite Change Flag}$$
- Verified: Zero modification to formula weights in `fusion_engine.py`, `live_assessment_service.py`, and `nersafe_autonomous_scheduler.py`.
- IMD Mausam is utilized strictly as contextual/corroborative nowcasting and does not inject artificial risk weights.

### 3. Multi-Temporal InSAR Decoupling
- Verified: InSAR velocity products remain strictly flagged as `RESEARCH_ONLY`.
- Operational risk contribution remains decoupled ($0.00$ operational weight).

### 4. External Drive Protection
- **Target Drive:** `G:\` (External HDD)
- **Status:** **STRICTLY UNTOUCHED AND UNREFERENCED**. All database persistence, logs, and telemetry are confined to `E:\landslide - Copy\landslide - Copy`.

### 5. Zero-Emoji UX4G Standard Compliance
- Automated scan across `ner_safe_live_dashboard.html`, `server.py`, `live_monitoring_controller.py`, `nersafe_autonomous_scheduler.py`, `test_live_monitoring_master_control.py`, and `verify_e2e_sih_master_control.py` returned **EXACTLY 0 EMOJIS** (100% clean SVG icons and professional typography).

---

## 9. Operator Quick-Start Guide for SIH Judges

1. **Launch Server:**
   ```powershell
   & "C:\Users\hp\AppData\Local\Python\pythoncore-3.14-64\python.exe" server.py
   ```
2. **Open Dashboard:**
   Navigate browser to: `http://localhost:8000/`
3. **Verify Initial State:**
   Observe the top Master Control Bar displays:
   `LIVE MONITORING: OFF`
   `SCHEDULER: STOPPED`
4. **Sign In as Administrator:**
   Click **Sign In** -> Authenticate with authorized operational demonstrator credentials (e.g. `admin@nersafe.gov.in` / configured operator password)
5. **Start Live Monitoring:**
   Click **`[ START LIVE MONITORING ]`** -> Confirm prompt in modal dialog.
   Observe transition: `OFF` $\rightarrow$ `STARTING` $\rightarrow$ `ON (ACTIVE)`.
6. **Inspect Telemetry:**
   Click **Live Feeds Telemetry** to expand per-source live telemetry cards (GPM, SMAP, Sentinel-1, Sentinel-2, GSI, SACHET, IMD).
7. **Stop Live Monitoring:**
   Click **`[ STOP LIVE MONITORING ]`** -> Confirm prompt in modal dialog.
   Observe graceful transition: `ON` $\rightarrow$ `STOPPING` $\rightarrow$ `OFF`.
