const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9288;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_debug_' + Date.now());

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

        if (msg.method === 'Runtime.consoleAPICalled') {
            const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            console.log(`[BROWSER ${msg.params.type.toUpperCase()}]`, text);
        }

        if (msg.method === 'Runtime.exceptionThrown') {
            console.log('[EXCEPTION]', JSON.stringify(msg.params.exceptionDetails));
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

    console.log('[TEST] Waiting 4s for dashboard...');
    await sleep(4000);

    console.log('[TEST] Checking Cesium definition...');
    const checkCesium = await send('Runtime.evaluate', {
        expression: '({ cesiumType: typeof Cesium, isWebGL: typeof isWebGLSupported === "function" ? isWebGLSupported() : "unknown" })',
        returnByValue: true
    });
    console.log('[TEST] Cesium check:', JSON.stringify(checkCesium.result.value));

    console.log('[TEST] Calling switchTo3D()...');
    const switchRes = await send('Runtime.evaluate', {
        expression: `(function() {
            try {
                switchTo3D();
                return {
                    success: true,
                    viewerExists: !!window.cesiumViewer,
                    isDestroyed: window.cesiumViewer ? window.cesiumViewer.isDestroyed() : null,
                    cesiumInitialized: window.cesiumInitialized,
                    entities: window.cesiumViewer ? window.cesiumViewer.entities.values.length : 0
                };
            } catch (e) {
                return { success: false, error: e.toString(), stack: e.stack };
            }
        })()`,
        returnByValue: true
    });
    console.log('[TEST] Switch result:', JSON.stringify(switchRes.result.value, null, 2));

    await sleep(3000);

    const globeCheck = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };
            return {
                globe: !!v.scene.globe,
                surface: !!v.scene.globe._surface,
                tilesToRender: v.scene.globe._surface ? v.scene.globe._surface._tilesToRender.length : -1,
                tilesLoaded: v.scene.globe.tilesLoaded,
                entities: v.entities.values.length,
                canvasWidth: v.canvas.width,
                canvasHeight: v.canvas.height
            };
        })()`,
        returnByValue: true
    });
    console.log('[TEST] Globe check:', JSON.stringify(globeCheck.result.value, null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
