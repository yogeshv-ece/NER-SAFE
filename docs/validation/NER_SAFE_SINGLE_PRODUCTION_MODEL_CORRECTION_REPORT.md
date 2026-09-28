# NER-SAFE: SINGLE PRODUCTION MODEL ARCHITECTURE CORRECTION REPORT
**Authoritative Architectural Governance & Forensics**  
**SIH Problem Statement 26001:** AI-Based Early Warning and Landslide Risk Monitoring System in NER  
**System Designation:** NER-SAFE Operational Runtime  
**Date:** September 21, 2026  
**Status:** COMPLETED & CERTIFIED  

---

## Executive Summary

As mandated by system governance, NER-SAFE has been architecturally corrected to enforce **ONE SINGLE PRODUCTION AI MODEL**:
$$\text{Production AI Model} = \mathbf{Calibrated\ XGBoost\ v1.1}$$

All operational fallback paths from XGBoost to Random Forest, PyTorch CNN, or any other machine-learning algorithm have been permanently removed. If the production XGBoost model cannot execute or its artifact is missing, the system transitions strictly to $\text{MODEL\_STATUS} = \mathbf{MODEL\_UNAVAILABLE}$ and $\text{RISK\_STATUS} = \mathbf{CURRENT\ RISK\ UNAVAILABLE}$, with $\text{current\_risk\_available} = \mathbf{False}$. No simulated, synthetic, or alternative model risk scores are fabricated.

---

## 1. Previous Architecture

In earlier transitional phases (v1.0.0 through v1.1.0-RC), NER-SAFE supported dual or comparative execution modes:
1. **Historical Baseline:** Random Forest (`calibrated_susceptibility_model.joblib` / `random_forest_susceptibility.joblib`) served as the v1.0.0 operational anchor (`SUSCEPTIBILITY_MODEL=rf`).
2. **Promoted Tabular Model:** Calibrated XGBoost (`calibrated_xgboost_model.joblib`) was promoted as primary, but retained an automatic, silent/non-silent fallback to Random Forest in `live_assessment_service.py` and `susceptibility_provider.py`.
3. **Model Selection Switching:** `SusceptibilityProviderManager` inspected the `SUSCEPTIBILITY_MODEL` environment variable and dynamically switched active providers (`rf`, `xgboost`, `cnn`).
4. **Dashboard Provenance Ambiguity:** UI cards and status endpoints declared `"XGBoost Primary, Random Forest Fallback"`, suggesting multi-model ambiguity in production.

---

## 2. Forensic Audit: Random Forest Fallback Locations Found

A full codebase ripgrep audit identified all points of operational model switching and fallback:

| Source File | Line(s) | Previous Code / Behavior | Nature of Dependency |
|---|---|---|---|
| `susceptibility_provider.py` | 8–11, 189–211 | `get_active_provider_name()` checked `env_choice` and defaulted to `"rf"`; on XGB failure, logged reason and returned `"rf"` | Operational Fallback & Selector |
| `susceptibility_provider.py` | 212–220 | `get_active_provider()` returned `self.rf_provider` when XGBoost failed | Operational Fallback |
| `susceptibility_provider.py` | 60–84 | `RFProductionProvider` declared `PRODUCTION_FROZEN_RETAINED` as an active production provider | Production Persona |
| `live_assessment_service.py` | 482–511 | `except Exception as e: is_fallback = True; active_model_id = "rf"` silently reverted to RF | Operational Fallback |
| `fusion_engine.py` | 98–100 | Metadata declared `"provider": "USGS / NER-SAFE Calibrated Model (XGBoost Primary, Random Forest Fallback)"` | Metadata Fallback Exposure |
| `server.py` | 421–430 | `/api/monitoring/multimodal` lacked explicit `operational_fallback: NONE` declaration | API Contract |
| `live_sensor_server_extension.py` | 350–384 | `/api/models/comparison` declared `PRODUCTION_FROZEN_RF_RETAINED` with RF as production model | API Contract |
| `ner_safe_live_dashboard.html` | 2496 | UI card displayed `XGBoost (PRIMARY) • Fallback: Random Forest (FALLBACK ONLY)` | UI Fallback Wording |
| `ner_safe_live_dashboard_extended.html` | 2053, 2135, 2137, 2149, 2302 | UI displayed `XGBOOST OFFICIAL • RF FALLBACK` and `FALLBACK MODEL: Calibrated Random Forest` | UI Fallback Wording |

---

## 3. Operational Paths Removed / Disabled

Every identified operational fallback path was eliminated:

