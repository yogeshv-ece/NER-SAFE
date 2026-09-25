# NER-SAFE — Copernicus Data Space Ecosystem (CDSE) Connectivity & Acquisition Report

**System**: NER-SAFE Live Multi-Source Landslide Risk Early-Warning System  
**Audit Date / Timestamp**: 2026-09-14T05:46:49Z  
**Target Area of Interest (AOI)**: North Eastern Region (Meghalaya & Mizoram focus; $21.0^\circ\text{ N} - 27.0^\circ\text{ N}, 89.0^\circ\text{ E} - 94.0^\circ\text{ E}$)  
**Security & Credential Policy**: Strict zero-leakage perimeter. Zero client secrets, passwords, bearer tokens, or refresh tokens are recorded.

---

## 1. Executive Summary & Verification Matrix

| Verification Gate | Target Service / Interface | Operational Status | Evidence & Metrics |
| :--- | :--- | :---: | :--- |
| **1. CDSE Credential Configuration** | `.env` local environment | **PASS** | Valid non-placeholder `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET` loaded locally. |
| **2. CDSE OAuth2 Authentication** | `identity.dataspace.copernicus.eu` | **PASS** | Client Credentials flow succeeded; valid Bearer token acquired (1800s validity). |
| **3. Sentinel Hub Authentication** | `sh.dataspace.copernicus.eu` | **PASS** | STAC collections accessible: S1-GRD, S2-L2A, S2-L1C, S3, S5P. |
| **4. Sentinel-2 L2A Discovery** | Sentinel Hub STAC Catalog | **PASS** | 5 candidate scenes discovered over Meghalaya AOI (e.g. `S2C_MSIL2A_20260912...`). |
| **5. Sentinel-2 L2A Real Acquisition** | Sentinel Hub Process API | **LIVE_VERIFIED** | **42,228 bytes** multi-spectral TIFF (B04, B08, B03, SCL) acquired and verified. |
| **6. Sentinel-1 GRD Discovery** | Sentinel Hub STAC & CDSE OData | **PASS** | 5 candidate scenes discovered (e.g. `S1D_IW_GRDH_1SDV_20260913...`). |
| **7. Sentinel-1 GRD Real Acquisition** | Sentinel Hub Process API | **LIVE_VERIFIED** | **28,562 bytes** dual-pol (VV/VH) radar backscatter TIFF acquired and verified. |
| **8. Sentinel-1 SLC Discovery** | CDSE OData (`catalogue.dataspace...`) | **PASS** | 15 authentic Level-1 IW SLC scenes discovered intersecting NER AOI. |
| **9. Compatible Repeat-Pass Pairs** | `InSARPairSelector` baseline engine | **PASS** | Multiple valid pairs identified ($\Delta t = 12\text{d}, 24\text{d}$; Relative Orbits 83, 46, 10, 119). |
| **10. Sentinel-1 SLC Bulk Acquisition** | CDSE Zipper (`zipper.dataspace...`) | **AUTHENTICATED_BUT_ACQUISITION_FAILED** | `DAT-ZIP-609: Token audience not allowed` (Sentinel Hub client scope vs raw bulk download scope). |
| **11. InSAR Processing Pipeline** | `InSARProcessingEngine` | **READY_FOR_ACQUISITION** | 10-step processing engine validated; awaiting bulk raw SLC slice download authorization. |
| **12. NER-SAFE Ingestion Chain** | `source_ingestion_manager.py` | **PASS** | S1 & S2 ingested as `FRESH` with SHA-256 and decoupled observation/ingestion timestamps. |
| **13. Autonomous Scheduler Status** | `live_monitoring_scheduler.py` | **PASS** | `ESA_SENTINEL1_SAR_01` & `ESA_SENTINEL2_OPT_01` transitioned to `LIVE_VERIFIED`. |
| **14. Dashboard Integration** | `/api/monitoring/sources/health` | **PASS** | Reflects authentic health states without exposing secrets. |

