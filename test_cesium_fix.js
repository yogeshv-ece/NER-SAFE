const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9238;

async function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

async function run() {
    console.log('[TEST] Launching Chrome on http://localhost:8000/ ...');
    const chrome = spawn(CHROME_PATH, [
        `--remote-debugging-port=${DEBUG_PORT}`,
        '--headless=new',
        '--disable-gpu-sandbox',
        '--enable-webgl',
        '--window-size=1600,1000',
        '--no-first-run',
        'http://localhost:8000/'
    ], { stdio: 'ignore' });

    let wsUrl = null;
    for (let i = 0; i < 25; i++) {
        await sleep(500);
        try {
            const list = await new Promise((res, rej) => {
                http.get(`http://127.0.0.1:${DEBUG_PORT}/json`, r => {
                    let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
                }).on('error', rej);
            });
            if (list && list[0]?.webSocketDebuggerUrl) {
                wsUrl = list[0].webSocketDebuggerUrl;
                break;
            }
        } catch(e) {}
    }

    const ws = new WebSocket(wsUrl);
    await new Promise(r => ws.onopen = r);

    let id = 1;
    const tileRequests = [];
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Network.responseReceived') {
            const url = msg.params.response.url;
            if (url.includes('/api/gis/terrain/tile')) {
                tileRequests.push({ status: msg.params.response.status, url });
                console.log('[TILE RES]', msg.params.response.status, url);
            } else if (url.includes('openstreetmap.org')) {
                console.log('[OSM RES]', msg.params.response.status, url);
            }
        } else if (msg.method === 'Runtime.consoleAPICalled') {
            const text = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            console.log('[CONSOLE]', text);
        }
    };

    function send(method, params = {}) {
        const curId = id++;
        return new Promise(resolve => {
            const h = e => {
                const m = JSON.parse(e.data);
                if (m.id === curId) { ws.removeEventListener('message', h); resolve(m.result); }
            };
            ws.addEventListener('message', h);
            ws.send(JSON.stringify({ id: curId, method, params }));
        });
    }

    await send('Runtime.enable');
    await send('Page.enable');
    await send('Network.enable');

    console.log('[TEST] Waiting 3s for page load...');
    await sleep(3000);

    // Apply runtime patch to verify Cesium fix in real Chrome
    console.log('[TEST] Applying Cesium runtime fixes in page...');
    const patchResult = await send('Runtime.evaluate', {
        expression: `
            (async function() {
                // 1. Destroy previous viewer if any
                if (window.cesiumViewer && !window.cesiumViewer.isDestroyed()) {
                    window.cesiumViewer.destroy();
                    window.cesiumViewer = null;
                }
                window.cesiumInitialized = false;

                // 2. Ensure container is visible and sized BEFORE creating viewer
                const cContainer = document.getElementById('cesiumContainer');
                const lMap = document.getElementById('liveMap');
                if (lMap) lMap.style.display = 'none';
                if (cContainer) {
                    cContainer.style.display = 'block';
                    cContainer.style.width = '100%';
                    cContainer.style.height = '100%';
                }

                // 3. Terrain Provider
                const srtmTerrainProvider = new Cesium.CustomHeightmapTerrainProvider({
                    width: 65,
                    height: 65,
                    tilingScheme: new Cesium.GeographicTilingScheme(),
                    callback: function (x, y, level) {
                        return fetch('/api/gis/terrain/tile?z=' + level + '&x=' + x + '&y=' + y + '&w=65&h=65')
                            .then(res => {
                                if (!res.ok) return new Float32Array(65 * 65);
                                return res.arrayBuffer();
                            })
                            .then(buf => new Float32Array(buf))
                            .catch(() => new Float32Array(65 * 65));
                    }
                });

                // 4. Base Imagery Provider (UrlTemplateImageryProvider)
                const baseImagery = new Cesium.ImageryLayer(new Cesium.UrlTemplateImageryProvider({
                    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    subdomains: ['a', 'b', 'c'],
                    maximumLevel: 19
                }));

                // 5. Create Viewer with baseLayer
                const viewer = new Cesium.Viewer('cesiumContainer', {
                    terrainProvider: srtmTerrainProvider,
                    baseLayer: baseImagery,
                    baseLayerPicker: false,
                    geocoder: false,
                    homeButton: false,
                    infoBox: true,
                    sceneModePicker: false,
                    selectionIndicator: true,
                    timeline: false,
                    animation: false,
                    navigationHelpButton: false,
                    fullscreenButton: false
                });
                window.cesiumViewer = viewer;
                window.is3DActive = true;
                window.cesiumInitialized = true;

                // 6. Scene & Globe settings
                viewer.scene.globe.enableLighting = false;
                viewer.scene.globe.depthTestAgainstTerrain = true;
                viewer.scene.globe.terrainExaggeration = 2.0;
                viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#1E3A8A');
                viewer.resize();

                // 7. Fly Camera to Shillong Plateau / East Khasi Hills (Meghalaya relief)
                viewer.camera.setView({
                    destination: Cesium.Cartesian3.fromDegrees(91.85, 25.40, 22000.0),
                    orientation: {
                        heading: Cesium.Math.toRadians(15.0),
                        pitch: Cesium.Math.toRadians(-32.0),
                        roll: 0.0
                    }
                });

                // 8. Add Live Hotspots
                if (window.hotspotsData && window.hotspotsData.features) {
                    populateCesiumHotspots(window.hotspotsData.features);
                }

                // 9. Add sample road and building
                viewer.entities.add({
                    name: 'Road: NH6 Shillong Arterial',
                    polyline: {
                        positions: Cesium.Cartesian3.fromDegreesArray([
                            91.82, 25.42,
                            91.85, 25.40,
                            91.89, 25.38
                        ]),
                        clampToGround: true,
                        width: 4.0,
                        material: Cesium.Color.fromCssColorString('#F59E0B')
                    }
                });

                viewer.entities.add({
                    name: 'Building: Shillong District HQ Complex',
                    polygon: {
                        hierarchy: Cesium.Cartesian3.fromDegreesArray([
                            91.848, 25.398,
                            91.852, 25.398,
                            91.852, 25.402,
                            91.848, 25.402
                        ]),
                        height: 0,
                        heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
                        extrudedHeight: 25.0,
                        extrudedHeightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
                        material: Cesium.Color.fromCssColorString('#E2E8F0'),
                        outline: true,
                        outlineColor: Cesium.Color.fromCssColorString('#0F172A')
                    }
                });

                return {
                    success: true,
                    imageryLayers: viewer.imageryLayers.length,
                    entities: viewer.entities.values.length,
                    canvasWidth: viewer.canvas.width,
                    canvasHeight: viewer.canvas.height
                };
            })()
        `,
        awaitPromise: true,
        returnByValue: true
    });

    console.log('[TEST] Patch Result:', JSON.stringify(patchResult.result.value, null, 2));

    console.log('[TEST] Waiting 6 seconds for tiles and frames to render...');
    await sleep(6000);

    // Scroll page to map container and capture screenshot
    console.log('[TEST] Scrolling to map container...');
    await send('Runtime.evaluate', {
        expression: `document.getElementById('cesiumContainer').scrollIntoView({ behavior: 'instant', block: 'center' })`
    });
    await sleep(1000);

    console.log('[TEST] Capturing screenshot of rendered 3D scene...');
    const screenshot = await send('Page.captureScreenshot', { format: 'png' });
    const buffer = Buffer.from(screenshot.data, 'base64');
    const screenshotPath = path.join(__dirname, 'cesium_fixed_screenshot.png');
    fs.writeFileSync(screenshotPath, buffer);
    console.log(`[TEST] Saved screenshot to ${screenshotPath} (${buffer.length} bytes)`);
    console.log(`[TEST] Total terrain tile requests captured: ${tileRequests.length}`);

    ws.close();
    chrome.kill();
}

run().catch(err => {
    console.error('[TEST] Error:', err);
    process.exit(1);
});
