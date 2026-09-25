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

async function testFetch() {
    const tmpDir = path.join(os.tmpdir(), 'chrome_f_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9272',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9272/json');
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
    await new Promise(r => setTimeout(r, 2000));
    
    const res = await send('Runtime.evaluate', {
        expression: `(async function() {
            try {
                const response = await fetch('/api/gis/terrain/tile?z=0&x=0&y=0');
                const buf = await response.arrayBuffer();
                const f32 = new Float32Array(buf);
                return {
                    status: response.status,
                    contentType: response.headers.get('content-type'),
                    byteLength: buf.byteLength,
                    f32Length: f32.length,
                    first5: Array.from(f32.slice(0, 5))
                };
            } catch(e) {
                return { error: e.toString() };
            }
        })()`,
        awaitPromise: true,
        returnByValue: true
    });
    console.log('Fetch Result:\n', JSON.stringify(res.result ? res.result.value : res, null, 2));
    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}
testFetch().catch(console.error);
