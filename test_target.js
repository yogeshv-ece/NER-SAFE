const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9299;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_check_page_' + Date.now());

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
    let targets = [];
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            targets = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            const p = targets.find(t => t.type === 'page' && t.url.includes('localhost:8000'));
            if (p && p.webSocketDebuggerUrl) {
                wsUrl = p.webSocketDebuggerUrl;
                break;
            }
        } catch (e) {}
    }

    console.log('Targets:', JSON.stringify(targets.map(t => ({ type: t.type, url: t.url }))));
    console.log('Connected wsUrl target:', wsUrl);

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
            console.log('[CONSOLE]', msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' '));
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

    await sleep(4000);

    const info = await send('Runtime.evaluate', {
        expression: `({
            url: window.location.href,
            title: document.title,
            hasCesium: typeof Cesium !== 'undefined',
            hasSwitchTo3D: typeof switchTo3D === 'function',
            hasViewer: !!window.cesiumViewer
        })`,
        returnByValue: true
    });
    console.log('Page info:', JSON.stringify(info.result.value));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
