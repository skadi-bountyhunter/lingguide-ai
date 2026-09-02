<template>
  <!-- 魔珐星云 3D 数字人舞台（可复用组件，对外暴露 connect/speak/stop） -->
  <div class="xy-wrapper">
    <div class="xy-stage">
      <!-- 顶部小徽章：连接态 + 表情 -->
      <div class="xy-overlay-top">
        <div class="xy-conn" :class="connClass">
          <span class="xy-dot" />{{ connText }}
        </div>
        <div class="xy-status-tags">
          <div v-if="displayRoleName" class="xy-role">{{ displayRoleName }}</div>
          <div v-if="emotionTag" class="xy-emo">{{ emotionTag }}</div>
        </div>
      </div>

      <!-- SDK 挂载点（必须有 id，星云 SDK 依赖 containerId） -->
      <div :id="containerId" class="xy-render"></div>

      <!-- 未连接：中央"接通"提示 -->
      <div v-if="!sessionReady && !connecting" class="xy-cta">
        <div class="xy-cta-icon">🤖</div>
        <p class="xy-cta-hint">{{ t('avatar.wakeHint') }}</p>
        <button class="xy-cta-btn" @click="connect">{{ t('avatar.wake') }}</button>
      </div>

      <!-- 连接中 / 资源下载 -->
      <div v-if="connecting || downloading" class="xy-loading">
        <div class="xy-loading-spin" />
        <p v-if="downloading">{{ t('avatar.loading', { progress: dlProgress }) }}</p>
        <p v-else>{{ t('avatar.waking') }}</p>
        <div v-if="downloading" class="xy-dl-bar">
          <div class="xy-dl-fill" :style="{ width: dlProgress + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 状态条移到 stage 下方，不再被视频层遮挡 -->
    <div v-if="sessionReady" class="xy-status-bar">
      <div v-if="speaking" class="xy-speak">
        <span class="xy-wave"><i /><i /><i /><i /></span>
        <span>{{ t('avatar.speaking') }}</span>
      </div>
      <div v-else class="xy-idle">
        {{ t('avatar.idle') }}
        <button v-if="lastSpokenText" class="xy-stop-mini xy-replay-btn" @click="replay">{{ t('avatar.replay') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, defineExpose } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { i18n } from '../i18n'

const { t } = useI18n()

const props = defineProps<{
  containerId?: string  // 允许多实例（默认 xy-sdk）
  autoConnect?: boolean // 是否挂载时自动连接
}>()

const containerId = props.containerId || 'xy-sdk-chat'

// 星云凭据仅保存在后端环境变量；前端经同源会话代理建立 SDK 连接。
const SDK_URL = import.meta.env.VITE_XINGYUN_SDK_URL || 'https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js'
let sdkLoadPromise: Promise<void> | null = null

async function loadSdk() {
  if (window.XmovAvatar) return
  if (!SDK_URL) throw new Error(t('avatar.sdkMissing'))
  if (sdkLoadPromise) return sdkLoadPromise
  sdkLoadPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = SDK_URL
    script.onload = () => window.XmovAvatar ? resolve() : reject(new Error(t('avatar.sdkMissing')))
    script.onerror = () => reject(new Error(t('avatar.sdkMissing')))
    document.head.appendChild(script)
  }).catch((error) => {
    sdkLoadPromise = null
    throw error
  })
  return sdkLoadPromise
}

type ActiveAvatar = {
  preset_key: string
  name: string
  scene_label: string
  voice_label: string
  performance_style: string
  available: boolean
  unavailable_reason: string
  gateway_url: string
}

// ===== 状态 =====
const connecting = ref(false)
const sessionReady = ref(false)
const downloading = ref(false)
const dlProgress = ref(0)
const speaking = ref(false)
const emotionTag = ref('')
const connClass = ref('off')
const connText = ref(t('avatar.disconnected'))
const avatar = ref<ActiveAvatar | null>(null)

let sdk: any = null
let resizeObs: ResizeObserver | null = null

const displayRoleName = computed(() => {
  if (!avatar.value) return ''
  return avatar.value.preset_key === 'default_guide' ? t('avatar.defaultRole') : avatar.value.name
})

const EMOTION_KEY: Record<string, string> = {
  happy: 'avatar.happy',
  neutral: 'avatar.neutral',
  concerned: 'avatar.concerned',
}

/** 设置表情标签（外部消息驱动） */
function setEmotion(expression?: string) {
  if (!expression) return
  emotionTag.value = t(EMOTION_KEY[expression] || EMOTION_KEY.neutral)
}

