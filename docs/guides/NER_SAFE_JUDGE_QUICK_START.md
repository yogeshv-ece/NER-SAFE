# NER-SAFE: JUDGE DEMONSTRATION QUICK-START GUIDE

**Release Baseline**: `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Deployment**: 100% Local-First / Zero Cloud / Standalone  
**Working Directory**: `E:\landslide - Copy\landslide - Copy`  

---

## START
From PowerShell in the project directory:
```powershell
.\start_nersafe_judge_demo.ps1
```
*(Alternative direct launch: `py server.py`)*

---

## OPEN
Open your web browser (Google Chrome or Microsoft Edge):
```text
http://localhost:8000
```

---

## OPERATIONAL DEMO (What to Show First)
1. Point out the top header: **MODE: OPERATIONAL**.
2. Point out the primary risk indicator:
   ```text
   CURRENT RISK: NOT AVAILABLE
   Reason: No qualifying fresh observations
   ```
3. **Core Message for Judges**:
   > *"NER-SAFE strictly prohibits historical data or old demo scores from masquerading as current operational risk. When qualifying fresh feeds (<6h GPM rainfall, <24h SMAP soil moisture) are unavailable or stale, the system reports NOT AVAILABLE rather than manufacturing a false sense of safety."*
4. Point out the **Digital India UX4G 3.0** aesthetic with **EXACTLY ZERO EMOJIS** (100% clean SVG vector icons).

---

## DEMO / REPLAY (How to Enter It)
1. Click the **Switch to Demo / Replay Mode** button on the dashboard header or inside the **E2E Demonstration Workflow Card**.
2. Notice the explicit state transition:
   * **Badge**: `MODE: DEMO_REPLAY`
   * **Data Source**: `LOCAL_REPLAY`
   * **Disclaimer**: *"Historical replay scenario for controlled evaluation. Does not represent current live conditions."*

---

## HOTSPOT
Select target hotspot from dropdown or map:
* **Hotspot ID**: `EVT-MEG-001`
* **Settlement**: Shella
* **District & State**: East Khasi Hills, Meghalaya
* **Historical Event**: Cyclone Remal (`2024-05-28T06:00:00Z`)

---

## EXPECTED REPLAY (Deterministic Result)
Click **Execute Deterministic Demonstration**:
* **Fused Risk Score**: `0.7055`
* **Risk Tier**: `CRITICAL` (Threshold $\ge 0.65$)
* **Four-Factor Breakdown**:
  $$\text{Risk} = 0.40(0.6869) + 0.30(0.9217) + 0.20(0.7714) + 0.10(0.0000) = 0.7055$$

---

## D8 FLOW PATH
* **Length**: `267.4 m`
* **Elevation Drop**: `73.0 m`
* **Scientific Note**: *"Predicted primary drainage descent based on SRTM 30m DEM; not a guaranteed future trajectory."*

---

## RUNOUT CORRIDOR
* **Footprint Area**: `29,264.6 m²`
* **Visual**: Rendered as a distinct red-orange empirical runout envelope on the map.

---

## EXPOSED ROADS & INFRASTRUCTURE
* **Exposed Road Segments**: `2`
* **Exposed Road Length**: `208.4 m`
* **Scientific Note**: *"Exposure is consequence analysis and strictly isolated from ML feature training."*

---

## CAP ADVISORY
* **Status**: `DEMO / LOCAL TEST`
* **Identifier**: `NER-SAFE-CAP-EVT-MEG-001`
* **Delivery Notice**: *"Local demonstration test advisory; strictly zero public SMS / SACHET broadcast transmission."*

---

## CITIZEN EVIDENCE & MODERATION
* **Report ID**: `REP-20260912-MEG-014` / `REP-20260913-MEG-002`
* **Nature**: Supporting qualitative ground observation for civil defense moderators.
* **ML Retraining Isolation**: `model_retraining_triggered: false` hard-enforced. Citizen observations never automatically retrain or bias ML models.

---

## OFFLINE LIMITATION
* **Basemap Tiles**: In an air-gapped / offline environment without internet access, vector layers (hotspots, D8 flow paths, runout corridors, roads) render accurately over a clean neutral grid. The system does not claim offline raster basemaps.

---

## STOP
To stop the local server:
* Switch to the console window and press `Ctrl + C`.

---

## FAILURE RECOVERY CHECKS

| Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| **Port 8000 is busy** | An orphaned Python process is still bound to port 8000. | Run `.\start_nersafe_judge_demo.ps1` (it auto-terminates old instances) or launch with `.\start_nersafe_judge_demo.ps1 -Port 8021`. |
| **Server fails to start** | Python path not found or missing standard library module. | Run directly with `py server.py` or verify Python with `py --version`. |
| **Current Risk is NOT AVAILABLE** | Normal operational behavior when feeds are stale. | **Do not panic!** This is the intended operational safety behavior. Switch to **Demo / Replay** to show deterministic scoring. |
| **Demo endpoint returns error** | Hotspot ID not selected or query parameter omitted. | Ensure `hotspot_id=EVT-MEG-001` is selected in the UI or test query. |
| **Basemap is blank / neutral grid** | Workstation is offline / air-gapped. | Expected behavior. Point out that all local vector overlays (flow paths, corridors, hotspots) are 100% locally computed and visible. |
| **Browser displays old UI state** | Browser aggressively cached previous page assets. | Press `Ctrl + Shift + R` (Hard Reload) in Chrome/Edge to refresh cleanly without cache. |

> [!CAUTION]
> **What NOT to do during failure recovery:**
> * DO NOT delete any `.tif`, `.geojson`, or `.csv` files.
> * DO NOT attempt to reinstall Python or packages.
> * DO NOT retrain or modify the machine learning models.
> * DO NOT change freshness thresholds.
