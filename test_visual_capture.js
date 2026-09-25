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

async function run() {
    const tmpDir = path.join(os.tmpdir(), 'chrome_vis_' + Date.now());
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9275',
        '--user-data-dir=' + tmpDir,
        '--headless=new',
        '--enable-webgl',
        '--window-size=1600,1050',
        'http://localhost:8000/'
    ]);
    
    let wsUrl = null;
    for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 400));
        try {
            const list = await getJson('http://127.0.0.1:9275/json');
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
    await send('Page.enable');
    
    // Wait for page
    console.log('[TEST] Waiting 4s for dashboard...');
    await new Promise(r => setTimeout(r, 4000));
    
    // Switch to 3D
    console.log('[TEST] Calling switchTo3D()...');
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    
    // Wait 5 seconds
    await new Promise(r => setTimeout(r, 5000));
    
    // Scroll #cesiumContainer into view
    console.log('[TEST] Scrolling #cesiumContainer into view...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ block: 'center' })`
    });
    await new Promise(r => setTimeout(r, 1000));
    
    // Capture screenshot
    console.log('[TEST] Capturing screenshot of current 3D view...');
    const ss1 = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(__dirname, 'vis_test_current.png'), Buffer.from(ss1.data, 'base64'));
    console.log('[TEST] Saved vis_test_current.png');

    ws.close();
    chrome.kill();
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