/** 同步资源下载进度；当前 SDK 要求构造器和 init 都传入此回调。 */
function handleDownloadProgress(p: number) {
  downloading.value = true
  dlProgress.value = Math.round(p)
  if (p >= 100) downloading.value = false
}

/** 建立 SDK 连接 */
async function connect() {
  if (connecting.value || sessionReady.value) return
  connecting.value = true
  connText.value = t('avatar.readConfig'); connClass.value = 'wait'
  try {
    const { data } = await axios.get<ActiveAvatar>('/api/avatar/active', { params: { locale: i18n.global.locale.value } })
    avatar.value = data
    if (!data.available) {
      throw new Error(data.unavailable_reason || t('avatar.unavailable'))
    }
    await loadSdk()
    const Ctor = window.XmovAvatar
    if (!Ctor) throw new Error(t('avatar.sdkMissing'))
    connText.value = t('avatar.wakingRole', { name: displayRoleName.value })
    sdk = new Ctor({
      containerId: '#' + containerId,
      // 星云 SDK 仍要求此字段，但会话请求经后端代理重签，浏览器不持有长期密钥。
      appId: data.preset_key,
      appSecret: '',
      gatewayServer: data.gateway_url,
      hardwareAcceleration: 'prefer-hardware',
      enableLogger: false,
      onDownloadProgress: handleDownloadProgress,
      onVoiceStateChange(status: string) {
        if (status === 'start' || status === 'voice_start') speaking.value = true
        else if (status === 'end' || status === 'voice_end') speaking.value = false
      },
      onMessage(msg: any) {
        if (msg?.code) console.warn('[XY]', msg.message || msg.code)
      },
    })
    await sdk.init({
      initModel: 'normal',
      onDownloadProgress: handleDownloadProgress,
    })
    sessionReady.value = true
    downloading.value = false  // SDK 进度回调可能在100%前停止，强制清除
    connText.value = t('avatar.connected'); connClass.value = 'on'
    ElMessage.success(t('avatar.ready', { name: displayRoleName.value || t('chat.assistant') }))

    // 启动尺寸同步：观察容器变化后通知 SDK 重绘，不手动改写 canvas buffer
    const container = document.getElementById(containerId)
    if (container && 'ResizeObserver' in window) {
      resizeObs = new ResizeObserver(() => {
        try {
          const rect = container.getBoundingClientRect()
          if (typeof sdk?.resize === 'function') sdk.resize(rect.width, rect.height)
          else if (typeof sdk?.onResize === 'function') sdk.onResize(rect.width, rect.height)
        } catch {}
      })
      resizeObs.observe(container)
    }
  } catch (e: any) {
    console.error('[XY] connect failed:', e)
    connText.value = t('avatar.connectFailed'); connClass.value = 'off'
    ElMessage.error(t('avatar.failed', { message: e?.message || t('avatar.network') }))
  } finally {
    connecting.value = false
  }
}

const lastSpokenText = ref('')
const lastExpression = ref<string | undefined>(undefined)

/** 播报文本（自动复位待机态再播，避免 is_end 之后不能再 speak 的限制） */
function speak(text: string, expression?: string) {
  if (!sdk || !sessionReady.value || !text?.trim()) return
  setEmotion(expression)
  speaking.value = true  // 提前设置，避免interactive_idle触发voice_end导致状态间隙
  try {
    try { sdk.interactive_idle() } catch {}  // 总是重置SDK状态
    sdk.speak(text, true, true)
    lastSpokenText.value = text
    lastExpression.value = expression
  } catch (e) {
    speaking.value = false  // 失败则恢复
    console.warn('[XY] speak failed:', e)
  }
}

/** 停止当前播报，回到待命状态 */
function stop() {
  if (!sdk || !sessionReady.value) return
  speaking.value = false
  try { sdk.stopAudio(-1) } catch {}     // 立即清空音频缓冲
  try { sdk.interactive_idle() } catch {} // 重置动画状态机
}

/** 重播上一段讲解 */
function replay() {
  if (!lastSpokenText.value) return
  speak(lastSpokenText.value, lastExpression.value)
}

onMounted(() => {
  if (props.autoConnect) {
    // 等一帧确保 SDK script 已加载
    setTimeout(() => connect(), 300)
  }
})

onBeforeUnmount(() => {
  try { resizeObs?.disconnect() } catch {}
  resizeObs = null
  try { sdk?.destroy?.() } catch {}
  sdk = null
})

defineExpose({ connect, speak, stop, replay, setEmotion, isSpeaking: speaking })
</script>

<style scoped>
/* 外层容器：承载圆角/阴影，flex 列布局让状态条始终在 stage 下方 */
.xy-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(45, 106, 79, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.xy-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(160deg, #f4ede0 0%, #e8dcc4 45%, #d9c8a5 100%);
}

.xy-render {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}
/* SDK 注入的 canvas/video 填满容器；底部锚点让人物脚踏背景地面 */
.xy-render :deep(canvas),
.xy-render :deep(video) {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center bottom;
}
.xy-render :deep(> div) {
  width: 100%;
  height: 100%;
}

/* SDK 注入的字幕/遮罩容器 */
.xy-render :deep(.avatar-sdk-widget-container) {
  background: transparent !important;
  pointer-events: none !important;
}
/* 背景图与视频使用同一缩放策略（contain + center bottom），确保任意分辨率下二者等比对齐 */
.xy-render :deep(.avatar-sdk-widget-container) img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center bottom;
}
/* 说话时 SDK 动态注入的空遮罩容器（z:1000, 无 IMG 子元素），直接隐藏 */
.xy-render :deep(.avatar-sdk-widget-container:not(:has(img))) {
  display: none !important;
}

/* 顶部 overlay */
.xy-overlay-top {
  position: absolute;
  top: 12px; left: 12px; right: 12px;
  display: flex; align-items: center; justify-content: space-between;
  pointer-events: none;
  z-index: 5;
}
.xy-conn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.xy-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.xy-conn.on { color: var(--color-success); }
.xy-conn.on .xy-dot { animation: pulseDot 2s ease-in-out infinite; }
.xy-conn.wait { color: var(--color-warning); }
.xy-conn.off { color: var(--color-text-muted); }
.xy-status-tags { display: flex; align-items: center; gap: 6px; }
.xy-role, .xy-emo {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-primary);
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.xy-role { color: #6d4d22; background: rgba(255, 248, 232, 0.92); }

/* 未连接 CTA */
.xy-cta {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 14px;
  background: linear-gradient(160deg, rgba(244, 237, 224, 0.92), rgba(232, 220, 196, 0.92));
  backdrop-filter: blur(2px);
  z-index: 4;
}
.xy-cta-icon {
  width: 72px; height: 72px;
  display: flex; align-items: center; justify-content: center;
  font-size: 36px;
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 6px 24px rgba(45, 106, 79, 0.12);
}
.xy-cta-hint {
  font-size: 13px; color: var(--color-text-secondary);
}
.xy-cta-btn {
  padding: 10px 28px;
  border-radius: 999px;
  border: none;
  font-size: 13px; font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light, var(--color-primary)));
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(45, 106, 79, 0.25);
  transition: transform 0.2s, box-shadow 0.2s;
}
.xy-cta-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(45, 106, 79, 0.32); }
.xy-cta-btn:active { transform: translateY(0); }

/* 加载态 */
.xy-loading {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px;
  background: rgba(244, 237, 224, 0.85);
  backdrop-filter: blur(4px);
  z-index: 4;
  font-size: 12px; color: var(--color-text-secondary);
}
.xy-loading-spin {
  width: 32px; height: 32px;
  border: 3px solid rgba(45, 106, 79, 0.15);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: xySpin 0.9s linear infinite;
}
.xy-dl-bar {
  width: 160px; height: 4px;
  background: rgba(0, 0, 0, 0.06);
  border-radius: 2px;
  overflow: hidden;
}
.xy-dl-fill {
  height: 100%;
  background: linear-gradient(to right, var(--color-primary), #66a982);
  transition: width 0.3s ease;
}

/* 状态条：stage 下方独立区域，永不被视频遮挡 */
.xy-status-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 16px;
  min-height: 36px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}
.xy-speak, .xy-idle {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 500;
}
.xy-idle { color: var(--color-text-muted); }
.xy-speak { color: var(--color-primary); }
.xy-wave { display: inline-flex; align-items: flex-end; gap: 2px; height: 12px; }
.xy-wave i {
  width: 2px; height: 100%;
  background: var(--color-primary);
  border-radius: 1px;
  animation: xyWave 1s ease-in-out infinite;
}
.xy-wave i:nth-child(2) { animation-delay: 0.15s; }
.xy-wave i:nth-child(3) { animation-delay: 0.3s; }
.xy-wave i:nth-child(4) { animation-delay: 0.45s; }
.xy-stop-mini {
  margin-left: 4px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
  font-size: 10px; font-weight: 600;
  cursor: pointer;
}
.xy-stop-mini:hover { background: var(--color-error); color: #fff; }

@keyframes xySpin { to { transform: rotate(360deg); } }
@keyframes pulseDot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.4); }
}
@keyframes xyWave {
  0%, 100% { height: 30%; }
  50% { height: 100%; }
}
</style>
