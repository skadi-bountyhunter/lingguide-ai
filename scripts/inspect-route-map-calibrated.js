// 截图游客端路线页地图，确认景点标记位置
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Runtime.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  await Page.navigate({ url: 'http://localhost:3000/route' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 4000));

  // 探测地图标记数量
  const probe = await Runtime.evaluate({
    expression: `(() => {
      const pins = document.querySelectorAll('.map-pin-wrap');
      const canv = document.querySelector('.map-container canvas, .amap-maps');
      return JSON.stringify({ pins: pins.length, hasMap: !!canv, href: location.href });
    })()`,
  });
  console.log('probe:', probe.result.value);

  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'route_map_calibrated.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('截图:', outFile);

  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
