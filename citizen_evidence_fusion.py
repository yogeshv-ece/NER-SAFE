"""
NER-SAFE: Citizen Evidence Confidence Fusion & Qualitative Scoring Layer
Fuses multi-dimensional observation signals into an EVIDENCE_CONFIDENCE score [0.0, 1.0].

Safeguards:
1. Citizen evidence is supporting qualitative corroboration for civil defense moderators.
2. It strictly does NOT modify C10/C15 risk scores directly.
3. It strictly does NOT trigger automated model retraining (model_retraining_triggered = False).
"""

import os
import sys
import math
from typing import Dict, Any, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from media_integrity_analyzer import media_integrity_analyzer, VERDICT_AUTHENTIC, VERDICT_MANIPULATED, VERDICT_SYNTHETIC

# Moderation Life-Cycle States
STATUS_SUBMITTED = "SUBMITTED"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_VERIFIED = "VERIFIED"
STATUS_REJECTED = "REJECTED"
STATUS_EXPIRED = "EXPIRED"

class CitizenEvidenceFusion:
    def compute_evidence_confidence(self, report_payload: Dict[str, Any],
                                    media_inspection: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculates a composite EVIDENCE_CONFIDENCE score [0.0, 1.0]."""
        base_score = 0.50
        contributors = []

        # 1. Moderation Status
        mod_status = report_payload.get("verification_status", STATUS_UNVERIFIED).upper()
        if mod_status == STATUS_VERIFIED or mod_status == "FIELD_VERIFIED":
            base_score += 0.35
            contributors.append("Field-officer ground verification confirmed (+0.35)")
        elif mod_status == STATUS_REJECTED:
            base_score = 0.05
            contributors.append("Report formally rejected by moderator (-0.45)")
        elif mod_status == STATUS_UNDER_REVIEW:
            base_score += 0.10
            contributors.append("Under active civil defense review (+0.10)")

        # 2. Media Integrity Verdict
        if media_inspection:
            m_verdict = media_inspection.get("verdict")
            if m_verdict == VERDICT_AUTHENTIC:
                base_score += 0.15
                contributors.append("Media integrity analysis indicates authentic photo (+0.15)")
            elif m_verdict == VERDICT_SYNTHETIC:
                base_score -= 0.35
                contributors.append("Media analysis detected AI-synthetic generation markers (-0.35)")
            elif m_verdict == VERDICT_MANIPULATED:
                base_score -= 0.25
                contributors.append("Media analysis indicates duplicate or manipulated photo (-0.25)")

        # 3. GPS & Accuracy
        accuracy = float(report_payload.get("accuracy_m", 25.0))
        if accuracy <= 10.0:
            base_score += 0.05
            contributors.append(f"High GPS precision: {accuracy:.1f} m (+0.05)")
        elif accuracy > 100.0:
            base_score -= 0.10
            contributors.append(f"Coarse GPS accuracy: {accuracy:.1f} m (-0.10)")

        # 4. Physical Plausibility of Ground Features
        crack_width = float(report_payload.get("crack_width_cm", 0.0))
        if 5.0 <= crack_width <= 200.0:
            base_score += 0.05
            contributors.append(f"Physical fissure dimension documented: {crack_width} cm (+0.05)")

        final_score = max(0.05, min(0.99, base_score))

        return {
            "evidence_confidence_score": round(final_score, 3),
            "confidence_tier": "HIGH" if final_score >= 0.75 else "MODERATE" if final_score >= 0.45 else "LOW",
            "moderation_status": mod_status,
            "scoring_contributors": contributors,
            "model_retraining_triggered": False,
            "disclaimer": "Supporting qualitative ground observation; isolated from ML models and operational four-factor fusion."
        }

# Global Singleton
citizen_evidence_fusion = CitizenEvidenceFusion()
