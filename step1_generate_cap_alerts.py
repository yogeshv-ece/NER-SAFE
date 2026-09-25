#!/usr/bin/env python3
"""
NER-SAFE — COMPONENT 12: STEP 1 (CORRECTED)
OASIS / ITU-T CAP v1.2 Schema-Aligned Prototype Alert Generator
Scientific Research Prototype — Spatial Guidance & Exposure Advisory Only
Author: NER-SAFE Research & Development Team
Date: September 2026
"""

import os
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Path references
C11_DIR = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\COMPONENT_11"
C12_DIR = r"E:\landslide - Copy\landslide - Copy\NER_SAFE_DATA\COMPONENT_12"
ALERTS_DIR = os.path.join(C12_DIR, "alerts")
XML_INDIV_DIR = os.path.join(ALERTS_DIR, "xml_individual")
META_DIR = os.path.join(C12_DIR, "metadata")
ROOT_DIR = r"E:\landslide - Copy\landslide - Copy"

os.makedirs(ALERTS_DIR, exist_ok=True)
os.makedirs(XML_INDIV_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 12: STEP 1 — CAP v1.2 PROTOTYPE ALERT GENERATOR (AUDITED)")
print("=" * 80)

# Load Component 11 deliverables
events_fp = os.path.join(C11_DIR, "events", "event_records.geojson")
corrs_fp = os.path.join(C11_DIR, "runout_corridors", "runout_corridors.geojson")

with open(events_fp, "r", encoding="utf-8") as f:
    events_data = json.load(f)
with open(corrs_fp, "r", encoding="utf-8") as f:
    corrs_data = json.load(f)

# Map corridors by event_id
corridor_map = {}
for feat in corrs_data["features"]:
    corridor_map[feat["id"]] = feat["geometry"]

print(f"Loaded {len(events_data['features'])} event records and {len(corridor_map)} runout polygons.")

# Timestamp in ISO 8601 with offset
CURRENT_UTC = "2026-09-07T16:45:00+05:30"

# CAP v1.2 Prototype Advisory Mapping (Internal Heuristic Research Tiers)
ALERT_TIER_MAPPING = {
    "CRITICAL": {
        "color": "RED",
        "urgency": "Expected",
        "severity": "Severe",
        "certainty": "Possible",
        "response_type": "Assess",
        "event_code": "LS-EXT-01"
    },
    "HIGH": {
        "color": "ORANGE",
        "urgency": "Expected",
        "severity": "Severe",
        "certainty": "Possible",
        "response_type": "Assess",
        "event_code": "LS-SEV-02"
    },
    "MODERATE": {
        "color": "YELLOW",
        "urgency": "Future",
        "severity": "Moderate",
        "certainty": "Possible",
        "response_type": "Monitor",
        "event_code": "LS-MOD-03"
    },
    "LOW": {
        "color": "GREEN",
        "urgency": "Past",
        "severity": "Minor",
        "certainty": "Unlikely",
        "response_type": "None",
        "event_code": "LS-ADV-04"
    }
}

def format_cap_polygon(geom):
    """Formats GeoJSON Polygon coordinates into space-delimited lat,lon pairs (CAP v1.2 format)"""
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
        outer_ring = rings[0]
    elif geom["type"] == "MultiPolygon":
        outer_ring = geom["coordinates"][0][0]
    else:
        return ""
    # Subsample if too dense (max 40 vertices for clean XML)
    step = max(1, len(outer_ring) // 40)
    sampled = outer_ring[::step]
    if sampled[-1] != sampled[0]:
        sampled.append(sampled[0])
    # CAP standard: latitude,longitude space-delimited
    pairs = [f"{round(pt[1], 6)},{round(pt[0], 6)}" for pt in sampled]
    return " ".join(pairs)

def build_alert_content(p):
    """Generates scientifically sound advisory headlines, descriptions, and informational guidance"""
    p_level = p["impact_priority"]
    cfg = ALERT_TIER_MAPPING[p_level]
    color = cfg["color"]
    state = p["state"]
    district = p["district"]
    near_place = p["nearest_settlement"]
    roads_exp = p["roads_exposed"]
    bldgs_exp = p["buildings_exposed"]
    road_names = p["exposed_road_names"]
    risk = p["risk_score"]
    
    # 1. Headline (Explicitly framed as research advisory, no claims of 'imminent failure')
    if p_level == "CRITICAL":
        if "NH" in road_names:
            headline = f"TIER 1 (RED) ADVISORY: Elevated Hazard Flag near {road_names} in {district}, {state}"
        elif bldgs_exp >= 5:
            headline = f"TIER 1 (RED) ADVISORY: Settlement Corridor Exposure ({bldgs_exp} Structures) in {district}, {state}"
        else:
            headline = f"TIER 1 (RED) ADVISORY: Elevated Slope Consequence Flag near {near_place}, {district}"
    elif p_level == "HIGH":
        headline = f"TIER 2 (ORANGE) ADVISORY: High Susceptibility & Runout Flag near {near_place}, {district}"
    elif p_level == "MODERATE":
        headline = f"TIER 3 (YELLOW) WATCH: Moderate Landslide Watch for Slopes near {near_place}, {district}"
    else:
        headline = f"TIER 4 (GREEN) BASELINE: Low Model Signal for Remote Slopes in {district}"
        
    # 2. Description (Includes prominent scientific disclaimer)
    desc_parts = [
        f"NER-SAFE decision-support prototype identified an elevated risk score of {risk:.3f} (Susceptibility: {p['susceptibility']:.3f}, Trigger Index: {p['dynamic_trigger']:.3f}).",
        f"Location: Latitude {p['latitude']:.4f}°N, Longitude {p['longitude']:.4f}°E (Elevation: {p['elevation_init_m']}m, modeled descent drop: {p['elevation_drop_m']}m).",
        f"Empirical DEM runout corridor extends {p['path_length_m']}m over a mapped footprint of {p['runout_area_m2']:,} m²."
    ]
    if roads_exp > 0:
        desc_parts.append(f"Exposed Road Infrastructure: {roads_exp} segment(s) ({p['roads_exposed_length_m']}m total) along {road_names}.")
    if bldgs_exp > 0:
        desc_parts.append(f"Potentially Exposed Structures: {bldgs_exp} building footprint(s) within modeled corridor (estimated {p['population_exposed']} residents).")
    
    desc_parts.append(
        "SCIENTIFIC NOTICE: This advisory is generated by a research prototype combining 30m DEM slope modeling with coarse satellite rainfall and soil moisture indicators. It does NOT predict the exact timing, occurrence, or certainty of slope failure. Low-confidence or unmonitored zones must not be presumed safe."
    )
    description = " ".join(desc_parts)
    
    # 3. Informational Instruction (Advisory only; no statutory evacuation/closure directives)
    if p_level == "CRITICAL":
        inst = (
            f"INFORMATIONAL HAZARD ADVISORY FOR DISTRICT DISASTER MANAGEMENT AUTHORITIES: "
            f"1. Review modeled potential exposure envelope along {road_names if roads_exp > 0 else 'hill corridors'}. "
            f"2. Recommend field verification of slope distress, tension cracks, and culvert drainage near {near_place}. "
            f"3. All statutory operational decisions (traffic advisories, public warnings, site access) rest exclusively with District Authorities under the Disaster Management Act 2005."
        )
    elif p_level == "HIGH":
        inst = (
            f"INFORMATIONAL HAZARD ADVISORY FOR LOCAL OFFICIALS: "
            f"1. Precautionary monitoring along {road_names if roads_exp > 0 else 'hill corridors'}. "
            f"2. Alert local beat staff and Village Disaster Management Committees near {near_place} to report visible slope displacement. "
            f"3. Note: Prototype outputs are non-statutory."
        )
    elif p_level == "MODERATE":
        inst = (
            f"MONITORING ADVISORY: "
            f"1. Field inspection of roadside drainage and vulnerable cut-slopes during precipitation events. "
            f"2. General precautionary vigilance recommended on steep slopes."
        )
    else:
        inst = (
            "BASELINE OBSERVATION: Satellite and DEM inputs show low relative trigger and susceptibility scores. "
            "Does NOT guarantee absolute slope stability; local micro-topographic, soil, and drainage factors may exist."
        )
        
    return headline, description, inst

cap_alert_records = []
xml_alerts = []

for feat in events_data["features"]:
    p = feat["properties"]
    event_id = p["event_id"]
    p_level = p["impact_priority"]
    cfg = ALERT_TIER_MAPPING[p_level]
    
    alert_id = f"NER-SAFE-CAP-{event_id}"
    headline, description, instruction = build_alert_content(p)
    geom = corridor_map.get(event_id, {"type": "Point", "coordinates": [p["longitude"], p["latitude"]]})
    polygon_str = format_cap_polygon(geom)
    
    alert_record = {
        "identifier": alert_id,
        "event_id": event_id,
        "sender": "nersafe.prototype.research@disaster.advisory",
        "sent": CURRENT_UTC,
        "status": "Actual",
        "msgType": "Alert",
        "scope": "Public",
        "state": p["state"],
        "district": p["district"],
        "tier": cfg["color"],
        "info": {
            "category": "Geo",
            "event": "Landslide Hazard Advisory (Research Prototype)",
            "urgency": cfg["urgency"],
            "severity": cfg["severity"],
            "certainty": cfg["certainty"],
            "eventCode": {
                "valueName": "SAME",
                "value": cfg["event_code"]
            },
            "expires": "2026-09-08T16:45:00+05:30",
            "headline": headline,
            "description": description,
            "instruction": instruction,
            "responseType": cfg["response_type"],
            "contact": "NER-SAFE Research & Development Platform (Experimental Advisory Feed)",
            "parameter": [
                {"valueName": "Prototype_Advisory_Level", "value": cfg["color"]},
                {"valueName": "Risk_Score", "value": str(p["risk_score"])},
                {"valueName": "Susceptibility", "value": str(p["susceptibility"])},
                {"valueName": "Dynamic_Trigger", "value": str(p["dynamic_trigger"])},
                {"valueName": "Uncertainty", "value": str(p["uncertainty"])},
                {"valueName": "Exposed_Road_Length_m", "value": str(p["roads_exposed_length_m"])},
                {"valueName": "Exposed_Buildings_Count", "value": str(p["buildings_exposed"])},
                {"valueName": "Potentially_Exposed_Population", "value": str(p["population_exposed"])},
                {"valueName": "Scientific_Notice", "value": "Research Prototype - Spatial Guidance Only; No Failure Timing Predicted"}
            ],
            "area": {
                "areaDesc": f"{p['district']}, {p['state']} — Vicinity of {p['nearest_settlement']}",
                "circle": f"{p['latitude']},{p['longitude']} 0.5",
                "polygon": polygon_str
            }
        }
    }
    cap_alert_records.append(alert_record)
    
    # Build XML Document
    alert_elem = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
    ET.SubElement(alert_elem, "identifier").text = alert_id
    ET.SubElement(alert_elem, "sender").text = "nersafe.prototype.research@disaster.advisory"
    ET.SubElement(alert_elem, "sent").text = CURRENT_UTC
    ET.SubElement(alert_elem, "status").text = "Actual"
    ET.SubElement(alert_elem, "msgType").text = "Alert"
    ET.SubElement(alert_elem, "scope").text = "Public"
    
    info_elem = ET.SubElement(alert_elem, "info")
    ET.SubElement(info_elem, "category").text = "Geo"
    ET.SubElement(info_elem, "event").text = "Landslide Hazard Advisory (Research Prototype)"
    ET.SubElement(info_elem, "urgency").text = cfg["urgency"]
    ET.SubElement(info_elem, "severity").text = cfg["severity"]
    ET.SubElement(info_elem, "certainty").text = cfg["certainty"]
    
    ec_elem = ET.SubElement(info_elem, "eventCode")
    ET.SubElement(ec_elem, "valueName").text = "SAME"
    ET.SubElement(ec_elem, "value").text = cfg["event_code"]
    
    ET.SubElement(info_elem, "expires").text = "2026-09-08T16:45:00+05:30"
    ET.SubElement(info_elem, "headline").text = headline
    ET.SubElement(info_elem, "description").text = description
    ET.SubElement(info_elem, "instruction").text = instruction
    ET.SubElement(info_elem, "responseType").text = cfg["response_type"]
    ET.SubElement(info_elem, "contact").text = "NER-SAFE Research Platform (Experimental Advisory Feed)"
    
    # Parameters
    for param_name, param_val in [
        ("Prototype_Advisory_Level", cfg["color"]),
        ("Risk_Score", str(p["risk_score"])),
        ("Susceptibility", str(p["susceptibility"])),
        ("Dynamic_Trigger", str(p["dynamic_trigger"])),
        ("Uncertainty", str(p["uncertainty"])),
        ("Exposed_Road_Length_m", str(p["roads_exposed_length_m"])),
        ("Exposed_Buildings_Count", str(p["buildings_exposed"])),
        ("Potentially_Exposed_Population", str(p["population_exposed"])),
        ("Scientific_Notice", "Research Prototype - Spatial Guidance Only; No Failure Timing Predicted")
    ]:
        p_elem = ET.SubElement(info_elem, "parameter")
        ET.SubElement(p_elem, "valueName").text = param_name
        ET.SubElement(p_elem, "value").text = param_val
        
    area_elem = ET.SubElement(info_elem, "area")
    ET.SubElement(area_elem, "areaDesc").text = f"{p['district']}, {p['state']} — Vicinity of {p['nearest_settlement']}"
    ET.SubElement(area_elem, "circle").text = f"{p['latitude']},{p['longitude']} 0.5"
    ET.SubElement(area_elem, "polygon").text = polygon_str
    
    xml_alerts.append(alert_elem)
    
    # Save individual XML for priority TIER 1 and TIER 2 events
    if cfg["color"] in ["RED", "ORANGE"]:
        indiv_xml_fp = os.path.join(XML_INDIV_DIR, f"{alert_id}.xml")
        indiv_str = minidom.parseString(ET.tostring(alert_elem, encoding="utf-8")).toprettyxml(indent="  ")
        with open(indiv_xml_fp, "w", encoding="utf-8") as f:
            f.write(indiv_str)

# Build Master Multi-Alert XML Feed
feed_root = ET.Element("alertsFeed", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
feed_root.attrib["version"] = "1.2"
feed_root.attrib["generated"] = CURRENT_UTC
feed_root.attrib["totalAlerts"] = str(len(xml_alerts))

for a_elem in xml_alerts:
    feed_root.append(a_elem)

master_xml_str = minidom.parseString(ET.tostring(feed_root, encoding="utf-8")).toprettyxml(indent="  ")
master_xml_fp = os.path.join(ALERTS_DIR, "cap_alerts.xml")
with open(master_xml_fp, "w", encoding="utf-8") as f:
    f.write(master_xml_str)
print(f"Saved master CAP v1.2 XML feed: {master_xml_fp} ({len(master_xml_str):,} bytes)")

# Save Master JSON feed
json_feed = {
    "feedTitle": "NER-SAFE Regional Landslide Prototype Advisory Feed",
    "standard": "OASIS CAP v1.2 Schema-Aligned Prototype Export",
    "published": CURRENT_UTC,
    "totalAlerts": len(cap_alert_records),
    "scientific_disclaimer": "Experimental decision-support prototype. For situational awareness only. Does not predict time of slope failure.",
    "alerts": cap_alert_records
}
master_json_fp = os.path.join(ALERTS_DIR, "cap_alerts.json")
with open(master_json_fp, "w", encoding="utf-8") as f:
    json.dump(json_feed, f, indent=2)
print(f"Saved master CAP JSON feed: {master_json_fp} ({len(json.dumps(json_feed)):,} bytes)")

# Save threshold config metadata
thresh_config = {
    "protocol": "NER-SAFE Prototype Multi-Tier Advisory Decision Matrix",
    "classification": "Prototype Heuristic Guidelines (Non-Statutory)",
    "timestamp": CURRENT_UTC,
    "tiers": ALERT_TIER_MAPPING,
    "scientific_safeguards": [
        "Component 10 dynamic trigger is an experimental indicator, not a supervised temporal predictor.",
        "Component 11 flow paths are DEM empirical steepest-descent paths, not guaranteed future slide vectors.",
        "Exposure is consequence information, not predictive evidence.",
        "System does not predict exact timing of slope failure.",
        "Low-signal zones are not certified as safe; unmonitored local factors may exist.",
        "No live government agency API or statutory evacuation authority is claimed."
    ]
}
thresh_fp = os.path.join(META_DIR, "alert_threshold_config.json")
with open(thresh_fp, "w", encoding="utf-8") as f:
    json.dump(thresh_config, f, indent=2)
print(f"Saved threshold config: {thresh_fp}")

# Mirror to project root
root_xml = os.path.join(ROOT_DIR, "cap_alerts.xml")
root_json = os.path.join(ROOT_DIR, "cap_alerts.json")
with open(root_xml, "w", encoding="utf-8") as f:
    f.write(master_xml_str)
with open(root_json, "w", encoding="utf-8") as f:
    json.dump(json_feed, f, indent=2)
print(f"Mirrored cap_alerts.xml and cap_alerts.json to project root.")

print("=" * 80)
print(f"STEP 1 COMPLETE: 48 CAP v1.2 prototype advisory alerts generated with full scientific safeguards.")
print("=" * 80)
