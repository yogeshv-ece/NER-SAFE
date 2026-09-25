# NER-SAFE: Prospective Validation Framework & Live Research Evidence Protocol

**Project:** AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India  
**Document Path:** `NER_SAFE_PROSPECTIVE_VALIDATION_FRAMEWORK.md`  
**System Status:** Operational Production (XGBoost V1.1.0) + Decoupled Live Research Pipelines  
**Governance Invariant:** XGBoost V1.1.0 Preserved (`45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`)  
**Operational Risk Formula:** `0.40 * Susceptibility + 0.30 * Rainfall_Anomaly + 0.20 * Soil_Moisture_Anomaly + 0.10 * Satellite_Change_Flag`  
**Operational Alert Tiers:** Critical $\ge 0.65$, High $\ge 0.48$, Moderate $\ge 0.32$, Watch $< 0.32$  
**Research Components:** Sentinel-1 InSAR (Weight 0.00), Spatial Context CNN (Weight 0.00), C15 Forecaster (Weight 0.00)  

---

## 1. Why Retrospective Evidence is Insufficient for InSAR and C15

In the development of landslide early warning systems, retrospective historical inventories (such as the 832-point 2020–2024 Northeast India dataset) frequently exhibit severe temporal and sensor coverage gaps:

1. **Sentinel-1 InSAR Coverage Asymmetry:**
   - Persistent Scatterer Interferometry (PSI) and Small Baseline Subset (SBAS) multi-temporal interferometry require dense, uninterrupted Single Look Complex (SLC) SAR acquisitions over an identical relative orbit and antenna viewing geometry.
   - Historical inventory events in Meghalaya and Mizoram occurred between 2020 and 2024. However, systematic, calibrated SLC acquisitions with eligible perpendicular baselines ($|B_\perp| \le 180\text{ m}$) and short temporal revisit intervals ($\Delta t \le 36\text{ days}$) were not archived co-temporally for the 832 ground-truth points.
   - Genuine CDSE acquisitions for Track 150 descending over the target plateau are available in the authentic local stack starting in August 2026.
   - **Scientific Principle:** It is mathematically impossible to evaluate retrospective historical InSAR accuracy without fabricating synthetic phase data or fabricating historical coherence maps. NER-SAFE strictly prohibits data fabrication.
2. **C15 Antecedent Precipitation Temporal Discretization:**
   - The C15 temporal forecaster evaluates dynamic rolling accumulation windows (1h, 3h, 6h, 12h, 24h, 72h).
   - Historical landslide inventory records catalog the event date (day), but routinely lack verified, sub-hourly failure initiation timestamps ($HH:MM$).
   - Evaluating a 1-hour or 3-hour storm trigger against an event timestamp with $\pm 12\text{-hour}$ uncertainty would introduce severe temporal misalignment or arbitrary assignment.
   - **Conclusion:** Retrospective validation for InSAR and sub-daily C15 forecasting is scientifically unavailable ($0/832$ coverage). Genuine prospective observation forward in time is the only valid scientific pathway.

---

## 2. Current Live Research State

The NER-SAFE architecture maintains an explicit separation between **Operational Production** and **Live Research Signals**:

```
OPERATIONAL DATA FLOW (Active Alerting):
Static SRTM DEM (30m) ──> XGBoost V1.1.0 ──────> Susceptibility (0.40) ┐
NASA GPM Early NRT   ──> Rainfall Ingestion   ──> Rain Anomaly   (0.30) ├─> Fused Risk
NASA SMAP NRT (107)  ──> Soil Moisture Engine ──> Soil Anomaly   (0.20) │   Score [0..1]
Sentinel-1/2 Optical ──> Surface Change Flag  ──> Sat Change     (0.10) ┘

DECOUPLED RESEARCH SIGNALS (Weight 0.00 — Non-Authoritative):
CDSE Sentinel-1 SLC  ──> InSAR SBAS Engine    ──> Coherence / Def (0.00) ──> Research Ledger
32x32 Raster Patches ──> PyTorch Spatial CNN  ──> Context Prob    (0.00) ──> Shadow Ledger
Multi-Window IMD/GPM ──> C15 Temporal Engine  ──> Rolling Forecast(0.00) ──> Forecast Ledger
```

- **Operational Status:**
  - Calibrated XGBoost V1.1.0: Primary Operational Susceptibility Provider (Weight: 0.40).
  - Four-Factor Fusion Formula: Authoritative Risk Engine (Weights: 0.40 / 0.30 / 0.20 / 0.10).
- **Research Status:**
  - Sentinel-1 InSAR: Live Automated Acquisition & Pair Processing (Weight: 0.00).
  - Spatial Context CNN: Live Shadow Inference across 48 Hotspots (Weight: 0.00).
  - C15 Temporal Forecaster: Live Rolling Multi-Window Antecedent Forecast (Weight: 0.00).

