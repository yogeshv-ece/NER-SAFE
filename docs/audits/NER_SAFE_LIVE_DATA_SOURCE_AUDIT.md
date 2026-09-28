# NER-SAFE: COMPREHENSIVE LIVE DATA SOURCE AUDIT REPORT
**Date**: September 13, 2026  
**System Baseline**: `nersafe-judge-demo-baseline-1.0` (`v1.0.0-judge-demo-freeze`)  
**Scope**: In-Depth Forensic Investigation of Ground Sensors, Satellite Observations, and Weather Streams in NER  

---

## 1. SOURCE-BY-SOURCE INVESTIGATION MATRIX

The following audit provides the definitive operational and legal status for every external data source evaluated for NER-SAFE:

### Source 1: Mawiongrim Geotechnical Slope Monitoring Station
* **State & District**: Meghalaya, East Khasi Hills (Mawiongrim, near Shillong)
* **Organization**: National Institute of Technology Meghalaya (NIT Meghalaya) & NEHU
* **Sensor Modalities**: Inclinometers (10m, 20m, 30m depth uphill/downhill), Piezometer (groundwater level), Tipping Bucket Rain Gauge, 5 Soil Suction Tensiometers.
* **Update Interval**: Hourly (1.0 hour)
* **Actual Observation Availability**: Historical research dataset (Dec 1, 2022 to Dec 30, 2022; 696 continuous hourly observations).
* **Data Format**: CSV time-series (`Landslide Civildf_new.csv`, 101.9 KB).
* **API / Feed Type**: Private Cellular / WSN Hub transmitting to NITM local servers. No open public REST endpoint.
* **Authentication**: None for historical research repository; `INSTITUTIONAL_ACCESS_REQUIRED` (MoU) for live streaming telemetry.
* **Current Accessibility**: Historical dataset downloaded and cached in `NER_SAFE_DATA/SENSORS/mawiongrim_telemetry.csv`. Live feed blocked by closed institutional network.
* **Historical vs. Live Distinction**: **HISTORICAL DATASET VERIFIED**; live feed requires NIT Meghalaya administrative access.
* **Automatic Ingestion Status**: Fully supported via `ground_sensor_adapter.ingest_mawiongrim_records()`.
* **Last Ingested Observation**: `2022-12-30T00:00:00Z` (Preserved original observation time).
* **Ingestion Timestamp**: `2026-09-13T16:12:12Z`.
* **Freshness State**: `DATA_STALE` (Historical baseline, correctly disclaimed).
* **Limitations**: Lacks ground-truth failure collapse timestamps; represents continuous pre-failure deformation.
* **User Action Required**: Establish an institutional research agreement with NIT Meghalaya (Department of Electronics & Communication / Civil Engineering) to acquire live API/MQTT credentials for the Mawiongrim hub.

---

### Source 2: NEHU Shillong Experimental Slope Research Station
* **State & District**: Meghalaya, East Khasi Hills (NEHU Campus, Shillong)
* **Organization**: North-Eastern Hill University (NEHU)
* **Sensor Modalities**: Soil moisture sensor probes, rain gauge, inclinometer/tilt modules.
* **Update Interval**: 1.0 hour.
* **Actual Observation Availability**: Offline academic research datalogger.
* **Data Format**: ASCII / CSV logger files.
* **API / Feed Type**: Offline datalogger. No public network endpoint.
* **Authentication**: `INSTITUTIONAL_ACCESS_REQUIRED`.
* **Current Accessibility**: External access blocked; requires physical campus retrieval or departmental access.
* **Historical vs. Live Distinction**: **ACADEMIC FIELD EXPERIMENT**.
* **Automatic Ingestion Status**: Software schema ready; physical streaming unlinked.
* **Limitations**: Not connected to a public cloud or internet gateway.
* **User Action Required**: Coordinate with NEHU Department of Environmental Studies / Geography for datalogger dumps.

---

