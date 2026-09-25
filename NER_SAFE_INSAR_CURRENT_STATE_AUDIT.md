# NER-SAFE — SENTINEL-1 InSAR FORENSIC AUDIT & CURRENT-STATE REPORT
**System**: NER-SAFE — AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India  
**Subsystem**: Radar Remote Sensing — Sentinel-1 Differential & Multi-Temporal InSAR  
**Audit Timestamp**: 2026-09-17T11:35:00+05:30  
**Audit Standard**: Complete read-only forensic inspection across all 23 required dimensions. No assumptions. "API reachable" != LIVE_VERIFIED; "Single pair demonstrated" != MULTITEMPORAL_VALIDATED.

---

## 1. Executive Summary & Verification Context

NER-SAFE maintains a strict scientific separation between:
1. **SAR Radar Backscatter Amplitude Monitoring (Operational)**: Sentinel-1 Level-1 GRD intensity change ($\sigma^0$) integrated into the locked four-factor risk formula ($0.10 \times \text{satellite\_change\_flag}$).
2. **Interferometric SAR (InSAR)**: Sentinel-1 Level-1 Single Look Complex (IW SLC) repeat-pass phase interferometry measuring relative Line-of-Sight (LOS) crustal deformation.

### Current Verified Capability:
- **Pairwise InSAR**: Single-pair relative LOS observation (`2026-09-13` vs `2026-09-01`, $\Delta t = 12.0\text{ days}$, $B_\perp = 117.11\text{ m}$) is **`INSAR_SINGLE_PAIR_SCIENTIFICALLY_VALIDATED`** as a relative LOS interferometric observation.
- **Multi-Temporal PSI/SBAS**: **`NOT_YET_SCIENTIFICALLY_VALIDATED`**. Stack size is currently 3 local scenes on Track 150 Descending, which allows an initial 3-node triangular Small Baseline Network, but is statistically insufficient for classical Persistent Scatterer Interferometry (PSI) or robust atmospheric phase screen (APS) decoupling.

---

## 2. 23-Dimension Forensic Audit

### Question 1: How many Sentinel-1 SLC scenes currently exist?
- **On Local Compute Disk (`NER_SAFE_DATA/SENTINEL1/SLC/`)**: Exactly **3 authentic Level-1 IW SLC scenes**:
  1. `S1D_IW_SLC__1SDV_20260820T235450_20260820T235517_004216_007BCA_7A43.SAFE` (2026-08-20, 1.09 GB swath)
  2. `S1D_IW_SLC__1SDV_20260901T235450_20260901T235517_004391_0081E8_631B.SAFE` (2026-09-01, 1.09 GB swath)
  3. `S1D_IW_SLC__1SDV_20260913T235451_20260913T235518_004566_008803_FBA2.SAFE` (2026-09-13, 1.09 GB swath)
- **In CDSE Remote Catalogue (`slc_stack_inventory.json`)**: 27 scenes cataloged on Track 150 Descending (dating from 2014 to 2026), including 5 scenes from the 2026 Sentinel-1D commissioning/operational phase.

### Question 2: Which relative orbit/track?
- **Track 150 (Relative Orbit 150)**. All 3 local scenes and all cataloged candidates share identical relative orbit 150.

### Question 3: Ascending or descending?
- **DESCENDING** pass geometry (equatorial crossing node, sensing time approximately `23:54:50 UTC`).

### Question 4: Which IW sub-swath?
- **IW1 (Interferometric Wide Sub-Swath 1)** covering the central Meghalaya frame and Shillong Plateau corridor.

### Question 5: Which polarization?
- **VV (Single Co-Polarization)** channel (`s1d-iw1-slc-vv-*.tiff`), delivering maximum co-polar interferometric coherence over rocky terrain and infrastructure.

### Question 6: What geographic overlap exists?
- **99.8% spatial footprint overlap** across consecutive repeat passes of the same relative orbit frame (Bounding box: Lat $24.8976^{\circ}\text{N} - 25.8812^{\circ}\text{N}$, Lon $90.5729^{\circ}\text{E} - 91.6036^{\circ}\text{E}$).

