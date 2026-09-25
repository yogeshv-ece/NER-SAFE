const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9345;
const tempUserDataDir = path.join(os.tmpdir(), 'chrome_layers_' + Date.now());

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
        if (msg.method === 'Runtime.consoleAPICalled') {
            console.log('[BROWSER]', msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' '));
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
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    await sleep(4000);

    const report = await send('Runtime.evaluate', {
        expression: `(function() {
            const v = window.cesiumViewer;
            if (!v) return { noViewer: true };

            const layers = [];
            for (let i = 0; i < v.imageryLayers.length; i++) {
                const l = v.imageryLayers.get(i);
                layers.push({
                    index: i,
                    show: l.show,
                    alpha: l.alpha,
                    provider: l.imageryProvider ? l.imageryProvider.constructor.name : null,
                    ready: l.imageryProvider ? l.imageryProvider.ready : false,
                    url: l.imageryProvider && l.imageryProvider.url ? l.imageryProvider.url : null
                });
            }

            const roadSample = v.entities.values.filter(e => e.polyline).slice(0, 3).map(e => ({
                name: e.name,
                hasPositions: !!e.polyline.positions,
                clampToGround: e.polyline.clampToGround ? e.polyline.clampToGround.getValue() : null,
                width: e.polyline.width ? e.polyline.width.getValue() : null
            }));

            const buildingSample = v.entities.values.filter(e => e.polygon).slice(0, 3).map(e => ({
                name: e.name,
                hasHierarchy: !!e.polygon.hierarchy,
                extrudedHeight: e.polygon.extrudedHeight ? e.polygon.extrudedHeight.getValue() : null,
                heightRef: e.polygon.heightReference ? e.polygon.heightReference.getValue() : null
            }));

            const hotspotSample = v.entities.values.filter(e => e.isHotspotEntity).slice(0, 3).map(e => ({
                name: e.name,
                pos: e.position ? Cesium.Ellipsoid.WGS84.cartesianToCartographic(e.position.getValue(Cesium.JulianDate.now())) : null
            }));

            return {
                layers,
                entitiesTotal: v.entities.values.length,
                roadsCount: v.entities.values.filter(e => e.polyline).length,
                buildingsCount: v.entities.values.filter(e => e.polygon).length,
                hotspotsCount: v.entities.values.filter(e => e.isHotspotEntity).length,
                roadSample,
                buildingSample,
                hotspotSample
            };
        })()`,
        returnByValue: true
    });

    console.log('Cesium Layer & Entity Report:\n', JSON.stringify(report.result.value, null, 2));

    ws.close();
    chrome.kill();
    try { fs.rmSync(tempUserDataDir, { recursive: true, force: true }); } catch(e) {}
}

run().catch(console.error);
