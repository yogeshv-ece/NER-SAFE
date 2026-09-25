const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9310;
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
    console.log('[ACCEPTANCE] Spawning Chrome with WebGL...');
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${tempUserDataDir}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1680,1050',
        '--no-first-run',
        '--no-default-browser-check',
        'about:blank'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            const list = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            const p = list.find(t => t.type === 'page');
            if (p && p.webSocketDebuggerUrl) {
                wsUrl = p.webSocketDebuggerUrl;
                break;
            }
        } catch (e) {}
    }

    if (!wsUrl) throw new Error('Could not connect to Chrome debugging target');

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();

    const consoleLogs = [];
    const networkResponses = [];
    const failedNetwork = [];

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
            console.log(`[BROWSER ${msg.params.type.toUpperCase()}]`, text);
        }

        if (msg.method === 'Network.responseReceived') {
            const { url, status, statusText } = msg.params.response;
            networkResponses.push({ url, status });
            if (status >= 400) {
                failedNetwork.push({ url, status, statusText });
                console.log(`[NET ERROR] ${status} ${url}`);
            }
        }
        if (msg.method === 'Network.loadingFailed') {
            failedNetwork.push({ url: msg.params.requestId, error: msg.params.errorText });
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

    console.log('[ACCEPTANCE] Navigating to http://localhost:8000/ ...');
    await send('Page.navigate', { url: 'http://localhost:8000/' });

    console.log('[ACCEPTANCE] Waiting 6 seconds for page and 2D data ingestion...');
    await sleep(6000);

    console.log('[ACCEPTANCE] Calling switchTo3D()...');
    const switchResult = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                switchTo3D();
                return {
                    success: true,
                    viewerInitialized: window.cesiumInitialized,
                    viewerExists: !!window.cesiumViewer,
                    is3DActive: window.is3DActive
                };
            } catch(e) {
                return { success: false, error: e.toString(), stack: e.stack };
            }
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] Switch result:', JSON.stringify(switchResult.result.value, null, 2));

    console.log('[ACCEPTANCE] Waiting 12 seconds for SRTM terrain tile subdivision and entity drape...');
    for (let sec = 1; sec <= 12; sec++) {
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
        console.log(`[ACCEPTANCE] Sec ${sec}:`, JSON.stringify(poll.result.value));
    }

    // Scroll to #cesiumContainer and render Screenshot 1
    console.log('[ACCEPTANCE] Scrolling #cesiumContainer into full view...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(2000);

    // Deep diagnostic of scene 1
    const scene1Diag = await send('Runtime.evaluate', {
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
                    lon: Cesium.Math.toDegrees(g.longitude),
                    lat: Cesium.Math.toDegrees(g.latitude),
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

            return {
                camera: {
                    lon: Cesium.Math.toDegrees(c.positionCartographic.longitude),
                    lat: Cesium.Math.toDegrees(c.positionCartographic.latitude),
                    height_m: Math.round(c.positionCartographic.height),
                    heading_deg: Math.round(Cesium.Math.toDegrees(c.heading)),
                    pitch_deg: Math.round(Cesium.Math.toDegrees(c.pitch))
                },
                centerPick: pickCarto,
                roadEntities,
                buildingEntities,
                hotspotEntities,
                totalEntities: v.entities.values.length,
                tilesLoaded: v.scene.globe.tilesLoaded
            };
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] Scene 1 Diagnostics:\n', JSON.stringify(scene1Diag.result.value, null, 2));

    console.log('[ACCEPTANCE] Capturing Screenshot 1: cesium_real_terrain_render.png ...');
    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[ACCEPTANCE] Saved cesium_real_terrain_render.png');

    // Screenshot 2: Hotspot Closeup Render
    console.log('[ACCEPTANCE] Triggering selectHotspot("EVT-MEG-012")...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(4000);

    const scene2Diag = await send('Runtime.evaluate', {
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
                    lon: Cesium.Math.toDegrees(g.longitude),
                    lat: Cesium.Math.toDegrees(g.latitude)
                };
                targetScreen = {
                    x: winPos ? Math.round(winPos.x) : null,
                    y: winPos ? Math.round(winPos.y) : null,
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
                targetHotspot: {
                    name: target ? target.name : null,
                    carto: targetCarto,
                    screen: targetScreen
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[ACCEPTANCE] Scene 2 Diagnostics:\n', JSON.stringify(scene2Diag.result.value, null, 2));

    console.log('[ACCEPTANCE] Capturing Screenshot 2: cesium_hotspot_closeup_render.png ...');
    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_hotspot_closeup_render.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[ACCEPTANCE] Saved cesium_hotspot_closeup_render.png');

    // Summary of Network & Browser Console
    console.log('[ACCEPTANCE] Total Console Logs:', consoleLogs.length);
    console.log('[ACCEPTANCE] Failed Network Requests:', failedNetwork.length);
    if (failedNetwork.length > 0) {
        console.log('[ACCEPTANCE] Failed Network Details:', JSON.stringify(failedNetwork, null, 2));
    }

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
