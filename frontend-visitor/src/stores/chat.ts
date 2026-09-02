import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RoutePlan } from '../types/route'
import type { Citation, RetrievalTrace } from '../types/retrieval'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  emotion?: string
  expression?: string
  routePlan?: RoutePlan
  sources?: string[]
  citations?: Citation[]
  retrieval?: RetrievalTrace
  traceId?: string
  requestId?: string
  timestamp: number
}

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(crypto.randomUUID())
  const sessionToken = ref(crypto.randomUUID() + crypto.randomUUID())
  const interests = ref<string[]>([])
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const wsConnected = ref(false)

  const lastAssistantMessage = computed(() => {
    const msgs = messages.value.filter(m => m.role === 'assistant')
    return msgs[msgs.length - 1] || null
  })

  function addMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  function clearMessages() {
    messages.value = []
  }

  function newSession() {
    sessionId.value = crypto.randomUUID()
    sessionToken.value = crypto.randomUUID() + crypto.randomUUID()
    clearMessages()
  }

  return {
    sessionId,
    sessionToken,
    interests,
    messages,
    isLoading,
    wsConnected,
    lastAssistantMessage,
    addMessage,
    clearMessages,
    newSession,
  }
})
