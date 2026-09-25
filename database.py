"""
NER-SAFE: SQLite Database Module for Shared Observations, Authentication & Role Management
Ensures multi-device synchronization and production-grade role-based access control.

Schema:
- citizen_reports: Persistent ground observations
- users: User profiles and roles (PUBLIC_USER, FIELD_OFFICER, ANALYST, ADMIN)
- sessions: Server-side cryptographically secure sessions
- role_requests: Elevation requests requiring ADMIN approval
- audit_logs: Security and administrative action logs
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "DATABASE")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "ner_safe_shared.db")

UPLOADS_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "UPLOADS")
os.makedirs(UPLOADS_DIR, exist_ok=True)

SYNTHETIC_DATA_PATH = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_13", "data", "synthetic_demonstration_reports.json")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Citizen Reports Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizen_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT UNIQUE NOT NULL,
        timestamp_utc TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        accuracy_m REAL DEFAULT 10.0,
        state TEXT NOT NULL,
        district TEXT NOT NULL,
        nearest_settlement TEXT,
        settlement_distance_km REAL,
        category TEXT NOT NULL,
        displacement_width TEXT,
        water_seepage INTEGER DEFAULT 0,
        seepage_flow_type TEXT,
        nearby_structures_count TEXT,
        corridor_proximity TEXT,
        slope_estimate_deg REAL DEFAULT 35.0,
        crack_width_cm REAL DEFAULT 20.0,
        photo_filename TEXT,
        user_notes TEXT,
        sync_status TEXT DEFAULT 'SYNCHRONIZED_LOCAL',
        verification_status TEXT DEFAULT 'UNVERIFIED_OBSERVATION',
        verified_by TEXT,
        verification_notes TEXT,
        record_type TEXT DEFAULT 'CITIZEN_OBSERVATION',
        data_category TEXT DEFAULT 'CITIZEN_OBSERVATION',
        nearest_c11_event_id TEXT,
        distance_to_runout_m REAL,
        intersects_c11_runout INTEGER DEFAULT 0,
        submitted_by_user_id INTEGER,
        verified_by_user_id INTEGER,
        verified_at TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # Check and add authentication and media columns to citizen_reports if table was created in earlier step
    cursor.execute("PRAGMA table_info(citizen_reports)")
    existing_cols = {row["name"] for row in cursor.fetchall()}
    if "submitted_by_user_id" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN submitted_by_user_id INTEGER;")
    if "verified_by_user_id" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN verified_by_user_id INTEGER;")
    if "verified_at" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN verified_at TEXT;")
    if "video_id" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN video_id TEXT;")
    if "photo_sha256" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN photo_sha256 TEXT;")
    if "ai_analysis_json" not in existing_cols:
        cursor.execute("ALTER TABLE citizen_reports ADD COLUMN ai_analysis_json TEXT;")

    # 2. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'PUBLIC_USER',
        requested_role TEXT,
        state TEXT NOT NULL,
        organization TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_login_at TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")

    # 3. Server-Side Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        revoked_at TEXT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);")

    # 4. Role Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS role_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        requested_role TEXT NOT NULL,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        reviewed_by INTEGER REFERENCES users(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_role_requests_status ON role_requests(status);")

    # 5. Security & Administrative Audit Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER REFERENCES users(id),
        action TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        metadata TEXT,
        ip_address TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")

    # 6. Observations Table (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_key TEXT NOT NULL,
        product_identifier TEXT NOT NULL,
        observation_time_utc TEXT NOT NULL,
        ingestion_time_utc TEXT NOT NULL,
        status TEXT NOT NULL,
        quality_status TEXT NOT NULL,
        file_hash TEXT,
        metadata_json TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_obs_source_time ON observations(source_key, observation_time_utc);")

    # 7. Forecast Assessments Table (C15 Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forecast_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hotspot_id TEXT NOT NULL,
        forecast_horizon TEXT NOT NULL,
        forecast_probability REAL NOT NULL,
        uncertainty_entropy REAL NOT NULL,
        likely_initiation_zone TEXT,
        model_name TEXT NOT NULL,
        model_version TEXT NOT NULL,
        validation_status TEXT NOT NULL,
        inputs_json TEXT,
        generated_time_utc TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecast_hotspot_horizon ON forecast_assessments(hotspot_id, forecast_horizon);")

    # 8. Alert Delivery Table (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_delivery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT UNIQUE NOT NULL,
        hotspot_id TEXT NOT NULL,
        tier TEXT NOT NULL,
        forecast_probability REAL NOT NULL,
        delivery_state TEXT NOT NULL,
        network_level TEXT DEFAULT 'ONLINE',
        recipient_count INTEGER DEFAULT 1,
        dispatched_at_utc TEXT NOT NULL,
        delivered_at_utc TEXT,
        expires_at_utc TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alert_delivery_state ON alert_delivery(delivery_state);")

    # 9. Citizen Abuse Flags Table (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizen_abuse_flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        report_id TEXT,
        flag_type TEXT NOT NULL,
        reason TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'FLAGGED',
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_abuse_flags_user ON citizen_abuse_flags(user_id);")

    # 10. Report Verification Events Audit (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_verification_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id TEXT NOT NULL,
        previous_status TEXT,
        new_status TEXT NOT NULL,
        verified_by_user_id INTEGER,
        notes TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rep_verif_report ON report_verification_events(report_id);")

    # 11. NASA SMAP NRT Observations Table (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS smap_nrt_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        product TEXT NOT NULL,
        version TEXT NOT NULL,
        observation_time TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        processed_at TEXT NOT NULL,
        source_file TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        quality_status TEXT NOT NULL,
        freshness_status TEXT NOT NULL,
        valid_fraction REAL,
        mean_soil_moisture REAL,
        median_soil_moisture REAL,
        anomaly REAL NOT NULL,
        anomaly_status TEXT NOT NULL,
        coverage_status TEXT NOT NULL,
        processing_duration REAL,
        error_message TEXT,
        metadata_json TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_smap_nrt_obs_time ON smap_nrt_observations(observation_time);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_smap_nrt_sha256 ON smap_nrt_observations(sha256);")

    # 13. Sentinel-1 InSAR Scenes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insar_scenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scene_id TEXT UNIQUE NOT NULL,
        granule_name TEXT NOT NULL,
        platform TEXT NOT NULL,
        mode TEXT NOT NULL,
        product_type TEXT NOT NULL,
        polarization TEXT NOT NULL,
        relative_orbit INTEGER NOT NULL,
        orbit_direction TEXT NOT NULL,
        sensing_start_utc TEXT NOT NULL,
        sensing_stop_utc TEXT NOT NULL,
        size_bytes INTEGER,
        sha256 TEXT,
        local_path TEXT,
        acquisition_status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insar_scenes_start ON insar_scenes(sensing_start_utc);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insar_scenes_orbit ON insar_scenes(relative_orbit, orbit_direction);")

    # 14. Sentinel-1 InSAR Interferometric Pairs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insar_pairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pair_id TEXT UNIQUE NOT NULL,
        primary_scene_id TEXT NOT NULL,
        secondary_scene_id TEXT NOT NULL,
        primary_time_utc TEXT NOT NULL,
        secondary_time_utc TEXT NOT NULL,
        temporal_baseline_days REAL NOT NULL,
        perpendicular_baseline_m REAL,
        relative_orbit INTEGER NOT NULL,
        orbit_direction TEXT NOT NULL,
        swath TEXT NOT NULL,
        polarization TEXT NOT NULL,
        coherence_mean REAL,
        coherence_median REAL,
        coherence_valid_fraction REAL,
        unwrapped_pixel_count INTEGER,
        disp_mean_mm REAL,
        disp_median_mm REAL,
        disp_min_mm REAL,
        disp_max_mm REAL,
        reference_point_name TEXT,
        pair_status TEXT NOT NULL,
        processing_status TEXT NOT NULL,
        processing_duration_s REAL,
        coherence_raster_path TEXT,
        interferogram_raster_path TEXT,
        unwrapped_phase_raster_path TEXT,
        displacement_raster_path TEXT,
        sha256 TEXT,
        metadata_json TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insar_pairs_time ON insar_pairs(primary_time_utc, secondary_time_utc);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insar_pairs_status ON insar_pairs(processing_status);")

    # 15. Sentinel-1 InSAR Multi-Temporal Deformation Products Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insar_deformation_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        network_id TEXT UNIQUE NOT NULL,
        methodology TEXT NOT NULL,
        stack_size INTEGER NOT NULL,
        pair_count INTEGER NOT NULL,
        earliest_observation_utc TEXT NOT NULL,
        latest_observation_utc TEXT NOT NULL,
        temporal_span_days REAL NOT NULL,
        mean_coherence REAL,
        mean_velocity_mm_year REAL,
        velocity_std_mm_year REAL,
        velocity_min_mm_year REAL,
        velocity_max_mm_year REAL,
        reference_point_name TEXT NOT NULL,
        reference_stability_status TEXT NOT NULL,
        phase_closure_mean_rad REAL,
        scientific_status TEXT NOT NULL,
        multitemporal_status TEXT NOT NULL,
        velocity_raster_path TEXT,
        metadata_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_insar_def_status ON insar_deformation_products(scientific_status);")

    # 16. Canonical Live Multimodal Features Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_multimodal_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hotspot_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        reference_time_utc TEXT NOT NULL,
        susceptibility_xgboost REAL NOT NULL,
        susceptibility_rf_fallback REAL NOT NULL,
        rainfall_anomaly REAL NOT NULL,
        soil_moisture_anomaly REAL NOT NULL,
        satellite_change_flag REAL NOT NULL,
        cnn_probability REAL,
        cnn_uncertainty REAL,
        cnn_status TEXT,
        c15_probability REAL,
        c15_entropy REAL,
        c15_status TEXT,
        insar_deformation_indicator REAL,
        insar_velocity_mm_yr REAL,
        insar_coherence REAL,
        insar_quality REAL,
        insar_status TEXT,
        feature_payload_json TEXT,
        created_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_multimodal_hotspot ON live_multimodal_features(hotspot_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_multimodal_time ON live_multimodal_features(reference_time_utc);")

    # 17. Citizen Videos & Moderation Table (Additive)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizen_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT UNIQUE NOT NULL,
        report_id TEXT,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        duration_seconds REAL DEFAULT 0.0,
        sha256_hash TEXT NOT NULL,
        gps_latitude REAL,
        gps_longitude REAL,
        capture_time_utc TEXT,
        quarantine_path TEXT NOT NULL,
        transcoded_path TEXT,
        keyframes_json TEXT,
        phash_list_json TEXT,
        moderation_status TEXT DEFAULT 'READY_FOR_REVIEW',
        verified_by TEXT,
        verification_notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_status ON citizen_videos(moderation_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_sha256 ON citizen_videos(sha256_hash);")

    conn.commit()

    # Seed demonstration reports if table empty
    cursor.execute("SELECT COUNT(*) FROM citizen_reports")
    count = cursor.fetchone()[0]
    if count == 0 and os.path.exists(SYNTHETIC_DATA_PATH):
        print("Seeding database with 13 validated benchmark demonstration records...")
        with open(SYNTHETIC_DATA_PATH, "r", encoding="utf-8") as f:
            bench_records = json.load(f)
        
        for r in bench_records:
            loc = r.get("location", {})
            obs = r.get("observation_details", {})
            spat = r.get("spatial_context", {})
            sys = r.get("system_state", {})
            
            cursor.execute("""
            INSERT OR IGNORE INTO citizen_reports (
                report_id, timestamp_utc, latitude, longitude, accuracy_m,
                state, district, nearest_settlement, settlement_distance_km,
                category, displacement_width, water_seepage, seepage_flow_type,
                nearby_structures_count, corridor_proximity, slope_estimate_deg,
                crack_width_cm, photo_filename, user_notes, sync_status,
                verification_status, verified_by, verification_notes,
                record_type, data_category, nearest_c11_event_id,
                distance_to_runout_m, intersects_c11_runout, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["report_id"],
                r.get("timestamp_utc", datetime.now().isoformat()),
                loc.get("latitude", 25.0),
                loc.get("longitude", 92.0),
                loc.get("accuracy_m", 8.5),
                loc.get("state", "Meghalaya"),
                loc.get("district", "East Jaintia Hills"),
                loc.get("nearest_settlement", "Unknown"),
                loc.get("settlement_distance_km", 0.0),
                obs.get("category", "SURFACE_TENSION_CRACK"),
                obs.get("displacement_width", "15_TO_50_CM"),
                1 if obs.get("water_seepage") else 0,
                obs.get("seepage_flow_type", "MUDDY_TURBID_FLOW"),
                obs.get("nearby_structures_count", "FEW_1_TO_5"),
                obs.get("corridor_proximity", "NH-06 Cut"),
                obs.get("slope_estimate_deg", 35.0),
                obs.get("crack_width_cm", 25.0),
                "demo_benchmark_crack.svg",
                obs.get("user_notes", "Benchmark demonstration observation."),
                sys.get("sync_status", "SYNCHRONIZED_LOCAL"),
                sys.get("verification_status", "UNVERIFIED_OBSERVATION"),
                sys.get("verified_by"),
                sys.get("verification_notes", "Initial intake."),
                r.get("record_type", "SYNTHETIC_DEMONSTRATION"),
                "CITIZEN_OBSERVATION",
                spat.get("nearest_c11_event_id", "EVT-MEG-023"),
                spat.get("distance_to_runout_m", 0.0),
                1 if spat.get("intersects_c11_runout") else 0,
                datetime.now().isoformat()
            ))
        conn.commit()

    conn.close()