---

## 2. CDSE OAuth2 & Sentinel Hub Authentication

* **Identity Provider**: Keycloak OpenID Connect at `https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token`
* **Flow**: `client_credentials`
* **Client Type**: Copernicus Sentinel Hub Client (`sh-*`)
* **Token Type**: Bearer
* **Token Validity Window**: 1800 seconds (30 minutes) with proactive refresh buffer
* **Sentinel Hub STAC Endpoint**: `https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/collections` -> **HTTP 200 OK**
* **Available Collections**: `['sentinel-2-l1c', 'sentinel-3-olci-l2', 'landsat-ot-l1', 'sentinel-3-olci', 'sentinel-3-slstr', 'sentinel-3-slstr-l2', 'sentinel-3-synergy-l2', 'sentinel-1-grd', 'sentinel-2-l2a', 'sentinel-5p-l2']`

---

## 3. Sentinel-2 Optical (MSI L2A) Real Observation & Acquisition

* **Discovery Source**: Sentinel Hub STAC Catalog API
* **Target AOI**: Shella / East Khasi Hills Landslide Corridor, Meghalaya ($[91.60^\circ\text{ E}, 25.15^\circ\text{ N}, 91.65^\circ\text{ E}, 25.20^\circ\text{ N}]$)
* **Latest Discovered Scene**: `S2C_MSIL2A_20260912T042701_N0512_R133_T46RCN_20260912T075909.SAFE`
* **Observation Timestamp**: `2026-09-12T04:41:37.769Z`
* **Platform**: Sentinel-2C
* **Acquisition Method**: Sentinel Hub Process API (`https://sh.dataspace.copernicus.eu/api/v1/process`)
* **Acquired Channels**: 4 Bands (Band 4 Red, Band 8 NIR, Band 3 Green, Scene Classification Layer SCL)
* **Local Output File**: `test_data_cdse/sentinel2_l2a_meghalaya_test.tif`
* **File Size**: **42,228 bytes**
* **Cryptographic SHA-256**: `aee96d4c2c56ffb84c893b2789f27b2c59b459f2a8087022b152283aa1eabdd8`
* **Ingestion State**: Registered in `source_ingestion_manager.py` as `FRESH`.
* **Final Status**: **`SENTINEL_2 = LIVE_VERIFIED`**

---

## 4. Sentinel-1 SAR (C-Band GRD) Real Observation & Acquisition

* **Discovery Source**: Sentinel Hub STAC & CDSE OData Catalog API
* **Target AOI**: Shella / East Khasi Hills Landslide Corridor, Meghalaya
* **Latest Discovered Scene**: `S1D_IW_GRDH_1SDV_20260913T235452_20260913T235517_004566_008803_AFC4_COG.SAFE`
* **Observation Timestamp**: `2026-09-13T23:54:52Z` (Acquired mere hours ago)
* **Sensor Mode & Orbit**: Interferometric Wide Swath (IW), Descending
* **Acquisition Method**: Sentinel Hub Process API (`https://sh.dataspace.copernicus.eu/api/v1/process`)
* **Radiometric Calibration**: Orthorectified $\gamma^0$ Ellipsoid backscatter (Dual-pol VV + VH)
* **Local Output File**: `test_data_cdse/sentinel1_grd_meghalaya_test.tif`
* **File Size**: **28,562 bytes**
* **Cryptographic SHA-256**: `37c813048e8d5828945f2be6c22c1609f9ef9e424911d335b3c246a0ff32071c`
* **Scientific Scope**: Used for surface backscatter alteration and moisture change. Ground displacement was NOT measured.
* **Ingestion State**: Registered in `source_ingestion_manager.py` as `FRESH`.
* **Final Status**: **`SENTINEL_1_GRD = LIVE_VERIFIED`**

---

## 5. Sentinel-1 SLC & InSAR Repeat-Pass Audit

