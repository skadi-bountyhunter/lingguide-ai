// 验证步行路线规划：点路线按钮，等规划完成，截图
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

  // 点"路线"按钮
  const click = await Runtime.evaluate({
    expression: `(() => {
      const b = [...document.querySelectorAll('button')].find(x => /路线/.test(x.textContent));
      if (!b) return 'no-btn';
      b.click();
      return 'clicked';
    })()`,
  });
  console.log('点击:', click.result.value);

  // 轮询等待 routeStatus 出现"已生成"或"失败"
  for (let i = 0; i < 24; i++) {
    await new Promise(r => setTimeout(r, 1500));
    const st = await Runtime.evaluate({ expression: `document.querySelector('.route-status')?.textContent || ''` });
    if (/已生成|失败|直线/.test(st.result.value)) {
      console.log('状态:', st.result.value);
      break;
    }
  }

  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'route_walking.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('截图:', outFile);

  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
