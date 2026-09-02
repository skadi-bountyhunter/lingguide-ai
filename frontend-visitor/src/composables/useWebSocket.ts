import { ref, onUnmounted, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import type { ChatMessage } from '../stores/chat'
import type { RoutePlan } from '../types/route'
import type { Citation, RetrievalTrace } from '../types/retrieval'
import { getAuthToken } from '../services/profile'
import { i18n } from '../i18n'

export interface ReplyDonePayload {
  text: string
  emotion?: string
  expression?: string
  routePlan?: RoutePlan
  citations?: Citation[]
  retrieval?: RetrievalTrace
  traceId?: string
  requestId?: string
}

type PendingMessage = {
  requestId: string
  messageId: string
  sources: string[]
  citations: Citation[]
  retrieval?: RetrievalTrace
  traceId?: string
  lastSeq: number
  seenSeq: Set<number>
  timeoutId?: ReturnType<typeof setTimeout>
}

export function useWebSocket(opts?: { onReplyDone?: (p: ReplyDonePayload) => void }) {
  const store = useChatStore()
  const isConnected = ref(false)
  let ws: WebSocket | null = null
  const pending = new Map<string, PendingMessage>()

  function connect() {
    disconnect()
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/chat/ws/${store.sessionId}`
    const socket = new WebSocket(url)
    ws = socket

    socket.onopen = () => {
      if (ws !== socket) return
      isConnected.value = true
      store.wsConnected = true
      socket.send(JSON.stringify({ session_token: store.sessionToken, auth_token: getAuthToken(), locale: i18n.global.locale.value }))
      console.log('WebSocket 已连接')
    }

    socket.onmessage = (event) => {
      if (ws !== socket) return
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch {
        console.warn('收到无法解析的聊天消息')
      }
    }

    socket.onclose = () => {
      if (ws !== socket) return
      isConnected.value = false
      store.wsConnected = false
      console.log('WebSocket 已断开')
    }

    socket.onerror = (err) => {
      if (ws === socket) console.error('WebSocket 错误:', err)
    }
  }

  function getPending(data: any): PendingMessage | null {
    const messageId = String(data.message_id || '')
    if (!messageId) return null
    let state = pending.get(messageId)
    if (!state) {
      state = {
        requestId: String(data.request_id || ''),
        messageId,
        sources: [],
        citations: [],
        retrieval: undefined,
        traceId: undefined,
        lastSeq: 0,
        seenSeq: new Set<number>(),
      }
      pending.set(messageId, state)
    }
    if (data.request_id) state.requestId = String(data.request_id)
    if (!state.timeoutId) {
      state.timeoutId = setTimeout(() => {
        if (!pending.delete(state!.messageId)) return
        const message = ensureAssistant(state!, i18n.global.t('chat.timeout'))
        message.content = i18n.global.t('chat.timeout')
        store.isLoading = false
      }, 60000)
    }
    if (typeof data.seq === 'number') {
      if (state.seenSeq.has(data.seq) || data.seq <= state.lastSeq) return null
      state.seenSeq.add(data.seq)
      state.lastSeq = data.seq
    }
    return state
  }

  function applyRetrieval(state: PendingMessage, data: any) {
    if (Array.isArray(data.sources)) state.sources = data.sources
    if (Array.isArray(data.citations)) state.citations = data.citations
    if (data.retrieval) state.retrieval = data.retrieval
    if (data.trace_id) state.traceId = data.trace_id
  }

  function ensureAssistant(state: PendingMessage, initialText = '') {
    const existing = store.messages.find(message => message.id === state.messageId)
    if (existing) return existing
    const message: ChatMessage = {
      id: state.messageId,
      role: 'assistant' as const,
      content: initialText,
      sources: state.sources,
      citations: state.citations,
      retrieval: state.retrieval,
      traceId: state.traceId,
      requestId: state.requestId,
      timestamp: Date.now(),
    }
    store.addMessage(message)
    return message
  }

  function finishMessage(data: any, state: PendingMessage | null) {
    const messageId = String(data.message_id || state?.messageId || '')
    if (!messageId) return
    const current = state || pending.get(messageId) || {
      requestId: String(data.request_id || ''),
      messageId,
      sources: [],
      citations: [],
      retrieval: undefined,
      traceId: undefined,
      lastSeq: 0,
      seenSeq: new Set<number>(),
    }
    applyRetrieval(current, data)
    if (current.timeoutId) {
      clearTimeout(current.timeoutId)
      current.timeoutId = undefined
    }
    const message = ensureAssistant(current, String(data.reply_text || ''))
    if (data.reply_text) message.content = String(data.reply_text)
    message.emotion = data.emotion
    message.expression = data.expression
    message.sources = current.sources
    message.citations = current.citations
    message.retrieval = current.retrieval
    message.traceId = current.traceId
    message.requestId = current.requestId
    if (data.route_plan) message.routePlan = data.route_plan
    return message
  }

  function handleMessage(data: any) {
    const state = data.message_id ? getPending(data) : null
    if (data.message_id && data.seq && !state) return

    switch (data.type) {
      case 'rag_started':
        break

      case 'rag_done':
        if (!state) break
        applyRetrieval(state, data)
        break

      case 'asr_done':
        store.addMessage({
          id: crypto.randomUUID(),
          role: 'user',
          content: data.asr_text,
          timestamp: Date.now(),
        })
        break

      case 'llm_stream': {
        if (!state) break
        const message = ensureAssistant(state)
        message.content += String(data.chunk || '')
        break
      }

      case 'llm_done': {
        store.isLoading = false
        const message = finishMessage(data, state)
        const replyText = String(data.reply_text || '').trim()
        if (message && opts?.onReplyDone && replyText) {
          opts.onReplyDone({
            text: data.reply_text,
            emotion: data.emotion,
            expression: data.expression,
            routePlan: data.route_plan,
            citations: message.citations,
            retrieval: message.retrieval,
            traceId: message.traceId,
            requestId: message.requestId,
          })
        }
        // 保留状态，等待新协议的 message_done 再清理；旧服务端没有该事件时由后续连接生命周期清理。
        break
      }

      case 'message_done':
        store.isLoading = false
        finishMessage(data, state)
        const messageId = String(data.message_id || '')
        const pendingState = pending.get(messageId)
        if (pendingState?.timeoutId) clearTimeout(pendingState.timeoutId)
        pending.delete(messageId)
        break

      case 'error': {
        // 外层已经按 seq 完成去重；不能再次 getPending，否则重复事件会返回 null。
        const messageId = String(data.message_id || '')
        const errorState = state || (messageId ? pending.get(messageId) : null)
        const fallback = String(data.message || i18n.global.t('chat.unavailable'))
        if (errorState) {
          const message = ensureAssistant(errorState, fallback)
          message.content = fallback
          applyRetrieval(errorState, data)
          message.sources = errorState.sources
          message.citations = errorState.citations
          message.retrieval = errorState.retrieval
          message.traceId = errorState.traceId
          message.requestId = errorState.requestId
        } else {
          store.addMessage({ id: crypto.randomUUID(), role: 'assistant', content: fallback, timestamp: Date.now() })
        }
        store.isLoading = false
            if (messageId) {
          const pendingState = pending.get(messageId)
          if (pendingState?.timeoutId) clearTimeout(pendingState.timeoutId)
          pending.delete(messageId)
        }
        break
      }
    }
  }

  function sendMessage(query: string, mode: 'text' | 'voice' = 'text') {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      disconnect()
      connect()
      const retryOnce = () => {
        if (ws && ws.readyState === WebSocket.OPEN) sendMessage(query, mode)
        else {
          console.error('WebSocket 连接失败，请确认后端服务已启动')
          store.isLoading = false
        }
      }
      setTimeout(retryOnce, 800)
      return
    }

    store.isLoading = true
    store.addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: Date.now(),
    })

    ws.send(JSON.stringify({ query, mode, interests: store.interests, locale: i18n.global.locale.value }))
  }

  function disconnect() {
    if (ws) {
      const socket = ws
      ws = null
      socket.close()
    }
    isConnected.value = false
    store.wsConnected = false
    store.isLoading = false
    for (const state of pending.values()) {
      if (state.timeoutId) clearTimeout(state.timeoutId)
    }
    pending.clear()
  }

  watch(() => store.sessionId, () => {
    disconnect()
    connect()
  })

  onUnmounted(() => disconnect())

  return { isConnected, connect, sendMessage, disconnect }
}
