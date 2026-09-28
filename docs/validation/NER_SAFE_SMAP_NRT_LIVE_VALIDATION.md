# NER-SAFE — NASA SMAP SPL2SMP_NRT LIVE OPERATIONAL VALIDATION REPORT
**System**: NER-SAFE — AI-Based Early Warning and Landslide Risk Monitoring System in NER India  
**Subsystem**: Multi-Source Environmental Ingestion — NASA SMAP Soil Moisture Channel  
**Validation Date / UTC**: 2026-09-17T05:30:00Z  
**Verification Level**: `LIVE_VERIFIED`  
**Operational Status**: OPERATIONAL & ACTIVE  

---

## 1. Executive Summary & Verification Verdict

The NER-SAFE soil moisture anomaly pipeline has been successfully upgraded from validated historical datasets (`SPL3SMP_E.006`) and static test mockups (`0.58`) to an end-to-end, Near-Real-Time (NRT) operational subsystem driven by NASA's official **SPL2SMP_NRT Version 107** product (Near Real-time SMAP L2 Radiometer Half-Orbit 36 km EASE-Grid Soil Moisture).

All 28 acceptance criteria set forth in the operationalization specification have been satisfied:
- NASA Earthdata authentication verified out-of-the-box via `~/.netrc` credentials.
- Real NASA NSIDC DAAC SPL2SMP_NRT granule discovered and acquired over the North Eastern Region of India.
- Swath HDF5 parsed with bitwise quality control (`retrieval_qual_flag & 0x0001 == 0`) and physical fill value filtering.
- Mathematically defensible spatial resolution harmonization derived between the 36 km NRT radiometer swath and the validated 9 km regional climatological baseline ($0.0727 - 0.4538\text{ cm}^3/\text{cm}^3$).
- Canonical 4-factor risk fusion weights ($0.40 \times \text{Susceptibility} + 0.30 \times \text{Rainfall} + 0.20 \times \text{Soil Moisture} + 0.10 \times \text{Satellite Change}$) and model artifacts remain strictly locked.
- Historical 180-file baseline preserved; 2025-03-18 NASA instrument outage preserved and documented without fabrication.
- Dashboard updated with zero emojis displaying observation timestamp, product, age, AOI mean, anomaly, and valid coverage.

---

## 2. Granule Acquisition & Provenance Forensic Evidence

| Parameter | Operational Audit Value |
| :--- | :--- |
| **Provider** | NASA National Snow and Ice Data Center (NSIDC DAAC) / NASA Earthdata Cloud |
| **Dataset Short Name** | `SPL2SMP_NRT` |
| **Version** | `107` |
| **Product Full Name** | Near Real-time SMAP L2 Radiometer Half-Orbit 36 km EASE-Grid Soil Moisture |
| **Granule Identifier** | `SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001` |
| **Orbit / Pass** | Half-Orbit `62104`, Descending (`D`) |
| **Satellite Platform** | SMAP (Soil Moisture Active Passive) |
| **Instrument** | L-band Radiometer (1.41 GHz) |
| **Observation Timestamp (UTC)** | `2026-09-16T23:53:22.206Z` |
| **Acquisition Timestamp (UTC)** | `2026-09-17T05:07:33.149Z` |
| **Processing Timestamp (UTC)** | `2026-09-17T05:07:35.321Z` |
| **Local Stored Filepath** | `NER_SAFE_DATA/SMAP/raw/nrt/SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001.h5` |
| **Binary File Size** | `1,570,391 bytes` (1.50 MB) |
| **Cryptographic SHA-256 Digest** | `d22d73a3ce65f059eb9b9ecdeccf9fd80c8cf77012558a80d0813f4f44f80c43` |
| **Download Integrity Check** | Verified matching bit-for-bit with SHA-256 calculation |

---

## 3. AOI Extraction & Geolocation

| Dimension | Specification | Observed Observation Swath |
| :--- | :--- | :--- |
| **Authoritative AOI** | Lat $[21.0^{\circ}\text{N}, 27.0^{\circ}\text{N}]$, Lon $[89.0^{\circ}\text{E}, 94.0^{\circ}\text{E}]$ | Meghalaya, Mizoram, Assam, Manipur, Tripura, Nagaland corridors |
| **Coordinate System** | EASE-Grid 2.0 Global Cylindrical (`EPSG:6933`) | Native swath geolocated by cell-center lat/lon vectors |
| **Total Cells in AOI** | 38 swath cells covering the monitored region | 38 cells intersecting bounding polygon |
| **Valid Retrieval Cells** | 38 cells (100.0% valid coverage) | Recommended radiometer quality satisfied across entire swath intersection |
| **Rejected Cells** | 0 cells | Zero fill values or frozen ground occlusions |
| **Valid Fraction** | `1.0` (100.0%) | Exceeds minimum operational quality threshold ($\ge 20\%$) |

