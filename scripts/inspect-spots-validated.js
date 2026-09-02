// scripts/inspect-spots-validated.js - 端到端验证景点前后端打通（端口已修正）
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

(async () => {
  // 检查 CDP 健康
  try {
    await require('http').get('http://localhost:9222/json/version', (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => console.log('CDP 健康:', JSON.parse(d). Browser?.slice(0, 20)));
    });
  } catch (e) {
    throw new Error('CDP 未启动: 先运行 chrome --remote-debugging-port=9222');
  }

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

  const outDir = path.resolve(__dirname, '..', 'uploads', '_debug');
  fs.mkdirSync(outDir, { recursive: true });

  let passed = 0, failed = 0;
  function check(name, ok) {
    if (ok) { console.log(`  ✅ ${name}`); passed++; }
    else { console.log(`  ❌ ${name}`); failed++; }
  }
  function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ===== 1. 游客端首页 =====
  console.log('\n=== 1. 游客端首页 (localhost:3000) ===');
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await wait(3000);

  const homeProbe = await Runtime.evaluate({
    expression: `(() => {
      const cards = document.querySelectorAll('.spot-card');
      const cnt = document.querySelector('.sec-count');
      return { cards: cards.length, countText: cnt?.textContent, firstCard: cards[0]?.textContent?.slice(0, 20) }
    })()`,
    returnByValue: true,
  });
  check('景点卡片 >= 1', homeProbe.result.value.cards >= 1);
  check('section count 显示', homeProbe.result.value.countText?.includes('处'));
  check('第一条卡片有内容', !!homeProbe.result.value.firstCard);

  fs.writeFileSync(path.join(outDir, 'home_spots.png'), Buffer.from(await (await Page.captureScreenshot()).data, 'base64'));
  console.log('  截图: uploads/_debug/home_spots.png');

  // ===== 2. 管理端景点管理页 =====
  console.log('\n=== 2. 管理端景点管理 (localhost:3001/spots) ===');
  await Page.navigate({ url: 'http://localhost:3001/spots' });
  await Page.loadEventFired();
  await wait(3000);

  const adminProbe = await Runtime.evaluate({
    expression: `(() => {
      const rows = document.querySelectorAll('.el-table__row');
      return {
        rows: rows.length,
        name: rows[0]?.querySelector('td:nth-child(3)')?.textContent?.trim(),
        duration: rows[0]?.querySelector('td:nth-child(4)')?.textContent?.trim(),
      }
    })()`,
    returnByValue: true,
  });
  check('景点表格行数 >= 1', adminProbe.result.value.rows >= 1);
  check('第一行名称非空', !!adminProbe.result.value.name);

  fs.writeFileSync(path.join(outDir, 'admin_spots.png'), Buffer.from(await (await Page.captureScreenshot()).data, 'base64'));
  console.log('  截图: uploads/_debug/admin_spots.png');

  // ===== 3. 游客端景点详情 =====
  console.log('\n=== 3. 游客端景点详情 (localhost:3000/spot/灵山大佛) ===');
  await Page.navigate({ url: 'http://localhost:3000/spot/%E7%81%B5%E5%B1%B1%E5%A4%A7%E4%BD%9B' });
  await Page.loadEventFired();
  await wait(4000);

  const detailProbe = await Runtime.evaluate({
    expression: `(() => {
      const h1 = document.querySelector('h1');
      const highlights = document.querySelectorAll('.highlight-item');
      const tips = document.querySelectorAll('.tip-row');
      const qi = document.querySelectorAll('.qi-item');
      return {
        name: h1?.textContent?.trim(),
        highlights: highlights.length,
        tips: tips.length,
        quickInfoItems: qi.length,
        notFound: !!document.querySelector('.empty-state'),
      }
    })()`,
    returnByValue: true,
  });
  check('详情页标题 = 灵山大佛', detailProbe.result.value.name === '灵山大佛');
  check('亮点数量 > 0', detailProbe.result.value.highlights > 0);
  check('贴士数量 > 0', detailProbe.result.value.tips > 0);
  check('快捷信息栏 >= 3项', detailProbe.result.value.quickInfoItems >= 3);
  check('非空状态', !detailProbe.result.value.notFound);

  fs.writeFileSync(path.join(outDir, 'detail_lingshan.png'), Buffer.from(await (await Page.captureScreenshot()).data, 'base64'));
  console.log('  截图: uploads/_debug/detail_lingshan.png');

  // ===== 4. 404 页面 =====
  console.log('\n=== 4. 404 测试 (localhost:3000/spot/不存在的景点) ===');
  await Page.navigate({ url: 'http://localhost:3000/spot/%E4%B8%8D%E5%AD%98%E5%9C%A8%E7%9A%84%E6%99%AF%E7%82%B9' });
  await Page.loadEventFired();
  await wait(2000);

  const notFoundProbe = await Runtime.evaluate({
    expression: `(() => document.querySelector('.empty-state')?.textContent?.includes('不存在'))()`,
    returnByValue: true,
  });
  check('不存在的景点显示 404', notFoundProbe.result.value);

  fs.writeFileSync(path.join(outDir, '404_spot.png'), Buffer.from(await (await Page.captureScreenshot()).data, 'base64'));
  console.log('  截图: uploads/_debug/404_spot.png');

  // ===== 总结 =====
  console.log(`\n=== 总结: ${passed}✅ ${failed}❌ 共 ${passed+failed} 项 ===`);
  if (failed > 0) {
    process.exitCode = 1;
  }

  await client.close();
  console.log('\nDone. 退出码:', process.exitCode || 0);
})();
