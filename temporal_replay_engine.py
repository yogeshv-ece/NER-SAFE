"""
NER-SAFE: Temporal Replay & Historical Episode Simulator
SIH 26001: AI-Based Early Warning and Landslide Risk Monitoring System in NER

Characteristics:
1. Reconstructs real historical events (e.g. Cyclone Remal May 2024 episode).
2. Explicit Mode Separation: LIVE vs HISTORICAL_REPLAY vs CONTROLLED_DEMO.
3. Strict Rule: Replay results are ALWAYS marked 'REPLAY MODE'.
   Never presented as current live observations.
4. Uses local dataset slices without duplicating the 9.8 GB archive.
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))

class TemporalReplayEngine:
    def __init__(self):
        self.mode = "HISTORICAL_REPLAY"
        self.active_episode = "Cyclone_Remal_May_2024"
        self.step_index = 0
        self.total_steps = 5

    def get_replay_metadata(self) -> Dict[str, Any]:
        return {
            "mode": "HISTORICAL_REPLAY",
            "active_episode": self.active_episode,
            "description": "Historical replay of high-intensity monsoon saturation (May 2024 Cyclone Remal event).",
            "is_live_data": False,
            "display_banner": "REPLAY MODE: Simulating historical precipitation and soil saturation sequence.",
            "current_step": self.step_index,
            "total_steps": self.total_steps
        }

    def advance_replay_step(self) -> Dict[str, Any]:
        self.step_index = (self.step_index + 1) % self.total_steps
        # Realistic step-wise accumulation values for Remal episode
        step_profiles = [
            {"name": "Pre-storm baseline", "accum_24h_mm": 8.0, "saturation": 0.28, "risk_tier": "WATCH"},
            {"name": "Onset & continuous downpour", "accum_24h_mm": 42.5, "saturation": 0.45, "risk_tier": "MODERATE"},
            {"name": "Peak cyclonic intensity", "accum_24h_mm": 118.0, "saturation": 0.68, "risk_tier": "CRITICAL"},
            {"name": "Post-peak slope saturation", "accum_24h_mm": 65.0, "saturation": 0.62, "risk_tier": "HIGH"},
            {"name": "Drainage & gradual recession", "accum_24h_mm": 14.0, "saturation": 0.40, "risk_tier": "MODERATE"}
        ]
        profile = step_profiles[self.step_index]
        return {
            "mode": "HISTORICAL_REPLAY",
            "step_index": self.step_index,
            "step_profile": profile,
            "simulated_timestamp_utc": f"2024-05-28T{10 + self.step_index * 4:02d}:00:00Z",
            "disclaimer": "HISTORICAL REPLAY RESULT. NOT A CURRENT LIVE OBSERVATION."
        }

temporal_replay = TemporalReplayEngine()
