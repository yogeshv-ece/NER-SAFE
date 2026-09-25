# NER-SAFE: JUDGE DEMONSTRATION BASELINE & REPRODUCIBILITY GUIDE

**Problem Statement**: SIH 26001 — AI-Based Early Warning and Landslide Risk Monitoring System in NER  
**Release Baseline**: `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Verification Date**: September 13, 2026  
**Freeze Status**: **FROZEN WITH WARNINGS**  
**Working Directory**: `E:\landslide - Copy\landslide - Copy`  

---

## 1. RUNTIME SPECIFICATION & ENVIRONMENT

* **Repository Path**: `E:\landslide - Copy\landslide - Copy`
* **Python Executable**: `C:\Users\hp\AppData\Local\Python\bin\python.exe` (or `py` launcher pointing to Python 3.14.0 64-bit)
* **Operating System**: Microsoft Windows 11 Workstation (AMD64)
* **Core Libraries**: `numpy 2.5.2`, `scipy 1.18.1`, `scikit-learn 1.9.0`, `h5py 3.16.0`, `xgboost 3.4.1`, `rasterio 1.5.1`, `shapely 2.1.2`, `requests 2.34.2`, `cryptography 50.0.1`
* **Deployment Topology**: 100% Local-First / Local Replay (Zero Cloud, Zero Paid APIs, Zero Fabricated Telemetry)

---

## 2. PRE-DEMONSTRATION VERIFICATION COMMANDS

Before presenting to evaluators or judges, run the automated verification suites from PowerShell:

```powershell
# Step 1: Change to working directory
cd "E:\landslide - Copy\landslide - Copy"

# Step 2: Execute the Judge Demonstration Reproducibility Suite (53 checks)
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_judge_demo_reproducibility.py

# Expected Output:
# JUDGE DEMO REPRODUCIBILITY SUITE SUMMARY: 53/53 CHECKS PASSED
# ALL JUDGE DEMONSTRATION REPRODUCIBILITY CHECKS PASSED PERFECTLY!

# Step 3: Execute the End-to-End Demo Workflow Suite (44 checks)
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_end_to_end_demo_workflow.py

# Expected Output:
# E2E DEMO WORKFLOW SUITE SUMMARY: 44/44 CHECKS PASSED
# ALL END-TO-END DEMONSTRATION WORKFLOW CHECKS PASSED PERFECTLY!
```

---

## 3. SERVER STARTUP PROCEDURE

Start the standalone multi-threaded REST server and UX4G live dashboard:

```powershell
# Start local server on default port 8000
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" server.py
```

Console output upon successful initialization:
```text
================================================================================
NER-SAFE LIVE MULTI-SOURCE MONITORING SERVER (AUTHENTICATED) STARTED
  URL: http://localhost:8000
  Live Homepage: http://localhost:8000/
  Monitoring API: http://localhost:8000/api/monitoring/status
  Auth API:       http://localhost:8000/api/auth/me
  Hotspots API:   http://localhost:8000/api/monitoring/hotspots
  Citizen API:    http://localhost:8000/api/reports
================================================================================
```

* **Actual Port**: `8000` (configurable via `PORT` environment variable if desired)
* **Browser Access URL**: `http://localhost:8000`

---

## 4. EXACT STEP-BY-STEP JUDGE DEMONSTRATION WALKTHROUGH (3–5 MINUTES)

### Step 1: Digital India UX4G Interface & Zero-Emoji Compliance
1. Open Google Chrome or Microsoft Edge and navigate to `http://localhost:8000`.
2. Observe the interface design:
   * Professional Digital India UX4G 3.0 government styling (Primary Navy `#1351A3`, crisp vector cards, CARTO Positron map).
   * **Strict Zero-Emoji Rule**: Exactly 0 Unicode emojis in the document object model; 100% clean SVG vector iconography.

### Step 2: Operational Mode Freshness Safety
1. Look at the primary **OPERATIONAL ASSESSMENT** header card.
2. Verify that **Current Risk** is explicitly displayed as:
   ```text
   CURRENT RISK: NOT AVAILABLE
   Reason: No qualifying fresh observations
   ```
3. Explain the scientific design decision to the judges:
   > *"NER-SAFE strictly enforces an anti-masquerade rule: when qualifying fresh satellite observations (NASA GPM IMERG <6h revisit, NASA SMAP L3 <24h revisit) are unavailable or stale, the system never presents a previous risk score or historical demo calculation as current risk, and never assumes missing data equals low risk."*
4. Inspect the **Live Ingestion Feeds** cards:
   * Point out the honest authentication indicators: Copernicus CDSE requires client credentials for full GRD radar downloads; IMD AWS weather requires an institutional MoU agreement.

### Step 3: Entering Controlled Demo / Replay Mode
1. In the dashboard header or the dedicated **E2E Demonstration Workflow Card** (`#e2eDemoWorkflowCard`), click **Switch to Demo / Replay Mode**.
2. Notice the UI state transition:
   * Visual badge changes to `MODE: DEMO_REPLAY`.
   * Data source tag explicitly identifies `DATA SOURCE: LOCAL_REPLAY`.
   * Non-operational disclaimer appears: *"Historical replay scenario for controlled evaluation. Does not represent current live conditions."*

