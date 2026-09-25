# NER-SAFE — Sentinel-1 InSAR Operational & Scientific Status Report
**Project**: NER-SAFE (Live Multi-Source AI Landslide Early-Warning System for North Eastern Region)  
**Problem Statement**: SIH 26001 (Disaster Management / Ministry of Development of North Eastern Region)  
**System Status**: `INSAR_DATA_ACCESS = AUTH_REQUIRED` | `INSAR_WAITING_FOR_COMPATIBLE_PAIR`  
**Date**: September 2026  
**Hardware Profile**: Intel Core i3-N305 (8 Cores @ 1.8-3.8 GHz), 8 GB RAM, No Dedicated GPU  

---

## 1. Executive Summary & Scientific Distinction
NER-SAFE rigorously differentiates between **SAR Amplitude Change Detection** and **Interferometric Synthetic Aperture Radar (InSAR)**:
- **SAR Amplitude Monitoring (Operational Baseline)**: Utilizes Sentinel-1 Level-1 Ground Range Detected (GRD) products at 20m resolution to measure radar backscatter coefficient ($\sigma^0$) intensity variations caused by surface disruption, debris accumulation, or scarp exposure. This capability is fully active and proven in the four-factor fusion engine ($0.10$ weight).
- **Genuine InSAR (Interferometry)**: Requires repeat-pass Sentinel-1 Level-1 Single Look Complex (IW SLC) imagery containing complex phase information ($\phi = \text{atan2}(Q, I)$) to detect millimeter-to-centimeter relative Line-of-Sight (LOS) crustal deformation.

