const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9255;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_inspect_' + Date.now());

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
    console.log('[INSPECT] Spawning Chrome...');
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

    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const pending = new Map();

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending.has(msg.id)) {
            const { resolve, reject } = pending.get(msg.id);
            pending.delete(msg.id);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
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

    console.log('[INSPECT] Waiting 5s for dashboard ready...');
    await sleep(5000);

    // Switch to 3D
    console.log('[INSPECT] Switching to 3D...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    await sleep(5000);

    // Deep diagnostics of Cesium scene
    const diag = await send('Runtime.evaluate', {
        expression: `(async function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };

            // Check what error the current terrain provider has
            let tileCount = v.scene.globe._surface ? v.scene.globe._surface._tilesToRender.length : 0;
            const c = v.camera;
            const center = new Cesium.Cartesian2(v.canvas.width / 2, v.canvas.height / 2);
            
            const ray = c.getPickRay(center);
            const pickGlobe = v.scene.globe.pick(ray, v.scene);
            const pickEllipsoid = c.pickEllipsoid(center);
            
            let pickGlobeCarto = null;
            if (pickGlobe) {
                const g = Cesium.Ellipsoid.WGS84.cartesianToCartographic(pickGlobe);
                pickGlobeCarto = { lon: Cesium.Math.toDegrees(g.longitude), lat: Cesium.Math.toDegrees(g.latitude), h: g.height };
            }

            const gl = v.scene.context._gl;
            const w = v.canvas.width;
            const h = v.canvas.height;
            const pxCenter = new Uint8Array(4);
            gl.readPixels(Math.floor(w/2), Math.floor(h/2), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pxCenter);

            return {
                tileCount,
                pickGlobeCarto,
                centerPixelRGBA: Array.from(pxCenter),
                entitiesCount: v.entities.values.length,
                tilesLoaded: v.scene.globe.tilesLoaded,
                camera: {
                    lon: Cesium.Math.toDegrees(c.positionCartographic.longitude),
                    lat: Cesium.Math.toDegrees(c.positionCartographic.latitude),
                    height_m: c.positionCartographic.height
                }
            };
        })()`,
        awaitPromise: true,
        returnByValue: true
    });

    console.log('[INSPECT] Diagnostic Results:\n', JSON.stringify(diag.result.value, null, 2));

    // Scroll #cesiumContainer into view
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(1000);

    // Capture screenshot
    const ss = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss.data, 'base64'));
    console.log('[INSPECT] Saved cesium_real_terrain_render.png');

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
