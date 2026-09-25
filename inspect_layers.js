const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9256;
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
        if (msg.method === 'Runtime.consoleAPICalled') {
            console.log('[CONSOLE]', msg.params.type, msg.params.args.map(a => a.value || a.description).join(' '));
        }
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

    // Check imagery layers
    const layerInfo = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };
            const layers = v.imageryLayers;
            const res = [];
            for (let i = 0; i < layers.length; i++) {
                const l = layers.get(i);
                res.push({
                    show: l.show,
                    alpha: l.alpha,
                    ready: l._imageryProvider ? l._imageryProvider.ready : false,
                    url: l._imageryProvider ? l._imageryProvider.url : null
                });
            }
            return {
                layerCount: layers.length,
                layers: res,
                baseColor: v.scene.globe.baseColor ? v.scene.globe.baseColor.toCssColorString() : null
            };
        })()`,
        returnByValue: true
    });
    console.log('[INSPECT] Imagery Layers:', JSON.stringify(layerInfo.result.value, null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
