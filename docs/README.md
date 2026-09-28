# 📚 NER-SAFE Documentation Directory

This directory contains comprehensive architectural, validation, audit, and operational documentation for the **NER-SAFE** early warning and landslide risk monitoring platform.

---

## 🏛️ 1. Architecture & Specifications (`docs/architecture/`)
Core operational specifications and system architecture:
* [`NER_SAFE_ARCHITECTURE_CURRENT_STATE.md`](architecture/NER_SAFE_ARCHITECTURE_CURRENT_STATE.md) — Operational architecture and multi-tier data flow map.
* [`NER_SAFE_PHASE3_FINAL_REALTIME_ARCHITECTURE.md`](architecture/NER_SAFE_PHASE3_FINAL_REALTIME_ARCHITECTURE.md) — Real-time operational data strategy and pipeline topology.
* [`NER_SAFE_HEATMAP_SPECIFICATION.md`](architecture/NER_SAFE_HEATMAP_SPECIFICATION.md) — Dynamic GIS heatmap generation architecture and color ramp specification.
* [`NER_SAFE_LIVE_ASSESSMENT_INPUT_POLICY.md`](architecture/NER_SAFE_LIVE_ASSESSMENT_INPUT_POLICY.md) — Assessment input governance, freshness windows, and reassessment policies.
* [`NER_SAFE_LIVE_SYSTEM_STATUS.md`](architecture/NER_SAFE_LIVE_SYSTEM_STATUS.md) — Live multi-sensor ingestion and autonomous monitoring status.
* [`NER_SAFE_PHASE5_FINAL_TECHNOLOGY_STACK.md`](architecture/NER_SAFE_PHASE5_FINAL_TECHNOLOGY_STACK.md) — Technology stack justification and component inventory.
* [`NER_SAFE_GROUND_SENSOR_HARDWARE_REQUIREMENTS.md`](architecture/NER_SAFE_GROUND_SENSOR_HARDWARE_REQUIREMENTS.md) — IoT tiltmeter/piezometer reference specifications.

---