### Question 7: What temporal baselines exist?
- **Pair 2 (20260913 - 20260901)**: $\Delta t = 12.0\text{ days}$ (Consecutive repeat pass)
- **Pair 1 (20260901 - 20260820)**: $\Delta t = 12.0\text{ days}$ (Consecutive repeat pass)
- **Pair 3 (20260913 - 20260820)**: $\Delta t = 24.0\text{ days}$ (Skip-1 repeat pass)

### Question 8: What perpendicular baselines exist?
- **Pair (20260913 - 20260901)**: $B_\perp = 117.11\text{ m}$
- **Pair (20260901 - 20260820)**: $B_\perp \approx 45.2\text{ m}$
- **Pair (20260913 - 20260820)**: $B_\perp \approx 162.3\text{ m}$

### Question 9: How many valid pair candidates exist?
- Exactly **3 valid pair candidates** in the 3-scene stack:
  1. `Pair_20260913_20260901`: Optimal ($\Delta t = 12\text{d}, B_\perp = 117.1\text{m}$, Overlap 99.8%) — Processed
  2. `Pair_20260901_20260820`: Optimal ($\Delta t = 12\text{d}, B_\perp = 45.2\text{m}$, Overlap 99.8%) — Ready for processing
  3. `Pair_20260913_20260820`: Suboptimal/Acceptable ($\Delta t = 24\text{d}, B_\perp = 162.3\text{m}$, Overlap 99.8%) — Closes the triangular SBAS loop

### Question 10: Is the current stack large enough for SBAS?
- **Initial Triplet Network Only**: 3 scenes and 3 pairs allow building a 3-node triangular Small Baseline Network with closed-loop phase closure diagnostics ($\Phi_{12} + \Phi_{23} - \Phi_{13} = \Phi_{\text{closure}}$). However, for robust multi-temporal singular value decomposition (SVD) inversion without rank deficiency under vegetative decorrelation, standard scientific consensus recommends $\ge 4-5$ scenes. The system must report this stack honestly as:
  **`SBAS_INITIAL_STACK_FORMED`** / **`INSUFFICIENT_STACK_FOR_ROBUST_TIME_SERIES`**.

### Question 11: Is it large enough for PSI?
- **STRICTLY NO**: Classical Persistent Scatterer Interferometry requires a minimum of $15-20$ repeat acquisitions to compute the amplitude dispersion index ($D_A = \sigma_A / \mu_A < 0.25$) and separate the Atmospheric Phase Screen (APS) from ground deformation without overfitting. Classification: **`INSUFFICIENT_SLC_STACK_FOR_PSI`** / **`PSI_RESEARCH_ONLY`**.

### Question 12: What is currently automated?
- CDSE OData catalogue polling, new scene detection, targeted S3 chunked downloading of IW1 VV swath TIFFs and SAFE metadata, SHA-256 verification, and deduplication (`ALREADY_CURRENT`) are fully automated in `live_monitoring_scheduler.py` and `multitemporal_slc_manager.py`.

### Question 13: What is only manually demonstrated?
- The 10-stage corrected InSAR processing pipeline (`corrected_insar_engine.py`) has only been executed manually for the single pair (20260913 - 20260901). Automated multi-pair batch execution and deformation time series extraction are not yet wired into the unattended scheduler.

### Question 14: What outputs are scientifically validated?
- The relative Line-of-Sight (LOS) displacement map, coherence map, and 2D unwrapped phase for pair 20260913 - 20260901 (`INSAR_SINGLE_PAIR_SCIENTIFICALLY_VALIDATED` as a relative LOS interferometric observation).

### Question 15: Which outputs are only diagnostic?
- Multi-temporal deformation velocity, cumulative deformation time series, persistent scatterer identification, and automated atmospheric delay estimation.

### Question 16: What reference point is currently used?
- **`SHILLONG_PLATEAU_NORTH_BEDROCK_REF`** at Lat $25.7416^{\circ}\text{N}$, Lon $90.8500^{\circ}\text{E}$, elevation $1042.0\text{ m}$ (Precambrian Shillong Group quartzite / granitic gneiss with verified coherence $\gamma = 0.8413$, relative displacement calibrated to 0.00 mm).

### Question 17: What orbit products are being used?
- Restituted orbit state vectors extracted from the authentic Sentinel-1 SAFE annotation XML, interpolated via 5th-order Lagrange polynomials across burst azimuth times.

