# NER-SAFE: JUDGE DEMONSTRATION DAY RUNTIME UTILITIES & TOOLING

**Purpose**: Post-Freeze Operational Tooling Documentation  
**Release Baseline**: `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Status**: Non-Scientific Runtime Convenience Utilities  
**Date**: September 13, 2026  

---

## 1. POST-FREEZE UTILITIES OVERVIEW

In strict adherence to the **Post-Freeze Change Control Protocol** (`NER_SAFE_CHANGE_CONTROL.md`), no frozen scientific logic, machine learning parameters, raster files, vector GeoJSONs, or authoritative release manifests (`NER_SAFE_RELEASE_MANIFEST.json` / `NER_SAFE_RELEASE_MANIFEST.md`) have been altered.

To ensure a seamless, foolproof experience for live demonstrations before technical judges and evaluators, two supplementary runtime utilities were created:

| File | Nature | Primary Role |
| :--- | :--- | :--- |
| `start_nersafe_judge_demo.ps1` | PowerShell Script | One-command launcher: resolves environment, terminates stale instances, runs smoke test, and launches `server.py` |
| `test_judge_demo_smoke.py` | Python Script | Rapid 38-check preflight smoke test verifying runtime readiness, HTTP endpoints, deterministic replay, and zero-emoji UI |

These utilities are strictly **post-freeze operational tooling** designed to orchestrate clean presentation workflows without perturbing the certified scientific baseline.

---

## 2. LAUNCHER SPECIFICATION (`start_nersafe_judge_demo.ps1`)

### Execution Command:
```powershell
.\start_nersafe_judge_demo.ps1
```
*Optional parameters*:
* `-Port <int>`: Specify an alternate port (Default: `8000`).
* `-SkipSmoke`: Bypass the preflight smoke test for instant server startup.

### Lifecycle Actions Executed:
1. **Directory Discovery**: Automatically derives `$PSScriptRoot` (supports running from any PowerShell prompt).
2. **Interpreter Resolution**: Discovers and selects the active 64-bit Python 3.14 interpreter.
3. **Core File Verification**: Confirms all 9 essential frozen runtime artifacts exist before executing code.
4. **Port Cleanup**: Proactively identifies and terminates any stale orphan processes bound to port 8000.
5. **Runtime Preflight**: Executes `test_judge_demo_smoke.py` (38 automated checks).
6. **Server Launch**: Binds `server.py` to `http://localhost:8000` and displays the full judge demonstration sequence on-screen.

---

## 3. SMOKE TEST SPECIFICATION (`test_judge_demo_smoke.py`)

### Execution Command:
```powershell
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_judge_demo_smoke.py
```

### Coverage (38 Automated Checks):
1. **Environment & Core Modules (Checks 01–06)**: Python 3.10+ compatibility, server and demo engine importability, dashboard existence, release manifest existence and valid identifier (`nersafe-judge-demo-baseline-1.0`).
2. **Clean-Start & Mode Separation (Checks 07–12)**: Initial operational state is `NOT_AVAILABLE`, `current_risk_available` is `False`, honest reason returned, previous score disclaimer active.
3. **Deterministic Replay (Checks 13–19)**: Mode is `DEMO_REPLAY`, data source is `LOCAL_REPLAY`, hotspot `EVT-MEG-001`, risk score `0.7055`, tier `CRITICAL`, observation timestamp `2024-05-28T06:00:00Z` decoupled from replay execution time.
4. **Live Server Endpoints (Checks 20–31)**: Ephemeral test server on port 8027 validates `GET /`, `GET /api/assessment/current`, `GET /api/assessment/demo`, and `GET /api/assessment/pipeline` (all 7 stages and `complete_chain_verified: true`).
5. **UX4G Zero-Emoji Compliance & Security (Checks 32–35)**: Zero emojis in active dashboard, E2E demo card present, no credentials or secrets leaked in payloads.
6. **Protected Benchmark Artifact Hash Invariance (Checks 36–38)**: Spot-check confirms `event_records.csv` (13009 bytes), `flow_paths.geojson` (84522 bytes), and `runout_corridors.geojson` (1062284 bytes) match authoritative SHA-256 hashes byte-for-byte.

---

## 4. INTEGRITY DECLARATION

The creation of these two runtime utilities:
* **Did NOT modify** any line of C7–C15 scientific code or four-factor fusion algorithms.
* **Did NOT modify** any validated GeoTIFF or GeoJSON outputs.
* **Did NOT modify** the authoritative freeze manifests `NER_SAFE_RELEASE_MANIFEST.json` and `NER_SAFE_RELEASE_MANIFEST.md`.
* Verified that all **101 protected baseline files** remain 100% SHA-256 intact.