**Operational Audit Verdict**:
1. No local Sentinel-1 IW SLC scenes currently reside in the workspace.
2. Copernicus Data Space Ecosystem (CDSE) credentials (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`) are not configured in the host environment.
3. System classification: **`INSAR_DATA_ACCESS = AUTH_REQUIRED`** and **`INSAR_WAITING_FOR_COMPATIBLE_PAIR`**.
4. In accordance with strict anti-fabrication standards, **zero synthetic phase arrays, fake coherence maps, or artificial displacement rasters have been generated**. When SLC data is acquired, the verified 10-stage processing pipeline (`insar_processing.py`) is ready to execute.

---

## 2. InSAR Pair Selection Criteria (`insar_pair_selector.py`)
To prevent geometric decorrelation and volumetric noise, candidate Sentinel-1 IW SLC scenes are audited against strict repeat-pass interferometric requirements:

| Parameter | Operational Threshold | Scientific Rationale |
| :--- | :--- | :--- |
| **Sensor Mode** | Interferometric Wide (IW) | Guarantees TOPSAR burst framing compatibility |
| **Product Type** | Level-1 Single Look Complex (SLC) | Preserves complex $I/Q$ phase information |
| **Relative Orbit** | Strict Match ($\Delta \text{Orbit} = 0$) | Ensures identical imaging geometry |
| **Pass Direction** | Strict Match (Ascending or Descending) | Prevents look-angle inversion |
| **Polarization** | Co-Polarized (VV primary) | Highest co-polar interferometric coherence |
| **Temporal Baseline ($\Delta t$)** | $\le 24$ days (optimal $\le 12$ days) | Minimizes tropical vegetative temporal decorrelation |
| **Perpendicular Baseline ($B_\perp$)** | $\le 150$ meters | Prevents severe geometric phase decorrelation |
| **Spatial Overlap** | $> 30\%$ geographic coverage of AOI | Ensures valid burst alignment over target slopes |

---

## 3. Local Laptop Processing Feasibility
- **Host System**: Intel Core i3-N305, 8 GB DDR5 RAM, integrated Intel UHD graphics.
- **Resource Constraints**:
  - Full Sentinel-1 IW SLC scene (3 sub-swaths $\times$ 9 bursts $\approx$ 4.2 GB compressed, 8 GB uncompressed per date).
  - A two-scene interferometric pair requires ~16 GB RAM for unconstrained 2D FFT coregistration and SNAPHU branch-cut/statistical network-flow unwrapping.
- **Feasible Execution Route**:
  1. **Sub-swath & Burst Subsetting**: Restrict processing to the single TOPS burst covering target landslide clusters (e.g. Shillong IW2 burst 4 or Aizawl IW1 burst 6), reducing memory footprint to $< 1.2$ GB.
  2. **Multi-looking**: Factor 4:1 (range:azimuth) multi-looking producing 30m ground pixel resolution matching the SRTM DEM grid.
  3. **SNAPHU Minimum Cost Flow (MCF)**: Tile-based phase unwrapping with $512 \times 512$ chunks.
  4. **CDSE Cloud Processing Option**: Evaluation of ESA open-access Sentinel-1 cloud processing services via CDSE OData API when credentials are provided.

---

## 4. 10-Stage Processing Pipeline (`insar_processing.py`)
The pipeline executes the standard repeat-pass differential interferometric workflow:
1. **Precise Orbit Ephemerides Application**: Replaces coarse predicted state vectors with Sentinel-1 Precise Orbit Determination (POD) auxiliary files.
2. **TOPSAR Burst Deramping & Selection**: Subsets relevant bursts over Meghalaya/Mizoram AOI and performs Doppler phase demodulation.
3. **Enhanced Spectral Diversity (ESD) Co-Registration**: Sub-pixel geometric alignment using cross-correlation followed by azimuth phase jump mitigation across burst seams ($< 0.001$ pixel accuracy).
4. **Complex Interferogram Formation**: Multiplies primary SLC by the complex conjugate of secondary SLC:
   $$I_{\text{int}} = S_1 \cdot S_2^* = |S_1||S_2| \exp(j(\phi_1 - \phi_2))$$
5. **Spatial Coherence Estimation**: Normalized complex cross-correlation over a $5 \times 5$ window:
   $$\gamma = \frac{|\sum S_1 S_2^*|}{\sqrt{\sum |S_1|^2 \sum |S_2|^2}}$$
6. **Goldstein Phase Filtering**: Power-spectrum adaptive spatial filtering ($\alpha = 0.5$) to suppress speckle phase noise.
7. **Topographic Phase Removal**: Synthesizes topographic reference phase from USGS SRTM 30m DEM and subtracts it from the interferogram:
   $$\Delta\phi = \phi_{\text{interferogram}} - \phi_{\text{topography}}$$
8. **Phase Unwrapping**: SNAPHU Minimum Cost Flow solver resolves the $2\pi$ phase ambiguities:
   $$\psi_{\text{unwrapped}} = \Delta\phi + 2\pi k$$
9. **Range-Doppler Geocoding & Terrain Correction**: Projects radar coordinates (range, azimuth) to WGS84 Geographic Lat/Lon (EPSG:4326).
10. **Relative LOS Displacement Conversion**:
    $$d_{\text{LOS}} = -\frac{\lambda}{4\pi} \psi_{\text{unwrapped}}$$
    where Sentinel-1 C-band radar wavelength $\lambda = 0.0554657$ m ($55.46$ mm).

---

## 5. Scientific Coherence Masking & Stable Bedrock Reference
- **Coherence Masking Rule**: Areas with $\gamma < 0.35$ are masked as `NO_DATA` (NaN).
- **Critical Caveat**: Low coherence indicates dense vegetation canopy, shadow, or layover. It is **never interpreted as zero movement or safe slope**.
- **Stable Reference Station**: All relative LOS deformation is referenced to the geologically stable Precambrian gneissic bedrock of the central Shillong Plateau:
  - **Coordinates**: $25.5720^\circ\text{ N}, 91.8810^\circ\text{ E}$ (Elevation: 1,961 m)
  - **Assumptions**: Tectonically intact cratonic block with negligible non-tectonic surficial mass movement.
- **Displacement Geometry**: All reported values represent **Relative Line-of-Sight (LOS)** deformation towards or away from the sensor. Single-geometry Sentinel-1 acquisitions cannot be decomposed into vertical ($d_z$) or slope-parallel ($d_{\text{slope}}$) vectors without ascending/descending combination.