# =========================================================================
# USER MANAGEMENT FUNCTIONS
# =========================================================================

def create_user(full_name: str, email: str, password_hash: str, role: str = "PUBLIC_USER",
                requested_role: str = None, state: str = "Meghalaya", organization: str = "",
                status: str = "ACTIVE") -> int:
    """Creates a new user record. Enforces unique email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO users (full_name, email, password_hash, role, requested_role, state, organization, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (full_name.strip(), email.strip().lower(), password_hash, role, requested_role, state, organization, status, now_str, now_str))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_user_by_email(email: str) -> dict:
    """Fetches user by normalized email."""
    if not email:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> dict:
    """Fetches user by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users() -> list:
    """Fetches all users with sanitized fields (excludes password_hash)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, full_name, email, role, requested_role, state, organization, status, created_at, last_login_at
    FROM users ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user_last_login(user_id: int):
    """Updates user last_login_at timestamp."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?", (now_str, now_str, user_id))
    conn.commit()
    conn.close()

def update_user_role(user_id: int, new_role: str) -> bool:
    """Updates user role."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("UPDATE users SET role = ?, requested_role = NULL, updated_at = ? WHERE id = ?", (new_role, now_str, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def update_user_status(user_id: int, new_status: str) -> bool:
    """Updates user status (ACTIVE, SUSPENDED, DISABLED)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_str, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def count_active_admins() -> int:
    """Returns the number of active administrators to prevent accidental lockout."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE'")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# =========================================================================
# SESSION MANAGEMENT FUNCTIONS
# =========================================================================

def create_session(user_id: int, session_id: str, duration_seconds: int = 604800) -> dict:
    """
    Creates a server-side session.
    Default duration: 7 days (604800 seconds).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    expires = now + timedelta(seconds=duration_seconds)
    cursor.execute("""
    INSERT INTO sessions (id, user_id, created_at, expires_at, last_seen_at)
    VALUES (?, ?, ?, ?, ?)
    """, (session_id, user_id, now.isoformat(), expires.isoformat(), now.isoformat()))
    conn.commit()
    conn.close()
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat()
    }

