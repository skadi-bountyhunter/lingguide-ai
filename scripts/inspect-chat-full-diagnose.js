const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation, Network } = client;
  await Page.enable();
  await Runtime.enable();
  await Network.enable();
  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const logs = [];
  const errors = [];
  const failed = [];
  Runtime.consoleAPICalled(({ type, args }) => {
    logs.push(`[${type}] ` + args.map(a => a.value || a.description || '').join(' '));
  });
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    errors.push(exceptionDetails.exception?.description || exceptionDetails.text || 'unknown');
  });
  Network.loadingFailed((e) => failed.push(`${e.type || ''} ${e.errorText || ''} ${e.blockedReason || ''} ${e.requestId}`));

  await Page.navigate({ url: 'http://localhost:3000/' });
  await Page.loadEventFired();
  await sleep(300);
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'dev-test-token')` });

  await Page.navigate({ url: 'http://localhost:3000/chat' });
  await Page.loadEventFired();
  await sleep(5000);

  const before = await Runtime.evaluate({ expression: `(() => {
    const input = document.querySelector('.input-row input');
    const send = document.querySelector('.send-btn');
    const dh = document.querySelector('.dh-panel');
    const xy = document.querySelector('#xy-sdk-chat');
    const canvas = xy && xy.querySelector('canvas');
    const video = xy && xy.querySelector('video');
    const cta = document.querySelector('.xy-cta');
    const conn = document.querySelector('.xy-conn');
    function rect(el){ if(!el) return null; const r=el.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; }
    return JSON.stringify({
      url: location.href,
      input: input ? {disabled: input.disabled, value: input.value, rect: rect(input), top: document.elementFromPoint(rect(input).x+10, rect(input).y+10)?.className || document.elementFromPoint(rect(input).x+10, rect(input).y+10)?.tagName} : null,
      send: send ? {disabled: send.disabled, rect: rect(send)} : null,
      buttons: [...document.querySelectorAll('button')].map(b=>b.textContent.trim()).slice(0,20),
      msgCount: document.querySelectorAll('.msg-row').length,
      dh: rect(dh), xy: rect(xy), canvas: rect(canvas), video: rect(video), cta: !!cta,
      connText: conn?.textContent?.trim() || null,
      sdkLoaded: !!window.XmovAvatar,
      bodyTextHead: document.body.innerText.slice(0,500)
    });
  })()`, returnByValue: true });
  console.log('BEFORE', before.result.value);

  const sendResult = await Runtime.evaluate({ expression: `(() => {
    const input = document.querySelector('.input-row input');
    if (!input) return 'no input';
    input.focus();
    input.value = '灵山大佛有多高？';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    const btn = document.querySelector('.send-btn');
    if (!btn) return 'no send';
    const beforeDisabled = btn.disabled;
    btn.click();
    return JSON.stringify({ beforeDisabled, valueAfterSet: input.value, clicked: true });
  })()`, returnByValue: true });
  console.log('SEND', sendResult.result.value);

  await sleep(3000);

  const after = await Runtime.evaluate({ expression: `(() => {
    const rows = [...document.querySelectorAll('.msg-row')].map(r => ({cls: r.className, text: r.innerText.slice(0,200)}));
    const input = document.querySelector('.input-row input');
    const send = document.querySelector('.send-btn');
    const conn = document.querySelector('.xy-conn');
    const xy = document.querySelector('#xy-sdk-chat');
    const canvas = xy && xy.querySelector('canvas');
    const video = xy && xy.querySelector('video');
    function rect(el){ if(!el) return null; const r=el.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; }
    return JSON.stringify({
      input: input ? {disabled: input.disabled, value: input.value} : null,
      send: send ? {disabled: send.disabled} : null,
      rows,
      storeText: document.body.innerText.slice(0,800),
      connText: conn?.textContent?.trim() || null,
      canvas: rect(canvas), video: rect(video), cta: !!document.querySelector('.xy-cta')
    });
  })()`, returnByValue: true });
  console.log('AFTER', after.result.value);

  console.log('ERRORS', JSON.stringify(errors, null, 2));
  console.log('LOGS', JSON.stringify(logs.slice(-80), null, 2));
  console.log('FAILED', JSON.stringify(failed.slice(-80), null, 2));

  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outFile = path.join(outDir, 'chat-full-diagnose.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('SCREENSHOT', outFile);
  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
