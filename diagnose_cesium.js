/**
 * NER-SAFE: Chrome CDP Diagnostics for Cesium 3D Terrain & Scene Rendering
 */

const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9228;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
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
    console.log('[CDP] Launching Chrome on http://localhost:8000/ ...');
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1600,1000',
        '--no-first-run',
        '--no-default-browser-check',
        'http://localhost:8000/'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 25; i++) {
        await sleep(500);
        try {
            const list = await getJson(`http://127.0.0.1:${DEBUG_PORT}/json`);
            if (list && list.length > 0) {
                const target = list.find(t => t.type === 'page' && t.url.includes('localhost:8000')) || list[0];
                if (target && target.webSocketDebuggerUrl) {
                    wsUrl = target.webSocketDebuggerUrl;
                    break;
                }
            }
        } catch (e) { }
    }

    if (!wsUrl) {
        console.error('[CDP] Failed to connect to Chrome debugging endpoint');
        chrome.kill();
        process.exit(1);
    }

    console.log('[CDP] Connected to Chrome page:', wsUrl);
    const ws = new WebSocket(wsUrl);

    let msgId = 1;
    const pending = new Map();

    function send(method, params = {}) {
        const id = msgId++;
        return new Promise((resolve, reject) => {
            pending.set(id, { resolve, reject });
            ws.send(JSON.stringify({ id, method, params }));
        });
    }

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && pending.has(msg.id)) {
            const { resolve, reject } = pending.get(msg.id);
            pending.delete(msg.id);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
        } else if (msg.method === 'Runtime.consoleAPICalled') {
            const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            console.log(`[BROWSER CONSOLE ${msg.params.type.toUpperCase()}]`, text);
        } else if (msg.method === 'Runtime.exceptionThrown') {
            console.error('[BROWSER EXCEPTION]', msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
        } else if (msg.method === 'Network.responseReceived') {
            const url = msg.params.response.url;
            if (url.includes('/api/gis/') || url.includes('openstreetmap') || url.includes('Cesium.js') || url.includes('leaflet')) {
                console.log('[BROWSER RES]', msg.params.response.status, url);
            }
        }
    };

    await new Promise(r => ws.onopen = r);

    await send('Page.enable');
    await send('Runtime.enable');
    await send('Network.enable');

    console.log('[CDP] Polling until document is ready and scripts load...');
    for (let i = 0; i < 30; i++) {
        await sleep(500);
        const evalRes = await send('Runtime.evaluate', {
            expression: `({
                readyState: document.readyState,
                title: document.title,
                hasL: typeof L !== 'undefined',
                hasCesium: typeof Cesium !== 'undefined',
                hasSwitchTo3D: typeof switchTo3D === 'function',
                hasHotspotsData: !!(window.hotspotsData && window.hotspotsData.features)
            })`,
            returnByValue: true
        });
        const v = evalRes.result.value;
        if (v && v.hasCesium && v.hasSwitchTo3D && v.hasHotspotsData) {
            console.log('[CDP] Page ready state reached:', v);
            break;
        }
    }

    console.log('[CDP] Triggering switchTo3D()...');
    const switchResult = await send('Runtime.evaluate', {
        expression: `
            (function() {
                try {
                    switchTo3D();
                    return { success: true, is3DActive: is3DActive, cesiumInitialized: cesiumInitialized };
                } catch(e) {
                    return { success: false, error: e.toString(), stack: e.stack };
                }
            })()
        `,
        returnByValue: true
    });
    console.log('[CDP] switchTo3D() returned:', switchResult.result.value);

    console.log('[CDP] Waiting 6 seconds for Cesium 3D scene, tiles, and entities to load...');
    await sleep(6000);

    // Inspect Cesium runtime state
    const cesiumState = await send('Runtime.evaluate', {
        expression: `
            (function() {
                if (typeof cesiumViewer === 'undefined' || !cesiumViewer) {
                    return { error: 'cesiumViewer is not defined' };
                }
                const scene = cesiumViewer.scene;
                const globe = scene.globe;
                const camera = cesiumViewer.camera;
                const carto = Cesium.Cartographic.fromCartesian(camera.position);

                const entities = cesiumViewer.entities.values;
                const hotspots = entities.filter(e => e.isHotspotEntity || (e.name && e.name.startsWith('EVT-')));
                const roads = entities.filter(e => e.polyline);
                const buildings = entities.filter(e => e.polygon);

                const imageryLayers = [];
                for (let i = 0; i < scene.imageryLayers.length; i++) {
                    const l = scene.imageryLayers.get(i);
                    imageryLayers.push({
                        show: l.show,
                        alpha: l.alpha,
                        isDestroyed: l.isDestroyed ? l.isDestroyed() : false
                    });
                }

                return {
                    isDestroyed: cesiumViewer.isDestroyed(),
                    containerDisplay: document.getElementById('cesiumContainer')?.style.display,
                    liveMapDisplay: document.getElementById('liveMap')?.style.display,
                    globe: {
                        show: globe.show,
                        enableLighting: globe.enableLighting,
                        depthTestAgainstTerrain: globe.depthTestAgainstTerrain,
                        terrainExaggeration: globe.terrainExaggeration,
                        hasTerrainProvider: !!cesiumViewer.terrainProvider
                    },
                    camera: {
                        lon: Cesium.Math.toDegrees(carto.longitude),
                        lat: Cesium.Math.toDegrees(carto.latitude),
                        height: carto.height,
                        heading: Cesium.Math.toDegrees(camera.heading),
                        pitch: Cesium.Math.toDegrees(camera.pitch),
                        roll: Cesium.Math.toDegrees(camera.roll)
                    },
                    imageryLayerCount: scene.imageryLayers.length,
                    imageryLayers: imageryLayers,
                    totalEntities: entities.length,
                    hotspotEntities: hotspots.length,
                    roadEntities: roads.length,
                    buildingEntities: buildings.length,
                    cesiumFallbackNoticeDisplay: document.getElementById('cesiumFallbackNotice')?.style.display
                };
            })()
        `,
        returnByValue: true
    });
    console.log('[CDP] Cesium Runtime State:', JSON.stringify(cesiumState.result.value, null, 2));

    // Capture screenshot
    console.log('[CDP] Capturing screenshot...');
    const screenshot = await send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(screenshot.data, 'base64');
    const screenshotPath = path.join(__dirname, 'cesium_diagnostics_screenshot.png');
    fs.writeFileSync(screenshotPath, buffer);
    console.log(`[CDP] Saved screenshot to ${screenshotPath} (${buffer.length} bytes)`);

    ws.close();
    chrome.kill();
    console.log('[CDP] Diagnostics complete.');
}

run().catch(err => {
    console.error('[CDP] Diagnostic error:', err);
    process.exit(1);
});
