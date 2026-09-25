const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9305;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_check_err_' + Date.now());

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
        'about:blank'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        try {
            const list = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            const p = list.find(t => t.type === 'page');
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
        if (msg.method === 'Runtime.consoleAPICalled') {
            console.log(`[CONSOLE ${msg.params.type}]`, msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' '));
        }
        if (msg.method === 'Runtime.exceptionThrown') {
            const d = msg.params.exceptionDetails;
            console.log(`[EXCEPTION at line ${d.lineNumber}:${d.columnNumber}]`, d.text, d.exception?.description || d.exception?.value);
        }
        if (msg.method === 'Log.entryAdded') {
            console.log(`[LOG ${msg.params.entry.level}]`, msg.params.entry.text);
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
    await send('Log.enable');

    console.log('[DEBUG] Navigating to http://localhost:8000/ ...');
    await send('Page.navigate', { url: 'http://localhost:8000/' });

    await sleep(6000);

    const check = await send('Runtime.evaluate', {
        expression: `({
            hasCesium: typeof Cesium !== 'undefined',
            hasL: typeof L !== 'undefined',
            hasSwitchTo3D: typeof switchTo3D === 'function',
            scriptsCount: document.scripts.length
        })`,
        returnByValue: true
    });
    console.log('[DEBUG] Final state:', JSON.stringify(check.result.value));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