def get_active_session(session_id: str) -> dict:
    """
    Retrieves an active, non-expired, non-revoked session joined with user details.
    """
    if not session_id:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    SELECT s.id as session_id, s.user_id, s.created_at as session_created_at, s.expires_at,
           u.id, u.full_name, u.email, u.role, u.requested_role, u.state, u.organization, u.status
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.id = ? AND s.revoked_at IS NULL AND s.expires_at > ?
    """, (session_id, now_str))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def touch_session(session_id: str):
    """Updates the last_seen_at timestamp for a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (datetime.now().isoformat(), session_id))
    conn.commit()
    conn.close()

def revoke_session(session_id: str) -> bool:
    """Invalidates a session server-side on logout."""
    if not session_id:
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET revoked_at = ? WHERE id = ?", (datetime.now().isoformat(), session_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

# =========================================================================
# ROLE REQUEST FUNCTIONS
# =========================================================================

def create_role_request(user_id: int, requested_role: str, reason: str = "") -> int:
    """Creates a role elevation request."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    # Mark any prior pending requests as SUPERSEDED
    cursor.execute("UPDATE role_requests SET status = 'SUPERSEDED' WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    cursor.execute("""
    INSERT INTO role_requests (user_id, requested_role, reason, status, created_at)
    VALUES (?, ?, ?, 'PENDING', ?)
    """, (user_id, requested_role, reason, now_str))
    req_id = cursor.lastrowid
    
    # Update requested_role in users table
    cursor.execute("UPDATE users SET requested_role = ?, updated_at = ? WHERE id = ?", (requested_role, now_str, user_id))
    
    conn.commit()
    conn.close()
    return req_id

def get_role_requests(status_filter: str = None) -> list:
    """Fetches role requests with user metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("""
        SELECT r.id, r.user_id, r.requested_role, r.reason, r.status, r.created_at, r.reviewed_at, r.reviewed_by,
               u.full_name, u.email, u.role as current_role, u.organization, u.state,
               rev.full_name as reviewer_name
        FROM role_requests r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN users rev ON r.reviewed_by = rev.id
        WHERE r.status = ?
        ORDER BY r.id DESC
        """, (status_filter,))
    else:
        cursor.execute("""
        SELECT r.id, r.user_id, r.requested_role, r.reason, r.status, r.created_at, r.reviewed_at, r.reviewed_by,
               u.full_name, u.email, u.role as current_role, u.organization, u.state,
               rev.full_name as reviewer_name
        FROM role_requests r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN users rev ON r.reviewed_by = rev.id
        ORDER BY r.id DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_role_request_by_id(req_id: int) -> dict:
    """Fetches role request by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT r.*, u.full_name, u.email, u.role as current_role
    FROM role_requests r
    JOIN users u ON r.user_id = u.id
    WHERE r.id = ?
    """, (req_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def review_role_request(req_id: int, new_status: str, reviewer_id: int) -> bool:
    """Approves or rejects a role request."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    UPDATE role_requests
    SET status = ?, reviewed_at = ?, reviewed_by = ?
    WHERE id = ?
    """, (new_status, now_str, reviewer_id, req_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

# =========================================================================
# AUDIT LOG FUNCTIONS
# =========================================================================

def record_audit_log(action: str, user_id: int = None, target_type: str = None,
                     target_id: str = None, metadata: dict = None, ip_address: str = None) -> int:
    """Records a security or administrative action in audit_logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    meta_str = json.dumps(metadata) if metadata else None
    cursor.execute("""
    INSERT INTO audit_logs (user_id, action, target_type, target_id, metadata, ip_address, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, action, target_type, target_id, meta_str, ip_address, now_str))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_audit_logs(limit: int = 100) -> list:
    """Retrieves recent audit logs with actor names."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT a.id, a.user_id, a.action, a.target_type, a.target_id, a.metadata, a.ip_address, a.created_at,
           u.full_name as user_name, u.email as user_email, u.role as user_role
    FROM audit_logs a
    LEFT JOIN users u ON a.user_id = u.id
    ORDER BY a.id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# =========================================================================
# CITIZEN REPORT FUNCTIONS
# =========================================================================

def get_all_reports():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM citizen_reports ORDER BY id DESC")
    rows = cursor.fetchall()
    
    reports = []
    for row in rows:
        r = dict(row)
        feat = {
            "type": "Feature",
            "id": r["report_id"],
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]]
            },
            "properties": {
                "report_id": r["report_id"],
                "record_type": r["record_type"],
                "data_category": r["data_category"],
                "timestamp_utc": r["timestamp_utc"],
                "state": r["state"],
                "district": r["district"],
                "nearest_settlement": r["nearest_settlement"],
                "settlement_distance_km": r["settlement_distance_km"],
                "category": r["category"],
                "displacement_width": r["displacement_width"],
                "water_seepage": bool(r["water_seepage"]),
                "seepage_flow_type": r["seepage_flow_type"],
                "nearby_structures_count": r["nearby_structures_count"],
                "corridor_proximity": r["corridor_proximity"],
                "slope_estimate_deg": r["slope_estimate_deg"],
                "crack_width_cm": r["crack_width_cm"],
                "photo_filename": r["photo_filename"],
                "user_notes": r["user_notes"],
                "sync_status": r["sync_status"],
                "verification_status": r["verification_status"],
                "verified_by": r["verified_by"],
                "verification_notes": r["verification_notes"],
                "nearest_c11_event_id": r["nearest_c11_event_id"],
                "distance_to_runout_m": r["distance_to_runout_m"],
                "intersects_c11_runout": bool(r["intersects_c11_runout"]),
                "submitted_by_user_id": r.get("submitted_by_user_id"),
                "verified_by_user_id": r.get("verified_by_user_id"),
                "verified_at": r.get("verified_at"),
                "video_id": r.get("video_id"),
                "photo_sha256": r.get("photo_sha256"),
                "ai_analysis": json.loads(r["ai_analysis_json"]) if r.get("ai_analysis_json") else None
            }
        }
        reports.append(feat)
    
    conn.close()
    return {
        "type": "FeatureCollection",
        "name": "NER_SAFE_Shared_Observations",
        "features": reports
    }