---

## 4. Quality Control & Bitwise Filtering

The HDF5 binary was parsed from group `/Soil_Moisture_Retrieval_Data` using official bitwise criteria:

1. **Retrieval Quality Flag (`retrieval_qual_flag`)**:
   - Bit 0 (`0x0001`): NASA official recommended retrieval filter.
   - Requirement: `(retrieval_qual_flag & 0x0001) == 0`.
   - Result: All 38 swath cells satisfied bit 0 = 0.
2. **Surface Exclusion Flag (`surface_flag`)**:
   - Frozen ground and snow/ice guarded via bits 5, 6, 8 (`0x0160`).
   - Tropical summer active status confirmed; no frozen ground or active snow pack present in North-East India.
3. **Physical Range & Fill Values**:
   - Fill value `-9999.0` filtered.
   - Physical bounding: $0.02 \le \theta \le 0.50\text{ cm}^3/\text{cm}^3$.
   - All retrieved cells fell within physically valid volumetric limits.

---

## 5. Soil Moisture Statistics & Baseline Harmonization

### 5.1 Observed Half-Orbit Swath Statistics
- **Mean Volumetric Soil Moisture ($\bar{\theta}$)**: $0.3833\text{ cm}^3/\text{cm}^3$
- **Median Soil Moisture**: $0.3832\text{ cm}^3/\text{cm}^3$
- **Minimum Soil Moisture**: $0.3340\text{ cm}^3/\text{cm}^3$
- **Maximum Soil Moisture**: $0.4418\text{ cm}^3/\text{cm}^3$
- **Standard Deviation**: $0.0271\text{ cm}^3/\text{cm}^3$

### 5.2 Resolution Harmonization Method
NASA SPL2SMP_NRT delivers half-orbit observations at 36 km spatial resolution, whereas the historical baseline uses the validated 9 km daily composite (`SPL3SMP_E.006`). Rather than fabricating synthetic high-resolution data, the operational pipeline maps the 36 km regional mean into a **Relative Saturation Index** based on regional climatological limits derived from the 9 km baseline rasters:

$$\text{Anomaly Score} = \text{clip}\left(\frac{\bar{\theta}_{\text{obs}} - \bar{\theta}_{\text{base,min}}}{\bar{\theta}_{\text{base,max}} - \bar{\theta}_{\text{base,min}}}, 0.0, 1.0\right)$$

- Regional Baseline Minimum ($\bar{\theta}_{\text{base,min}}$): $0.0727\text{ cm}^3/\text{cm}^3$
- Regional Baseline Maximum ($\bar{\theta}_{\text{base,max}}$): $0.4538\text{ cm}^3/\text{cm}^3$
- Effective Climatological Range ($\Delta\theta$): $0.3811\text{ cm}^3/\text{cm}^3$
- Operational Anomaly:
  $$\text{Anomaly} = \frac{0.3833 - 0.0727}{0.4538 - 0.0727} = \frac{0.3106}{0.3811} = \mathbf{0.8149}$$

---

## 6. Freshness Model & State Machine

| Metric | Recorded Value | Policy Evaluation |
| :--- | :--- | :--- |
| **Observation Timestamp** | `2026-09-16T23:53:22Z` | Satellite pass over North-East India |
| **Current Operational Clock** | `2026-09-17T05:30:00Z` | System evaluation time |
| **Observation Age** | 5.6 hours (336 minutes) | Within FRESH threshold ($\le 36.0\text{ hours}$) |
| **Freshness Classification** | `FRESH` | Machine-readable status badge |
| **Ingestion Pipeline Status** | `LIVE_VERIFIED` | Provenance verified from authentic NASA download |

---

## 7. Protected Architecture & Risk Engine Integration

### 7.1 Locked Risk Formula Verification
The risk formula remains strictly intact with four-factor weighted fusion:
$$\text{Risk Score} = 0.40 \times \text{Susceptibility} + 0.30 \times \text{Rainfall Anomaly} + 0.20 \times \text{Soil Moisture Anomaly} + 0.10 \times \text{Satellite Change Flag}$$

- Susceptibility weight: `0.40` (Locked)
- Rainfall weight: `0.30` (Locked, NASA GPM IMERG NRT)
- Soil moisture weight: `0.20` (Locked, NASA SMAP SPL2SMP_NRT: $0.8149$)
- Satellite change flag: `0.10` (Locked, Sentinel-1 SAR / Sentinel-2)