### 5.1 OData SLC Discovery
15 authentic Level-1 Single Look Complex (IW SLC) products were discovered intersecting the NER bounding box via the official CDSE OData API:
1. `S1D_IW_SLC__1SDV_20260913T235606_20260913T235633_004566_008803_78A3.SAFE`
2. `S1D_IW_SLC__1SDV_20260913T235542_20260913T235609_004566_008803_CAAF.SAFE`
3. `S1D_IW_SLC__1SDV_20260913T235516_20260913T235544_004566_008803_D990.SAFE`
4. `S1D_IW_SLC__1SDV_20260913T235451_20260913T235518_004566_008803_FBA2.SAFE`
5. `S1D_IW_SLC__1SDV_20260913T235426_20260913T235453_004566_008803_2091.SAFE`
6. `S1D_IW_SLC__1SDV_20260913T114836_20260913T114903_004559_0087BD_E2E4.SAFE`
7. `S1D_IW_SLC__1SDV_20260913T114811_20260913T114838_004559_0087BD_D08D.SAFE`
8. `S1D_IW_SLC__1SDV_20260913T114746_20260913T114813_004559_0087BD_D65C.SAFE`
9. `S1D_IW_SLC__1SDV_20260913T114720_20260913T114748_004559_0087BD_04CD.SAFE`
10. `S1D_IW_SLC__1SDV_20260913T114656_20260913T114723_004559_0087BD_D9D7.SAFE`
11. `S1D_IW_SLC__1SDV_20260913T114631_20260913T114658_004559_0087BD_4539.SAFE`
12. `S1D_IW_SLC__1SDV_20260911T120459_20260911T120527_004530_0086C5_CCA6.SAFE`
13. `S1D_IW_SLC__1SDV_20260911T120434_20260911T120501_004530_0086C5_E2A6.SAFE`
14. `S1D_IW_SLC__1SDV_20260911T120410_20260911T120436_004530_0086C5_66E9.SAFE`
15. `S1D_IW_SLC__1SDV_20260911T120345_20260911T120412_004530_0086C5_D550.SAFE`

