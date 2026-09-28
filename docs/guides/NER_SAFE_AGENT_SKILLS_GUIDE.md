# NER-SAFE Agent Engineering Skills Guide

**Project**: AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India (NER-SAFE)  
**Document**: Standard Operating Policy & Skill Usage Guide  
**Status**: Active & Authoritative  

---

## 1. Operating Policy & Governance Precedence

> [!IMPORTANT]
> **Skills are engineering guidance.**  
> Project-specific scientific, operational, and governance invariants for NER-SAFE **always take precedence** over general skill instructions.
>
> Invariants:
> 1. **Production Primary Model**: Calibrated XGBoost with SHA-256 `45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c`.
> 2. **Operational 4-Factor Risk Formula**:
>    $$\text{Risk} = 0.40 \times \text{Susceptibility} + 0.30 \times \text{Rainfall Anomaly} + 0.20 \times \text{Soil Moisture Anomaly} + 0.10 \times \text{Soil Moisture Anomaly} + 0.10 \times \text{Satellite Change}$$
> 3. **External Drive Protection**: The external drive `G:\` is strictly protected and never accessed.
> 4. **No Synthetic Data & No Emojis**: Real telemetry, validated baselines, and scientific telemetry only.

---

## 2. Standard Agent Workflow Lifecycle

### Phase 1: Before Any Major NER-SAFE Change
1. **Understand Architecture First**: Use Understand Anything (`/understand`, `/understand-explain`) or native codebase inspection to map architecture, components, and relationships before proposing edits.
2. **Inspect Dependencies & Data Flow**: Trace upstream sources (NASA GPM, NASA SMAP, Sentinel-1 GRD, Sentinel-1 SLC, Sentinel-2 MSI, IMD, GSI, SACHET, OSINT, OSIRIS) and downstream consumers (telemetry DB, live assessment service, WebSocket dispatch, dashboard).
3. **Isolate Exact Root Cause**: Never guess; pinpoint failure points via systematic debugging.
4. **Plan Minimal Atomic Interventions**: Use `concise-planning` to prepare a minimal, surgical change checklist.
5. **Preserve Validated Behavior**: Retain tested scientific semantics and UI state contracts (`LIVE_VERIFIED`, `VALIDATED_STATIC_BASELINE`, `CLOUD_FILTERED_OBSERVATION`, `VALIDATED_RETAINED_BASELINE`, `RESEARCH_ONLY`, `WAITING`).

### Phase 2: During Implementation
- **Invoke Relevant Skills Selectively**: Never load unrelated catalogs or flood context.
- Use `test-driven-development` to write regression and unit coverage for source/scheduler/API fixes.
- Use `backend-architect` for robust API routing, graceful error containment, and thread safety.
- Use `data-engineer` and `data-quality-frameworks` for multi-source ingestion, cadence checks, and schema validation.

### Phase 3: After Implementation & Verification Gate
1. **Run Focused Tests**: Execute unit tests targeting modified components.
2. **Run Regression Suites**: Execute all NER-SAFE integration suites:
   - `test_live_monitoring_master_control.py`
   - `verify_e2e_sih_master_control.py`
   - `test_judge_demo_smoke.py`
   - `test_live_system.py`
   - `test_autonomous_pipeline_activation.py`
   - `test_xgboost_production_promotion.py`
   - `test_insar_multitemporal.py`
3. **Perform Browser & UI Checks**: Use `browser-automation` and `webapp-testing` to verify real browser rendering, console logs, and state indicators.
4. **Conduct Code Quality Review**: Apply `code-review-and-quality` checking correctness, error paths, performance, and formatting.
5. **Verify Protected Invariants**: Confirm XGBoost SHA-256 hash, 4-factor risk weights, and non-access to `G:\`.
6. **Ensure Zero Secret Exposure**: Check that no tokens, credentials, or `.env` files are logged or displayed.
7. **Verify Authentic Upstream Behavior**: Ensure real-time or retained baseline telemetry is honestly represented.
8. **Declare Completion**: Only conclude work once all 7 preceding validation gates pass cleanly.

---

## 3. Curated Skill Inventory & Intended Use

### Understand Anything Suite (Official Egonex-AI)
| Skill / Command | Intended NER-SAFE Use Case |
| :--- | :--- |
| **`/understand`** | Generates/updates interactive knowledge graph of NER-SAFE architecture while strictly excluding `.env`, rasters, models, and cache. |
| **`/understand-explain`** | Deep-dive architectural explanation of individual engines (e.g. `sentinel1_sar_engine.py`, `fusion_engine.py`). |
| **`/understand-onboard`** | Structured onboarding guide documenting NER-SAFE data pipelines and live scheduler architecture. |
| **`/understand-chat`** | Interactive query interface over the indexed codebase knowledge graph. |
| **`/understand-dashboard`** | Visual architecture dashboard representing subsystem couplings and data flows. |

### Agentic Awesome Skills (Curated 10 Engineering Skills)
| Skill ID | Intended NER-SAFE Use Case |
| :--- | :--- |
| **`concise-planning`** | Produces concise, atomic checklists before implementing backend, ingestion, or UI fixes. |
| **`systematic-debugging`** | Traces forensic root causes of observation discrepancies, socket race conditions, or pipeline stalls. |
| **`test-driven-development`** | Builds failing tests first for scheduler state transitions, provenance tagging, and risk anomalies. |
| **`e2e-testing-patterns`** | Verifies full user journeys from master monitoring switch to alert banner dissemination. |
| **`browser-automation`** | Drives headless and interactive browser checks of `ner_safe_live_dashboard.html` without manual overhead. |
| **`webapp-testing`** | Automates localhost API testing and end-to-end telemetry dispatch validation. |
| **`code-review-and-quality`** | Reviews changes against multi-axis criteria (scientific validity, security, error handling, performance). |
| **`backend-architect`** | Guides scalable API endpoints, threading policies, database pooling, and graceful daemon shutdowns. |
| **`data-engineer`** | Hardens multi-source satellite ingestion pipelines (NASA GPM, NASA SMAP, ESA Sentinel-1/2, IMD). |
| **`data-quality-frameworks`** | Enforces data freshness rules, deduplication, cloud occlusion detection, and observation schemas. |

---

## 4. Understand Anything Safety Boundaries for NER-SAFE

When running `/understand` or codebase indexing on NER-SAFE, the following paths and patterns must **always be excluded**:

```
# Security & Credentials
.env
*.env
credentials*
secrets*
*token*
*key*

# Raw & Large Raster Data
NER_SAFE_DATA/RAW_*
NER_SAFE_DATA/RASTER_*
*.tif
*.tiff
*.geotiff
*.h5
*.nc
*.zip
*.tar.gz

# Machine Learning Binaries
NER_SAFE_DATA/COMPONENT_10/models/calibrated_xgboost_model.joblib
*.joblib
*.pkl
*.pth
*.onnx

# Cache & Temporary Directories
__pycache__/
*.pyc
.cache/
temp_downloads/
cache/
logs/
*.log

# External Drives
G:/**
```

---

## 5. Summary

With this curated skill set installed, NER-SAFE developers and autonomous agents follow a structured, test-backed, and security-conscious engineering process while safeguarding all project-specific scientific models and operational invariants.
