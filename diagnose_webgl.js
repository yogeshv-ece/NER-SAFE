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
    const tmpDir = path.join(os.tmpdir(), 'chrome_gl_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9288',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 25; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9288/json');
            const target = list.find(t => t.type === 'page' && t.url.includes('localhost:8000'));
            if (target && target.webSocketDebuggerUrl) {
                wsUrl = target.webSocketDebuggerUrl;
                break;
            }
        } catch(e) {}
    }
    if (!wsUrl) throw new Error('Could not connect to Chrome on port 9288');
    const ws = new WebSocket(wsUrl);
    await new Promise(r => ws.onopen = r);
    
    let msgId = 1;
    const pending = new Map();
    const networkUrls = [];
    ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id && pending.has(m.id)) {
            pending.get(m.id)(m.result);
            pending.delete(m.id);
        } else if (m.method === 'Network.responseReceived') {
            networkUrls.push({ status: m.params.response.status, url: m.params.response.url });
        }
    };
    function send(method, params = {}) {
        const id = msgId++;
        return new Promise(r => { pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
    }
    await send('Network.enable');
    await send('Runtime.enable');
    await new Promise(r => setTimeout(r, 2500));
    
    // Switch to 3D
    console.log('[TEST] Calling switchTo3D()...');
    const switchRes = await send('Runtime.evaluate', {
        expression: `(function() {
            switchTo3D();
            return {
                is3DActive: window.is3DActive,
                cesiumInitialized: window.cesiumInitialized,
                cWidth: document.getElementById('cesiumContainer').offsetWidth,
                cHeight: document.getElementById('cesiumContainer').offsetHeight
            };
        })()`,
        returnByValue: true
    });
    console.log('[TEST] switchTo3D result:', switchRes.result.value);
    
    // Wait for tiles and render
    console.log('[TEST] Waiting 6 seconds for tiles and frames...');
    await new Promise(r => setTimeout(r, 6000));
    
    const diag = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { error: 'no viewer on window' };
            
            const canvas = v.canvas;
            const gl = v.scene.context._gl;
            const pixels = new Uint8Array(4);
            gl.readPixels(Math.floor(canvas.width / 2), Math.floor(canvas.height / 2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

            const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(v.camera.position);

            return {
                canvasWidth: canvas.width,
                canvasHeight: canvas.height,
                centerPixelRGBA: [pixels[0], pixels[1], pixels[2], pixels[3]],
                camera: {
                    lon: Cesium.Math.toDegrees(carto.longitude),
                    lat: Cesium.Math.toDegrees(carto.latitude),
                    height: carto.height,
                    pitch: Cesium.Math.toDegrees(v.camera.pitch)
                },
                globeShow: v.scene.globe.show,
                baseColor: v.scene.globe.baseColor.toCssColorString(),
                imageryLayersLength: v.imageryLayers.length,
                entitiesCount: v.entities.values.length
            };
        })()`,
        returnByValue: true
    });
    
    console.log('DIAGNOSTIC RESULT:\n', JSON.stringify(diag.result.value, null, 2));
    
    const terrainReqs = networkUrls.filter(u => u.url.includes('/api/gis/terrain'));
    const osmReqs = networkUrls.filter(u => u.url.includes('openstreetmap'));
    console.log(`[TEST] Terrain requests: ${terrainReqs.length}, OSM requests: ${osmReqs.length}`);
    if (terrainReqs.length > 0) console.log('Sample terrain requests:', terrainReqs.slice(0, 5));
    if (osmReqs.length > 0) console.log('Sample OSM requests:', osmReqs.slice(0, 5));

    // Capture screenshot
    const ss = await send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(ss.data, 'base64');
    fs.writeFileSync(path.join(__dirname, 'cesium_diagnose_scene.png'), buffer);
    console.log(`[TEST] Screenshot saved to cesium_diagnose_scene.png (${buffer.length} bytes)`);
    
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
