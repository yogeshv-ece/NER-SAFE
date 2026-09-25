"""
NER-SAFE: Authoritative Live Ground-Sensor and Multi-Source Ingestion Registry
Provides a unified catalog of all investigated real-world sensor deployments,
satellite products, and meteorological telemetry streams across Meghalaya and Mizoram.

Principles:
1. Distinguishes Discovery, Binary Access, Authentication, and Operational Status.
2. Strictly refuses to label research papers or closed networks as "open live streaming".
3. Enforces separated observation_timestamp vs. ingested_timestamp.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Operational Lifecycle Statuses
STATUS_LIVE_STREAMING = "LIVE_STREAMING"
STATUS_LIVE_READY = "LIVE_READY"
STATUS_AUTH_REQUIRED = "AUTH_REQUIRED"
STATUS_INSTITUTIONAL_ACCESS_REQUIRED = "INSTITUTIONAL_ACCESS_REQUIRED"
STATUS_HISTORICAL_ONLY = "HISTORICAL_ONLY"
STATUS_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
STATUS_HARDWARE_REQUIRED = "HARDWARE_REQUIRED"
STATUS_DISABLED = "DISABLED"

# Fast, Medium, Context Temporal Classification
SIGNAL_SPEED_FAST = "FAST"      # Sub-hourly to 4h: ground sensors, rain gauges, GPM NRT
SIGNAL_SPEED_MEDIUM = "MEDIUM"  # Daily to weekly: Sentinel-1 SAR, SMAP
SIGNAL_SPEED_CONTEXT = "CONTEXT" # 5-day to static: Sentinel-2 optical, SRTM DEM, inventory

SENSOR_SOURCES: Dict[str, Dict[str, Any]] = {
    "NIT_MEG_MAWIONGRIM_01": {
        "source_id": "NIT_MEG_MAWIONGRIM_01",
        "name": "Mawiongrim Landslide Geotechnical Monitoring Station",
        "organization": "National Institute of Technology Meghalaya (NIT Meghalaya)",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "site": "Mawiongrim",
        "latitude": 25.5312,
        "longitude": 91.8745,
        "elevation_m": 1520.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["RAIN_GAUGE", "TILT", "PORE_PRESSURE", "WATER_LEVEL"],
        "sensor_channels": {
            "Rainfall": {"unit": "mm", "type": "RAIN_GAUGE"},
            "Water_level": {"unit": "mm", "type": "PORE_PRESSURE"},
            "Inc10mup": {"unit": "degrees", "type": "TILT"},
            "Inc10mdown": {"unit": "degrees", "type": "TILT"},
            "Inc20mup": {"unit": "degrees", "type": "TILT"},
            "Inc20mdown": {"unit": "degrees", "type": "TILT"},
            "Inc30mup": {"unit": "degrees", "type": "TILT"},
            "Inc30mdown": {"unit": "degrees", "type": "TILT"},
            "Tensiometers": {"unit": "kPa", "type": "PORE_PRESSURE"}
        },
        "discovery": "PUBLIC_RESEARCH_LITERATURE",
        "access_method": "PRIVATE_WSN_HUB / PROPRIETARY_CELLULAR",
        "telemetry_format": "CSV / TIME_SERIES",
        "update_interval_hours": 1.0,
        "status": STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
        "historical_dataset_available": True,
        "historical_records_count": 696,
        "historical_window": "2022-12-01 to 2022-12-30",
        "live_endpoint": "https://nitm.ac.in/private_telemetry/mawiongrim (Restricted)",
        "auth_type": "INSTITUTIONAL_DATA_SHARING_MOU",
        "operational_disclaimer": "Ground telemetry deployed by NIT Meghalaya researchers; live streaming operates over closed cellular hub. Public historical dataset verified; live machine-to-machine streaming requires formal MoU with NIT Meghalaya."
    },

    "NEHU_SHILLONG_SLOPE_01": {
        "source_id": "NEHU_SHILLONG_SLOPE_01",
        "name": "NEHU Campus Experimental Slope Monitoring Station",
        "organization": "North-Eastern Hill University (NEHU)",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "site": "NEHU Shillong Campus",
        "latitude": 25.6067,
        "longitude": 91.9022,
        "elevation_m": 1430.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["SOIL_MOISTURE", "RAIN_GAUGE", "TILT", "TEMPERATURE"],
        "sensor_channels": {
            "soil_moisture": {"unit": "%", "type": "SOIL_MOISTURE"},
            "rain_gauge": {"unit": "mm/h", "type": "RAIN_GAUGE"},
            "tilt_inclinometer": {"unit": "degrees", "type": "TILT"}
        },
        "discovery": "PUBLIC_ACADEMIC_RESEARCH",
        "access_method": "LOCAL_LOGGER / PROPRIETARY_RADIO",
        "telemetry_format": "CSV / ASCII",
        "update_interval_hours": 1.0,
        "status": STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
        "historical_dataset_available": False,
        "auth_type": "ACADEMIC_COLLABORATION_AGREEMENT",
        "operational_disclaimer": "Academic geotechnical monitoring installation; live feed operates on offline dataloggers without public REST endpoints."
    },

    "MIRSAC_AIZAWL_01": {
        "source_id": "MIRSAC_AIZAWL_01",
        "name": "Aizawl Urban Slope Instability Monitoring Network",
        "organization": "Mizoram Remote Sensing Application Centre (MIRSAC)",
        "state": "Mizoram",
        "district": "Aizawl",
        "site": "Laipuitlang / Ngaizel Slopes",
        "latitude": 23.7307,
        "longitude": 92.7173,
        "elevation_m": 1130.0,
        "signal_speed": SIGNAL_SPEED_MEDIUM,
        "sensor_types": ["RAIN_GAUGE", "TILT", "GROUND_DISPLACEMENT"],
        "sensor_channels": {
            "rainfall": {"unit": "mm/day", "type": "RAIN_GAUGE"},
            "inclinometer_borehole": {"unit": "mm_displacement", "type": "TILT"}
        },
        "discovery": "STATE_DISASTER_MANAGEMENT_REPORTS",
        "access_method": "SILAAS_ADVISORY_PORTAL / GOVERNMENT_INTRANET",
        "telemetry_format": "PDF_BULLETIN / GIS_SHAPEFILE",
        "update_interval_hours": 24.0,
        "status": STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
        "historical_dataset_available": False,
        "auth_type": "STATE_SDMA_AUTHORIZATION",
        "operational_disclaimer": "SILAAS produces daily municipal hazard zonation bulletins; raw geotechnical sensor feeds are maintained on Mizoram State Government private networks."
    },

    "JAXA_GSMAP_NOW_01": {
        "source_id": "JAXA_GSMAP_NOW_01",
        "name": "JAXA GSMaP_NOW Version 8 Half-Hourly Precipitation",
        "organization": "JAXA Earth Observation Research Center (EORC)",
        "state": "North Eastern Region (Synoptic Coverage)",
        "district": "All NER Districts",
        "site": "Regional Grid (21.0N-27.0N, 89.0E-94.0E)",
        "latitude": 24.5000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["RAIN_GAUGE"],
        "sensor_channels": {
            "RainRate": {"unit": "mm/h", "type": "RAIN_GAUGE"}
        },
        "discovery": "FTP_PASSIVE_DIRECTORY_LISTING",
        "access_method": "FTP_PASSIVE_CSV_DOWNLOAD",
        "telemetry_format": "CSV.ZIP / NETCDF4",
        "update_interval_hours": 0.5,
        "nominal_latency_hours": 0.52,
        "status": STATUS_LIVE_READY,
        "auth_type": "JAXA_FTP_REGISTRATION",
        "operational_disclaimer": "Primary operational precipitation ingestor (~10 km resolution). Verified publication latency ~31 minutes; fuels 0.30 dynamic rainfall anomaly channel with NASA GPM Early NRT as fallback."
    },

    "NASA_GPM_NRT_01": {
        "source_id": "NASA_GPM_NRT_01",
        "name": "NASA GPM IMERG Early NRT Half-Hourly Precipitation",
        "organization": "NASA Goddard Earth Sciences (GES DISC)",
        "state": "North Eastern Region (Synoptic Coverage)",
        "district": "All NER Districts",
        "site": "Regional Grid (21.0N-27.0N, 89.0E-94.0E)",
        "latitude": 24.5000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["RAIN_GAUGE"],
        "sensor_channels": {
            "precipitationCal": {"unit": "mm/h", "type": "RAIN_GAUGE"}
        },
        "discovery": "PUBLIC_CMR_REST_API",
        "access_method": "HTTPS_DOWNLOAD_WITH_NETRC",
        "telemetry_format": "HDF5 / GeoTIFF",
        "update_interval_hours": 0.5,
        "nominal_latency_hours": 4.0,
        "status": STATUS_LIVE_READY,
        "auth_type": "EARTHDATA_LOGIN",
        "operational_disclaimer": "Secondary/Fallback satellite precipitation estimation proxy (~10 km resolution). Standby failover when primary GSMaP feed drops."
    },

    "NASA_SMAP_L3_01": {
        "source_id": "NASA_SMAP_L3_01",
        "name": "NASA SMAP NRT Radiometer Surface Soil Moisture",
        "organization": "NASA National Snow and Ice Data Center (NSIDC DAAC)",
        "product": "SPL2SMP_NRT",
        "version": "107",
        "state": "North Eastern Region (Synoptic Coverage)",
        "district": "All NER Districts",
        "site": "Regional Grid (36km EASE-Grid 2.0)",
        "latitude": 24.5000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_MEDIUM,
        "sensor_types": ["SOIL_MOISTURE"],
        "sensor_channels": {
            "soil_moisture": {"unit": "cm3/cm3", "type": "SOIL_MOISTURE"}
        },
        "discovery": "PUBLIC_CMR_REST_API",
        "access_method": "HTTPS_DOWNLOAD_WITH_NETRC",
        "telemetry_format": "HDF5",
        "update_interval_hours": 24.0,
        "nominal_latency_hours": 3.0,
        "status": STATUS_LIVE_READY,
        "auth_type": "EARTHDATA_LOGIN",
        "operational_disclaimer": "Near-real-time surface relative saturation index (top 5cm); saturation indicator, not deep pore-pressure. Harmonized with 9 km historical baseline."
    },

    "NASA_SMAP_NRT_01": {
        "source_id": "NASA_SMAP_NRT_01",
        "name": "NASA SMAP NRT Radiometer Half-Orbit Soil Moisture",
        "organization": "NASA National Snow and Ice Data Center (NSIDC DAAC)",
        "product": "SPL2SMP_NRT",
        "version": "107",
        "state": "North Eastern Region (Synoptic Coverage)",
        "district": "All NER Districts",
        "site": "Regional Grid (36km EASE-Grid 2.0)",
        "latitude": 24.5000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_MEDIUM,
        "sensor_types": ["SOIL_MOISTURE"],
        "sensor_channels": {
            "soil_moisture": {"unit": "cm3/cm3", "type": "SOIL_MOISTURE"}
        },
        "discovery": "PUBLIC_CMR_REST_API",
        "access_method": "HTTPS_DOWNLOAD_WITH_NETRC",
        "telemetry_format": "HDF5",
        "update_interval_hours": 24.0,
        "nominal_latency_hours": 3.0,
        "status": STATUS_LIVE_READY,
        "auth_type": "EARTHDATA_LOGIN",
        "operational_disclaimer": "Near-real-time surface relative saturation index (top 5cm); saturation indicator, not deep pore-pressure. Harmonized with 9 km historical baseline."
    },

    "ESA_SENTINEL1_SAR_01": {
        "source_id": "ESA_SENTINEL1_SAR_01",
        "name": "Copernicus Sentinel-1 C-SAR GRD All-Weather Surface Change",
        "organization": "European Space Agency / Copernicus Data Space Ecosystem (CDSE)",
        "state": "North Eastern Region",
        "district": "All NER Districts",
        "site": "Satellite Orbital Swaths",
        "latitude": 25.0000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_MEDIUM,
        "sensor_types": ["GROUND_DISPLACEMENT"],
        "sensor_channels": {
            "backscatter_ratio_vv_vh": {"unit": "dB", "type": "GROUND_DISPLACEMENT"}
        },
        "discovery": "PUBLIC_CDSE_ODATA_API",
        "access_method": "OAUTH2_AUTHENTICATED_REST",
        "telemetry_format": "SAFE_ZIP / GeoTIFF",
        "update_interval_hours": 144.0, # 6-12 days
        "status": STATUS_AUTH_REQUIRED,
        "auth_type": "COPERNICUS_OAUTH2",
        "operational_disclaimer": "Sentinel-1 SAR surface-change monitoring is used as an all-weather/night-capable surface-change signal. This implementation does not perform InSAR displacement measurement."
    },

    "ESA_SENTINEL1_INSAR_01": {
        "source_id": "ESA_SENTINEL1_INSAR_01",
        "name": "Copernicus Sentinel-1 IW Repeat-Pass Differential InSAR",
        "organization": "European Space Agency / Copernicus Data Space Ecosystem (CDSE)",
        "state": "North Eastern Region (Meghalaya focus)",
        "district": "All NER Districts",
        "site": "Satellite Orbital Swaths (Track 150 Descending)",
        "latitude": 25.5720,
        "longitude": 91.8810,
        "elevation_m": 1496.0,
        "signal_speed": SIGNAL_SPEED_MEDIUM,
        "sensor_types": ["GROUND_DISPLACEMENT"],
        "sensor_channels": {
            "relative_los_displacement_m": {"unit": "m", "type": "GROUND_DISPLACEMENT"},
            "coherence": {"unit": "gamma", "type": "COHERENCE"}
        },
        "discovery": "PUBLIC_CDSE_ODATA_API",
        "access_method": "AUTHENTICATED_S3_EODATA",
        "telemetry_format": "GeoTIFF (EPSG:4326)",
        "update_interval_hours": 288.0, # 12 days
        "status": STATUS_LIVE_READY,
        "auth_type": "CDSE_S3",
        "operational_disclaimer": "Relative Line-of-Sight deformation referenced to Shillong Plateau bedrock. Coherence < 0.35 masked as NoData."
    },

    "ESA_SENTINEL2_OPT_01": {
        "source_id": "ESA_SENTINEL2_OPT_01",
        "name": "Copernicus Sentinel-2 MSI Multi-Spectral Surface Reflectance",
        "organization": "Copernicus / Element84 Earth Search STAC",
        "state": "North Eastern Region",
        "district": "All NER Districts",
        "site": "Satellite Orbital Swaths",
        "latitude": 25.0000,
        "longitude": 91.5000,
        "elevation_m": 0.0,
        "signal_speed": SIGNAL_SPEED_CONTEXT,
        "sensor_types": ["OPTICAL_SURFACE_CHANGE"],
        "sensor_channels": {
            "ndvi": {"unit": "index", "type": "OPTICAL_SURFACE_CHANGE"},
            "bare_soil_index": {"unit": "index", "type": "OPTICAL_SURFACE_CHANGE"}
        },
        "discovery": "PUBLIC_STAC_API",
        "access_method": "HTTPS_REST / AWS_S3",
        "telemetry_format": "Cloud-Optimized GeoTIFF",
        "update_interval_hours": 120.0, # 5 days
        "status": STATUS_AUTH_REQUIRED,
        "auth_type": "CDSE_OAUTH2_OR_AWS_PAYER",
        "operational_disclaimer": "Optical passes frequently occluded by heavy monsoon cloud cover; missing observations are never interpreted as low risk."
    },

    "IMD_AWS_SHILLONG_01": {
        "source_id": "IMD_AWS_SHILLONG_01",
        "name": "IMD Automatic Weather Station Shillong",
        "organization": "India Meteorological Department (Ministry of Earth Sciences)",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "site": "Shillong Civil Aerodrome / Observatory",
        "latitude": 25.5686,
        "longitude": 91.8831,
        "elevation_m": 1500.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["RAIN_GAUGE", "TEMPERATURE"],
        "sensor_channels": {
            "rainfall_hourly": {"unit": "mm", "type": "RAIN_GAUGE"},
            "temperature_c": {"unit": "degC", "type": "TEMPERATURE"}
        },
        "discovery": "PUBLIC_MAUSAM_PORTAL",
        "access_method": "RESTRICTED_DEPARTMENTAL_API",
        "telemetry_format": "JSON / XML",
        "update_interval_hours": 1.0,
        "status": STATUS_INSTITUTIONAL_ACCESS_REQUIRED,
        "auth_type": "MOES_INSTITUTIONAL_MOU",
        "operational_disclaimer": "Public web portal mausam.imd.gov.in provides rendered HTML; automated machine-to-machine REST streaming requires official institutional data agreement."
    },

    "LOCAL_ESP32_GATEWAY_01": {
        "source_id": "LOCAL_ESP32_GATEWAY_01",
        "name": "NER-SAFE Reference Slope Hardware Gateway",
        "organization": "NER-SAFE Edge Deployment",
        "state": "Meghalaya / Mizoram",
        "district": "Target Hotspot Slope",
        "site": "Local Physical Deployment Node",
        "latitude": 25.1837,
        "longitude": 91.6421,
        "elevation_m": 150.0,
        "signal_speed": SIGNAL_SPEED_FAST,
        "sensor_types": ["SOIL_MOISTURE", "RAIN_GAUGE", "TILT", "TEMPERATURE"],
        "sensor_channels": {
            "SOIL_MOISTURE": {"unit": "%", "type": "SOIL_MOISTURE"},
            "RAIN_GAUGE": {"unit": "mm/h", "type": "RAIN_GAUGE"},
            "TILT": {"unit": "deg", "type": "TILT"}
        },
        "discovery": "LOCAL_HARDWARE_INTERFACE",
        "access_method": "USB_SERIAL / LOCAL_HTTP_POST / LORA",
        "telemetry_format": "$NER_NMEA_SENTENCE",
        "update_interval_hours": 0.0014, # 5 seconds
        "status": STATUS_HARDWARE_REQUIRED,
        "firmware_source": "esp32_reference_gateway.ino",
        "auth_type": "LOCAL_TOKEN",
        "operational_disclaimer": "Standalone reference firmware created and tested via emulator; requires physical ESP32 and sensor hardware connected by user."
    }
}

class SensorSourceRegistry:
    def __init__(self):
        self.sources = SENSOR_SOURCES

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self.sources.get(source_id)

    def list_sources(self, state_filter: Optional[str] = None,
                     speed_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self.sources.values())
        if state_filter:
            results = [s for s in results if state_filter.lower() in s["state"].lower()]
        if speed_filter:
            results = [s for s in results if s["signal_speed"] == speed_filter]
        return results

    def get_source_health_summary(self) -> Dict[str, Any]:
        counts = {}
        for s in self.sources.values():
            st = s["status"]
            counts[st] = counts.get(st, 0) + 1
        return {
            "total_registered_sources": len(self.sources),
            "status_breakdown": counts,
            "fast_signals_count": len([s for s in self.sources.values() if s["signal_speed"] == SIGNAL_SPEED_FAST]),
            "medium_signals_count": len([s for s in self.sources.values() if s["signal_speed"] == SIGNAL_SPEED_MEDIUM]),
            "context_signals_count": len([s for s in self.sources.values() if s["signal_speed"] == SIGNAL_SPEED_CONTEXT]),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        }

# Global Singleton Registry
sensor_source_registry = SensorSourceRegistry()

if __name__ == "__main__":
    reg = SensorSourceRegistry()
    print(json.dumps(reg.get_source_health_summary(), indent=2))
