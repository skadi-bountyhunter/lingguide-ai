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

  const consoleLogs = [];
  const jsErrors = [];
  Runtime.consoleAPICalled(({ type, args }) => {
    const text = args.map(a => a.value || a.description || '').join(' ');
    consoleLogs.push(`[${type}] ${text}`);
  });
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    jsErrors.push(exceptionDetails.text || exceptionDetails.exception?.description || 'unknown');
  });

  // 注入登录态
  await Page.navigate({ url: 'http://localhost:3000' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 500));
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev')` });

  // 跳转对话页
  await Page.navigate({ url: 'http://localhost:3000/chat' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2000));

  // 点击"唤醒数字人"按钮
  console.log('--- 点击唤醒数字人 ---');
  const clickResult = await Runtime.evaluate({
    expression: `(() => {
      const btn = [...document.querySelectorAll('button')].find(b => /唤醒数字人/.test(b.textContent));
      if (btn) { btn.click(); return 'clicked'; }
      return 'no button found';
    })()`,
  });
  console.log(clickResult.result.value);

  // 等待 SDK 连接和资源下载
  console.log('--- 等待 SDK 初始化 (20s) ---');
  for (let i = 0; i < 10; i++) {
    await new Promise(r => setTimeout(r, 2000));
    const status = await Runtime.evaluate({
      expression: `(() => {
        const el = document.querySelector('.xy-conn');
        const loading = document.querySelector('.xy-loading');
        const dl = document.querySelector('.xy-dl-fill');
        return JSON.stringify({
          connText: el?.textContent?.trim() || 'n/a',
          isLoading: !!loading,
          dlProgress: dl ? dl.style.width : 'n/a',
        });
      })()`,
    });
    console.log(`[${(i+1)*2}s]`, status.result.value);
    const parsed = JSON.parse(status.result.value);
    if (parsed.connText === '已连接') break;
  }

  // 截图：连接成功后的待命状态
  const { data: ss1 } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'dh-idle.png'), Buffer.from(ss1, 'base64'));
  console.log('截图1 (待命):', path.join(outDir, 'dh-idle.png'));

  // 探测渲染区 DOM 结构（待命态）
  const domProbeIdle = await Runtime.evaluate({
    expression: `(() => {
      const render = document.querySelector('.xy-render');
      if (!render) return 'no .xy-render';
      const children = [...render.children].map(el => ({
        tag: el.tagName,
        id: el.id,
        cls: el.className,
        rect: (() => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height) }; })(),
        bg: getComputedStyle(el).backgroundColor,
      }));
      const canvas = render.querySelector('canvas');
      const video = render.querySelector('video');
      return JSON.stringify({
        children,
        canvas: canvas ? { w: canvas.width, h: canvas.height, bg: getComputedStyle(canvas).backgroundColor } : null,
        video: video ? { w: video.videoWidth, h: video.videoHeight, bg: getComputedStyle(video).backgroundColor } : null,
      });
    })()`,
  });
  console.log('DOM idle:', domProbeIdle.result.value);

  // 触发播报：在输入框输入文字并发送
  console.log('--- 发送消息触发播报 ---');
  await Runtime.evaluate({
    expression: `(() => {
      const input = document.querySelector('input[type="text"]');
      if (input) {
        const nativeSet = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        nativeSet.call(input, '灵山大佛有多高');
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    })()`,
  });
  await new Promise(r => setTimeout(r, 500));

  // 点击发送按钮
  await Runtime.evaluate({
    expression: `(() => {
      const btn = document.querySelector('.send-btn');
      if (btn && !btn.disabled) { btn.click(); return 'sent'; }
      return 'btn disabled or not found';
    })()`,
  });

  // 等待 AI 回复 + 数字人开始播报
  console.log('--- 等待回复和播报 (15s) ---');
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const state = await Runtime.evaluate({
      expression: `(() => {
        const speaking = document.querySelector('.xy-speak');
        const msgs = document.querySelectorAll('.msg-bubble.assistant');
        return JSON.stringify({
          isSpeaking: !!speaking,
          msgCount: msgs.length,
          lastMsg: msgs.length ? msgs[msgs.length-1].textContent.substring(0, 50) : '',
        });
      })()`,
    });
    const parsed = JSON.parse(state.result.value);
    console.log(`[${i+1}s]`, state.result.value);
    if (parsed.isSpeaking) {
      // 播报中！立刻截图
      console.log('--- 检测到播报中，截图 ---');

      // 探测播报时的 DOM
      const domProbeSpeak = await Runtime.evaluate({
        expression: `(() => {
          const render = document.querySelector('.xy-render');
          if (!render) return 'no .xy-render';
          const children = [...render.children].map(el => ({
            tag: el.tagName,
            id: el.id,
            cls: el.className,
            style: el.getAttribute('style') || '',
            rect: (() => { const r = el.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.x), y: Math.round(r.y) }; })(),
            bg: getComputedStyle(el).backgroundColor,
            opacity: getComputedStyle(el).opacity,
          }));
          const canvas = render.querySelector('canvas');
          const video = render.querySelector('video');
          const stage = document.querySelector('.xy-stage');
          const stageBg = stage ? getComputedStyle(stage).backgroundColor : 'n/a';
          return JSON.stringify({
            children,
            canvas: canvas ? { w: canvas.width, h: canvas.height, style: canvas.getAttribute('style'), bg: getComputedStyle(canvas).backgroundColor } : null,
            video: video ? { w: video.videoWidth, h: video.videoHeight, style: video.getAttribute('style'), bg: getComputedStyle(video).backgroundColor, objectFit: getComputedStyle(video).objectFit } : null,
            stageBg,
          });
        })()`,
      });
      console.log('DOM speaking:', domProbeSpeak.result.value);

      const { data: ss2 } = await Page.captureScreenshot({ format: 'png' });
      fs.writeFileSync(path.join(outDir, 'dh-speaking.png'), Buffer.from(ss2, 'base64'));
      console.log('截图2 (播报中):', path.join(outDir, 'dh-speaking.png'));
      break;
    }
  }

  // 打印错误
  if (jsErrors.length) {
    console.log('\n=== JS ERRORS ===');
    jsErrors.forEach(e => console.log(e));
  }
  if (consoleLogs.length > 20) {
    console.log('\n=== Console (last 20) ===');
    consoleLogs.slice(-20).forEach(l => console.log(l));
  }

  await client.close();
})();
