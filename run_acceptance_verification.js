const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9325;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_accept_' + Date.now());

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
    console.log('[VERIFY] Launching Chrome on http://localhost:8000/ ...');
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

    if (!wsUrl) throw new Error('Could not obtain Chrome debugging WebSocket URL');

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();

    const consoleLogs = [];
    const terrainTileResponses = [];
    const apiRequests = [];
    const failedRequests = [];

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
                console.log(`[BROWSER ERROR]`, text);
            }
        }

        if (msg.method === 'Network.responseReceived') {
            const { url, status, statusText } = msg.params.response;
            if (url.includes('/api/gis/terrain/tile')) {
                terrainTileResponses.push({ status, url });
            } else if (url.includes('/api/')) {
                apiRequests.push({ status, url });
            }
            if (status >= 400) {
                failedRequests.push({ url, status, statusText });
            }
        }

        if (msg.method === 'Network.loadingFailed') {
            failedRequests.push({ id: msg.params.requestId, error: msg.params.errorText });
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

    console.log('[VERIFY] Waiting for CesiumJS and Dashboard initialization...');
    let cesiumReady = false;
    for (let wait = 1; wait <= 30; wait++) {
        await sleep(1000);
        const probe = await send('Runtime.evaluate', {
            expression: `({
                hasCesium: typeof Cesium !== 'undefined',
                hasSwitchTo3D: typeof switchTo3D === 'function',
                hasHotspots: !!(window.hotspotsData && window.hotspotsData.features),
                hotspotsCount: window.hotspotsData && window.hotspotsData.features ? window.hotspotsData.features.length : 0,
                hasRoads: !!(window.roadsData && window.roadsData.features),
                hasBuildings: !!(window.buildingsData && window.buildingsData.features)
            })`,
            returnByValue: true
        });
        const v = probe.result.value || {};
        console.log(`[VERIFY] Wait ${wait}s: Cesium=${v.hasCesium}, switchTo3D=${v.hasSwitchTo3D}, Hotspots=${v.hotspotsCount}, Roads=${v.hasRoads}, Buildings=${v.hasBuildings}`);
        if (v.hasCesium && v.hasSwitchTo3D && v.hasHotspots) {
            cesiumReady = true;
            break;
        }
    }

    if (!cesiumReady) throw new Error('Cesium library failed to load in time');

    console.log('[VERIFY] Switching to 3D...');
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
    console.log('[VERIFY] switchTo3D result:', JSON.stringify(switchRes.result.value));

    console.log('[VERIFY] Monitoring terrain subdivision and entity creation...');
    let lastStats = null;
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
        lastStats = poll.result.value;
        console.log(`[VERIFY] Sec ${s}:`, JSON.stringify(lastStats));
        if (lastStats && lastStats.tileCount >= 30 && lastStats.entitiesCount >= 4000) {
            // Keep rendering to let meshes settle
        }
    }

    // Scroll to #cesiumContainer and capture scene 1
    console.log('[VERIFY] Scrolling #cesiumContainer into full view...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(2000);

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

            let roadEntities = 0;
            let buildingEntities = 0;
            let hotspotEntities = 0;
            v.entities.values.forEach(e => {
                if (e.isHotspotEntity) hotspotEntities++;
                else if (e.polyline) roadEntities++;
                else if (e.polygon) buildingEntities++;
            });

            const tiles = v.scene.globe._surface ? v.scene.globe._surface._tilesToRender : [];
            const levels = tiles.map(t => t.level);

            return {
                viewerExists: true,
                terrainProviderName: v.terrainProvider ? v.terrainProvider.constructor.name : 'None',
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
                    roads: roadEntities,
                    buildings: buildingEntities,
                    hotspots: hotspotEntities
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[VERIFY] Scene 1 Report:\n', JSON.stringify(scene1Report.result.value, null, 2));

    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[VERIFY] Captured and saved cesium_real_terrain_render.png');

    // Trigger selectHotspot('EVT-MEG-012')
    console.log('[VERIFY] Selecting EVT-MEG-012...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(4000);

    const scene2Report = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };
            const c = v.camera;
            const w = v.canvas.width;
            const h = v.canvas.height;
            const target = v.entities.values.find(e => e.name && e.name.includes('EVT-MEG-012'));
            let targetScreen = null;
            let targetCarto = null;
            if (target) {
                const pos = target.position.getValue(Cesium.JulianDate.now());
                const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
                const g = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos);
                targetCarto = {
                    lon: Number(Cesium.Math.toDegrees(g.longitude).toFixed(6)),
                    lat: Number(Cesium.Math.toDegrees(g.latitude).toFixed(6))
                };
                targetScreen = {
                    x: winPos ? Math.round(winPos.x) : null,
                    y: winPos ? Math.round(winPos.y) : null,
                    inViewport: winPos ? (winPos.x >= 0 && winPos.x <= w && winPos.y >= 0 && winPos.y <= h) : false
                };
            }

            return {
                camera: {
                    lon: Number(Cesium.Math.toDegrees(c.positionCartographic.longitude).toFixed(5)),
                    lat: Number(Cesium.Math.toDegrees(c.positionCartographic.latitude).toFixed(5)),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Number(Cesium.Math.toDegrees(c.heading).toFixed(1)),
                    pitch_deg: Number(Cesium.Math.toDegrees(c.pitch).toFixed(1))
                },
                selectedHotspot: {
                    eventId: 'EVT-MEG-012',
                    carto: targetCarto,
                    screen: targetScreen
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[VERIFY] Scene 2 Report:\n', JSON.stringify(scene2Report.result.value, null, 2));

    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_hotspot_closeup_render.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[VERIFY] Captured and saved cesium_hotspot_closeup_render.png');

    console.log('[VERIFY] Terrain Tile Responses Count:', terrainTileResponses.length);
    console.log('[VERIFY] API Requests Count:', apiRequests.length);
    console.log('[VERIFY] Failed Requests Count:', failedRequests.length);
    if (failedRequests.length > 0) {
        console.log('[VERIFY] Failed Requests Details:', JSON.stringify(failedRequests, null, 2));
    }

    // Save report to disk as JSON for programmatic inspection
    const fullAudit = {
        timestamp: new Date().toISOString(),
        scene1Report: scene1Report.result.value,
        scene2Report: scene2Report.result.value,
        terrainTileResponsesCount: terrainTileResponses.length,
        apiRequestsCount: apiRequests.length,
        failedRequestsCount: failedRequests.length,
        consoleLogsCount: consoleLogs.length
    };
    fs.writeFileSync(path.join(__dirname, 'cesium_acceptance_audit.json'), JSON.stringify(fullAudit, null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