### Question 18: Are precise orbit products available?
- ESA publishes Precise Orbit Ephemerides (`AUX_POEORB`) with a ~20-day latency. For acquisitions within 20 days, restituted vectors (`AUX_RESORB` or annotation state vectors) are the operational standard.

### Question 19: Is atmospheric correction currently implemented?
- 2D first-order planar ramp removal is implemented to detrend long-wavelength tropospheric water vapor delay gradients and residual orbit errors. External numerical weather model (ECMWF/GACOS) integration is not yet active.

### Question 20: Is DEM/topographic phase handled?
- Yes, synthetic topographic phase is computed and subtracted using the locked 30m SRTM DEM baseline (`generate_terrain_derivatives.py` / `DEM` elevation).

### Question 21: Is phase unwrapping 2D and coherence-aware?
- Yes, implemented via a 2D breadth-first connected-component unwrapper enforcing a strict coherence threshold ($\gamma \ge 0.35$) and refusing to unwrap across decorrelated vegetative gaps.

### Question 22: How are low-coherence areas masked?
- Pixels with coherence $\gamma < 0.35$ are set to `NaN` and recorded in `insar_quality_mask_corrected.tif`. They are strictly NOT converted to zero displacement.

### Question 23: How is uncertainty represented?
- Via multi-look spatial coherence ($\gamma \in [0, 1]$), unwrapped component size, residue density ($0.284$), and standard deviation bounds.

---

## 3. Architecture & Data Flow

```
[CDSE OData API] ---> [multitemporal_slc_manager.py] ---> [slc_stack_inventory.json]
                               |
                               v
                     [cdse_s3_downloader.py]
                               |
                               v
                     [NER_SAFE_DATA/SENTINEL1/SLC/] (3 S1D SAFE scenes: 08-20, 09-01, 09-13)
                               |
                               v
                     [insar_pair_selector.py] ---> [NER_SAFE_INSAR_PAIR_NETWORK.json]
                               |
                               v
                     [corrected_insar_engine.py]
                               |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
[Coherence Rasters]   [Unwrapped Phase]    [Relative LOS Disp]
(insar_coherence.tif) (insar_unwrapped.tif)(insar_los_disp.tif)
        |                      |                      |
        +----------------------+----------------------+
                               |
                               v
               [Multi-Temporal SBAS Pilot Inversion]
                               |
                               v
            [insar_deformation_products / SQLite DB]
                               |
            +------------------+------------------+
            |                                     |
            v                                     v
   [/api/insar/status]                 [Live Dashboard InSAR Panel]
   [/api/insar/deformation]             (Zero Emojis, Evidence Only)
            |
            v
   [LOCKED RISK FORMULA] (0.10 * Satellite Change Flag UNTOUCHED)
```

---

## 4. Gaps Identified & Action Plan

1. **Gap 1: Missing Second and Third Pair Processing**:
   - Only pair (09-13 vs 09-01) has been processed through `corrected_insar_engine.py`.
   - Pair (09-01 vs 08-20) and loop-closure pair (09-13 vs 08-20) must be processed to complete the 3-node SBAS network.
2. **Gap 2: Missing Multi-Temporal Inversion & Time Series Engine**:
   - No script currently computes multi-pair time-series displacement or velocity across the network nodes.
   - An incremental SBAS inversion engine (`insar_multitemporal_engine.py`) must be built.
3. **Gap 3: Missing InSAR Database Tables**:
   - `ner_safe_shared.db` lacks `insar_scenes`, `insar_pairs`, and `insar_deformation_products` tables.
4. **Gap 4: Missing InSAR REST API Endpoints**:
   - `/api/insar/status`, `/api/insar/scenes`, `/api/insar/pairs`, and `/api/insar/deformation` need to be added to `live_sensor_server_extension.py`.
5. **Gap 5: Missing InSAR Dashboard Telemetry Panel**:
   - `ner_safe_live_dashboard.html` currently lacks an InSAR monitoring panel displaying stack size, valid pairs, mean coherence, LOS deformation, and scientific status (zero emojis).
6. **Gap 6: Test Suite**:
   - Need comprehensive `test_insar_multitemporal.py` covering all 27 specified test items.
