# NER-SAFE: POST-FREEZE CHANGE CONTROL PROTOCOL

**Document Purpose**: Mandatory Governance and Change Control for NER-SAFE Following Release Freeze  
**Current Release Baseline**: `nersafe-judge-demo-baseline-1.0` (v1.0.0-judge-demo-freeze)  
**Effective Date**: September 13, 2026  
**Scope**: All future development, maintenance, and bug fixes  

---

## 1. CHANGE CONTROL PRINCIPLES

Following the release freeze of the Judge Demonstration Baseline, no developer or automated agent may modify the NER-SAFE codebase without adhering to this 10-point change control protocol.

> [!IMPORTANT]
> The primary objective of this protocol is to prevent silent regressions, preserve scientific integrity, protect reproducible judge demonstration flows, and maintain an immutable historical record.

---

## 2. THE 10 MANDATORY RULES FOR POST-FREEZE MODIFICATIONS

### Rule 1: Record Reason for Change
Before modifying any file in the workspace, explicitly document:
* Why the change is necessary.
* Which user requirement, bug report, or stakeholder feedback requested it.
* Anticipated technical and operational impact.

### Rule 2: Never Silently Alter Protected Scientific Outputs
The validated outputs of Component 10 (susceptibility rasters, uncertainty maps) and Component 11 (flow paths, empirical runout corridors, infrastructure intersections) are frozen deliverables.
* **Prohibited**: Overwriting, re-running with different random seeds, reslicing, resampling, or "cleaning" existing GeoTIFF or GeoJSON outputs without prior approval and version bumping.

### Rule 3: Re-Run Relevant Unit and Component Tests
Any modification to a subsystem (e.g., ingestion, auth, routing) must immediately execute its dedicated regression test suite before staging changes.

### Rule 4: Re-Run the 53-Check Judge Reproducibility Suite
Any changes—regardless of how minor—must be followed by a successful execution of:
```powershell
& "C:\Users\hp\AppData\Local\Python\bin\python.exe" test_judge_demo_reproducibility.py
```
All **53/53 checks** must pass. Zero regressions are permitted in the demonstration workflow.

### Rule 5: Compare Protected SHA-256 Hashes
Compute the SHA-256 hash of every modified file against the authoritative hashes recorded in:
* `NER_SAFE_RELEASE_MANIFEST.json`
* `NER_SAFE_RELEASE_MANIFEST.md`
Verify that only intentionally modified files exhibit hash changes.

### Rule 6: Update Manifest and Version Identifier on Intentional Changes
If a protected artifact is intentionally modified:
1. Increment the version identifier (e.g., from `1.0.0-judge-demo-freeze` to `1.0.1` or `1.1.0`).
2. Re-compute SHA-256 hashes and file sizes for all changed files.
3. Update `NER_SAFE_RELEASE_MANIFEST.json` and `NER_SAFE_RELEASE_MANIFEST.md` with the new timestamp and checksums.
4. Record the specific diff in the release history.

### Rule 7: Document Scientific and Operational Impact
If modifying ML hyperparameters, feature sets, threshold cutoffs, or physical routing parameters:
* Quantify and document the impact on spatial ROC-AUC, Brier score, flow-path length, or runout corridor area.
* Never alter scientific thresholds purely to force a test to pass.

### Rule 8: Preserve the Historical 328/328 Record
The historical validation baseline established on September 12, 2026 (**328 / 328 PASS across 9 baseline suites**) is a permanent historical milestone.
* Do not edit historical documents to erase or modify this record.
* Retain historical validation logs intact.

### Rule 9: Distinguish Current Run Counts from Historical Validation
Always transparently separate:
* **Historical Validation Baseline**: 328 / 328 PASS
* **Current Reproduction Rerun**: e.g., 325 / 328 PASS (reflecting elapsed wall-clock observation age)
* **Judge Reproducibility Suite**: 53 / 53 PASS
Never present a combined or aggregate count (e.g., 381) as if it were a single historical test execution.

### Rule 10: Never Turn Demo Data into Operational Data
Under no circumstances may:
* Historical demonstration scenarios (such as `EVT-MEG-001`) be routed to the live operational endpoint (`/api/assessment/current`).
* Stale or offline observation states be masked by falling back to demonstration replays.
* Synthetic citizen reports be converted into authentic emergency dispatches.
* Citizen reports be fed into ML model retraining pipelines.

---

## 3. CHECKLIST BEFORE COMMITTING POST-FREEZE CHANGES

Before declaring any post-freeze task complete, verify:

- [ ] Reason for change recorded in task notes
- [ ] No protected `.tif` or `.geojson` file was inadvertently modified
- [ ] `test_judge_demo_reproducibility.py` passed (53/53)
- [ ] `test_end_to_end_demo_workflow.py` passed (44/44)
- [ ] Active dashboard `ner_safe_live_dashboard.html` verified for EXACTLY ZERO EMOJIS
- [ ] Operational endpoint `/api/assessment/current` still reports `NOT_AVAILABLE` when fresh data are absent
- [ ] `NER_SAFE_RELEASE_MANIFEST.json` updated if protected files were intentionally updated
- [ ] No secrets, `.env` contents, or API credentials captured in committed documents
