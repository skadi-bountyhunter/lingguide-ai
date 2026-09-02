// 自动跑校准页：导航→点开始→等搜索→点写回→截图
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  if (!target) throw new Error('no page target');
  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime } = client;
  await Page.enable();
  await Runtime.enable();

  await Page.navigate({ url: 'file:///E:/ruanjianbei/scripts/calibrate_spots.html' });
  await Page.loadEventFired();
  await new Promise(r => setTimeout(r, 2000));

  // 点"开始校准"
  const r1 = await Runtime.evaluate({
    expression: `(() => {
      const b = [...document.querySelectorAll('button')].find(x => /开始校准/.test(x.textContent));
      if (!b) return 'no-btn';
      b.click();
      return 'clicked';
    })()`,
  });
  console.log('开始校准:', r1.result.value);

  // 轮询等"写回后端"按钮可用
  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 1500));
    const st = await Runtime.evaluate({
      expression: `(() => {
        const b = [...document.querySelectorAll('button')].find(x => /写回后端/.test(x.textContent));
        return b && !b.disabled ? 'ready' : 'wait';
      })()`,
    });
    if (st.result.value === 'ready') break;
  }

  // 读 dry-run 结果表
  const tbl = await Runtime.evaluate({
    expression: `[...document.querySelectorAll('#tbl tbody tr')].map(tr => tr.innerText.replace(/\\t/g,' | ')).join('\\n')`,
  });
  console.log('=== 校准对比表 ===\n' + tbl.result.value);

  const status = await Runtime.evaluate({ expression: `document.getElementById('status').textContent` });
  console.log('状态:', status.result.value);

  // 点"写回后端"
  const r2 = await Runtime.evaluate({
    expression: `(() => {
      const b = [...document.querySelectorAll('button')].find(x => /写回后端/.test(x.textContent));
      if (!b || b.disabled) return 'disabled';
      b.click();
      return 'clicked';
    })()`,
  });
  console.log('写回:', r2.result.value);

  await new Promise(r => setTimeout(r, 4000));
  const st2 = await Runtime.evaluate({ expression: `document.getElementById('status').textContent` });
  console.log('写回结果:', st2.result.value);

  // 截图
  const { data } = await Page.captureScreenshot({ format: 'png' });
  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'calibrate_spots.png');
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));
  console.log('截图:', outFile);

  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
