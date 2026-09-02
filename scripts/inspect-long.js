// 长时间等待 SDK 完成模型下载，验证最终渲染效果
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

  // 注入 token
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 500));
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev')` });

  console.log('=== /chat (长时间等待) ===');
  await Page.navigate({ url: 'http://localhost:3000/chat' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2500));

  const click = await Runtime.evaluate({
    expression: `(() => {
      const btn = [...document.querySelectorAll('button')].find(b => /唤醒数字人|连接数字人/.test(b.textContent));
      if (btn) { btn.click(); return 'clicked'; }
      return 'no-btn at ' + location.href;
    })()`,
  });
  console.log(click.result.value);

  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });

  // 每 10s 抓一次，共 60s
  for (let i = 1; i <= 6; i++) {
    await new Promise(r => setTimeout(r, 10000));
    const probe = await Runtime.evaluate({
      expression: `(() => {
        const dl = document.querySelector('.xy-loading p, .xy-dl-bar');
        const ready = document.querySelector('.xy-overlay-bottom .xy-idle, .xy-overlay-bottom .xy-speak');
        const c = document.querySelector('canvas');
        return JSON.stringify({
          loadingText: dl ? dl.textContent : null,
          isReady: !!ready,
          canvasIntrinsic: c ? {w:c.width,h:c.height} : null,
          downloading: !!document.querySelector('.xy-dl-bar'),
        });
      })()`,
    });
    console.log(`+${i*10}s ->`, probe.result.value);

    if (i === 6 || i === 3) {
      const { data } = await Page.captureScreenshot({ format: 'png' });
      const fn = path.join(outDir, `chat-dh-t${i*10}.png`);
      fs.writeFileSync(fn, Buffer.from(data, 'base64'));
      console.log('截图:', fn);
    }
  }

  await client.close();
})();
