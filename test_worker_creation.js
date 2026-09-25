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

async function test() {
    const tmpDir = path.join(os.tmpdir(), 'chrome_wkr_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9268',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9268/json');
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
    
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        const cCheck = await send('Runtime.evaluate', { expression: `typeof Cesium !== 'undefined'`, returnByValue: true });
        if (cCheck.result && cCheck.result.value === true) break;
    }
    
    const res = await send('Runtime.evaluate', {
        expression: `(async function() {
            try {
                // Test TaskProcessor('createVerticesFromHeightmap')
                const processor = new Cesium.TaskProcessor('createVerticesFromHeightmap');
                
                // Inspect how TaskProcessor builds worker URL
                const workerUrl = Cesium.buildModuleUrl('Workers/createVerticesFromHeightmap.js');
                
                // Now test calling createMesh on a HeightmapTerrainData directly!
                const hData = new Cesium.HeightmapTerrainData({
                    buffer: new Float32Array(65 * 65),
                    width: 65,
                    height: 65
                });
                
                let meshResult = null;
                let meshError = null;
                try {
                    const meshPromise = hData.createMesh({
                        tilingScheme: new Cesium.GeographicTilingScheme(),
                        x: 0, y: 0, level: 0,
                        exaggeration: 1.0
                    });
                    meshResult = await Promise.race([
                        meshPromise,
                        new Promise((_, rej) => setTimeout(() => rej(new Error('TIMEOUT_AFTER_3_SECONDS')), 3000))
                    ]);
                } catch(e) {
                    meshError = e.toString();
                }
                
                return {
                    workerUrl: workerUrl,
                    meshError: meshError,
                    meshResultType: meshResult ? meshResult.constructor.name : null
                };
            } catch(e) {
                return { error: e.toString(), stack: e.stack };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    
    console.log('Worker & Mesh Test:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

test().catch(console.error);
