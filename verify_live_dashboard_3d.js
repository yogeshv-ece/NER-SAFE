const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9250;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_3d_test_' + Date.now());

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
    console.log('[TEST] Launching Chrome with dedicated user-data-dir on http://localhost:8000/ ...');
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
                    console.log('[TEST] Found page target:', target.url);
                    break;
                }
            }
        } catch (e) {}
    }

    if (!wsUrl) {
        chrome.kill();
        throw new Error('Failed to connect to Chrome debugging endpoint');
    }

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();
    const tileRequests = [];
    const consoleLogs = [];
    const consoleErrors = [];

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending.has(msg.id)) {
            const { resolve, reject } = pending.get(msg.id);
            pending.delete(msg.id);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
        } else if (msg.method === 'Runtime.consoleAPICalled') {
            const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            consoleLogs.push({ type: msg.params.type, text });
            if (msg.params.type === 'error') {
                consoleErrors.push(text);
                console.error('[BROWSER ERROR]', text);
            }
        } else if (msg.method === 'Runtime.exceptionThrown') {
            const exText = msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text;
            consoleErrors.push(exText);
            console.error('[BROWSER EXCEPTION]', exText);
        } else if (msg.method === 'Network.responseReceived') {
            const url = msg.params.response.url;
            if (url.includes('/api/gis/terrain/tile')) {
                tileRequests.push({ status: msg.params.response.status, url });
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

    console.log('[TEST] Waiting for document to be ready...');
    let pageReady = false;
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            const evalRes = await send('Runtime.evaluate', {
                expression: `({
                    readyState: document.readyState,
                    title: document.title,
                    hasL: typeof L !== 'undefined',
                    hasCesium: typeof Cesium !== 'undefined',
                    hasSwitchTo3D: typeof switchTo3D === 'function',
                    hasHotspotsData: !!(window.hotspotsData && window.hotspotsData.features),
                    hotspotsCount: window.hotspotsData ? (window.hotspotsData.features || []).length : 0
                })`,
                returnByValue: true
            });
            const v = evalRes.result.value;
            console.log(`[TEST] Poll #${i}: readyState=${v.readyState}, hasCesium=${v.hasCesium}, hasHotspots=${v.hasHotspotsData}, count=${v.hotspotsCount}`);
            if (v && v.hasCesium && v.hasSwitchTo3D && v.hasHotspotsData && v.hotspotsCount > 0) {
                console.log('[TEST] Page ready state reached:', v);
                pageReady = true;
                break;
            }
        } catch(e) {}
    }

    if (!pageReady) {
        throw new Error('Page did not reach ready state with Cesium and hotspotsData');
    }

    // Check 2D initial state
    const initial2d = await send('Runtime.evaluate', {
        expression: `({
            mapExists: !!window.map,
            hotspotsCount: window.hotspotsData ? (window.hotspotsData.features || []).length : 0,
            roadsCount: window.roadsData ? (window.roadsData.features || []).length : 0,
            buildingsCount: window.buildingsData ? (window.buildingsData.features || []).length : 0,
            activeBasemap: window.activeBasemap,
            liveMapDisplay: document.getElementById('liveMap') ? document.getElementById('liveMap').style.display : null,
            cesiumContainerDisplay: document.getElementById('cesiumContainer') ? document.getElementById('cesiumContainer').style.display : null
        })`,
        returnByValue: true
    });
    console.log('[TEST] Initial 2D State:', JSON.stringify(initial2d.result.value, null, 2));

    // Switch to 3D
    console.log('[TEST] Triggering switchTo3D()...');
    const switchRes = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                switchTo3D();
                return { success: true, is3DActive: is3DActive, cesiumInitialized: cesiumInitialized };
            } catch(e) {
                return { success: false, error: e.toString(), stack: e.stack };
            }
        })()`,
        returnByValue: true
    });
    console.log('[TEST] switchTo3D() returned:', switchRes.result.value);

    console.log('[TEST] Waiting 8 seconds for Cesium 3D viewer, tiles, OSM imagery, roads, buildings, and live hotspots...');
    await sleep(8000);

    // Inspect Cesium runtime
    const cesiumState = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v || v.isDestroyed()) return { initialized: false };
            
            const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(v.camera.position);
            const lon = Cesium.Math.toDegrees(carto.longitude);
            const lat = Cesium.Math.toDegrees(carto.latitude);
            const alt = carto.height;

            const entityTypes = { billboard: 0, polyline: 0, polygon: 0, other: 0 };
            v.entities.values.forEach(e => {
                if (e.billboard) entityTypes.billboard++;
                else if (e.polyline) entityTypes.polyline++;
                else if (e.polygon) entityTypes.polygon++;
                else entityTypes.other++;
            });

            return {
                initialized: true,
                is3DActive: window.is3DActive,
                canvasWidth: v.canvas ? v.canvas.width : 0,
                canvasHeight: v.canvas ? v.canvas.height : 0,
                imageryLayersCount: v.imageryLayers ? v.imageryLayers.length : 0,
                totalEntities: v.entities ? v.entities.values.length : 0,
                entityBreakdown: entityTypes,
                terrainExaggeration: v.scene.globe.terrainExaggeration,
                depthTestAgainstTerrain: v.scene.globe.depthTestAgainstTerrain,
                enableLighting: v.scene.globe.enableLighting,
                camera: {
                    longitude: Number(lon.toFixed(4)),
                    latitude: Number(lat.toFixed(4)),
                    altitude_m: Math.round(alt)
                },
                cesiumContainerVisible: document.getElementById('cesiumContainer').style.display !== 'none',
                liveMapVisible: document.getElementById('liveMap').style.display !== 'none',
                hudVisible: document.getElementById('cesiumProvenanceHUD') ? document.getElementById('cesiumProvenanceHUD').style.display !== 'none' : false
            };
        })()`,
        returnByValue: true
    });
    console.log('[TEST] Cesium 3D Runtime State:', JSON.stringify(cesiumState.result.value, null, 2));

    // Scroll into view and capture 3D rendered screenshot
    console.log('[TEST] Scrolling to Cesium 3D container...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(1000);

    console.log('[TEST] Capturing screenshot of rendered 3D scene...');
    const ss3d = await send('Page.captureScreenshot', { format: 'png' });
    const buffer3d = Buffer.from(ss3d.data, 'base64');
    const ss3dPath = path.join(__dirname, 'cesium_live_rendered_scene.png');
    fs.writeFileSync(ss3dPath, buffer3d);
    console.log(`[TEST] Saved 3D screenshot to ${ss3dPath} (${buffer3d.length} bytes)`);

    // Test returning to 2D Leaflet
    console.log('[TEST] Testing return to 2D Leaflet map (clicking #leafletSwitchBtn)...');
    await send('Runtime.evaluate', {
        expression: `(function() {
            const btn = document.getElementById('leafletSwitchBtn');
            if (btn) btn.click();
            else if (window.switchTo2D) window.switchTo2D();
        })()`
    });
    await sleep(2000);

    const return2dState = await send('Runtime.evaluate', {
        expression: `({
            is3DActive: window.is3DActive,
            liveMapDisplay: document.getElementById('liveMap').style.display,
            cesiumContainerDisplay: document.getElementById('cesiumContainer').style.display
        })`,
        returnByValue: true
    });
    console.log('[TEST] State after returning to 2D:', JSON.stringify(return2dState.result.value, null, 2));

    const ss2d = await send('Page.captureScreenshot', { format: 'png' });
    const buffer2d = Buffer.from(ss2d.data, 'base64');
    const ss2dPath = path.join(__dirname, 'leaflet_2d_restored_scene.png');
    fs.writeFileSync(ss2dPath, buffer2d);
    console.log(`[TEST] Saved 2D screenshot to ${ss2dPath} (${buffer2d.length} bytes)`);

    console.log(`[TEST] Total terrain tile requests captured: ${tileRequests.length}`);
    console.log(`[TEST] Total console errors: ${consoleErrors.length}`);

    ws.close();
    chrome.kill();

    try {
        fs.rmSync(tempUserDataDir, { recursive: true, force: true });
    } catch(e) {}

    // Assertions
    const cVal = cesiumState.result.value;
    if (!cVal.initialized) throw new Error('Cesium failed to initialize');
    if (cVal.canvasWidth === 0 || cVal.canvasHeight === 0) throw new Error('Cesium canvas has 0 dimensions');
    if (cVal.imageryLayersCount < 1) throw new Error('Cesium has no imagery layers (black globe)');
    if (cVal.totalEntities < 48) throw new Error(`Cesium entities insufficient (${cVal.totalEntities})`);
    if (cVal.camera.longitude < 89.0 || cVal.camera.longitude > 94.5 || cVal.camera.latitude < 21.0 || cVal.camera.latitude > 27.5) {
        throw new Error(`Camera outside NER AOI: lon ${cVal.camera.longitude}, lat ${cVal.camera.latitude}`);
    }

    console.log('\n==================================================');
    console.log('>>> 3D REAL RENDERING VERIFICATION SUITE: PASSED <<<');
    console.log('==================================================\n');
}

run().catch(err => {
    console.error('[TEST] Verification Failed:', err);
    process.exit(1);
});
