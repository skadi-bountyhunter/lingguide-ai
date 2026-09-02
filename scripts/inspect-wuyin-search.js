// 单独搜五印坛城：尝试多个备选关键词
const CDP = require('chrome-remote-interface');

(async () => {
  const targets = await CDP.List({ port: 9222 });
  const target = targets.find(t => t.type === 'page');
  const client = await CDP({ target, port: 9222 });
  const { Runtime } = client;
  await Runtime.enable();

  const keywords = ['灵山胜境五印坛城', '灵山 坛城', '五印坛城 灵山', '灵山胜境 藏式', '灵山胜境'];
  for (const kw of keywords) {
    const r = await Runtime.evaluate({
      expression: `new Promise(resolve => {
        const ps = new AMap.PlaceSearch({ city: '无锡', citylimit: true, pageSize: 5, extensions: 'all' });
        ps.search('${kw}', (status, res) => {
          if (status !== 'complete' || !res.poiList || !res.poiList.pois.length) { resolve('[]'); return; }
          resolve(JSON.stringify(res.poiList.pois.map(p => ({ name: p.name, loc: p.location && p.location.lng ? p.location.lng + ',' + p.location.lat : '' }))));
        });
      })`,
      awaitPromise: true,
    });
    console.log(`【${kw}】`, r.result.value);
  }
  await client.close();
})().catch(e => { console.error(e); process.exit(1); });