def add_report(report_data: dict, submitted_by_user_id: int = None) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now_str = datetime.now().isoformat()
    rep_id = report_data.get("report_id")
    if not rep_id:
        st_code = "MEG" if "Meghalaya" in report_data.get("state", "Meghalaya") else "MIZ"
        date_tag = datetime.now().strftime("%Y%m%d")
        cursor.execute("SELECT COUNT(*) FROM citizen_reports WHERE report_id LIKE ?", (f"REP-{date_tag}%",))
        next_seq = cursor.fetchone()[0] + 1
        while True:
            rep_id = f"REP-{date_tag}-{st_code}-{next_seq:03d}"
            cursor.execute("SELECT 1 FROM citizen_reports WHERE report_id = ?", (rep_id,))
            if not cursor.fetchone():
                break
            next_seq += 1
    
    ai_analysis_raw = report_data.get("ai_analysis_json")
    if isinstance(ai_analysis_raw, dict):
        ai_analysis_raw = json.dumps(ai_analysis_raw)
    elif not ai_analysis_raw and report_data.get("ai_analysis"):
        ai_analysis_raw = json.dumps(report_data.get("ai_analysis"))

    cursor.execute("""
    INSERT INTO citizen_reports (
        report_id, timestamp_utc, latitude, longitude, accuracy_m,
        state, district, nearest_settlement, settlement_distance_km,
        category, displacement_width, water_seepage, seepage_flow_type,
        nearby_structures_count, corridor_proximity, slope_estimate_deg,
        crack_width_cm, photo_filename, user_notes, sync_status,
        verification_status, verified_by, verification_notes,
        record_type, data_category, nearest_c11_event_id,
        distance_to_runout_m, intersects_c11_runout, submitted_by_user_id, created_at,
        video_id, photo_sha256, ai_analysis_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rep_id,
        report_data.get("timestamp_utc", now_str),
        report_data["latitude"],
        report_data["longitude"],
        report_data.get("accuracy_m", 10.0),
        report_data.get("state", "Meghalaya"),
        report_data.get("district", "East Jaintia Hills"),
        report_data.get("nearest_settlement", "Nearby Village"),
        report_data.get("settlement_distance_km", 1.0),
        report_data.get("category", "SURFACE_TENSION_CRACK"),
        report_data.get("displacement_width", "5_TO_15_CM"),
        1 if report_data.get("water_seepage") else 0,
        report_data.get("seepage_flow_type", "CLEAR_TRICKLE"),
        report_data.get("nearby_structures_count", "FEW_1_TO_5"),
        report_data.get("corridor_proximity", "Local Road"),
        report_data.get("slope_estimate_deg", 35.0),
        report_data.get("crack_width_cm", 15.0),
        report_data.get("photo_filename", "none"),
        report_data.get("user_notes", ""),
        "SYNCHRONIZED_LOCAL",
        "UNVERIFIED_OBSERVATION",
        None,
        "Awaiting prototype field inspection.",
        "CITIZEN_OBSERVATION",
        "CITIZEN_OBSERVATION",
        report_data.get("nearest_c11_event_id", "None"),
        report_data.get("distance_to_runout_m", 999.0),
        1 if report_data.get("intersects_c11_runout") else 0,
        submitted_by_user_id,
        now_str,
        report_data.get("video_id"),
        report_data.get("photo_sha256"),
        ai_analysis_raw
    ))
    conn.commit()
    conn.close()
    return rep_id

def update_verification_status(report_id: str, new_status: str, verified_by: str = "FIELD_OFFICER_LOCAL (Prototype Role)",
                               notes: str = "", verified_by_user_id: int = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    UPDATE citizen_reports
    SET verification_status = ?, verified_by = ?, verification_notes = ?, verified_by_user_id = ?, verified_at = ?
    WHERE report_id = ?
    """, (new_status, verified_by, notes, verified_by_user_id, now_str, report_id))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def check_citizen_report_abuse(user_id: int, latitude: float, longitude: float) -> dict:
    """
    Evidence-based citizen report abuse detection.
    1. Per-user rate limiting (max 5 reports in 10 minutes)
    2. Duplicate report detection (within 50m and 1 hour for authenticated, or exact coordinate spam)
    Logs flags to citizen_abuse_flags without automated permanent ban.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    ten_min_ago = (datetime.now() - timedelta(minutes=10)).isoformat()
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    
    # 1. Rate limiting (if authenticated)
    if user_id:
        cursor.execute("""
        SELECT COUNT(*) FROM citizen_reports
        WHERE submitted_by_user_id = ? AND created_at >= ?
        """, (user_id, ten_min_ago))
        recent_count = cursor.fetchone()[0]
        if recent_count >= 5:
            cursor.execute("""
            INSERT INTO citizen_abuse_flags (user_id, flag_type, reason, severity, created_at)
            VALUES (?, 'RATE_LIMIT_EXCEEDED', 'Submitted >= 5 reports in 10 minutes', 'WARNING', ?)
            """, (user_id, now_str))
            conn.commit()
            conn.close()
            return {"allowed": False, "flag_type": "RATE_LIMIT_EXCEEDED", "reason": "Submission rate limit exceeded (max 5 reports per 10 minutes). Please wait."}

    # 2. Duplicate proximity detection (approx ~50m ~ 0.0005 deg within 1 hour)
    if user_id:
        cursor.execute("""
        SELECT report_id, latitude, longitude FROM citizen_reports
        WHERE submitted_by_user_id = ? AND created_at >= ?
        """, (user_id, one_hour_ago))
    else:
        cursor.execute("""
        SELECT report_id, latitude, longitude FROM citizen_reports
        WHERE (submitted_by_user_id IS NULL OR submitted_by_user_id = 0) AND created_at >= ?
        ORDER BY id DESC LIMIT 50
        """, (one_hour_ago,))
    
    rows = cursor.fetchall()
    for r in rows:
        d_lat = abs(r["latitude"] - latitude)
        d_lon = abs(r["longitude"] - longitude)
        if d_lat < 0.0005 and d_lon < 0.0005:
            cursor.execute("""
            INSERT INTO citizen_abuse_flags (user_id, report_id, flag_type, reason, severity, created_at)
            VALUES (?, ?, 'DUPLICATE_REPORT', 'Duplicate submission within 50m and 1 hour', 'INFO', ?)
            """, (user_id, r["report_id"], now_str))
            conn.commit()
            conn.close()
            return {"allowed": False, "flag_type": "DUPLICATE_REPORT", "reason": f"Duplicate report detected within 50 meters of a recent report ({r['report_id']})."}

    conn.close()
    return {"allowed": True}

def record_forecast_assessment(hotspot_id: str, horizon: str, probability: float,
                                uncertainty_entropy: float, likely_zone: str,
                                model_name: str, model_version: str,
                                validation_status: str, inputs: dict = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO forecast_assessments (
        hotspot_id, forecast_horizon, forecast_probability, uncertainty_entropy,
        likely_initiation_zone, model_name, model_version, validation_status,
        inputs_json, generated_time_utc, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        hotspot_id, horizon, probability, uncertainty_entropy,
        likely_zone, model_name, model_version, validation_status,
        json.dumps(inputs or {}), now_str, now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def record_alert_delivery(alert_id: str, hotspot_id: str, tier: str, probability: float,
                          delivery_state: str, network_level: str = 'ONLINE', expires_at: str = None) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    exp_str = expires_at or (datetime.now() + timedelta(hours=12)).isoformat()
    cursor.execute("""
    INSERT OR REPLACE INTO alert_delivery (
        alert_id, hotspot_id, tier, forecast_probability, delivery_state,
        network_level, dispatched_at_utc, expires_at_utc, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_id, hotspot_id, tier, probability, delivery_state,
        network_level, now_str, exp_str, now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

# =============================================================================
# SENTINEL-1 InSAR MULTI-TEMPORAL PERSISTENCE HELPERS
# =============================================================================

def register_insar_scene(scene_data: Dict[str, Any]) -> int:
    """Inserts or updates a Sentinel-1 SLC scene record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT OR REPLACE INTO insar_scenes (
        scene_id, granule_name, platform, mode, product_type,
        polarization, relative_orbit, orbit_direction,
        sensing_start_utc, sensing_stop_utc, size_bytes,
        sha256, local_path, acquisition_status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scene_data["scene_id"],
        scene_data.get("granule_name", scene_data.get("product_name", "")),
        scene_data.get("platform", "Sentinel-1D"),
        scene_data.get("mode", "IW"),
        scene_data.get("product_type", "SLC"),
        scene_data.get("polarization", "VV"),
        scene_data.get("relative_orbit", 150),
        scene_data.get("orbit_direction", "DESCENDING"),
        scene_data["sensing_start_utc"],
        scene_data["sensing_stop_utc"],
        scene_data.get("size_bytes", 0),
        scene_data.get("sha256", ""),
        scene_data.get("local_path", ""),
        scene_data.get("acquisition_status", "LIVE_VERIFIED"),
        now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def register_insar_pair(pair_data: Dict[str, Any]) -> int:
    """Inserts or updates an InSAR interferometric pair record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT OR REPLACE INTO insar_pairs (
        pair_id, primary_scene_id, secondary_scene_id,
        primary_time_utc, secondary_time_utc,
        temporal_baseline_days, perpendicular_baseline_m,
        relative_orbit, orbit_direction, swath, polarization,
        coherence_mean, coherence_median, coherence_valid_fraction,
        unwrapped_pixel_count, disp_mean_mm, disp_median_mm,
        disp_min_mm, disp_max_mm, reference_point_name,
        pair_status, processing_status, processing_duration_s,
        coherence_raster_path, interferogram_raster_path,
        unwrapped_phase_raster_path, displacement_raster_path,
        sha256, metadata_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pair_data["pair_id"],
        pair_data["primary_scene_id"],
        pair_data["secondary_scene_id"],
        pair_data["primary_time_utc"],
        pair_data["secondary_time_utc"],
        pair_data.get("temporal_baseline_days", 0.0),
        pair_data.get("perpendicular_baseline_m", 0.0),
        pair_data.get("relative_orbit", 150),
        pair_data.get("orbit_direction", "DESCENDING"),
        pair_data.get("swath", "IW1"),
        pair_data.get("polarization", "VV"),
        pair_data.get("coherence_mean", 0.0),
        pair_data.get("coherence_median", 0.0),
        pair_data.get("coherence_valid_fraction", 0.0),
        pair_data.get("unwrapped_pixel_count", 0),
        pair_data.get("disp_mean_mm", 0.0),
        pair_data.get("disp_median_mm", 0.0),
        pair_data.get("disp_min_mm", 0.0),
        pair_data.get("disp_max_mm", 0.0),
        pair_data.get("reference_point_name", "SHILLONG_PLATEAU_NORTH_BEDROCK_REF"),
        pair_data.get("pair_status", "VALID_PAIR"),
        pair_data.get("processing_status", "PROCESSED"),
        pair_data.get("processing_duration_s", 0.0),
        pair_data.get("coherence_raster_path", ""),
        pair_data.get("interferogram_raster_path", ""),
        pair_data.get("unwrapped_phase_raster_path", ""),
        pair_data.get("displacement_raster_path", ""),
        pair_data.get("sha256", ""),
        json.dumps(pair_data.get("metadata", {})),
        now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def save_insar_deformation_product(product_data: Dict[str, Any]) -> int:
    """Inserts or updates a multi-temporal InSAR deformation product record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT OR REPLACE INTO insar_deformation_products (
        network_id, methodology, stack_size, pair_count,
        earliest_observation_utc, latest_observation_utc,
        temporal_span_days, mean_coherence,
        mean_velocity_mm_year, velocity_std_mm_year,
        velocity_min_mm_year, velocity_max_mm_year,
        reference_point_name, reference_stability_status,
        phase_closure_mean_rad, scientific_status,
        multitemporal_status, velocity_raster_path,
        metadata_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_data["network_id"],
        product_data.get("methodology", "SBAS_SVD_TRIANGULAR_INVERSION"),
        product_data["stack_size"],
        product_data["pair_count"],
        product_data["earliest_observation_utc"],
        product_data["latest_observation_utc"],
        product_data.get("temporal_span_days", 0.0),
        product_data.get("mean_coherence", 0.0),
        product_data.get("mean_velocity_mm_year", 0.0),
        product_data.get("velocity_std_mm_year", 0.0),
        product_data.get("velocity_min_mm_year", 0.0),
        product_data.get("velocity_max_mm_year", 0.0),
        product_data.get("reference_point_name", "SHILLONG_PLATEAU_NORTH_BEDROCK_REF"),
        product_data.get("reference_stability_status", "STABLE_BEDROCK_ANCHOR"),
        product_data.get("phase_closure_mean_rad", 0.0),
        product_data.get("scientific_status", "RESEARCH_ONLY"),
        product_data.get("multitemporal_status", "SBAS_INITIAL_STACK_FORMED"),
        product_data.get("velocity_raster_path", ""),
        json.dumps(product_data.get("metadata", {})),
        now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def get_insar_scenes() -> List[Dict[str, Any]]:
    """Fetches all registered Sentinel-1 InSAR SLC scenes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insar_scenes ORDER BY sensing_start_utc ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_insar_pairs() -> List[Dict[str, Any]]:
    """Fetches all registered InSAR pairs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insar_pairs ORDER BY primary_time_utc DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_insar_latest_deformation() -> Optional[Dict[str, Any]]:
    """Fetches the latest multi-temporal deformation product."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insar_deformation_products ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def record_observation(source_key: str, product_identifier: str, observation_time_utc: str,
                       ingestion_time_utc: str, status: str, quality_status: str,
                       file_hash: str = "", metadata: dict = None) -> int:
    """Inserts a standardized observation record into the observations table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata) if metadata else None
    cursor.execute("""
    INSERT INTO observations (
        source_key, product_identifier, observation_time_utc, ingestion_time_utc,
        status, quality_status, file_hash, metadata_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source_key, product_identifier, observation_time_utc, ingestion_time_utc,
        status, quality_status, file_hash, meta_json, now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def get_latest_observation_by_source(source_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves the newest observation for a given source key."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM observations WHERE source_key = ? ORDER BY observation_time_utc DESC, id DESC LIMIT 1
    """, (source_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        if res.get("metadata_json"):
            try:
                res["metadata"] = json.loads(res["metadata_json"])
            except Exception:
                pass
        return res
    return None

def record_multimodal_features(record_dict: Dict[str, Any]) -> int:
    """Inserts a canonical multimodal feature record into live_multimodal_features."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO live_multimodal_features (
        hotspot_id, latitude, longitude, reference_time_utc,
        susceptibility_xgboost, susceptibility_rf_fallback,
        rainfall_anomaly, soil_moisture_anomaly, satellite_change_flag,
        cnn_probability, cnn_uncertainty, cnn_status,
        c15_probability, c15_entropy, c15_status,
        insar_deformation_indicator, insar_velocity_mm_yr, insar_coherence, insar_quality, insar_status,
        feature_payload_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record_dict.get("hotspot_id", "UNKNOWN"),
        record_dict.get("latitude", 0.0),
        record_dict.get("longitude", 0.0),
        record_dict.get("reference_time_utc", now_str),
        record_dict.get("susceptibility_xgboost", 0.5),
        record_dict.get("susceptibility_rf_fallback", 0.5),
        record_dict.get("rainfall_anomaly", 0.0),
        record_dict.get("soil_moisture_anomaly", 0.0),
        record_dict.get("satellite_change_flag", 0.0),
        record_dict.get("cnn_probability"),
        record_dict.get("cnn_uncertainty"),
        record_dict.get("cnn_status", "AWAITING_INFERENCE"),
        record_dict.get("c15_probability"),
        record_dict.get("c15_entropy"),
        record_dict.get("c15_status", "INSUFFICIENT_TEMPORAL_INPUT"),
        record_dict.get("insar_deformation_indicator"),
        record_dict.get("insar_velocity_mm_yr"),
        record_dict.get("insar_coherence"),
        record_dict.get("insar_quality"),
        record_dict.get("insar_status", "RESEARCH_ONLY"),
        json.dumps(record_dict),
        now_str
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id

def get_latest_multimodal_features(hotspot_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves newest multimodal feature records, optionally filtered by hotspot_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if hotspot_id:
        cursor.execute("""
        SELECT * FROM live_multimodal_features WHERE hotspot_id = ? ORDER BY reference_time_utc DESC, id DESC LIMIT 1
        """, (hotspot_id,))
        rows = cursor.fetchall()
    else:
        cursor.execute("""
        SELECT * FROM live_multimodal_features GROUP BY hotspot_id ORDER BY hotspot_id ASC
        """)
        rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("feature_payload_json"):
            try:
                d["payload"] = json.loads(d["feature_payload_json"])
            except Exception:
                pass
        results.append(d)
    return results

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with authentication, observation, and InSAR schemas.")


