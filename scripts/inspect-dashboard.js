// 核验管理端数据大屏的实际请求、周期切换、渲染结果和浏览器错误。
const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find((item) => item.type === 'page');
  if (!target) throw new Error('未找到 Chrome 页面，请先启动 CDP 浏览器');

  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation, Network, Log } = client;
  const consoleErrors = [];
  const failedResponses = [];
  const dashboardRequests = [];
  await Promise.all([Page.enable(), Runtime.enable(), Network.enable(), Log.enable()]);
  await Emulation.setDeviceMetricsOverride({
    width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  });

  Runtime.consoleAPICalled(({ type, args }) => {
    if (type === 'error') consoleErrors.push(args.map((item) => item.value || item.description).join(' '));
  });
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    consoleErrors.push(exceptionDetails.exception?.description || exceptionDetails.text);
  });
  Log.entryAdded(({ entry }) => {
    if (entry.level === 'error') consoleErrors.push(`${entry.text} (${entry.url || 'unknown'})`);
  });
  Network.responseReceived(({ response }) => {
    if (response.status >= 400) failedResponses.push({ url: response.url, status: response.status });
    if (response.url.includes('/api/dashboard/overview')) {
      dashboardRequests.push({ url: response.url, status: response.status, mimeType: response.mimeType });
    }
  });

  await Page.navigate({ url: 'http://localhost:3001/dashboard' });
  await Page.loadEventFired();
  await sleep(2500);

  const periodResults = [];
  for (const label of ['今日', '近 7 天', '近 30 天']) {
    const clickResult = await Runtime.evaluate({
      expression: `(() => {
        const button = [...document.querySelectorAll('.period-switch button')]
          .find((item) => item.textContent.trim() === ${JSON.stringify(label)});
        if (!button) return false;
        button.click();
        return true;
      })()`,
      returnByValue: true,
    });
    if (!clickResult.result.value) throw new Error(`未找到周期按钮：${label}`);

    for (let attempt = 0; attempt < 40; attempt += 1) {
      await sleep(100);
      const state = await Runtime.evaluate({
        expression: `(() => ({
          active: document.querySelector('.period-switch button.active')?.textContent?.trim(),
          loading: [...document.querySelectorAll('.period-switch button')].some((item) => item.disabled),
        }))()`,
        returnByValue: true,
      });
      if (state.result.value.active === label && !state.result.value.loading) break;
    }

    const probe = await Runtime.evaluate({
      expression: `(() => ({
        requested: ${JSON.stringify(label)},
        active: document.querySelector('.period-switch button.active')?.textContent?.trim(),
        metrics: [...document.querySelectorAll('.metric-card')].map((card) => ({
          label: card.querySelector('.metric-label')?.textContent?.trim(),
          value: card.querySelector('strong')?.textContent?.trim(),
        })),
        charts: document.querySelectorAll('.chart canvas').length,
        questions: document.querySelectorAll('.question-list li').length,
        modes: document.querySelectorAll('.mode-row').length,
        error: document.querySelector('.refresh-warning, .empty-state')?.textContent?.trim() || null,
      }))()`,
      returnByValue: true,
    });
    periodResults.push(probe.result.value);
  }

  const outDir = path.resolve(__dirname, '../uploads/_debug');
  fs.mkdirSync(outDir, { recursive: true });
  const outFile = path.join(outDir, 'admin-dashboard-audit.png');
  const { data } = await Page.captureScreenshot({ format: 'png' });
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'));

  console.log(JSON.stringify({
    dashboardRequests,
    failedResponses,
    consoleErrors: [...new Set(consoleErrors)],
    periodResults,
    screenshot: outFile,
  }, null, 2));
  await client.close();
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
