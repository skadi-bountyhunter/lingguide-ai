// 观察正式 /chat 页面的数字人 DOM 与样式
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

async function inspect(url, screenshotName, waitMs = 25000) {
  const targets = await CDP.List({ port: 9222 });
  let target = targets.find(t => t.type === 'page');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Runtime.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  // 注入测试 token
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 500));
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev-test-token')` });

  console.log(`\n===== ${url} =====`);
  await Page.navigate({ url });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2500));

  // 点击唤醒按钮
  const click = await Runtime.evaluate({
    expression: `(() => {
      const btns = [...document.querySelectorAll('button')];
      const btn = btns.find(b => /唤醒数字人|连接数字人/.test(b.textContent));
      if (btn) { btn.click(); return 'clicked: ' + btn.textContent; }
      return 'no-btn; current url: ' + location.href + '; btns: ' + btns.map(b=>b.textContent.trim()).slice(0,8).join('|');
    })()`,
  });
  console.log('click ->', click.result.value);

  // 每 5s 抽样一下 canvas 尺寸
  for (let i = 1; i <= Math.ceil(waitMs / 5000); i++) {
    await new Promise(r => setTimeout(r, 5000));
    const snap = await Runtime.evaluate({
      expression: `(() => {
        const c = document.querySelector('canvas');
        if (!c) return 'no canvas yet';
        const r = c.getBoundingClientRect();
        const cs = getComputedStyle(c);
        return JSON.stringify({
          t: ${i * 5},
          canvasIntrinsic: { w: c.width, h: c.height },
          rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
          cssWH: { w: cs.width, h: cs.height },
          parent: c.parentElement ? c.parentElement.id || c.parentElement.className.toString() : null,
        });
      })()`,
    });
    console.log(`+${i * 5}s ->`, snap.result.value);
  }

  // 截屏
  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, screenshotName);
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('截图:', outFile);

  // 检查 SDK 注入的 DOM 详细结构
  const { result } = await Runtime.evaluate({
    expression: `(() => {
      const root = document.querySelector('#xy-sdk-chat') || document.querySelector('#xy-sdk');
      if (!root) return JSON.stringify({error: 'no sdk root'});
      const stage = document.querySelector('.xy-stage') || document.querySelector('.dh3-stage');
      const stageRect = stage ? stage.getBoundingClientRect().toJSON() : null;
      const rootRect = root.getBoundingClientRect().toJSON();
      const list = [];
      root.querySelectorAll('*').forEach(el => {
        const cs = window.getComputedStyle(el);
        const r = el.getBoundingClientRect();
        list.push({
          tag: el.tagName,
          cls: (el.className||'').toString().substring(0,60),
          rect: {x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)},
          pos: cs.position,
          w: cs.width, h: cs.height,
          transform: cs.transform.substring(0, 40),
        });
      });
      return JSON.stringify({ stageRect, rootRect, sdkChildren: list }, null, 2);
    })()`,
    returnByValue: true,
  });
  console.log(result.value);
  await client.close();
}

(async () => {
  try {
    await inspect('http://localhost:3000/chat', 'chat-dh.png', 25000);
  } catch (e) {
    console.error(e);
    process.exit(1);
  }
})();
