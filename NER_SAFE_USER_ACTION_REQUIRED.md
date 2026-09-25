# NER-SAFE: USER ACTION REQUIRED & EXTERNAL ACCESS PREREQUISITES

**Document Purpose**: Definitive Classification of Operational Capabilities vs. External Institutional, Credential, and Hardware Requirements  
**Project**: NER-SAFE (SIH 26001)  
**Date**: September 13, 2026  
**Operational Principle**: Real Multi-Source Observation Ingestion — No Fabricated Feeds, No Replay Masquerading as Live  

---

## 1. EXECUTIVE SUMMARY & USER PREFERENCE DIRECTIVE

NER-SAFE is designed as an operational, live multi-source monitoring and early-warning system. In accordance with operational directives:
1. **Existing NER Sensors First**: The primary objective is consuming **existing field sensor deployments** across Meghalaya and Mizoram (e.g., NIT Meghalaya's Mawiongrim station, NEHU slope stations, MIRSAC/SILAAS regional monitoring) rather than mandating do-it-yourself (DIY) ESP32 hardware.
2. **Strict Provenance & Honesty**: NER-SAFE never fabricates sensor feeds, never fakes live REST/MQTT APIs, and never treats academic papers or historical datasets as live streaming telemetry.
3. **Transparent Boundaries**: Every required external step is clearly categorized into what has been automated locally, what requires user credentials, what requires institutional access/agreements, and what requires physical hardware.

---

## 2. CATEGORIZATION OF CAPABILITIES AND REQUIREMENTS

### Category A: Capabilities Antigravity Has Completed Locally
* **Universal Live Sensor Registry** (`sensor_source_registry.py`): Full 9-source catalog categorizing signals into Fast (ground sensors, GPM NRT), Medium (Sentinel-1 SAR), and Context (Sentinel-2, SMAP, SRTM), with complete metadata and operational status tracking.
* **Standardized Ground Sensor Adapter** (`ground_sensor_interface.py`): Hardware-neutral, multi-sensor observation ingestion engine supporting `SOIL_MOISTURE`, `RAIN_GAUGE`, `TILT`, `TEMPERATURE`, `PORE_PRESSURE`, `GEOPHONE`, and `STRAIN`. Includes full provenance schema (`site_id`, `state`, `observation_time`, `available_time`, `received_time`, `ingested_time`, `source`, `raw_reference`).
* **Mawiongrim Field Telemetry Ingestion Pipeline**: Ingestion of 696 continuous hourly multi-parameter field records from NIT Meghalaya's Mawiongrim station (`NER_SAFE_DATA/SENSORS/mawiongrim_telemetry.csv`) covering rainfall, piezometric water level, 3-depth inclinometers, and 5 suction tensiometers.
* **Automated Multi-Source Cadence Scheduler** (`live_monitoring_scheduler.py`): Autonomous polling loop with observation hash/timestamp deduplication, freshness tracking, and decoupled observation vs. ingestion timestamps.
* **Zero-Network Engine & Local Sensor Alerts** (`zero_network_manager.py`, `local_sensor_alert_engine.py`): Multi-stage persistence and hysteresis evaluation yielding `WATCH`, `WARNING`, `HIGH`, and `CRITICAL` local alerts during complete Level 4 communication blackouts (no cellular, no internet).
* **Live REST Endpoints** (`server.py`): Exposing `/api/sensors/sources`, `/api/sensors/latest`, `/api/sensors/mawiongrim`, `/api/monitoring/sources/health`, `/api/sensors/reading`, and `/api/monitoring/poll`.
* **NASA Earthdata Discovery Engine**: Automated discovery of GPM NRT Half-Hourly (`GPM_3IMERGHHE_V07`) and SMAP L3 Enhanced Soil Moisture (`SPL3SMP_E_006`) via NASA CMR API.

---

### Category B: Things Requiring Credentials (User Configuration)
* **Copernicus CDSE OAuth2 API Credentials (Sentinel-1 SAR & InSAR SLC Downloads)**:
  * *Purpose*: Automated authenticated download of Sentinel-1 Level-1 Single Look Complex (IW SLC) archives for genuine repeat-pass InSAR deformation processing.
  * *Action Required*: Register at [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) and set environment variables:
    ```powershell
    [System.Environment]::SetEnvironmentVariable("CDSE_CLIENT_ID", "<YOUR_CLIENT_ID>", "User")
    [System.Environment]::SetEnvironmentVariable("CDSE_CLIENT_SECRET", "<YOUR_CLIENT_SECRET>", "User")
    ```
  * *Current State*: `insar_pair_selector.py` and `insar_processing.py` report `INSAR_DATA_ACCESS = AUTH_REQUIRED` and `INSAR_WAITING_FOR_COMPATIBLE_PAIR`. Zero fake deformation rasters are created.
* **NASA Earthdata Credentials (Direct HDF5 Binary Streaming)**:
  * *Status*: Active credentials already present on the host environment in `C:\Users\hp\.netrc`. No further user credential action required for NASA CMR or GPM NRT discovery.

---

### Category C: Things Requiring Institutional Permission & Data Sharing MoUs
* **IMD AWS Live Telemetry (Automatic Weather Stations)**:
  * *Why Blocked*: India Meteorological Department real-time station telemetry is not exposed as a public open REST API. It requires an official institutional Memorandum of Understanding (MoU) with the Ministry of Earth Sciences (MoES).
  * *Current Operational State*: System routes precipitation monitoring to NASA GPM IMERG NRT and correctly reports `AWAITING_INSTITUTIONAL_ACCESS`.
  * *User Action Required*: Formalize an administrative data exchange agreement between the state disaster management authority (SDMA) and MoES/IMD.

---

### Category D: Things Requiring Physical Equipment
* **Physical Siren / Horn Actuator for Zero-Network Level 4 Warnings**:
  * *Why Required*: Physical audible siren sound cannot be generated by software alone in a localized mountain village without physical transducer hardware.
  * *What Has Been Built*: Software dispatch trigger (`LOCAL_SIREN_TRIGGER`), offline dashboard alert banner, and local emergency broadcast payloads.
  * *User Action Required*: Connect a 12V high-decibel siren horn via a 5V relay module to the local edge node GPIO pin.
* **Secondary / Supplementary DIY Field Sensor (Optional ESP32)**:
  * *Status*: Standalone reference firmware (`esp32_reference_gateway.ino`) and software gateway (`esp32_reference_gateway.py`) are fully implemented.
  * *Directive*: Mandated **ONLY** if existing institutional field deployments cannot be accessed. Do NOT buy an ESP32 as the primary solution.

---

### Category E: Things Requiring Access from Meghalaya / Mizoram Authorities & Institutions
* **NIT Meghalaya Mawiongrim Live Cellular Telemetry Stream**:
  * *Discovered Station*: Mawiongrim Landslide Monitoring Station, East Khasi Hills, Meghalaya (Dr. Shubhankar Majumdar, Dr. Smrutirekha Sahoo, Kamal Das, NIT Meghalaya).
  * *Current Access Level*: 696 continuous hourly field records (Dec 1–30, 2022) downloaded and ingested into NER-SAFE.
  * *Why Live Stream is Blocked*: The field node transmits over a closed cellular 4G/GSM WSN uplink directly to internal laboratory servers at NIT Meghalaya. No public internet API endpoint is published.
  * *User Action Required*: Contact the Department of Civil Engineering & ECE at NIT Meghalaya (Shillong campus) to establish a data-forwarding webhook or MQTT bridge to the NER-SAFE edge server.
* **MIRSAC / Mizoram SDMA / SILAAS (Aizawl Slope Monitoring)**:
  * *Discovered System*: Mizoram Remote Sensing Application Centre (MIRSAC) / SILAAS slope instability advisory network in Aizawl (Laipuitlang, Ngaizel, Tlangnuam).
  * *Current Access Level*: Publishes periodic municipal landslide hazard bulletins, zone maps, and rainfall advisories.
  * *Why Live Stream is Blocked*: SILAAS operates as an administrative advisory platform, not an open public machine-to-machine REST/MQTT telemetry stream.
  * *User Action Required*: Establish an institutional data-sharing protocol with MIRSAC and Mizoram SDMA to ingest raw telemetry or digital advisory feeds.

---

### Category F: Hardware Feasibility & Constraints
* **InSAR Memory Optimization on Intel i3-N305 (8 GB RAM)**:
  * *Status*: Full Sentinel-1 SLC frames exceed RAM. Pipeline is configured to use **sub-swath burst extraction** (`TARGET_BURSTS`) and $512 \times 512$ SNAPHU unwrapping tiles to run safely under 1.5 GB memory footprint without system instability.
* **PyTorch Deep Learning Execution**:
  * *Status*: Successfully resolved using native CPU-compatible PyTorch 2.14.0 with Microsoft Visual C++ 2022 runtimes. Model trained and validated across 5 geographic folds in ~38s, generating `cnn_susceptibility_probability.tif` without OOM.
* **Multi-Gigabyte Deep Learning AI Image Forensics (Citizen Media)**:
  * *Limitation*: Heavy 4GB+ vision transformer models (e.g., TruFor) cannot run concurrently on 8GB shared RAM.
  * *Current Operational Solution*: CPU-efficient media integrity pipeline analyzing SHA-256 digests, EXIF metadata, camera software tags, Laplacian blur, and GPS plausibility (`media_integrity_analyzer.py`).

---

## 3. USER ACTION CHECKLIST PRIORITIZED

| Priority | Category | Action Item | Target Entity | Impact on NER-SAFE |
| :---: | :---: | :--- | :--- | :--- |
| **P1** | **B** | Configure Copernicus CDSE OAuth2 credentials (`CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`) | **Copernicus User Portal** | Enables automated Sentinel-1 IW SLC repeat-pass pair download for InSAR |
| **P1** | **E** | Request real-time telemetry forwarding webhook / MQTT bridge | **NIT Meghalaya** (Civil Eng. Dept.) | Converts Mawiongrim from historical batch ingestion to live continuous telemetry |
| **P2** | **E** | Establish data exchange agreement for Aizawl slope advisories | **MIRSAC / Mizoram SDMA** | Ingests real-time Aizawl slope stability data into NER-SAFE |
| **P2** | **C** | Secure institutional weather telemetry MoU | **IMD / Ministry of Earth Sciences** | Connects Shillong & Aizawl IMD AWS ground stations directly |
| **P3** | **D** | Connect physical 12V siren relay to edge gateway GPIO | **Local Edge Hardware** | Translates Level 4 zero-network software siren triggers into physical sound |
