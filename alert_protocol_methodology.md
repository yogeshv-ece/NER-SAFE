# NER-SAFE — ADVISORY METHODOLOGY & DECISION RULES (RESEARCH PROTOTYPE)
**Heuristic Multi-Tier Landslide Advisory Protocol**  
**Issuing Authority**: NER-SAFE Research & Development Platform (SIH 26001 / MDoNER)  
**Standard**: OASIS / ITU-T Common Alerting Protocol v1.2 Open Schema Alignment  

---

## 1. Prototype Architecture & Decision Logic
The NER-SAFE Advisory Engine maps quantitative physical parameters derived in Components 10 and 11 into heuristic advisory tiers for decision-support evaluation:

```
+-----------------------------------------------------------------------------------------+
|                  COMPONENT 10 RISK SCORE & TRIGGER METRICS                              |
|                     + COMPONENT 11 EXPOSURE CONSEQUENCES                                |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
               +-------------------------------------------+
               |  Is Impact Priority CRITICAL?             |
               |  OR (Risk >= 0.40 AND Exposed Assets > 0)?|
               +-------------------------------------------+
                              /             \
                           YES               NO
                           /                   \
             +-----------------------+   +------------------------------------+
             |   🔴 TIER 1 (HIGH)     |   | Is Impact Priority HIGH?           |
             | Urgency: Expected     |   | OR (Risk >= 0.35)?                 |
             | Severity: Severe      |   +------------------------------------+
             | Certainty: Possible   |                  /             \
             | Action: Field Assess  |               YES               NO
             | (Non-Statutory)       |               /                   \
             +-----------------------+ +-----------------------+   +----------------------+
                                       |  🟠 TIER 2 (ELEVATED) |   | Is Impact Priority   |
                                       | Urgency: Expected     |   |    MODERATE?         |
                                       | Severity: Severe      |   | OR (Risk >= 0.30)?   |
                                       | Certainty: Possible   |   +----------------------+
                                       | Action: Precautionary |           /          \
                                       |         Monitoring    |        YES            NO
                                       +-----------------------+        /                \
                                                      +--------------------+  +--------------------+
                                                      |  🟡 TIER 3 (WATCH) |  |  🟢 TIER 4 (BASE)  |
                                                      | Urgency: Future    |  | Urgency: Past      |
                                                      | Severity: Moderate |  | Severity: Minor    |
                                                      | Certainty: Possible|  | Certainty: Unlikely|
                                                      | Action: Moisture   |  | Action: Low Signal |
                                                      |         Check      |  | (Not Proven Safe)  |
                                                      +--------------------+  +--------------------+
```

---

## 2. Scientific & Statutory Safeguards
1. **Non-Predictive of Time-of-Failure**: Regional precipitation (~10 km) and soil moisture (~9 km) cannot capture transient pore-water pressure spikes or micro-shear failures. Advisories reflect spatial exposure flags, not imminent disaster declarations.
2. **Statutory Non-Interference**: Under the Disaster Management Act 2005, only the State Disaster Management Authority and District Magistrates possess the legal authority to issue public evacuation directives, road closures, and emergency resource orders.
3. **Unmonitored Areas**: Areas showing low model signal are explicitly labeled as "Low Signal", never as "Safe", acknowledging potential data gaps and unmodeled local slope modifications.
