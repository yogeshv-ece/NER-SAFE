# NER-SAFE — Sentinel-1 InSAR Processing & Acquisition Guide
**Module**: Component 10 / InSAR Processing Subsystem  
**Target Areas**: Meghalaya (East Khasi Hills / Ri-Bhoi) and Mizoram (Aizawl / Serchhip)  
**Status**: Ready for Execution upon CDSE SLC Ingestion  

---

## 1. Authentication Setup (Copernicus Data Space Ecosystem)
To enable automated discovery and acquisition of Sentinel-1 Level-1 Single Look Complex (IW SLC) products, register for a free account at [dataspace.copernicus.eu](https://dataspace.copernicus.eu/):

1. Log in to the Copernicus Data Space Ecosystem portal.
2. Navigate to **User Profile** -> **OAuth Clients**.
3. Create a new client credential pair with permissions for product catalog search and download.
4. Set the following environment variables in PowerShell:
   ```powershell
   [System.Environment]::SetEnvironmentVariable("CDSE_CLIENT_ID", "<YOUR_CLIENT_ID>", "User")
   [System.Environment]::SetEnvironmentVariable("CDSE_CLIENT_SECRET", "<YOUR_CLIENT_SECRET>", "User")
   ```
5. Verify access in Python:
   ```python
   import os
   print("CDSE ID Set:", bool(os.getenv("CDSE_CLIENT_ID")))
   print("CDSE Secret Set:", bool(os.getenv("CDSE_CLIENT_SECRET")))
   ```

---

## 2. InSAR Pair Selection (`insar_pair_selector.py`)
Run the automated pair evaluation script to audit candidate scenes:
```powershell
py insar_pair_selector.py --audit
```
The script queries CDSE OData API for repeat-pass IW SLC products covering the regional AOIs:
- **Meghalaya Track**: Relative Orbit 136 (Ascending) or Track 63 (Descending).
- **Mizoram Track**: Relative Orbit 121 (Ascending) or Track 48 (Descending).

**Selection Logic**:
- Checks if $\Delta t \le 24$ days (prefers 12-day Sentinel-1 repeat cycle).
- Verifies perpendicular baseline $B_\perp \le 150$ m.
- Confirms VV co-polarization and identical TOPSAR sub-swath/burst footprint.
- Rejects GRD products, cross-track pairs, or scenes with $< 30\%$ AOI overlap.

---

## 3. Execution on 8 GB RAM Machine
Given the Intel Core i3-N305 with 8 GB RAM, running full-frame Sentinel-1 SLC processing will cause memory exhaustion. Follow the optimized burst subset procedure:

1. **Configure Burst Clipping**:
   In `insar_processing.py`, verify `SUBSET_BURST_ONLY = True`.
   ```python
   # Limits processing to bursts covering active monitoring hotspots:
   TARGET_BURSTS = {
       "SHILLONG": {"subswath": "IW2", "burst_idx": [3, 4]},
       "AIZAWL":   {"subswath": "IW1", "burst_idx": [5, 6]}
   }
   ```
2. **Execute Processing Pipeline**:
   ```powershell
   py insar_processing.py --primary <PATH_TO_PRIMARY_SLC.SAFE> --secondary <PATH_TO_SECONDARY_SLC.SAFE>
   ```
3. **Pipeline Stages Executed**:
   - Precise orbit update via ESA POD vectors.
   - TOPS deramp and burst extraction.
   - Enhanced Spectral Diversity (ESD) coregistration.
   - Complex interferogram generation ($S_1 \cdot S_2^*$).
   - Spatial coherence map estimation ($5 \times 5$ window).
   - Goldstein adaptive phase filter ($\alpha = 0.5$).
   - Topographic phase simulation from SRTM 30m DEM and subtraction.
   - SNAPHU phase unwrapping (tile size $512 \times 512$).
   - Range-Doppler geocoding to EPSG:4326.
   - Relative LOS displacement computation ($d_{\text{LOS}} = -\frac{\lambda}{4\pi}\psi_{\text{unwrapped}}$).

---

## 4. Generated Products & Quality Control
The pipeline writes georeferenced GeoTIFFs to `NER_SAFE_DATA/COMPONENT_10/insar/`:
- **`insar_los_displacement.tif`**: Float32 raster representing relative LOS displacement in millimeters ($\pm \text{mm}$). Negative values indicate range increase (movement away from satellite), positive values indicate range decrease (movement toward satellite).
- **`insar_coherence.tif`**: Float32 raster representing interferometric coherence $\gamma \in [0, 1]$.
- **Quality Masking**: All pixels with $\gamma < 0.35$ are masked as `NaN` (NoData). Low coherence is strictly never interpreted as zero movement.

---

## 5. Live Dashboard Integration
Once valid rasters are written to disk:
1. `dynamic_risk_heatmap.py` automatically detects `insar_los_displacement.tif` and `insar_coherence.tif`.
2. The endpoint `GET /api/heatmap/insar` generates the corresponding GeoJSON deformation surface.
3. The live Leaflet dashboard toggles the **InSAR LOS Deformation** layer with the documented Shillong bedrock reference point ($25.572^\circ\text{ N}, 91.881^\circ\text{ E}$).
