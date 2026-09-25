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
    const tmpDir = path.join(os.tmpdir(), 'chrome_tg_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9263',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9263/json');
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
    
    // Wait for Cesium to load
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        const cCheck = await send('Runtime.evaluate', {
            expression: `typeof Cesium !== 'undefined'`,
            returnByValue: true
        });
        if (cCheck.result && cCheck.result.value === true) {
            console.log('[TEST] Cesium loaded at attempt', i);
            break;
        }
    }
    
    const res = await send('Runtime.evaluate', {
        expression: `(async function() {
            try {
                // Test 1: what does requestTileGeometry return?
                let callCount = 0;
                let lastArgs = null;
                const custom = new Cesium.CustomHeightmapTerrainProvider({
                    width: 65, height: 65,
                    tilingScheme: new Cesium.GeographicTilingScheme(),
                    callback: function(x, y, level) {
                        callCount++;
                        lastArgs = { x, y, level };
                        return new Float32Array(65 * 65);
                    }
                });
                
                const geom0 = await custom.requestTileGeometry(0, 0, 0);
                
                // Now test creating a Viewer with this custom provider
                const div = document.createElement('div');
                div.id = 'testCesiumDiv';
                div.style.width = '500px';
                div.style.height = '500px';
                document.body.appendChild(div);
                
                const viewer = new Cesium.Viewer('testCesiumDiv', {
                    terrainProvider: custom,
                    baseLayerPicker: false,
                    geocoder: false,
                    animation: false,
                    timeline: false
                });
                
                // Wait for tilesLoaded or check state over 3 seconds
                let renderStates = [];
                for (let f = 0; f < 10; f++) {
                    viewer.render();
                    await new Promise(r => setTimeout(r, 200));
                    const s = viewer.scene.globe._surface;
                    renderStates.push({
                        frame: f,
                        tilesLoaded: viewer.scene.globe.tilesLoaded,
                        tilesToRender: s ? s._tilesToRender.length : 0,
                        tile0State: s && s._levelZeroTiles ? s._levelZeroTiles[0].state : null
                    });
                    if (viewer.scene.globe.tilesLoaded && s && s._tilesToRender.length > 0) break;
                }
                
                const surface = viewer.scene.globe._surface;
                const tilesToRender = surface ? surface._tilesToRender.length : 0;
                
                return {
                    geom0Type: geom0 ? geom0.constructor.name : null,
                    renderStates: renderStates,
                    tilesToRender: tilesToRender,
                    tilesLoaded: viewer.scene.globe.tilesLoaded
                };
            } catch(e) {
                return { error: e.toString(), stack: e.stack };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    
    console.log('Test Result:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

test().catch(console.error);
