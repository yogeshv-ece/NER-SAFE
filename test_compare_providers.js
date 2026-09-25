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

async function check() {
    const tmpDir = path.join(os.tmpdir(), 'chrome_comp_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9262',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9262/json');
            if (list && list.length > 0) {
                const target = list.find(t => t.type === 'page' && t.url.includes('localhost:8000')) || list.find(t => t.type === 'page');
                if (target && target.webSocketDebuggerUrl) { wsUrl = target.webSocketDebuggerUrl; break; }
            }
        } catch(e) {}
    }
    const ws = new WebSocket(wsUrl);
    await new Promise(r => ws.onopen = r);
    let msgId = 1;
    const pending = new Map();
    ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result || m.error); pending.delete(m.id); }
    };
    function send(method, params = {}) {
        const id = msgId++;
        return new Promise(r => { pending.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
    }
    await send('Runtime.enable');
    await new Promise(r => setTimeout(r, 2000));
    
    const res = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                const ellip = new Cesium.EllipsoidTerrainProvider();
                const custom = new Cesium.CustomHeightmapTerrainProvider({
                    width: 65, height: 65,
                    tilingScheme: new Cesium.GeographicTilingScheme(),
                    callback: (x, y, l) => new Float32Array(65 * 65)
                });
                
                function inspectP(p) {
                    return {
                        className: p.constructor.name,
                        ready: p.ready,
                        hasWaterMask: p.hasWaterMask,
                        hasVertexNormals: p.hasVertexNormals,
                        tilingScheme: p.tilingScheme ? p.tilingScheme.constructor.name : null,
                        error0: typeof p.getLevelMaximumGeometricError === 'function' ? p.getLevelMaximumGeometricError(0) : null,
                        error1: typeof p.getLevelMaximumGeometricError === 'function' ? p.getLevelMaximumGeometricError(1) : null,
                        hasAvailability: !!p.availability,
                        methods: Object.getOwnPropertyNames(Object.getPrototypeOf(p))
                    };
                }
                
                return {
                    ellipsoid: inspectP(ellip),
                    custom: inspectP(custom)
                };
            } catch(e) {
                return { error: e.toString() };
            }
        })()`,
        returnByValue: true
    });
    
    console.log('Provider Comparison:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

check().catch(console.error);