## 🔬 2. Scientific Validation & Model Benchmarks (`docs/validation/`)
Independent scientific verification and machine learning validation reports:
* [`COMPONENT_15_VALIDATION_REPORT.md`](validation/COMPONENT_15_VALIDATION_REPORT.md) — Temporal forecasting engine and early warning acceptance gates.
* [`NER_SAFE_RF_XGBOOST_CNN_MODEL_SELECTION_AUDIT.md`](validation/NER_SAFE_RF_XGBOOST_CNN_MODEL_SELECTION_AUDIT.md) — 3-way machine learning benchmark (XGBoost vs. Random Forest vs. PyTorch CNN).
* [`NER_SAFE_CANONICAL_MODEL_EVALUATION.md`](validation/NER_SAFE_CANONICAL_MODEL_EVALUATION.md) — Canonical model evaluation and statistical protocol.
* [`NER_SAFE_XGBOOST_PRODUCTION_PROMOTION_VALIDATION.md`](validation/NER_SAFE_XGBOOST_PRODUCTION_PROMOTION_VALIDATION.md) — Calibrated XGBoost v1.1 production promotion audit.
* [`NER_SAFE_SINGLE_PRODUCTION_MODEL_CORRECTION_REPORT.md`](validation/NER_SAFE_SINGLE_PRODUCTION_MODEL_CORRECTION_REPORT.md) — Model governance and single production model enforcement.
* [`NER_SAFE_PYTORCH_CNN_LIVE_INFERENCE_VALIDATION.md`](validation/NER_SAFE_PYTORCH_CNN_LIVE_INFERENCE_VALIDATION.md) — Parallel research CNN shadow model inference validation.
* [`NER_SAFE_CNN_LIVE_A_B_VALIDATION.md`](validation/NER_SAFE_CNN_LIVE_A_B_VALIDATION.md) — Controlled A/B spatial testing report.
* [`NER_SAFE_INSAR_METHODOLOGY_VALIDATION.md`](validation/NER_SAFE_INSAR_METHODOLOGY_VALIDATION.md) — Sentinel-1 repeat-pass InSAR interferometry validation.
* [`NER_SAFE_INSAR_MULTITEMPORAL_VALIDATION.md`](validation/NER_SAFE_INSAR_MULTITEMPORAL_VALIDATION.md) — Multi-temporal SLC stack accumulation report.
* [`NER_SAFE_INSAR_REAL_DATA_VALIDATION.md`](validation/NER_SAFE_INSAR_REAL_DATA_VALIDATION.md) — Genuine IW SLC acquisition and phase unwrapping validation.
* [`NER_SAFE_SENTINEL1_SLC_LIVE_ACQUISITION_VALIDATION.md`](validation/NER_SAFE_SENTINEL1_SLC_LIVE_ACQUISITION_VALIDATION.md) — CDSE S3 automated live ingestion validation.
* [`NER_SAFE_SENTINEL1_SLC_LIVE_AUTOMATION_VALIDATION.md`](validation/NER_SAFE_SENTINEL1_SLC_LIVE_AUTOMATION_VALIDATION.md) — Automated live SLC acquisition pipeline tests.
* [`NER_SAFE_SMAP_NRT_LIVE_VALIDATION.md`](validation/NER_SAFE_SMAP_NRT_LIVE_VALIDATION.md) — NASA SMAP SPL2SMP_NRT soil moisture live validation.
* [`NER_SAFE_LIVE_GPM_TO_DASHBOARD_VALIDATION.md`](validation/NER_SAFE_LIVE_GPM_TO_DASHBOARD_VALIDATION.md) — NASA GPM IMERG to live dashboard pipeline validation.
* [`NER_SAFE_PHASE1_FORENSIC_BASELINE_AUDIT.md`](validation/NER_SAFE_PHASE1_FORENSIC_BASELINE_AUDIT.md) — Baseline dataset integrity and CRS audit.
* [`NER_SAFE_PHASE2_JAXA_GSMAP_NOW_FORENSIC_VERIFICATION.md`](validation/NER_SAFE_PHASE2_JAXA_GSMAP_NOW_FORENSIC_VERIFICATION.md) — JAXA GSMaP_NOW real-time FTP access and parsing verification.
* [`NER_SAFE_PHASE4A_IMPLEMENTATION_REPORT.md`](validation/NER_SAFE_PHASE4A_IMPLEMENTATION_REPORT.md) — Phase 4A operational implementation audit.
* [`NER_SAFE_PHASE4B_FULL_OPERATIONAL_LIVE_VALIDATION.md`](validation/NER_SAFE_PHASE4B_FULL_OPERATIONAL_LIVE_VALIDATION.md) — Full multi-sensor operational live test report.
* [`NER_SAFE_PHASE5_FINAL_OPERATIONAL_READINESS.md`](validation/NER_SAFE_PHASE5_FINAL_OPERATIONAL_READINESS.md) — Final SIH deployment readiness baseline.
* [`NER_SAFE_PHASE5_SIH_TRACEABILITY_FINAL.md`](validation/NER_SAFE_PHASE5_SIH_TRACEABILITY_FINAL.md) — Final SIH 26001 requirement traceability matrix.
* [`NER_SAFE_PROSPECTIVE_VALIDATION_FRAMEWORK.md`](validation/NER_SAFE_PROSPECTIVE_VALIDATION_FRAMEWORK.md) — Prospective evidence logging and statistical framework.
* [`NER_SAFE_PROSPECTIVE_POPULATION_AUDIT.md`](validation/NER_SAFE_PROSPECTIVE_POPULATION_AUDIT.md) — Real-time prospective ledger population audit.
* [`NER_SAFE_REAL_OBSERVATION_INTEGRITY_AUDIT.md`](validation/NER_SAFE_REAL_OBSERVATION_INTEGRITY_AUDIT.md) — Regression reconciliation and scientific integrity audit.
* [`NER_SAFE_REAL_LIVE_SOURCE_ACTIVATION_VALIDATION.md`](validation/NER_SAFE_REAL_LIVE_SOURCE_ACTIVATION_VALIDATION.md) — Real-time satellite source activation tests.
* [`NER_SAFE_REAL_LIVE_POPULATION_VERIFICATION.md`](validation/NER_SAFE_REAL_LIVE_POPULATION_VERIFICATION.md) — Autonomous evidence ingestion verification.
* [`NER_SAFE_GIS_3D_RUNTIME_FINAL_VALIDATION_REPORT.md`](validation/NER_SAFE_GIS_3D_RUNTIME_FINAL_VALIDATION_REPORT.md) — CesiumJS 3D digital elevation tiling validation.
* [`NER_SAFE_GIS_VISUALIZATION_CORRECTION_REPORT.md`](validation/NER_SAFE_GIS_VISUALIZATION_CORRECTION_REPORT.md) — 2D Leaflet and 3D Cesium visualization synchronization.
* [`NER_SAFE_OPERATIONAL_WEBSITE_SYNCHRONIZATION_REPORT.md`](validation/NER_SAFE_OPERATIONAL_WEBSITE_SYNCHRONIZATION_REPORT.md) — Live website state sync verification.
* [`NER_SAFE_SIH_FINAL_DEMO_PREFLIGHT.md`](validation/NER_SAFE_SIH_FINAL_DEMO_PREFLIGHT.md) — Preflight operational checklist.
* [`NER_SAFE_SIH_LIVE_MONITORING_CONTROL_VALIDATION.md`](validation/NER_SAFE_SIH_LIVE_MONITORING_CONTROL_VALIDATION.md) — Master monitoring control panel validation.
* [`NER_SAFE_VALIDATED_TO_LIVE_ACTIVATION_REPORT.md`](validation/NER_SAFE_VALIDATED_TO_LIVE_ACTIVATION_REPORT.md) — Pipeline autonomous activation verification.

