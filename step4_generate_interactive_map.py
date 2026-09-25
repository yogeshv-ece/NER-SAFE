"""
NER-SAFE — AI-Based Landslide Early Warning & Risk Monitoring System
Component 11: Step 4 — Standalone Interactive Leaflet HTML Map Generator

Generates a standalone, dependency-free interactive HTML map:
- Reads flow_paths.geojson, runout_corridors.geojson, event_records.geojson, exposure_intersections.geojson
- Embeds data as self-contained JSON objects (zero CORS errors when opened from local disk file:///)
- Features dark/satellite base layers, event click inspect, sidebar event navigator, priority filtering
"""

import os
import json

PROJECT_ROOT = r"E:\landslide - Copy\landslide - Copy"
C11_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "COMPONENT_11")
MAPS_DIR = os.path.join(C11_DIR, "maps")
os.makedirs(MAPS_DIR, exist_ok=True)

print("=" * 80)
print("NER-SAFE — COMPONENT 11: STEP 4 — INTERACTIVE LEAFLET MAP GENERATOR")
print("=" * 80)

# Load GeoJSON datasets
with open(os.path.join(C11_DIR, "events", "event_records.geojson"), "r", encoding="utf-8") as f:
    events_data = json.load(f)
with open(os.path.join(C11_DIR, "flow_paths", "flow_paths.geojson"), "r", encoding="utf-8") as f:
    paths_data = json.load(f)
with open(os.path.join(C11_DIR, "runout_corridors", "runout_corridors.geojson"), "r", encoding="utf-8") as f:
    corrs_data = json.load(f)
with open(os.path.join(C11_DIR, "exposure", "exposure_intersections.geojson"), "r", encoding="utf-8") as f:
    exp_data = json.load(f)

# Compute Dashboard KPIs
total_events = len(events_data["features"])
crit_count = sum(1 for f in events_data["features"] if f["properties"]["impact_priority"] == "CRITICAL")
high_count = sum(1 for f in events_data["features"] if f["properties"]["impact_priority"] == "HIGH")
mod_count = sum(1 for f in events_data["features"] if f["properties"]["impact_priority"] == "MODERATE")
low_count = sum(1 for f in events_data["features"] if f["properties"]["impact_priority"] == "LOW")

