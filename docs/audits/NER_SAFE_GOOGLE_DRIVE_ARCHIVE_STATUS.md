# NER-SAFE: Google Drive Cloud Heavy-Data Archival Status Report

**Release Lineage:** `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Component:** `GOOGLE_DRIVE_ARCHIVE`  
**Execution Timestamp:** `2026-09-14T07:25:00Z`  
**Security Classification:** RESTRICTED LOCAL RESEARCH PROTOTYPE (Zero Credentials Exposed)  
**Status:** `READY`

---

## 1. Executive Summary & Verification Matrix

NER-SAFE's storage architecture has been extended to support direct, authenticated cloud archival of validated heavy satellite data (Sentinel-1 IW SLC, Sentinel-1 GRD, Sentinel-2 optical, genuine InSAR deformation rasters, GPM rainfall, and SMAP soil moisture) to the user's Google Drive cloud:

| Milestone | Status | Details / Evidence |
| :--- | :---: | :--- |
| **Google Drive API v3 Authentication** | **PASS** | Authenticated via OAuth2 (`credentials.json` & `token.json`) for account **Yogesh V** |
| **5 TB Cloud Quota Verification** | **PASS** | Total Limit: **5,120.00 GB (5.0 TB)** | Cloud Available: **> 5,117 GB** |
| **Active Compute Storage Policy** | **PASS** | `E:` remains the primary active compute and cache filesystem; `G:\` is NOT used for compute |
| **Local Retention Policy** | **PASS** | `LOCAL_RETENTION_POLICY = KEEP` strictly enforced; zero local files deleted |
| **Remote Archive Hierarchy** | **PASS** | Canonical `NER-SAFE-DATA/` hierarchy created with verified Google Drive folder IDs |
| **Resumable Chunked Streaming** | **PASS** | Streaming in 8 MB chunks; zero full-scene loading into system RAM |
| **Remote Integrity Verification** | **PASS** | Remote file metadata and byte size verified matching local file size; SHA-256 computed |
| **InSAR Outputs Archival** | **PASS** | All 6 persistent InSAR products and metadata records verified and archived |
| **Sentinel-1 SLC Metadata Archival** | **PASS** | Manifests, annotation XMLs, calibration XMLs, noise XMLs, RFI XMLs archived |
| **Deduplication Mechanism** | **PASS** | Remote directory queries skip re-uploading identical existing files |
| **Error Decoupling** | **PASS** | Network/cloud interruptions return `ARCHIVE_PENDING` / `ARCHIVE_FAILED` without failing scientific state |
| **Security Perimeter** | **PASS** | Zero tokens, passwords, or client secrets logged, committed, or exposed |

---

## 2. Google Drive Authentication & Cloud Quota

- **API Version:** Google Drive REST API v3
- **OAuth Scopes:** `https://www.googleapis.com/auth/drive.file`
- **Authorized Account:** `Yogesh V`
- **Cloud Quota Total:** `5,120.00 GB` (5.0 TB)
- **Cloud Storage Used:** `2.87 GB`
- **Cloud Storage Available:** `5,117.13 GB`
- **Desktop Virtual Filesystem:** `G:\` (136.68 GB local mirror partition)

---

## 3. Remote Folder Structure (`NER-SAFE-DATA/`)

The following folder hierarchy was created on Google Drive cloud and cached in [`NER_SAFE_DATA/archive_folder_cache.json`](file:///e:/landslide%20-%20Copy/landslide%20-%20Copy/NER_SAFE_DATA/archive_folder_cache.json):

```text
NER-SAFE-DATA/                              [ID: 1ROx1ceIPFSmNQpKWMrTfw9g9Mh7vRIiN]
  ├── SENTINEL1/
  │     ├── SLC/                            [ID: 11X1b73zQJhB7DVQF6F8ECZdibZknL5xS]
  │     └── GRD/                            [ID: 1Hz6EB6yOEXJfCBUOBgMfqXyifeL_Fl_k]
  ├── SENTINEL2/                            [ID: 1FlQIYY8P4fswxkKwIqYgLo5chG3PftwW]
  ├── INSAR/                                [ID: 1taJVSu9bdRLAAR7MdLotXjatbYG5X_ot]
  ├── GPM/                                  [ID: 10b7YDVqBE5XRC0xyRbt8oDQgsaaMvHGb]
  ├── SMAP/                                 [ID: 1LbIRNITolJgrzQfa6iM0-6aN9310_g6W]
  └── MANIFESTS/                            [ID: 1Kt4ZYA9FU-9f9lvPuV5ThrsP9K2YLxe7]