1. **`susceptibility_provider.py`**:
   - `RFProductionProvider` was re-engineered as `RFHistoricalBaselineProvider` and marked strictly `RESEARCH/HISTORICAL ONLY` with zero operational role.
   - `get_active_provider_name()` was stripped of environment switching; it now returns `"xgboost"` if available or `"MODEL_UNAVAILABLE"` if failed.
   - `get_active_provider()` strictly returns `self.xgb_provider`. If XGBoost is unavailable, it raises a `RuntimeError("MODEL_UNAVAILABLE: ...")`. It **never** returns Random Forest, CNN, or any other model.
   - `operational_fallback` was locked to `"NONE"`.

2. **`live_assessment_service.py`**:
   - Removed `except Exception: active_model_id = "rf"`.
   - On XGBoost exception or artifact absence, the engine marks:
     - `model_status = "UNAVAILABLE"`
     - `assessment_status = "MODEL_UNAVAILABLE"`
     - `risk_status = "CURRENT RISK UNAVAILABLE"`
     - `current_risk_available = False`
     - Hotspot operational risk scores are set to `None` with tier `"MODEL_UNAVAILABLE"`.
     - Zero risk scores are fabricated or invented.

---

## 4. XGBoost-Only Production Architecture

The production runtime is now strictly decoupled into:
- **One Operational AI Model:** Calibrated XGBoost v1.1
- **Multiple Live Data Sources:** JAXA GSMaP_NOW, NASA GPM IMERG NRT, NASA SMAP L3, ESA Sentinel-1 C-SAR, NIT Meghalaya ground telemetry.
- **Contextual Sources:** GSI Bhusanket bulletins, NDMA SACHET CAP feeds, OSINT field reports, Crowdsourced citizen observations.
- **Decoupled Research Components (Operational Weight = 0.00):** PyTorch Spatial CNN, Sentinel-1 InSAR SBAS/PSI, Component 15 Temporal Forecaster, Historical Random Forest Benchmark.

```
   [JAXA GSMaP_NOW / NASA GPM]  [NASA SMAP]  [Sentinel-1 SAR]  [Ground Telemetry]
                 \                  |               /                 /
                  \                 |              /                 /
                   v                v             v                 v
            ================================================================
                      DATA ACQUISITION & FEATURE PIPELINE
            ================================================================
                                    |
                 +------------------+------------------+
                 | Point Features                      |
                 v                                     v
       +--------------------+                +--------------------+
       |  CALIBRATED        |                |  RESEARCH PIPELINE |
       |  XGBOOST v1.1      |                |  - PyTorch CNN     |
       |  (SOLE PROD MODEL) |                |  - InSAR Multi-Temp|
       |  PR-AUC: 0.3608    |                |  - C15 Temporal    |
       |  Hash: 45544c...   |                |  - Historical RF   |
       +--------------------+                +--------------------+
                 |                                     |
                 v Susceptibility (40%)                v Weight = 0.00
       ================================================================
           LOCKED FOUR-FACTOR RISK FUSION (0.40 / 0.30 / 0.20 / 0.10)
       ================================================================
                 |
                 +--> Normal Execution  --> CURRENT_ASSESSMENT_ACTIVE
                 |
                 +--> XGBoost Failure   --> MODEL_UNAVAILABLE (NO FALLBACK)
```

---

## 5. Model Failure Behavior vs. Normal Behavior

| Scenario | Model Status | Assessment Status | Current Risk Available | Hotspot Risk Scores | Fallback Invoked? |
|---|---|---|---|---|---|
| **XGBoost Normal** | `AVAILABLE` | `CURRENT_ASSESSMENT_ACTIVE` | `True` | Computed via $0.40 \times \text{XGB} + \text{Dynamic}$ | None (`operational_fallback: NONE`) |
| **XGBoost Missing Artifact** | `UNAVAILABLE` | `MODEL_UNAVAILABLE` | `False` | `None` (Tier: `MODEL_UNAVAILABLE`) | **NONE** (Zero fallback) |
| **XGBoost Inference Exception**| `UNAVAILABLE` | `MODEL_UNAVAILABLE` | `False` | `None` (Tier: `MODEL_UNAVAILABLE`) | **NONE** (Zero fallback) |

When the model is unavailable:
1. `current_risk_available = False` is returned across all REST APIs and GIS endpoints.
2. The system distinguishes `CURRENT_ASSESSMENT` (which is `MODEL_UNAVAILABLE`) from `LAST_VALID_ASSESSMENT` (which preserves the previous valid assessment metadata as a historical record).
3. No new automated risk alerts are generated or dispatched.

---

## 6. Distinction: Model Failure vs. Data-Source Failover

NER-SAFE maintains a clean, rigorous architectural separation between:

