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
    localStorage.setItem('lingguide_user', JSON.stringify({phone:'13900000001', nickname:'游客0001'}));
  })()`);

  await navigate('http://localhost:3000/profile', 1600);
  console.log('profile:', await evaluate(`({url:location.href,text:document.body.innerText.slice(0,900),cards:document.querySelectorAll('.stat-card').length})`));
  await screenshot('profile-features.png');

  await navigate('http://localhost:3000/profile/language');
  const langProbe = await evaluate(`(() => {
    const buttons=[...document.querySelectorAll('button')];
    const ja=buttons.find(button=>/日本語|日语|Japanese/.test(button.textContent));
    if(!ja)return {clicked:false,text:document.body.innerText};
    ja.click();
    return new Promise(resolve=>setTimeout(()=>resolve({clicked:true,lang:document.documentElement.lang,text:document.body.innerText.slice(0,500)}),300));
  })()`);
  console.log('language:', langProbe);
  await screenshot('profile-language-ja.png');

  await navigate('http://localhost:3000/profile/voice');
  const voiceProbe = await evaluate(`(() => {
    const buttons=[...document.querySelectorAll('button')];
    if(buttons[2])buttons[2].click();
    const range=document.querySelector('input[type=range]');
    if(range){range.value='62';range.dispatchEvent(new Event('input',{bubbles:true}));}
    return {text:document.body.innerText.slice(0,600),stored:localStorage.getItem('lingguide_voice_settings_v1')};
  })()`);
  console.log('voice:', voiceProbe);
  await screenshot('profile-voice.png');

  await navigate('http://localhost:3000/profile/feedback');
  const feedbackProbe = await evaluate(`(() => ({text:document.body.innerText.slice(0,600), textarea:!!document.querySelector('textarea')}))()`);
  console.log('feedback:', feedbackProbe);
  await screenshot('profile-feedback.png');

  await navigate('http://localhost:3000/profile/notifications', 1600);
  console.log('notifications:', await evaluate(`({text:document.body.innerText.slice(0,600),items:document.querySelectorAll('.notification').length})`));
  await screenshot('profile-notifications.png');

  await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await navigate('http://localhost:3001/feedback');
  console.log('admin-feedback:', await evaluate(`({text:document.body.innerText.slice(0,700),tables:document.querySelectorAll('.el-table').length})`));
  await screenshot('admin-feedback.png');

  await navigate('http://localhost:3001/notifications', 4000);
  console.log('admin-notifications:', await evaluate(`({text:document.body.innerText.slice(0,700),tables:document.querySelectorAll('.el-table').length,html:document.querySelector('main')?.innerHTML.slice(0,300)})`));
  await screenshot('admin-notifications.png');

  await client.close();
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
