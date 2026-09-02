// scripts/inspect-weather-card.js — 验证路线页天气卡片渲染
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Runtime.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  // 先到首页注入登录态
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 400));
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token','dev')` });

  // 跳路线页
  await Page.navigate({ url: 'http://localhost:3000/route' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 3500));

  // 探测天气卡片
  const probe = await Runtime.evaluate({
    expression: `(() => {
      const wc = document.querySelector('.weather-card');
      if (!wc) return 'NO weather-card';
      const rect = wc.getBoundingClientRect();
      // 读取关键文本
      const temp = document.querySelector('.wc-temp')?.textContent;
      const desc = document.querySelector('.wc-desc')?.textContent;
      const place = document.querySelector('.wc-place')?.textContent;
      const fcs = [...document.querySelectorAll('.fc-day')].map(d => d.textContent.replace(/\\s+/g,' ').trim());
      const cs = getComputedStyle(wc);
      return JSON.stringify({
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        bg: cs.backgroundImage.slice(0,60),
        temp, desc, place,
        forecastCount: fcs.length,
        forecast: fcs,
      }, null, 1);
    })()`,
  });
  console.log('probe:', probe.result.value);

  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'weather-card.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('截图:', outFile);

  await client.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });