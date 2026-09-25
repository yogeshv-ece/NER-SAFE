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
    const tmpDir = path.join(os.tmpdir(), 'chrome_dtl_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9266',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9266/json');
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
    
    // Wait for Cesium
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 500));
        const cCheck = await send('Runtime.evaluate', {
            expression: `typeof Cesium !== 'undefined'`,
            returnByValue: true
        });
        if (cCheck.result && cCheck.result.value === true) break;
    }
    
    const res = await send('Runtime.evaluate', {
        expression: `(async function() {
            try {
                // Inspect how GlobeSurfaceTileProvider processes tile.data
                const custom = new Cesium.CustomHeightmapTerrainProvider({
                    width: 65, height: 65,
                    tilingScheme: new Cesium.GeographicTilingScheme(),
                    callback: (x, y, level) => new Float32Array(65 * 65)
                });
                
                const div = document.createElement('div');
                div.id = 'diagCesiumDiv';
                div.style.width = '400px'; div.style.height = '400px';
                document.body.appendChild(div);
                
                const v = new Cesium.Viewer('diagCesiumDiv', {
                    terrainProvider: custom,
                    baseLayerPicker: false
                });
                
                for (let i = 0; i < 5; i++) {
                    v.render();
                    await new Promise(r => setTimeout(r, 100));
                }
                
                const surface = v.scene.globe._surface;
                const tile0 = surface && surface._levelZeroTiles ? surface._levelZeroTiles[0] : null;
                
                let tileInfo = null;
                if (tile0) {
                    const d = tile0.data;
                    tileInfo = {
                        state: tile0.state,
                        hasData: !!d,
                        terrainData: d && d.terrainData ? d.terrainData.constructor.name : null,
                        mesh: d && d.mesh ? d.mesh.constructor.name : null,
                        waterMaskTexture: d ? !!d.waterMaskTexture : null,
                        imageryLength: d && d.imagery ? d.imagery.length : null,
                        ready: d ? d.ready : null,
                        tileProps: d ? Object.keys(d) : []
                    };
                }
                
                v.destroy();
                div.remove();
                return tileInfo;
            } catch(e) {
                return { error: e.toString(), stack: e.stack };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    
    console.log('Tile Loader Diagnosis:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

test().catch(console.error);