---

## 3. Prospective Prediction Ledger Design

Prospective validation requires that predictions be logged immutably **before** future outcomes are observed. Once recorded, predictions cannot be modified, re-calibrated, or deleted.

### Storage Architecture
- **Directory:** `NER_SAFE_DATA/RESEARCH_EVIDENCE/live_predictions/`
- **File Format:** Append-only JSON Lines (`prospective_predictions.jsonl`).
- **Data Model:**
  - `prediction_id`: Unique immutable identifier (`PRED-<hotspot>-<uuid>`).
  - `hotspot_id`: Target monitoring hotspot identifier (`EVT-MEG-001` through `EVT-MIZ-024`).
  - `latitude`, `longitude`: Spatial coordinates (WGS-84).
  - `predicted_at`: Exact ISO 8601 UTC timestamp of prediction generation.
  - `susceptibility`: Production XGBoost V1.1.0 susceptibility score $[0, 1]$.
  - `rainfall_anomaly`: Dynamic rainfall trigger $[0, 1]$.
  - `soil_moisture_anomaly`: Dynamic soil saturation index $[0, 1]$.
  - `satellite_change_flag`: Optical/radar surface disturbance $[0, 1]$.
  - `fused_risk_score`: Four-factor weighted risk output $[0, 1]$.
  - `fused_risk_tier`: Operational classification (`CRITICAL`, `HIGH`, `MODERATE`, `WATCH`).
  - `model_version`: Frozen baseline version (`calibrated_xgboost_v1_1_0`).
  - `model_sha256`: Cryptographic invariant check (`45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`).
  - `risk_formula`: Immutable mathematical string.
  - `outcome_id`: Pointer to subsequent outcome (initially `None`).
  - `outcome_state`: Initial state `PENDING_OBSERVATION`.

---

## 4. Outcome-Label Policy & Non-Binary Classification

Unlike laboratory benchmarks that assume omniscient binary labels, real-world geotechnical monitoring encounters ambiguous, unverified, or incomplete post-prediction reports. 

NER-SAFE formally establishes a four-tier non-binary outcome policy:

1. **`CONFIRMED_EVENT`**:
   - Criterion: Landslide, mudflow, rockfall, or slope collapse verified by GSI (Geological Survey of India) Bhusanket portal, State Disaster Management Authority (SDMA / SDRF) official bulletins, or multi-observer authenticated field inspection.
   - Ground Truth Label: $y = 1.0$.
2. **`NO_CONFIRMED_EVENT`**:
   - Criterion: Monitoring period elapsed (e.g. 72 hours post-trigger) with verified slope stability confirmed through clear-sky Sentinel-2 optical imagery, unchanged Sentinel-1 radar backscatter, and absence of incident reports.
   - Ground Truth Label: $y = 0.0$.
3. **`UNRESOLVED`**:
   - Criterion: Incident reported via social media or unverified citizen reports without official institutional corroboration, or heavy cloud cover preventing optical surface confirmation.
   - Handling: Retained in the research ledger. **Excluded from binary precision/recall scoring until corroboration is achieved.**
4. **`INSUFFICIENT_EVIDENCE`**:
   - Criterion: Hotspot sensor outage, data link interruption, or corrupted telemetry during the prospective verification window.
   - Handling: Flagged for sensor maintenance; strictly excluded from validation metrics.

---

## 5. Temporal Integrity Rules

To eliminate temporal data leakage in prospective validation, the following inequalities are enforced:

$$t_\text{observed} \le t_\text{ingested} \le t_\text{processed} \le t_\text{predicted} < t_\text{outcome}$$

- **`OBSERVED_AT`**: Time when satellite sensor or weather station acquired the measurement.
- **`INGESTED_AT`**: Time when raw telemetry was received by the NER-SAFE ingestion daemon.
- **`PROCESSED_AT`**: Time when terrain/weather feature calculation finished.
- **`PREDICTED_AT`**: Time when the model inference was computed and archived to the ledger.
- **`OUTCOME_AT`**: Time when the physical landslide event initiated or stability window concluded.

**Strict Constraint:** If $t_\text{predicted} \ge t_\text{outcome}$, the prediction is disqualified from prospective validation due to post-event leakage.

---

## 6. Spatial Matching Rules

A prospective prediction is paired with an outcome record if and only if both conditions are met:
1. **Spatial Proximity:**
   $$\text{Haversine}(\text{lat}_\text{pred}, \text{lon}_\text{pred}, \text{lat}_\text{out}, \text{lon}_\text{out}) \le R_\text{matching}$$
   Where $R_\text{matching} = 1,000\text{ meters}$ (the spatial footprint of the hotspot zone).
