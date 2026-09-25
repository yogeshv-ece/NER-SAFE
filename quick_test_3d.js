const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9335;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_quick_' + Date.now());

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
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        `--user-data-dir=${tempUserDataDir}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1680,1050',
        '--no-first-run',
        '--no-default-browser-check',
        'http://localhost:8000/'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            const list = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            const p = list.find(t => t.type === 'page' && t.url.includes('localhost:8000'));
            if (p && p.webSocketDebuggerUrl) {
                wsUrl = p.webSocketDebuggerUrl;
                break;
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

    console.log('[QUICK] Waiting for Cesium & switchTo3D...');
    for (let w = 1; w <= 15; w++) {
        await sleep(1000);
        const check = await send('Runtime.evaluate', {
            expression: `({
                cesium: typeof Cesium !== 'undefined',
                switchTo3D: typeof switchTo3D === 'function',
                hotspots: !!(window.hotspotsData && window.hotspotsData.features)
            })`,
            returnByValue: true
        });
        if (check.result.value.cesium && check.result.value.switchTo3D && check.result.value.hotspots) {
            console.log(`[QUICK] Ready at ${w}s!`);
            break;
        }
    }

    console.log('[QUICK] Switching to 3D...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });

    for (let s = 1; s <= 15; s++) {
        await sleep(1000);
        const st = await send('Runtime.evaluate', {
            expression: `(function() {
                const v = window.cesiumViewer;
                if (!v || !v.scene.globe._surface) return { ready: false };
                const tiles = v.scene.globe._surface._tilesToRender;
                const levels = tiles.map(t => t.level);
                return {
                    sec: ${s},
                    tileCount: tiles.length,
                    maxLevel: levels.length ? Math.max(...levels) : -1,
                    entities: v.entities.values.length,
                    tilesLoaded: v.scene.globe.tilesLoaded
                };
            })()`,
            returnByValue: true
        });
        console.log(`[QUICK] Sec ${s}:`, JSON.stringify(st.result.value));
    }

    // Scroll to #cesiumContainer
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(2000);

    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_real_terrain_render.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[QUICK] Saved cesium_real_terrain_render.png');

    console.log('[QUICK] Selecting EVT-MEG-012...');
    await send('Runtime.evaluate', { expression: `selectHotspot('EVT-MEG-012')` });
    await sleep(4000);

    const targetPos = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return null;
            const t = v.entities.values.find(e => e.name && e.name.includes('EVT-MEG-012'));
            if (!t) return { notFound: true };
            const pos = t.position.getValue(Cesium.JulianDate.now());
            const winPos = Cesium.SceneTransforms.wgs84ToWindowCoordinates(v.scene, pos);
            return {
                name: t.name,
                winPos: winPos ? { x: Math.round(winPos.x), y: Math.round(winPos.y) } : null,
                canvasWidth: v.canvas.width,
                canvasHeight: v.canvas.height
            };
        })()`,
        returnByValue: true
    });
    console.log('[QUICK] Target hotspot position:', JSON.stringify(targetPos.result.value));

    const ss2 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'cesium_hotspot_closeup_render.png'), Buffer.from(ss2.data, 'base64'));
    console.log('[QUICK] Saved cesium_hotspot_closeup_render.png');

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
