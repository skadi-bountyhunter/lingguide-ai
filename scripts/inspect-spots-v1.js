// scripts/inspect-spots-v1.js - 验证景点前后端打通
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
  await Emulation.setDeviceMetricsOverride({
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  const outDir = path.resolve(__dirname, 'uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });

  // 1. 游客端首页
  console.log('=== 1. 游客端首页 ===');
  await Page.navigate({ url: 'http://localhost:3003/' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2500));

  // 检查景点数量
  const homeProbe = await Runtime.evaluate({
    expression: `(() => {
      const cards = document.querySelectorAll('.spot-card');
      return { cards: cards.length, secCount: document.querySelector('.sec-count')?.textContent }
    })()`,
  });
  console.log('首页景点卡片:', homeProbe.result.value);

  const out1 = path.join(outDir, 'home.png');
  const { data: d1 } = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(out1, Buffer.from(d1, 'base64'));
  console.log('截图:', out1);

  // 2. 管理端景点管理
  console.log('=== 2. 管理端景点管理 ===');
  await Page.navigate({ url: 'http://localhost:3001/spots' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2500));

  const adminProbe = await Runtime.evaluate({
    expression: `(() => {
      const rows = document.querySelectorAll('tbody tr');
      return { rows: rows.length, firstCell: rows[0]?.querySelector('td:nth-child(2)')?.textContent }
    })()`,
  });
  console.log('管理端景点表格:', adminProbe.result.value);

  const out2 = path.join(outDir, 'admin-spots.png');
  const { data: d2 } = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(out2, Buffer.from(d2, 'base64'));
  console.log('截图:', out2);

  // 3. 景点详情
  console.log('=== 3. 景点详情 ===');
  await Page.navigate({ url: 'http://localhost:3003/spot/灵山大佛' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 3000));

  const detailProbe = await Runtime.evaluate({
    expression: `(() => {
      const h1 = document.querySelector('h1');
      const para = document.querySelectorAll('.desc-para');
      const hl = document.querySelectorAll('.highlight-item');
      return {
        name: h1?.textContent,
        paras: para.length,
        highlights: hl.length,
      }
    })()`,
  });
  console.log('详情数据:', detailProbe.result.value);

  const out3 = path.join(outDir, 'detail.png');
  const { data: d3 } = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(out3, Buffer.from(d3, 'base64'));
  console.log('截图:', out3);

  console.log('=== 完成 ===');
  await client.close();
})();
