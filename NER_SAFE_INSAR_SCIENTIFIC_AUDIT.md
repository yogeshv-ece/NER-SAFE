# NER-SAFE: Sentinel-1 IW Repeat-Pass InSAR Scientific Audit Report

**Release Lineage:** `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Execution Timestamp:** `2026-09-14T07:42:00Z`  
**Security Classification:** RESTRICTED LOCAL RESEARCH PROTOTYPE (Zero Credentials Exposed)  
**Evaluated Target:** Sentinel-1 IW SLC Repeat-Pass InSAR Pipeline & Products  
**Final Scientific Judgement:** `INSAR_SCIENTIFIC_VALIDATION_FAILED` (Initial Uncorrected Products) / `INSAR_SCIENTIFIC_VALIDATION_PENDING` (Overall Multi-Temporal Evidence Integration)

---

## 1. Real Input SLC Identification

The audit verified authentic Level-1 Sentinel-1 Interferometric Wide (IW) Single Look Complex (SLC) products acquired from the Copernicus Data Space Ecosystem (CDSE) S3 repository:

```text
Primary Acquisition (Master Scene):
  Granule ID:      S1D_IW_SLC__1SDV_20260913T235451_20260913T235518_004566_008803_FBA2.SAFE
  Product UUID:    01a90514-8bcd-474e-95c5-692052bd573d
  Sensing Start:   2026-09-13T23:54:51.000Z
  Sensing Stop:    2026-09-13T23:55:18.000Z
  Platform / Track:Sentinel-1D (S1D) / Track 150 (Descending)
  Subswath / Pol:  IW1 / VV

Secondary Acquisition (Slave Scene):
  Granule ID:      S1D_IW_SLC__1SDV_20260901T235450_20260901T235517_004391_0081E8_631B.SAFE
  Product UUID:    87f4b70b-574d-4027-87a5-5000ae28e8b9
  Sensing Start:   2026-09-01T23:54:50.000Z
  Sensing Stop:    2026-09-01T23:55:17.000Z
  Platform / Track:Sentinel-1D (S1D) / Track 150 (Descending)
  Subswath / Pol:  IW1 / VV

Pair Baseline Geometry:
  Temporal Baseline:          12.0 days (Optimal repeat-pass cycle)
  Perpendicular Baseline B_perp: 117.11 m (Optimal; <= 150 m critical limit)
  Spatial Overlap Ratio:      99.8%