2. **Temporal Window:**
   $$0\text{ hours} < (t_\text{outcome} - t_\text{predicted}) \le 72\text{ hours}$$
   Predictions issued more than 72 hours prior to the event are outside the dynamic forecasting horizon.

---

## 7. Live CNN Evidence Methodology

- **Pipeline:** Continuous 48-hotspot shadow inference executed in parallel with operational cycles.
- **Input Channels (8):** Elevation, Slope, Aspect Sin, Aspect Cos, Profile Curvature, TWI, Sentinel-2 NDVI, Sentinel-2 NDWI ($32 \times 32$ patch, 960m context).
- **Ledger Path:** `NER_SAFE_DATA/RESEARCH_EVIDENCE/cnn_observations/cnn_shadow_observations.jsonl`.
- **Recorded Fields:** Hotspot ID, timestamps, CNN probability, XGBoost susceptibility, score difference ($\Delta = P_\text{CNN} - P_\text{XGB}$), input raster quality, inference latency (ms).
- **Operational Protection:** CNN score is stored strictly for comparison; operational risk formula remains unmodified.

---

## 8. Live InSAR Evidence Methodology

- **Pipeline:** Autonomous Copernicus Data Space Ecosystem (CDSE) discovery and ingestion of Sentinel-1 SLC IW descending Track 150 scenes.
- **Ledger Path:** `NER_SAFE_DATA/RESEARCH_EVIDENCE/insar_observations/insar_pair_observations.jsonl`.
- **Interferogram Selection Bounds:** Temporal baseline $\Delta t \le 36\text{ days}$, perpendicular baseline $|B_\perp| \le 180\text{ m}$.
- **Recorded Fields:** Pair ID, master/slave scene IDs, acquisition dates, spatial/temporal baselines, mean coherence, valid pixel percentage, velocity estimate (mm/yr) if available, uncertainty, persistent target count.
- **Scientific Guardrail:** A localized phase shift or displacement velocity estimate is **never** automatically classified as a confirmed landslide. It represents surface deformation that must be correlated with geomorphic context.

---

## 9. Real InSAR Historical Stack Audit (Track 150 Archive)

An audit of authentic CDSE Sentinel-1 SLC acquisitions over the target Meghalaya plateau yields:

| Acquisition Date | Relative Orbit | Orbit Pass | Swath | Polarization | Archive Status | Quality Check |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **2026-08-20T23:53:43Z** | Track 150 | Descending | IW1 | VV | Registered in Local Stack | Full swath coverage, valid calibration XML |
| **2026-09-01T23:53:43Z** | Track 150 | Descending | IW1 | VV | Registered in Local Stack | Full swath coverage, valid calibration XML |
| **2026-09-13T23:53:48Z** | Track 150 | Descending | IW1 | VV | Registered in Local Stack | Full swath coverage, valid calibration XML |

### Formed Interferometric Network:
- `PAIR_20260901_20260820`: $\Delta t = 12.0\text{ days}, B_\perp = 27.94\text{ m}$ (Eligible, Processed)
- `PAIR_20260913_20260820`: $\Delta t = 24.0\text{ days}, B_\perp = 145.0\text{ m}$ (Eligible, Processed)
- `PAIR_20260913_20260901`: $\Delta t = 12.0\text{ days}, B_\perp = 117.11\text{ m}$ (Eligible, Processed)

### Scientific Finding on Stack Depth:
- **SBAS (Small Baseline Subset):** Initial 3-scene stack is formed and tracking interferometric coherence across 3 pairs.
- **PSI (Persistent Scatterer Interferometry):** Requires a minimum of 15–20 SAR acquisitions to reliably separate atmospheric phase screen (APS) from non-linear ground displacement. The current 3-scene archive is scientifically insufficient for standalone PSI time-series inversion. Additional real scenes will be accumulated forward in time without synthesizing past data.

---

## 10. C15 Evidence Methodology

- **Pipeline:** Rolling antecedent rainfall forecasting across 6 standard windows: 1h, 3h, 6h, 12h, 24h, 72h.
- **Ledger Path:** `NER_SAFE_DATA/RESEARCH_EVIDENCE/c15_observations/c15_forecast_observations.jsonl`.
- **Recorded Fields:** Window hours, rainfall accumulation (mm), antecedent soil saturation, forecast value, input completeness (`COMPLETE`, `WAITING_FOR_DATA`), latency (s).
- **Scientific Guardrail:** When sub-hourly precipitation gauges are offline, C15 logs `WAITING_FOR_DATA` rather than imputing fabricated rainfall pulses.

---

## 11. Source Freshness Rules

To prevent stale or cached data from masquerading as current observations, source-specific age thresholds are enforced:

