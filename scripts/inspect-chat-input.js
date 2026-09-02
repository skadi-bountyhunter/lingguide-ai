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

  // 收集控制台日志和错误
  const consoleLogs = [];
  const jsErrors = [];
  Runtime.consoleAPICalled(({ type, args }) => {
    const text = args.map(a => a.value || a.description || '').join(' ');
    consoleLogs.push(`[${type}] ${text}`);
  });
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    const msg = exceptionDetails.text || exceptionDetails.exception?.description || 'unknown';
    jsErrors.push(msg);
  });

  // 注入登录态
  await Page.navigate({ url: 'http://localhost:3000' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 500));
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev')` });

  // 跳转对话页
  await Page.navigate({ url: 'http://localhost:3000/chat' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 3000));

  // 检查输入框是否可见/可用
  const inputProbe = await Runtime.evaluate({
    expression: `(() => {
      const input = document.querySelector('input[type="text"]');
      if (!input) return 'no input found';
      const r = input.getBoundingClientRect();
      const cs = getComputedStyle(input);
      return JSON.stringify({
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        disabled: input.disabled,
        display: cs.display,
        visibility: cs.visibility,
        pointerEvents: cs.pointerEvents,
        zIndex: cs.zIndex,
        placeholder: input.placeholder,
      });
    })()`,
  });
  console.log('input probe:', inputProbe.result.value);

  // 检查发送按钮
  const sendBtnProbe = await Runtime.evaluate({
    expression: `(() => {
      const btns = document.querySelectorAll('.send-btn');
      if (!btns.length) return 'no send button';
      const btn = btns[0];
      const r = btn.getBoundingClientRect();
      const cs = getComputedStyle(btn);
      return JSON.stringify({
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        disabled: btn.disabled,
        display: cs.display,
        visibility: cs.visibility,
      });
    })()`,
  });
  console.log('send btn:', sendBtnProbe.result.value);

  // 检查语音按钮
  const voiceBtnProbe = await Runtime.evaluate({
    expression: `(() => {
      const btns = document.querySelectorAll('.voice-btn');
      if (!btns.length) return 'no voice button';
      const btn = btns[0];
      const r = btn.getBoundingClientRect();
      const cs = getComputedStyle(btn);
      return JSON.stringify({
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        display: cs.display,
        visibility: cs.visibility,
        pointerEvents: cs.pointerEvents,
      });
    })()`,
  });
  console.log('voice btn:', voiceBtnProbe.result.value);

  // 检查是否有元素遮挡输入框
  const overlapCheck = await Runtime.evaluate({
    expression: `(() => {
      const input = document.querySelector('input[type="text"]');
      if (!input) return 'no input';
      const r = input.getBoundingClientRect();
      const cx = r.x + r.width / 2;
      const cy = r.y + r.height / 2;
      const topEl = document.elementFromPoint(cx, cy);
      return JSON.stringify({
        inputTag: input.tagName,
        topElement: topEl ? topEl.tagName + (topEl.className ? '.' + topEl.className.split(' ')[0] : '') : 'null',
        isSameElement: topEl === input,
      });
    })()`,
  });
  console.log('overlap check:', overlapCheck.result.value);

  // 检查布局面板尺寸
  const layoutProbe = await Runtime.evaluate({
    expression: `(() => {
      const dhPanel = document.querySelector('.dh-panel');
      const chatPanel = document.querySelector('.chat-panel');
      const inputBar = document.querySelector('.input-bar');
      const result = {};
      if (dhPanel) {
        const r = dhPanel.getBoundingClientRect();
        result.dhPanel = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
      }
      if (chatPanel) {
        const r = chatPanel.getBoundingClientRect();
        result.chatPanel = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
      }
      if (inputBar) {
        const r = inputBar.getBoundingClientRect();
        result.inputBar = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
      }
      return JSON.stringify(result);
    })()`,
  });
  console.log('layout:', layoutProbe.result.value);

  // 打印收集到的 JS 错误
  if (jsErrors.length) {
    console.log('\n=== JS ERRORS ===');
    jsErrors.forEach(e => console.log(e));
  } else {
    console.log('\n=== No JS errors ===');
  }

  // 打印控制台日志
  if (consoleLogs.length) {
    console.log('\n=== Console Logs ===');
    consoleLogs.forEach(l => console.log(l));
  }

  // 截屏
  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'chat-debug.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('\nscreenshot:', outFile);

  await client.close();
})();