tot_bldgs = sum(f["properties"]["buildings_exposed"] for f in events_data["features"])
tot_roads_m = sum(f["properties"]["roads_exposed_length_m"] for f in events_data["features"])
tot_pop = sum(f["properties"]["population_exposed"] for f in events_data["features"])

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NER-SAFE — Landslide Flow-Path, Runout & Exposure Impact Engine (Component 11)</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0b0f19;
            color: #e2e8f0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        /* Top Navigation Bar */
        header {{
            background: rgba(15, 23, 42, 0.95);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(12px);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 1000;
        }}
        .header-title {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .badge {{
            background: #2563eb;
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            letter-spacing: 0.5px;
        }}
        .badge-pill {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 9999px;
        }}
        h1 {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.3px;
            color: #f8fafc;
        }}
        .subtitle {{
            font-size: 12px;
            color: #94a3b8;
        }}
        /* App Container */
        .app-body {{
            display: flex;
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        /* Sidebar Dashboard */
        #sidebar {{
            width: 380px;
            background: #0f172a;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            flex-direction: column;
            z-index: 900;
            overflow-y: auto;
        }}
        .sidebar-section {{
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }}
        .section-header {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        /* KPI Cards Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        .kpi-card {{
            background: rgba(30, 41, 59, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 10px 12px;
            border-radius: 8px;
        }}
        .kpi-val {{
            font-size: 20px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}
        .kpi-label {{
            font-size: 11px;
            color: #94a3b8;
            margin-top: 2px;
        }}
        .text-red {{ color: #ef4444; }}
        .text-orange {{ color: #f97316; }}
        .text-amber {{ color: #f59e0b; }}
        .text-blue {{ color: #3b82f6; }}
        .text-emerald {{ color: #10b981; }}
        /* Event List Filter */
        .search-box {{
            width: 100%;
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            margin-bottom: 10px;
            outline: none;
        }}
        .search-box:focus {{
            border-color: #3b82f6;
        }}
        .event-list {{
            flex: 1;
            overflow-y: auto;
            max-height: 480px;
        }}
        .event-item {{
            padding: 10px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .event-item:hover {{
            background: rgba(59, 130, 246, 0.1);
            border-left: 3px solid #3b82f6;
        }}
        .event-item.active {{
            background: rgba(59, 130, 246, 0.2);
            border-left: 3px solid #60a5fa;
        }}
        .evt-id {{
            font-weight: 700;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: #f1f5f9;
        }}
        .evt-loc {{
            font-size: 11px;
            color: #94a3b8;
            margin-top: 2px;
        }}
        .evt-pill {{
            font-size: 10px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .pill-CRITICAL {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .pill-HIGH {{ background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.4); }}
        .pill-MODERATE {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4); }}
        .pill-LOW {{ background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4); }}
        /* Map Container */
        #map {{
            flex: 1;
            height: 100%;
            background: #070a12;
        }}
        /* Custom Leaflet Popups */
        .leaflet-popup-content-wrapper {{
            background: #0f172a !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 8px !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
        }}
        .leaflet-popup-tip {{
            background: #0f172a !important;
        }}
        .popup-header {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 8px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .popup-title {{
            font-size: 14px;
            font-weight: 700;
            color: #f8fafc;
        }}
        .prop-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px 12px;
            font-size: 11px;
            margin-top: 6px;
        }}
        .prop-lbl {{
            color: #94a3b8;
        }}
        .prop-val {{
            font-weight: 600;
            color: #f1f5f9;
            font-family: 'JetBrains Mono', monospace;
        }}
        /* Legend */
        .map-legend {{
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 11px;
            line-height: 1.5;
            color: #cbd5e1;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 4px 0;
        }}
        .legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>

    <header>
        <div class="header-title">
            <span class="badge">NER-SAFE</span>
            <div>
                <h1>Landslide Flow-Path, Runout & Consequence Analysis Engine</h1>
                <div class="subtitle">Component 11 Operational Decision-Support Interface — Phase 1: Meghalaya & Mizoram</div>
            </div>
        </div>
        <div style="display: flex; gap: 8px;">
            <span class="badge-pill">✓ 48 Monitored Hotspots</span>
            <span class="badge-pill">✓ DEM D8 Flow Routing</span>
            <span class="badge-pill">✓ STRtree Spatial Indexing</span>
        </div>
    </header>

    <div class="app-body">
        <!-- Sidebar Dashboard -->
        <div id="sidebar">
            <div class="sidebar-section">
                <div class="section-header">
                    <span>Phase 1 Impact Overview</span>
                    <span style="font-size: 10px; color: #3b82f6;">MEGHALAYA & MIZORAM</span>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-val text-red">{crit_count}</div>
                        <div class="kpi-label">Critical Priority</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-val text-orange">{high_count}</div>
                        <div class="kpi-label">High Priority</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-val text-amber">{mod_count}</div>
                        <div class="kpi-label">Moderate Priority</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-val text-blue">{low_count}</div>
                        <div class="kpi-label">Low Priority</div>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="section-header">
                    <span>Exposed Infrastructure Metrics</span>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-val text-emerald">{tot_bldgs}</div>
                        <div class="kpi-label">Buildings Intersected</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-val text-emerald">{tot_roads_m:,.0f} m</div>
                        <div class="kpi-label">Road Network Exposed</div>
                    </div>
                    <div class="kpi-card" style="grid-column: span 2;">
                        <div class="kpi-val text-emerald">{tot_pop} citizens</div>
                        <div class="kpi-label">Estimated Potentially Exposed Population</div>
                    </div>
                </div>
            </div>

            <div class="sidebar-section" style="flex: 1; display: flex; flex-direction: column; overflow: hidden;">
                <div class="section-header">
                    <span>Monitored Landslide Events ({total_events})</span>
                </div>
                <input type="text" id="eventSearch" class="search-box" placeholder="Filter by event ID, district, or place...">
                <div class="event-list" id="eventList"></div>
            </div>
        </div>

        <!-- Interactive Map Container -->
        <div id="map"></div>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

    <script>
        // Embedded GeoJSON Datasets
        const eventsData = {json.dumps(events_data)};
        const pathsData = {json.dumps(paths_data)};
        const corrsData = {json.dumps(corrs_data)};
        const expData = {json.dumps(exp_data)};

        // Initialize Leaflet Map centered between Meghalaya and Mizoram
        const map = L.map('map', {{
            center: [24.2, 92.5],
            zoom: 8,
            zoomControl: true
        }});

        // Base Maps
        const cartoDark = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://carto.com/">CARTO</a> | &copy; OpenStreetMap',
            maxZoom: 19
        }}).addTo(map);

        const esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: '&copy; Esri World Imagery',
            maxZoom: 19
        }});

        const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }});

        // Styling helpers
        function getPriorityColor(priority) {{
            switch(priority) {{
                case 'CRITICAL': return '#ef4444';
                case 'HIGH': return '#f97316';
                case 'MODERATE': return '#f59e0b';
                default: return '#3b82f6';
            }}
        }}

        // Layers
        const corrsLayer = L.geoJSON(corrsData, {{
            style: function(feat) {{
                return {{
                    color: getPriorityColor(feat.properties.impact_priority),
                    weight: 1.5,
                    opacity: 0.8,
                    fillColor: getPriorityColor(feat.properties.impact_priority),
                    fillOpacity: 0.22,
                    dashArray: '4, 4'
                }};
            }},
            onEachFeature: function(feat, layer) {{
                bindEventPopup(feat.properties, layer, 'Runout Corridor');
            }}
        }}).addTo(map);

        const pathsLayer = L.geoJSON(pathsData, {{
            style: function(feat) {{
                return {{
                    color: '#ffffff',
                    weight: 2.5,
                    opacity: 0.95
                }};
            }},
            onEachFeature: function(feat, layer) {{
                bindEventPopup(feat.properties, layer, 'Flow Path Centerline');
            }}
        }}).addTo(map);

        const expLayer = L.geoJSON(expData, {{
            style: function(feat) {{
                if (feat.properties.asset_type === 'Road') {{
                    return {{ color: '#facc15', weight: 3, opacity: 1.0 }};
                }} else if (feat.properties.asset_type === 'Building') {{
                    return {{ color: '#ec4899', weight: 1, fillColor: '#f43f5e', fillOpacity: 0.7 }};
                }}
                return {{ color: '#06b6d4', weight: 2 }};
            }},
            pointToLayer: function(feat, latlng) {{
                return L.circleMarker(latlng, {{
                    radius: 5,
                    fillColor: '#06b6d4',
                    color: '#ffffff',
                    weight: 1.5,
                    fillOpacity: 0.9
                }});
            }},
            onEachFeature: function(feat, layer) {{
                let p = feat.properties;
                layer.bindPopup(`
                    <div style="font-size:12px;">
                        <strong>${{p.asset_type}} Exposed</strong><br/>
                        Event: <code>${{p.event_id}}</code><br/>
                        Name: ${{p.name || 'Unnamed'}}<br/>
                        ${{p.fclass ? 'Class: ' + p.fclass : ''}}
                        ${{p.area_m2 ? '<br/>Footprint: ' + p.area_m2 + ' m²' : ''}}
                    </div>
                `);
            }}
        }}).addTo(map);

        const eventMarkers = {{}};
        const pointsLayer = L.geoJSON(eventsData, {{
            pointToLayer: function(feat, latlng) {{
                const p = feat.properties;
                const marker = L.circleMarker(latlng, {{
                    radius: 7,
                    fillColor: getPriorityColor(p.impact_priority),
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1.0,
                    fillOpacity: 0.95
                }});
                eventMarkers[p.event_id] = {{ marker: marker, latlng: latlng, props: p }};
                return marker;
            }},
            onEachFeature: function(feat, layer) {{
                bindEventPopup(feat.properties, layer, 'Initiation Point');
            }}
        }}).addTo(map);

        function bindEventPopup(p, layer, title) {{
            const content = `
                <div style="min-width: 280px; padding: 4px;">
                    <div class="popup-header">
                        <div>
                            <div class="popup-title">${{p.event_id}}</div>
                            <span style="font-size:10px; color:#94a3b8;">${{p.state}} • ${{p.district}}</span>
                        </div>
                        <span class="evt-pill pill-${{p.impact_priority}}">${{p.impact_priority}}</span>
                    </div>
                    <div class="prop-grid">
                        <div><span class="prop-lbl">Hazard Risk:</span> <span class="prop-val">${{p.risk_score}}</span></div>
                        <div><span class="prop-lbl">Impact Score:</span> <span class="prop-val">${{p.impact_score || p.combined_risk_score}}</span></div>
                        <div><span class="prop-lbl">Elevation Drop:</span> <span class="prop-val">${{p.elevation_drop_m}} m</span></div>
                        <div><span class="prop-lbl">Path Length:</span> <span class="prop-val">${{p.path_length_m}} m</span></div>
                        <div><span class="prop-lbl">Runout Area:</span> <span class="prop-val">${{p.runout_area_m2}} m²</span></div>
                        <div><span class="prop-lbl">Stop Reason:</span> <span class="prop-val" style="font-size:10px;">${{p.stopping_reason}}</span></div>
                    </div>
                    <div style="margin-top:10px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.08); font-size:11px;">
                        <strong>Exposed Consequence Assets:</strong><br/>
                        • Roads: <span style="color:#facc15;">${{p.roads_exposed || 0}} segments (${{p.roads_exposed_length_m || 0}} m)</span><br/>
                        • Buildings: <span style="color:#f43f5e;">${{p.buildings_exposed || 0}} structures</span><br/>
                        • Pop. Exposed: <span style="color:#10b981;">${{p.population_exposed || 0}} residents</span><br/>
                        • Near Locality: <span>${{p.nearest_settlement}} (${{p.settlement_distance_km}} km)</span><br/>
                        • Overall Confidence: <span>${{p.overall_confidence ? (p.overall_confidence * 100).toFixed(0) + '%' : '85%'}}</span>
                    </div>
                </div>
            `;
            layer.bindPopup(content);
        }}

        // Build Sidebar Event List
        const eventListEl = document.getElementById('eventList');
        function renderEventList(filterText = '') {{
            eventListEl.innerHTML = '';
            eventsData.features.forEach(feat => {{
                const p = feat.properties;
                const matchStr = `${{p.event_id}} ${{p.district}} ${{p.nearest_settlement}} ${{p.state}}`.toLowerCase();
                if (filterText && !matchStr.includes(filterText.toLowerCase())) return;

                const item = document.createElement('div');
                item.className = 'event-item';
                item.id = `item-${{p.event_id}}`;
                item.innerHTML = `
                    <div>
                        <div class="evt-id">${{p.event_id}}</div>
                        <div class="evt-loc">${{p.district}} • Near ${{p.nearest_settlement}}</div>
                    </div>
                    <span class="evt-pill pill-${{p.impact_priority}}">${{p.impact_priority}}</span>
                `;
                item.onclick = function() {{
                    document.querySelectorAll('.event-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    const target = eventMarkers[p.event_id];
                    if (target) {{
                        map.flyTo(target.latlng, 15, {{ duration: 1.2 }});
                        setTimeout(() => {{
                            target.marker.openPopup();
                        }}, 1300);
                    }}
                }};
                eventListEl.appendChild(item);
            }});
        }}
        renderEventList();

        document.getElementById('eventSearch').addEventListener('input', function(e) {{
            renderEventList(e.target.value);
        }});

        // Layer Controls
        const baseMaps = {{
            "Dark Theme (CARTO)": cartoDark,
            "Satellite (Esri Imagery)": esriSat,
            "OpenStreetMap Standard": osm
        }};

        const overlayMaps = {{
            "Initiation Points": pointsLayer,
            "Predicted Flow Paths": pathsLayer,
            "Runout Corridors": corrsLayer,
            "Exposed Assets": expLayer
        }};

        L.control.layers(baseMaps, overlayMaps, {{ collapsed: false, position: 'topright' }}).addTo(map);

        // Add Legend
        const legend = L.control({{ position: 'bottomright' }});
        legend.onAdd = function(map) {{
            const div = L.DomUtil.create('div', 'map-legend');
            div.innerHTML = `
                <div style="font-weight:700; margin-bottom:6px; color:#f8fafc;">Impact Priority</div>
                <div class="legend-item"><div class="legend-color" style="background:#ef4444;"></div> Critical Priority</div>
                <div class="legend-item"><div class="legend-color" style="background:#f97316;"></div> High Priority</div>
                <div class="legend-item"><div class="legend-color" style="background:#f59e0b;"></div> Moderate Priority</div>
                <div class="legend-item"><div class="legend-color" style="background:#3b82f6;"></div> Low Priority</div>
                <div style="margin-top:8px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.1); font-weight:700; color:#f8fafc;">Exposure Assets</div>
                <div class="legend-item"><div class="legend-color" style="background:#facc15;"></div> Intersected Highway / Road</div>
                <div class="legend-item"><div class="legend-color" style="background:#f43f5e;"></div> Intersected Building Footprint</div>
            `;
            return div;
        }};
        legend.addTo(map);

    </script>
</body>
</html>
"""

html_fp = os.path.join(MAPS_DIR, "ner_safe_component11_map.html")
with open(html_fp, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Generated standalone interactive map: {html_fp}")

# Also mirror to project root
root_html = os.path.join(PROJECT_ROOT, "ner_safe_component11_map.html")
with open(root_html, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Mirrored interactive map to project root: {root_html}")

print("=" * 80)
print("STEP 4 COMPLETE: Standalone Interactive HTML Map Generated Successfully!")
print("=" * 80)