### Source 3: MIRSAC Aizawl Critical Slope Network (SILAAS)
* **State & District**: Mizoram, Aizawl District (Laipuitlang, Ngaizel, Tlangnuam slopes)
* **Organization**: Mizoram Remote Sensing Application Centre (MIRSAC) / Mizoram Disaster Management & Rehabilitation
* **Sensor Modalities**: Municipal rain gauge network, geotechnical inclinometer boreholes.
* **Update Interval**: Daily advisory cycle (24 hours).
* **Actual Observation Availability**: Published hazard zonation maps and advisory PDF bulletins.
* **Data Format**: PDF situation reports, GIS shapefiles.
* **API / Feed Type**: Government intranet / SILAAS portal. No machine-readable public REST telemetry feed.
* **Authentication**: `INSTITUTIONAL_ACCESS_REQUIRED`.
* **Current Accessibility**: Public can view summary hazard bulletins; live sensor streams are restricted to state emergency operations.
* **Historical vs. Live Distinction**: **MUNICIPAL ADVISORY ZONATION**.
* **Automatic Ingestion Status**: Ingestion adapter ready (`MIRSAC_AIZAWL_01`); automated polling blocked pending state government credentials.
* **Limitations**: SILAAS publishes administrative advisories, not raw high-frequency telemetry streams.
* **User Action Required**: Request API credentials or automated email push from MIRSAC / Mizoram SDMA.

---

### Source 4: NASA GPM IMERG Early NRT (Precipitation)
* **State & District**: Regional Synoptic Coverage (All NER States)
* **Organization**: NASA GES DISC / Earthdata
* **Sensor Modalities**: Satellite dual-frequency precipitation radar and microwave radiometer constellation.
* **Update Interval**: Half-hourly (30 minutes; ~4-hour processing latency).
* **Actual Observation Availability**: Live satellite passes available 24/7.
* **Data Format**: HDF5 / GeoTIFF / UMM-JSON metadata.
* **API / Feed Type**: NASA CMR REST API (`cmr.earthdata.nasa.gov`) + GES DISC HTTPS download.
* **Authentication**: Earthdata Login credentials (Configured in `~/.netrc`).
* **Current Accessibility**: `LIVE_READY`. Discovery queries return real granules.
* **Historical vs. Live Distinction**: **GENUINE LIVE SATELLITE DISCOVERY**.
* **Automatic Ingestion Status**: Automated via `live_monitoring_scheduler.py`.
* **Last Ingested Observation**: `2026-09-13T10:30:00.000Z`.
* **Ingestion Timestamp**: `2026-09-13T16:13:54Z`.
* **Freshness State**: `FRESH` (Within nominal revisit window).
* **Limitations**: 0.1° (~10 km) resolution is a regional precipitation proxy; cannot resolve micro-scale slope drainage ditches.
* **User Action Required**: Ensure `~/.netrc` Earthdata credentials remain active.

---

### Source 5: NASA SMAP L3 Enhanced Radiometer (Soil Moisture)
* **State & District**: Regional Synoptic Coverage (All NER States)
* **Organization**: NASA NSIDC DAAC / Earthdata
* **Sensor Modalities**: L-Band microwave radiometer (top 5cm relative soil moisture saturation).
* **Update Interval**: Daily (~24-36 hours).
* **Actual Observation Availability**: Live satellite passes available daily.
* **Data Format**: HDF5 / EASE-Grid 2.0 (9 km resolution).
* **API / Feed Type**: NASA CMR REST API + NSIDC HTTPS download.
* **Authentication**: Earthdata Login credentials (Configured in `~/.netrc`).
* **Current Accessibility**: `LIVE_READY`.
* **Historical vs. Live Distinction**: **GENUINE LIVE SATELLITE DISCOVERY**.
* **Automatic Ingestion Status**: Automated via `live_monitoring_scheduler.py`.
* **Last Ingested Observation**: `2026-09-12T00:00:00.000Z`.
* **Ingestion Timestamp**: `2026-09-13T16:13:55Z`.
* **Freshness State**: `RECENT`.
* **Limitations**: Senses only top 5 cm surface soil moisture; does not measure deep slip-surface pore pressure.
* **User Action Required**: None. Operational.

