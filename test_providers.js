const http = require('http');
const { spawn } = require('child_process');

async function run() {
  const chrome = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
    '--remote-debugging-port=9242',
    '--headless=new',
    '--enable-webgl',
    '--user-data-dir=C:\\Users\\hp\\AppData\\Local\\Temp\\chrome_dev_user_dir',
    'http://localhost:8000/'
  ]);

  await new Promise(r => setTimeout(r, 2000));
  const list = await new Promise(res => http.get('http://127.0.0.1:9242/json', r => {
    let d = ''; r.on('data', c => d += c); r.on('end', () => res(JSON.parse(d)));
  }));
  const ws = new WebSocket(list[0].webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  function send(method, params) {
    return new Promise(r => {
      const id = Math.random();
      const h = e => {
        const m = JSON.parse(e.data);
        if (m.id === id) { ws.removeEventListener('message', h); r(m.result); }
      };
      ws.addEventListener('message', h);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  await send('Runtime.enable');
  await new Promise(r => setTimeout(r, 2000));

  const test1 = await send('Runtime.evaluate', {
    expression: `
      (function() {
        const results = {};
        try {
          const p = new Cesium.UrlTemplateImageryProvider({ url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png' });
          const l = new Cesium.ImageryLayer(p);
          results.urlTemplate = 'OK: ' + (l instanceof Cesium.ImageryLayer);
        } catch(e) {
          results.urlTemplate = 'ERR: ' + e.toString();
        }

        try {
          const osm = new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' });
          results.openStreetMap = 'OK: ' + (osm instanceof Cesium.ImageryProvider);
        } catch(e) {
          results.openStreetMap = 'ERR: ' + e.toString();
        }

        try {
          const hm = new Cesium.CustomHeightmapTerrainProvider({
            width: 65,
            height: 65,
            tilingScheme: new Cesium.GeographicTilingScheme(),
            callback: function(x, y, level) { return new Float32Array(65 * 65); }
          });
          results.heightmap = 'OK: ' + (hm instanceof Cesium.TerrainProvider);
        } catch(e) {
          results.heightmap = 'ERR: ' + e.toString();
        }

        return results;
      })()
    `,
    returnByValue: true
  });

  console.log('CESIUM PROVIDERS TEST:', test1.result.value);
  ws.close();
  chrome.kill();
}
run();
