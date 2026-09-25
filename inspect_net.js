const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9257;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_net_' + Date.now());

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

    const networkRequests = []; const reqMap = new Map();
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Network.requestWillBeSent') { reqMap.set(msg.params.requestId, msg.params.request.url); }
if (msg.method === 'Network.responseReceived') {
            const resp = msg.params.response;
            if (resp.url.includes('/api/gis/') || resp.url.includes('tile') || resp.url.includes('openstreetmap')) {
                networkRequests.push({ url: resp.url.substring(0, 100), status: resp.status, mimeType: resp.mimeType });
            }
        }
        if (msg.method === 'Network.loadingFailed') {
            networkRequests.push({ requestId: msg.params.requestId, error: msg.params.errorText });
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
    await send('Network.enable');

    await sleep(4000);
    console.log('[NET] Switching to 3D...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    await sleep(6000);

    console.log('[NET] Captured requests:', networkRequests.length);
    console.log(JSON.stringify(networkRequests.slice(25).map(r => ({ url: reqMap.get(r.requestId) || r.url, status: r.status, error: r.error })), null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