---

## 📖 3. Operational Guides & Runbooks (`docs/guides/`)
Guides for judges, evaluators, and system administrators:
* [`NER_SAFE_RELEASE_MANIFEST.md`](guides/NER_SAFE_RELEASE_MANIFEST.md) — Authoritative release baseline and SHA-256 asset manifest.
* [`NER_SAFE_PHASE5_JUDGE_DEMONSTRATION_RUNBOOK.md`](guides/NER_SAFE_PHASE5_JUDGE_DEMONSTRATION_RUNBOOK.md) — Step-by-step judge demonstration script and test workflows.
* [`NER_SAFE_JUDGE_QUICK_START.md`](guides/NER_SAFE_JUDGE_QUICK_START.md) — 60-second evaluator launch runbook.
* [`NER_SAFE_JUDGE_RUNTIME_TOOLS.md`](guides/NER_SAFE_JUDGE_RUNTIME_TOOLS.md) — Demonstration day runtime utilities.
* [`NER_SAFE_JUDGE_DEMO_BASELINE.md`](guides/NER_SAFE_JUDGE_DEMO_BASELINE.md) — Demo baseline reproducibility guide.
* [`NER_SAFE_INSAR_PROCESSING_GUIDE.md`](guides/NER_SAFE_INSAR_PROCESSING_GUIDE.md) — Sentinel-1 SLC download and interferometric processing guide.
* [`NER_SAFE_AGENT_SKILLS_GUIDE.md`](guides/NER_SAFE_AGENT_SKILLS_GUIDE.md) — Architecture and subsystem guide for engineering agents.

---

