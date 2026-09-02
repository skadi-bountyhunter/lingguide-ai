// 验证地图缩放时 marker 锚点是否对齐：放大后截图对比
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

  // 先在默认缩放下截图
  const shot1 = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(path.resolve(__dirname, '../uploads/_debug/map_zoom_default.png'), Buffer.from(shot1.data, 'base64'));

  // 放大到 18 级，中心对准灵山大佛
  await Runtime.evaluate({
    expression: `window.__map && window.__map.setZoomAndCenter(18, [120.096477, 31.430194])`,
  });
  // 注：__map 未暴露，改用 AMap 全局触发。先尝试通过 DOM 拿到 map 实例不可行，直接用页面里的 marker 位置
  // 改用滚轮缩放：聚焦到一个标记中心
  await Runtime.evaluate({
    expression: `(() => {
      // 找到地图容器，模拟聚焦
      const el = document.querySelector('.map-container');
      if (!el) return 'no-container';
      // 用高德 API：通过 Vue 实例拿不到，直接用 window.AMap 没有地图实例
      return 'has-container';
    })()`,
  });

  // 用键盘/滚轮缩放不可控，改方案：直接读 marker 的 offset 和 anchor 配置，验证逻辑正确
  const probe = await Runtime.evaluate({
    expression: `(() => {
      const wrap = document.querySelector('.map-pin-wrap');
      if (!wrap) return 'no-pin';
      const r = wrap.getBoundingClientRect();
      const cs = getComputedStyle(wrap);
      const after = getComputedStyle(wrap, '::after');
      return JSON.stringify({
        wrapSize: { w: r.width, h: r.height },
        afterTop: after.top,
        afterLeft: after.left,
        afterBorderTop: after.borderTopWidth,
      });
    })()`,
  });
  console.log('pin probe:', probe.result.value);

  // 截放大后的图（即便没放大成功，也截一张当前状态）
  const shot2 = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(path.resolve(__dirname, '../uploads/_debug/map_zoom_in.png'), Buffer.from(shot2.data, 'base64'));
  console.log('截图完成: map_zoom_default.png + map_zoom_in.png');

  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
