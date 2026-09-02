<template>
  <div class="route-page">
    <!-- Header -->
    <header class="route-header">
      <h1>{{ t('routePage.title') }}</h1>
    </header>

    <div class="route-content">
      <!-- Map Module -->
      <ScenicMap ref="mapRef" :active-route="activeRoute" />

      <!-- AI Planning -->
      <div class="card ai-card">
        <div class="ai-header">
          <div class="ai-icon"><img src="/images/features/route.jpg" alt="AI规划" /></div>
          <div>
            <h2>{{ t('routePage.aiPlan') }}</h2>
            <p>{{ t('routePage.aiDesc') }}</p>
          </div>
        </div>

        <p class="label-text">{{ t('routePage.interests') }}</p>
        <div class="tag-group">
          <button v-for="item in interestOptions" :key="item.key"
            :class="{ active: aiInterests.includes(item.key) }"
            @click="toggleKey(item.key, aiInterests)">
            {{ item.icon }} {{ interestLabel(item.label) }}
          </button>
        </div>

        <p class="label-text">{{ t('routePage.duration') }}</p>
        <div class="duration-group">
          <button :class="{ active: aiDuration === '半天' }" @click="aiDuration = '半天'">☀️ {{ t('routePage.halfDay') }}</button>
          <button :class="{ active: aiDuration === '全天' }" @click="aiDuration = '全天'">🌅 {{ t('routePage.fullDay') }}</button>
        </div>

        <button class="plan-btn" :disabled="aiLoading" @click="() => generateRoute()">
          <span v-if="aiLoading" class="loading-text">
            <el-icon class="is-loading"><Loading /></el-icon> {{ loadingStepText }}
          </span>
          <span v-else>✨ {{ t('routePage.plan') }}</span>
        </button>

        <div v-if="aiError" class="planning-error" role="alert">
          <span>{{ aiError }}</span>
          <button type="button" :disabled="aiLoading" @click="retryGenerateRoute">{{ t('routePage.replan') }}</button>
        </div>
      </div>

      <!-- Generated Route -->
      <RoutePlanCard
        v-if="aiRouteData"
        :route="aiRouteData"
        mode="generated"
        :saved="generatedSavedId !== null"
        :saving="savingRoute"
        :editable="true"
        @save="saveGeneratedRoute"
        @show-map="showRouteOnMap(aiRouteData)"
        @update:spots="updateRouteSpots"
        @recalculate="recalculateRoute"
        @add-spot="openAddSpotDialog"
        @focus-spot="focusSpotOnMap"
      />

      <!-- 备选方案入口 -->
      <button
        v-if="aiRouteData && alternativeRoutes.length > 0"
        class="compare-trigger"
        @click="showCompareDialog = true"
      >
        <span>🔀</span>
        <span>还有 {{ alternativeRoutes.length }} 个备选方案可供对比</span>
        <el-icon><ArrowRight /></el-icon>
      </button>

      <!-- 实时优化建议 -->
      <div v-if="aiRouteData && routeSuggestion" class="suggestion-card">
        <div class="suggestion-icon">{{ routeSuggestion.icon }}</div>
        <div class="suggestion-text">
          <strong>{{ routeSuggestion.title }}</strong>
          <p>{{ routeSuggestion.message }}</p>
        </div>
        <button class="suggestion-dismiss" @click="dismissSuggestion">×</button>
      </div>

      <!-- 路线对比对话框 -->
      <el-dialog
        v-model="showCompareDialog"
        title="路线方案对比"
        width="95%"
        :style="{ maxWidth: '600px' }"
      >
        <div class="compare-list">
          <!-- 当前方案 -->
          <div class="compare-item current">
            <div class="compare-badge">当前方案</div>
            <h4>{{ aiRouteData?.title }}</h4>
            <div class="compare-meta">
              <span>🕐 {{ aiRouteData?.duration }}</span>
              <span>📍 {{ aiRouteData?.spots?.length }} 个景点</span>
            </div>
            <div class="compare-spots">
              <span v-for="(spot, i) in aiRouteData?.spots" :key="i">
                {{ i + 1 }}. {{ spot.display_name || spot.name }}
              </span>
            </div>
            <p v-if="aiRouteData?.tips" class="compare-tips">{{ aiRouteData?.tips }}</p>
          </div>

          <!-- 备选方案 -->
          <div
            v-for="(alt, index) in alternativeRoutes"
            :key="index"
            class="compare-item"
          >
            <div class="compare-badge alt">方案 {{ index + 2 }}</div>
            <h4>{{ alt.title }}</h4>
            <div class="compare-meta">
              <span>🕐 {{ alt.duration }}</span>
              <span>📍 {{ alt.spots?.length }} 个景点</span>
            </div>
            <div class="compare-spots">
              <span v-for="(spot, i) in alt.spots" :key="i">
                {{ i + 1 }}. {{ spot.display_name || spot.name }}
              </span>
            </div>
            <p v-if="alt.tips" class="compare-tips">{{ alt.tips }}</p>
            <button class="select-alt-btn" @click="selectAlternativeRoute(alt)">
              选择此方案
            </button>
          </div>
        </div>
      </el-dialog>

      <!-- 添加景点浮层 -->
      <el-dialog
        v-model="showAddSpotDialog"
        title="添加景点"
        width="90%"
        :style="{ maxWidth: '500px' }"
      >
        <div class="add-spot-search">
          <el-input
            v-model="spotSearchQuery"
            placeholder="搜索景点..."
            clearable
            @input="filterAvailableSpots"
          />
        </div>
        <div class="spot-list">
          <button
            v-for="spot in filteredAvailableSpots"
            :key="spot.name"
            class="spot-item"
            :disabled="isSpotInRoute(spot.name)"
            @click="addSpotToRoute(spot)"
          >
            <span class="spot-name">{{ spot.name }}</span>
            <span v-if="isSpotInRoute(spot.name)" class="spot-added">已添加</span>
          </button>
          <div v-if="filteredAvailableSpots.length === 0" class="no-spots">
            未找到景点
          </div>
        </div>
      </el-dialog>

      <!-- Saved Routes -->
      <section class="saved-section">
        <div class="section-title saved-title">
          <div class="section-heading"><span>📌</span><h2>{{ t('routePage.savedRoutes') }}</h2></div>
          <span v-if="savedRoutes.length" class="saved-count">{{ t('routePage.count', { count: savedRoutes.length }) }}</span>
        </div>

        <div v-if="savedRoutesLoading" class="saved-state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ t('routePage.loadingSaved') }}</span>
        </div>
        <div v-else-if="savedRoutesError" class="saved-state error-state" role="alert">
          <span>{{ savedRoutesError }}</span>
          <button type="button" @click="loadSavedRoutes">{{ t('routePage.reload') }}</button>
        </div>
        <div v-else-if="savedRoutes.length === 0" class="saved-state empty-state">
          <span>{{ t('routePage.emptySaved') }}</span>
        </div>
        <div v-else class="saved-route-list">
          <RoutePlanCard
            v-for="savedRoute in savedRoutes"
            :key="savedRoute.id"
            :route="savedRoute"
            mode="saved"
            :created-at="savedRoute.created_at"
            :deleting="deletingRouteId === savedRoute.id"
            @show-map="showRouteOnMap(savedRoute)"
            @delete="removeSavedRoute(savedRoute)"
            @focus-spot="focusSpotOnMap"
          />
        </div>
      </section>

      <!-- Preset Routes -->
      <div class="preset-section">
        <div class="section-title">
          <span>📋</span><h2>{{ t('routePage.presets') }}</h2>
        </div>
        <div class="filter-scroll">
          <button v-for="tag in filterTags" :key="tag"
            :class="{ active: routeFilter === tag }" @click="routeFilter = tag">{{ filterLabel(tag) }}</button>
        </div>
        <div class="route-list">
          <div v-for="(r, idx) in filteredRoutes" :key="r.title" class="card card-interactive route-card"
            :style="{ animationDelay: `${0.05 + idx * 0.06}s` }">
            <div class="rc-top">
              <div class="rc-icon"><span>{{ r.icon }}</span></div>
              <div class="rc-info">
                <h3>{{ r.display_title || r.title }}</h3>
                <div class="rc-meta">
                  <span><el-icon><Clock /></el-icon>{{ r.display_duration || r.duration }}</span>
                  <span><el-icon><LocationFilled /></el-icon>{{ r.display_distance || r.distance }}</span>
                </div>
              </div>
              <span class="rc-difficulty">{{ r.display_difficulty || r.difficulty }}</span>
            </div>
            <p class="rc-desc">{{ r.display_desc || r.desc }}</p>
            <div class="rc-spots">
              <span v-for="(s, spotIndex) in (r.display_spots || r.spots)" :key="r.spots[spotIndex] || s">📍 {{ s }}</span>
            </div>
            <div class="rc-tip"><span>💡</span>{{ r.display_tip || r.tip }}</div>
            <button class="show-on-map-btn" @click="showPresetOnMap(r)">
              <el-icon><Guide /></el-icon> {{ t('routePage.showOnMap') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div style="height: 80px" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import ScenicMap from '../components/ScenicMap.vue'
import RoutePlanCard from '../components/RoutePlanCard.vue'
import { useChatStore } from '../stores/chat'
import { i18n } from '../i18n'
import { fetchSpots } from '../data/spots'
import { deleteSavedRoute, fetchSavedRoutes, saveRoute } from '../services/savedRoutes'
import type { ActiveMapRoute, PresetRoute, RoutePlan, RouteSpot, SavedRoute } from '../types/route'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const { t, tm } = useI18n()

const aiInterests = ref<string[]>([])
const aiDuration = ref('半天')
const aiLoading = ref(false)
const aiError = ref('')
const loadingStepIndex = ref(0)
let loadingStepTimer: number | null = null

const loadingStepText = computed(() => {
  const steps = tm('routePage.loadingSteps') as unknown as string[]
  return Array.isArray(steps) && steps.length ? steps[loadingStepIndex.value % steps.length] : t('routePage.planning')
})

function startLoadingSteps() {
  loadingStepIndex.value = 0
  stopLoadingSteps()
  loadingStepTimer = window.setInterval(() => {
    loadingStepIndex.value += 1
  }, 1100)
}

function stopLoadingSteps() {
  if (loadingStepTimer !== null) {
    window.clearInterval(loadingStepTimer)
    loadingStepTimer = null
  }
}
const aiRouteData = ref<RoutePlan | null>(null)
const alternativeRoutes = ref<RoutePlan[]>([])
const showCompareDialog = ref(false)
const lastChatQuery = ref('')
const lastChatReply = ref('')
const routeFilter = ref('全部')
const mapRef = ref<InstanceType<typeof ScenicMap>>()
// 当前要在地图上呈现的路线（含景点名顺序），null 表示清空路线
const activeRoute = ref<ActiveMapRoute | null>(null)
const savedRoutes = ref<SavedRoute[]>([])
const savedRoutesLoading = ref(true)
const savedRoutesError = ref('')
const savingRoute = ref(false)
const deletingRouteId = ref<number | null>(null)
const generatedSavedId = ref<number | null>(null)
const showAddSpotDialog = ref(false)
const spotSearchQuery = ref('')
const allSpots = ref<any[]>([])
const filteredAvailableSpots = ref<any[]>([])

const interestOptions = ref([
  { key: '佛教文化', label: '佛教文化', icon: '🛕' },
  { key: '自然风光', label: '自然风光', icon: '🌿' },
  { key: '历史古迹', label: '历史古迹', icon: '🏛️' },
  { key: '亲子游乐', label: '亲子游乐', icon: '🎠' },
  { key: '建筑艺术', label: '建筑艺术', icon: '⛩️' },
  { key: '美食素斋', label: '美食素斋', icon: '🍜' },
])

const presetRoutes = ref<PresetRoute[]>([])
const interestTranslationKeys: Record<string, string> = {
  佛教文化: 'routePage.buddhism', 自然风光: 'routePage.nature', 历史古迹: 'routePage.history',
  亲子游乐: 'routePage.family', 建筑艺术: 'routePage.architecture', 美食素斋: 'routePage.food',
}
function interestLabel(label: string) {
  return interestTranslationKeys[label] ? t(interestTranslationKeys[label]) : label
}

function isValidRouteSnapshot(snapshot: RoutePlan | undefined): snapshot is RoutePlan {
  if (!snapshot || snapshot.schema_version !== 1 || snapshot.source !== 'chat') return false
  if (!snapshot.title || !snapshot.duration || !Array.isArray(snapshot.spots) || !snapshot.spots.length) return false
  const names = snapshot.spots.map(spot => spot?.name).filter(Boolean)
  return names.length === snapshot.spots.length && new Set(names).size === names.length
}

onMounted(async () => {
  const savedRoutesPromise = loadSavedRoutes()

  // 从景点数据动态汇总兴趣标签，后台新增标签后路线页自动覆盖
  try {
    const spots = await fetchSpots()
    allSpots.value = spots
    const labelsByCanonical = new Map<string, string>()
    spots.forEach(spot => {
      spot.canonicalTags.forEach((canonicalTag, index) => {
        if (!labelsByCanonical.has(canonicalTag)) {
          labelsByCanonical.set(canonicalTag, spot.displayTags[index] || interestLabel(canonicalTag))
        }
      })
    })
    if (labelsByCanonical.size) {
      interestOptions.value = Array.from(labelsByCanonical, ([key, label]) => ({
        key, label, icon: interestIcon(key),
      }))
    }
  } catch {
    // 标签加载失败时保留默认兴趣项
  }

  // 加载预设路线
  try {
    const { data } = await axios.get('/api/routes', { params: { locale: i18n.global.locale.value } })
    presetRoutes.value = data
  } catch {
    presetRoutes.value = []
  }

  // 从对话页跳转而来时直接消费本轮路线快照，避免再次生成导致景点漂移。
  if (route.query.from === 'chat') {
    const snapshot = window.history.state?.route_plan as RoutePlan | undefined
    if (isValidRouteSnapshot(snapshot)) {
      const routeData = { ...snapshot, source: 'chat' as const, interests: snapshot.interests || [] }
      aiRouteData.value = routeData
      aiInterests.value = routeData.interests
        .map(label => interestOptions.value.find(i => i.label === label)?.key || label)
      if (routeData.duration_mode === '半天' || routeData.duration_mode === '全天') {
        aiDuration.value = routeData.duration_mode
      }
      lastChatQuery.value = ''
      lastChatReply.value = ''
      showRouteOnMap(routeData, false)
    } else {
      aiError.value = t('routePage.snapshotExpired')
    }
  }

  await savedRoutesPromise
})

function interestIcon(label: string) {
  if (label.includes('佛')) return '🛕'
  if (label.includes('自然') || label.includes('风光')) return '🌿'
  if (label.includes('历史') || label.includes('古迹')) return '🏛️'
  if (label.includes('亲子') || label.includes('游乐')) return '🎠'
  if (label.includes('建筑') || label.includes('艺术')) return '⛩️'
  if (label.includes('美食') || label.includes('素斋')) return '🍜'
  return '🏷️'
}

const filterTags = computed(() => ['全部', ...interestOptions.value.map(i => i.key)])
function filterLabel(key: string) {
  if (key === '全部') return t('routePage.all')
  return interestOptions.value.find(item => item.key === key)?.label || interestLabel(key)
}

const filteredRoutes = computed(() => {
  if (routeFilter.value === '全部') return presetRoutes.value
  return presetRoutes.value.filter(r => r.tags.includes(routeFilter.value))
})

function toggleKey(key: string, list: string[]) {
  const idx = list.indexOf(key)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(key)
}

async function generateRoute(chatQuery = '', chatReply = '') {
  aiLoading.value = true
  aiError.value = ''
  aiRouteData.value = null
  alternativeRoutes.value = []
  generatedSavedId.value = null
  activeRoute.value = null
  lastChatQuery.value = chatQuery
  lastChatReply.value = chatReply
  startLoadingSteps()
  try {
    const interests = [...aiInterests.value]
    const { data } = await axios.post('/api/chat/route', {
      interests,
      duration: aiDuration.value,
      chat_query: chatQuery,
      chat_reply: chatReply,
      locale: i18n.global.locale.value,
    })
    // 保存完整结构化快照，展示、上图和持久化共用同一份数据。
    aiRouteData.value = {
      source: chatQuery ? 'chat' : 'manual',
      title: data.title || t('routePage.aiRecommended'),
      duration: data.duration || t('routePage.aboutDuration', { duration: aiDuration.value }),
      spots: data.spots?.length ? data.spots : [],
      tips: data.tips || '',
      interests,
      sources: Array.isArray(data.sources) ? data.sources : [],
      citations: Array.isArray(data.citations) ? data.citations : [],
      retrieval: data.retrieval,
      traceId: data.trace_id,
      trace_id: data.trace_id,
      index_version: data.retrieval?.index_version,
    }

    // 处理备选方案
    if (data.alternatives && Array.isArray(data.alternatives)) {
      alternativeRoutes.value = data.alternatives.map((alt: any) => ({
        source: 'manual' as const,
        title: alt.title || t('routePage.alternative'),
        duration: alt.duration || data.duration,
        spots: alt.spots || [],
        tips: alt.tips || '',
        interests,
        sources: [],
        citations: [],
      }))
    }

    showRouteOnMap(aiRouteData.value, false)

    // 如果有备选方案，提示用户
    if (alternativeRoutes.value.length > 0) {
      ElMessage.success(`已生成${alternativeRoutes.value.length + 1}个路线方案，可对比查看`)
    }
  } catch (error: any) {
    aiRouteData.value = null
    alternativeRoutes.value = []
    activeRoute.value = null
    aiError.value = error.response?.data?.detail || t('routePage.planFailed')
  } finally {
    aiLoading.value = false
    stopLoadingSteps()
  }
}

function retryGenerateRoute() {
  generateRoute(lastChatQuery.value, lastChatReply.value)
}

async function loadSavedRoutes() {
  savedRoutesLoading.value = true
  savedRoutesError.value = ''
  try {
    savedRoutes.value = await fetchSavedRoutes()
  } catch (error: any) {
    if (handleUnauthorized(error)) return
    savedRoutesError.value = error.response?.data?.detail || t('routePage.savedLoadFailed')
  } finally {
    savedRoutesLoading.value = false
  }
}

async function saveGeneratedRoute() {
  if (!aiRouteData.value?.spots.length || savingRoute.value || generatedSavedId.value !== null) return

  savingRoute.value = true
  try {
    const savedRoute = await saveRoute(aiRouteData.value)
    savedRoutes.value = [savedRoute, ...savedRoutes.value.filter(item => item.id !== savedRoute.id)]
    generatedSavedId.value = savedRoute.id
    savedRoutesError.value = ''
    ElMessage.success(t('routePage.saved'))
  } catch (error: any) {
    if (!handleUnauthorized(error)) {
      ElMessage.error(error.response?.data?.detail || t('routePage.saveFailed'))
    }
  } finally {
    savingRoute.value = false
  }
}

async function removeSavedRoute(savedRoute: SavedRoute) {
  if (deletingRouteId.value !== null) return

  try {
    await ElMessageBox.confirm(
      t('routePage.deleteConfirm', { title: savedRoute.title }),
      t('routePage.deleteTitle'),
      {
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      },
    )
  } catch {
    return
  }

  deletingRouteId.value = savedRoute.id
  try {
    await deleteSavedRoute(savedRoute.id)
    savedRoutes.value = savedRoutes.value.filter(item => item.id !== savedRoute.id)
    if (generatedSavedId.value === savedRoute.id) generatedSavedId.value = null
    ElMessage.success(t('routePage.deleted'))
  } catch (error: any) {
    if (!handleUnauthorized(error)) {
      ElMessage.error(error.response?.data?.detail || t('routePage.deleteFailed'))
    }
  } finally {
    deletingRouteId.value = null
  }
}

function handleUnauthorized(error: any) {
  if (error.response?.status !== 401) return false
  ElMessage.error(t('common.loginExpired'))
  router.replace({ name: 'auth' })
  return true
}

function showRouteOnMap(routePlan: RoutePlan, shouldScroll = true) {
  const names = routePlan.spots.map(spot => spot.name).filter(Boolean)
  if (!names.length) return
  activeRoute.value = { title: routePlan.title, spots: names }
  if (shouldScroll) scrollToMap()
}

// 点击路线卡片中的景点名：滚动到地图并高亮对应标记
function focusSpotOnMap(name: string) {
  scrollToMap()
  requestAnimationFrame(() => mapRef.value?.focusSpot(name))
}

// 预设路线：点亮到地图
function showPresetOnMap(r: PresetRoute) {
  activeRoute.value = { title: r.title, spots: r.spots }
  scrollToMap()
}

function scrollToMap() {
  // 滚动到顶部地图区域；下一帧确保 ScenicMap 的 watch 已触发
  requestAnimationFrame(() => {
    document.querySelector('.route-page')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function updateRouteSpots(spots: RouteSpot[]) {
  if (!aiRouteData.value) return
  aiRouteData.value = {
    ...aiRouteData.value,
    spots,
  }
  showRouteOnMap(aiRouteData.value, false)
}

async function recalculateRoute() {
  if (!aiRouteData.value) return

  const totalMinutes = aiRouteData.value.spots.reduce((sum, spot) => {
    return sum + (spot.duration_min && spot.duration_min > 0 ? spot.duration_min : 30)
  }, 0)
  const totalHours = totalMinutes / 60
  const rounded = Math.round(totalHours * 10) / 10  // 保留一位小数
  aiRouteData.value.duration = `约${rounded % 1 === 0 ? rounded : rounded.toFixed(1)}小时`

  ElMessage.success('路线已更新')
}

function filterAvailableSpots() {
  const query = spotSearchQuery.value.toLowerCase()
  filteredAvailableSpots.value = allSpots.value.filter(spot =>
    spot.name.toLowerCase().includes(query) ||
    spot.description?.toLowerCase().includes(query)
  )
}

function isSpotInRoute(spotName: string): boolean {
  return aiRouteData.value?.spots.some(s => s.name === spotName) || false
}

function parseDurationMinutes(duration: string): number {
  const text = (duration || '').trim().toLowerCase()
  const hourMatch = text.match(/^(\d+(?:\.\d+)?)\s*h/)
  if (hourMatch) return Math.round(parseFloat(hourMatch[1]) * 60)
  const minMatch = text.match(/^(\d+(?:\.\d+)?)\s*m/)
  if (minMatch) return Math.round(parseFloat(minMatch[1]))
  return 30
}

function addSpotToRoute(spot: any) {
  if (!aiRouteData.value || isSpotInRoute(spot.name)) return

  const newSpot: RouteSpot = {
    name: spot.name,
    display_name: spot.name,
    description: spot.description || '',
    duration_min: parseDurationMinutes(spot.duration || ''),
  }

  aiRouteData.value.spots.push(newSpot)
  showAddSpotDialog.value = false
  spotSearchQuery.value = ''
  recalculateRoute()
  ElMessage.success(`已添加${spot.name}`)
}

function openAddSpotDialog() {
  showAddSpotDialog.value = true
  spotSearchQuery.value = ''
  filterAvailableSpots()
}

function selectAlternativeRoute(alt: RoutePlan) {
  aiRouteData.value = { ...alt }
  generatedSavedId.value = null
  showCompareDialog.value = false
  showRouteOnMap(alt, false)
  ElMessage.success(`已切换至：${alt.title}`)
}

const suggestionDismissed = ref(false)

const routeSuggestion = computed(() => {
  if (!aiRouteData.value || suggestionDismissed.value) return null
  const hour = new Date().getHours()
  if (hour >= 6 && hour < 9) return {
    icon: '🌅', title: '清晨游览建议',
    message: '当前时间可前往九龙灌浴观看晨间表演，人流较少体验更佳。',
  }
  if (hour >= 10 && hour < 12) return {
    icon: '☀️', title: '上午游览提示',
    message: '灵山大佛上午光线充足，建议优先安排开阔景区。',
  }
  if (hour >= 12 && hour < 14) return {
    icon: '🌡️', title: '午间游览建议',
    message: '正午阳光强烈，可先参观梵宫、佛教文化博览馆等室内景点。',
  }
  if (hour >= 14 && hour < 17) return {
    icon: '🌤️', title: '下午游览提示',
    message: '下午是拈花广场和梵天花海拍照的黄金时段，光线柔和。',
  }
  if (hour >= 17 && hour < 19) return {
    icon: '🌇', title: '傍晚特别推荐',
    message: '傍晚夕照灵山大佛，是全天最美的观赏时刻，建议留在大佛广场。',
  }
  return null
})

function dismissSuggestion() {
  suggestionDismissed.value = true
}

onUnmounted(() => {
  stopLoadingSteps()
})
</script>

<style scoped>
.route-page { max-width: 672px; margin: 0 auto; min-height: 100vh; }
.route-header { padding: 12px 16px; background: rgba(255,255,255,0.8); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(0,0,0,0.04); text-align: center; position: sticky; top: 0; z-index: 10; }
.route-header h1 { font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); }
.route-content { padding: 20px 16px; display: flex; flex-direction: column; gap: 20px; }

/* Map */
.map-placeholder { height: 220px; background: linear-gradient(to bottom right, #e8efe6, #f0f4ed, #e4ece2); position: relative; display: flex; align-items: center; justify-content: center; }
.map-texture { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0.07; }
.map-center { position: relative; z-index: 1; text-align: center; }
.map-pin { width: 48px; height: 48px; border-radius: 16px; background: rgba(255,255,255,0.8); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; margin: 0 auto 10px; box-shadow: 0 2px 12px rgba(45,106,79,0.12); color: var(--color-primary); }
.map-center p { font-size: 0.75rem; font-weight: 600; color: rgba(45,106,79,0.7); }
.map-center span { font-size: 10px; color: var(--color-text-muted); }
.map-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; background: #fff; border-top: 1px solid rgba(0,0,0,0.04); }
.map-toolbar button { display: flex; align-items: center; gap: 6px; border: none; background: none; cursor: pointer; font-size: 0.75rem; color: var(--color-text-secondary); }
.map-toolbar button:hover { color: var(--color-primary); }
.expand-btn { margin-left: auto; color: var(--color-primary) !important; font-weight: 500; }

/* AI Card */
.ai-card { padding: 20px; }
.ai-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.ai-icon { width: 36px; height: 36px; border-radius: 12px; background: var(--color-accent-bg); display: flex; align-items: center; justify-content: center; font-size: 1rem; overflow: hidden; }
.ai-icon img { width: 100%; height: 100%; object-fit: cover; }
.ai-header h2 { font-size: 15px; font-weight: 700; color: var(--color-text-primary); }
.ai-header p { font-size: 11px; color: var(--color-text-muted); }
.label-text { font-size: 11px; color: var(--color-text-muted); font-weight: 500; margin-bottom: 10px; }
.tag-group { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.tag-group button { padding: 6px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 500; border: 1px solid rgba(0,0,0,0.04); background: #fff; color: var(--color-text-secondary); cursor: pointer; transition: all 0.3s; }
.tag-group button.active { background: var(--color-primary-bg); color: var(--color-primary); border-color: var(--color-primary-border); }
.duration-group { display: flex; gap: 10px; margin-bottom: 20px; }
.duration-group button { flex: 1; padding: 10px; border-radius: 12px; font-size: 0.875rem; font-weight: 500; border: 1px solid rgba(0,0,0,0.04); background: #fff; color: var(--color-text-secondary); cursor: pointer; transition: all 0.3s; }
.duration-group button.active { background: var(--color-primary-bg); color: var(--color-primary); border-color: var(--color-primary-border); }
.plan-btn { width: 100%; padding: 12px; border-radius: 12px; border: none; background: var(--color-accent); color: #fff; font-size: 0.875rem; font-weight: 600; cursor: pointer; box-shadow: 0 4px 16px rgba(176,125,79,0.25); transition: all 0.2s; }
.plan-btn:active { transform: scale(0.98); }
.plan-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.loading-text { display: flex; align-items: center; justify-content: center; gap: 8px; }
.ai-result { margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(0,0,0,0.04); }
.ai-rc-icon { background: linear-gradient(135deg, #f0e6d3, #e8d5b0) !important; }
.rc-spots span em { font-style: normal; color: var(--color-text-muted); font-weight: 400; }
.show-on-map-btn {
  width: 100%; margin-top: 12px; padding: 9px;
  border: 1px solid var(--color-primary-border); background: var(--color-primary-bg);
  color: var(--color-primary); font-size: 0.75rem; font-weight: 600;
  border-radius: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;
  transition: all 0.2s;
}
.show-on-map-btn:hover { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }

@media (max-width: 420px) {
  .route-content { padding: 16px 12px; gap: 16px; }
  .ai-card { padding: 16px; }
  .planning-error { align-items: flex-start; flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  .preset-section, .route-card { animation: none; opacity: 1; }
  .show-on-map-btn, .plan-btn { transition: none; }
  .plan-btn:active { transform: none; }
}

/* Generated route and saved routes */
.planning-error {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  margin-top: 14px; padding: 10px 12px; border-radius: 10px;
  background: rgba(196,84,74,0.06); color: var(--color-error); font-size: 11px;
}
.planning-error button, .error-state button {
  flex-shrink: 0; border: none; background: none; color: inherit;
  font-size: 11px; font-weight: 700; cursor: pointer;
}
.planning-error button:focus-visible, .error-state button:focus-visible {
  outline: 3px solid rgba(64,145,108,0.28); outline-offset: 2px;
}
.saved-section { min-width: 0; }
.saved-title { justify-content: space-between; }
.section-heading { display: flex; align-items: center; gap: 8px; }
.saved-count {
  color: var(--color-accent); background: var(--color-accent-bg);
  border: 1px solid var(--color-accent-border); border-radius: 999px;
  padding: 2px 8px; font-size: 10px; font-weight: 700;
}
.saved-route-list { display: flex; flex-direction: column; gap: 12px; }
.saved-state {
  display: flex; min-height: 72px; align-items: center; justify-content: center; gap: 8px;
  padding: 18px; border: 1px dashed var(--color-primary-border); border-radius: 12px;
  background: rgba(255,255,255,0.45); color: var(--color-text-muted);
  text-align: center; font-size: 11px;
}
.error-state { color: var(--color-error); border-color: rgba(196,84,74,0.18); }

/* Presets */
.preset-section { animation: fadeUp 0.6s ease-out 0.15s forwards; opacity: 0; }
.section-title { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.section-title h2 { font-size: 15px; font-weight: 700; color: var(--color-text-primary); }
.filter-scroll { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 12px; }
.filter-scroll button { padding: 6px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 500; white-space: nowrap; border: 1px solid rgba(0,0,0,0.04); background: #fff; color: var(--color-text-secondary); cursor: pointer; transition: all 0.3s; flex-shrink: 0; }
.filter-scroll button.active { background: var(--color-primary-bg); color: var(--color-primary); border-color: var(--color-primary-border); }
.route-list { display: flex; flex-direction: column; gap: 12px; }
.route-card { padding: 16px; opacity: 0; animation: fadeUp 0.6s ease-out forwards; }
.rc-top { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 8px; }
.rc-icon { width: 40px; height: 40px; border-radius: 12px; background: var(--color-primary-bg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.25rem; }
.rc-info { flex: 1; }
.rc-info h3 { font-size: 0.875rem; font-weight: 700; color: var(--color-text-primary); }
.rc-meta { display: flex; gap: 12px; margin-top: 2px; }
.rc-meta span { display: flex; align-items: center; gap: 2px; font-size: 11px; color: var(--color-text-muted); }
.rc-difficulty { font-size: 11px; font-weight: 600; color: var(--color-accent); background: var(--color-accent-bg); padding: 2px 8px; border-radius: 6px; }
.rc-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.6; margin-bottom: 12px; }
.rc-spots { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.rc-spots span { font-size: 11px; color: var(--color-primary); background: var(--color-primary-bg); padding: 2px 8px; border-radius: 6px; font-weight: 500; }
.rc-tip { display: flex; align-items: center; gap: 4px; font-size: 11px; color: var(--color-text-muted); background: var(--color-bg-elevated); border-radius: 8px; padding: 6px 10px; }

.add-spot-search { margin-bottom: 16px; }
.spot-list { max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.spot-item {
  width: 100%; padding: 12px; border: 1px solid rgba(0,0,0,0.08);
  background: #fff; border-radius: 8px; cursor: pointer;
  display: flex; align-items: center; justify-content: space-between;
  transition: all 0.2s; text-align: left;
}
.spot-item:hover:not(:disabled) {
  background: var(--color-primary-bg);
  border-color: var(--color-primary-border);
}
.spot-item:disabled { opacity: 0.5; cursor: not-allowed; }
.spot-name { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }
.spot-added { font-size: 11px; color: var(--color-text-muted); }
.no-spots {
  text-align: center; padding: 40px 20px;
  color: var(--color-text-muted); font-size: 13px;
}

/* 备选方案入口 */
.compare-trigger {
  width: 100%; padding: 12px 16px;
  border: 1px solid var(--color-primary-border);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: 13px; font-weight: 600;
  border-radius: 12px; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  transition: all 0.2s;
}
.compare-trigger span:first-child { font-size: 16px; }
.compare-trigger span:nth-child(2) { flex: 1; text-align: left; }
.compare-trigger:hover { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }

/* 实时建议卡片 */
.suggestion-card {
  display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px;
  background: linear-gradient(135deg, rgba(255,200,100,0.12), rgba(255,170,50,0.08));
  border: 1px solid rgba(200,150,50,0.2); border-radius: 12px;
}
.suggestion-icon { font-size: 22px; flex-shrink: 0; padding-top: 2px; }
.suggestion-text { flex: 1; min-width: 0; }
.suggestion-text strong { font-size: 13px; color: var(--color-text-primary); display: block; margin-bottom: 3px; }
.suggestion-text p { font-size: 12px; color: var(--color-text-secondary); line-height: 1.6; margin: 0; }
.suggestion-dismiss {
  flex-shrink: 0; width: 24px; height: 24px;
  border: none; background: none; cursor: pointer;
  color: var(--color-text-muted); font-size: 18px; line-height: 1;
  border-radius: 4px; padding: 0;
  display: flex; align-items: center; justify-content: center;
}
.suggestion-dismiss:hover { background: rgba(0,0,0,0.06); color: var(--color-text-primary); }

/* 路线对比对话框 */
.compare-list { display: flex; flex-direction: column; gap: 14px; }
.compare-item {
  position: relative; padding: 16px;
  border: 1.5px solid rgba(0,0,0,0.08); border-radius: 12px;
  background: #fff;
}
.compare-item.current { border-color: var(--color-primary-border); background: var(--color-primary-bg); }
.compare-badge {
  display: inline-block; margin-bottom: 8px; padding: 2px 8px;
  background: var(--color-primary); color: #fff;
  font-size: 10px; font-weight: 700; border-radius: 999px;
}
.compare-badge.alt { background: var(--color-accent); }
.compare-item h4 { font-size: 14px; font-weight: 700; color: var(--color-text-primary); margin: 0 0 8px; }
.compare-meta { display: flex; gap: 14px; margin-bottom: 10px; }
.compare-meta span { font-size: 11px; color: var(--color-text-muted); }
.compare-spots { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.compare-spots span { font-size: 12px; color: var(--color-text-secondary); }
.compare-tips {
  font-size: 11px; color: var(--color-text-muted); line-height: 1.5;
  margin: 8px 0 12px; padding: 8px 10px;
  background: rgba(176,125,79,0.06); border-radius: 8px;
}
.select-alt-btn {
  width: 100%; padding: 9px; border: none;
  background: var(--color-accent); color: #fff;
  font-size: 13px; font-weight: 600; border-radius: 8px;
  cursor: pointer; transition: all 0.2s;
}
.select-alt-btn:hover { background: var(--color-accent-light); }
</style>
