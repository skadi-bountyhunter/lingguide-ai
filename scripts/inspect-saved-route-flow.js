const CDP = require('chrome-remote-interface')
const fs = require('fs')
const path = require('path')

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

async function waitFor(Runtime, expression, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const result = await Runtime.evaluate({ expression, awaitPromise: true, returnByValue: true })
    if (result.result.value) return result.result.value
    await sleep(1000)
  }
  throw new Error(`等待超时：${label}`)
}

async function snapshot(Page, fileName) {
  const { data } = await Page.captureScreenshot({ format: 'png' })
  const outDir = path.resolve(__dirname, '../uploads/_debug')
  fs.mkdirSync(outDir, { recursive: true })
  const outFile = path.join(outDir, fileName)
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'))
  return outFile
}

;(async () => {
  const targets = await CDP.List({ port: 9222 })
  const target = targets.find(item => item.type === 'page')
  if (!target) throw new Error('未找到 Chrome 页面')

  const client = await CDP({ target, port: 9222 })
  const { Page, Runtime, Emulation, Log } = client
  const logs = []
  await Page.enable()
  await Runtime.enable()
  await Log.enable()
  Log.entryAdded(({ entry }) => logs.push(`${entry.level}: ${entry.text}`))
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    logs.push(`exception: ${exceptionDetails.exception?.description || exceptionDetails.text}`)
  })

  await Emulation.setDeviceMetricsOverride({
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  })

  await Page.navigate({ url: 'http://localhost:3000/' })
  await Page.loadEventFired()
  await Runtime.evaluate({
    expression: `localStorage.setItem('lingguide_token', 'token_15012345678')`,
  })

  // 先调用路线接口生成数据，再按当前 history.state 契约进入路线页。
  await Runtime.evaluate({
    expression: `fetch('/api/chat/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interests: [],
        duration: '半天',
        chat_query: '我带老人游览半天，想看大佛和梵宫，请规划轻松路线',
        chat_reply: '',
      }),
    }).then(async response => {
      if (!response.ok) throw new Error('路线接口返回 ' + response.status)
      const data = await response.json()
      const snapshot = {
        ...data,
        schema_version: 1,
        source: 'chat',
        duration_mode: '半天',
        interests: [],
      }
      history.replaceState({ ...(history.state || {}), route_plan: snapshot }, '', '/route?from=chat')
      setTimeout(() => location.reload(), 50)
      return true
    })`,
    awaitPromise: true,
    returnByValue: true,
  })
  await Page.loadEventFired()

  await waitFor(
    Runtime,
    `document.querySelector('.route-plan-card')?.innerText.includes('小灵推荐') || false`,
    180000,
    '数字人推荐路线卡片',
  )

  const generated = await Runtime.evaluate({
    expression: `(() => {
      const card = document.querySelector('.route-plan-card')
      card?.scrollIntoView({ block: 'center' })
      return {
        title: card?.querySelector('h3')?.textContent?.trim() || '',
        stations: card?.querySelectorAll('.route-stations li').length || 0,
        text: card?.innerText || '',
      }
    })()`,
    returnByValue: true,
  })
  await sleep(500)
  const generatedShot = await snapshot(Page, 'saved-route-generated-mobile.png')

  await Runtime.evaluate({
    expression: `(() => {
      const card = [...document.querySelectorAll('.route-plan-card')]
        .find(item => item.textContent.includes('小灵推荐'))
      const button = [...(card?.querySelectorAll('button') || [])]
        .find(item => item.textContent.includes('保存路线'))
      button?.click()
      button?.click()
      return Boolean(button)
    })()`,
  })

  await waitFor(
    Runtime,
    `document.querySelector('.route-plan-card')?.innerText.includes('已保存') || false`,
    30000,
    '路线保存完成',
  )

  const savedBeforeReload = await Runtime.evaluate({
    expression: `fetch('/api/profile/routes', {
      headers: { Authorization: localStorage.getItem('lingguide_token') || '' },
    }).then(response => response.json())`,
    awaitPromise: true,
    returnByValue: true,
  })

  await Page.reload({ ignoreCache: true })
  await Page.loadEventFired()
  await waitFor(
    Runtime,
    `document.querySelector('.saved-route-list .route-plan-card')?.innerText.includes('已保存') || false`,
    30000,
    '刷新后已保存路线',
  )

  const refreshed = await Runtime.evaluate({
    expression: `(() => {
      const card = document.querySelector('.saved-route-list .route-plan-card')
      card?.scrollIntoView({ block: 'center' })
      return {
        title: card?.querySelector('h3')?.textContent?.trim() || '',
        stations: card?.querySelectorAll('.route-stations li').length || 0,
        countText: document.querySelector('.saved-count')?.textContent?.trim() || '',
      }
    })()`,
    returnByValue: true,
  })
  await sleep(500)
  const refreshedShot = await snapshot(Page, 'saved-route-refreshed-mobile.png')

  await Runtime.evaluate({
    expression: `(() => {
      const card = document.querySelector('.saved-route-list .route-plan-card')
      const button = [...(card?.querySelectorAll('button') || [])]
        .find(item => item.textContent.includes('在地图查看'))
      button?.click()
      return Boolean(button)
    })()`,
  })
  await sleep(8000)

  const mapState = await Runtime.evaluate({
    expression: `(() => ({
      status: document.querySelector('.route-status')?.textContent?.trim() || '',
      mapText: document.querySelector('.scenic-map')?.innerText?.slice(0, 300) || '',
      scrollY: Math.round(scrollY),
    }))()`,
    returnByValue: true,
  })
  const mapShot = await snapshot(Page, 'saved-route-map-mobile.png')

  await Runtime.evaluate({
    expression: `(() => {
      const card = document.querySelector('.saved-route-list .route-plan-card')
      const button = [...(card?.querySelectorAll('button') || [])]
        .find(item => item.textContent.includes('删除路线'))
      button?.click()
      return Boolean(button)
    })()`,
  })
  await waitFor(Runtime, `Boolean(document.querySelector('.el-message-box'))`, 10000, '删除确认框')
  await Runtime.evaluate({
    expression: `(() => {
      const cancel = [...document.querySelectorAll('.el-message-box button')]
        .find(item => item.textContent.includes('取消'))
      cancel?.click()
      return Boolean(cancel)
    })()`,
  })
  await sleep(500)

  const afterCancel = await Runtime.evaluate({
    expression: `Boolean(document.querySelector('.saved-route-list .route-plan-card'))`,
    returnByValue: true,
  })

  await Runtime.evaluate({
    expression: `(() => {
      const card = document.querySelector('.saved-route-list .route-plan-card')
      const button = [...(card?.querySelectorAll('button') || [])]
        .find(item => item.textContent.includes('删除路线'))
      button?.click()
      return Boolean(button)
    })()`,
  })
  await waitFor(Runtime, `Boolean(document.querySelector('.el-message-box'))`, 10000, '第二次删除确认框')
  await Runtime.evaluate({
    expression: `(() => {
      const confirm = [...document.querySelectorAll('.el-message-box button')]
        .find(item => item.textContent.trim() === '删除')
      confirm?.click()
      return Boolean(confirm)
    })()`,
  })

  await waitFor(
    Runtime,
    `!document.querySelector('.saved-route-list .route-plan-card')`,
    30000,
    '删除路线完成',
  )

  await Page.reload({ ignoreCache: true })
  await Page.loadEventFired()
  await waitFor(
    Runtime,
    `!document.querySelector('.saved-state')?.innerText.includes('正在加载')`,
    30000,
    '删除后刷新完成',
  )

  const afterDelete = await Runtime.evaluate({
    expression: `fetch('/api/profile/routes', {
      headers: { Authorization: localStorage.getItem('lingguide_token') || '' },
    }).then(response => response.json()).then(routes => ({
      count: routes.length,
      emptyText: document.querySelector('.saved-state')?.innerText || '',
    }))`,
    awaitPromise: true,
    returnByValue: true,
  })

  console.log(JSON.stringify({
    generated: generated.result.value,
    savedBeforeReload: savedBeforeReload.result.value,
    refreshed: refreshed.result.value,
    mapState: mapState.result.value,
    afterCancel: afterCancel.result.value,
    afterDelete: afterDelete.result.value,
    screenshots: [generatedShot, refreshedShot, mapShot],
    logs: logs.slice(-20),
  }, null, 2))

  await client.close()
})().catch(error => {
  console.error(error)
  process.exit(1)
})
