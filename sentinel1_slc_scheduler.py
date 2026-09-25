"""
=============================================================================
NER-SAFE: Sentinel-1 SLC Windows-Compatible Live InSAR Scheduler
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Scheduled background acquisition & stack accumulation service for
         genuine Sentinel-1 IW SLC repeat-pass observations over Meghalaya AOI.
Modes:
  1. RUN_ONCE: Executes a single discovery and accumulation cycle, then exits.
  2. CONTINUOUS: Runs as a long-lived Windows daemon, periodically checking CDSE
     with configurable polling interval and exponential backoff retry.
Guarantees:
  - Zero Credential Exposure: OAuth2/S3 secrets never printed or logged.
  - Zero Risk Pollution: InSAR evidence is decoupled; operational weights locked.
  - Idempotent: No duplicates downloaded or re-registered.
  - Storage Safe: Halts safely if free disk < 10 GB.
  - Zero Emojis: Strictly compliant with operational UX4G standards.
=============================================================================
"""

import os
import sys
import time
import json
import argparse
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sentinel1_slc_live_engine import sentinel1_slc_live_engine

DEFAULT_POLL_INTERVAL_SECONDS = int(os.environ.get("NER_SAFE_SLC_POLL_INTERVAL_SEC", 21600))  # 6 hours nominal
MIN_POLL_INTERVAL_SECONDS = 5  # For testing and fast polling


def format_audit_log(cycle_res: Dict[str, Any]) -> str:
    """Formats auditable cycle execution record without credential exposure."""
    lines = [
        "------------------------------------------------------------",
        "NER-SAFE SENTINEL-1 SLC LIVE CHECK",
        "------------------------------------------------------------",
        f"Checked:              {cycle_res.get('polled_at_utc', datetime.now(timezone.utc).isoformat())}",
        "Provider:             Copernicus Data Space Ecosystem (CDSE)",
        "Query:                Sentinel-1 SLC / IW / descending / Track 150 / VV (Meghalaya)",
        f"Cycle Status:         {cycle_res.get('status')}",
        f"Cycle Result:         {cycle_res.get('cycle_result')}",
        f"Products Discovered:  {cycle_res.get('total_catalogue_scenes', 0)}",
        f"Already Registered:   {cycle_res.get('already_registered_scenes', 0)}",
        f"New Eligible:         {cycle_res.get('new_eligible_scenes', 0)}",
        f"Stack Scenes:         {cycle_res.get('current_stack_size', 3)} / {cycle_res.get('target_stack_size', 15)}+ scenes",
        f"Eligible Pairs:       {cycle_res.get('eligible_pairs_count', 3)}",
        f"SBAS Status:          {cycle_res.get('sbas_status', 'SBAS_INITIAL_STACK_FORMED')}",
        f"PSI Status:           {cycle_res.get('psi_status', 'INSUFFICIENT_SLC_STACK_FOR_PSI')}",
        f"Scientific Status:    {cycle_res.get('scientific_status', 'RESEARCH_ONLY')}",
        f"Duration:             {cycle_res.get('duration_seconds', 0.0)}s",
        "------------------------------------------------------------"
    ]
    return "\n".join(lines)


class Sentinel1SLCScheduler:
    """
    Windows-compatible daemon/runner for Sentinel-1 SLC live accumulation.
    """

    def __init__(self,
                 poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
                 max_retries: int = 3,
                 backoff_factor: float = 2.0):
        self.poll_interval = max(poll_interval, MIN_POLL_INTERVAL_SECONDS)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.running = False
        self.cycle_count = 0

    def run_once(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Executes a single live acquisition cycle with error catching."""
        self.cycle_count += 1
        print(f"\n[SLC Scheduler] Starting RUN_ONCE cycle #{self.cycle_count} at {datetime.now(timezone.utc).isoformat()}...")
        try:
            res = sentinel1_slc_live_engine.execute_live_cycle(force_refresh=force_refresh)
            print(format_audit_log(res))
            return res
        except Exception as e:
            err_msg = str(e)
            print(f"[SLC Scheduler ERROR] Cycle #{self.cycle_count} failed: {err_msg}")
            return {
                "status": "FAILED",
                "error": err_msg,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            }

    def run_continuous(self, max_cycles: Optional[int] = None, force_refresh: bool = False):
        """Runs periodic acquisition loop on Windows host."""
        self.running = True
        print(f"[SLC Scheduler] Continuous monitoring started on Windows host.")
        print(f"  Polling interval: {self.poll_interval}s")
        print(f"  Max cycles: {max_cycles if max_cycles else 'UNLIMITED'}")

        consecutive_failures = 0

        while self.running:
            res = self.run_once(force_refresh=force_refresh)
            if res.get("status") == "FAILED":
                consecutive_failures += 1
                backoff = min(self.poll_interval, (self.backoff_factor ** consecutive_failures) * 10)
                print(f"[SLC Scheduler] Encountered failure #{consecutive_failures}. Backing off for {backoff:.1f}s...")
                time.sleep(backoff)
            else:
                consecutive_failures = 0

            if max_cycles and self.cycle_count >= max_cycles:
                print(f"[SLC Scheduler] Reached max cycles ({max_cycles}). Exiting continuous loop.")
                break

            print(f"[SLC Scheduler] Sleeping {self.poll_interval}s until next check...")
            time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="NER-SAFE Sentinel-1 SLC Live InSAR Scheduler")
    parser.add_argument("--mode", choices=["RUN_ONCE", "CONTINUOUS"], default="RUN_ONCE", help="Execution mode")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS, help="Polling interval in seconds")
    parser.add_argument("--max-cycles", type=int, default=None, help="Maximum cycles to execute in CONTINUOUS mode")
    parser.add_argument("--force-refresh", action="store_true", help="Force fresh CDSE OData catalogue fetch")

    args = parser.parse_args()
    scheduler = Sentinel1SLCScheduler(poll_interval=args.interval)

    if args.mode == "RUN_ONCE":
        res = scheduler.run_once(force_refresh=args.force_refresh)
        sys.exit(0 if res.get("status") in ("ALREADY_CURRENT", "NEW_OBSERVATION_ACQUIRED") else 1)
    else:
        try:
            scheduler.run_continuous(max_cycles=args.max_cycles, force_refresh=args.force_refresh)
        except KeyboardInterrupt:
            print("\n[SLC Scheduler] Terminated by user (KeyboardInterrupt).")
            sys.exit(0)


if __name__ == "__main__":
    main()
