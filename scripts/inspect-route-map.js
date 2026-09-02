const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target; check Chrome is running on :9222');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation, Log } = client;
  await Page.enable();
  await Runtime.enable();
  await Log.enable();
  const logs = [];
  Runtime.exceptionThrown(({ exceptionDetails }) => logs.push('EXCEPTION: ' + (exceptionDetails.text || exceptionDetails.exception?.description || '')));
  Log.entryAdded(({ entry }) => logs.push(`${entry.level}: ${entry.text}`));

  await Emulation.setDeviceMetricsOverride({ width: 430, height: 900, deviceScaleFactor: 1, mobile: true });
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await sleep(500);
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev')` });

  await Page.navigate({ url: 'http://localhost:3000/route' });
  await Page.loadEventFired();
  await sleep(6000);

  const before = await Runtime.evaluate({ expression: `(() => {
    const map = document.querySelector('.map-container');
    const canvas = document.querySelector('.amap-layer canvas, canvas');
    const weather = document.querySelector('.weather-card')?.innerText || '';
    const status = document.querySelector('.route-status')?.innerText || '';
    const markerCount = document.querySelectorAll('.map-pin-wrap').length;
    const buttons = [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(Boolean).slice(0,20);
    return JSON.stringify({
      url: location.href,
      mapRect: map ? (() => { const r = map.getBoundingClientRect(); return {w:Math.round(r.width), h:Math.round(r.height), x:Math.round(r.x), y:Math.round(r.y)} })() : null,
      canvas: canvas ? (() => { const r = canvas.getBoundingClientRect(); return {w:Math.round(r.width), h:Math.round(r.height), iw:canvas.width, ih:canvas.height} })() : null,
      weather,
      status,
      markerCount,
      buttons
    });
  })()` });
  console.log('before:', before.result.value);

  const click = await Runtime.evaluate({ expression: `(() => {
    const btn = [...document.querySelectorAll('button')].find(b => /在地图上查看路线/.test(b.textContent));
    if (btn) { btn.click(); return 'clicked preset/ai route button'; }
    const routeBtn = [...document.querySelectorAll('button')].find(b => /路线/.test(b.textContent));
    if (routeBtn) { routeBtn.click(); return 'clicked toolbar route button'; }
    return 'no route button';
  })()` });
  console.log('click:', click.result.value);
  await sleep(9000);

  const after = await Runtime.evaluate({ expression: `(() => {
    const polyline = document.querySelectorAll('svg path, .amap-overlay-text-container').length;
    const status = document.querySelector('.route-status')?.innerText || '';
    const markerCount = document.querySelectorAll('.map-pin-wrap').length;
    const mapText = document.querySelector('.scenic-map')?.innerText || '';
    return JSON.stringify({ status, markerCount, overlayCount: polyline, mapText });
  })()` });
  console.log('after:', after.result.value);

  const { data } = await Page.captureScreenshot({ format: 'png', captureBeyondViewport: true });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'route-map.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('logs:', JSON.stringify(logs.slice(-30), null, 2));
  console.log('截图:', outFile);
  await client.close();
})().catch(err => { console.error(err); process.exit(1); });
