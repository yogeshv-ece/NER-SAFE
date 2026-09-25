/**
 * Test exact entity creation for roads and buildings in Chrome
 */

const { spawn } = require('child_process');
const http = require('http');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DEBUG_PORT = 9230;

async function run() {
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
    for (let i = 0; i < 20; i++) {
        await new Promise(r => setTimeout(r, 500));
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
    function send(method, params = {}) {
        const curId = id++;
        return new Promise((resolve, reject) => {
            const handler = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.id === curId) {
                    ws.removeEventListener('message', handler);
                    if (msg.error) reject(msg.error);
                    else resolve(msg.result);
                }
            };
            ws.addEventListener('message', handler);
            ws.send(JSON.stringify({ id: curId, method, params }));
        });
    }

    await send('Runtime.enable');
    await send('Page.enable');

    console.log('Waiting 3s for page...');
    await new Promise(r => setTimeout(r, 3000));

    // Call switchTo3D()
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    console.log('Called switchTo3D(). Waiting 4s...');
    await new Promise(r => setTimeout(r, 4000));

    // Now test manually running loadCesiumRoads logic with error reporting
    const testResult = await send('Runtime.evaluate', {
        expression: `
            (async function() {
                const results = { roads: null, buildings: null, roadsLoadedFlag: cesiumRoadsLoaded, buildingsLoadedFlag: cesiumBuildingsLoaded };
                try {
                    const res = await fetch('/api/gis/roads?tier=major');
                    const json = await res.json();
                    results.roadsFetchCount = json.features.length;
                    let addedRoads = 0;
                    json.features.slice(0, 5).forEach(feat => {
                        const geom = feat.geometry;
                        const p = feat.properties || {};
                        let lines = geom.type === 'LineString' ? [geom.coordinates] : geom.coordinates;
                        lines.forEach(line => {
                            const flat = [];
                            line.forEach(pt => { flat.push(pt[0]); flat.push(pt[1]); });
                            const ent = cesiumViewer.entities.add({
                                name: 'Test Road',
                                polyline: {
                                    positions: Cesium.Cartesian3.fromDegreesArray(flat),
                                    clampToGround: true,
                                    width: 3.0,
                                    material: Cesium.Color.RED
                                }
                            });
                            if (ent) addedRoads++;
                        });
                    });
                    results.roads = { success: true, added: addedRoads };
                } catch(e) {
                    results.roads = { success: false, error: e.toString(), stack: e.stack };
                }

                try {
                    const res = await fetch('/api/gis/buildings?limit=10');
                    const json = await res.json();
                    results.bldgsFetchCount = json.features.length;
                    let addedBldgs = 0;
                    json.features.forEach(feat => {
                        const geom = feat.geometry;
                        const p = feat.properties || {};
                        let rings = geom.type === 'Polygon' ? geom.coordinates : geom.coordinates[0];
                        if (rings && rings.length > 0) {
                            const extRing = rings[0];
                            const flat = [];
                            extRing.forEach(pt => { flat.push(pt[0]); flat.push(pt[1]); });
                            const ent = cesiumViewer.entities.add({
                                name: 'Test Building',
                                polygon: {
                                    hierarchy: Cesium.Cartesian3.fromDegreesArray(flat),
                                    extrudedHeight: 10.0,
                                    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                                    extrudedHeightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
                                    material: Cesium.Color.BLUE
                                }
                            });
                            if (ent) addedBldgs++;
                        }
                    });
                    results.buildings = { success: true, added: addedBldgs };
                } catch(e) {
                    results.buildings = { success: false, error: e.toString(), stack: e.stack };
                }

                results.totalEntitiesNow = cesiumViewer.entities.values.length;
                return results;
            })()
        `,
        awaitPromise: true,
        returnByValue: true
    });

    console.log('Test entity creation result:', JSON.stringify(testResult.result.value, null, 2));
    ws.close();
    chrome.kill();
}
run();
