const CDP = require('chrome-remote-interface');
const fs = require('fs');
const path = require('path');

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const outDir = path.resolve(__dirname, '../uploads/_debug');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(item => item.type === 'page');
  if (!target) throw new Error('没有可复用的 Chrome 页面');

  const client = await CDP({ target, port: 9222 });
  const { Page, Runtime, Emulation } = client;
  await Page.enable();
  await Runtime.enable();
  await Emulation.setDeviceMetricsOverride({
    width: 430,
    height: 900,
    deviceScaleFactor: 1,
    mobile: true,
  });

  async function navigate(url, wait = 1200) {
    await Page.navigate({ url });
    await Page.loadEventFired();
    await sleep(wait);
  }

  async function evaluate(expression) {
    const result = await Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  }

  async function screenshot(name) {
    const { data } = await Page.captureScreenshot({ format: 'png', captureBeyondViewport: false });
    const file = path.join(outDir, name);
    fs.writeFileSync(file, Buffer.from(data, 'base64'));
    console.log('截图:', file);
  }

  await navigate('http://localhost:3000/auth');
  await evaluate(`(() => {
    localStorage.setItem('lingguide_token', 'token_13900000001');
    localStorage.setItem('lingguide_user', JSON.stringify({ phone: '13900000001', nickname: '游客0001' }));
  })()`);

  for (const locale of ['zh-CN', 'en', 'ja', 'ko']) {
    await evaluate(`localStorage.setItem('lingguide_locale', ${JSON.stringify(locale)})`);

    await navigate('http://localhost:3000/profile/language');
    const language = await evaluate(`(() => ({
      locale: localStorage.getItem('lingguide_locale'),
      htmlLang: document.documentElement.lang,
      title: document.querySelector('h1')?.textContent?.trim(),
      text: document.body.innerText.slice(0, 400),
    }))()`);

    await navigate('http://localhost:3000/', 1800);
    const home = await evaluate(`(() => ({
      htmlLang: document.documentElement.lang,
      heading: document.querySelector('.header-left h1')?.textContent?.trim(),
      firstSpot: document.querySelector('.spot-info h3')?.textContent?.trim(),
      firstDesc: document.querySelector('.spot-desc')?.textContent?.trim(),
      firstTags: [...document.querySelectorAll('.spot-tags span')].slice(0, 2).map(item => item.textContent?.trim()),
      spotCount: document.querySelectorAll('.spot-card').length,
      text: document.body.innerText.slice(0, 500),
    }))()`);

    await navigate('http://localhost:3000/chat', 1600);
    const chat = await evaluate(`(() => ({
      htmlLang: document.documentElement.lang,
      title: document.querySelector('.h-name')?.textContent?.trim(),
      intro: document.querySelector('.empty-state > p')?.textContent?.trim(),
      questions: [...document.querySelectorAll('.quick-list button')].map(item => item.textContent?.trim()),
      input: document.querySelector('.input-row input')?.getAttribute('placeholder'),
      avatarState: document.querySelector('.xy-conn')?.textContent?.trim(),
      avatarName: document.querySelector('.xy-role')?.textContent?.trim(),
      bodyText: document.body.innerText.slice(0, 500),
    }))()`);

    await navigate('http://localhost:3000/spot/%E7%81%B5%E5%B1%B1%E5%A4%A7%E4%BD%9B', 1600);
    const detail = await evaluate(`(() => ({
      title: document.querySelector('.hero-title-row h1')?.textContent?.trim(),
      summary: document.querySelector('.desc-para')?.textContent?.trim(),
      highlights: [...document.querySelectorAll('.highlight-text')].map(item => item.textContent?.trim()),
      bestSeason: document.querySelector('.qi-value-sm')?.textContent?.trim(),
      sections: [...document.querySelectorAll('.section-block')].map(item => item.textContent?.trim().slice(0, 160)),
      nearbyCount: document.querySelectorAll('.nearby-card').length,
    }))()`);

    await navigate('http://localhost:3000/route', 1800);
    const route = await evaluate(`(() => ({
      title: document.querySelector('.route-header h1')?.textContent?.trim(),
      interests: [...document.querySelectorAll('.tag-group button')].map(item => item.textContent?.trim()),
      presetTitle: document.querySelector('.route-card h3')?.textContent?.trim(),
      presetDifficulty: document.querySelector('.rc-difficulty')?.textContent?.trim(),
      presetDesc: document.querySelector('.rc-desc')?.textContent?.trim(),
      presetSpots: [...document.querySelectorAll('.route-card .rc-spots span')].map(item => item.textContent?.trim()),
      presetTip: document.querySelector('.rc-tip')?.textContent?.trim(),
    }))()`);

    console.log(JSON.stringify({ locale, language, home, chat, detail, route }, null, 2));
    await screenshot(`i18n-${locale}.png`);
  }

  await client.close();
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
