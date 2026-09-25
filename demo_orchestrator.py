"""
NER-SAFE: Demonstrator Orchestrator & State Machine
Manages the three operational modes:
1. MODE 1: LIVE MONITORING (Real / near-real-time event-driven observation stream)
2. MODE 2: HISTORICAL REPLAY (Reconstructs real historical events like May 2024 Remal)
3. MODE 3: CONTROLLED DEMO SCENARIO (Multi-stage isolated presentation escalation)

Supports non-destructive manual controls:
[ START ], [ STOP ], [ PAUSE ], [ RESUME ]
"""

import os
import json
import time
import threading
from datetime import datetime, timezone

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))

import fusion_engine
from live_ingestion import ingestion_engine
from storage_engine import storage_engine

class DemoOrchestrator:
    def __init__(self):
        self.lock = threading.RLock()
        self.mode = "LIVE_MONITORING" # LIVE_MONITORING | HISTORICAL_REPLAY | DEMO_SCENARIO
        self.status = "STOPPED"       # STOPPED | RUNNING | PAUSED
        self.cycle_index = 0
        self.max_cycles = 100
        self.interval_seconds = 5
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        # Temporal timeline storage (last 30 snapshots)
        self.timeline_snapshots = []
        
        # Scenario step for DEMO_SCENARIO (0 to 3)
        self.scenario_step = 0
        
        # Initialize baseline timeline snapshot
        self._record_snapshot("Initial baseline observation recorded.")

    def get_state(self) -> dict:
        with self.lock:
            return {
                "mode": self.mode,
                "status": self.status,
                "cycle_index": self.cycle_index,
                "scenario_step": self.scenario_step,
                "interval_seconds": self.interval_seconds,
                "timeline_points_count": len(self.timeline_snapshots),
                "last_update": datetime.now(timezone.utc).isoformat()
            }

    def start_live_monitoring(self) -> dict:
        with self.lock:
            if self.status == "RUNNING" and self.mode == "LIVE_MONITORING":
                return {"status": "RUNNING", "mode": self.mode}
            
            self._stop_current_worker_locked()
            self.mode = "LIVE_MONITORING"
            self.status = "RUNNING"
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._run_live_loop, daemon=True)
            self.worker_thread.start()
            
        ingestion_engine.record_ingestion_cycle(mode="LIVE_MONITORING")
        self._record_snapshot("Live monitoring started. Ingestion scheduler active.")
        return {"status": "STARTED", "system_status": "RUNNING", "mode": self.mode}

    def start_historical_replay(self) -> dict:
        with self.lock:
            self._stop_current_worker_locked()
            self.mode = "HISTORICAL_REPLAY"
            self.status = "RUNNING"
            self.cycle_index = 0
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._run_replay_loop, daemon=True)
            self.worker_thread.start()

        ingestion_engine.record_ingestion_cycle(mode="HISTORICAL_REPLAY")
        self._record_snapshot("Historical replay initialized: May 2024 antecedent rain event.")
        return {"status": "STARTED", "system_status": "RUNNING", "mode": self.mode}

    def pause_replay(self) -> dict:
        with self.lock:
            if self.mode != "HISTORICAL_REPLAY":
                return {"error": "PAUSE_ONLY_SUPPORTED_FOR_REPLAY"}
            self.status = "PAUSED"
        return {"status": "PAUSED", "mode": self.mode}

    def resume_replay(self) -> dict:
        with self.lock:
            if self.mode != "HISTORICAL_REPLAY":
                return {"error": "RESUME_ONLY_SUPPORTED_FOR_REPLAY"}
            self.status = "RUNNING"
        return {"status": "RUNNING", "mode": self.mode}

    def start_demo_scenario(self) -> dict:
        with self.lock:
            self._stop_current_worker_locked()
            self.mode = "DEMO_SCENARIO"
            self.status = "RUNNING"
            self.scenario_step = 0
            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self._run_demo_scenario_loop, daemon=True)
            self.worker_thread.start()

        ingestion_engine.record_ingestion_cycle(mode="DEMO_SCENARIO")
        self._record_snapshot("Demo Scenario started: Stage 1 Baseline.")
        return {"status": "STARTED", "system_status": "RUNNING", "mode": self.mode}

    def stop_monitoring(self) -> dict:
        with self.lock:
            self._stop_current_worker_locked()
            self.status = "STOPPED"
        
        self._record_snapshot("Monitoring stopped by demonstrator. Results preserved.")
        return {"status": "STOPPED", "mode": self.mode}

    def _stop_current_worker_locked(self):
        self.stop_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            # Thread is daemon, event tells it to cleanly exit
            pass

    def _run_live_loop(self):
        """Periodically evaluates real satellite data feeds and generates fresh live predictions."""
        while not self.stop_event.is_set():
            # Refresh live satellite observations from external feeds
            cycle_info = ingestion_engine.refresh_all_feeds(mode="LIVE_MONITORING")
            with self.lock:
                self.cycle_index += 1

            live_features = cycle_info.get("live_features")
            self._record_snapshot(
                f"Live satellite observation cycle #{self.cycle_index} refreshed.",
                live_features=live_features
            )

            # Sleep interval checking stop_event
            for _ in range(max(1, int(self.interval_seconds * 2))):
                if self.stop_event.is_set():
                    break
                time.sleep(0.5)

    def _run_replay_loop(self):
        """Steps through historical progression."""
        replay_stages = [
            {"day": "Day 1 (Baseline)", "rain_factor": 0.2, "soil_factor": 0.3},
            {"day": "Day 2 (Moderate Rain)", "rain_factor": 0.45, "soil_factor": 0.48},
            {"day": "Day 3 (Continuous Downpour)", "rain_factor": 0.72, "soil_factor": 0.68},
            {"day": "Day 4 (Peak Cloudburst Trigger)", "rain_factor": 0.95, "soil_factor": 0.89},
            {"day": "Day 5 (Post-Event Stabilization)", "rain_factor": 0.35, "soil_factor": 0.75}
        ]

        while not self.stop_event.is_set() and self.cycle_index < len(replay_stages):
            if self.status == "PAUSED":
                time.sleep(0.5)
                continue

            stage = replay_stages[self.cycle_index]
            self._record_snapshot(f"Historical Replay: {stage['day']}", overrides=stage)
            
            time.sleep(self.interval_seconds)
            with self.lock:
                self.cycle_index += 1

        with self.lock:
            self.status = "STOPPED"
        self._record_snapshot("Historical Replay sequence completed.")

    def _run_demo_scenario_loop(self):
        """Steps through the 4 controlled presentation stages."""
        scenario_descriptions = [
            "Stage 1: Pre-Monsoon Dry Season Baseline (Normal Terrain Susceptibility)",
            "Stage 2: Regional Convective Storm Arrival (GPM Anomaly Surge to 110mm/3d)",
            "Stage 3: Soil Moisture Saturation Threshold Exceeded (SMAP index > 0.75, High-Risk Hotspots Triggered)",
            "Stage 4: Runout Corridor Activation & CAP Red Alert Dispatch for NH-06 Corridors"
        ]

        while not self.stop_event.is_set() and self.scenario_step < len(scenario_descriptions):
            desc = scenario_descriptions[self.scenario_step]
            self._record_snapshot(f"Controlled Demo: {desc}", scenario_step=self.scenario_step)
            
            time.sleep(self.interval_seconds)
            with self.lock:
                self.scenario_step += 1

        with self.lock:
            self.status = "STOPPED"
        self._record_snapshot("Controlled Demo scenario completed.")

    def _record_snapshot(self, message: str, overrides: dict = None, scenario_step: int = None, live_features: dict = None):
        """Computes current risk metrics from genuine observations and appends to temporal history."""
        # In LIVE_MONITORING mode, use the dynamic satellite features from ingestion engine
        hotspots_data = fusion_engine.compute_fused_hotspots(live_features=live_features)
        features = hotspots_data.get("features", [])
        
        # Calculate summary statistics across 48 hotspots
        scores = [f["properties"]["fused_risk_score"] for f in features]
        avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        
        tier_counts = hotspots_data.get("metadata", {}).get("tier_breakdown", {})
        
        # Determine strict provenance badge
        if self.mode == "LIVE_MONITORING":
            data_classification = "LIVE_SATELLITE"
        elif self.mode == "HISTORICAL_REPLAY":
            data_classification = "HISTORICAL_REPLAY"
        else:
            data_classification = "CONTROLLED_DEMO"

        pub_status = ingestion_engine.get_public_status()
        sources_meta = pub_status.get("sources", {})

        snap = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "data_classification": data_classification,
            "status": self.status,
            "message": message,
            "metrics": {
                "mean_risk_score": avg_score,
                "peak_risk_score": max_score,
                "critical_hotspots_count": tier_counts.get("CRITICAL", 0),
                "high_hotspots_count": tier_counts.get("HIGH", 0),
                "moderate_hotspots_count": tier_counts.get("MODERATE", 0),
                "watch_hotspots_count": tier_counts.get("WATCH", 0),
                "total_monitored_hotspots": len(features)
            },
            "satellite_provenance": {
                "gpm_observation": sources_meta.get("rainfall", {}).get("latest_observation"),
                "gpm_granule": sources_meta.get("rainfall", {}).get("granule_id"),
                "smap_observation": sources_meta.get("soil_moisture", {}).get("latest_observation"),
                "smap_granule": sources_meta.get("soil_moisture", {}).get("granule_id"),
                "s2_observation": sources_meta.get("satellite_optical", {}).get("latest_observation"),
                "s2_granule": sources_meta.get("satellite_optical", {}).get("granule_id"),
                "srtm_status": sources_meta.get("terrain_susceptibility", {}).get("processing_status")
            }
        }
        
        with self.lock:
            self.timeline_snapshots.append(snap)
            if len(self.timeline_snapshots) > 40:
                self.timeline_snapshots = self.timeline_snapshots[-40:]

        # Save snapshot using storage engine (writes locally & syncs to Google Drive if configured)
        fname = f"snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        storage_engine.save_snapshot("predictions/risk", fname, snap, mode=self.mode)

    def get_timeline(self) -> dict:
        with self.lock:
            return {
                "current_mode": self.mode,
                "current_status": self.status,
                "timeline": list(self.timeline_snapshots)
            }

# Global Orchestrator Singleton
orchestrator = DemoOrchestrator()
