const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9370;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_final_accept_' + Date.now());

async function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

function getJson(url) {
    return new Promise((resolve, reject) => {
        http.get(url, res => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
            });
        }).on('error', reject);
    });
}

async function run() {
    console.log('[ACCEPTANCE] Starting Chrome browser runtime check on port', DEBUG_PORT);
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${tempUserDataDir}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1680,1050',
        '--no-first-run',
        '--no-default-browser-check',
        'http://localhost:8000/'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            const list = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            if (list && list.length > 0) {
                const target = list.find(t => t.type === 'page' && t.url.includes('localhost:8000')) ||
                               list.find(t => t.type === 'page');
                if (target && target.webSocketDebuggerUrl) {
                    wsUrl = target.webSocketDebuggerUrl;
                    break;
                }
            }
        } catch (e) {}
    }

    if (!wsUrl) throw new Error('Could not establish CDP WebSocket connection to Chrome');

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();

    const consoleLogs = [];
    const browserErrors = [];
    const localNetworkRequests = [];
    const failedNetworkRequests = [];

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending.has(msg.id)) {
            const { resolve, reject } = pending.get(msg.id);
            pending.delete(msg.id);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
        }

        if (msg.method === 'Runtime.consoleAPICalled') {
            const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            consoleLogs.push({ type: msg.params.type, text });
            if (msg.params.type === 'error') {
                browserErrors.push(text);
                console.log('[BROWSER CONSOLE ERROR]', text);
            }
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            const d = msg.params.exceptionDetails;
            const desc = d.exception?.description || d.text;
            browserErrors.push(desc);
            console.log('[BROWSER EXCEPTION]', desc);
        }

        if (msg.method === 'Network.responseReceived') {
            const { url, status, statusText } = msg.params.response;
            if (url.includes('localhost:8000') || url.includes('/api/')) {
                localNetworkRequests.push({ url, status });
            }
            if (status >= 400 && (url.includes('localhost:8000') || url.includes('/api/'))) {
                failedNetworkRequests.push({ url, status, statusText });
                console.log(`[NET ERROR] ${status} ${url}`);
            }
        }

        if (msg.method === 'Network.loadingFailed') {
            if (msg.params.errorText !== 'net::ERR_ABORTED') {
                failedNetworkRequests.push({ id: msg.params.requestId, error: msg.params.errorText });
                console.log(`[NET FAILED] ${msg.params.errorText}`);
            }
        }
    };

    function send(method, params = {}) {
        const id = msgId++;
        return new Promise((resolve, reject) => {
            pending.set(id, { resolve, reject });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    await new Promise(r => ws.onopen = r);
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Network.enable');

    console.log('[ACCEPTANCE] Waiting for CesiumJS and Dashboard initialization...');
    let isReady = false;
    for (let wait = 1; wait <= 25; wait++) {
        await sleep(1000);
        const check = await send('Runtime.evaluate', {
            expression: `({
                hasCesium: typeof Cesium !== 'undefined',
                hasSwitchTo3D: typeof switchTo3D === 'function',
                hasHotspots: !!(window.hotspotsData && window.hotspotsData.features),
                hotspotsLen: window.hotspotsData?.features?.length || 0,
                hasRoads: !!(window.roadsData && window.roadsData.features),
                roadsLen: window.roadsData?.features?.length || 0,
                hasBuildings: !!(window.buildingsData && window.buildingsData.features),
                buildingsLen: window.buildingsData?.features?.length || 0
            })`,
            returnByValue: true
        });
        const v = check.result.value || {};
        console.log(`[ACCEPTANCE] Sec ${wait}: Cesium=${v.hasCesium}, switchTo3D=${v.hasSwitchTo3D}, Hotspots=${v.hotspotsLen}, Roads=${v.roadsLen}, Buildings=${v.buildingsLen}`);
        if (v.hasCesium && v.hasSwitchTo3D && v.hasHotspots && v.hasRoads && v.hasBuildings) {
            isReady = true;
            break;
        }
    }

    if (!isReady) throw new Error('Timeout waiting for Dashboard and GIS datasets');

    // Verify 2D vs API consistency for known hotspot EVT-MEG-012 before switching to 3D
    const consistencyCheck = await send('Runtime.evaluate', {
        expression: `(function() {
            const apiHotspot = window.hotspotsData.features.find(f => f.properties.event_id === 'EVT-MEG-012');
            let leafletMarker = null;
            if (window.mapLayers && window.mapLayers.hotspots) {
                window.mapLayers.hotspots.eachLayer(l => {
                    if (l.feature && l.feature.properties && l.feature.properties.event_id === 'EVT-MEG-012') {
                        leafletMarker = l;
                    }
                });
            }

            return {
                api: {
                    eventId: apiHotspot ? apiHotspot.properties.event_id : null,
                    coords: apiHotspot ? apiHotspot.geometry.coordinates : null,
                    score: apiHotspot ? apiHotspot.properties.fused_risk_score : null,
                    tier: apiHotspot ? apiHotspot.properties.fused_tier : null
                },
                leaflet2D: {
                    found: !!leafletMarker,
                    coords: leafletMarker ? [leafletMarker.getLatLng().lng, leafletMarker.getLatLng().lat] : null,
                    score: leafletMarker ? leafletMarker.feature.properties.fused_risk_score : null,
                    tier: leafletMarker ? leafletMarker.feature.properties.fused_tier : null
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] 2D / API Pre-Check:\n', JSON.stringify(consistencyCheck.result.value, null, 2));

    // Switch to 3D
    console.log('[ACCEPTANCE] Calling switchTo3D()...');
    const switchRes = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                switchTo3D();
                return { success: true };
            } catch(e) {
                return { success: false, error: e.toString() };
            }
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] switchTo3D Result:', JSON.stringify(switchRes.result.value));

    // Wait for terrain tiles to subdivide and entities to drape
    console.log('[ACCEPTANCE] Waiting 15s for 3D globe rendering and terrain tile subdivision...');
    let scene1State = null;
    for (let s = 1; s <= 15; s++) {
        await sleep(1000);
        const poll = await send('Runtime.evaluate', {
            expression: `(function() {
                const v = window.cesiumViewer;
                if (!v || !v.scene || !v.scene.globe || !v.scene.globe._surface) {
                    return { ready: false };
                }
                const tiles = v.scene.globe._surface._tilesToRender || [];
                const levels = tiles.map(t => t.level);
                return {
                    ready: true,
                    tileCount: tiles.length,
                    maxLevel: levels.length > 0 ? Math.max(...levels) : -1,
                    minLevel: levels.length > 0 ? Math.min(...levels) : -1,
                    entitiesCount: v.entities.values.length,
                    tilesLoaded: v.scene.globe.tilesLoaded
                };
            })()`,
            returnByValue: true
        });
        scene1State = poll.result.value;
        console.log(`[ACCEPTANCE] 3D Sec ${s}:`, JSON.stringify(scene1State));
    }

    // Scroll #cesiumContainer into full view
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(2000);

    // Deep scene 1 analysis
    const scene1Report = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };
            const c = v.camera;
            const w = v.canvas.width;
            const h = v.canvas.height;
            const center = new Cesium.Cartesian2(w / 2, h / 2);
            const ray = c.getPickRay(center);
            const pickGlobe = v.scene.globe.pick(ray, v.scene);
            let pickCarto = null;
            if (pickGlobe) {
                const g = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pickGlobe);
                pickCarto = {
                    lon: Number(Cesium.Math.toDegrees(g.longitude).toFixed(5)),
                    lat: Number(Cesium.Math.toDegrees(g.latitude).toFixed(5)),
                    height_m: Math.round(g.height)
                };
            }

            let roadCount = 0;
            let buildingCount = 0;
            let hotspotCount = 0;
            v.entities.values.forEach(e => {
                if (e.isHotspotEntity) hotspotCount++;
                else if (e.polyline) roadCount++;
                else if (e.polygon) buildingCount++;
            });

            const tiles = v.scene.globe._surface ? v.scene.globe._surface._tilesToRender : [];
            const levels = tiles.map(t => t.level);

            // Check 3D hotspot representation for EVT-MEG-012
            const ent012 = v.entities.values.find(e => e.name && e.name.includes('EVT-MEG-012'));
            let h012Carto = null;
            let h012WinPos = null;
            if (ent012) {
                const pos = ent012.position.getValue(Cesium.JulianDate.now());
                const g = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos);
                const win = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
                h012Carto = [Number(Cesium.Math.toDegrees(g.longitude).toFixed(6)), Number(Cesium.Math.toDegrees(g.latitude).toFixed(6))];
                h012WinPos = win ? { x: Math.round(win.x), y: Math.round(win.y) } : null;
            }

            return {
                viewerExists: true,
                terrainProviderName: v.terrainProvider ? v.terrainProvider.constructor.name : null,
                camera: {
                    lon: Number(Cesium.Math.toDegrees(c.positionCartographic.longitude).toFixed(5)),
                    lat: Number(Cesium.Math.toDegrees(c.positionCartographic.latitude).toFixed(5)),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Number(Cesium.Math.toDegrees(c.heading).toFixed(1)),
                    pitch_deg: Number(Cesium.Math.toDegrees(c.pitch).toFixed(1))
                },
                centerPickTerrain: pickCarto,
                tileCount: tiles.length,
                maxLevel: levels.length > 0 ? Math.max(...levels) : -1,
                tilesLoaded: v.scene.globe.tilesLoaded,
                entities: {
                    total: v.entities.values.length,
                    roads: roadCount,
                    buildings: buildingCount,
                    hotspots: hotspotCount
                },
                hotspot012In3D: {
                    found: !!ent012,
                    coords: h012Carto,
                    winPos: h012WinPos
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] Scene 1 Full Diagnostics:\n', JSON.stringify(scene1Report.result.value, null, 2));

    // Capture Screenshot 1: cesium_real_terrain_render.png
    console.log('[ACCEPTANCE] Capturing Screenshot 1: cesium_real_terrain_render.png ...');
    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[ACCEPTANCE] Saved cesium_real_terrain_render.png');

    // Trigger selectHotspot('EVT-MEG-012')
    console.log('[ACCEPTANCE] Selecting hotspot EVT-MEG-012...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(4000);

    // Deep scene 2 analysis
    const scene2Report = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };
            const c = v.camera;
            const w = v.canvas.width;
            const h = v.canvas.height;
            const ent012 = v.entities.values.find(e => e.name && e.name.includes('EVT-MEG-012'));
            let h012WinPos = null;
            let inViewport = false;
            if (ent012) {
                const pos = ent012.position.getValue(Cesium.JulianDate.now());
                const win = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
                if (win) {
                    h012WinPos = { x: Math.round(win.x), y: Math.round(win.y) };
                    inViewport = (win.x >= 0 && win.x <= w && win.y >= 0 && win.y <= h);
                }
            }

            // Find nearby road screen coordinates
            const nearbyRoads = [];
            v.entities.values.filter(e => e.polyline).forEach(r => {
                const posArr = r.polyline.positions.getValue(Cesium.JulianDate.now());
                if (posArr && posArr.length > 0) {
                    const win = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, posArr[0]);
                    if (win && win.x >= 0 && win.x <= w && win.y >= 0 && win.y <= h) {
                        nearbyRoads.push({ name: r.name, x: Math.round(win.x), y: Math.round(win.y) });
                    }
                }
            });

            // Find nearby building screen coordinates
            const nearbyBuildings = [];
            v.entities.values.filter(e => e.polygon).forEach(b => {
                const hier = b.polygon.hierarchy.getValue(Cesium.JulianDate.now());
                if (hier && hier.positions && hier.positions.length > 0) {
                    const win = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, hier.positions[0]);
                    if (win && win.x >= 0 && win.x <= w && win.y >= 0 && win.y <= h) {
                        nearbyBuildings.push({ name: b.name, x: Math.round(win.x), y: Math.round(win.y) });
                    }
                }
            });

            const sidebarCard = document.querySelector('.hotspot-card.selected');
            const inspectorTitle = document.querySelector('#hotspotRunoutInspector .qual-critical, #hotspotRunoutInspector');

            return {
                camera: {
                    lon: Number(Cesium.Math.toDegrees(c.positionCartographic.longitude).toFixed(5)),
                    lat: Number(Cesium.Math.toDegrees(c.positionCartographic.latitude).toFixed(5)),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Number(Cesium.Math.toDegrees(c.heading).toFixed(1)),
                    pitch_deg: Number(Cesium.Math.toDegrees(c.pitch).toFixed(1))
                },
                canvas: { width: w, height: h },
                selectedHotspot: {
                    eventId: 'EVT-MEG-012',
                    winPos: h012WinPos,
                    inViewport,
                    sidebarSelected: !!sidebarCard,
                    inspectorVisible: inspectorTitle ? inspectorTitle.style.display !== 'none' : false
                },
                visibleRoadsInView: nearbyRoads.length,
                sampleVisibleRoads: nearbyRoads.slice(0, 5),
                visibleBuildingsInView: nearbyBuildings.length,
                sampleVisibleBuildings: nearbyBuildings.slice(0, 5)
            };
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] Scene 2 Full Diagnostics:\n', JSON.stringify(scene2Report.result.value, null, 2));

    // Capture Screenshot 2: cesium_hotspot_closeup_render.png
    console.log('[ACCEPTANCE] Capturing Screenshot 2: cesium_hotspot_closeup_render.png ...');
    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_hotspot_closeup_render.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[ACCEPTANCE] Saved cesium_hotspot_closeup_render.png');

    // Final Report Audit Output
    const auditOutput = {
        executionTimestamp: new Date().toISOString(),
        consistencyCheck: consistencyCheck.result.value,
        scene1Report: scene1Report.result.value,
        scene2Report: scene2Report.result.value,
        browserErrorsCount: browserErrors.length,
        browserErrors,
        localNetworkRequestsCount: localNetworkRequests.length,
        failedNetworkRequestsCount: failedNetworkRequests.length,
        failedNetworkRequests
    };

    fs.writeFileSync(path.join(__dirname, 'FINAL_VISUAL_ACCEPTANCE_DATA.json'), JSON.stringify(auditOutput, null, 2));
    console.log('[ACCEPTANCE] Saved FINAL_VISUAL_ACCEPTANCE_DATA.json');

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