---

### Source 6: Copernicus Sentinel-1 C-SAR (Surface Change)
* **State & District**: Regional Synoptic Coverage (Meghalaya, Mizoram, Assam)
* **Organization**: European Space Agency / Copernicus Data Space Ecosystem (CDSE)
* **Sensor Modalities**: C-band Synthetic Aperture Radar (IW Mode, VV + VH polarization).
* **Update Interval**: 6 to 12 days.
* **Actual Observation Availability**: Regularly acquired orbital passes.
* **Data Format**: SAFE archive / Level-1 GRD GeoTIFF.
* **API / Feed Type**: CDSE OData REST API (`catalogue.dataspace.copernicus.eu`).
* **Authentication**: `AUTH_REQUIRED` (Requires `CDSE_CLIENT_ID` and `CDSE_CLIENT_SECRET`).
* **Current Accessibility**: Public metadata discovery works; binary download requires OAuth2 credentials.
* **Historical vs. Live Distinction**: **CATALOG DISCOVERY PUBLIC / BINARY DOWNLOAD AUTH REQUIRED**.
* **Automatic Ingestion Status**: Ready in `source_ingestion_manager.py`; waiting for CDSE environment credentials.
* **Freshness State**: `AUTH_REQUIRED`.
* **Limitations**: Surface backscatter ratio only; strictly does NOT perform InSAR millimeter displacement.
* **User Action Required**: Register on `dataspace.copernicus.eu`, generate OAuth2 credentials, and export `CDSE_CLIENT_ID` / `CDSE_CLIENT_SECRET`.

---

### Source 7: Copernicus Sentinel-2 MSI (Optical Reflectance)
* **State & District**: Regional Synoptic Coverage
* **Organization**: ESA / Copernicus / Element84 STAC
* **Sensor Modalities**: Multi-spectral instrument (13 spectral bands, 10m/20m resolution).
* **Update Interval**: 5 days (constellation 2A + 2B + 2C).
* **Actual Observation Availability**: Regularly acquired optical passes.
* **Data Format**: Cloud-Optimized GeoTIFF (COG).
* **API / Feed Type**: Element84 Earth Search STAC API / CDSE.
* **Authentication**: `AUTH_REQUIRED`.
* **Current Accessibility**: Metadata search is open; downloading full multi-band arrays requires authenticated access.
* **Historical vs. Live Distinction**: **CATALOG DISCOVERY PUBLIC / BINARY DOWNLOAD AUTH REQUIRED**.
* **Limitations**: Heavy cloud occlusion (>80% cloud cover) during summer monsoon season.
* **User Action Required**: Configure CDSE or AWS requester-pays credentials.

---

### Source 8: IMD Automatic Weather Station Network (Shillong / Aizawl)
* **State & District**: Meghalaya & Mizoram urban weather stations
* **Organization**: India Meteorological Department (Ministry of Earth Sciences)
* **Sensor Modalities**: Ground tipping-bucket rain gauge, thermometer, anemometer, hygrometer.
* **Update Interval**: Hourly (1.0 hour).
* **Actual Observation Availability**: Web portal rendered HTML (`mausam.imd.gov.in`).
* **Data Format**: Rendered HTML tables (no public machine-readable JSON endpoint).
* **API / Feed Type**: Restricted departmental AWS network.
* **Authentication**: `EXTERNAL_INSTITUTIONAL_ACCESS_REQUIRED`.
* **Current Accessibility**: Blocked for automated programmatic ingestion.
* **Historical vs. Live Distinction**: **GOVERNMENT PUBLIC HTML PORTAL ONLY**.
* **Automatic Ingestion Status**: Provider abstraction implemented (`weather_provider.py`); returns `AWAITING_INSTITUTIONAL_MOU`.
* **Limitations**: Public web scraping is brittle and prohibited by government terms of service; machine-to-machine streaming requires official MoU.
* **User Action Required**: Execute an academic/government MoU with MoES / IMD to obtain official AWS REST API tokens.

