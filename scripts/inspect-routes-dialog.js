const fs = require('fs');
const path = require('path');

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function cdpClient() {
  const targets = await (await fetch('http://127.0.0.1:9222/json')).json();
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  });
  return {
    send(method, params = {}) {
      const msgId = ++id;
      ws.send(JSON.stringify({ id: msgId, method, params }));
      return new Promise((resolve, reject) => pending.set(msgId, { resolve, reject }));
    },
    close() { ws.close(); },
  };
}

(async () => {
  const cdp = await cdpClient();
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  await cdp.send('Page.navigate', { url: 'http://127.0.0.1:3001/routes' });
  await sleep(2500);

  const click = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const btn = [...document.querySelectorAll('button')].find(b => /新增路线/.test(b.textContent || ''));
      if (!btn) return 'no button: ' + document.body.innerText.slice(0, 200);
      btn.click();
      return 'clicked';
    })()`,
    returnByValue: true,
  });
  console.log('click:', click.result.value);
  await sleep(1000);

  const probe = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const dlg = document.querySelector('.el-dialog');
      const body = document.querySelector('.el-dialog__body');
      const footer = document.querySelector('.el-dialog__footer');
      if (!dlg) return { found: false, url: location.href, text: document.body.innerText.slice(0, 300) };
      const rect = (el) => { const r = el.getBoundingClientRect(); return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height), bottom: Math.round(r.bottom) }; };
      return {
        found: true,
        viewport: { w: innerWidth, h: innerHeight },
        dialog: rect(dlg),
        body: body ? rect(body) : null,
        footer: footer ? rect(footer) : null,
        dialogOverflowY: getComputedStyle(dlg).overflowY,
        bodyOverflowY: body ? getComputedStyle(body).overflowY : null,
        canSeeFooter: !!footer && footer.getBoundingClientRect().bottom <= innerHeight,
      };
    })()`,
    returnByValue: true,
  });
  console.log('probe:', JSON.stringify(probe.result.value, null, 2));

  const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'routes-dialog-before.png');
  fs.writeFileSync(outFile, Buffer.from(shot.data, 'base64'));
  console.log('截图:', outFile);
  cdp.close();
})().catch(err => { console.error(err); process.exit(1); });