```

---

## 2. SLC Data Integrity & Authenticity

Local files in [`NER_SAFE_DATA/SENTINEL1/SLC/`](file:///e:/landslide%20-%20Copy/landslide%20-%20Copy/NER_SAFE_DATA/SENTINEL1/SLC/) were independently audited against cryptographic SHA-256 acquisition manifests:
- `2026-09-13/manifest.safe`: `931ec30139258bd21112504304ed5260f3ca32155c98b3fd14c5c35bbd9cc06a` (**MATCH**)
- `2026-09-13/measurement/*.tiff` (1,146,389,672 bytes): `6b4fa516b838e695539f252972fe9f7f6b41619019965828822f9a645ab69319` (**MATCH**)
- `2026-09-01/manifest.safe`: `62d09193721200cdcc78bbb44e916d29d01df0e881e26182ea84d6fd5c7434ac` (**MATCH**)
- `2026-09-01/measurement/*.tiff` (1,146,389,672 bytes): `fce61ffa8d5122569121d87df57ce2709b8f17a5bdff46095e97828e61cff974` (**MATCH**)

Zero synthetic files, zero mock datasets, and zero altered bytes exist in the inputs.

---

## 3. Complex-Data Interpretation

Direct header inspection of the measurement TIFFs using `rasterio` verified:
- **Driver:** `GTiff`
- **Data Type:** `complex_int16` (16-bit signed integer In-phase $I$ and Quadrature $Q$ components)
- **Dimensions:** Exactly $21,282\text{ samples} \times 13,464\text{ lines}$ per swath
- **Interpretation Check:** Reading into NumPy yields complex arrays (`complex64`, e.g. `58.0 + 219.0j`). The data are **strictly NOT interpreted as real-valued scalar rasters**.
- **Amplitude Statistics:**
  - Primary Scene: Mean Amplitude = `122.4`, Max Amplitude = `26,894.2`
  - Secondary Scene: Mean Amplitude = `119.8`, Max Amplitude = `27,411.0`

---

## 4. Polarization Verification

- Both source products are dual-polarization (`VV+VH`).
- The acquired files and annotations are strictly **IW1 VV**.
- Annotation XML tags: `<polarisation>VV</polarisation>` and `<swath>IW1</swath>` in both products.
- **Verification:** Both scenes use identical co-polarization (`VV`). Zero accidental `VV/VH` cross-polarization mixing exists.

---

## 5. Burst Selection & Framing

From direct inspection of the annotation XMLs:
- **Total Bursts in Swath:** 9 bursts (indices 0 to 8).
- **Burst Dimensions:** `linesPerBurst = 1496`, `samplesPerBurst = 21282`.
- **Selected Bursts:** Bursts 2 to 6 (inclusive, 5 bursts total).
  - Lines: `2992` to `10472` ($5 \times 1496 = 7,480\text{ lines}$).
  - Samples: `0` to `21282`.
- **Burst Timing Compatibility:**
  - Burst 2: `2026-09-01T23:54:57.294` vs `2026-09-13T23:54:57.910` ($\Delta t = 0.615\text{ s}$)
  - Burst 6: `2026-09-01T23:55:08.324` vs `2026-09-13T23:55:08.938` ($\Delta t = 0.613\text{ s}$)
- **Coverage:** Spans Northern Shillong Plateau ($25.88^\circ\text{N}$) through East Khasi Hills / Shella / Cherrapunji down to the Bangladesh plains border ($24.89^\circ\text{N}$).

---

## 6. Co-Registration Diagnostics

- **Implemented Algorithm:** 2D cross-correlation peak on an amplitude patch ($512 \times 512$) located at line 1,000, sample 5,000.
- **Estimated Shifts:** Azimuth shift $\Delta\text{az} = -2\text{ px}$, Range shift $\Delta\text{rg} = -27\text{ px}$.
- **Scientific Audit Finding:**
  - A single global shift was applied to the entire $7,480 \times 21,282$ array.
  - In Sentinel-1 TOPSAR, the Doppler centroid frequency varies rapidly with azimuth ($\sim 5,200\text{ Hz/s}$ Doppler rate). To prevent phase discontinuities across burst boundaries, azimuth co-registration requires **Enhanced Spectral Diversity (ESD)** with sub-pixel precision of **0.001 pixel**.
  - A single integer cross-correlation offset provides coarse subswath alignment but leaves residual azimuth phase ramps across burst overlap seams.

---

## 7. Interferogram Mathematics

- **Complex Product:** $I = S_1 \cdot S_2^*$ (Primary $S_1$ multiplied by the complex conjugate of Secondary $S_2$).
- **Ordering:** Master = `2026-09-13`, Slave = `2026-09-01`.
- **Multi-looking:** $4\text{ azimuth} \times 16\text{ range}$ spatial averaging producing a $1,870 \times 1,330$ grid ($2,487,100$ pixels).
- **Wrapped Phase:** $\phi = \text{arctan2}(\text{Im}(I), \text{Re}(I)) \in [-\pi, +\pi]$.

---

## 8. Coherence Diagnostics & Spatial Statistics

- **Mathematical Formulation:**
  $$\gamma = \frac{\left|\sum S_1 S_2^*\right|}{\sqrt{\sum |S_1|^2 \sum |S_2|^2}} \in [0.0, 1.0]$$
- **Evaluated Coherence Statistics:**
  - Mean: `0.1818` | Median: `0.1697`
  - High Coherence ($\gamma \ge 0.35$): **163,415 pixels (6.57%)**
  - Low Coherence ($\gamma < 0.35$): **2,323,685 pixels (93.43%)**
- **Spatial Structure:**
  - The 6.57% coherent pixels form **113,572 isolated spatial islands**.
  - The largest single connected component contains only **660 pixels (0.40% of coherent pixels)**.
  - 93.43% of the scene is dense subtropical forest decorrelated by monsoon moisture and leaf motion over the 12-day interval.

---

## 9. Low-Coherence Quality Mask Validation

- Strict Rule: $\gamma \ge 0.35$ required for valid displacement.
- Validation Check:
  - `insar_quality_mask.tif` strictly equals `(insar_coherence.tif >= 0.35)`: **TRUE (100% pixel match)**.
  - `insar_los_displacement.tif` NaNs strictly equal `(insar_coherence.tif < 0.35)`: **TRUE (100% pixel match)**.
- Invariant Upheld: Low coherence is treated strictly as **NoData / Uncertainty** and NEVER as zero displacement or low hazard.

---

## 10. Phase Unwrapping Audit (Critical Finding)

Inspection of `unwrap_phase_2d()` in `real_insar_processor.py` revealed:
```python
for r in range(rows):
    unwrapped[r, :] = np.unwrap(wrapped_phase[r, :])
col_grad = np.unwrap(unwrapped[:, cols // 2])
col_offset = col_grad - unwrapped[:, cols // 2]
unwrapped += col_offset[:, np.newaxis]
```

### Numerical Defect Identified:
1. The unwrapping function integrates phase along horizontal rows (1D `np.unwrap`).
2. Because 93.43% of pixels are decorrelated noise with random phase $[-\pi, \pi]$, row-wise 1D integration walks through extensive noise corridors, accumulating fictitious $2\pi$ wrap errors ($28\text{ mm}$ each) across the width of the image.
3. Across 1,330 columns, cumulative wrap drift reaches $\pm 120$ cycles ($\approx \pm 3,400\text{ mm}$).
4. This is the **exact numerical cause** of the extreme displacement values ($-490\text{ mm}$ to $+3449\text{ mm}$).
5. The extreme values are **phase unwrapping integration artifacts over low-coherence gaps**, not real ground motion.

---

## 11. Topographic Phase Removal Audit

- **Formula Used:**
  $$\phi_{\text{topo}} = -\frac{4\pi}{\lambda} \frac{B_\perp}{R \sin\theta} h$$
  Where $\lambda = 0.05546576\text{ m}$, $B_\perp = 117.11\text{ m}$, average slant range $R = 850\text{ km}$, incidence angle $\theta = 34^\circ$, and $h$ sampled from 30m SRTM DEM.
- **Topographic Scale Factor:** $k_{\text{topo}} = -0.0565\text{ rad/m}$.
- **Magnitude:** For elevation ranging from 20m (plains) to 1,900m (Shillong peak), $\Delta\phi_{\text{topo}} \approx 106\text{ radians}$ ($\approx 17$ fringes).
- **Assessment:** Topographic phase was correctly formulated and subtracted; however, regional slant-range variations across the swath were approximated by a single mean range.

---

## 12. Orbit Data Provenance

- **Source:** On-board GPS/GNSS orbit state vectors embedded in the Sentinel-1 SAFE annotation XML `<orbitList>`.
- **Count:** 16 state vectors in primary (`2026-09-13`), 17 state vectors in secondary (`2026-09-01`), sampled at 10-second intervals.
- **Interpolation:** 5th-order Lagrange polynomial fitting.
- **Provenance Truth:** These are **product orbit metadata** (restituted downlink navigation solution), not final post-processed Precise Orbit Ephemerides (`AUX_POEORB`, which are published by ESA ~20 days after sensing). Residual baseline errors contribute a long-wavelength orbital phase ramp across the scene.

---

## 13. Phase-to-LOS Displacement Conversion

- **Formula:**
  $$d_{\text{LOS}} = -\frac{\lambda}{4\pi} (\phi_{\text{diff}} - \phi_{\text{ref}})$$
  Where $\lambda = 0.05546576\text{ m}$.
- **Scale Factor:** $-\frac{\lambda}{4\pi} = -0.0044138\text{ m/rad} = -4.4138\text{ mm/rad}$.
- **Units:** Raster stored as Float32 in meters.
- **Convention:** Positive $d_{\text{LOS}}$ represents movement towards the satellite; negative represents movement away.

---

## 14. Reference Area Validation (Critical Finding)

- **Selected Reference Point:** $25.572^\circ\text{N}, 91.881^\circ\text{E}$ (Precambrian bedrock, Shillong Plateau).
- **Actual Subswath Extent:** Longitude $90.573^\circ\text{E}$ to $91.604^\circ\text{E}$.
- **Audit Finding:**
  - $91.881^\circ\text{E}$ is **28.5 km EAST of the subswath boundary** (located in subswath IW2).
  - In `real_insar_processor.py`, `np.clip` forced the column index to the eastern image edge (`col = 1329`).
  - At `row=588, col=1329`, the coherence is **0.0000** (completely decorrelated radar margin).
  - **Verdict:** `REFERENCE_AREA_INVALID`. The initial reference calibration was anchored to an incoherent edge pixel rather than stable bedrock.

---

## 15. Audit of Extreme Displacement Values

- Initial Statistics: Min = `-490.26 mm`, Max = `+3449.23 mm`, Mean = `+805.52 mm`.
- Location of Max ($+3449\text{ mm}$): `row=1334, col=22` (western edge of raster, 219 km from reference).
- Location of Min ($-490\text{ mm}$): `row=810, col=1273` (eastern side).
- **Causality:** The extreme values are explained by:
  1. Horizontal 1D unwrapping error drift across 113,572 decorrelated forest gaps.
  2. Uncompensated linear orbital phase ramp across the 100 km subswath.
  3. Reference point anchored to an out-of-swath, zero-coherence margin.
  4. Atmospheric delay gradient across the Meghalaya escarpment.

---

## 16. Atmospheric & Non-Tectonic Phase Caveat

> [!WARNING]
> **Mandatory Scientific Disclaimer**  
> Single-pair repeat-pass Sentinel-1 InSAR in the tropical monsoon environment of Meghalaya observes the sum of ground displacement, tropospheric water vapor delay gradients, orbital baseline residuals, and phase unwrapping errors.  
> Differential atmospheric delay across the Cherrapunji/Mawsynram escarpment frequently exceeds $10\text{ to }20\text{ cm}$ of apparent LOS shift during the monsoon.  
> **Under no circumstances should single-pair differential phase be interpreted directly as landslide movement without multi-temporal Persistent Scatterer (PSI) stacking or external GACOS atmospheric correction.**

---

## 17. Corrected Outputs (Non-Destructive)

As mandated by Step 22, the original files were preserved untouched, and corrected rasters were generated separately addressing the reference anchor and orbital ramp:

1. **In-Swath Coherent Bedrock Anchor:** Located at $25.8171^\circ\text{N}, 91.5803^\circ\text{E}$ (Northern Shillong Plateau quartzite within IW1), where coherence is **1.0000**.
2. **Orbital Ramp Removal:** 2D planar trend estimated over coherent bedrock pixels was subtracted.
3. **Corrected Files Generated in [`NER_SAFE_DATA/SENTINEL1/`](file:///e:/landslide%20-%20Copy/landslide%20-%20Copy/NER_SAFE_DATA/SENTINEL1/):**
   - `insar_coherence_corrected.tif`
   - `insar_los_displacement_corrected.tif`
   - `insar_unwrapped_phase_corrected.tif`
   - `insar_quality_mask_corrected.tif`
4. **Corrected Displacement Statistics:**
   - Min: `-1820.17 mm`
   - Max: `+1693.31 mm`
   - Mean: `-567.36 mm`
   - Displacement at Bedrock Anchor: `0.00 mm`

---

## 18. Google Drive Cloud Archive Status

- **API v3 Cloud Storage:** Verified connected to 5 TB Google Drive account **Yogesh V**.
- **Archive Status:** Complete set of InSAR persistent rasters, metadata records, SLC XML annotations, and full 1.09 GB measurement TIFFs (2.33 GB total) verified in `NER-SAFE-DATA/` (Remote IDs recorded in `NER_SAFE_DATA/archive_manifest.json`).
- **Retention Policy:** `LOCAL_RETENTION_POLICY = KEEP`. All local files on `E:` preserved.

---

## 19. Verification Test Suite & Baseline Audit

- `test_google_drive_archive.py`: **7/7 PASS**
- `test_insar_s3_real_pipeline.py`: **11/11 PASS**
- `test_live_observation_to_heatmap.py`: **9/9 PASS**
- `test_judge_demo_smoke.py`: **38/38 PASS**
- Combined Satellite & InSAR Suite: **56/56 PASS**
- Protected Baseline Manifest Audit (`run_final_validation.py`): **101/101 PASS (100% exact SHA-256 match)**

---

## 20. Final Scientific Judgement

```text
FINAL STATUS: INSAR_SCIENTIFIC_VALIDATION_FAILED (Initial Uncorrected Displacement Product)
OPERATIONAL INTEGRATION STATUS: INSAR_SCIENTIFIC_VALIDATION_PENDING (Evidence Layer Only)
```

### Scientific Decision Summary:
1. **Acquisition & Coherence:** Fully verified, authentic, and scientifically sound. Real SLC radar samples were correctly acquired, and the multi-look coherence raster honestly reflects Meghalaya's vegetative decorrelation.
2. **Quantitative LOS Displacement:** The initial quantitative displacement raster cannot be validated as a direct numerical trigger for operational landslide risk due to:
   - Out-of-swath reference point clipping.
   - 1D phase unwrapping error accumulation across 113,572 disconnected islands.
   - Lack of sub-burst Enhanced Spectral Diversity (ESD) co-registration.
   - Unmitigated monsoon tropospheric phase delays.
3. **Operational Protection:** The production Random Forest model (C10) and risk weights (`0.40, 0.30, 0.20, 0.10`) remain 100% frozen and untouched. InSAR is classified strictly as an **EXPERIMENTAL OBSERVATIONAL EVIDENCE LAYER** pending multi-temporal Persistent Scatterer Interferometry (PSI) processing.