## 🔍 4. System Audits & Evidence Logs (`docs/audits/`)
Technical audit histories and component forensic reports:
* [`NER_SAFE_SOURCE_REGISTRY.md`](audits/NER_SAFE_SOURCE_REGISTRY.md) — Comprehensive earth observation data source registry and acquisition modes.
* [`NER_SAFE_SOURCE_STATUS_AND_UI_CONSISTENCY_AUDIT.md`](audits/NER_SAFE_SOURCE_STATUS_AND_UI_CONSISTENCY_AUDIT.md) — UI status badge consistency and model lineage audit.
* [`NER_SAFE_CURRENT_STATE_AUDIT.md`](audits/NER_SAFE_CURRENT_STATE_AUDIT.md) — Complete repository state and subsystem audit.
* [`NER_SAFE_PRD_CURRENT_STATE_AUDIT.md`](audits/NER_SAFE_PRD_CURRENT_STATE_AUDIT.md) — PRD requirement alignment and verification audit.
* [`NER_SAFE_IMD_LIVE_INTEGRATION_REPORT.md`](audits/NER_SAFE_IMD_LIVE_INTEGRATION_REPORT.md) — IMD Mausam API live weather and warning integration report.
* [`NER_SAFE_GSMAP_REALTIME_FORENSIC_REPORT.md`](audits/NER_SAFE_GSMAP_REALTIME_FORENSIC_REPORT.md) — GSMaP_NOW hourly precipitation latency audit.
* [`NER_SAFE_CDSE_CONNECTIVITY_REPORT.md`](audits/NER_SAFE_CDSE_CONNECTIVITY_REPORT.md) — Copernicus Data Space Ecosystem API connectivity report.
* [`NER_SAFE_INSAR_CURRENT_STATE_AUDIT.md`](audits/NER_SAFE_INSAR_CURRENT_STATE_AUDIT.md) — InSAR subsystem forensic report.
* [`NER_SAFE_GSI_SACHET_BHUVAN_EXTERNAL_DATA_AUDIT.md`](audits/NER_SAFE_GSI_SACHET_BHUVAN_EXTERNAL_DATA_AUDIT.md) — External national spatial data acquisition audit.
* [`NER_SAFE_OSINT_PREDICTION_VALIDATION_REPORT.md`](audits/NER_SAFE_OSINT_PREDICTION_VALIDATION_REPORT.md) — OSINT disaster intelligence and outcome loop report.
* [`NER_SAFE_OSINT_VALIDATION_METHODOLOGY_CORRECTION.md`](audits/NER_SAFE_OSINT_VALIDATION_METHODOLOGY_CORRECTION.md) — OSINT validation methodology correction audit.
* [`NER_SAFE_OSIRIS_COMPATIBILITY_COVERAGE_AUDIT.md`](audits/NER_SAFE_OSIRIS_COMPATIBILITY_COVERAGE_AUDIT.md) — OSIRIS AI platform compatibility audit.
* [`NER_SAFE_LIVE_DATA_SOURCE_AUDIT.md`](audits/NER_SAFE_LIVE_DATA_SOURCE_AUDIT.md) — Multi-feed live observation provenance audit.
* [`NER_SAFE_LIVE_UPDATE_LATENCY_REPORT.md`](audits/NER_SAFE_LIVE_UPDATE_LATENCY_REPORT.md) — Ingestion and dashboard latency benchmark.
* [`NER_SAFE_LIVE_OUTCOME_CLOSURE_AUDIT.md`](audits/NER_SAFE_LIVE_OUTCOME_CLOSURE_AUDIT.md) — Prediction-to-outcome closure audit.
* [`NER_SAFE_OUTCOME_INGESTION_AND_TEST_HEALTH_AUDIT.md`](audits/NER_SAFE_OUTCOME_INGESTION_AND_TEST_HEALTH_AUDIT.md) — Ingestion health and test suite audit.
* [`NER_SAFE_REAL_INGESTION_AUDIT.md`](audits/NER_SAFE_REAL_INGESTION_AUDIT.md) — Real-world sensor ingestion audit.
* [`NER_SAFE_CLEAN_LIVE_STARTUP_AUDIT.md`](audits/NER_SAFE_CLEAN_LIVE_STARTUP_AUDIT.md) — Clean live pipeline startup audit.
* [`NER_SAFE_AUTOMATIC_LIVE_STARTUP_REPORT.md`](audits/NER_SAFE_AUTOMATIC_LIVE_STARTUP_REPORT.md) — Automatic pipeline startup audit.
* [`NER_SAFE_FINAL_DEMO_READINESS_AUDIT.md`](audits/NER_SAFE_FINAL_DEMO_READINESS_AUDIT.md) — Pre-presentation demonstration readiness audit.
* [`NER_SAFE_END_TO_END_DEMO.md`](audits/NER_SAFE_END_TO_END_DEMO.md) — Multi-tier demonstration workflow specification.
* [`NER_SAFE_GOOGLE_DRIVE_ARCHIVE_STATUS.md`](audits/NER_SAFE_GOOGLE_DRIVE_ARCHIVE_STATUS.md) — Google Drive heavy-data backup audit.
* [`NER_SAFE_UI_COMPONENT_FORENSIC_AUDIT_REPORT.md`](audits/NER_SAFE_UI_COMPONENT_FORENSIC_AUDIT_REPORT.md) — UI component to backend API trace audit.
