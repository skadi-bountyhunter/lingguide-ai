// 验证 ChatView 数字人对话页：AI 回复后点「规划路线到地图」按钮，地图画出步行路线
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

  // 注入登录态
  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await sleep(500);
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token','dev')` });

  // 进对话页
  await Page.navigate({ url: 'http://localhost:3000/chat' });
  await Page.loadEventFired();
  await sleep(2500);

  // 探测初始状态
  const init = await Runtime.evaluate({
    expression: `(() => {
      const bubbles = document.querySelectorAll('.msg-bubble.assistant').length;
      const mapPanel = document.querySelector('.map-panel') ? 'visible' : 'hidden';
      const routeBtns = [...document.querySelectorAll('button')].filter(b => b.textContent.includes('规划路线到地图')).length;
      return JSON.stringify({ bubbles, mapPanel, routeBtns });
    })()`,
  });
  console.log('[init]', init.result.value);

  // 发送「推荐一条游览路线」
  const sendRes = await Runtime.evaluate({
    expression: `(() => {
      const inp = document.querySelector('.input-row input');
      if (!inp) return 'no-input';
      // 直接调 Vue：从 store 触发？简单做法：聚焦输入并模拟回车
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(inp, '推荐一条佛教文化的游览路线');
      inp.dispatchEvent(new Event('input', { bubbles: true }));
      return 'typed';
    })()`,
  });
  console.log('[type]', sendRes.result.value);

  await Runtime.evaluate({
    expression: `(() => {
      const inp = document.querySelector('.input-row input');
      inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      return 'enter-sent';
    })()`,
  });

  // 等 WS 流式回复完成（llm_done）
  let replied = false;
  for (let i = 1; i <= 12; i++) {
    await sleep(2000);
    const st = await Runtime.evaluate({
      expression: `(() => {
        const bubbles = document.querySelectorAll('.msg-bubble.assistant');
        const last = bubbles[bubbles.length - 1];
        const text = last ? last.querySelector('.bubble-text')?.textContent?.length || 0 : 0;
        const routeBtns = [...document.querySelectorAll('button')].filter(b => b.textContent.includes('规划路线到地图')).length;
        return JSON.stringify({ bubbles: bubbles.length, lastLen: text, routeBtns });
      })()`,
    });
    const v = JSON.parse(st.result.value || '{}');
    console.log(`[reply t+${i*2}s]`, st.result.value);
    if (v.routeBtns > 0 && v.lastLen > 30) { replied = true; break; }
  }

  await Page.captureScreenshot({ format: 'png' }).then(({ data }) => {
    fs.writeFileSync(path.join(OUT, 'chat-01-replied.png'), Buffer.from(data, 'base64'));
  });

  if (!replied) { console.log('WARN: 回复未就绪'); }

  // 点最后一条 assistant 气泡的「规划路线到地图」按钮
  const clickRoute = await Runtime.evaluate({
    expression: `(() => {
      const btns = [...document.querySelectorAll('button')].filter(b => b.textContent.includes('规划路线到地图'));
      if (!btns.length) return 'no-route-btn';
      const lastBtn = btns[btns.length - 1];
      lastBtn.click();
      return 'clicked last route-btn, total=' + btns.length;
    })()`,
  });
  console.log('[click route]', clickRoute.result.value);

  // 等后端 /api/chat/route 返回 + ScenicMap 画线
  for (let i = 1; i <= 10; i++) {
    await sleep(2000);
    const st = await Runtime.evaluate({
      expression: `(() => {
        const mapPanel = document.querySelector('.map-panel') ? 'visible' : 'hidden';
        const status = document.querySelector('.route-status')?.textContent || '';
        const svgPaths = document.querySelectorAll('svg path, svg polyline').length;
        const mpTitle = document.querySelector('.mp-title')?.textContent || '';
        return JSON.stringify({ mapPanel, status, svgPaths, mpTitle });
      })()`,
    });
    const v = JSON.parse(st.result.value || '{}');
    console.log(`[map t+${i*2}s]`, st.result.value);
    if (v.mapPanel === 'visible' && /已生成|显示直线|规划失败|匹配/.test(v.status)) break;
  }

  await Page.captureScreenshot({ format: 'png' }).then(({ data }) => {
    fs.writeFileSync(path.join(OUT, 'chat-02-route-map.png'), Buffer.from(data, 'base64'));
  });

  console.log('DONE. screenshots in', OUT);
  await client.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });