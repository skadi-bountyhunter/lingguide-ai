// 验证 /route 个性化路线在地图上的呈现
// 复用 :9222 已有 page target，避免新开标签
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve(__dirname, '../uploads/_debug');
fs.mkdirSync(OUT, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target on :9222');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Runtime.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  // 注入登录态（项目 token key=lingguide_token）
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await sleep(500);
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token','dev')` });

  // 目标页
  await Page.navigate({ url: 'http://localhost:3000/route' });
  await Page.loadEventFired();
  await sleep(3000);

  // 探测地图是否就绪：高德 canvas / .amap-maps
  const probeMap = await Runtime.evaluate({
    expression: `(() => {
      const c = document.querySelector('.amap-maps canvas, .amap-canvas, canvas');
      const pins = document.querySelectorAll('.map-pin-wrap');
      const status = document.querySelector('.route-status')?.textContent || '';
      return JSON.stringify({
        href: location.href,
        hasCanvas: !!document.querySelector('canvas'),
        pinCount: pins.length,
        status,
      });
    })()`,
  });
  console.log('[init map]', probeMap.result.value);

  await Page.captureScreenshot({ format: 'png' }).then(({ data }) => {
    fs.writeFileSync(path.join(OUT, 'route-01-initial.png'), Buffer.from(data, 'base64'));
  });

  // 场景1：点击预设路线第一个"在地图上查看路线"按钮
  const click1 = await Runtime.evaluate({
    expression: `(() => {
      const btns = [...document.querySelectorAll('button')].filter(b => b.textContent.includes('在地图上查看路线'));
      if (!btns.length) return 'no-show-on-map-btn';
      btns[0].click();
      return 'clicked preset #0, total=' + btns.length;
    })()`,
  });
  console.log('[click preset]', click1.result.value);

  // 等步行规划（分段，最多 ~8s 全失败兜底）
  for (let i = 1; i <= 6; i++) {
    await sleep(2000);
    const st = await Runtime.evaluate({
      expression: `document.querySelector('.route-status')?.textContent || ''`,
    });
    const status = st.result.value;
    if (/已生成|显示直线|规划失败|匹配到/.test(status)) {
      console.log(`[preset status t+${i * 2}s]`, status);
      break;
    }
    if (i % 2 === 0) console.log(`[preset status t+${i * 2}s]`, status);
  }

  // 探测路线是否画上
  const probeRoute = await Runtime.evaluate({
    expression: `(() => {
      // 高德 Polyline 渲染为 SVG path 或 canvas；查 DOM 中的 path / polyline
      const svgPaths = document.querySelectorAll('svg path, svg polyline').length;
      const canvasCount = document.querySelectorAll('canvas').length;
      const status = document.querySelector('.route-status')?.textContent || '';
      // 读组件 expose 的 activeRoute 与 spots 坐标匹配情况
      const active = document.querySelector('[class*="route-page"]')?.__vue_app__ ? '' : '';
      return JSON.stringify({ svgPaths, canvasCount, status });
    })()`,
  });
  console.log('[preset probe]', probeRoute.result.value);

  await Page.captureScreenshot({ format: 'png' }).then(({ data }) => {
    fs.writeFileSync(path.join(OUT, 'route-02-preset.png'), Buffer.from(data, 'base64'));
  });

  // 记录点击前 marker 数量、点击后 fitView 应聚焦途经点——通过当前 zoom/center 对比
  const view1 = await Runtime.evaluate({
    expression: `(() => {
      const m = document.querySelector('.amap-maps')?.parentElement;
      // 不可直接拿 map 实例，靠 route-status 文案 + 截图判断
      return '{}';
    })()`,
  });

  // 场景2：AI 智能规划
  // 选 1 个兴趣（佛教文化）+ 半天
  const pickInterest = await Runtime.evaluate({
    expression: `(() => {
      const tagBtns = [...document.querySelectorAll('.tag-group button')];
      // 点第一个兴趣
      if (tagBtns[0]) tagBtns[0].click();
      return tagBtns[0]?.textContent || 'no-tag';
    })()`,
  });
  console.log('[pick interest]', pickInterest.result.value);

  // 点 AI 规划按钮
  const planClick = await Runtime.evaluate({
    expression: `(() => {
      const btn = [...document.querySelectorAll('button')].find(b => /AI 智能规划|规划中/.test(b.textContent));
      if (!btn) return 'no-plan-btn';
      if (btn.disabled) return 'plan-btn-disabled';
      btn.click();
      return 'clicked plan';
    })()`,
  });
  console.log('[click plan]', planClick.result.value);

  // 等 LLM 返回（deepseek 约 6-12s）+ watch 触发画线
  for (let i = 1; i <= 10; i++) {
    await sleep(2000);
    const st = await Runtime.evaluate({
      expression: `(() => {
        const aiRes = document.querySelector('.ai-result');
        const status = document.querySelector('.route-status')?.textContent || '';
        const aiSpots = document.querySelectorAll('.ai-result .rc-spots span').length;
        return JSON.stringify({ hasAi: !!aiRes, aiSpots, status });
      })()`,
    });
    const v = JSON.parse(st.result.value || '{}');
    console.log(`[ai t+${i * 2}s]`, st.result.value);
    if (v.aiSpots > 0 && /已生成|直线|失败|匹配/.test(v.status)) break;
  }

  await Page.captureScreenshot({ format: 'png' }).then(({ data }) => {
    fs.writeFileSync(path.join(OUT, 'route-03-ai.png'), Buffer.from(data, 'base64'));
  });

  console.log('DONE. screenshots in', OUT);
  await client.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });