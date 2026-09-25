const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9260;
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
    console.log('[TEST] Spawning Chrome...');
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

    console.log('[TEST] Waiting 4s for dashboard ready...');
    await sleep(4000);

    console.log('[TEST] Switching to 3D...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });

    // Wait for terrain tiles to load
    for (let s = 1; s <= 12; s++) {
        await sleep(1000);
        const st = await send('Runtime.evaluate', {
            expression: `(function() {
                const v = window.cesiumViewer;
                if (!v || !v.scene.globe._surface) return { ready: false };
                const tiles = v.scene.globe._surface._tilesToRender;
                const levels = tiles.map(t => t.level);
                return {
                    tileCount: tiles.length,
                    maxLevel: levels.length ? Math.max(...levels) : -1,
                    entitiesCount: v.entities.values.length,
                    tilesLoaded: v.scene.globe.tilesLoaded
                };
            })()`,
            returnByValue: true
        });
        console.log(`[TEST] Sec ${s}:`, JSON.stringify(st.result.value));
        if (st.result.value && st.result.value.maxLevel >= 6) {
            // Keep going a few more seconds to allow meshes and textures to complete
        }
    }

    // Scroll #cesiumContainer into view and take main screenshot
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(1500);

    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[TEST] Saved cesium_real_terrain_render.png');

    // Now click on EVT-MEG-012 in the list to fly closer
    console.log('[TEST] Selecting EVT-MEG-012...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(3500);

    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_hotspot_closeup_render.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[TEST] Saved cesium_hotspot_closeup_render.png');

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