1. **Data-Source Failover (Permitted & Operational):**
   - If primary precipitation source `JAXA_GSMAP_NOW_01` is stale (>2h) or unreachable:
     $$\text{Precipitation Source} \longrightarrow \mathbf{NASA\_GPM\_NRT\_01}\ (\text{GPM Early Run})$$
   - This ensures resilient physical observation intake.
   - The production AI model (Calibrated XGBoost v1.1) continues running normally on the validly ingested observations.

2. **Model Failure (Strict Fail-Safe — No Substitution):**
   - If `Calibrated XGBoost v1.1` cannot execute:
     $$\text{Model Execution} \centernot\longrightarrow \text{Random Forest}$$
     $$\text{Model Execution} \centernot\longrightarrow \text{PyTorch CNN}$$
     $$\text{Model Execution} \centernot\longrightarrow \text{Any Alternate Model}$$
   - The system halts automated risk generation and declares `MODEL_UNAVAILABLE`.

---

## 7. Dashboard Changes

Both dashboard interfaces were sanitized in accordance with UX4G guidelines and the zero-emoji rule:

1. **`ner_safe_live_dashboard.html` (Card 4):**
   - Source Title: `PRODUCTION MODEL`
   - Pill: `AVAILABLE` (`#16A34A`) / `UNAVAILABLE` (`#DC2626`)
   - Granule: `PRODUCTION MODEL: Calibrated XGBoost v1.1`
   - Model Name: `Calibrated XGBoost v1.1`
   - Version: `v1.1`
   - Status: `AVAILABLE`
   - Canonical Hash: `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`
   - Operational Fallback: `NONE (Sole Operational Model)`
   - Weight: `40% Static Anchor`
   - Removed all text mentioning Random Forest fallback or model switching.

2. **`ner_safe_live_dashboard_extended.html` (Card 7 & C15 Panel):**
   - Removed `XGBOOST OFFICIAL • RF FALLBACK`. Replaced with `CALIBRATED XGBOOST V1.1 (SOLE PRODUCTION MODEL)`.
   - Labeled Random Forest explicitly as `RESEARCH/HISTORICAL ONLY (Weight: 0.00)`.
   - Updated C15 panel model description to `C15 Pre-Landslide Temporal Forecaster • v1.0.0 (Research Pipeline • Operational Weight: 0.00)`.

---

## 8. API Changes & Provenance

1. **`GET /api/models/comparison` (`live_sensor_server_extension.py`):**
   - `governance_decision`: `"CALIBRATED_XGBOOST_V1_1_SOLE_PRODUCTION_MODEL"`
   - `production_model.model_name`: `"Calibrated XGBoost v1.1"`
   - `production_model.canonical_sha256`: `"45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c"`
   - `operational_fallback_policy.fallback_model`: `"NONE"`
   - `operational_fallback_policy.failure_behavior`: `"MODEL_STATUS = MODEL_UNAVAILABLE; RISK_STATUS = CURRENT RISK UNAVAILABLE"`
   - Random Forest, CNN, InSAR, and C15 listed exclusively under `research_benchmarks_and_evidence` with `operational_role: "NONE"` and `operational_weight: 0.00`.

2. **`GET /api/monitoring/multimodal` (`server.py`):**
   - `active_production_model`: `"CALIBRATED_XGBOOST_V1_1_0_BASELINE"`
   - `production_model_name`: `"Calibrated XGBoost v1.1"`
   - `operational_fallback`: `"NONE"`
   - `random_forest` listed under `live_research_components` with `status: "RESEARCH_HISTORICAL_ONLY"`, `operational_weight: 0.00`.

3. **`GET /api/monitoring/status` (`fusion_engine.py`):**
   - `sources.terrain_susceptibility.production_model`: `"Calibrated XGBoost v1.1"`
   - `sources.terrain_susceptibility.model_status`: `"AVAILABLE"`
   - `sources.terrain_susceptibility.operational_fallback`: `"NONE"`

4. **`GET /api/assessment/current` (`live_assessment_service.py`):**
   - When XGBoost is unavailable, returns `assessment_status: "MODEL_UNAVAILABLE"`, `current_risk_available: false`, `risk_status: "CURRENT RISK UNAVAILABLE"`.
   - Exposes `last_valid_assessment` as a clearly designated historical audit object.

---

## 9. Alert Behavior on Model Failure

1. In `live_assessment_service.py`, if `model_status == "UNAVAILABLE"`, `risk_summary.tier_distribution` is set to `{}` and `max_risk_score` is `None`.
2. Hotspot features contain `fused_tier = "MODEL_UNAVAILABLE"` and `fused_risk_score = None`.
3. No alerts are dispatched or queued by `alert_safeguard_engine.py`.
4. Previous alerts in the database remain intact with their historical creation timestamps.
5. Zero alerts are fabricated.

