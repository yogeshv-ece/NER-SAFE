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
    const tmpDir = path.join(os.tmpdir(), 'chrome_diag_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9333',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1600,1050',
        'http://localhost:8000/'
    ]);

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9333/json');
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

    ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id && pending.has(m.id)) {
            pending.get(m.id)(m.result || m.error);
            pending.delete(m.id);
        } else if (m.method === 'Runtime.consoleAPICalled') {
            const text = m.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            console.log(`[PAGE LOG]`, text);
        } else if (m.method === 'Runtime.exceptionThrown') {
            console.error(`[PAGE EXC]`, m.params.exceptionDetails);
        }
    };

    function send(method, params = {}) {
        const id = msgId++;
        return new Promise(r => { pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
    }

    await send('Runtime.enable');
    await send('Page.enable');
    await new Promise(r => setTimeout(r, 3000));

    // Switch to 3D and inspect
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    await new Promise(r => setTimeout(r, 4000));

    const res = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                const v = window.cesiumViewer;
                if (!v) return { noViewer: true };

                const cam = v.camera;
                const carto = Cesium.Ellipsoid.WGS84.cartesianToCartographic(cam.position);
                const dir = cam.direction;
                const up = cam.up;
                const right = cam.right;

                // Pick point at center of screen
                const centerRay = cam.getPickRay(new Cesium.Cartesian2(v.canvas.width / 2, v.canvas.height / 2));
                const globeIntersection = v.scene.globe.pick(centerRay, v.scene);
                let hitCarto = null;
                if (globeIntersection) {
                    const c = Cesium.Ellipsoid.WGS84.cartesianToCartographic(globeIntersection);
                    hitCarto = {
                        lon: Cesium.Math.toDegrees(c.longitude),
                        lat: Cesium.Math.toDegrees(c.latitude),
                        height: c.height
                    };
                }

                // Check surface tiles
                const surface = v.scene.globe._surface;
                const tilesToRender = surface ? surface._tilesToRender.length : 0;
                const levelZeroLoaded = surface ? surface._levelZeroTiles : null;

                // Sample 5 pixels across the canvas
                const gl = v.scene.context._gl;
                const samples = [];
                [0.1, 0.3, 0.5, 0.7, 0.9].forEach(fx => {
                    [0.2, 0.5, 0.8].forEach(fy => {
                        const px = new Uint8Array(4);
                        gl.readPixels(Math.floor(v.canvas.width * fx), Math.floor(v.canvas.height * fy), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
                        samples.push({ fx, fy, rgba: Array.from(px) });
                    });
                });

                return {
                    globeShow: v.scene.globe.show,
                    tilesToRenderCount: tilesToRender,
                    cameraCarto: {
                        lon: Cesium.Math.toDegrees(carto.longitude),
                        lat: Cesium.Math.toDegrees(carto.latitude),
                        height: carto.height
                    },
                    cameraDir: { x: dir.x, y: dir.y, z: dir.z },
                    pitchDeg: Cesium.Math.toDegrees(cam.pitch),
                    headingDeg: Cesium.Math.toDegrees(cam.heading),
                    hitGlobeAtCenter: hitCarto,
                    entitiesTotal: v.entities.values.length,
                    samples: samples
                };
            } catch(e) {
                return { error: e.toString(), stack: e.stack };
            }
        })()`,
        returnByValue: true
    });

    console.log('[VIEWER STATE]:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
