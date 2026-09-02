const CDP = require('chrome-remote-interface')
const fs = require('fs')
const http = require('http')
const path = require('path')

const API_BASE = 'http://127.0.0.1:8000'
const CHAT_URL = 'http://127.0.0.1:3000/chat'
const QUERY = '灵山大佛有多高？'
const TIMEOUT_MS = 20000

function parseArgs(argv) {
  const args = { allowLiveWrite: false, screenshot: null }
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === '--allow-live-write') args.allowLiveWrite = true
    if (argv[index] === '--screenshot') args.screenshot = argv[index + 1] || null
  }
  return args
}

function requestJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, response => {
      let body = ''
      response.setEncoding('utf8')
      response.on('data', chunk => { body += chunk })
      response.on('end', () => {
        try {
          resolve({ status: response.statusCode, body: JSON.parse(body) })
        } catch (error) {
          reject(new Error(`响应不是 JSON: ${error.message}`))
        }
      })
    }).on('error', error => reject(new Error(`无法访问 ${url}: ${error.message}`)))
  })
}

async function waitFor(probe, description) {
  const deadline = Date.now() + TIMEOUT_MS
  let lastValue
  while (Date.now() < deadline) {
    lastValue = await probe()
    if (lastValue?.ready) return lastValue
    await new Promise(resolve => setTimeout(resolve, 250))
  }
  throw new Error(`${description}超时: ${JSON.stringify(lastValue)}`)
}

async function evaluateJson(Runtime, expression) {
  const result = await Runtime.evaluate({ expression, returnByValue: true })
  return result.result.value
}

;(async () => {
  const args = parseArgs(process.argv.slice(2))
  if (!args.allowLiveWrite) {
    throw new Error('真实聊天会写入 interaction；请显式传入 --allow-live-write')
  }
  if (args.screenshot && !fs.existsSync(path.dirname(path.resolve(args.screenshot)))) {
    throw new Error('--screenshot 的父目录不存在')
  }

  const readiness = await requestJson(`${API_BASE}/api/readiness`)
  if (readiness.status !== 200 || readiness.body.status !== 'ready') {
    throw new Error(`后端未就绪: HTTP ${readiness.status}`)
  }

  const targets = await CDP.List({ port: 9222 })
  const target = targets.find(item => item.type === 'page' && item.url.includes('127.0.0.1:3000'))
    || targets.find(item => item.type === 'page')
  if (!target) throw new Error('Chrome CDP 中没有可用页面')

  const client = await CDP({ target, port: 9222 })
  const { Page, Runtime, Emulation, Input, Network } = client
  const pageErrors = []
  const failedRequests = []
  try {
    await Promise.all([Page.enable(), Runtime.enable(), Network.enable()])
    Runtime.exceptionThrown(({ exceptionDetails }) => {
      const message = exceptionDetails.text || exceptionDetails.exception?.description || '未知页面异常'
      pageErrors.push(message)
    })
    Network.loadingFailed(({ errorText, type }) => {
      if (type === 'WebSocket' || type === 'XHR' || type === 'Fetch') {
        failedRequests.push(`${type}:${errorText}`)
      }
    })
    await Emulation.setDeviceMetricsOverride({ width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })
    await Page.navigate({ url: 'http://127.0.0.1:3000/' })
    await Page.loadEventFired()
    await Runtime.evaluate({ expression: "localStorage.setItem('lingguide_token', 'token_demo_admin')" })
    await Page.navigate({ url: CHAT_URL })
    await Page.loadEventFired()

    const input = await waitFor(async () => evaluateJson(Runtime, `(() => {
      const element = document.querySelector('.input-bar input')
      if (!element) return { ready: false, reason: 'input_missing' }
      const rect = element.getBoundingClientRect()
      return { ready: rect.width > 0 && rect.height > 0 && !element.disabled, x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 }
    })()`), '聊天输入框就绪')

    const before = await evaluateJson(Runtime, `JSON.stringify({
      assistantCount: document.querySelectorAll('.msg-bubble.assistant').length,
      userCount: document.querySelectorAll('.msg-bubble.user').length,
      connected: document.querySelector('.h-status')?.textContent?.includes('在线') || false
    })`)
    const beforeState = JSON.parse(before)
    if (!beforeState.connected) throw new Error('WebSocket 未连接')

    await Input.dispatchMouseEvent({ type: 'mousePressed', x: input.x, y: input.y, button: 'left', clickCount: 1 })
    await Input.dispatchMouseEvent({ type: 'mouseReleased', x: input.x, y: input.y, button: 'left', clickCount: 1 })
    await Runtime.evaluate({ expression: "document.querySelector('.input-bar input')?.focus()" })
    await Input.insertText({ text: QUERY })
    await waitFor(async () => evaluateJson(Runtime, `(() => ({
      ready: document.querySelector('.input-bar input')?.value === ${JSON.stringify(QUERY)}
    }))()`), '问题写入输入框')
    await Runtime.evaluate({ expression: `(() => {
      const input = document.querySelector('.input-bar input')
      input?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }))
    })()` })
    await waitFor(async () => evaluateJson(Runtime, `(() => ({
      ready: document.querySelector('.input-bar input')?.value === ''
    }))()`), '问题发送')

    const result = await waitFor(async () => {
      const raw = await evaluateJson(Runtime, `JSON.stringify((() => {
        const assistants = [...document.querySelectorAll('.msg-bubble.assistant')]
        const users = [...document.querySelectorAll('.msg-bubble.user')]
        const latest = assistants.at(-1)
        const answer = latest?.querySelector('.bubble-text')?.textContent?.trim() || ''
        const citation = latest?.querySelector('.citation-box')
        const citationMeta = latest?.querySelector('.citation-meta')?.textContent?.trim() || ''
        const degraded = Boolean(latest?.querySelector('.answer-status'))
        const loading = Boolean(document.querySelector('.loading-bubble'))
        return {
          users: users.length,
          assistants: assistants.length,
          answer,
          citations: latest?.querySelectorAll('.citation-item').length || 0,
          citationMeta,
          degraded,
          loading,
        }
      })())`)
      const state = JSON.parse(raw)
      const ready = state.users > beforeState.userCount
        && state.assistants > beforeState.assistantCount
        && state.answer.includes('88米')
        && state.citations >= 1
        && state.citationMeta.includes('faq')
        && !state.degraded
        && !state.loading
      return { ready, state }
    }, 'FAQ 回答和 Citation')

    if (pageErrors.length) throw new Error(`页面异常: ${pageErrors.join(' | ')}`)
    if (failedRequests.length) throw new Error(`请求失败: ${failedRequests.join(' | ')}`)

    if (args.screenshot) {
      const { data } = await Page.captureScreenshot({ format: 'png' })
      fs.writeFileSync(path.resolve(args.screenshot), Buffer.from(data, 'base64'))
    }
    console.log(JSON.stringify({ passed: true, answer: result.state.answer, citations: result.state.citations, screenshot: Boolean(args.screenshot) }))
  } finally {
    await client.close()
  }
})().catch(error => {
  console.error(error.message || error)
  process.exit(1)
})
