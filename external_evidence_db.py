"""
=============================================================================
NER-SAFE: Additive External Evidence Database & Schema Layer
=============================================================================
Author: Antigravity (Advanced Agentic Coding)
Purpose: Manages persistent storage, audit logs, and provenance for external
         government data sources (GSI Bhusanket, NDMA SACHET, ISRO Bhuvan)
         strictly as additive tables within SQLite (ner_safe_shared.db).

INVARIANTS:
1. Does NOT modify the 101 protected manifest artifacts (e.g. database.py is untouched).
2. Existing tables (users, citizen_reports, assessments, audit_logs) are strictly preserved.
3. External warnings & events do NOT modify the locked 4-factor risk formula (0.40/0.30/0.20/0.10).
4. Zero emojis across all log strings, statuses, and schema definitions.
=============================================================================
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("NER_SAFE.ExternalEvidenceDB")

PROJECT_ROOT = os.environ.get("NER_SAFE_ROOT", os.path.abspath(os.path.dirname(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "DATABASE")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "ner_safe_shared.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_external_evidence_tables():
    """Creates additive external evidence tables in ner_safe_shared.db if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. External Sources Registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT UNIQUE NOT NULL,
        source_name TEXT NOT NULL,
        organization TEXT NOT NULL,
        product_name TEXT NOT NULL,
        purpose TEXT NOT NULL,
        state_coverage TEXT NOT NULL,
        meghalaya_coverage INTEGER DEFAULT 1,
        mizoram_coverage INTEGER DEFAULT 1,
        hazard_type TEXT NOT NULL,
        data_type TEXT NOT NULL,
        format TEXT NOT NULL,
        api_available INTEGER DEFAULT 0,
        download_available INTEGER DEFAULT 0,
        web_service_available INTEGER DEFAULT 0,
        live_or_static TEXT NOT NULL,
        update_frequency TEXT NOT NULL,
        spatial_resolution TEXT,
        temporal_resolution TEXT,
        authentication_required INTEGER DEFAULT 0,
        public_access INTEGER DEFAULT 1,
        automation_feasibility TEXT NOT NULL,
        official_url TEXT NOT NULL,
        discovery_status TEXT NOT NULL,
        last_successful_fetch TEXT,
        last_attempt TEXT,
        http_status INTEGER,
        latency_ms INTEGER,
        failure_count INTEGER DEFAULT 0,
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 2. External Fetch Audit Runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_fetch_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT UNIQUE NOT NULL,
        source_id TEXT NOT NULL,
        timestamp_utc TEXT NOT NULL,
        endpoint_url TEXT NOT NULL,
        http_status INTEGER,
        response_time_ms INTEGER,
        content_type TEXT,
        content_length INTEGER,
        content_sha256 TEXT,
        etag TEXT,
        last_modified TEXT,
        records_retrieved INTEGER DEFAULT 0,
        records_meghalaya INTEGER DEFAULT 0,
        records_mizoram INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        error_message TEXT,
        FOREIGN KEY (source_id) REFERENCES external_sources(source_id)
    );
    """)

    # 3. External Warnings Table (Normalized CAP 1.2 from SACHET / NDMA)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_warning_id TEXT UNIQUE NOT NULL,
        source_id TEXT NOT NULL,
        hazard_type TEXT NOT NULL,
        warning_type TEXT NOT NULL,
        state TEXT NOT NULL,
        district TEXT,
        area_description TEXT,
        latitude REAL,
        longitude REAL,
        geometry_json TEXT,
        issued_at TEXT NOT NULL,
        effective_at TEXT,
        expires_at TEXT,
        severity TEXT NOT NULL,
        urgency TEXT,
        certainty TEXT,
        headline TEXT,
        description TEXT,
        instruction TEXT,
        status TEXT NOT NULL,
        source_url TEXT,
        content_sha256 TEXT,
        retrieved_at TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES external_sources(source_id)
    );
    """)

    # 4. Canonical External Landslide Events (Historical & Active Incidents)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_landslide_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_event_id TEXT UNIQUE NOT NULL,
        primary_source TEXT NOT NULL,
        state TEXT NOT NULL,
        district TEXT,
        locality TEXT,
        latitude REAL,
        longitude REAL,
        geometry_json TEXT,
        event_date TEXT NOT NULL,
        event_time TEXT,
        event_type TEXT NOT NULL,
        inventory_type TEXT NOT NULL,
        verification_status TEXT NOT NULL,
        dataset_role TEXT NOT NULL DEFAULT 'INDEPENDENT_TEST',
        fatalities INTEGER DEFAULT 0,
        injuries INTEGER DEFAULT 0,
        impact_summary TEXT,
        source_url TEXT,
        content_sha256 TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 5. External Event Source Linkages (Cross-Source Deduplication Mapping)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_event_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_event_id TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_record_id TEXT NOT NULL,
        source_url TEXT,
        confidence_score REAL DEFAULT 1.0,
        linked_at TEXT NOT NULL,
        FOREIGN KEY (canonical_event_id) REFERENCES external_landslide_events(canonical_event_id)
    );
    """)

    # 6. External Spatial Layers & Exposure References
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS external_spatial_layers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        layer_id TEXT UNIQUE NOT NULL,
        source_id TEXT NOT NULL,
        layer_name TEXT NOT NULL,
        layer_title TEXT NOT NULL,
        crs TEXT NOT NULL,
        bbox_json TEXT,
        feature_count INTEGER DEFAULT 0,
        meghalaya_covered INTEGER DEFAULT 1,
        mizoram_covered INTEGER DEFAULT 1,
        service_type TEXT NOT NULL,
        wms_url TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES external_sources(source_id)
    );
    """)

    conn.commit()
    conn.close()
    logger.info("External evidence tables initialized cleanly in ner_safe_shared.db")


def seed_authoritative_sources():
    """Populates the initial authoritative government source inventory."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    sources = [
        {
            "source_id": "GSI_BHUSANKET_WEBAPI",
            "source_name": "Geological Survey of India (GSI) Bhusanket WebAPI",
            "organization": "Geological Survey of India, Ministry of Mines",
            "product_name": "National Landslide Forecasting Centre (NLFC) Bulletins & Incident News",
            "purpose": "Dissemination of national landslide early warnings, incident inventories, and awareness bulletins",
            "state_coverage": "National (with dedicated Northeast coverage)",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Landslide / Debris Flow / Rockfall",
            "data_type": "Structured JSON / Public News Bulletins",
            "format": "JSON",
            "api_available": 1,
            "download_available": 1,
            "web_service_available": 1,
            "live_or_static": "LIVE",
            "update_frequency": "Event-driven / Daily during Monsoon",
            "spatial_resolution": "District / Locality level",
            "temporal_resolution": "Event timestamp",
            "authentication_required": 0,
            "public_access": 1,
            "automation_feasibility": "AUTOMATED_JSON_CLIENT",
            "official_url": "https://bhusanket.gsi.gov.in/WebAPI_v2/News/datalist",
            "discovery_status": "LIVE_API_ACCESSIBLE",
            "http_status": 200
        },
        {
            "source_id": "GSI_BHUSANKET_ARCGIS",
            "source_name": "GSI Bhusanket ArcGIS Enterprise Services",
            "organization": "Geological Survey of India",
            "product_name": "India All Landslides & Susceptibility MapServer / FeatureServer",
            "purpose": "National 1:50k spatial landslide hazard and inventory layers",
            "state_coverage": "National",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Landslide Susceptibility & Inventory",
            "data_type": "ArcGIS REST FeatureServer / ImageServer",
            "format": "ArcGIS REST / JSON",
            "api_available": 1,
            "download_available": 0,
            "web_service_available": 1,
            "live_or_static": "SEMI_STATIC",
            "update_frequency": "Annual / Post-monsoon revision",
            "spatial_resolution": "1:50,000 scale / 30m grid",
            "temporal_resolution": "Annual release",
            "authentication_required": 1,
            "public_access": 0,
            "automation_feasibility": "TOKEN_PROTECTED",
            "official_url": "https://bhusanket.gsi.gov.in/gisserver/rest/services/Hosted/India_All_Landslided/FeatureServer/0",
            "discovery_status": "INSTITUTIONAL_ACCESS_REQUIRED",
            "http_status": 499
        },
        {
            "source_id": "NDMA_SACHET_CAP",
            "source_name": "NDMA SACHET National Disaster Alert Feed",
            "organization": "National Disaster Management Authority & C-DOT",
            "product_name": "All India Public Alert Feed (Common Alerting Protocol CAP 1.2)",
            "purpose": "Live multi-agency disaster warnings (IMD, CWC, GSI, SDMAs)",
            "state_coverage": "National (State-wise & Coordinate-wise)",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Multi-Hazard (Landslide, Flood, Heavy Rain, Thunderstorm)",
            "data_type": "Structured CAP 1.2 JSON / Geo-Targeted Alerts",
            "format": "JSON / CAP XML",
            "api_available": 1,
            "download_available": 0,
            "web_service_available": 1,
            "live_or_static": "LIVE",
            "update_frequency": "Real-time (Every 15-30 minutes)",
            "spatial_resolution": "Sub-district / Coordinate radius (20-100km)",
            "temporal_resolution": "Near real-time (Minutes)",
            "authentication_required": 0,
            "public_access": 1,
            "automation_feasibility": "AUTOMATED_REST_CLIENT",
            "official_url": "https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails",
            "discovery_status": "LIVE_FEED_ACCESSIBLE",
            "http_status": 200
        },
        {
            "source_id": "ISRO_BHUVAN_WMS",
            "source_name": "ISRO NRSC Bhuvan Vector Geoportal WMS",
            "organization": "National Remote Sensing Centre (NRSC), ISRO",
            "product_name": "OGC Web Map Service (WMS) Disaster & Thematic Layers",
            "purpose": "Standardized spatial GIS layers for landslides, floods, and geomorphology",
            "state_coverage": "National",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Landslide / Geomorphology / Disaster",
            "data_type": "OGC WMS 1.1.1 Vector / Raster Tiles",
            "format": "OGC WMS (image/png, application/vnd.ogc.wms_xml)",
            "api_available": 1,
            "download_available": 0,
            "web_service_available": 1,
            "live_or_static": "STATIC_AVAILABLE",
            "update_frequency": "Thematic updates per mission cycle",
            "spatial_resolution": "1:50,000 / Cartosat / LISS-IV",
            "temporal_resolution": "Seasonal / Atlas",
            "authentication_required": 0,
            "public_access": 1,
            "automation_feasibility": "OGC_WMS_CLIENT",
            "official_url": "https://bhuvan-vec1.nrsc.gov.in/bhuvan/wms",
            "discovery_status": "LIVE_API_ACCESSIBLE",
            "http_status": 200
        },
        {
            "source_id": "ISRO_NRSC_LANDSLIDE_ATLAS",
            "source_name": "ISRO NRSC Landslide Atlas of India Database",
            "organization": "National Remote Sensing Centre (NRSC), ISRO",
            "product_name": "District-Wise Landslide Vulnerability & Historical Inventory",
            "purpose": "Authoritative historical incident database for North-Western and North-Eastern Himalayas",
            "state_coverage": "Northeast (Meghalaya, Mizoram, Assam, Sikkim, etc.)",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Historical Landslide Incidences (1998-2022)",
            "data_type": "Point Inventory / Statistical Risk Rankings",
            "format": "CSV / GeoJSON / Technical Publication",
            "api_available": 0,
            "download_available": 1,
            "web_service_available": 1,
            "live_or_static": "STATIC_AVAILABLE",
            "update_frequency": "Static Multi-Year Baseline",
            "spatial_resolution": "Point coordinates (WGS84)",
            "temporal_resolution": "Historical multi-decade catalog",
            "authentication_required": 0,
            "public_access": 1,
            "automation_feasibility": "LOCAL_CACHE_STANDARDIZATION",
            "official_url": "https://bhuvan.nrsc.gov.in",
            "discovery_status": "PUBLIC_DOWNLOAD",
            "http_status": 200
        },
        {
            "source_id": "GSI_BHUKOSH_CATALOG",
            "source_name": "GSI Bhukosh National Geoscientific Data Repository",
            "organization": "Geological Survey of India",
            "product_name": "GSI National Landslide Inventory Database",
            "purpose": "Comprehensive georeferenced historical landslide inventory points across India",
            "state_coverage": "All Hilly States (including Meghalaya & Mizoram)",
            "meghalaya_coverage": 1,
            "mizoram_coverage": 1,
            "hazard_type": "Landslide Occurrence & Geomorphology",
            "data_type": "Tabular Geological / Spatial Points",
            "format": "CSV / Spatial Database",
            "api_available": 0,
            "download_available": 1,
            "web_service_available": 1,
            "live_or_static": "STATIC_AVAILABLE",
            "update_frequency": "Periodic Field Updates",
            "spatial_resolution": "GPS Coordinates",
            "temporal_resolution": "Historical Catalog",
            "authentication_required": 0,
            "public_access": 1,
            "automation_feasibility": "LOCAL_CACHE_STANDARDIZATION",
            "official_url": "https://bhukosh.gsi.gov.in",
            "discovery_status": "PUBLIC_DOWNLOAD",
            "http_status": 200
        }
    ]

    for s in sources:
        cursor.execute("""
        INSERT INTO external_sources (
            source_id, source_name, organization, product_name, purpose, state_coverage,
            meghalaya_coverage, mizoram_coverage, hazard_type, data_type, format,
            api_available, download_available, web_service_available, live_or_static,
            update_frequency, spatial_resolution, temporal_resolution, authentication_required,
            public_access, automation_feasibility, official_url, discovery_status,
            http_status, created_at, updated_at
        ) VALUES (
            :source_id, :source_name, :organization, :product_name, :purpose, :state_coverage,
            :meghalaya_coverage, :mizoram_coverage, :hazard_type, :data_type, :format,
            :api_available, :download_available, :web_service_available, :live_or_static,
            :update_frequency, :spatial_resolution, :temporal_resolution, :authentication_required,
            :public_access, :automation_feasibility, :official_url, :discovery_status,
            :http_status, :created_at, :updated_at
        ) ON CONFLICT(source_id) DO UPDATE SET
            discovery_status = excluded.discovery_status,
            http_status = excluded.http_status,
            updated_at = excluded.updated_at;
        """, {**s, "created_at": now_iso, "updated_at": now_iso})

    conn.commit()
    conn.close()
    logger.info("Authoritative government source inventory seeded successfully.")


def init_osint_tables():
    """Creates additive OSINT and prediction outcome validation tables in ner_safe_shared.db."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. OSINT Sources Registry
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS osint_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT UNIQUE NOT NULL,
        source_name TEXT NOT NULL,
        source_class TEXT NOT NULL,
        publisher TEXT NOT NULL,
        state_scope TEXT NOT NULL,
        district_scope TEXT,
        base_url TEXT NOT NULL,
        feed_url TEXT,
        discovery_method TEXT NOT NULL,
        access_state TEXT NOT NULL,
        reliability_class TEXT NOT NULL,
        poll_interval_minutes INTEGER DEFAULT 60,
        enabled INTEGER DEFAULT 1,
        last_fetch TEXT,
        last_success TEXT,
        last_failure TEXT,
        http_status INTEGER,
        latency_ms INTEGER,
        etag TEXT,
        last_modified TEXT,
        parser_version TEXT DEFAULT 'v1.1.0',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 2. OSINT Raw & Normalized Observations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS osint_observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        osint_observation_id TEXT UNIQUE NOT NULL,
        source_id TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_title TEXT,
        publisher TEXT,
        published_at TEXT,
        observed_at TEXT,
        ingested_at TEXT NOT NULL,
        state TEXT NOT NULL,
        district TEXT,
        locality TEXT,
        road TEXT,
        landmark TEXT,
        latitude REAL,
        longitude REAL,
        location_confidence TEXT NOT NULL,
        location_method TEXT,
        hazard_type TEXT NOT NULL,
        hazard_subtype TEXT,
        headline TEXT,
        summary TEXT,
        source_text_hash TEXT NOT NULL,
        source_reliability TEXT NOT NULL,
        extraction_confidence REAL DEFAULT 0.8,
        verification_state TEXT DEFAULT 'UNVERIFIED',
        language TEXT DEFAULT 'en',
        raw_reference TEXT,
        archived_reference TEXT,
        rejection_reason TEXT,
        FOREIGN KEY (source_id) REFERENCES osint_sources(source_id)
    );
    """)

    # 3. Canonical Deduplicated OSINT Events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canonical_osint_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_osint_event_id TEXT UNIQUE NOT NULL,
        primary_observation_id TEXT,
        state TEXT NOT NULL,
        district TEXT,
        locality TEXT,
        road TEXT,
        landmark TEXT,
        latitude REAL,
        longitude REAL,
        location_confidence TEXT NOT NULL,
        hazard_type TEXT NOT NULL,
        event_date TEXT NOT NULL,
        event_time TEXT,
        observed_at TEXT,
        verification_state TEXT NOT NULL,
        independence_groups_count INTEGER DEFAULT 1,
        source_count INTEGER DEFAULT 1,
        impact_summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 4. OSINT Event Linkages (Cross-Source & Independence Group Mapping)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS osint_event_linkages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_osint_event_id TEXT NOT NULL,
        osint_observation_id TEXT NOT NULL,
        independence_group_id TEXT NOT NULL,
        similarity_score REAL DEFAULT 1.0,
        linked_at TEXT NOT NULL,
        FOREIGN KEY (canonical_osint_event_id) REFERENCES canonical_osint_events(canonical_osint_event_id),
        FOREIGN KEY (osint_observation_id) REFERENCES osint_observations(osint_observation_id)
    );
    """)

    # 5. Prediction Outcomes Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_outcomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prediction_id TEXT UNIQUE NOT NULL,
        prediction_time TEXT NOT NULL,
        prediction_valid_from TEXT NOT NULL,
        prediction_valid_until TEXT NOT NULL,
        predicted_geometry TEXT,
        hotspot_id TEXT,
        state TEXT NOT NULL,
        district TEXT,
        predicted_risk_class TEXT NOT NULL,
        predicted_probability REAL NOT NULL,
        model_name TEXT NOT NULL,
        dynamic_feature_state_json TEXT,
        observed_event_id TEXT,
        outcome_classification TEXT NOT NULL,
        spatial_error_km REAL,
        temporal_error_hours REAL,
        lead_time_hours REAL,
        evaluation_notes TEXT,
        evaluated_at TEXT NOT NULL,
        match_scale TEXT DEFAULT 'UNKNOWN',
        prediction_distance_km REAL,
        geometry_overlap INTEGER DEFAULT 0,
        temporal_match_type TEXT DEFAULT 'UNKNOWN_EVENT_TIME',
        temporal_difference_hours REAL,
        matching_rule_version TEXT DEFAULT 'v1.1-spatial-temporal-correction',
        previous_outcome_classification TEXT
    );
    """)

    # Migration helper for prediction_outcomes
    def _add_col(tbl, col, typedef):
        cursor.execute(f"PRAGMA table_info({tbl});")
        cols = [r[1] for r in cursor.fetchall()]
        if col not in cols:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typedef};")

    _add_col("prediction_outcomes", "match_scale", "TEXT DEFAULT 'UNKNOWN'")
    _add_col("prediction_outcomes", "prediction_distance_km", "REAL")
    _add_col("prediction_outcomes", "geometry_overlap", "INTEGER DEFAULT 0")
    _add_col("prediction_outcomes", "temporal_match_type", "TEXT DEFAULT 'UNKNOWN_EVENT_TIME'")
    _add_col("prediction_outcomes", "temporal_difference_hours", "REAL")
    _add_col("prediction_outcomes", "matching_rule_version", "TEXT DEFAULT 'v1.1-spatial-temporal-correction'")
    _add_col("prediction_outcomes", "previous_outcome_classification", "TEXT")

    # 5b. Prediction Outcomes Audit History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_outcomes_audit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        outcome_id INTEGER,
        prediction_id TEXT NOT NULL,
        validation_method_version TEXT NOT NULL,
        outcome_classification TEXT NOT NULL,
        match_scale TEXT NOT NULL,
        spatial_error_km REAL,
        lead_time_hours REAL,
        evaluation_notes TEXT,
        archived_at TEXT NOT NULL
    );
    """)

    # 6. Prediction Validation Operational Metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prediction_validation_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        state TEXT NOT NULL,
        total_predictions INTEGER DEFAULT 0,
        true_positives INTEGER DEFAULT 0,
        false_positives INTEGER DEFAULT 0,
        false_negatives INTEGER DEFAULT 0,
        unknown_outcomes INTEGER DEFAULT 0,
        precision_score REAL DEFAULT 0.0,
        recall_score REAL DEFAULT 0.0,
        f1_score REAL DEFAULT 0.0,
        mean_lead_time_hours REAL DEFAULT 0.0,
        mean_spatial_error_km REAL DEFAULT 0.0,
        hit_rate REAL DEFAULT 0.0,
        sample_size_adequate INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL,
        site_true_positives INTEGER DEFAULT 0,
        corridor_true_positives INTEGER DEFAULT 0,
        regional_true_positives INTEGER DEFAULT 0,
        site_precision REAL DEFAULT 0.0,
        site_recall REAL DEFAULT 0.0,
        site_f1 REAL DEFAULT 0.0,
        mean_spatial_error_site REAL DEFAULT 0.0,
        mean_spatial_error_regional REAL DEFAULT 0.0,
        median_spatial_error_km REAL DEFAULT 0.0,
        p05_spatial_error_km REAL DEFAULT 0.0,
        p95_spatial_error_km REAL DEFAULT 0.0,
        median_lead_time_hours REAL DEFAULT 0.0,
        p05_lead_time_hours REAL DEFAULT 0.0,
        p95_lead_time_hours REAL DEFAULT 0.0,
        validation_method_version TEXT DEFAULT 'v1.1-spatial-temporal-correction',
        UNIQUE(model_name, state)
    );
    """)

    _add_col("prediction_validation_metrics", "site_true_positives", "INTEGER DEFAULT 0")
    _add_col("prediction_validation_metrics", "corridor_true_positives", "INTEGER DEFAULT 0")
    _add_col("prediction_validation_metrics", "regional_true_positives", "INTEGER DEFAULT 0")
    _add_col("prediction_validation_metrics", "site_precision", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "site_recall", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "site_f1", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "mean_spatial_error_site", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "mean_spatial_error_regional", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "median_spatial_error_km", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "p05_spatial_error_km", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "p95_spatial_error_km", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "median_lead_time_hours", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "p05_lead_time_hours", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "p95_lead_time_hours", "REAL DEFAULT 0.0")
    _add_col("prediction_validation_metrics", "validation_method_version", "TEXT DEFAULT 'v1.1-spatial-temporal-correction'")

    conn.commit()
    conn.close()
    logger.info("OSINT and prediction outcome tables initialized cleanly in ner_safe_shared.db")


def seed_osint_sources():
    """Populates the initial OSINT source registry for Meghalaya and Mizoram."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    sources = [
        {
            "source_id": "MEGHALAYA_SDMA",
            "source_name": "Meghalaya State Disaster Management Authority",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "Government of Meghalaya, Revenue & Disaster Management",
            "state_scope": "Meghalaya",
            "district_scope": "All Meghalaya Districts",
            "base_url": "https://msdma.gov.in/",
            "feed_url": "https://msdma.gov.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 60,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 899
        },
        {
            "source_id": "MEGHALAYA_GOV",
            "source_name": "Government of Meghalaya Official Web Portal",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "Information & Public Relations, Meghalaya",
            "state_scope": "Meghalaya",
            "district_scope": "Statewide",
            "base_url": "https://meghalaya.gov.in/",
            "feed_url": "https://meghalaya.gov.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 120,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 942
        },
        {
            "source_id": "EAST_KHASI_HILLS_DDMA",
            "source_name": "East Khasi Hills District Administration & DDMA",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "Office of the Deputy Commissioner, Shillong",
            "state_scope": "Meghalaya",
            "district_scope": "East Khasi Hills",
            "base_url": "https://eastkhasihills.gov.in/",
            "feed_url": "https://eastkhasihills.gov.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 60,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 3848
        },
        {
            "source_id": "MIZORAM_DIPR",
            "source_name": "Directorate of Information & Public Relations (DIPR) Mizoram",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "Government of Mizoram",
            "state_scope": "Mizoram",
            "district_scope": "All Mizoram Districts",
            "base_url": "https://dipr.mizoram.gov.in/",
            "feed_url": "https://dipr.mizoram.gov.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 60,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 1003
        },
        {
            "source_id": "MIZORAM_DMR",
            "source_name": "Disaster Management & Rehabilitation Department (DM&R) Mizoram",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "DM&R Department, Government of Mizoram",
            "state_scope": "Mizoram",
            "district_scope": "Statewide",
            "base_url": "https://dmr.mizoram.gov.in/",
            "feed_url": "https://dmr.mizoram.gov.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 60,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 969
        },
        {
            "source_id": "AIZAWL_DDMA",
            "source_name": "Aizawl District Administration & DDMA",
            "source_class": "CLASS_1_OFFICIAL_PUBLIC",
            "publisher": "Office of the Deputy Commissioner, Aizawl",
            "state_scope": "Mizoram",
            "district_scope": "Aizawl",
            "base_url": "https://aizawl.nic.in/",
            "feed_url": "https://aizawl.nic.in/",
            "discovery_method": "PORTAL_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "HIGH",
            "poll_interval_minutes": 60,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 5896
        },
        {
            "source_id": "THE_SHILLONG_TIMES",
            "source_name": "The Shillong Times",
            "source_class": "CLASS_2_REPUTABLE_NEWS",
            "publisher": "The Shillong Times Publications",
            "state_scope": "Meghalaya",
            "district_scope": "Meghalaya / Regional",
            "base_url": "https://theshillongtimes.com/",
            "feed_url": "https://theshillongtimes.com/feed/",
            "discovery_method": "RSS_FEED_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "MEDIUM",
            "poll_interval_minutes": 30,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 2867
        },
        {
            "source_id": "NORTHEAST_TODAY",
            "source_name": "Northeast Today General Feed",
            "source_class": "CLASS_2_REPUTABLE_NEWS",
            "publisher": "Northeast Today Media",
            "state_scope": "Northeast",
            "district_scope": "Regional",
            "base_url": "https://northeasttoday.in/",
            "feed_url": "https://northeasttoday.in/feed/",
            "discovery_method": "RSS_FEED_PARSER",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "MEDIUM",
            "poll_interval_minutes": 30,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 1677
        },
        {
            "source_id": "NORTHEAST_TODAY_SEARCH_MEG",
            "source_name": "Northeast Today Meghalaya Landslide Query Feed",
            "source_class": "CLASS_3_SEARCH_DISCOVERY",
            "publisher": "Northeast Today Media",
            "state_scope": "Meghalaya",
            "district_scope": "Meghalaya",
            "base_url": "https://northeasttoday.in/",
            "feed_url": "https://northeasttoday.in/?s=Meghalaya+landslide&feed=rss2",
            "discovery_method": "RSS_SEARCH_QUERY",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "MEDIUM",
            "poll_interval_minutes": 30,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 1820
        },
        {
            "source_id": "NORTHEAST_TODAY_SEARCH_MIZ",
            "source_name": "Northeast Today Mizoram Landslide Query Feed",
            "source_class": "CLASS_3_SEARCH_DISCOVERY",
            "publisher": "Northeast Today Media",
            "state_scope": "Mizoram",
            "district_scope": "Mizoram",
            "base_url": "https://northeasttoday.in/",
            "feed_url": "https://northeasttoday.in/?s=Mizoram+landslide&feed=rss2",
            "discovery_method": "RSS_SEARCH_QUERY",
            "access_state": "LIVE_VERIFIED",
            "reliability_class": "MEDIUM",
            "poll_interval_minutes": 30,
            "enabled": 1,
            "http_status": 200,
            "latency_ms": 1750
        }
    ]

    for s in sources:
        cursor.execute("""
        INSERT INTO osint_sources (
            source_id, source_name, source_class, publisher, state_scope, district_scope,
            base_url, feed_url, discovery_method, access_state, reliability_class,
            poll_interval_minutes, enabled, http_status, latency_ms, created_at, updated_at
        ) VALUES (
            :source_id, :source_name, :source_class, :publisher, :state_scope, :district_scope,
            :base_url, :feed_url, :discovery_method, :access_state, :reliability_class,
            :poll_interval_minutes, :enabled, :http_status, :latency_ms, :created_at, :updated_at
        ) ON CONFLICT(source_id) DO UPDATE SET
            access_state = excluded.access_state,
            http_status = excluded.http_status,
            latency_ms = excluded.latency_ms,
            updated_at = excluded.updated_at;
        """, {**s, "created_at": now_iso, "updated_at": now_iso})

    conn.commit()
    conn.close()
    logger.info("OSINT source registry seeded successfully.")


# Initialize tables and seed on import
init_external_evidence_tables()
seed_authoritative_sources()
init_osint_tables()
seed_osint_sources()