### Step 4: Selecting Hotspot EVT-MEG-001 (Shella, Meghalaya)
1. Select target hotspot **EVT-MEG-001** from the hotspot dropdown or click the Shella marker on the Leaflet map.
2. Note the hotspot geomorphic location:
   * **Nearest Settlement**: Shella
   * **District**: East Khasi Hills
   * **State**: Meghalaya
   * **Coordinates**: 25.1837°N, 91.6421°E
   * **Historical Observation Timestamp**: `2024-05-28T06:00:00Z` (Cyclone Remal event window)

### Step 5: Verifying the Deterministic 0.7055 Fused Risk Score
1. Click **Execute Deterministic Demonstration**.
2. Verify the mathematical reconciliation table:
   $$\text{Fused Risk} = 0.40 \times 0.6869 + 0.30 \times 0.9217 + 0.20 \times 0.7714 + 0.10 \times 0.0000 = 0.7055$$
   * **Component 10 Calibrated Susceptibility**: `0.6869` (Weight: 40%)
   * **Precipitation Anomaly (NASA GPM)**: `0.9217` (Weight: 30%)
   * **Soil Moisture Saturation (NASA SMAP)**: `0.7714` (Weight: 20%)
   * **Satellite Surface Change (Sentinel-2/1)**: `0.0000` (Weight: 10%)
   * **Fused Risk Score**: **`0.7055`**
   * **Assigned Tier**: **`CRITICAL`** (Threshold $\ge 0.65$)

### Step 6: Visualizing D8 Flow Paths and Runout Corridors
1. On the map controls, ensure **D8 Flow Paths** and **Runout Corridors** checkboxes are enabled.
2. Observe the map rendering:
   * **D8 Steepest Descent Drainage Line**: Cyan line descending along topography. Length: **`267.4 m`**, Elevation Drop: **`73.0 m`**.
   * **Scientific Disclaimer**: Highlight that this represents the predicted primary drainage descent based on SRTM 30m DEM, not a guaranteed exact future slide trajectory.
   * **Empirical Runout Corridor**: Red-orange polygon footprint enveloping **`29,264.6 m²`**.

### Step 7: Showing Exposed Infrastructure Consequence
1. Open the **Consequence & Lifeline Impact** panel.
2. Verify intersected assets:
   * **Exposed Road Segments**: **`2`** segments intersected.
   * **Exposed Road Length**: **`208.4 m`** of roadway within the empirical runout corridor.
   * Clarify: Exposure analysis is downstream consequence modelling and is strictly isolated from ML feature training.

### Step 8: Showing Common Alerting Protocol (CAP) Advisory
1. Click **View CAP Bulletin**.
2. Inspect the ITU-T CAP v1.2 advisory payload:
   * **Identifier**: `NER-SAFE-CAP-EVT-MEG-001`
   * **Status Tag**: **`DEMO / LOCAL TEST`**
   * **Delivery Notice**: Explicitly states *"Local demonstration test advisory; strictly zero public SMS / SACHET broadcast transmission"*.

### Step 9: Showing Citizen Evidence Moderation & Model Isolation
1. In the **Citizen Observations** tab, locate demonstration ground report `REP-20260912-MEG-014` (or `REP-20260913-MEG-002`).
2. Point out:
   * Clear label: *"Supporting qualitative ground observation; isolated from ML models"*.
   * Field officer verification status.
   * **Retraining Safeguard**: `model_retraining_triggered: false` is hard-enforced. Ground observations corroborate emergency response but never retrain or bias C10 Random Forest or C15 XGBoost models.

### Step 10: Returning to Operational Mode & Anti-Contamination Check
1. Click **Return to Operational Mode**.
2. Confirm the system state:
   * The live operational card immediately returns to `CURRENT RISK: NOT AVAILABLE`.
   * The historical score `0.7055` did not bleed into the live operational assessment slot.

---

## 5. SHUTTING DOWN THE SERVER

To gracefully terminate the local server process:
* Press `Ctrl + C` in the PowerShell console running `server.py`.
* Output will confirm:
  ```text
  Server shutting down.
  ```

---

## 6. VERIFYING RELEASE MANIFEST INTEGRITY

To verify that all 101 protected release artifacts on disk match their certified SHA-256 hashes:

```powershell
# Run the automated manifest integrity validator
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" -c "
import os, json, hashlib

WORKSPACE = r'E:\landslide - Copy\landslide - Copy'
manifest_path = os.path.join(WORKSPACE, 'NER_SAFE_RELEASE_MANIFEST.json')

with open(manifest_path, 'r', encoding='utf-8') as f:
    m = json.load(f)

print(f'Verifying {len(m[\"protected_artifacts\"])} protected artifacts...')
mismatches = 0
for item in m['protected_artifacts']:
    norm_path = item['path'].replace('/', os.sep)
    full_path = os.path.join(WORKSPACE, norm_path)
    if not os.path.exists(full_path):
        print(f'MISSING: {norm_path}')
        mismatches += 1
        continue
    h = hashlib.sha256()
    with open(full_path, 'rb') as fp:
        while chunk := fp.read(65536):
            h.update(chunk)
    digest = h.hexdigest()
    if digest != item['sha256']:
        print(f'HASH MISMATCH: {norm_path}')
        print(f'  Expected: {item[\"sha256\"]}')
        print(f'  Got:      {digest}')
        mismatches += 1

if mismatches == 0:
    print('ALL 101 PROTECTED ARTIFACTS VERIFIED: 100% SHA-256 INTEGRITY CONFIRMED!')
else:
    print(f'FAILED: {mismatches} mismatches detected.')
"
```