```

---

## 4. InSAR Persistent Outputs Archival

All 6 genuine InSAR output products and metadata records have been archived to `NER-SAFE-DATA/INSAR/` and verified:

| Local Artifact | Remote File ID | Size (Bytes) | SHA-256 Checksum | Verification |
| :--- | :--- | :---: | :--- | :---: |
| `insar_coherence.tif` | `1xsEb2mSw0AQf4Q0t91rnBJgxIVpmmQlX` | 9,960,004 | `2c0c6a74fa97fc65df6084b6bd13379c99dbf0394740a462920f42e283981bce` | `VERIFIED_SIZE_MATCH` |
| `insar_los_displacement.tif` | `1VlSoWhRnXnitfmORuWN1ThHfxnLX-obZ` | 9,959,998 | `7d38166f76fe95e767b8d971c7aa06b0702a32edc5717136953f54fdee7a975e` | `VERIFIED_SIZE_MATCH` |
| `insar_unwrapped_phase.tif` | `1jMzHVcm3LG42RJ-pEqrA3TOQKiLeKJtt` | 9,960,004 | `44f72d798bd8fe3a034145c43828de230bc5d0fbf70e0960a504696fc086e330` | `VERIFIED_SIZE_MATCH` |
| `insar_quality_mask.tif` | `1EMxWUSboaOj0IXZNUKL59BYa8QzTUIS2` | 2,489,350 | `2bead608baa415865f176d1a60af7c3a8808e0e63338b6a25d5680533f72830e` | `VERIFIED_SIZE_MATCH` |
| `insar_processing_summary.json` | `1Fnhhihq7qCyKEaDZeZjQ11V0EmKHQ_mR` | 2,063 | `465361105ffae83fad68a37272e679ad2d53bb979de910991e21685770581f4d` | `VERIFIED_SIZE_MATCH` |
| `insar_ingestion_record.json` | `1IyVLI5vYl6My8Joodf4jbcW_Sh08lVYx` | 2,192 | `5157c9f7f8371137117d991c3f145c316ddbcd54164f5aa21d14a711c128db05` | `VERIFIED_SIZE_MATCH` |

---

## 5. Sentinel-1 SLC Metadata & Provenance Archival

The complete XML annotations, calibration files, noise vectors, SAFE manifests, and full 1.09 GB measurement TIFFs for the repeat-pass pair were archived to `NER-SAFE-DATA/SENTINEL1/SLC/`:

1. **Secondary Acquisition (`2026-09-01`)**:
   - `manifest.safe` -> ID: `1kWOnqASPu0hpYMca4dvTE9lv2UCF5hiq`
   - `s1d-iw1-slc-vv-20260901...xml` -> ID: `1CUG0C0iWeO60jgLb7Qp8GK9h9nXzxwAu`
   - `calibration-s1d-iw1-slc-vv-20260901...xml` -> ID: `10KrPwUuERncoYwHLZFn1_3lUthPj7tNM`
   - `noise-s1d-iw1-slc-vv-20260901...xml` -> ID: `1D6mEEmlfQloKhBycUDlcxJ-WuP0PkrET`
   - `rfi-s1d-iw1-slc-vv-20260901...xml` -> ID: `13gz6QCeKU2-zvIC5UfleZRqmTYEMrx4J`
   - `acquisition_record.json` -> ID: `1VF5W2L1BJlC4HlagCk7q3meXCqr4iGIa`
   - `measurement/*.tiff` (1.09 GB) -> ID: `1lfeBLb1NaG985bjQjmlVVBHREWI2UHgB`
2. **Primary Acquisition (`2026-09-13`)**:
   - `manifest.safe` -> ID: `1xoXBnxMJC5UZSC27G6Ut3d1b3M_WPdqx`
   - `s1d-iw1-slc-vv-20260913...xml` -> ID: `1WeF1_sFUpV8hczGDQXqO1IP6yx6ZLV-U`
   - `calibration-s1d-iw1-slc-vv-20260913...xml` -> ID: `1VPpkJDI_0pnYbsf_eFSRJmFQYV_8GbiK`
   - `noise-s1d-iw1-slc-vv-20260913...xml` -> ID: `1DGV2sDqlfy84DHSx6gOK47uARLDB9nvn`
   - `rfi-s1d-iw1-slc-vv-20260913...xml` -> ID: `1S7jUSDMb3gtJ2ofrq3z6NucUurMyU8L-`
   - `acquisition_record.json` -> ID: `1Raa02wQLH-XbC791vwv4P_-lBaru-C50`
   - `measurement/*.tiff` (1.09 GB) -> ID: `1BcNFENrFbAIqEcWSA8S-3fybH6qJhqRH`

---

## 6. Storage Policy & Operational Rules

1. **Active Working Data**: `E:\landslide - Copy\landslide - Copy\` is the authoritative local compute directory.
2. **Long-Term Archive**: Google Drive 5 TB cloud storage.
3. **Mounted Drive (`G:\`)**: Never used as a direct compute location (avoids network filesystem locks and sync latency).
4. **Local Retention**: `LOCAL_RETENTION_POLICY = KEEP`. All local satellite files, rasters, and baseline datasets on `E:` are strictly retained.
5. **Decoupled Ingestion State**:
   - Scientific observation validation is independent of cloud availability.
   - If Google Drive is temporarily offline, the pipeline records `ARCHIVE_PENDING` or `ARCHIVE_FAILED` and continues live landslide hazard monitoring without interruption.

---

## 7. Automated Test Suite Results

```text
test_01_connection_and_quota                    ... PASS (Connected, 5 TB quota verified)
test_02_archive_folder_structure                ... PASS (All 7 subfolders verified)
test_03_resumable_upload_and_verification       ... PASS (Resumable upload + size match + dedup + cleanup)
test_04_local_retention_policy                  ... PASS (Policy strictly 'KEEP')
test_05_insar_products_archived_in_manifest     ... PASS (InSAR rasters verified in manifest)
test_06_zero_secrets_in_manifest                ... PASS (Zero tokens/secrets detected)
test_07_archiver_summary_and_provenance         ... PASS (Metrics, byte counts, and categories verified)

7/7 TESTS PASSED (100%)
```

---

## 8. Final Status

```text
GOOGLE_DRIVE_ARCHIVE = READY
```
