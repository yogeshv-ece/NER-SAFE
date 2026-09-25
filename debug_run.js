const { spawn } = require('child_process');
const http = require('http');

async function main() {
    const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--remote-debugging-port=9234', '--headless=new', '--enable-webgl', 'http://localhost:8000/'
    ]);
    await new Promise(r => setTimeout(r, 2000));
    const list = await new Promise(res => http.get('http://127.0.0.1:9234/json', r => {
        let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
    }));
    const ws = new WebSocket(list[0].webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);

    let id = 1;
    function send(method, params) {
        return new Promise(resolve => {
            const cur = id++;
            const h = e => {
                const m = JSON.parse(e.data);
                if (m.id === cur) { ws.removeEventListener('message', h); resolve(m.result); }
            };
            ws.addEventListener('message', h);
            ws.send(JSON.stringify({ id: cur, method, params }));
        });
    }

    await send('Runtime.enable');
    await new Promise(r => setTimeout(r, 2000));
    await send('Runtime.evaluate', { expression: 'switchTo3D()' });
    await new Promise(r => setTimeout(r, 2000));

    const test = await send('Runtime.evaluate', {
        expression: `
            (async function() {
                const logs = [];
                try {
                    const res = await fetch('/api/gis/roads?tier=major');
                    const geoJson = await res.json();
                    logs.push('Roads features: ' + geoJson.features.length);
                    let count = 0;
                    for (let feat of geoJson.features.slice(0, 10)) {
                        const geom = feat.geometry;
                        const p = feat.properties || {};
                        let lines = geom.type === 'LineString' ? [geom.coordinates] : geom.coordinates;
                        for (let line of lines) {
                            const flat = [];
                            line.forEach(pt => { flat.push(pt[0]); flat.push(pt[1]); });
                            const ent = cesiumViewer.entities.add({
                                name: 'Road: ' + (p.name || 'Corridor'),
                                polyline: {
                                    positions: Cesium.Cartesian3.fromDegreesArray(flat),
                                    clampToGround: true,
                                    width: 2.5,
                                    material: Cesium.Color.fromCssColorString('#F59E0B')
                                }
                            });
                            if (ent) count++;
                        }
                    }
                    logs.push('Added roads: ' + count);
                } catch(err) {
                    logs.push('Roads error: ' + err.toString());
                }

                try {
                    const res = await fetch('/api/gis/buildings?limit=10');
                    const geoJson = await res.json();
                    logs.push('Buildings features: ' + geoJson.features.length);
                    let count = 0;
                    for (let feat of geoJson.features) {
                        const geom = feat.geometry;
                        const p = feat.properties || {};
                        let rings = geom.type === 'Polygon' ? geom.coordinates : geom.coordinates[0];
                        if (rings && rings.length > 0) {
                            const extRing = rings[0];
                            const flat = [];
                            extRing.forEach(pt => { flat.push(pt[0]); flat.push(pt[1]); });
                            const ent = cesiumViewer.entities.add({
                                name: 'Building',
                                polygon: {
                                    hierarchy: Cesium.Cartesian3.fromDegreesArray(flat),
                                    height: 0,
                                    heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
                                    extrudedHeight: 10.0,
                                    extrudedHeightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
                                    material: Cesium.Color.fromCssColorString('#94A3B8').withAlpha(0.75)
                                }
                            });
                            if (ent) count++;
                        }
                    }
                    logs.push('Added buildings: ' + count);
                } catch(err) {
                    logs.push('Buildings error: ' + err.toString());
                }

                return logs;
            })()
        `,
        awaitPromise: true,
        returnByValue: true
    });

    console.log('DEBUG RUN LOGS:', test.result.value);
    ws.close();
    chrome.kill();
}
main();