### 7.2 Model & Threshold Preservation
- Production XGBoost: SHA-256 `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c` verified unchanged.
- Risk Thresholds: Critical $\ge 0.65$, High $[0.48, 0.65)$, Moderate $[0.32, 0.48)$, Watch $< 0.32$.
- Historical Baseline: Exactly 180 valid historical HDF5 files preserved in `NER_SAFE_DATA/SMAP/raw/`.
- Missing Date (2025-03-18): Documented as true satellite payload safe-hold; zero synthetic data fabricated.

---

## 8. Database Persistence & API Evidence

### 8.1 SQLite Persistence (`smap_nrt_observations`)
```sql
SELECT id, source_file, quality_status, freshness_status, mean_soil_moisture, anomaly, sha256 
FROM smap_nrt_observations ORDER BY id DESC LIMIT 1;
```
**Database Record Output**:
```json
{
  "id": 1,
  "source_file": "SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001.h5",
  "quality_status": "VALID",
  "freshness_status": "FRESH",
  "mean_soil_moisture": 0.3833,
  "anomaly": 0.8149,
  "sha256": "d22d73a3ce65f059eb9b9ecdeccf9fd80c8cf77012558a80d0813f4f44f80c43"
}
```

### 8.2 REST API Endpoint (`GET /api/smap/latest`)
```json
{
  "source_id": "NASA_SMAP_SPL2SMP_NRT",
  "product": "SPL2SMP_NRT",
  "version": "107",
  "granule_id": "SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001",
  "source_file": "SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001.h5",
  "sha256": "d22d73a3ce65f059eb9b9ecdeccf9fd80c8cf77012558a80d0813f4f44f80c43",
  "observation_time": "2026-09-16T23:53:22.206Z",
  "age_hours": 5.61,
  "freshness_status": "FRESH",
  "quality_status": "VALID",
  "aoi_cells_valid": 38,
  "aoi_cells_total": 38,
  "aoi_valid_fraction": 1.0,
  "sm_mean": 0.3833,
  "anomaly": 0.8149,
  "anomaly_status": "VALID_ANOMALY",
  "status": "LIVE_VERIFIED"
}
```

---

## 9. Dashboard Display & UX4G Compliance

The live monitoring portal (`ner_safe_live_dashboard.html`) was inspected and verified:
- Source Card: `NASA SMAP NRT Radiometer`
- Product: `SPL2SMP_NRT v107`
- Pill Badge: `LIVE_VERIFIED` (`#059669` emerald green)
- Granule ID: `SMAP_L2_SM_P_NRT_62104_D_20260916T235010_N19241_001`
- Observation Time (UTC): `2026-09-16 23:53:22 UTC`
- Age Display: `6h ago (Active Swath)`
- AOI Soil Moisture: `0.3833 cm³/cm³`
- Derived Anomaly: `0.8149 (4-Factor Channel)`
- Valid Coverage: `100.0% Recommended QC`
- **Zero-Emoji Compliance**: Verified 0 emojis present in HTML/CSS/JS (100% clean SVG icons & UX4G typography).

---

## 10. Automated Validation & Regression Test Results

| Test Suite | Command | Total Tests | Passed | Result |
| :--- | :--- | :--- | :--- | :--- |
| **SMAP NRT Pipeline Suite** | `py test_smap_nrt_pipeline.py` | 12 | 12 | **OK** (100% Pass) |
| **Live System Validation** | `py test_live_system.py` | 21 | 21 | **OK** (100% Pass) |
| **XGBoost Production Promotion** | `py test_xgboost_production_promotion.py` | 9 | 9 | **OK** (100% Pass) |

---

## 11. NASA Geolocation Limitation Notice (2026)

NASA NSIDC documentation flags a known geolocation anomaly affecting SMAP Standard and NRT products observed between **14 May 2026** and **28 July 2026** due to star tracker attitude calibration adjustments.
- **Audit Verification**: The live observation acquired by NER-SAFE is from **16 September 2026** (`20260916T235010`), well after the 28 July 2026 anomaly window. Geolocation coordinates in EASE-Grid 2.0 over North-East India are fully validated.

---

## 12. Conclusion & Operational Status

The SMAP subsystem in NER-SAFE is officially certified as:
- **`LIVE_VERIFIED`**: YES (authentic NASA SPL2SMP_NRT granule acquired, parsed, QC filtered, harmonized, persisted to SQLite, and served via REST API and live dashboard).
- **`AUTO_UPDATE_VERIFIED`**: READY (cadence scheduler is fully idempotent, handles deduplication, and suppresses redundant reassessments).
