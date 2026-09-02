// 核验真实“数字人对话 → 路线推荐 → 路线页地图”链路。
const CDP = require('chrome-remote-interface')
const fs = require('fs')
const path = require('path')

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

;(async () => {
  const target = (await CDP.List({ port: 9222 })).find(item => item.type === 'page')
  if (!target) throw new Error('未找到 Chrome 页面，请先启动 CDP 浏览器')

  const client = await CDP({ target, port: 9222 })
  const { Page, Runtime, Emulation, Network, Log } = client
  const errors = []
  const failedResponses = []
  const routeApiRequests = []
  await Promise.all([Page.enable(), Runtime.enable(), Network.enable(), Log.enable()])
  await Emulation.setDeviceMetricsOverride({
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  })

  Runtime.consoleAPICalled(({ type, args }) => {
    if (type === 'error') errors.push(args.map(item => item.value || item.description).join(' '))
  })
  Runtime.exceptionThrown(({ exceptionDetails }) => {
    errors.push(exceptionDetails.exception?.description || exceptionDetails.text)
  })
  Log.entryAdded(({ entry }) => {
    if (entry.level === 'error') errors.push(entry.text)
  })
  Network.responseReceived(({ response }) => {
    if (response.status >= 400) failedResponses.push({ status: response.status, url: response.url })
    if (response.url.includes('/api/chat/route')) {
      routeApiRequests.push({ status: response.status, url: response.url })
    }
  })

  await Page.navigate({ url: 'http://localhost:3000/' })
  await Page.loadEventFired()
  await Runtime.evaluate({ expression: `localStorage.setItem('lingguide_token', 'token_15012345678')` })
  await Page.navigate({ url: 'http://localhost:3000/chat' })
  await Page.loadEventFired()
  await sleep(2500)

  const query = '我带老人游览半天，请规划一条轻松路线'
  const sent = await Runtime.evaluate({
    expression: `(() => {
      const input = document.querySelector('.input-row input')
      if (!input) return false
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(input, ${JSON.stringify(query)})
      input.dispatchEvent(new Event('input', { bubbles: true }))
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
      return true
    })()`,
    returnByValue: true,
  })
  if (!sent.result.value) throw new Error('未找到对话输入框')

  let routeReady = false
  for (let attempt = 0; attempt < 90; attempt += 1) {
    await sleep(2000)
    const result = await Runtime.evaluate({
      expression: `(() => ({
        loading: Boolean(document.querySelector('.loading-bubble')),
        routeButtons: document.querySelectorAll('.route-btn').length,
      }))()`,
      returnByValue: true,
    })
    if (!result.result.value.loading && result.result.value.routeButtons > 0) {
      routeReady = true
      break
    }
  }
  if (!routeReady) throw new Error('等待路线推荐按钮超时')

  await Runtime.evaluate({
    expression: `(() => {
      const buttons = [...document.querySelectorAll('.route-btn')]
      buttons[buttons.length - 1]?.click()
    })()`,
  })

  let rendered = null
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await sleep(1000)
    const result = await Runtime.evaluate({
      expression: `(() => {
        const snapshot = history.state?.route_plan
        const routeCard = document.querySelector('.route-plan-card')
        return {
          href: location.href,
          hasSnapshot: Boolean(snapshot),
          snapshotSerializable: snapshot ? (() => { try { JSON.stringify(snapshot); return true } catch { return false } })() : false,
          snapshotTitle: snapshot?.title || '',
          snapshotDurationMode: snapshot?.duration_mode || '',
          cardTitle: routeCard?.querySelector('h3')?.textContent?.trim() || '',
          stationCount: routeCard?.querySelectorAll('.route-stations li').length || 0,
          routeStatus: document.querySelector('.route-status')?.textContent?.trim() || '',
          durationActive: [...document.querySelectorAll('.duration-group button')]
            .find(item => item.classList.contains('active'))?.textContent?.trim() || '',
          error: document.querySelector('.planning-error')?.textContent?.trim() || null,
        }
      })()`,
      returnByValue: true,
    })
    rendered = result.result.value
    if (rendered.href.includes('/route?from=chat') && rendered.cardTitle) break
  }

  const outDir = path.resolve(__dirname, '../uploads/_debug')
  fs.mkdirSync(outDir, { recursive: true })
  const outFile = path.join(outDir, 'chat-route-map.png')
  const { data } = await Page.captureScreenshot({ format: 'png', captureBeyondViewport: true })
  fs.writeFileSync(outFile, Buffer.from(data, 'base64'))

  console.log(JSON.stringify({
    rendered,
    routeApiRequests,
    failedResponses,
    errors: [...new Set(errors)],
    screenshot: outFile,
  }, null, 2))
  await client.close()
})().catch(error => {
  console.error(error)
  process.exitCode = 1
})
