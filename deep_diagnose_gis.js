const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9277;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_deep_gis_' + Date.now());

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
    console.log('[DIAG] Spawning Chrome...');
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${tempUserDataDir}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1600,1050',
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

    if (!wsUrl) throw new Error('Could not get CDP wsUrl');

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();

    const consoleLogs = [];
    const networkRequests = [];
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
            if (msg.params.type === 'error' || msg.params.type === 'warning') {
                console.log(`[BROWSER ${msg.params.type.toUpperCase()}]`, text);
            }
        }

        if (msg.method === 'Network.responseReceived') {
            const { url, status, statusText } = msg.params.response;
            networkRequests.push({ url, status });
            if (status >= 400) {
                failedRequests.push({ url, status, statusText });
                console.log(`[NET ERROR] ${status} ${url}`);
            }
        }

        if (msg.method === 'Network.loadingFailed') {
            failedRequests.push({ url: msg.params.requestId, error: msg.params.errorText });
            console.log(`[NET FAILED] ${msg.params.errorText}`);
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

    console.log('[DIAG] Waiting 4s for initial dashboard data to load...');
    await sleep(4000);

    console.log('[DIAG] Calling switchTo3D()...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });

    console.log('[DIAG] Waiting 10s for Cesium terrain subdivision and layers...');
    for (let s = 1; s <= 10; s++) {
        await sleep(1000);
        const poll = await send('Runtime.evaluate', {
            expression: `(function() {
                const v = window.cesiumViewer;
                if (!v || !v.scene.globe._surface) return { ready: false };
                const tiles = v.scene.globe._surface._tilesToRender;
                const levels = tiles.map(t => t.level);
                return {
                    tileCount: tiles.length,
                    maxLevel: levels.length ? Math.max(...levels) : -1,
                    entities: v.entities.values.length,
                    tilesLoaded: v.scene.globe.tilesLoaded
                };
            })()`,
            returnByValue: true
        });
        console.log(`[DIAG] Sec ${s}:`, JSON.stringify(poll.result.value));
    }

    // Now deep inspect entities, coordinates, screen projections
    const entityAnalysis = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { error: 'No viewer' };

            const c = v.camera;
            const w = v.canvas.width;
            const h = v.canvas.height;

            const hotspots = [];
            let roadCount = 0;
            let buildingCount = 0;
            let hotspotCount = 0;

            const entities = v.entities.values;
            for (let i = 0; i < entities.length; i++) {
                const ent = entities[i];
                if (ent.isHotspotEntity) {
                    hotspotCount++;
                    const pos = ent.position.getValue(Cesium.JulianDate.now());
                    const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
                    const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos);
                    hotspots.push({
                        name: ent.name,
                        cartoLon: Cesium.Math.toDegrees(carto.longitude),
                        cartoLat: Cesium.Math.toDegrees(carto.latitude),
                        screenX: winPos ? Math.round(winPos.x) : null,
                        screenY: winPos ? Math.round(winPos.y) : null,
                        inViewport: winPos ? (winPos.x >= 0 && winPos.x <= w && winPos.y >= 0 && winPos.y <= h) : false
                    });
                } else if (ent.polyline) {
                    roadCount++;
                } else if (ent.polygon) {
                    buildingCount++;
                }
            }

            // Find sample buildings and roads screen coordinates
            const sampleBuildings = [];
            for (let i = 0; i < entities.length && sampleBuildings.length < 5; i++) {
                const ent = entities[i];
                if (ent.polygon && ent.polygon.hierarchy) {
                    const hier = ent.polygon.hierarchy.getValue(Cesium.JulianDate.now());
                    if (hier && hier.positions && hier.positions.length > 0) {
                        const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, hier.positions[0]);
                        const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(hier.positions[0]);
                        sampleBuildings.push({
                            name: ent.name,
                            lon: Cesium.Math.toDegrees(carto.longitude),
                            lat: Cesium.Math.toDegrees(carto.latitude),
                            screenX: winPos ? Math.round(winPos.x) : null,
                            screenY: winPos ? Math.round(winPos.y) : null
                        });
                    }
                }
            }

            const sampleRoads = [];
            for (let i = 0; i < entities.length && sampleRoads.length < 5; i++) {
                const ent = entities[i];
                if (ent.polyline && ent.polyline.positions) {
                    const pos = ent.polyline.positions.getValue(Cesium.JulianDate.now());
                    if (pos && pos.length > 0) {
                        const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos[0]);
                        const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pos[0]);
                        sampleRoads.push({
                            name: ent.name,
                            lon: Cesium.Math.toDegrees(carto.longitude),
                            lat: Cesium.Math.toDegrees(carto.latitude),
                            screenX: winPos ? Math.round(winPos.x) : null,
                            screenY: winPos ? Math.round(winPos.y) : null
                        });
                    }
                }
            }

            return {
                totalEntities: entities.length,
                hotspotCount,
                roadCount,
                buildingCount,
                canvasWidth: w,
                canvasHeight: h,
                camera: {
                    lon: Cesium.Math.toDegrees(c.positionCartographic.longitude),
                    lat: Cesium.Math.toDegrees(c.positionCartographic.latitude),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Math.round(Cesium.Math.toDegrees(c.heading)),
                    pitch_deg: Math.round(Cesium.Math.toDegrees(c.pitch))
                },
                hotspotsInView: hotspots.filter(h => h.inViewport),
                sampleRoads,
                sampleBuildings
            };
        })()`,
        returnByValue: true
    });

    console.log('[DIAG] Entity Analysis:');
    console.log(JSON.stringify(entityAnalysis.result.value, null, 2));

    // Scroll to #cesiumContainer and capture test screenshot
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(1500);

    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_diag_test1.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[DIAG] Captured cesium_diag_test1.png');

    // Test selectHotspot('EVT-MEG-012')
    console.log('[DIAG] Calling selectHotspot(EVT-MEG-012)...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(3500);

    const closeupAnalysis = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return null;
            const c = v.camera;
            const w = v.canvas.width;
            const h = v.canvas.height;
            const targetHotspot = v.entities.values.find(e => e.name && e.name.includes('EVT-MEG-012'));
            let hotspotScreen = null;
            if (targetHotspot) {
                const pos = targetHotspot.position.getValue(Cesium.JulianDate.now());
                const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
                hotspotScreen = {
                    screenX: winPos ? Math.round(winPos.x) : null,
                    screenY: winPos ? Math.round(winPos.y) : null,
                    inViewport: winPos ? (winPos.x >= 0 && winPos.x <= w && winPos.y >= 0 && winPos.y <= h) : false
                };
            }
            return {
                camera: {
                    lon: Cesium.Math.toDegrees(c.positionCartographic.longitude),
                    lat: Cesium.Math.toDegrees(c.positionCartographic.latitude),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Math.round(Cesium.Math.toDegrees(c.heading)),
                    pitch_deg: Math.round(Cesium.Math.toDegrees(c.pitch))
                },
                hotspotScreen
            };
        })()`,
        returnByValue: true
    });
    console.log('[DIAG] Closeup Analysis:');
    console.log(JSON.stringify(closeupAnalysis.result.value, null, 2));

    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_diag_test2.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[DIAG] Captured cesium_diag_test2.png');

    console.log('[DIAG] Summary:');
    console.log('Total Console Messages:', consoleLogs.length);
    console.log('Failed Requests:', failedRequests.length);
    if (failedRequests.length > 0) {
        console.log(JSON.stringify(failedRequests, null, 2));
    }

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
