# NER-SAFE PHASE 5: FINAL OPERATIONAL TECHNOLOGY STACK

**Document ID:** `NER-SAFE-TECHSTACK-PHASE5-20260921`  
**Author:** Antigravity (Advanced Agentic Coding)  
**Execution Date:** September 21, 2026  
**Governance Standard:** SIH 26001 Operational Deployment Baseline  

---

## 1. Technology Audit Principles

To prevent technical debt and inaccurate claims during Hackathon evaluation, the NER-SAFE technology stack is classified into two distinct categories:
1. **`CURRENTLY USED IN PRODUCTION CODE`**: Actively running in the operational workspace, evaluated in regression test suites, and deployed in the running server.
2. **`FUTURE ARCHITECTURE / CLOUD ROADMAP`**: Architectural designs documented for post-hackathon national deployment; **strictly not required or claimed for local hackathon evaluation**.

---

## 2. Currently Used Operational Technology Stack

| Technology / Library | Version / Runtime | Component | Actual Current Operational Use | Status |
| :--- | :---: | :--- | :--- | :---: |
| **Python** | `3.14.0 (64-bit)` | Core Runtime | Coordinates all operational ingestion, calculation, scheduling, and REST endpoints. | **ACTIVE (OPERATIONAL)** |
| **XGBoost** | `2.1.1+` | Component 10 | **Authoritative Sole Production AI Model** (`calibrated_xgboost_model.joblib`, SHA-256: `45544c7f...`). | **ACTIVE (OPERATIONAL)** |
| **Scikit-Learn** | `1.5.0+` | Component 10 | Probability calibration (`CalibratedClassifierCV`) and spatial evaluation metrics. | **ACTIVE (OPERATIONAL)** |
| **PyTorch** | `2.14.0+cpu` | Component 10 (Research) | **Research Shadow CNN Model** (`cnn_model.py`); runs parallel inference at strictly **0.00 operational weight**. | **ACTIVE (RESEARCH)** |
| **NumPy & SciPy** | `2.0.0+` | Core Spatial | Vectorized array extraction for JAXA GSMaP (CSV) and NASA GPM (HDF5) regional subsets. | **ACTIVE (OPERATIONAL)** |
| **h5py** | `3.11.0+` | Component 01 / GPM | Authenticated binary parsing and regional extraction of NASA GPM IMERG HDF5 granules. | **ACTIVE (OPERATIONAL)** |
| **Rasterio / GDAL** | `1.3.10+` | Component 02 / DEM | 30m SRTM elevation raster extraction, slope derivatives, and dynamic trigger overlays. | **ACTIVE (OPERATIONAL)** |
| **SQLite3** | Native standard lib | Database (`WAL` mode) | Local persistence of live assessments (`live_assessments`), citizen reports, and audit logs. | **ACTIVE (OPERATIONAL)** |
| **HTTP Server (Python)** | Native `ThreadingHTTPServer` | Server (`server.py`) | REST API handling 24 endpoints (`/api/assessment/current`, `/api/monitoring/status`, etc.). | **ACTIVE (OPERATIONAL)** |
| **Leaflet** | `1.9.4` (Vanilla JS) | Web-GIS 2D Map | Primary resilient 2D operations map; renders 48 hotspots, rainfall isobars, roads, and buildings. | **ACTIVE (OPERATIONAL)** |
| **CesiumJS** | `1.119+` (CDN) | Web-GIS 3D Map | 3D topographic terrain viewer (`#cesiumContainer`) with automated WebGL fallback to 2D Leaflet. | **ACTIVE (OPERATIONAL)** |
| **FFmpeg** | System binary | Video Pipeline | Normalizes citizen video uploads to 720p H.264, extracts I-frame keyframes, and parses containers. | **ACTIVE (OPERATIONAL)** |
| **ImageHash / PIL** | `4.3.1+` | Image/Video Forensics | Perceptual hashing (pHash) for near-duplicate citizen photo and video detection. | **ACTIVE (OPERATIONAL)** |
| **Requests / ftplib** | Native / `2.32+` | Ingestion Clients | Authenticated passive FTP client for JAXA EORC; authenticated HTTPS client for NASA CMR. | **ACTIVE (OPERATIONAL)** |
| **Google Drive Client** | Abstracted API | Storage Engine | Secondary offsite archive sync for periodic backup staging (`storage_engine.py`). | **ACTIVE (OPERATIONAL)** |

---

## 3. Future Architecture & Cloud Migration Stack (Disclaimed for SIH)

The following technologies were referenced in preliminary architectural pitch decks as future cloud-scale targets, but are **NOT required for local competition evaluation**:

| Technology | Legacy Pitch Role | Current Code State | Actual Production Alternative Used Today | Cloud Migration Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL / PostGIS** | Enterprise spatial database | Not required locally | SQLite WAL mode with spatial GeoJSON & in-memory NumPy spatial queries | Scale $> 100,000$ active municipal telemetry streams |
| **Redis** | In-memory message broker & cache | Not required locally | In-memory Python thread-safe dictionaries with SQLite persistence | Multi-node distributed worker cluster |
| **Apache Airflow** | Scheduled ETL orchestration | Not required locally | Autonomous scheduler (`nersafe_autonomous_scheduler.py`) with PID file locks | Enterprise workflow scheduling across multiple government servers |
| **FastAPI / Uvicorn** | Async ASGI REST API | Partially scaffolded | Lightweight standard library `ThreadingHTTPServer` (Zero external daemon dependency) | Transition to multi-worker ASGI web servers |
| **Kubernetes (K8s)** | Container orchestration | Containerfile present | Standalone single-instance edge execution | State Emergency Operations Center (SEOC) high-availability clustering |
| **AWS / MeitY Cloud** | National cloud deployment | Abstracted in `storage_engine.py` | 100% local laptop / workstation execution | Formal execution of State Disaster Management Authority (SDMA) MoU |

---

## 4. Key Architectural Takeaways for Evaluators

1. **Zero Cloud Dependency:** The entire system runs locally on standard x86-64 hardware without requiring active AWS, GCP, or Azure subscriptions.
2. **Minimal External Dependencies:** Core inference and risk fusion execute in pure Python using NumPy and pre-compiled XGBoost binary libraries.
3. **Resilient Edge Deployment:** The chosen stack (SQLite WAL + ThreadingHTTPServer + Vanilla JS Leaflet) guarantees survivability during field disaster deployments with zero external server reliance.
