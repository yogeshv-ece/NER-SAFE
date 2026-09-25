const { spawn } = require('child_process');
const http = require('http');
const os = require('os');
const path = require('path');
const fs = require('fs');

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
    const tmpDir = path.join(os.tmpdir(), 'chrome_3d_final_' + Date.now());
    console.log('[TEST] Spawning Chrome with WebGL on http://localhost:8000/ ...');
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9305',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1600,1050',
        '--no-first-run',
        '--no-default-browser-check',
        'http://localhost:8000/'
    ]);

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9305/json');
            if (list && list.length > 0) {
                const target = list.find(t => t.type === 'page' && t.url.includes('localhost:8000')) || list.find(t => t.type === 'page');
                if (target && target.webSocketDebuggerUrl) {
                    wsUrl = target.webSocketDebuggerUrl;
                    break;
                }
            }
        } catch(e) {}
    }
    if (!wsUrl) throw new Error('Could not connect to Chrome debugging port');

    const ws = new WebSocket(wsUrl);
    await new Promise(r => ws.onopen = r);

    let msgId = 1;
    const pending = new Map();
    const networkUrls = [];
    const consoleLogs = [];
    const exceptions = [];

    ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id && pending.has(m.id)) {
            pending.get(m.id)(m.result);
            pending.delete(m.id);
        } else if (m.method === 'Network.responseReceived') {
            networkUrls.push({ status: m.params.response.status, url: m.params.response.url });
        } else if (m.method === 'Runtime.consoleAPICalled') {
            const text = m.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            consoleLogs.push({ type: m.params.type, text });
            console.log(`[BROWSER CONSOLE ${m.params.type}]`, text);
        } else if (m.method === 'Runtime.exceptionThrown') {
            const desc = m.params.exceptionDetails ? m.params.exceptionDetails.text + ': ' + (m.params.exceptionDetails.exception ? m.params.exceptionDetails.exception.description : '') : JSON.stringify(m.params);
            exceptions.push(desc);
            console.error('[BROWSER EXCEPTION]', desc);
        }
    };

    function send(method, params = {}) {
        const id = msgId++;
        return new Promise(r => { pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
    }

    await send('Network.enable');
    await send('Runtime.enable');
    await send('Page.enable');

    console.log('[TEST] Waiting 4 seconds for page load...');
    await new Promise(r => setTimeout(r, 4000));

    // Click 3D Terrain
    console.log('[TEST] Switching to 3D Terrain mode...');
    const switchRes = await send('Runtime.evaluate', {
        expression: `(function() {
            switchTo3D();
            return {
                is3DActive: window.is3DActive,
                cesiumInitialized: window.cesiumInitialized,
                cWidth: document.getElementById('cesiumContainer').offsetWidth,
                cHeight: document.getElementById('cesiumContainer').offsetHeight,
                mapWidth: document.querySelector('.map-container').offsetWidth,
                mapHeight: document.querySelector('.map-container').offsetHeight
            };
        })()`,
        returnByValue: true
    });
    console.log('[TEST] Switch result:', switchRes.result.value);

    console.log('[TEST] Waiting 7 seconds for terrain geometry, OSM imagery, and entities to load...');
    await new Promise(r => setTimeout(r, 7000));

    // Inspect runtime state
    const state = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };

            const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(v.camera.position);

            const entityTypes = { billboard: 0, polyline: 0, polygon: 0, other: 0 };
            v.entities.values.forEach(e => {
                if (e.billboard) entityTypes.billboard++;
                else if (e.polyline) entityTypes.polyline++;
                else if (e.polygon) entityTypes.polygon++;
                else entityTypes.other++;
            });

            const centerRay = v.camera.getPickRay(new Cesium.Cartesian2(v.canvas.width / 2, v.canvas.height / 2));
            const pickGlobe = v.scene.globe.pick(centerRay, v.scene);
            let pickCarto = null;
            if (pickGlobe) {
                const c = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pickGlobe);
                pickCarto = { lon: Cesium.Math.toDegrees(c.longitude), lat: Cesium.Math.toDegrees(c.latitude), height: c.height };
            }

            const surface = v.scene.globe._surface;
            const tilesToRender = surface ? surface._tilesToRender.length : 0;

            const gl = v.scene.context._gl;
            const pxCenter = new Uint8Array(4);
            gl.readPixels(Math.floor(v.canvas.width / 2), Math.floor(v.canvas.height / 2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pxCenter);

            const layer0 = v.imageryLayers.get(0);

            return {
                canvasWidth: v.canvas.width,
                canvasHeight: v.canvas.height,
                globeShow: v.scene.globe.show,
                globeBaseColor: v.scene.globe.baseColor.toCssColorString(),
                tilesToRenderCount: tilesToRender,
                pickCarto: pickCarto,
                centerPixelRGBA: Array.from(pxCenter),
                imageryLayersCount: v.imageryLayers.length,
                layer0Provider: layer0 && layer0.imageryProvider ? layer0.imageryProvider.constructor.name : null,
                layer0Ready: layer0 && layer0.imageryProvider ? layer0.imageryProvider.ready : null,
                totalEntities: v.entities.values.length,
                entityBreakdown: entityTypes,
                terrainExaggeration: v.scene.globe.terrainExaggeration,
                depthTest: v.scene.globe.depthTestAgainstTerrain,
                camera: {
                    lon: Number(Cesium.Math.toDegrees(carto.longitude).toFixed(4)),
                    lat: Number(Cesium.Math.toDegrees(carto.latitude).toFixed(4)),
                    altitude_m: Math.round(carto.height),
                    heading: Number(Cesium.Math.toDegrees(v.camera.heading).toFixed(1)),
                    pitch: Number(Cesium.Math.toDegrees(v.camera.pitch).toFixed(1))
                }
            };
        })()`,
        returnByValue: true
    });
    console.log('[TEST] Cesium Scene State:\n', JSON.stringify(state.result.value, null, 2));

    // Scroll map container into view
    console.log('[TEST] Scrolling map container into view...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await new Promise(r => setTimeout(r, 1200));

    // Capture screenshot
    console.log('[TEST] Capturing screenshot of rendered 3D scene...');
    const ss = await send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(ss.data, 'base64');
    const outPath = path.join(__dirname, 'cesium_rendered_scene_final.png');
    fs.writeFileSync(outPath, buffer);
    console.log(`[TEST] Saved screenshot to ${outPath} (${buffer.length} bytes)`);

    const terrainReqs = networkUrls.filter(u => u.url.includes('/api/gis/terrain'));
    const osmReqs = networkUrls.filter(u => u.url.includes('openstreetmap'));
    console.log(`[TEST] Terrain tile responses: ${terrainReqs.length}`);
    console.log(`[TEST] OSM imagery tile responses: ${osmReqs.length}`);

    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