---

## 10. Test Verification Results

### Dedicated Single Production Model Test Suite (`test_single_production_model.py`)
Ran all 13 required test cases:

| Test ID | Test Description | Result |
|---|---|---|
| `test_01` | XGBoost loads successfully and reports valid metadata | **PASS** |
| `test_02` | Canonical SHA-256 hash matches 45544c7f... exactly | **PASS** |
| `test_03` | XGBoost generates valid susceptibility output for all 48 hotspots | **PASS** |
| `test_04` | Four-factor weights (0.40/0.30/0.20/0.10) & thresholds (0.65/0.48/0.32) locked | **PASS** |
| `test_05` | Simulated XGBoost failure produces MODEL_UNAVAILABLE & current_risk_available=False | **PASS** |
| `test_06` | Simulated XGBoost failure does NOT invoke Random Forest fallback | **PASS** |
| `test_07` | Simulated XGBoost failure does NOT invoke PyTorch CNN fallback | **PASS** |
| `test_08` | Simulated XGBoost failure does NOT invoke C15 forecasting fallback | **PASS** |
| `test_09` | GSMaP_NOW -> GPM Early NRT data-source failover functions independently | **PASS** |
| `test_10` | Model failure and data-source failover remain separate, orthogonal states | **PASS** |
| `test_11` | Dashboard displays XGBoost as sole model; zero RF fallback wording | **PASS** |
| `test_12` | Automated alerts are suppressed when model is unavailable | **PASS** |
| `test_13` | Research components (CNN, InSAR, C15, RF) all retain 0.00 operational weight | **PASS** |

**Summary: 13 / 13 TESTS PASSED (18.261s)**

### Regression Suites Executed
1. `test_xgboost_production_promotion.py`: **9 / 9 PASSED**
2. `test_model_selection_audit_suite.py`: **8 / 8 PASSED**
3. `test_phase4a_gsmap_failover.py`: **9 / 9 PASSED**
4. `test_phase4a_video_pipeline.py`: **8 / 8 PASSED**
5. `test_phase4a_3d_terrain.py`: **7 / 7 PASSED**
6. `test_judge_demo_smoke.py`: **38 / 38 PASSED**

**Total Verified Checks: 92 / 92 PASSED across all suites.**

---

## 11. Production Model Hash Verification

```
Artifact File: NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib
Expected Hash: 45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c
Actual Hash:   45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c
Status:        100% EXACT MATCH (VERIFIED PRE- AND POST-IMPLEMENTATION)
File Size:     552,283 bytes
Modification:  ZERO BYTES MODIFIED (Artifact Strictly Frozen)
```

---

## 12. Remaining Research Components Status

All non-production models are explicitly classified as independent research components with zero operational influence:

| Component | Model Artifact / Pipeline | Governance Status | Operational Weight | Operational Role |
|---|---|---|---|---|
| **Random Forest Baseline** | `calibrated_susceptibility_model.joblib` | `RESEARCH/HISTORICAL ONLY` | 0.00 | Historical academic benchmark only |
| **PyTorch Spatial CNN** | `cnn_susceptibility_model.pt` | `RESEARCH_SHADOW_ONLY` | 0.00 | Offline spatial pattern learning |
| **Sentinel-1 InSAR** | Multitemporal SBAS / PSI pipeline | `RESEARCH_ONLY` | 0.00 | Surface deformation measurement |
| **C15 Temporal Forecaster** | Pre-landslide 24h hazard model | `RESEARCH_ONLY` | 0.00 | Future temporal hazard research |

---

## 13. Absolute Confirmation

I hereby confirm:
1. **Calibrated XGBoost v1.1** is the **ONLY** operational machine learning model in NER-SAFE.
2. Random Forest fallback has been completely removed from production inference, live assessment, GIS heatmaps, APIs, and alerts.
3. No machine learning model fallback exists anywhere in the operational code paths.
4. If XGBoost is unavailable, the system strictly reports `MODEL_STATUS = MODEL_UNAVAILABLE` and `RISK_STATUS = CURRENT RISK UNAVAILABLE` without fabricating scores.
5. The four-factor risk formula ($0.40 \times \text{Susc} + 0.30 \times \text{Rain} + 0.20 \times \text{Soil} + 0.10 \times \text{SatChange}$) and operational thresholds ($\ge 0.65$ Critical, $\ge 0.48$ High, $\ge 0.32$ Moderate, $< 0.32$ Watch) remain 100% locked and unaltered.
6. External backup drive `G:\` was never accessed, queried, or modified.
7. Zero secrets, credentials, or API keys were exposed.
8. Zero emojis are present in the user interface or system status logs.