---

### Source 9: Local Reference Edge Slope Gateway
* **State & District**: Field Node (Target Hotspot Slope)
* **Organization**: NER-SAFE Edge Deployment
* **Sensor Modalities**: Capacitive soil moisture, MPU-6050 6-DoF accelerometer/inclinometer, tipping bucket rain counter.
* **Update Interval**: Continuous (5 seconds).
* **Actual Observation Availability**: Real-time when board is physically connected.
* **Data Format**: NMEA XOR serial sentences (`$NER,...`) and JSON HTTP POST.
* **API / Feed Type**: USB Serial / Local HTTP REST endpoint (`/api/sensors/reading`).
* **Authentication**: Local authorization token.
* **Current Accessibility**: `SOFTWARE_INTERFACE_READY / HARDWARE_VALIDATION_REQUIRED`.
* **Historical vs. Live Distinction**: **LOCAL HARDWARE PROTOCOL READY**.
* **Firmware**: Standalone Arduino C++ sketch `esp32_reference_gateway.ino`.
* **Limitations**: Requires physical hardware connected by user.
* **User Action Required**: Connect ESP32 Dev board with sensors over USB and flash firmware.

---

## 2. SUMMARY OF OPERATIONAL STATUSES

| Source ID | Name | Organization | Signal Speed | Status Classification | Genuine Ingestion Capability Today |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NIT_MEG_MAWIONGRIM_01** | Mawiongrim Geotechnical Station | NIT Meghalaya | FAST (Hourly) | `INSTITUTIONAL_ACCESS_REQUIRED` | Historical dataset (696 records) ingested; live stream requires NITM MoU |
| **NEHU_SHILLONG_SLOPE_01** | NEHU Campus Slope Station | NEHU Shillong | FAST (Hourly) | `INSTITUTIONAL_ACCESS_REQUIRED` | Ingestion schema ready; offline datalogger access requires campus agreement |
| **MIRSAC_AIZAWL_01** | Aizawl Slope Network (SILAAS) | MIRSAC / Mizoram SDMA | MEDIUM (Daily) | `INSTITUTIONAL_ACCESS_REQUIRED` | Advisory bulletins public; raw telemetry requires State MoU |
| **NASA_GPM_NRT_01** | GPM IMERG Early Precipitation | NASA GES DISC | FAST (30 min) | `LIVE_READY` | Live discovery operational; observation from earlier today ingested |
| **NASA_SMAP_L3_01** | SMAP L3 Soil Moisture | NASA NSIDC | MEDIUM (Daily) | `LIVE_READY` | Live discovery operational; observation from yesterday ingested |
| **ESA_SENTINEL1_SAR_01** | Sentinel-1 C-SAR GRD | Copernicus CDSE | MEDIUM (6-12d) | `AUTH_REQUIRED` | Catalog discovery public; binary download requires CDSE OAuth2 credentials |
| **ESA_SENTINEL2_OPT_01** | Sentinel-2 MSI Optical L2A | Copernicus / STAC | CONTEXT (5d) | `AUTH_REQUIRED` | Catalog discovery public; binary download requires CDSE credentials |
| **IMD_AWS_SHILLONG_01** | IMD Automatic Weather Station | IMD / MoES | FAST (Hourly) | `INSTITUTIONAL_ACCESS_REQUIRED` | Web portal public; automated machine REST API requires Ministry MoU |
| **LOCAL_ESP32_GATEWAY_01** | NER-SAFE Edge Slope Gateway | NER-SAFE Edge | FAST (5 sec) | `HARDWARE_REQUIRED` | Firmware created; requires user to connect physical ESP32 board |
