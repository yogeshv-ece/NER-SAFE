"""
NER-SAFE: Multi-Threaded Live REST API Server & Dashboard Host with Production Authentication
Built using Python standard library (http.server.ThreadingHTTPServer).
Zero external pip dependencies required.

Routes:
  GET   /                             -> Serves ner_safe_live_dashboard.html
  GET   /ner_safe_live_dashboard.html -> Serves ner_safe_live_dashboard.html
  GET   /api/monitoring/status        -> Independent multi-source observation status & timestamps
  GET   /api/monitoring/hotspots      -> 48 Fused risk hotspots GeoJSON with 4-factor weights
  GET   /api/monitoring/corridors     -> Component 11 DEM runout corridors GeoJSON
  GET   /api/monitoring/advisories    -> Component 12 CAP v1.2 advisories JSON
  GET   /api/reports                  -> Shared citizen & field observations GeoJSON (from SQLite)
  POST  /api/reports                  -> Ingest citizen observation (records submitted_by_user_id)
  PATCH /api/reports/<id>/verify      -> Update verification status (Requires FIELD_OFFICER or ADMIN)
  GET   /uploads/<filename>           -> Serves uploaded observation photos

Authentication & Role Management Routes:
  POST  /api/auth/register            -> Register new user account (default PUBLIC_USER)
  POST  /api/auth/login               -> Authenticate user, rate-limited, sets HttpOnly session cookie
  POST  /api/auth/logout              -> Invalidate server-side session, clear cookie
  GET   /api/auth/me                  -> Retrieve currently authenticated user profile
  POST  /api/auth/role-request        -> Request role elevation to FIELD_OFFICER or ANALYST

Administrator Management Routes (ADMIN only):
  GET   /api/admin/role-requests      -> View role elevation requests
  PATCH /api/admin/role-requests/<id>/approve -> Approve role elevation (self-approval prohibited)
  PATCH /api/admin/role-requests/<id>/reject  -> Reject role elevation
  GET   /api/admin/users              -> List all registered users
  GET   /api/admin/users/<id>         -> View user profile & history
  PATCH /api/admin/users/<id>/role    -> Change user role (last admin protected)
  PATCH /api/admin/users/<id>/status  -> Change account status: ACTIVE/SUSPENDED/DISABLED
  GET   /api/admin/audit-logs         -> View security & administrative audit logs
"""

import os
import sys
import json
import base64
import uuid
import urllib.parse
from http.cookies import SimpleCookie
from http.server import HTTPServer, ThreadingHTTPServer, SimpleHTTPRequestHandler
from datetime import datetime, timezone

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import fusion_engine
import database
import spatial_cross_ref
import auth_security
from live_ingestion import ingestion_engine
from storage_engine import storage_engine
from demo_orchestrator import orchestrator
from c15_forecasting_engine import c15_forecaster
from observation_provenance import provenance_registry
from alert_safeguard_engine import alert_safeguards
from network_state_manager import network_manager
from sentinel1_sar_engine import s1_engine
from weather_provider import precipitation_manager
from temporal_replay_engine import temporal_replay
import live_monitoring_controller
from video_integrity_analyzer import video_analyzer, KEYFRAMES_DIR
from media_integrity_analyzer import media_integrity_analyzer
from gis_service import gis_service

PORT = int(os.environ.get("PORT", 8000))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") in ("1", "true", "True")
DASHBOARD_PATH = os.path.join(PROJECT_ROOT, "ner_safe_live_dashboard.html")
C11_CORRIDORS_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "runout_corridors", "runout_corridors.geojson")
C11_FLOWPATHS_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "flow_paths", "flow_paths.geojson")
C11_EXPOSURE_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11", "exposure", "exposure_intersections.geojson")
C12_ALERTS_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_12", "alerts", "cap_alerts.json")
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "UPLOADS")
os.makedirs(UPLOADS_DIR, exist_ok=True)

class NERSafeRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for clients with credential support
        origin = self.headers.get("Origin") if self.headers else None
        allowed = os.environ.get("ALLOWED_ORIGINS", "*")
        if origin and allowed != "*":
            allowed_list = [o.strip() for o in allowed.split(",")]
            if origin in allowed_list:
                self.send_header("Access-Control-Allow-Origin", origin)
            else:
                self.send_header("Access-Control-Allow-Origin", allowed_list[0])
        else:
            self.send_header("Access-Control-Allow-Origin", origin if origin else "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Cookie, X-Forwarded-Proto")
        self.send_header("Access-Control-Allow-Credentials", "true")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # =========================================================================
    # AUTHENTICATION & SESSION HELPERS
    # =========================================================================

    def _get_client_ip(self) -> str:
        """Extracts client IP address for audit and rate-limiting."""
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def _get_session_id(self) -> str:
        """Parses session ID from Cookie header or Authorization: Bearer fallback."""
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            cookie = SimpleCookie()
            try:
                cookie.load(cookie_header)
                if "nersafe_session" in cookie:
                    return cookie["nersafe_session"].value
            except Exception:
                pass
        
        # Fallback to Authorization: Bearer <session_id>
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        
        return None

    def _get_authenticated_user(self):
        """
        Retrieves and validates currently authenticated user.
        Rejects if account is SUSPENDED or DISABLED.
        """
        session_id = self._get_session_id()
        if not session_id:
            return None
        
        session_data = database.get_active_session(session_id)
        if not session_data:
            return None
        
        # Check account status
        if session_data["status"] in ("SUSPENDED", "DISABLED"):
            return None
        
        # Touch session activity timestamp
        database.touch_session(session_id)
        return session_data

    def _send_json(self, data, status_code=200, cookies_to_set=None):
        """Helper to send JSON responses with optional Set-Cookie headers."""
        body = json.dumps(data, separators=(',', ':')).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookies_to_set:
            for c in cookies_to_set:
                self.send_header("Set-Cookie", c)
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, error_code: str, message: str, status_code: int = 400):
        """Standardized JSON error responder."""
        self._send_json({
            "success": False,
            "error": error_code,
            "message": message
        }, status_code=status_code)

    def _read_json_body(self, max_size: int = 60 * 1024 * 1024):
        """Safely parses incoming JSON request body with configurable max payload size."""
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len == 0:
            return {}
        if content_len > max_size:
            raise ValueError("Payload too large")
        raw = self.rfile.read(content_len)
        return json.loads(raw.decode("utf-8"))

    # =========================================================================
    # GET HANDLER
    # =========================================================================

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Whitelisted Prototype Web Applications & Static HTML
        STATIC_PAGES = {
            "/": "ner_safe_live_dashboard.html",
            "/index.html": "ner_safe_live_dashboard.html",
            "/ner_safe_live_dashboard.html": "ner_safe_live_dashboard.html",
            "/ner_safe_citizen_app.html": "ner_safe_citizen_app.html",
            "/ner_safe_early_warning_dashboard.html": "ner_safe_early_warning_dashboard.html",
            "/ner_safe_component11_map.html": "ner_safe_component11_map.html"
        }
        if path in STATIC_PAGES:
            target_path = os.path.join(PROJECT_ROOT, STATIC_PAGES[path])
            if os.path.exists(target_path):
                with open(target_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, f"{STATIC_PAGES[path]} not found")
                return

        # 1a. Favicon Handler
        if path == "/favicon.ico":
            svg_icon = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#1351A3"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>"""
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(svg_icon)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(svg_icon)
            return

        # 1b. Master Live Monitoring Status (Phase 5)
        if path == "/api/live-monitoring/status":
            self._send_json(live_monitoring_controller.get_status())
            return

        # 2. Public API: Monitoring Status
        if path == "/api/monitoring/status":
            data = fusion_engine.get_multi_source_status()
            self._send_json(data)
            return

        # 2a. C15 Temporal Forecast Status
        if path == "/api/forecast/status":
            from temporal_label_validator import temporal_label_validator
            from c15_model_comparator import c15_comparator
            comp_res = c15_comparator.run_rigorous_comparison()
            data = {
                "system_name": "NER-SAFE Pre-Landslide Temporal Forecasting Engine (C15)",
                "validation_status": comp_res.get("status", "NOT_SCIENTIFICALLY_VALIDATED"),
                "candidate_horizons": ["1h", "3h", "6h", "12h", "24h", "48h"],
                "supported_horizons": ["24h"],
                "model_name": c15_forecaster.model_name,
                "model_version": c15_forecaster.model_version,
                "scientific_objective": "Estimate probability that a landslide may occur within a defined future time window and identify the most likely initiation zone together with spatial and temporal uncertainty.",
                "scientific_disclaimer": "Supervised temporal ML validation remains NOT_SCIENTIFICALLY_VALIDATED due to lack of co-temporal historical event timestamps.",
                "label_audit": temporal_label_validator.audit_result
            }
            self._send_json(data)
            return

        # 2b. C15 Temporal Forecast Hotspots
        if path == "/api/forecast/hotspots":
            query_params = urllib.parse.parse_qs(parsed.query)
            req_horizon = query_params.get("horizon", ["24h"])[0]
            hotspots_geojson = fusion_engine.compute_fused_hotspots()
            features = []
            for feat in hotspots_geojson.get("features", []):
                p = feat["properties"]
                geom = feat["geometry"]
                coords = geom["coordinates"]
                static_ctx = {
                    "location_name": p.get("location_name", "Hotspot"),
                    "district": p.get("district", "Unknown"),
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "susceptibility_probability": p.get("susceptibility_score", 0.5),
                    "elevation_m": p.get("elevation_drop_m", 1200),
                    "slope_deg": p.get("reach_angle_deg", 32)
                }
                fc = c15_forecaster.evaluate_forecast(
                    hotspot_id=p.get("event_id", "EVT-000"),
                    horizon=req_horizon,
                    static_context=static_ctx,
                    rainfall_data=[{"timestamp_utc": p.get("rainfall_obs_time", datetime.now().isoformat()), "precipitation_mm": p.get("rainfall_anomaly_score", 0.5) * 40.0}],
                    smap_data={"status": "FRESH", "saturation_index": p.get("soil_moisture_score", 0.4), "observation_age_hours": 18.0},
                    sentinel1_data=s1_engine.get_latest_sar_observation(),
                    sentinel2_data={"status": "FRESH", "surface_change_score": p.get("sentinel2_surface_change_flag", 0.0), "observation_age_hours": 24.0}
                )
                fc_props = dict(p)
                fc_props.update(fc)
                features.append({
                    "type": "Feature",
                    "geometry": geom,
                    "properties": fc_props
                })
            self._send_json({
                "type": "FeatureCollection",
                "name": "NER_SAFE_C15_Temporal_Forecasts",
                "horizon": req_horizon,
                "features": features
            })
            return

        # 2c. Connectivity Status
        if path == "/api/connectivity/status":
            self._send_json(network_manager.get_connectivity_status())
            return

        # 2d. Sentinel-1 SAR Status
        if path == "/api/sar/status":
            self._send_json(s1_engine.get_latest_sar_observation())
            return

        # 2d-1. Sentinel-1 Multi-Temporal InSAR Pipeline Status (Decoupled Research)
        if path == "/api/insar/status":
            try:
                from sentinel1_slc_live_engine import sentinel1_slc_live_engine
                scenes = database.get_insar_scenes()
                pairs = database.get_insar_pairs()
                latest_def = database.get_insar_latest_deformation()
                stack_summary = sentinel1_slc_live_engine.get_stack_summary()

                n_scenes = len(scenes)
                n_pairs = len(pairs)
                latest_acq = scenes[-1]["sensing_start_utc"] if scenes else None
                latest_pair_time = pairs[0]["primary_time_utc"] if pairs else None

                valid_cohs = [p["coherence_mean"] for p in pairs if p.get("coherence_mean") is not None]
                avg_coh = round(float(sum(valid_cohs) / len(valid_cohs)), 4) if valid_cohs else None

                status_payload = {
                    "system": "NER-SAFE Sentinel-1 Multi-Temporal InSAR Pipeline",
                    "instrument": "Sentinel-1 C-SAR (C-band 5.546 cm)",
                    "track": 150,
                    "orbit_direction": "DESCENDING",
                    "swath": "IW1",
                    "polarization": "VV",
                    "stack_size_scenes": n_scenes,
                    "target_stack_size": stack_summary.get("target_stack_size", 15),
                    "stack_target_progress": stack_summary.get("stack_target_progress", f"{n_scenes} / 15+ scenes"),
                    "valid_pairs_count": n_pairs,
                    "eligible_pairs_count": n_pairs,
                    "latest_acquisition_utc": latest_acq,
                    "latest_discovery_utc": stack_summary.get("latest_discovery_utc"),
                    "last_successful_cdse_check_utc": stack_summary.get("last_successful_cdse_check_utc"),
                    "last_check_status": stack_summary.get("last_check_status", "ALREADY_CURRENT"),
                    "last_failure": stack_summary.get("last_failure"),
                    "acquisition_status": stack_summary.get("acquisition_status", "ACCUMULATION_ACTIVE"),
                    "latest_interferogram_utc": latest_pair_time,
                    "mean_coherence": avg_coh,
                    "storage": stack_summary.get("storage", {}),
                    "reference_point": {
                        "name": "SHILLONG_PLATEAU_NORTH_BEDROCK_REF",
                        "latitude": 25.7416,
                        "longitude": 90.8500,
                        "elevation_m": 1042.0,
                        "stability_status": latest_def.get("reference_stability_status", "STABLE_BEDROCK_ANCHOR") if latest_def else "STABLE_BEDROCK_ANCHOR"
                    },
                    "sbas_status": latest_def.get("multitemporal_status", "SBAS_INITIAL_STACK_FORMED") if latest_def else ("SBAS_INITIAL_STACK_FORMED" if n_scenes >= 3 else "INSUFFICIENT_STACK"),
                    "psi_status": "INSUFFICIENT_SLC_STACK_FOR_PSI",
                    "scientific_status": "RESEARCH_ONLY",
                    "risk_integration_status": "INSAR_RESEARCH_EVIDENCE_DECOUPLED",
                    "production_risk_impact": "NONE (Operational 4-factor risk formula protected)",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                }
                self._send_json(status_payload)
            except Exception as e:
                self._send_error_json("INSAR_STATUS_ERROR", str(e), 500)
            return

        if path == "/api/insar/scenes":
            scenes = database.get_insar_scenes()
            self._send_json({
                "total_scenes": len(scenes),
                "track": 150,
                "orbit_direction": "DESCENDING",
                "scenes": scenes
            })
            return

        if path == "/api/insar/pairs":
            pairs = database.get_insar_pairs()
            self._send_json({
                "total_pairs": len(pairs),
                "pairs": pairs
            })
            return

        # 2e. Multi-Source Weather & Precipitation Providers
        if path == "/api/weather/providers":
            self._send_json(precipitation_manager.get_all_provider_statuses())
            return

        # 2e. Replay Status
        if path == "/api/replay/status":
            self._send_json(temporal_replay.get_replay_metadata())
            return

        # 2f. Operational vs Demo Assessment Separation (SIH 26001 Phase 2/5)
        if path == "/api/assessment/current":
            from live_assessment_service import live_assessment_service
            cur = live_assessment_service.get_current_assessment()
            if cur:
                self._send_json(cur)
            else:
                from e2e_demo_engine import e2e_demo_engine
                self._send_json(e2e_demo_engine.run_operational_assessment())
            return

        if path == "/api/assessment/demo":
            from e2e_demo_engine import e2e_demo_engine
            query_params = urllib.parse.parse_qs(parsed.query)
            hotspot = query_params.get("hotspot_id", ["EVT-MEG-001"])[0]
            step = int(query_params.get("step", ["0"])[0])
            self._send_json(e2e_demo_engine.run_demo_assessment(hotspot_id=hotspot, step=step))
            return

        if path == "/api/assessment/pipeline":
            from e2e_demo_engine import e2e_demo_engine
            query_params = urllib.parse.parse_qs(parsed.query)
            hotspot = query_params.get("hotspot_id", ["EVT-MEG-001"])[0]
            self._send_json(e2e_demo_engine.run_demo_assessment(hotspot_id=hotspot))
            return

        # 2g. Canonical Live Multimodal Features & Model Lineage
        if path == "/api/monitoring/multimodal":
            try:
                eval_data = {}
                eval_path = os.path.join(PROJECT_ROOT, "multimodal_model_evaluation_results.json")
                if os.path.exists(eval_path):
                    with open(eval_path, "r", encoding="utf-8") as f:
                        eval_data = json.load(f)
                
                features = database.get_latest_multimodal_features()
                payload = {
                    "system": "NER-SAFE Live Multi-Source Model Governance & Lineage Registry",
                    "active_production_model": "CALIBRATED_XGBOOST_V1_1_0_BASELINE",
                    "production_model_name": "Calibrated XGBoost v1.1",
                    "production_model_sha256": "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c",
                    "operational_fallback": "NONE",
                    "candidate_v2_model": "CALIBRATED_XGBOOST_V2_MULTIMODAL",
                    "candidate_v2_sha256": "ec22c7b4acbcbbda167cd2f9c754bc87263411c5f37bdfb64fa57b8ec83e58e0",
                    "operational_risk_formula": "0.40*Susceptibility + 0.30*Rainfall_Anomaly + 0.20*Soil_Moisture_Anomaly + 0.10*Satellite_Change_Flag",
                    "live_research_components": {
                        "random_forest": {
                            "status": "RESEARCH_HISTORICAL_ONLY",
                            "operational_weight": 0.00,
                            "scientific_status": "HISTORICAL_BENCHMARK",
                            "operational_role": "NONE"
                        },
                        "insar_sbas": {
                            "status": "LIVE_RESEARCH_AUTOMATED",
                            "operational_weight": 0.00,
                            "scientific_status": "RESEARCH_ONLY",
                            "stack_size": 3,
                            "eligible_pairs": 3
                        },
                        "spatial_cnn": {
                            "status": "LIVE_SHADOW_INFERENCE",
                            "operational_weight": 0.00,
                            "scientific_status": "SHADOW_INFERENCE",
                            "input_channels": 8,
                            "patch_size": "32x32 (960m context)"
                        },
                        "c15_temporal_forecaster": {
                            "status": "LIVE_RESEARCH_FORECAST",
                            "operational_weight": 0.00,
                            "scientific_status": "RESEARCH_DECISION_SUPPORT",
                            "forecast_horizon": "24h"
                        }
                    },
                    "canonical_feature_count": len(features),
                    "features_sample": features[:5] if features else [],
                    "evaluation_summary": eval_data.get("promotion_decision", {}),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                }
                self._send_json(payload)
            except Exception as e:
                self._send_error_json("MULTIMODAL_FETCH_ERROR", str(e), 500)
            return

        # 2h. Prospective Validation & Research Evidence Registry
        if path == "/api/monitoring/prospective-evidence":
            try:
                from prospective_validation_engine import prospective_engine
                evidence_summary = prospective_engine.get_evidence_summary()
                eval_metrics = prospective_engine.evaluate_prospective_performance()
                insar_audit = prospective_engine.audit_cdse_insar_stack()
                payload = {
                    "system": "NER-SAFE Prospective Validation & Research Evidence Pipeline",
                    "evidence_counts": evidence_summary,
                    "evaluation_metrics": eval_metrics,
                    "insar_genuine_stack": insar_audit,
                    "total_cycles": evidence_summary["total_cycles"],
                    "total_production_predictions": evidence_summary["total_production_predictions"],
                    "total_cnn_observations": evidence_summary["total_cnn_observations"],
                    "total_c15_observations": evidence_summary["total_c15_observations"],
                    "total_insar_observations": evidence_summary["total_insar_observations"],
                    "total_outcomes": evidence_summary["total_outcomes"],
                    "waiting_for_data": evidence_summary["waiting_for_data"],
                    "confirmed_events": evidence_summary["confirmed_events"],
                    "confirmed_non_events": evidence_summary["confirmed_non_events"],
                    "unresolved": evidence_summary["unresolved"],
                    "insufficient_evidence": evidence_summary["insufficient_evidence"],
                    "resolved_predictions": evidence_summary.get("resolved_predictions", 0),
                    "last_cycle_timestamp": evidence_summary["last_cycle_timestamp"],
                    "last_prediction_timestamp": evidence_summary["last_prediction_timestamp"],
                    "last_cnn_timestamp": evidence_summary["last_cnn_timestamp"],
                    "last_c15_timestamp": evidence_summary["last_c15_timestamp"],
                    "last_insar_timestamp": evidence_summary["last_insar_timestamp"],
                    "last_outcome_timestamp": evidence_summary.get("last_outcome_timestamp", "NONE_RECORDED"),
                    "evaluation_status": eval_metrics.get("status", "INSUFFICIENT_OUTCOME_DATA"),
                    "production_model_protected": "CALIBRATED_XGBOOST_V1_1_0",
                    "production_sha256": "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c",
                    "operational_risk_formula": "0.40*Susceptibility + 0.30*Rainfall_Anomaly + 0.20*Soil_Moisture_Anomaly + 0.10*Satellite_Change_Flag",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                }
                self._send_json(payload)
            except Exception as e:
                self._send_error_json("PROSPECTIVE_EVIDENCE_ERROR", str(e), 500)
            return

        # 2i. Live Outcome Registry
        if path == "/api/monitoring/outcomes":
            try:
                from live_outcome_ingestor import live_outcome_ingestor
                outcomes = live_outcome_ingestor.load_outcomes()
                summary = live_outcome_ingestor.get_outcome_monitoring_summary()
                self._send_json({
                    "system": "NER-SAFE Live Canonical Outcome Registry",
                    "total_outcomes": len(outcomes),
                    "confirmed_events": summary["confirmed_events"],
                    "latest_outcome_observation": summary["latest_outcome_observation"],
                    "evaluation_status": summary["evaluation_status"],
                    "sources_status": summary["sources_reachable"],
                    "predictions_status": summary["predictions_audit"],
                    "outcomes": [o.to_dict() for o in outcomes[-50:]],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                self._send_error_json("OUTCOMES_FETCH_ERROR", str(e), 500)
            return

        # 2j. Prediction-Outcome Matches
        if path == "/api/monitoring/prospective-matches":
            try:
                from live_outcome_ingestor import live_outcome_ingestor
                matches = live_outcome_ingestor.load_matches()
                status_breakdown: Dict[str, int] = {}
                for m in matches:
                    status_breakdown[m.match_status] = status_breakdown.get(m.match_status, 0) + 1
                self._send_json({
                    "system": "NER-SAFE Prediction-to-Outcome Spatial-Temporal Match Registry",
                    "total_matches": len(matches),
                    "status_breakdown": status_breakdown,
                    "matching_parameters": {
                        "spatial_radius_km": live_outcome_ingestor.spatial_radius_km,
                        "temporal_window_hours": live_outcome_ingestor.temporal_window_hours
                    },
                    "matches": [m.to_dict() for m in matches],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                self._send_error_json("MATCHES_FETCH_ERROR", str(e), 500)
            return

        # 2k. Prospective Performance Evaluation
        if path == "/api/monitoring/prospective-performance":
            try:
                from prospective_validation_engine import prospective_engine
                from live_outcome_ingestor import live_outcome_ingestor
                query_params = urllib.parse.parse_qs(parsed.query)
                min_n = int(query_params.get("min_sample_size", ["30"])[0])
                eval_metrics = prospective_engine.evaluate_prospective_performance(min_sample_size=min_n)
                pred_audit = live_outcome_ingestor.audit_prospective_predictions()
                self._send_json({
                    "system": "NER-SAFE Prospective Validation Performance Evaluation",
                    "evaluation_metrics": eval_metrics,
                    "prediction_audit": pred_audit,
                    "evaluation_status": eval_metrics.get("status", "INSUFFICIENT_OUTCOME_DATA"),
                    "minimum_threshold_required": min_n,
                    "production_model_hash": "45544c7f5823879315c5caf244ebdaa85b964fe14a51dafe01c910f50a0acc6c",
                    "operational_risk_formula": "0.40*susceptibility + 0.30*rainfall_anomaly + 0.20*soil_moisture_anomaly + 0.10*satellite_change_flag",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                self._send_error_json("PERFORMANCE_EVAL_ERROR", str(e), 500)
            return

        # 3. Public API: Fused Risk Hotspots
        if path == "/api/monitoring/hotspots":
            query_params = urllib.parse.parse_qs(parsed.query)
            use_live = query_params.get("live", ["0"])[0] in ("1", "true", "True")
            live_feat = None
            if use_live or live_monitoring_controller.is_active() or (orchestrator.mode == "LIVE_MONITORING" and orchestrator.status == "RUNNING"):
                from live_assessment_service import live_assessment_service
                cur_asm = live_assessment_service.get_current_assessment()
                if cur_asm and cur_asm.get("inputs"):
                    inp = cur_asm["inputs"]
                    live_feat = {
                        "rainfall_anomaly": inp.get("rainfall", {}).get("derived_anomaly", 0.50),
                        "soil_moisture_anomaly": inp.get("soil_moisture", {}).get("derived_anomaly", 0.50),
                        "satellite_surface_change": 0.0,
                        "sar_surface_change": inp.get("sar_radar", {}).get("surface_change_score", 0.0)
                    }
                else:
                    obs = ingestion_engine.state.get("observations", {})
                    live_feat = {
                        "rainfall_anomaly": obs.get("rainfall", {}).get("feature_value", 0.62),
                        "soil_moisture_anomaly": obs.get("soil_moisture", {}).get("feature_value", 0.58),
                        "satellite_surface_change": obs.get("satellite_optical", {}).get("feature_value", 0.0),
                        "sar_surface_change": s1_engine.get_latest_sar_observation().get("surface_change_score", 0.0)
                    }
            data = fusion_engine.compute_fused_hotspots(live_features=live_feat)

            # Optional Filtering
            evt_filter = query_params.get("event_id", [None])[0]
            tier_filter = query_params.get("tier", [None])[0]
            qual_filter = query_params.get("qualifying", ["0"])[0] in ("1", "true", "True")

            if evt_filter or tier_filter or qual_filter:
                filtered_feats = []
                for f in data.get("features", []):
                    p = f.get("properties", {})
                    if evt_filter and p.get("event_id") != evt_filter and f.get("id") != evt_filter:
                        continue
                    if tier_filter and p.get("fused_tier") not in tier_filter.split(","):
                        continue
                    if qual_filter and not p.get("qualifies_for_runout"):
                        continue
                    filtered_feats.append(f)
                data["features"] = filtered_feats
                data["metadata"]["total_hotspots"] = len(filtered_feats)

            self._send_json(data)
            return

        # 4. Public API: Runout Corridors (Component 11 Empirical Lateral Spreading Envelopes)
        if path == "/api/monitoring/corridors":
            query_params = urllib.parse.parse_qs(parsed.query)
            evt_filter = query_params.get("event_id", [None])[0]
            qual_filter = query_params.get("qualifying", ["0"])[0] in ("1", "true", "True")

            if os.path.exists(C11_CORRIDORS_PATH):
                with open(C11_CORRIDORS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if evt_filter or qual_filter:
                    qual_ids = None
                    if qual_filter:
                        hotspots = fusion_engine.compute_fused_hotspots()
                        qual_ids = {h["id"] for h in hotspots["features"] if h["properties"].get("qualifies_for_runout")}

                    filtered = []
                    for feat in data.get("features", []):
                        fid = feat.get("properties", {}).get("event_id") or feat.get("id")
                        if evt_filter and fid != evt_filter:
                            continue
                        if qual_ids is not None and fid not in qual_ids:
                            continue
                        filtered.append(feat)
                    data["features"] = filtered

                self._send_json(data)
            else:
                self._send_json({"type": "FeatureCollection", "features": []})
            return

        # 4a. Public API: D8 Flow Paths (Component 11 Steepest-Descent Streamlines)
        if path in ("/api/monitoring/flowpaths", "/api/monitoring/flow-paths"):
            query_params = urllib.parse.parse_qs(parsed.query)
            evt_filter = query_params.get("event_id", [None])[0]
            qual_filter = query_params.get("qualifying", ["0"])[0] in ("1", "true", "True")

            if os.path.exists(C11_FLOWPATHS_PATH):
                with open(C11_FLOWPATHS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if evt_filter or qual_filter:
                    qual_ids = None
                    if qual_filter:
                        hotspots = fusion_engine.compute_fused_hotspots()
                        qual_ids = {h["id"] for h in hotspots["features"] if h["properties"].get("qualifies_for_runout")}

                    filtered = []
                    for feat in data.get("features", []):
                        fid = feat.get("properties", {}).get("event_id") or feat.get("id")
                        if evt_filter and fid != evt_filter:
                            continue
                        if qual_ids is not None and fid not in qual_ids:
                            continue
                        filtered.append(feat)
                    data["features"] = filtered

                self._send_json(data)
            else:
                self._send_json({"type": "FeatureCollection", "features": []})
            return

        # 4b. Public API: Infrastructure Exposure Intersections (Component 11 Lifeline Overlays)
        if path == "/api/monitoring/exposure":
            query_params = urllib.parse.parse_qs(parsed.query)
            evt_filter = query_params.get("event_id", [None])[0]

            if os.path.exists(C11_EXPOSURE_PATH):
                with open(C11_EXPOSURE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if evt_filter:
                    data["features"] = [
                        feat for feat in data.get("features", [])
                        if feat.get("properties", {}).get("event_id") == evt_filter
                    ]
                self._send_json(data)
            else:
                self._send_json({"type": "FeatureCollection", "features": []})
            return

        # 4c. Public API: Coupled Hotspot Runout & Flow-Path Package
        if (path.startswith("/api/monitoring/hotspots/") and path.endswith("/runout")) or path == "/api/monitoring/runout":
            query_params = urllib.parse.parse_qs(parsed.query)
            if path == "/api/monitoring/runout":
                target_event_id = query_params.get("event_id", [None])[0]
            else:
                parts = path.strip("/").split("/")
                target_event_id = parts[3] if len(parts) >= 4 else None

            if not target_event_id:
                self._send_error_json("MISSING_EVENT_ID", "event_id parameter or path variable required", 400)
                return

            use_live = query_params.get("live", ["0"])[0] in ("1", "true", "True")
            live_feat = None
            if use_live or (orchestrator.mode == "LIVE_MONITORING" and orchestrator.status == "RUNNING"):
                obs = ingestion_engine.state.get("observations", {})
                live_feat = {
                    "rainfall_anomaly": obs.get("rainfall", {}).get("feature_value", 0.62),
                    "soil_moisture_anomaly": obs.get("soil_moisture", {}).get("feature_value", 0.58),
                    "satellite_surface_change": obs.get("satellite_optical", {}).get("feature_value", 0.0)
                }

            package = fusion_engine.get_hotspot_runout_package(target_event_id, live_features=live_feat)
            if "error" in package:
                self._send_error_json(package["error"], package["message"], 404)
                return

            self._send_json(package)
            return

        # 4d. Public API: GIS Visualization Endpoints (SRTM Terrain, Population, Roads, Buildings)
        if path == "/api/gis/terrain/tile":
            query_params = urllib.parse.parse_qs(parsed.query)
            try:
                z = int(query_params.get("z", ["0"])[0])
                x = int(query_params.get("x", ["0"])[0])
                y = int(query_params.get("y", ["0"])[0])
                w = int(query_params.get("w", ["65"])[0])
                h = int(query_params.get("h", ["65"])[0])
                tile_data = gis_service.get_terrain_tile_float32(z, x, y, width=w, height=h)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(tile_data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(tile_data)
            except Exception as e:
                self._send_error_json("TERRAIN_TILE_ERROR", str(e), 500)
            return

        if path == "/api/gis/terrain/metadata":
            self._send_json(gis_service.get_dem_metadata())
            return

        if path == "/api/gis/population":
            self._send_json(gis_service.get_population_exposure())
            return

        if path == "/api/gis/roads":
            query_params = urllib.parse.parse_qs(parsed.query)
            tier = query_params.get("tier", ["major"])[0]
            road_bytes = gis_service.get_roads_exposure_bytes(tier=tier)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(road_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(road_bytes)
            return

        if path == "/api/gis/buildings":
            query_params = urllib.parse.parse_qs(parsed.query)
            try:
                limit = int(query_params.get("limit", ["1500"])[0])
            except ValueError:
                limit = 1500
            bldg_bytes = gis_service.get_buildings_exposure_bytes(limit=limit)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(bldg_bytes)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(bldg_bytes)
            return

        # 5. Public API: CAP Advisories
        if path == "/api/monitoring/advisories":
            if os.path.exists(C12_ALERTS_PATH):
                with open(C12_ALERTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json(data)
            else:
                self._send_json({"alerts": []})
            return

        # 6. Shared Citizen Reports
        if path == "/api/reports":
            data = database.get_all_reports()
            self._send_json(data)
            return

        # 6.1 Citizen Video Submissions & Moderation Queue (Phase 4A)
        if path == "/api/videos":
            query_params = urllib.parse.parse_qs(parsed.query)
            status_filter = query_params.get("status", [None])[0]
            limit = int(query_params.get("limit", ["50"])[0])
            videos = video_analyzer.list_videos(status=status_filter, limit=limit)
            self._send_json({
                "system": "NER-SAFE Citizen Video Ingestion & Moderation Queue",
                "total_count": len(videos),
                "filter": status_filter,
                "videos": videos,
                "operational_risk_weight": 0.00,
                "evidence_status": "CONTEXTUAL_EVIDENCE_ONLY"
            })
            return

        if path.startswith("/api/videos/") and not path.endswith("/moderate"):
            vid_id = path.split("/")[-1]
            videos = video_analyzer.list_videos(limit=200)
            target = next((v for v in videos if v["video_id"] == vid_id), None)
            if target:
                self._send_json({"video": target})
            else:
                self._send_error_json("NOT_FOUND", f"Video {vid_id} not found", 404)
            return

        # 6.2 Keyframe Thumbnails
        if path.startswith("/videos/thumbnails/"):
            thumb_name = os.path.basename(path)
            thumb_path = os.path.join(KEYFRAMES_DIR, thumb_name)
            if os.path.exists(thumb_path):
                with open(thumb_path, "rb") as f:
                    thumb_data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(thumb_data)))
                self.end_headers()
                self.wfile.write(thumb_data)
                return
            else:
                self.send_error(404, "Thumbnail not found")
                return

        # 6a. Demonstrator State & System Mode
        if path == "/api/system/state":
            self._send_json(orchestrator.get_state())
            return

        # 6b. Temporal Risk & Environmental Timeline
        if path == "/api/monitoring/timeline":
            self._send_json(orchestrator.get_timeline())
            return

        # 6c. Multi-Source Ingestion Tracking & Freshness Diagnostic
        if path == "/api/ingestion/status":
            self._send_json(ingestion_engine.get_public_status())
            return

        # 6d. Dual-Backend Storage Diagnostic (Local + Google Drive / Google One)
        if path == "/api/storage/status":
            self._send_json(storage_engine.get_status())
            return

        # 6e. Scientific Transparency & Pipeline Methodology
        if path == "/api/system/methodology":
            self._send_json({
                "system_title": "NER-SAFE: North-East Region Satellite-based Risk Assessment & Forest-soil Analysis Engine",
                "authority": "Ministry of Development of North Eastern Region (MDoNER) Prototype",
                "methodological_pipeline": [
                    {
                        "stage": "1. Multi-Source Environmental Data Ingestion",
                        "type": "OBSERVED (Satellites & Earth Observation Feeds)",
                        "description": "Ingests decoupled observation feeds from ESA Sentinel-2 optical imagery, NASA GPM IMERG precipitation, NASA SMAP radiometer soil moisture, and ground observations."
                    },
                    {
                        "stage": "2. Dynamic Feature Extraction & Spatial Indexing",
                        "type": "MODELLED (Morphometric & Hydrological Derivatives)",
                        "description": "Extracts 30m terrain slope, aspect, curvature, and topographic wetness index (TWI) alongside 3-day antecedent rainfall anomaly and surface soil moisture saturation index."
                    },
                    {
                        "stage": "3. AI Susceptibility & Multi-Factor Risk Fusion",
                        "type": "PREDICTED (Calibrated Random Forest + Weighted Fusion)",
                        "description": "Evaluates static geomorphic susceptibility via Platt Sigmoid Calibrated Random Forest (0.40), fused with dynamic rainfall anomaly (0.30), soil moisture saturation (0.20), and optical surface disturbance (0.10)."
                    },
                    {
                        "stage": "4. Empirical Runout Corridors & Downhill Flow Routing",
                        "type": "SIMULATED (D8 Steepest-Descent & Spreading Envelope)",
                        "description": "Calculates downhill gravitational movement corridors using SRTM 1-Arcsecond DEM and empirical Fahrboschung reach angle (10 deg). Defensible terminology: 'Predicted Potential Runout Corridor' (not guaranteed trajectory)."
                    },
                    {
                        "stage": "5. Multi-Criteria Exposure & Lifeline Intersections",
                        "type": "MODELLED (GIS Infrastructure Overlays)",
                        "description": "Spatially intersects active runout corridors with National Highways (NH-06), state roads, settlements, and community infrastructure to classify impact priority."
                    },
                    {
                        "stage": "6. Standardized Public Early Warning Feeds",
                        "type": "ADVISORY (ITU-T / OASIS CAP v1.2 Protocol)",
                        "description": "Dispatches structured Common Alerting Protocol v1.2 alerts categorized into Watch, Moderate, High, and Critical alert tiers with civil protection instructions."
                    }
                ],
                "scientific_limitations": "Modelled runout corridors represent empirical likelihood zones based on digital elevation gradients. The system cannot guarantee the exact future initiation second or micro-scale volume of a landslide."
            })
            return

        # 7. Authentication: Current User
        if path == "/api/auth/me":
            user = self._get_authenticated_user()
            if user:
                self._send_json({
                    "authenticated": True,
                    "user": {
                        "id": user["id"],
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "role": user["role"],
                        "requested_role": user["requested_role"],
                        "state": user["state"],
                        "organization": user["organization"],
                        "status": user["status"]
                    }
                })
            else:
                self._send_json({
                    "authenticated": False,
                    "user": None
                })
            return

        # 8. Admin API: View Role Requests (ADMIN only)
        if path == "/api/admin/role-requests":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrative privilege required.", 403)
            
            requests = database.get_role_requests()
            self._send_json({"role_requests": requests})
            return

        # 9. Admin API: View All Users (ADMIN only)
        if path == "/api/admin/users":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrative privilege required.", 403)
            
            users = database.get_all_users()
            self._send_json({"users": users})
            return

        # 10. Admin API: View Single User (ADMIN only)
        if path.startswith("/api/admin/users/"):
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrative privilege required.", 403)
            
            try:
                target_id = int(path.split("/")[-1])
                target_user = database.get_user_by_id(target_id)
                if not target_user:
                    return self._send_error_json("NOT_FOUND", "User not found.", 404)
                
                # Sanitize password hash
                del target_user["password_hash"]
                self._send_json({"user": target_user})
                return
            except ValueError:
                return self._send_error_json("VALIDATION_ERROR", "Invalid user ID.", 400)

        # 11. Admin API: View Audit Logs (ADMIN only)
        if path == "/api/admin/audit-logs":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrative privilege required.", 403)
            
            logs = database.get_audit_logs(limit=100)
            self._send_json({"audit_logs": logs})
            return

        # 12. Uploaded Photos
        if path.startswith("/uploads/"):
            filename = os.path.basename(path)
            file_path = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(file_path):
                ext = os.path.splitext(filename)[1].lower()
                mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/svg+xml"
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "Photo not found")
                return

        # Strict 404 handler for unmapped paths (prevents arbitrary file exposure / directory traversal)
        self.send_error(404, "Endpoint or resource not found")
        return

    # =========================================================================
    # POST HANDLER
    # =========================================================================

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self._get_client_ip()

        # 0a. Connectivity Level Override
        if path == "/api/connectivity/set-level":
            try:
                payload = self._read_json_body()
                lvl = payload.get("level", "ONLINE")
                res = network_manager.set_connectivity_level(lvl)
                return self._send_json(res)
            except Exception as e:
                return self._send_error_json("ERROR", str(e), 400)

        # 0b. Connectivity Sync Outbox
        if path == "/api/connectivity/sync":
            try:
                res = network_manager.synchronize_offline_outbox(lambda p: {"status": "SUCCESS", "id": database.add_report(p)})
                return self._send_json(res)
            except Exception as e:
                return self._send_error_json("ERROR", str(e), 400)

        # 0c. Replay Advance
        if path == "/api/replay/advance":
            step_res = temporal_replay.advance_replay_step()
            return self._send_json(step_res)

        # 1. Authentication: Registration
        if path == "/api/auth/register":
            try:
                payload = self._read_json_body()
            except Exception:
                return self._send_error_json("VALIDATION_ERROR", "Malformed JSON request body.", 400)

            full_name = payload.get("full_name", "").strip()
            email = auth_security.normalize_email(payload.get("email", ""))
            password = payload.get("password", "")
            state = payload.get("state", "Meghalaya").strip()
            org = payload.get("organization", "").strip()
            requested_role = payload.get("requested_role", "PUBLIC_USER").strip().upper()

            if not full_name or not email or not password:
                return self._send_error_json("VALIDATION_ERROR", "Full name, email, and password are required.", 422)

            if not auth_security.is_valid_email(email):
                return self._send_error_json("VALIDATION_ERROR", "Invalid email address format.", 422)

            valid_pwd, pwd_msg = auth_security.validate_password_strength(password)
            if not valid_pwd:
                return self._send_error_json("VALIDATION_ERROR", pwd_msg, 422)

            # Prevent direct self-registration as ADMIN
            if requested_role == "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrator accounts cannot be self-registered.", 403)

            # Check duplicate email
            if database.get_user_by_email(email):
                return self._send_error_json("CONFLICT", "An account with this email address already exists.", 409)

            pwd_hash = auth_security.hash_password(password)

            # Standard users default to PUBLIC_USER. If elevated role requested, create as PUBLIC_USER with PENDING request.
            initial_role = "PUBLIC_USER"
            user_id = database.create_user(
                full_name=full_name,
                email=email,
                password_hash=pwd_hash,
                role=initial_role,
                requested_role=requested_role if requested_role in ("FIELD_OFFICER", "ANALYST") else None,
                state=state,
                organization=org,
                status="ACTIVE"
            )

            # If elevated role was requested, create role request entry
            req_msg = "Registration successful. You can now sign in."
            if requested_role in ("FIELD_OFFICER", "ANALYST"):
                database.create_role_request(user_id, requested_role, f"Initial registration request for {requested_role}")
                req_msg = "Registration successful. Your account has been created as a Public User. Your requested role requires administrator approval."

            database.record_audit_log(
                "REGISTER",
                user_id=user_id,
                target_type="USER",
                target_id=str(user_id),
                metadata={"email": email, "requested_role": requested_role},
                ip_address=client_ip
            )

            return self._send_json({
                "status": "SUCCESS",
                "message": req_msg,
                "user": {
                    "id": user_id,
                    "full_name": full_name,
                    "email": email,
                    "role": initial_role,
                    "status": "ACTIVE"
                }
            }, status_code=201)

        # 2. Authentication: Login
        if path == "/api/auth/login":
            try:
                payload = self._read_json_body()
            except Exception:
                return self._send_error_json("VALIDATION_ERROR", "Malformed JSON request body.", 400)

            email = auth_security.normalize_email(payload.get("email", ""))
            password = payload.get("password", "")

            if not email or not password:
                return self._send_error_json("VALIDATION_ERROR", "Email and password are required.", 422)

            rate_limit_key = f"{client_ip}:{email}"
            if auth_security.login_rate_limiter.is_rate_limited(rate_limit_key):
                return self._send_error_json("RATE_LIMITED", "Too many failed login attempts. Please try again in a few minutes.", 429)

            user = database.get_user_by_email(email)
            if not user or not auth_security.verify_password(password, user["password_hash"]):
                auth_security.login_rate_limiter.record_attempt(rate_limit_key)
                database.record_audit_log(
                    "LOGIN_FAILURE",
                    user_id=user["id"] if user else None,
                    target_type="AUTH",
                    metadata={"attempted_email": email},
                    ip_address=client_ip
                )
                return self._send_error_json("UNAUTHORIZED", "Invalid email or password.", 401)

            # Check account status
            if user["status"] == "SUSPENDED":
                return self._send_error_json("FORBIDDEN", "This account has been suspended by an administrator.", 403)
            if user["status"] == "DISABLED":
                return self._send_error_json("FORBIDDEN", "This account has been disabled.", 403)

            # Login success
            auth_security.login_rate_limiter.reset(rate_limit_key)
            session_id = auth_security.generate_session_id()
            database.create_session(user["id"], session_id, duration_seconds=604800)  # 7 days
            database.update_user_last_login(user["id"])

            database.record_audit_log(
                "LOGIN_SUCCESS",
                user_id=user["id"],
                target_type="AUTH",
                metadata={"role": user["role"]},
                ip_address=client_ip
            )

            # Build HttpOnly cookie (supports X-Forwarded-Proto for reverse proxies / tunnels)
            is_https = COOKIE_SECURE or (self.headers.get("X-Forwarded-Proto", "").lower() == "https")
            secure_flag = "; Secure" if is_https else ""
            cookie_str = f"nersafe_session={session_id}; Path=/; HttpOnly; SameSite=Lax{secure_flag}; Max-Age=604800"

            return self._send_json({
                "authenticated": True,
                "message": "Login successful.",
                "user": {
                    "id": user["id"],
                    "full_name": user["full_name"],
                    "email": user["email"],
                    "role": user["role"],
                    "requested_role": user["requested_role"],
                    "state": user["state"],
                    "organization": user["organization"],
                    "status": user["status"]
                }
            }, status_code=200, cookies_to_set=[cookie_str])

        # 3. Authentication: Logout
        if path == "/api/auth/logout":
            session_id = self._get_session_id()
            user = self._get_authenticated_user()
            if session_id:
                database.revoke_session(session_id)
                database.record_audit_log(
                    "LOGOUT",
                    user_id=user["id"] if user else None,
                    target_type="AUTH",
                    ip_address=client_ip
                )

            # Clear cookie
            clear_cookie = "nersafe_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
            return self._send_json({
                "authenticated": False,
                "message": "Session invalidated successfully."
            }, status_code=200, cookies_to_set=[clear_cookie])

        # 4. Authentication: Request Role Elevation
        if path == "/api/auth/role-request":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)

            try:
                payload = self._read_json_body()
            except Exception:
                return self._send_error_json("VALIDATION_ERROR", "Malformed JSON request body.", 400)

            requested_role = payload.get("requested_role", "").strip().upper()
            reason = payload.get("reason", "").strip()

            if requested_role not in ("FIELD_OFFICER", "ANALYST"):
                return self._send_error_json("VALIDATION_ERROR", "Requested role must be FIELD_OFFICER or ANALYST.", 422)

            req_id = database.create_role_request(user["id"], requested_role, reason)
            database.record_audit_log(
                "ROLE_REQUEST",
                user_id=user["id"],
                target_type="ROLE_REQUEST",
                target_id=str(req_id),
                metadata={"requested_role": requested_role, "reason": reason},
                ip_address=client_ip
            )

            return self._send_json({
                "status": "SUCCESS",
                "message": f"Role elevation request for {requested_role} submitted for administrator review.",
                "request_id": req_id
            }, status_code=201)

        # 4b. Citizen AI Image Forensic & Evidence Analysis
        if path == "/api/reports/analyze-image":
            try:
                payload = self._read_json_body()
                img_b64 = payload.get("image_base64", "")
                filename = payload.get("filename", "ground_photo.jpg")
                claimed_mime = payload.get("mime_type", "image/jpeg")
                lat = float(payload.get("latitude")) if payload.get("latitude") is not None else None
                lon = float(payload.get("longitude")) if payload.get("longitude") is not None else None
                ts = payload.get("timestamp")
                cat = payload.get("category", "")
                notes = payload.get("notes", "")

                if not img_b64:
                    return self._send_error_json("MISSING_DATA", "image_base64 is required", 400)
                if "," in img_b64:
                    img_b64 = img_b64.split(",", 1)[1]

                try:
                    img_bytes = base64.b64decode(img_b64)
                except Exception as e:
                    return self._send_error_json("INVALID_BASE64", f"Could not decode base64: {e}", 400)

                result = media_integrity_analyzer.process_image_submission(
                    file_bytes=img_bytes,
                    original_filename=filename,
                    claimed_mime=claimed_mime,
                    reported_lat=lat,
                    reported_lon=lon,
                    reported_timestamp_iso=ts,
                    category_hint=cat,
                    notes_hint=notes,
                    target_dir=UPLOADS_DIR
                )

                status_code = 200 if result.get("success", False) else 422
                return self._send_json(result, status_code=status_code)
            except Exception as e:
                return self._send_error_json("IMAGE_ANALYSIS_ERROR", str(e), 500)

        # 5. Ground Observation Intake
        if path == "/api/reports":
            try:
                payload = self._read_json_body()
                lat = float(payload.get("latitude", 0.0))
                lon = float(payload.get("longitude", 0.0))

                # Dynamic Spatial Cross-Referencing
                spatial_info = spatial_cross_ref.analyze_location(lat, lon)

                # Photo handling with safe validation & forensics
                photo_filename = payload.get("photo_filename", "none")
                photo_sha256 = payload.get("photo_sha256")
                ai_analysis = payload.get("ai_analysis")
                photo_b64 = payload.get("photo_base64")
                if photo_b64 and len(photo_b64) > 20:
                    if "," in photo_b64:
                        photo_b64 = photo_b64.split(",", 1)[1]
                    try:
                        photo_bytes = base64.b64decode(photo_b64)
                        img_res = media_integrity_analyzer.process_image_submission(
                            file_bytes=photo_bytes,
                            original_filename=photo_filename if photo_filename != "none" else "citizen_photo.jpg",
                            reported_lat=lat,
                            reported_lon=lon,
                            reported_timestamp_iso=datetime.now(timezone.utc).isoformat(),
                            category_hint=payload.get("category", ""),
                            notes_hint=payload.get("user_notes", ""),
                            target_dir=UPLOADS_DIR
                        )
                        if img_res.get("success"):
                            photo_filename = img_res["filename"]
                            photo_sha256 = img_res["file_sha256"]
                            ai_analysis = img_res
                    except Exception as e:
                        print(f"Error validating/saving photo: {e}")

                # Optional user attachment
                current_user = self._get_authenticated_user()
                sub_user_id = current_user["id"] if current_user else None

                report_record = {
                    "latitude": lat,
                    "longitude": lon,
                    "accuracy_m": float(payload.get("accuracy_m", 10.0)),
                    "state": spatial_info["state"],
                    "district": spatial_info["district"],
                    "nearest_settlement": spatial_info["nearest_settlement"],
                    "settlement_distance_km": spatial_info["settlement_distance_km"],
                    "category": payload.get("category", "SURFACE_TENSION_CRACK"),
                    "displacement_width": payload.get("displacement_width", "5_TO_15_CM"),
                    "water_seepage": 1 if payload.get("water_seepage") else 0,
                    "seepage_flow_type": payload.get("seepage_flow_type", "CLEAR_TRICKLE"),
                    "nearby_structures_count": payload.get("nearby_structures_count", "FEW_1_TO_5"),
                    "corridor_proximity": payload.get("corridor_proximity", "Local Road"),
                    "slope_estimate_deg": float(payload.get("slope_estimate_deg", 35.0)),
                    "crack_width_cm": float(payload.get("crack_width_cm", 15.0)),
                    "photo_filename": photo_filename,
                    "video_id": payload.get("video_id"),
                    "photo_sha256": photo_sha256,
                    "ai_analysis_json": json.dumps(ai_analysis) if ai_analysis else None,
                    "user_notes": payload.get("user_notes", ""),
                    "nearest_c11_event_id": spatial_info["nearest_c11_event_id"],
                    "distance_to_runout_m": spatial_info["distance_to_runout_m"],
                    "intersects_c11_runout": 1 if spatial_info["intersects_c11_runout"] else 0
                }

                # Check Citizen Report Abuse (Rate Limit + Proximity Duplicate)
                abuse_check = database.check_citizen_report_abuse(
                    user_id=sub_user_id,
                    latitude=lat,
                    longitude=lon
                )
                if not abuse_check.get("allowed", True):
                    if abuse_check.get("flag_type") == "RATE_LIMIT_EXCEEDED":
                        return self._send_error_json("ABUSE_PREVENTION", abuse_check.get("reason"), 429)
                    elif abuse_check.get("flag_type") == "DUPLICATE_REPORT":
                        # Mark duplicate submissions under review without abruptly dropping
                        report_record["verification_status"] = "UNDER_REVIEW" 

                rep_id = database.add_report(report_record, submitted_by_user_id=sub_user_id)
                database.record_audit_log(
                    "REPORT_SUBMITTED",
                    user_id=sub_user_id,
                    target_type="REPORT",
                    target_id=rep_id,
                    metadata={"category": report_record["category"], "state": spatial_info["state"]},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "message": "Report successfully incorporated into shared prototype catalog.",
                    "report_id": rep_id,
                    "spatial_analysis": spatial_info,
                    "photo_sha256": photo_sha256,
                    "ai_analysis": ai_analysis
                }, status_code=201)

            except Exception as e:
                return self._send_error_json("VALIDATION_ERROR", str(e), 400)

        # 5a. Citizen Video Upload & Integrity Pipeline (Phase 4A)
        if path == "/api/videos/upload":
            try:
                payload = self._read_json_body()
                video_b64 = payload.get("video_base64", "")
                filename = payload.get("filename", "citizen_video.mp4")
                report_id = payload.get("report_id")
                claimed_mime = payload.get("mime_type", "video/mp4")
                lat = float(payload.get("latitude")) if payload.get("latitude") is not None else None
                lon = float(payload.get("longitude")) if payload.get("longitude") is not None else None

                if not video_b64:
                    return self._send_error_json("MISSING_DATA", "video_base64 is required", 400)

                if "," in video_b64:
                    video_b64 = video_b64.split(",", 1)[1]

                try:
                    video_bytes = base64.b64decode(video_b64)
                except Exception as e:
                    return self._send_error_json("INVALID_BASE64", f"Could not decode base64: {e}", 400)

                current_user = self._get_authenticated_user()
                result = video_analyzer.process_video_submission(
                    file_bytes=video_bytes,
                    original_filename=filename,
                    claimed_mime=claimed_mime,
                    report_id=report_id,
                    gps_lat=lat,
                    gps_lon=lon
                )

                database.record_audit_log(
                    "VIDEO_SUBMITTED",
                    user_id=current_user["id"] if current_user else None,
                    target_type="VIDEO",
                    target_id=result.get("video_id", "UNKNOWN"),
                    metadata={
                        "filename": filename,
                        "status": result.get("moderation_status"),
                        "sha256": result.get("sha256_hash", "")[:12]
                    },
                    ip_address=client_ip
                )

                status_code = 201 if result.get("success", False) else 422
                return self._send_json(result, status_code=status_code)
            except Exception as e:
                return self._send_error_json("VIDEO_PROCESSING_ERROR", str(e), 500)

        # 5b. Master Live Monitoring Control: Start (Phase 3)
        if path == "/api/live-monitoring/start":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required to start live monitoring.", 401)
            
            if user["role"] not in ("ADMIN", "FIELD_OFFICER", "ANALYST"):
                return self._send_error_json("FORBIDDEN", "Insufficient privileges. Operational role required to control live monitoring.", 403)
            
            result = live_monitoring_controller.start_monitoring(
                user=f"{user['full_name']} ({user['role']})",
                ip=client_ip
            )
            status_code = 200 if result.get("success") else 400
            if not result.get("success") and result.get("error") == "STORAGE_ERROR":
                status_code = 507
            return self._send_json(result, status_code=status_code)

        # 5c. Master Live Monitoring Control: Stop (Phase 4)
        if path == "/api/live-monitoring/stop":
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required to stop live monitoring.", 401)
            
            if user["role"] not in ("ADMIN", "FIELD_OFFICER", "ANALYST"):
                return self._send_error_json("FORBIDDEN", "Insufficient privileges. Operational role required to control live monitoring.", 403)
            
            result = live_monitoring_controller.stop_monitoring(
                user=f"{user['full_name']} ({user['role']})",
                ip=client_ip
            )
            status_code = 200 if result.get("success") else 400
            return self._send_json(result, status_code=status_code)

        # 6. Demonstrator Control & Mode State Machine
        if path == "/api/system/control":
            try:
                payload = self._read_json_body()
                action = payload.get("action", "").upper().strip()
                
                app_env = os.environ.get("APP_ENV", "development").lower()
                user = self._get_authenticated_user()
                if app_env == "production" and (not user or user["role"] == "PUBLIC_USER"):
                    return self._send_error_json("FORBIDDEN", "Demonstrator authentication required to control monitoring state.", 403)

                if action == "START_LIVE":
                    res = orchestrator.start_live_monitoring()
                elif action in ("STOP_LIVE", "STOP", "STOP_MONITORING"):
                    res = orchestrator.stop_monitoring()
                elif action == "START_REPLAY":
                    res = orchestrator.start_historical_replay()
                elif action == "PAUSE_REPLAY":
                    res = orchestrator.pause_replay()
                elif action == "RESUME_REPLAY":
                    res = orchestrator.resume_replay()
                elif action == "START_DEMO":
                    res = orchestrator.start_demo_scenario()
                elif action == "STOP_DEMO":
                    res = orchestrator.stop_monitoring()
                else:
                    return self._send_error_json("VALIDATION_ERROR", f"Unknown control action: '{action}'.", 400)

                database.record_audit_log(
                    "SYSTEM_CONTROL",
                    user_id=user["id"] if user else None,
                    target_type="SYSTEM",
                    target_id=action,
                    metadata={"result": res},
                    ip_address=client_ip
                )

                current_state = orchestrator.get_state()
                return self._send_json({
                    "status": "SUCCESS",
                    "action": action,
                    "mode": current_state["mode"],
                    "system_status": current_state["status"],
                    "orchestrator": res,
                    "state": current_state
                })
            except Exception as e:
                return self._send_error_json("SERVER_ERROR", str(e), 500)

        # 7. Live Satellite Ingestion Refresh
        if path == "/api/ingestion/refresh":
            try:
                refresh_res = ingestion_engine.refresh_all_feeds(mode="LIVE_MONITORING")
                live_features = refresh_res.get("live_features", {})
                new_predictions = fusion_engine.compute_fused_hotspots(live_features=live_features)
                
                # Store prediction snapshot locally and sync to Drive if linked
                snap_file = f"live_prediction_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
                snap_path = storage_engine.save_snapshot("predictions/risk", snap_file, new_predictions, mode="LIVE_MONITORING")
                
                provenance = ingestion_engine.get_public_status()
                return self._send_json({
                    "status": "SUCCESS",
                    "message": "Live satellite observations successfully retrieved from NASA CMR and Element84 STAC.",
                    "provenance": provenance,
                    "refresh_result": refresh_res,
                    "storage_snapshot": snap_path,
                    "drive_sync_status": storage_engine.get_status(),
                    "prediction_summary": new_predictions.get("metadata", {}).get("tier_breakdown", {})
                })
            except Exception as e:
                return self._send_error_json("INGESTION_ERROR", str(e), 500)

        self.send_error(404, "Endpoint not found")

    # =========================================================================
    # PATCH HANDLER
    # =========================================================================

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        client_ip = self._get_client_ip()

        # 1. Protected Verification: /api/reports/<report_id>/verify
        if path.startswith("/api/reports/") and path.endswith("/verify"):
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                rep_id = parts[2]
                user = self._get_authenticated_user()
                if not user:
                    return self._send_error_json("UNAUTHORIZED", "Authentication required to verify reports.", 401)
                
                # Enforce role authorization: Only FIELD_OFFICER or ADMIN can verify
                if user["role"] not in ("FIELD_OFFICER", "ADMIN"):
                    return self._send_error_json("FORBIDDEN", "Field Officer or Administrator role required for report verification.", 403)

                try:
                    payload = self._read_json_body()
                    new_status = payload.get("verification_status", "FIELD_VERIFIED")
                    verifier_title = f"{user['full_name']} ({user['role']})"
                    notes = payload.get("verification_notes", f"Verified by {verifier_title}")

                    success = database.update_verification_status(
                        rep_id,
                        new_status,
                        verified_by=verifier_title,
                        notes=notes,
                        verified_by_user_id=user["id"]
                    )

                    if success:
                        database.record_audit_log(
                            "REPORT_VERIFIED",
                            user_id=user["id"],
                            target_type="REPORT",
                            target_id=rep_id,
                            metadata={"status": new_status, "verified_by": verifier_title},
                            ip_address=client_ip
                        )
                        return self._send_json({
                            "status": "SUCCESS",
                            "message": f"Report {rep_id} updated to {new_status} in shared database.",
                            "report_id": rep_id,
                            "verification_status": new_status
                        })
                    else:
                        return self._send_error_json("NOT_FOUND", f"Report {rep_id} not found", 404)
                except Exception as e:
                    return self._send_error_json("VALIDATION_ERROR", str(e), 400)

        # 1b. Citizen Video Moderation: /api/videos/<id>/moderate (Phase 4A)
        if path.startswith("/api/videos/") and path.endswith("/moderate"):
            user = self._get_authenticated_user()
            verifier = f"{user['full_name']} ({user['role']})" if user else "Authorized Analyst"
            try:
                parts = path.strip("/").split("/")
                vid_id = parts[2]
                payload = self._read_json_body()
                new_status = payload.get("moderation_status") or payload.get("status")
                notes = payload.get("notes", "")

                if not new_status:
                    return self._send_error_json("MISSING_STATUS", "moderation_status required (VERIFIED, REJECTED, UNDER_REVIEW)", 400)

                mod_result = video_analyzer.moderate_video(
                    video_id=vid_id,
                    new_status=new_status,
                    verified_by=verifier,
                    notes=notes
                )

                database.record_audit_log(
                    "VIDEO_MODERATED",
                    user_id=user["id"] if user else None,
                    target_type="VIDEO",
                    target_id=vid_id,
                    metadata={"new_status": new_status, "verified_by": verifier},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "video": mod_result
                })
            except KeyError as ke:
                return self._send_error_json("NOT_FOUND", str(ke), 404)
            except ValueError as ve:
                return self._send_error_json("VALIDATION_ERROR", str(ve), 400)
            except Exception as e:
                return self._send_error_json("MODERATION_ERROR", str(e), 500)

        # 2. Admin: Approve Role Request: /api/admin/role-requests/<id>/approve
        if path.startswith("/api/admin/role-requests/") and path.endswith("/approve"):
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrator privilege required.", 403)

            try:
                parts = path.strip("/").split("/")
                req_id = int(parts[3])
                role_req = database.get_role_request_by_id(req_id)
                if not role_req:
                    return self._send_error_json("NOT_FOUND", "Role request not found.", 404)

                # Requesters cannot approve their own request
                if role_req["user_id"] == user["id"]:
                    return self._send_error_json("FORBIDDEN", "Administrators cannot approve their own role elevation requests.", 403)

                target_role = role_req["requested_role"]
                database.review_role_request(req_id, "APPROVED", user["id"])
                database.update_user_role(role_req["user_id"], target_role)

                database.record_audit_log(
                    "ROLE_APPROVED",
                    user_id=user["id"],
                    target_type="ROLE_REQUEST",
                    target_id=str(req_id),
                    metadata={"target_user_id": role_req["user_id"], "elevated_to": target_role},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "message": f"Role request {req_id} approved. User promoted to {target_role}."
                })
            except ValueError:
                return self._send_error_json("VALIDATION_ERROR", "Invalid role request ID.", 400)

        # 3. Admin: Reject Role Request: /api/admin/role-requests/<id>/reject
        if path.startswith("/api/admin/role-requests/") and path.endswith("/reject"):
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrator privilege required.", 403)

            try:
                parts = path.strip("/").split("/")
                req_id = int(parts[3])
                role_req = database.get_role_request_by_id(req_id)
                if not role_req:
                    return self._send_error_json("NOT_FOUND", "Role request not found.", 404)

                # Requesters cannot review their own request
                if role_req["user_id"] == user["id"]:
                    return self._send_error_json("FORBIDDEN", "Administrators cannot reject their own role elevation requests.", 403)

                database.review_role_request(req_id, "REJECTED", user["id"])
                # Reset requested_role on user
                database.update_user_role(role_req["user_id"], role_req["current_role"])

                database.record_audit_log(
                    "ROLE_REJECTED",
                    user_id=user["id"],
                    target_type="ROLE_REQUEST",
                    target_id=str(req_id),
                    metadata={"target_user_id": role_req["user_id"]},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "message": f"Role request {req_id} rejected. User remains {role_req['current_role']}."
                })
            except ValueError:
                return self._send_error_json("VALIDATION_ERROR", "Invalid role request ID.", 400)

        # 4. Admin: Update User Role: /api/admin/users/<id>/role
        if path.startswith("/api/admin/users/") and path.endswith("/role"):
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrator privilege required.", 403)

            try:
                parts = path.strip("/").split("/")
                target_user_id = int(parts[3])
                payload = self._read_json_body()
                new_role = payload.get("role", "").strip().upper()

                if new_role not in ("PUBLIC_USER", "FIELD_OFFICER", "ANALYST", "ADMIN"):
                    return self._send_error_json("VALIDATION_ERROR", "Invalid role specified.", 422)

                target_user = database.get_user_by_id(target_user_id)
                if not target_user:
                    return self._send_error_json("NOT_FOUND", "Target user not found.", 404)

                # Prevent demoting last active administrator
                if target_user["role"] == "ADMIN" and new_role != "ADMIN":
                    if database.count_active_admins() <= 1:
                        return self._send_error_json("FORBIDDEN", "Cannot demote the final active administrator.", 403)

                database.update_user_role(target_user_id, new_role)
                database.record_audit_log(
                    "ROLE_CHANGED",
                    user_id=user["id"],
                    target_type="USER",
                    target_id=str(target_user_id),
                    metadata={"old_role": target_user["role"], "new_role": new_role},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "message": f"User {target_user_id} role updated to {new_role}."
                })
            except ValueError:
                return self._send_error_json("VALIDATION_ERROR", "Invalid user ID.", 400)

        # 5. Admin: Update User Status: /api/admin/users/<id>/status
        if path.startswith("/api/admin/users/") and path.endswith("/status"):
            user = self._get_authenticated_user()
            if not user:
                return self._send_error_json("UNAUTHORIZED", "Authentication required.", 401)
            if user["role"] != "ADMIN":
                return self._send_error_json("FORBIDDEN", "Administrator privilege required.", 403)

            try:
                parts = path.strip("/").split("/")
                target_user_id = int(parts[3])
                payload = self._read_json_body()
                new_status = payload.get("status", "").strip().upper()

                if new_status not in ("ACTIVE", "SUSPENDED", "DISABLED"):
                    return self._send_error_json("VALIDATION_ERROR", "Status must be ACTIVE, SUSPENDED, or DISABLED.", 422)

                target_user = database.get_user_by_id(target_user_id)
                if not target_user:
                    return self._send_error_json("NOT_FOUND", "Target user not found.", 404)

                # Prevent disabling/suspending last active administrator
                if target_user["role"] == "ADMIN" and new_status in ("SUSPENDED", "DISABLED"):
                    if database.count_active_admins() <= 1:
                        return self._send_error_json("FORBIDDEN", "Cannot suspend or disable the final active administrator.", 403)

                database.update_user_status(target_user_id, new_status)
                
                action_tag = "USER_SUSPENDED" if new_status == "SUSPENDED" else "USER_DISABLED" if new_status == "DISABLED" else "USER_RESTORED"
                database.record_audit_log(
                    action_tag,
                    user_id=user["id"],
                    target_type="USER",
                    target_id=str(target_user_id),
                    metadata={"old_status": target_user["status"], "new_status": new_status},
                    ip_address=client_ip
                )

                return self._send_json({
                    "status": "SUCCESS",
                    "message": f"User {target_user_id} status updated to {new_status}."
                })
            except ValueError:
                return self._send_error_json("VALIDATION_ERROR", "Invalid user ID.", 400)

        self.send_error(404, "Endpoint not found")

def start_server(port=PORT, auto_start_monitoring=True):
    database.init_db()
    live_monitoring_controller.reset_for_restart()
    monitoring_res = None
    if auto_start_monitoring:
        try:
            monitoring_res = live_monitoring_controller.start_monitoring(
                user="SYSTEM_ADMIN (ADMIN)",
                ip="127.0.0.1",
                spawn_worker=True
            )
        except Exception as err:
            logger.error(f"Automatic live monitoring startup encountered error: {err}")
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, NERSafeRequestHandler)
    print("=" * 80)
    print(f"NER-SAFE LIVE MULTI-SOURCE MONITORING SERVER (AUTHENTICATED) STARTED")
    print(f"  URL: http://localhost:{port}")
    print(f"  Live Homepage: http://localhost:{port}/")
    print(f"  Monitoring API: http://localhost:{port}/api/monitoring/status")
    print(f"  Auth API:       http://localhost:{port}/api/auth/me")
    print(f"  Hotspots API:   http://localhost:{port}/api/monitoring/hotspots")
    print(f"  Citizen API:    http://localhost:{port}/api/reports")
    if monitoring_res and monitoring_res.get("success"):
        print(f"  Live Monitoring: ACTIVE (Autonomous scheduler & worker thread running)")
    else:
        print(f"  Live Monitoring: {live_monitoring_controller.get_status().get('state')}")
    print("=" * 80)
    return httpd

if __name__ == "__main__":
    httpd = start_server(PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        try:
            live_monitoring_controller.stop_monitoring(user="SYSTEM_ADMIN (ADMIN)", ip="127.0.0.1")
        except Exception:
            pass
        httpd.server_close()