| Upstream Source | Maximum Freshness Window | Fresh Status | Baseline Retained | Stale Threshold |
| :--- | :---: | :---: | :---: | :---: |
| **NASA GPM Early NRT** | 24 hours | $\le 24\text{ h}$ | $24\text{ h} - 48\text{ h}$ | $> 48\text{ h}$ |
| **NASA SMAP NRT (107)** | 72 hours | $\le 72\text{ h}$ | $72\text{ h} - 144\text{ h}$ | $> 144\text{ h}$ |
| **Sentinel-2 Optical L2A** | 168 hours (7 days) | $\le 168\text{ h}$ | $168\text{ h} - 336\text{ h}$ | $> 336\text{ h}$ |
| **Sentinel-1 GRD SAR** | 288 hours (12 days) | $\le 288\text{ h}$ | $288\text{ h} - 576\text{ h}$ | $> 576\text{ h}$ |
| **Sentinel-1 SLC InSAR** | 864 hours (36 days) | $\le 864\text{ h}$ | $864\text{ h} - 1728\text{ h}$| $> 1728\text{ h}$ |
| **SRTM Static Terrain** | 87,600 hours (10 years)| $\le 87,600\text{ h}$ | Static Baseline | N/A |

---

## 12. Prospective Performance Metrics

When genuine confirmed outcomes accumulate ($N \ge N_\text{min}$), the prospective evaluation service computes:

1. **Confusion Matrix:** $TP, FP, TN, FN$ based on operational alert threshold ($Risk \ge 0.48$ for elevated alert).
2. **Precision (Positive Predictive Value):**
   $$\text{Precision} = \frac{TP}{TP + FP}$$
3. **Recall (Event Detection Rate):**
   $$\text{Recall} = \frac{TP}{TP + FN}$$
4. **False Alert Rate:**
   $$\text{FAR} = \frac{FP}{FP + TN}$$
5. **Missed Event Rate:**
   $$\text{MER} = \frac{FN}{TP + FN}$$
6. **Brier Score:**
   $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (P_i - Y_i)^2$$

---

## 13. Early-Warning & Operational Latency Metrics

Because warning lead time is critical to disaster mitigation, the ledger records:

1. **Data Ingestion Latency:**
   $$L_\text{ingestion} = t_\text{ingested} - t_\text{observed}$$
2. **Assessment Processing Latency:**
   $$L_\text{processing} = t_\text{predicted} - t_\text{ingested}$$
3. **End-to-End Early-Warning Lead Time:**
   $$T_\text{lead} = t_\text{outcome} - t_\text{first\_elevated\_alert}$$
   - Metrics Reported: Median lead time (hours), 90th percentile lead time, minimum and maximum lead times.

---

## 14. Minimum Sample-Size Rules & Promotion Prerequisites

### Sample Size Constraints
- **Rule 1 ($N < 10$):** If resolved prospective outcomes $N < 10$, the evaluation service returns `INSUFFICIENT_OUTCOME_DATA`. No percentage metrics are published.
- **Rule 2 ($10 \le N < 30$):** Preliminary observational reporting permitted with explicit sample count caveats. No promotion decisions permitted.
- **Rule 3 ($N \ge 30$):** Statistically valid prospective evaluation threshold.

### Promotion Prerequisites for Research Candidates
Before any research component (CNN, InSAR, or C15) or candidate model (Model C, Model F, Candidate V2) can be considered for operational risk formula promotion:
1. Candidate model must demonstrate statistically significant improvement in prospective PR-AUC ($p < 0.05$) over the frozen XGBoost V1.1.0 baseline across at least 30 resolved prospective events.
2. Candidate model must maintain Brier score $\le 0.1984$ (zero calibration degradation).
3. Candidate features must achieve $\ge 90\%$ verified live availability without missing-value fallback spikes.
4. Independent peer audit and scientific sign-off must be completed.

---

## 15. The Operational Hierarchy: LIVE vs. VALIDATED vs. PROMOTABLE

To prevent premature claims of superiority, the system enforces three distinct states:

| Category | Definition | Current NER-SAFE State |
| :--- | :--- | :--- |
| **LIVE** | Automated real-world ingestion, regular processing, and telemetry display active. | **Sentinel-1 InSAR, Spatial CNN, C15 Forecaster** |
| **VALIDATED** | Proven out-of-fold accuracy on identical evaluation datasets under leak-free protocols. | **XGBoost V1.1.0 (Production), Random Forest (Fallback)** |
| **PROMOTABLE** | Meets all promotion gates under prospective validation with statistically significant superiority. | **NONE** (XGBoost V1.1.0 remains the sole operational production model). |

---
*Framework Certified by: NER-SAFE Forensic Model Evaluation & Scientific Governance Board*