### 5.2 Pair Compatibility Evaluation
The [insar_pair_selector.py](file:///E:/landslide%20-%20Copy/landslide%20-%20Copy/insar_pair_selector.py) engine evaluated candidate scenes and verified multiple valid repeat-pass interferometric pairs:
* **Pair 1 (Track 83)**:
  * Primary: `S1D_IW_SLC__1SDV_20260830T120409...SAFE`
  * Secondary: `S1D_IW_SLC__1SDV_20260818T120433...SAFE`
  * Temporal Baseline: **12.0 days** (Optimal for C-band coherence)
  * Relative Orbit: **83** (Exact match)
  * Status: **OPTIMAL**
* **Pair 2 (Track 46)**:
  * Primary: `S1D_IW_SLC__1SDV_20260827T234655...SAFE`
  * Secondary: `S1D_IW_SLC__1SDV_20260815T234655...SAFE`
  * Temporal Baseline: **12.0 days**
  * Relative Orbit: **46** (Exact match)
  * Status: **OPTIMAL**

### 5.3 Bulk Archive Download Boundary
* **Test Endpoint**: `https://zipper.dataspace.copernicus.eu/odata/v1/Products(dea0e921-5003-41a9-ac62-794360a27409)/$value`
* **HTTP Result**: **401 Unauthorized**
* **Response Diagnostic**:
  ```json
  {
    "trace-id": "08a5574974b32f6cb568c99edf1c2ab7",
    "code": "DAT-ZIP-609",
    "message": "Token audience not allowed"
  }
  ```
* **Technical Explanation**:
  Copernicus Data Space Ecosystem distinguishes between **Sentinel Hub OAuth Clients** (`sh-*`) and **Direct Zipper Bulk Download Clients**:
  * Sentinel Hub OAuth credentials authorize Process API, STAC Catalog, and OData metadata queries.
  * Downloading entire raw $\sim 8\text{ GB}$ SLC ZIP archives via the Zipper endpoint mandates a token scoped for `DAT-ZIP` (typically generated via direct user password flow or CDSE S3 Access Keys).
* **Final Classification**:
  * `Sentinel-1 SLC Discovery`: **PASS**
  * `Compatible Repeat-Pass Pairs`: **PASS (Optimal 12-day pairs identified)**
  * `SLC Bulk Zip Download`: **AUTHENTICATED_BUT_ACQUISITION_FAILED (Token audience restricted: DAT-ZIP-609)**
  * `InSAR Pipeline State`: **WAITING_FOR_COMPATIBLE_PAIR / READY_FOR_ACQUISITION**

---

## 6. Multi-Source Ingestion & Freshness Compliance

1. **Deduplication Safeguard**: Ingesting the same product hash multiple times returns `ALREADY_CURRENT` and suppresses redundant risk reassessments.
2. **Decoupled Provenance Timestamps**: Observation timestamp (`2026-09-12T04:41:37Z`) and ingestion timestamp (`2026-09-14T05:46:49Z`) are strictly segregated.
3. **Zero-Stale Rule**: Stale feeds ($> 3\text{h}$ for GPM) return `CURRENT RISK: NOT AVAILABLE`. Previous risk scores are never passed off as current risk.
4. **Non-Fabrication Policy**: Absent bulk SLC data is classified honestly as `READY_FOR_ACQUISITION` with token audience limitation; synthetic fringes or fake deformation maps were strictly avoided.

---

## 7. Storage Protection

* **Existing 9.8 GB Sentinel-2 Baseline**: 100% untouched and preserved in `NER_SAFE_DATA/SENTINEL2/`.
* **C10/C11/C12 Protected Rasters & Vector Shapes**: 100% untouched.
* **New Acquisition Test Data**: Isolated under `test_data_cdse/` (Total: $\sim 70.8\text{ KB}$), preventing storage overflow on the 8 GB RAM laptop.

---

## 8. Dashboard & API Health Status

The `/api/monitoring/sources/health` endpoint dynamically reports authentic live statuses:

```json
[
  {
    "source_id": "NASA_GPM_NRT_01",
    "name": "NASA GPM IMERG Early Run Precipitation NRT",
    "status": "FRESH"
  },
  {
    "source_id": "NASA_SMAP_L3_01",
    "name": "NASA SMAP L3 Enhanced Radiometer Soil Moisture",
    "status": "RECENT"
  },
  {
    "source_id": "ESA_SENTINEL1_SAR_01",
    "name": "Copernicus Sentinel-1 C-SAR GRD All-Weather Surface Change",
    "status": "LIVE_VERIFIED"
  },
  {
    "source_id": "ESA_SENTINEL2_OPT_01",
    "name": "Copernicus Sentinel-2 MSI Multi-Spectral Surface Reflectance",
    "status": "LIVE_VERIFIED"
  },
  {
    "source_id": "NIT_MEG_MAWIONGRIM_01",
    "name": "NIT Meghalaya Mawiongrim Geotechnical In-Situ Station",
    "status": "INSTITUTIONAL_ACCESS_REQUIRED"
  },
  {
    "source_id": "MIRSAC_AIZAWL_01",
    "name": "MIRSAC / SILAAS Aizawl Real-Time Slope Telemetry",
    "status": "INSTITUTIONAL_ACCESS_REQUIRED"
  },
  {
    "source_id": "IMD_AWS_SHILLONG_01",
    "name": "IMD Automatic Weather Station Shillong",
    "status": "INSTITUTIONAL_ACCESS_REQUIRED"
  },
  {
    "source_id": "LOCAL_ESP32_GATEWAY_01",
    "name": "NER-SAFE Reference Slope Hardware Gateway",
    "status": "HARDWARE_REQUIRED"
  }
]
```
