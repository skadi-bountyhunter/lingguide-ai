<template>
  <div class="chat-page">
    <!-- 顶栏 -->
    <header class="chat-header">
      <div class="header-center">
        <div class="avatar-dot"><img src="/images/features/ai-guide.jpg" alt="AI导游" class="avatar-img" /></div>
        <div>
          <p class="h-name">{{ t('chat.title') }}</p>
          <div class="h-status">
            <span class="status-dot" :class="{ on: wsConn }" />
            <span>{{ wsConn ? t('chat.online') : t('chat.offline') }}</span>
            <span class="dh-toggle-hint" v-if="!dhEnabled">·</span>
            <button v-if="!dhEnabled" class="dh-toggle" @click="enableDh">{{ t('chat.enableAvatar') }}</button>
            <button v-else class="dh-toggle dh-toggle-on" @click="disableDh">{{ t('chat.disableAvatar') }}</button>
          </div>
        </div>
      </div>
      <button class="new-chat-btn" :title="t('chat.newChat')" @click="startNewSession">
        <el-icon><Refresh /></el-icon>
      </button>
    </header>

    <!-- 主体：左数字人 + 右对话 -->
    <div class="chat-main" :class="{ 'with-dh': dhEnabled }">
      <!-- 左侧：3D 数字人舞台 -->
      <aside v-if="dhEnabled" class="dh-panel">
        <XingyunStage ref="stageRef" auto-connect />
      </aside>

      <!-- 右侧：消息流 + 输入栏 -->
      <section class="chat-panel">
        <!-- Messages -->
        <div class="msg-area" ref="msgContainer">
          <!-- Empty State -->
          <div v-if="store.messages.length === 0" class="empty-state">
            <div class="empty-avatar"><img src="/images/features/ai-guide.jpg" alt="AI导游" class="avatar-img" /></div>
            <h2>{{ t('chat.hello') }} 👋</h2>
            <p>{{ t('chat.intro') }}</p>
            <div class="quick-list">
              <button v-for="(q, i) in quickQuestions" :key="i" @click="sendText(q.q)">
                <span class="q-icon">{{ q.icon }}</span>{{ q.q }}
              </button>
            </div>
          </div>

          <!-- Message List -->
          <div v-for="msg in store.messages" :key="msg.id" class="msg-row" :class="msg.role">
            <div v-if="msg.role === 'assistant'" class="msg-avatar"><img src="/images/features/ai-guide.jpg" alt="AI导游" class="avatar-img" /></div>
            <div class="msg-bubble" :class="msg.role">
              <span v-if="msg.role === 'assistant'" class="bubble-name">{{ t('chat.assistant') }}</span>
              <p class="bubble-text">{{ msg.content }}</p>
              <details v-if="msg.role === 'assistant' && msg.citations?.length" class="citation-box">
                <summary>{{ t('chat.references', { count: msg.citations.length }) }}</summary>
                <div v-for="citation in msg.citations" :key="citation.id" class="citation-item">
                  <div class="citation-title">{{ citation.id }} · {{ citation.source?.title || citation.source?.filename || t('chat.scenicSource') }}</div>
                  <div class="citation-quote">{{ citation.quote }}</div>
                  <div class="citation-meta">
                    {{ citation.evidence_type || citation.retrieval?.route || 'retrieval' }}
                    <span v-if="citation.locator?.section"> · {{ citation.locator.section }}</span>
                    <span v-if="citation.locator?.page"> · {{ t('chat.page', { page: citation.locator.page }) }}</span>
                    <span v-else-if="citation.locator?.char_start != null"> · {{ t('chat.fragment', { start: citation.locator.char_start, end: citation.locator.char_end }) }}</span>
                    <span v-if="citation.as_of"> · {{ t('chat.dataTime', { time: citation.as_of }) }}</span>
                  </div>
                </div>
              </details>
              <p v-if="msg.role === 'assistant' && msg.retrieval?.degraded" class="answer-status">
                {{ t('chat.degraded', { reason: msg.retrieval?.fallback_reason || t('chat.partialUnavailable') }) }}
              </p>
              <p v-else-if="msg.role === 'assistant' && msg.retrieval?.citation_validation === 'no_evidence'" class="answer-status">
                {{ t('chat.noEvidence') }}
              </p>
              <!-- 操作区（仅 assistant） -->
              <div v-if="msg.role === 'assistant'" class="bubble-actions">
                <button v-if="dhEnabled" @click="speakByDh(msg)">
                  <el-icon><VideoPlay /></el-icon>
                  {{ t('chat.avatarSpeak') }}
                </button>
                <button @click="playTTS(msg)">
                  <el-icon><Headset /></el-icon>
                  {{ playingState[msg.id] ? t('chat.pauseVoice') : pausedState[msg.id] ? t('chat.resumeVoice') : t('chat.voice') }}
                </button>
                <button @click="copyText(msg.content)">
                  <el-icon><CopyDocument /></el-icon>{{ t('chat.copy') }}
                </button>
                <button
                  v-if="msg.routePlan"
                  class="route-btn"
                  @click="goToRoute(msg)"
                  :title="t('chat.routeRecommend')"
                >
                  <el-icon><Guide /></el-icon>{{ t('chat.routeRecommend') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Loading Dots -->
          <div v-if="store.isLoading" class="msg-row assistant">
            <div class="msg-avatar"><img src="/images/features/ai-guide.jpg" alt="AI导游" class="avatar-img" /></div>
            <div class="loading-bubble">
              <span class="dot" /><span class="dot" /><span class="dot" />
            </div>
          </div>
        </div>

        <!-- 输入栏 -->
        <div class="input-bar">
          <div class="input-row">
            <button class="voice-btn" :class="{ recording: isRecording }" @click="toggleVoice">
              <el-icon><Microphone /></el-icon>
            </button>
            <input
              v-model="inputText"
              type="text"
              :placeholder="t('chat.input')"
              :disabled="store.isLoading"
              @keydown.enter="sendText(inputText)"
            />
            <button
              class="send-btn"
              :disabled="!inputText.trim() || store.isLoading"
              @click="sendText(inputText)"
            >
              <el-icon><Promotion /></el-icon>
            </button>
          </div>
          <p class="input-hint">
            {{ t('chat.inputHint') }}
            <span v-if="dhEnabled"> {{ t('chat.avatarAuto') }}</span>
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useChatStore } from '../stores/chat'
import { useWebSocket, type ReplyDonePayload } from '../composables/useWebSocket'
import type { ChatMessage } from '../stores/chat'
import type { RoutePlan } from '../types/route'
import XingyunStage from '../components/XingyunStage.vue'
import { authorizationHeaders } from '../services/profile'
import { useVoiceSettings } from '../composables/useVoiceSettings'
import { i18n } from '../i18n'

const store = useChatStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { settings: voiceSettings } = useVoiceSettings()

const inputText = ref('')
const msgContainer = ref<HTMLElement>()
const stageRef = ref<InstanceType<typeof XingyunStage> | null>(null)

/** 数字人启停（默认开启；用户可手动关闭以节省并发额度） */
const dhEnabled = ref(true)

/** WS 收到 llm_done 时自动驱动数字人播报 */
function onReplyDone(p: ReplyDonePayload) {
  if (!dhEnabled.value) return
  stageRef.value?.speak(p.text, p.expression)
}

const { isConnected: wsConn, connect, sendMessage } = useWebSocket({ onReplyDone })

function startNewSession() {
  store.newSession()
}

/** TTS 独立控制（保留原浏览器音频播放能力） */
const playingState = reactive<Record<string, boolean>>({})
const pausedState = reactive<Record<string, boolean>>({})
const audioMap = new Map<string, HTMLAudioElement>()

/** 点击消息气泡内"数字人播报" */
function speakByDh(msg: ChatMessage) {
  stageRef.value?.speak(msg.content, msg.expression)
}

const quickQuestions = computed(() => [
  { q: t('chat.quick1'), icon: '🗿' },
  { q: t('chat.quick2'), icon: '✨' },
  { q: t('chat.quick3'), icon: '🐉' },
  { q: t('chat.quick4'), icon: '🗺️' },
  { q: t('chat.quick5'), icon: '📜' },
])

onMounted(() => {
  connect()
  const query = typeof route.query.q === 'string' ? route.query.q.trim() : ''
  if (query) {
    inputText.value = query
    router.replace({ name: 'chat' })
  }
})

watch(() => store.messages.length, async () => {
  await nextTick()
  if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight
})

function sendText(text: string) {
  if (!text.trim() || store.isLoading) return
  sendMessage(text.trim(), 'text')
  inputText.value = ''
}

function enableDh() {
  dhEnabled.value = true
  ElMessage.success(t('chat.avatarEnabled'))
}
function disableDh() {
  // 关闭前先停止当前播报
  stageRef.value?.stop()
  dhEnabled.value = false
  ElMessage.info(t('chat.avatarDisabled'))
}

// ==== 浏览器端 TTS 播放（保留原能力） ====
async function playTTS(msg: ChatMessage) {
  const exist = audioMap.get(msg.id)
  if (exist) {
    if (pausedState[msg.id]) {
      // 继续播放
      await exist.play()
      pausedState[msg.id] = false
      playingState[msg.id] = true
    } else {
      // 暂停（保留 Audio 对象和进度）
      exist.pause()
      pausedState[msg.id] = true
      playingState[msg.id] = false
    }
    return
  }
  playingState[msg.id] = true
  const audio = new Audio()
  audioMap.set(msg.id, audio)
  audio.onended = () => {
    if (audio.src.startsWith('blob:')) URL.revokeObjectURL(audio.src)
    audioMap.delete(msg.id)
    delete playingState[msg.id]
    delete pausedState[msg.id]
  }
  audio.onerror = () => {
    ElMessage.warning(t('chat.ttsFailed'))
    audioMap.delete(msg.id)
    delete playingState[msg.id]
    delete pausedState[msg.id]
    URL.revokeObjectURL(audio.src)
  }

  try {
    const res = await fetch(`/api/chat/audio/${store.sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authorizationHeaders() },
      body: JSON.stringify({ text: msg.content, voice_key: voiceSettings.value.voiceKey, rate: voiceSettings.value.rate, locale: i18n.global.locale.value }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    audio.src = URL.createObjectURL(blob)
    audio.volume = voiceSettings.value.volume
    await audio.play()
  } catch {
    ElMessage.warning(t('chat.ttsFailed'))
    audioMap.delete(msg.id)
    delete playingState[msg.id]
    delete pausedState[msg.id]
  }
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success(t('chat.copied'))).catch(() => {})
}

/** 跳转到路线页；先移除响应式代理，确保浏览器可克隆 history state。 */
function goToRoute(msg: ChatMessage) {
  if (!msg.routePlan) return
  const snapshot = JSON.parse(JSON.stringify(msg.routePlan)) as RoutePlan
  router.push({
    name: 'route',
    query: { from: 'chat' },
    state: { route_plan: snapshot as any },
  })
}

// ==== Voice Input (PCM WAV → 科大讯飞) ====
const isRecording = ref(false)
let audioCtx: AudioContext | null = null
let scriptNode: ScriptProcessorNode | null = null
let stream: MediaStream | null = null
let pcmSamples: Float32Array[] = []
let recordingSampleRate = 16000

function encodeWAV(samples: Float32Array, sampleRate: number): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buf)
  const w = (off: number, s: string) => { for (let i=0;i<s.length;i++) view.setUint8(off+i, s.charCodeAt(i)) }
  w(0, 'RIFF'); view.setUint32(4, 36+samples.length*2, true); w(8, 'WAVE')
  w(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true)
  view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate*2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  w(36, 'data'); view.setUint32(40, samples.length*2, true)
  let off = 44
  for (let i=0;i<samples.length;i++,off+=2) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(off, s<0?s*0x8000:s*0x7FFF, true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}

async function resampleTo16k(samples: Float32Array, fromRate: number): Promise<Float32Array> {
  if (fromRate === 16000) return samples
  const duration = samples.length / fromRate
  const targetLen = Math.floor(duration * 16000)
  const offline = new OfflineAudioContext(1, targetLen, 16000)
  const buffer = offline.createBuffer(1, samples.length, fromRate)
  buffer.copyToChannel(samples as any, 0)
  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start()
  const rendered = await offline.startRendering()
  return rendered.getChannelData(0)
}

async function toggleVoice() {
  if (isRecording.value) {
    scriptNode?.disconnect()
    await audioCtx?.close().catch(() => {})
    stream?.getTracks().forEach(t => t.stop())
    isRecording.value = false

    if (pcmSamples.length === 0) {
      ElMessage.warning(t('chat.noVoice'))
      return
    }
    const totalLen = pcmSamples.reduce((a,c) => a + c.length, 0)
    const merged = new Float32Array(totalLen)
    let off = 0
    for (const c of pcmSamples) { merged.set(c, off); off += c.length }
    const resampled = await resampleTo16k(merged, recordingSampleRate)
    const wavBlob = encodeWAV(resampled, 16000)
    pcmSamples = []
    console.log(`Voice: ${totalLen}@${recordingSampleRate}Hz → ${resampled.length}@16000Hz, WAV:${wavBlob.size}bytes`)
    await sendVoiceToServer(wavBlob)
    return
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: { ideal: 16000 }, channelCount: { ideal: 1 } } })
    audioCtx = new AudioContext()
    recordingSampleRate = audioCtx.sampleRate
    const source = audioCtx.createMediaStreamSource(stream)
    scriptNode = audioCtx.createScriptProcessor(4096, 1, 1)
    pcmSamples = []
    scriptNode.onaudioprocess = (e) => {
      pcmSamples.push(new Float32Array(e.inputBuffer.getChannelData(0)))
    }
    source.connect(scriptNode); scriptNode.connect(audioCtx.destination)
    isRecording.value = true
    ElMessage.success(t('chat.listening'))
  } catch {
    ElMessage.warning(t('chat.microphoneDenied'))
  }
}

async function sendVoiceToServer(wavBlob: Blob) {
  const fd = new FormData()
  fd.append('audio', wavBlob, 'recording.wav')
  fd.append('session_id', store.sessionId)
  fd.append('interests', JSON.stringify(store.interests))
  fd.append('locale', i18n.global.locale.value)
  store.isLoading = true
  try {
    const res = await fetch('/api/chat/voice', { method: 'POST', headers: authorizationHeaders(), body: fd })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.query_text) {
      store.addMessage({ id: crypto.randomUUID(), role: 'user', content: data.query_text, timestamp: Date.now() })
    }
    if (data.reply) {
      store.addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.reply,
        emotion: data.emotion,
        expression: data.expression,
        routePlan: data.route_plan,
        sources: Array.isArray(data.sources) ? data.sources : [],
        citations: Array.isArray(data.citations) ? data.citations : [],
        retrieval: data.retrieval,
        traceId: data.trace_id,
        timestamp: Date.now(),
      })
      // 语音通道也驱动数字人播报
      if (dhEnabled.value) stageRef.value?.speak(data.reply, data.expression)
    }
  } catch (e: any) {
    ElMessage.error(t('chat.asrFailed', { message: e.message || t('common.retry') }))
  } finally {
    store.isLoading = false
  }
}

onUnmounted(() => {
  scriptNode?.disconnect()
  void audioCtx?.close().catch(() => {})
  stream?.getTracks().forEach(track => track.stop())
  for (const [, audio] of audioMap) {
    audio.pause()
    if (audio.src.startsWith('blob:')) URL.revokeObjectURL(audio.src)
    audio.src = ''
  }
  audioMap.clear()
})
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px);
  width: 100%;
}

/* Header */
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 24px;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,0.04);
  flex-shrink: 0;
}
.header-center { display: flex; align-items: center; gap: 10px; }
.avatar-dot {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--color-primary-bg);
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; overflow: hidden;
}
.h-name { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); line-height: 1.2; }
.h-status { display: flex; align-items: center; gap: 6px; font-size: 10px; color: var(--color-success); font-weight: 500; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-text-muted); }
.status-dot.on { background: var(--color-success); animation: pulseSoft 2.5s ease-in-out infinite; }
.dh-toggle-hint { color: var(--color-text-muted); margin: 0 2px; }
.dh-toggle {
  border: 1px solid var(--color-primary-border, rgba(45,106,79,0.25));
  background: transparent;
  color: var(--color-primary);
  font-size: 10px; font-weight: 600;
  padding: 2px 8px; border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}
.dh-toggle:hover { background: var(--color-primary-bg); }
.dh-toggle-on { background: var(--color-primary); color: #fff; }
.dh-toggle-on:hover { background: var(--color-primary); opacity: 0.85; }
.new-chat-btn {
  width: 32px; height: 32px; border-radius: 8px;
  border: none; background: none; cursor: pointer;
  color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
}
.new-chat-btn:hover { color: var(--color-primary); background: var(--color-primary-bg); }

/* 主体双栏 */
.chat-main {
  flex: 1;
  min-height: 0;
  display: flex;
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: 16px;
  gap: 16px;
  box-sizing: border-box;
}
.chat-main:not(.with-dh) {
  max-width: 720px;
  padding: 0;
}

/* 数字人左栏 */
.dh-panel {
  flex: 0 0 38%;
  max-width: 460px;
  min-width: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  /* 限制内部 stage 的最大高度，避免数字人比例过高造成上下大量留白 */
}
.dh-panel > * {
  width: 100%;
  height: 100%;
}

/* 对话右栏 */
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}
.chat-main:not(.with-dh) .chat-panel {
  background: transparent;
  border-radius: 0;
  box-shadow: none;
}

/* 地图折叠区样式已移除：路线改由 /route 页面承载，避免移动端布局拥挤 */
.route-btn { color: var(--color-accent) !important; }
.route-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Messages */
.msg-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Empty State */
.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; text-align: center; }
.empty-avatar { width: 80px; height: 80px; border-radius: 22px; background: #fff; display: flex; align-items: center; justify-content: center; margin-bottom: 20px; box-shadow: 0 6px 24px rgba(45,106,79,0.1); overflow: hidden; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; border-radius: inherit; display: block; }
.empty-state h2 { font-size: 1.25rem; font-weight: 700; color: var(--color-text-primary); margin-bottom: 6px; }
.empty-state > p { font-size: 0.875rem; color: var(--color-text-muted); max-width: 280px; line-height: 1.6; margin-bottom: 28px; }
.quick-list { width: 100%; max-width: 320px; display: flex; flex-direction: column; gap: 8px; }
.quick-list button { width: 100%; text-align: left; padding: 12px 16px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.04); background: #fff; cursor: pointer; font-size: 0.875rem; color: var(--color-text-secondary); transition: all 0.3s; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
.quick-list button:hover { border-color: var(--color-primary-border); background: var(--color-primary-bg); color: var(--color-primary); }
.q-icon { margin-right: 8px; }

/* Message Bubbles */
.msg-row { display: flex; align-items: flex-start; gap: 8px; animation: fadeUp 0.4s ease-out forwards; }
.msg-row.user { justify-content: flex-end; }
.msg-avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--color-primary-bg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 4px; font-size: 0.75rem; overflow: hidden; }
.msg-bubble { max-width: 80%; border-radius: 16px; padding: 12px 16px; }
.msg-bubble.user { background: var(--color-primary); color: #fff; border-bottom-right-radius: 4px; }
.msg-bubble.assistant { background: #fff; border: 1px solid rgba(0,0,0,0.04); border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.bubble-name { font-size: 10px; font-weight: 600; color: var(--color-primary); display: block; margin-bottom: 6px; }
.bubble-text { font-size: 13px; line-height: 1.65; white-space: pre-wrap; word-break: break-word; }
.citation-box { margin-top: 10px; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 8px; font-size: 11px; color: var(--color-text-muted); }
.citation-box summary { cursor: pointer; color: var(--color-primary); font-weight: 600; }
.citation-item { margin-top: 8px; padding: 8px; border-radius: 8px; background: var(--color-bg-input); }
.citation-title { font-weight: 600; color: var(--color-text-secondary); }
.citation-quote { margin-top: 4px; line-height: 1.5; }
.citation-meta { margin-top: 4px; opacity: 0.8; }
.answer-status { margin: 8px 0 0; color: #a15c00; font-size: 11px; line-height: 1.5; }
.bubble-actions { display: flex; align-items: center; gap: 16px; margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.04); flex-wrap: wrap; }
.bubble-actions button { display: flex; align-items: center; gap: 6px; border: none; background: none; cursor: pointer; font-size: 11px; color: var(--color-text-muted); transition: color 0.2s; padding: 0; }
.bubble-actions button:hover { color: var(--color-primary); }

/* Loading */
.loading-bubble { background: #fff; border-radius: 16px; border-bottom-left-radius: 4px; padding: 20px; display: flex; align-items: center; gap: 6px; border: 1px solid rgba(0,0,0,0.04); box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(45,106,79,0.4); animation: dotBounce 1.2s ease-in-out infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

/* Input Bar */
.input-bar { padding: 14px 20px; background: rgba(255,255,255,0.8); backdrop-filter: blur(12px); border-top: 1px solid rgba(0,0,0,0.04); }
.input-row { display: flex; align-items: center; gap: 10px; }
.input-row input { flex: 1; padding: 10px 16px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.04); background: var(--color-bg-input); font-size: 0.875rem; color: var(--color-text-primary); outline: none; transition: all 0.3s; }
.input-row input:focus { border-color: var(--color-primary-border); box-shadow: 0 0 0 3px rgba(45,106,79,0.1); }
.input-row input::placeholder { color: var(--color-text-muted); }
.input-row input:disabled { opacity: 0.5; }
.voice-btn { width: 40px; height: 40px; border-radius: 12px; border: none; background: var(--color-primary-bg); color: var(--color-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.voice-btn.recording { background: var(--color-error); color: #fff; }
.send-btn { width: 40px; height: 40px; border-radius: 12px; border: none; background: var(--color-primary); color: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.send-btn:active { transform: scale(0.95); }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.input-hint { text-align: center; font-size: 10px; color: var(--color-text-muted); margin-top: 8px; }

/* ===== 响应式：窄屏（< 960px）切换为上下布局，数字人在上 ===== */
@media (max-width: 960px) {
  .chat-main {
    flex-direction: column;
    padding: 12px;
    gap: 12px;
  }
  .dh-panel {
    flex: 0 0 auto;
    width: 100%;
    max-width: none;
    height: 38vh;
    min-height: 280px;
  }
  .chat-panel {
    flex: 1;
    min-height: 0;
  }
}

/* 超窄屏（< 600px）：进一步压缩数字人高度 */
@media (max-width: 600px) {
  .chat-main { padding: 8px; gap: 8px; }
  .chat-header { padding: 12px 16px; }
  .dh-panel { height: 32vh; min-height: 240px; }
  .msg-area { padding: 16px; }
  .input-bar { padding: 12px 16px; }
}
</style>
