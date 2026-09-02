<template>
  <div class="scenic-map-wrap">
    <!-- 天气卡片：地图上方，展示景区今日实况 + 未来几日预报 -->
    <div class="weather-card" :class="{ loading: weatherLoading }">
      <template v-if="weatherLoading">
        <div class="wc-loading">{{ t('map.weatherLoading') }}</div>
      </template>
      <template v-else-if="weatherError">
        <div class="wc-error">{{ weatherError }}</div>
      </template>
      <template v-else-if="weather">
        <div class="wc-main">
          <span class="wc-emoji">{{ weatherEmoji(weather.live?.weather, weather.live?.weather_code) }}</span>
          <div class="wc-center">
            <div class="wc-temp">{{ weather.live?.temperature ?? '—' }}°</div>
            <div class="wc-desc">{{ weatherText(weather.live?.weather, weather.live?.weather_code) }}</div>
          </div>
          <div class="wc-meta">
            <div class="wc-place">{{ shortPlace(weather.place) }}</div>
            <div class="wc-detail">
              {{ t('map.humidity', { value: weather.live?.humidity ?? '—' }) }}
              · {{ t('map.wind', { direction: windDirectionText(weather.live), power: weather.live?.windpower ?? '' }) }}
            </div>
            <button class="wc-refresh" :disabled="weatherLoading" @click="loadWeather">{{ t('map.refresh') }}</button>
          </div>
        </div>
        <div class="wc-forecast" v-if="weather.casts?.length">
          <div v-for="c in weather.casts.slice(0, 4)" :key="c.date" class="fc-day">
            <span class="fc-date">{{ fcLabel(c) }}</span>
            <span class="fc-emoji">{{ weatherEmoji(c.dayweather, c.dayweather_code || c.weather_code) }}</span>
            <span class="fc-weather">{{ weatherText(c.dayweather, c.dayweather_code || c.weather_code) }}</span>
            <span class="fc-temp">{{ c.nighttemp }}° / {{ c.daytemp }}°</span>
          </div>
        </div>
      </template>
    </div>

    <div class="scenic-map card" style="padding:0;overflow:hidden">
      <div ref="mapEl" class="map-container" />
      <div v-if="!ready" class="map-placeholder">
        <div class="ph-pin"><el-icon size="24"><LocationFilled /></el-icon></div>
        <p>{{ t('map.scenicMap') }}</p>
        <span>{{ loading ? t('map.mapLoading') : mapError || t('map.clickLoad') }}</span>
      </div>
      <transition name="gf-slide">
        <div v-if="geofenceNotif" class="geofence-notif">
          <span class="gf-icon">📍</span>
          <div class="gf-text">
            <div class="gf-title">{{ t('map.nearbySpot', { name: geofenceNotif.displayName }) }}</div>
            <div class="gf-sub">{{ t('map.nearbySpotDesc') }}</div>
          </div>
          <button class="gf-guide" @click="onGeofenceGuide">{{ t('map.guide') }}</button>
          <button class="gf-dismiss" @click="geofenceNotif = null">{{ t('map.dismiss') }}</button>
        </div>
      </transition>
      <div class="map-toolbar">
        <button @click="locateMe" :class="{ 'toolbar-active': gpsStatus === 'tracking' }"><el-icon><Aim /></el-icon>{{ t('map.locate') }}</button>
        <button @click="drawActiveRoute"><el-icon><Guide /></el-icon>{{ t('map.route') }}</button>
        <button @click="fitAll"><el-icon><FullScreen /></el-icon>{{ t('map.panorama') }}</button>
        <button @click="openFilter">
          <el-icon><Filter /></el-icon>{{ t('map.filter') }}
          <span v-if="hiddenCount > 0" class="filter-badge">{{ hiddenCount }}</span>
        </button>
        <button @click="togglePinMode" :class="{ 'toolbar-active': pinMode }">
          <el-icon><EditPen /></el-icon>{{ t('map.customPin') }}
        </button>
        <span v-if="routeStatus" class="route-status">{{ routeStatus }}</span>
        <template v-if="isAnimating">
          <button @click="isPaused ? resumeAnimation() : pauseAnimation()">
            <el-icon><component :is="isPaused ? 'VideoPlay' : 'VideoPause'" /></el-icon>
            {{ isPaused ? t('map.resumeRoute') : t('map.pauseRoute') }}
          </button>
          <button @click="clearRoute"><el-icon><CircleClose /></el-icon>{{ t('map.stopRoute') }}</button>
        </template>
        <span v-if="pinMode" class="pin-mode-hint">{{ t('map.pinModeHint') }}</span>
      </div>
    </div>

    <el-dialog v-model="showFilter" :title="t('map.filterTitle')" width="min(360px, 92vw)" append-to-body>
      <div class="filter-quick-actions">
        <button class="filter-link" @click="selectAllSpots">{{ t('map.selectAll') }}</button>
        <button class="filter-link" @click="selectNoSpots">{{ t('map.selectNone') }}</button>
        <button class="filter-link" @click="selectPopularSpots">{{ t('map.popularOnly') }}</button>
      </div>
      <div v-for="group in SPOT_GROUPS" :key="group.category" class="filter-group">
        <div class="filter-group-label">{{ group.category }}</div>
        <el-checkbox-group v-model="pendingVisibleNames" class="filter-checkboxes">
          <el-checkbox v-for="name in group.names" :key="name" :value="name" :label="name" class="filter-checkbox-item">
            {{ name }}
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <template #footer>
        <button class="filter-btn filter-btn--cancel" @click="showFilter = false">{{ t('map.cancelFilter') }}</button>
        <button class="filter-btn filter-btn--apply" @click="applyFilter">{{ t('map.applyFilter') }}</button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPinDialog" :title="t('map.pinName')" width="min(320px, 92vw)" append-to-body>
      <el-input v-model="newPinName" :placeholder="t('map.pinNamePlaceholder')" maxlength="20" clearable @keyup.enter="confirmPin" />
      <div class="pin-delete-tip">{{ t('map.pinDeleteTip') }}</div>
      <template #footer>
        <button class="filter-btn filter-btn--cancel" @click="showPinDialog = false">{{ t('map.pinCancel') }}</button>
        <button class="filter-btn filter-btn--apply" @click="confirmPin">{{ t('map.pinSave') }}</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import { useAmap } from '../composables/useAmap'
import { fetchSpots, type ScenicSpot } from '../data/spots'

// 父组件传入的推荐路线：景点名按游览顺序排列
const props = defineProps<{ activeRoute: { title: string; spots: string[] } | null }>()

const { load } = useAmap()
const router = useRouter()
const { t, locale } = useI18n()
const mapEl = ref<HTMLElement>()
const ready = ref(false)
const loading = ref(false)
const mapError = ref('')
const routeStatus = ref('')
const isAnimating = ref(false)
const isPaused = ref(false)
let map: any = null
let markers: any[] = []
let infoWindow: any = null
let routePolylines: any[] = []
let movingArrow: any = null
let routeRequestVersion = 0
let spots: ScenicSpot[] = []
const markerMap = new Map<string, any>()

// ===== GPS / 地理围栏 =====
let watchId: number | null = null
let userMarker: any = null
let userAccCircle: any = null
const gpsStatus = ref<'idle' | 'tracking' | 'denied' | 'error'>('idle')
const isFirstLocation = ref(true)
const triggeredSpots = new Set<string>()
interface GeofenceNotif { canonicalName: string; displayName: string }
const geofenceNotif = ref<GeofenceNotif | null>(null)
let geofenceTimer: ReturnType<typeof setTimeout> | null = null
// ===== 自定义标记 =====
interface CustomPin { id: string; name: string; lnglat: [number, number] }
const LS_PIN_KEY = 'lingguide_custom_pins'
const customPins = ref<CustomPin[]>([])
const pinMarkers = new Map<string, any>()
const pinMode = ref(false)
const showPinDialog = ref(false)
const pendingPinPos = ref<[number, number] | null>(null)
const newPinName = ref('')

// ===== 景点分组与筛选 =====
const SPOT_GROUPS = [
  { category: '核心景区', names: ['灵山大佛', '梵宫', '九龙灌浴', '五印坛城', '拈花广场', '梵天花海'] },
  { category: '文化建筑', names: ['降魔浮雕', '菩提大道', '阿育王柱', '五智门', '佛足坛', '祥符禅寺', '佛教文化博览馆', '曼飞龙塔'] },
  { category: '景观设施', names: ['灵山大照壁', '五明桥', '无尽意斋', '百子戏弥勒'] },
  { category: '休闲体验', names: ['香月花街', '拈花堂', '五灯湖', '鹿鸣谷'] },
]
const POPULAR_SPOTS = ['灵山大佛', '梵宫', '九龙灌浴', '五印坛城', '拈花广场', '梵天花海', '百子戏弥勒', '阿育王柱', '祥符禅寺', '鹿鸣谷']
const LS_KEY = 'lingguide_map_visible_spots'

const visibleSpotNames = ref<string[]>([...POPULAR_SPOTS])
const pendingVisibleNames = ref<string[]>([...POPULAR_SPOTS])
const showFilter = ref(false)
const hiddenCount = computed(() => spots.filter(s => !visibleSpotNames.value.includes(s.canonicalName)).length)

type RoutePoint = [number, number]

interface PlannedSegment {
  path: RoutePoint[]
  fallback: boolean
}

// ===== 天气卡片状态 =====
interface WeatherLive {
  weather: string; weather_code?: string; temperature: string; humidity: string
  winddirection: string; wind_direction_code?: string; windpower: string; reporttime: string
}

interface WeatherCast {
  date: string; week: string; dayweather: string; nightweather: string;
  daytemp: string; nighttemp: string; daywind: string; nightwind: string;
  weather_code?: string; dayweather_code?: string; nightweather_code?: string; daypower: string; nightpower: string;
}
interface WeatherResp { place: string; ok: boolean; live: WeatherLive | null; casts: WeatherCast[]; message: string; reason?: string }

function windDirectionText(live: WeatherLive | null): string {
  if (!live?.wind_direction_code) return live?.winddirection || ''
  const key = `map.windDirections.${live.wind_direction_code}`
  const translated = t(key)
  return translated === key ? (live.winddirection || '') : translated
}

function weatherText(value?: string, code?: string): string {
  if (!code) return value || '—'
  const key = `map.weatherConditions.${code}`
  const translated = t(key)
  return translated === key ? (value || '—') : translated
}

const weather = ref<WeatherResp | null>(null)
const weatherLoading = ref(false)
const weatherError = ref('')

async function loadWeather() {
  weatherLoading.value = true
  weatherError.value = ''
  try {
    const { data } = await axios.get<WeatherResp>('/api/weather', { params: { locale: locale.value } })
    if (data.ok) {
      weather.value = data
    } else {
      weatherError.value = data.message || data.reason || t('map.weatherFailed')
    }
  } catch (e: any) {
    weatherError.value = t('map.weatherUnavailable')
  } finally {
    weatherLoading.value = false
  }
}

// 天气现象 → emoji，覆盖高德常见描述
function weatherEmoji(w?: string, code?: string): string {
  if (code && /^(00|01)$/.test(code)) return '☀️'
  if (!w) return '🌤️'
  const map: Record<string, string> = {
    '晴': '☀️', '多云': '⛅', '阴': '☁️',
    '阵雨': '🌦️', '雷阵雨': '⛈️', '雷阵雨伴有冰雹': '⛈️',
    '雨夹雪': '🌨️', '小雨': '🌧️', '中雨': '🌧️', '大雨': '🌧️', '暴雨': '🌧️', '大暴雨': '🌧️', '特大暴雨': '🌧️',
    '冻雨': '🌧️', '小雪': '🌨️', '中雪': '🌨️', '大雪': '❄️', '暴雪': '❄️',
    '雾': '🌫️', '浓雾': '🌫️', '霾': '🌫️', '浮尘': '🌫️', '扬沙': '🌬️', '沙尘暴': '🌪️', '强沙尘暴': '🌪️',
  }
  return map[w] ?? '🌤️'
}

// 闽侯县类长地名简化为区/县
function shortPlace(p?: string): string {
  if (!p) return ''
  return p.replace(/^[^省]+省/, '').replace(/^[^市]+市/, '') || p
}

// 预报日标签：今天/明天/后天/日期。用日期字符串比对避免时区偏差
function fcLabel(c: WeatherCast): string {
  // 截取本地日期 YYYY-MM-DD（toDateString 取当前时区）
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const baseDate = new Date(todayStr + 'T00:00:00')
  const d = new Date(c.date + 'T00:00:00')  // 强制按本地时区解析，避免 UTC 偏移
  const diff = Math.round((d.getTime() - baseDate.getTime()) / 86400000)
  if (diff === 0) return t('map.today')
  if (diff === 1) return t('map.tomorrow')
  if (diff === 2) return t('map.afterTomorrow')
  return c.date.slice(5)  // MM-DD
}

function loadFilter() {
  try {
    const stored = localStorage.getItem(LS_KEY)
    visibleSpotNames.value = stored ? JSON.parse(stored) : [...POPULAR_SPOTS]
  } catch {
    visibleSpotNames.value = [...POPULAR_SPOTS]
  }
  pendingVisibleNames.value = [...visibleSpotNames.value]
}

function saveFilter() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(visibleSpotNames.value)) } catch {}
}

function updateMarkerVisibility() {
  const visible = new Set(visibleSpotNames.value)
  markerMap.forEach((marker, name) => {
    marker.setMap(visible.has(name) ? map : null)
  })
}

function getVisibleMarkers(): any[] {
  const visible = new Set(visibleSpotNames.value)
  return [...markerMap.entries()].filter(([n]) => visible.has(n)).map(([, m]) => m)
}

function openFilter() {
  pendingVisibleNames.value = [...visibleSpotNames.value]
  showFilter.value = true
}

function applyFilter() {
  visibleSpotNames.value = [...pendingVisibleNames.value]
  saveFilter()
  updateMarkerVisibility()
  showFilter.value = false
}

function selectAllSpots() { pendingVisibleNames.value = spots.map(s => s.canonicalName) }
function selectNoSpots() { pendingVisibleNames.value = [] }
function selectPopularSpots() { pendingVisibleNames.value = [...POPULAR_SPOTS] }

// 灵山胜境景区中心
const CENTER: [number, number] = [120.100, 31.423]

// 跳转景点详情页
function goDetail(name: string) {
  infoWindow?.close()
  router.push(`/spot/${encodeURIComponent(name)}`)
}

async function initMap() {
  if (ready.value) return
  loading.value = true
  mapError.value = ''
  try {
    // 并行加载地图 SDK 和景点数据
    const [_, spotList] = await Promise.all([load(), fetchSpots()])
    spots = spotList.filter(s => s.lng != null && s.lat != null)
    if (!mapEl.value) return
    const AMap = window.AMap

    map = new AMap.Map(mapEl.value, {
      zoom: 16,
      center: CENTER,
      mapStyle: 'amap://styles/light',
      resizeEnable: true,
    })

    // 预创建共享 InfoWindow
    infoWindow = new AMap.InfoWindow({
      offset: { x: 0, y: -36 },
      closeWhenClickMap: true,
    })

    await new Promise<void>((resolve) => {
      AMap.plugin(['AMap.Marker', 'AMap.Walking', 'AMap.MoveAnimation'], () => {
        spots.forEach((spot, idx) => {
          const pos: [number, number] = [spot.lng!, spot.lat!]
          const marker = new AMap.Marker({
            position: pos,
            content: markerHtml(spot, idx),
            offset: { x: -18, y: -44 },
          })
          marker.on('click', () => openInfo(spot))
          markerMap.set(spot.canonicalName, marker)
          markers.push(marker)
        })

        updateMarkerVisibility()

        const visibleMarkers = getVisibleMarkers()
        if (visibleMarkers.length) {
          map.setFitView(visibleMarkers, false, [60, 60, 60, 60])
        }
        resolve()
      })
    })

    ready.value = true
    map.on('click', onMapClick)
    loadCustomPins()
    // 首次从对话页跳转时，activeRoute 可能早于地图 ready 写入；这里补画一次。
    if (props.activeRoute?.spots?.length) {
      drawRouteByNames(props.activeRoute.spots)
    }
  } catch (error) {
    mapError.value = error instanceof Error ? error.message : t('map.weatherUnavailable')
  } finally {
    loading.value = false
  }
}

// 标记 HTML：圆形缩略图 pin；有图显示图片，无图降级为 emoji。
function markerHtml(spot: ScenicSpot, idx: number): string {
  const inner = spot.image
    ? `<img class="map-pin-thumb-img" src="${spot.image}" alt="" loading="lazy">`
    : `<span class="map-pin-thumb-fallback">${spot.icon || '📍'}</span>`
  return `<div class="map-pin-wrap" data-spot="${spot.canonicalName}">
    <div class="map-pin-badge map-pin-badge--thumb">${inner}</div>
    <div class="map-pin-num">${idx + 1}</div>
  </div>`
}

// 点击标记弹缩略介绍
function openInfo(spot: ScenicSpot) {
  if (!map || !infoWindow) return
  const pos: [number, number] = [spot.lng!, spot.lat!]
  const img = spot.image
    ? `<img class="iw-thumb" src="${spot.image}" alt="${spot.displayName}"/>`
    : ''
  const desc = spot.desc || t('map.noIntro')
  const tags = spot.displayTags?.length
    ? `<div class="iw-tags">${spot.displayTags.map(tag => `<span>${tag}</span>`).join('')}</div>`
    : ''
  infoWindow.setContent(`
    <div class="iw-card">
      ${img}
      <div class="iw-body">
        <h3>${spot.displayName}</h3>
        ${tags}
        <p class="iw-desc">${desc}</p>
        <button class="iw-btn" data-name="${spot.canonicalName}">${t('map.details')}</button>
      </div>
    </div>`)
  infoWindow.open(map, pos)
  fetch('/api/visits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ spot_id: spot.id ?? spot.canonicalName, lng: pos[0], lat: pos[1] }),
  }).catch(() => {})
}

// 事件委托：InfoWindow 内按钮点击
function onInfoClick(e: MouseEvent) {
  const target = (e.target as HTMLElement).closest('[data-name]') as HTMLElement | null
  if (target?.dataset.name) {
    goDetail(target.dataset.name)
  }
}

function locateMe() {
  if (!map) { initMap(); return }
  if (!navigator.geolocation) { map.setZoomAndCenter(17, CENTER); return }
  if (gpsStatus.value === 'tracking') {
    if (userMarker) {
      const p = userMarker.getPosition()
      map.setZoomAndCenter(17, [p.getLng(), p.getLat()])
    }
    return
  }
  startGPS()
}

function startGPS() {
  gpsStatus.value = 'tracking'
  isFirstLocation.value = true
  watchId = navigator.geolocation.watchPosition(
    ({ coords }) => {
      const pos: [number, number] = [coords.longitude, coords.latitude]
      updateUserMarker(pos, coords.accuracy)
      checkGeofencing(pos)
    },
    () => {
      gpsStatus.value = 'error'
      map?.setZoomAndCenter(17, CENTER)
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
  )
}

function stopGPS() {
  if (watchId !== null) {
    navigator.geolocation.clearWatch(watchId)
    watchId = null
  }
  gpsStatus.value = 'idle'
  userMarker?.setMap(null); userMarker = null
  userAccCircle?.setMap(null); userAccCircle = null
}

function updateUserMarker(pos: [number, number], accuracy = 0) {
  if (!map) return
  const AMap = window.AMap
  if (!userMarker) {
    userMarker = new AMap.Marker({
      position: pos,
      content: '<div class="user-location-dot"></div>',
      offset: { x: -12, y: -12 },
      zIndex: 300,
    })
    userMarker.setMap(map)
  } else {
    userMarker.setPosition(pos)
  }
  if (accuracy > 0) {
    if (!userAccCircle) {
      userAccCircle = new AMap.Circle({
        center: pos, radius: accuracy,
        strokeColor: '#4A90E2', strokeWeight: 1, strokeOpacity: 0.5,
        fillColor: '#4A90E2', fillOpacity: 0.08, zIndex: 50,
      })
      userAccCircle.setMap(map)
    } else {
      userAccCircle.setCenter(pos)
      userAccCircle.setRadius(accuracy)
    }
  }
  if (isFirstLocation.value) {
    isFirstLocation.value = false
    map.setZoomAndCenter(17, pos)
  }
}

function checkGeofencing(pos: [number, number]) {
  for (const spot of spots) {
    if (!spot.lng || !spot.lat) continue
    if (triggeredSpots.has(spot.canonicalName)) continue
    const dist = pointDistance(pos, [spot.lng, spot.lat])
    if (dist <= 50) {
      triggeredSpots.add(spot.canonicalName)
      geofenceNotif.value = { canonicalName: spot.canonicalName, displayName: spot.displayName }
      if (geofenceTimer) clearTimeout(geofenceTimer)
      geofenceTimer = window.setTimeout(() => { geofenceNotif.value = null }, 8000)
    }
  }
}

function onGeofenceGuide() {
  if (!geofenceNotif.value) return
  const name = geofenceNotif.value.canonicalName
  geofenceNotif.value = null
  router.push(`/spot/${encodeURIComponent(name)}`)
}

function loadCustomPins() {
  try {
    const stored = localStorage.getItem(LS_PIN_KEY)
    customPins.value = stored ? JSON.parse(stored) : []
  } catch { customPins.value = [] }
  customPins.value.forEach(pin => renderCustomPin(pin))
}

function saveCustomPins() {
  try { localStorage.setItem(LS_PIN_KEY, JSON.stringify(customPins.value)) } catch {}
}

function renderCustomPin(pin: CustomPin) {
  if (!map) return
  const AMap = window.AMap
  const marker = new AMap.Marker({
    position: pin.lnglat,
    content: `<div class="custom-pin-wrap" title="${pin.name}">${pin.name}</div>`,
    offset: { x: -20, y: -36 },
    draggable: true,
    zIndex: 150,
  })
  marker.on('rightclick', () => deleteCustomPin(pin.id))
  marker.on('dragend', () => {
    const p = marker.getPosition()
    const idx = customPins.value.findIndex(c => c.id === pin.id)
    if (idx !== -1) {
      customPins.value[idx].lnglat = [p.getLng(), p.getLat()]
      saveCustomPins()
    }
  })
  marker.setMap(map)
  pinMarkers.set(pin.id, marker)
}

function togglePinMode() { pinMode.value = !pinMode.value }

function onMapClick(e: any) {
  if (!pinMode.value) return
  pendingPinPos.value = [e.lnglat.getLng(), e.lnglat.getLat()]
  newPinName.value = ''
  showPinDialog.value = true
}

function confirmPin() {
  if (!pendingPinPos.value) return
  const pin: CustomPin = {
    id: Date.now().toString(),
    name: newPinName.value.trim() || t('map.customPin'),
    lnglat: pendingPinPos.value,
  }
  customPins.value.push(pin)
  saveCustomPins()
  renderCustomPin(pin)
  fetch('/api/pins', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: pin.name, lng: pin.lnglat[0], lat: pin.lnglat[1] }),
  }).catch(() => {})
  showPinDialog.value = false
  pendingPinPos.value = null
  pinMode.value = false
}

function deleteCustomPin(id: string) {
  const marker = pinMarkers.get(id)
  if (marker) { marker.setMap(null); pinMarkers.delete(id) }
  customPins.value = customPins.value.filter(p => p.id !== id)
  saveCustomPins()
}

/** 按名称定位并高亮景点标记；若该景点被筛选隐藏则临时显示3秒。 */
function focusSpot(name: string) {
  if (!map || !ready.value) return
  const spot = matchSpot(name)
  if (!spot) return
  const marker = markerMap.get(spot.canonicalName)
  const isHidden = marker && !visibleSpotNames.value.includes(spot.canonicalName)
  if (isHidden) {
    marker.setMap(map)
    window.setTimeout(() => {
      if (!visibleSpotNames.value.includes(spot.canonicalName)) marker.setMap(null)
    }, 3000)
  }
  map.setZoomAndCenter(18, [spot.lng!, spot.lat!])
  openInfo(spot)
  bounceMarker(spot.canonicalName)
}

/** 短暂放大标记形成「跳一下」的高亮反馈；标记 DOM 通过 data-spot 定位，不依赖高德内部私有字段。 */
function bounceMarker(canonicalName: string) {
  const target = mapEl.value?.querySelector<HTMLElement>(`[data-spot="${cssEscape(canonicalName)}"]`)
  if (!target) return
  target.classList.remove('map-pin-bounce')
  void target.offsetWidth // 强制重排以重启动画
  target.classList.add('map-pin-bounce')
  window.setTimeout(() => target.classList.remove('map-pin-bounce'), 900)
}

function cssEscape(value: string): string {
  return window.CSS?.escape ? window.CSS.escape(value) : value.replace(/["\\]/g, '\\$&')
}

/** 仅移除当前路线覆盖物，不改变正在执行的请求版本。 */
function clearRouteOverlays() {
  try { movingArrow?.stopMove?.() } catch {}
  movingArrow?.setMap?.(null)
  movingArrow = null
  isAnimating.value = false
  isPaused.value = false
  routePolylines.forEach(line => line.setMap?.(null))
  routePolylines = []
}

/** 清除已画路线，并使尚未结束的步行规划失效。 */
function clearRoute() {
  routeRequestVersion++
  clearRouteOverlays()
  routeStatus.value = ''
}

function pauseAnimation() {
  try { movingArrow?.pauseMove?.() } catch {}
  isPaused.value = true
}

function resumeAnimation() {
  try { movingArrow?.resumeMove?.() } catch {}
  isPaused.value = false
}

/** 名字匹配景点坐标：先精确，再包含，命中即返回，匹配不到返回 null。 */
function matchSpot(name: string): ScenicSpot | null {
  const target = name.trim()
  if (!target) return null
  let hit = spots.find(s => s.canonicalName === target)
  if (hit && hit.lng != null && hit.lat != null) return hit
  hit = spots.find(s => (s.canonicalName.includes(target) || target.includes(s.canonicalName)) && s.lng != null && s.lat != null)
  return (hit && hit.lng != null && hit.lat != null) ? hit : null
}

function toRoutePoint(point: any): RoutePoint | null {
  const lng = Array.isArray(point) ? Number(point[0]) : Number(point?.getLng?.() ?? point?.lng)
  const lat = Array.isArray(point) ? Number(point[1]) : Number(point?.getLat?.() ?? point?.lat)
  return Number.isFinite(lng) && Number.isFinite(lat) ? [lng, lat] : null
}

/** 计算两点间近似距离（米），用于去重和匀速分配动画时长。 */
function pointDistance(a: RoutePoint, b: RoutePoint): number {
  const rad = Math.PI / 180
  const lat1 = a[1] * rad
  const lat2 = b[1] * rad
  const dLat = (b[1] - a[1]) * rad
  const dLng = (b[0] - a[0]) * rad
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  return 6371000 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h))
}

/** 将高德 LngLat/坐标数组归一化为一维路线，并补齐景点端点。 */
function normalizeWalkingPath(rawPath: any[], origin: RoutePoint, dest: RoutePoint): RoutePoint[] | null {
  const points: RoutePoint[] = []
  rawPath.forEach((raw) => {
    const point = toRoutePoint(raw)
    if (!point || (points.length && pointDistance(points[points.length - 1], point) < 0.5)) return
    points.push(point)
  })
  if (points.length < 2) return null
  if (pointDistance(origin, points[0]) >= 0.5) points.unshift(origin)
  if (pointDistance(points[points.length - 1], dest) >= 0.5) points.push(dest)
  return points
}

function planWalkingSegment(planner: any, origin: RoutePoint, dest: RoutePoint) {
  return new Promise<RoutePoint[] | null>((resolve) => {
    let done = false
    const finish = (path: RoutePoint[] | null) => {
      if (done) return
      done = true
      clearTimeout(timer)
      resolve(path)
    }
    const timer = window.setTimeout(() => finish(null), 8000)
    try {
      planner.search(origin, dest, (status: string, result: any) => {
        if (status !== 'complete' || !result?.routes?.length) return finish(null)
        const rawPath = result.routes[0].steps?.flatMap((step: any) => step.path || []) || []
        finish(normalizeWalkingPath(rawPath, origin, dest))
      })
    } catch {
      finish(null)
    }
  })
}

/** 将连续路线段拼成动画路径；若中间存在不可见断口则不生成动画。 */
function mergeSegmentPaths(segments: PlannedSegment[]): RoutePoint[] | null {
  const path: RoutePoint[] = []
  for (const segment of segments) {
    if (!path.length) {
      path.push(...segment.path)
      continue
    }
    if (pointDistance(path[path.length - 1], segment.path[0]) >= 0.5) return null
    path.push(...segment.path.slice(1))
  }
  return path.length >= 2 ? path : null
}

/** 将路线按近似等距点重采样，使 moveAlong 使用统一分段时长时保持匀速。 */
function buildMoveAlongPath(path: RoutePoint[]) {
  const spacing = 12
  const sampled: RoutePoint[] = [path[0]]
  let totalDistance = 0

  for (let i = 1; i < path.length; i++) {
    const from = path[i - 1]
    const to = path[i]
    const distance = pointDistance(from, to)
    if (distance < 0.5) continue
    totalDistance += distance
    const steps = Math.max(1, Math.ceil(distance / spacing))
    for (let step = 1; step <= steps; step++) {
      const ratio = step / steps
      sampled.push([
        from[0] + (to[0] - from[0]) * ratio,
        from[1] + (to[1] - from[1]) * ratio,
      ])
    }
  }

  if (sampled.length < 2 || totalDistance < 0.5) return null
  const totalDuration = Math.min(30000, Math.max(8000, totalDistance * 20))
  return {
    path: sampled,
    duration: Math.max(50, Math.round(totalDuration / (sampled.length - 1))),
  }
}

function startMovingArrow(path: RoutePoint[], version: number) {
  if (version !== routeRequestVersion || !map) return
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  const animation = buildMoveAlongPath(path)
  if (!animation) return

  const AMap = window.AMap
  movingArrow = new AMap.Marker({
    position: path[0],
    content: '<div class="route-moving-arrow">➤</div>',
    offset: { x: -14, y: -14 },
    zIndex: 200,
  })
  movingArrow.setMap(map)
  if (typeof movingArrow.moveAlong !== 'function') {
    movingArrow.setMap(null)
    movingArrow = null
    return
  }
  movingArrow.moveAlong(animation.path, {
    duration: animation.duration,
    autoRotation: true,
    circlable: true,
  })
  isAnimating.value = true
  isPaused.value = false
}

/**
 * 按景点名顺序规划并绘制步行路线。
 * 每个相邻景点独立规划；失败段以虚线显示，禁止跨越失败段错误直连。
 */
async function drawRouteByNames(names?: string[] | null) {
  if (!map) return initMap()

  const version = ++routeRequestVersion
  const label = props.activeRoute?.title || t('map.routeLabel')
  clearRouteOverlays()

  const matched: Array<ScenicSpot | null> = (names && names.length)
    ? names.map(matchSpot)
    : spots.slice()
  const targets = matched.filter((spot): spot is ScenicSpot => spot !== null)
  const unmatchedCount = matched.length - targets.length

  if (targets.length < 2) {
    routeStatus.value = names?.length ? t('map.notEnough') : t('map.spotsNotEnough')
    return
  }

  const AMap = window.AMap
  const planner = new AMap.Walking({ hideMarkers: true })
  const plannedSegments: PlannedSegment[] = []
  routeStatus.value = t('map.planning')

  for (let i = 0; i < matched.length - 1; i++) {
    const from = matched[i]
    const to = matched[i + 1]
    if (!from || !to) continue
    const origin: RoutePoint = [from.lng!, from.lat!]
    const dest: RoutePoint = [to.lng!, to.lat!]
    if (pointDistance(origin, dest) < 0.5) continue

    const walkingPath = await planWalkingSegment(planner, origin, dest)
    if (version !== routeRequestVersion || !map) return
    plannedSegments.push({
      path: walkingPath || [origin, dest],
      fallback: !walkingPath,
    })
  }

  if (version !== routeRequestVersion || !map) return
  if (!plannedSegments.length) {
    routeStatus.value = unmatchedCount
      ? t('map.unmatched', { label })
      : t('map.noSegment', { label })
    return
  }

  plannedSegments.forEach((segment) => {
    const line = new AMap.Polyline(segment.fallback ? {
      path: segment.path,
      strokeColor: '#2D6A4F',
      strokeWeight: 6,
      strokeOpacity: 0.72,
      strokeStyle: 'dashed',
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true,
      dirColor: '#FFFFFF',
    } : {
      path: segment.path,
      strokeColor: '#B07D4F',
      strokeWeight: 8,
      strokeOpacity: 0.94,
      isOutline: true,
      outlineColor: '#FFFFFF',
      borderWeight: 2,
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true,
      dirColor: '#FFFFFF',
    })
    line.setMap(map)
    routePolylines.push(line)
  })

  const fallbackCount = plannedSegments.filter(segment => segment.fallback).length
  const successCount = plannedSegments.length - fallbackCount
  const suffix = unmatchedCount ? t('map.unmatchedSuffix', { count: unmatchedCount }) : ''
  if (!fallbackCount) {
    routeStatus.value = t('map.success', { label, stations: targets.length, segments: successCount, suffix })
  } else if (successCount) {
    routeStatus.value = t('map.partial', { label, success: successCount, total: plannedSegments.length, fallback: fallbackCount, suffix })
  } else {
    routeStatus.value = t('map.failed', { label, suffix })
  }

  const animationPath = unmatchedCount ? null : mergeSegmentPaths(plannedSegments)
  if (animationPath) startMovingArrow(animationPath, version)

  const routeMarkers = markers.filter((marker) => {
    const pos = marker.getPosition()
    return targets.some(spot => spot.lng === pos.getLng() && spot.lat === pos.getLat())
  })
  map.setFitView([...routePolylines, ...routeMarkers], false, [60, 60, 60, 60])
}

// toolbar「路线」按钮：有推荐就画推荐，否则画全部景点
function drawActiveRoute() {
  if (props.activeRoute?.spots?.length) drawRouteByNames(props.activeRoute.spots)
  else drawRouteByNames()
}

// 推荐路线变化时自动重画（地图就绪后）
watch(() => props.activeRoute, (route) => {
  if (!ready.value || !map) return
  if (route?.spots?.length) drawRouteByNames(route.spots)
  else clearRoute()
})

watch(locale, async () => {
  infoWindow?.close()
  clearRoute()
  if (ready.value && map) {
    markers.forEach(marker => marker.setMap(null))
    markers = []
    markerMap.clear()
    map.destroy()
    map = null
    ready.value = false
    await initMap()
  }
  await loadWeather()
})

defineExpose({ drawRouteByNames, fitAll, focusSpot })

function fitAll() {
  if (!map) return initMap()
  const visible = getVisibleMarkers()
  if (visible.length) map.setFitView(visible, false, [60, 60, 60, 60])
}

onMounted(() => {
  loadFilter()
  initMap()
  loadWeather()
  document.addEventListener('click', onInfoClick, true)
})

onUnmounted(() => {
  document.removeEventListener('click', onInfoClick, true)
  stopGPS()
  if (geofenceTimer) clearTimeout(geofenceTimer)
  clearRoute()
  if (map) {
    markers.forEach(marker => marker.setMap(null))
    infoWindow?.close()
    map.destroy()
    map = null
  }
})
</script>

<style scoped>
.scenic-map-wrap { display: flex; flex-direction: column; gap: 12px; }

/* 天气卡片 */
.weather-card {
  background: linear-gradient(135deg, #2D6A4F 0%, #40916C 60%, #52B788 100%);
  border-radius: 16px; padding: 16px 20px; color: #fff;
  box-shadow: 0 4px 16px rgba(45,106,79,0.18);
  min-height: 96px;
}
.weather-card.loading { opacity: 0.85; }
.wc-loading, .wc-error {
  display: flex; align-items: center; justify-content: center; height: 64px;
  font-size: 0.8rem; opacity: 0.85;
}
.wc-main { display: flex; align-items: center; gap: 14px; }
.wc-emoji { font-size: 2.4rem; line-height: 1; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.15)); }
.wc-center { display: flex; flex-direction: column; }
.wc-temp { font-size: 1.9rem; font-weight: 700; line-height: 1.1; }
.wc-desc { font-size: 0.85rem; opacity: 0.9; }
.wc-meta { margin-left: auto; text-align: right; display: flex; flex-direction: column; gap: 2px; }
.wc-place { font-size: 0.78rem; font-weight: 600; opacity: 0.95; }
.wc-detail { font-size: 0.68rem; opacity: 0.8; }
.wc-refresh {
  align-self: flex-end; margin-top: 4px; background: rgba(255,255,255,0.18);
  border: none; color: #fff; font-size: 0.68rem; padding: 3px 10px; border-radius: 10px;
  cursor: pointer; transition: background 0.2s;
}
.wc-refresh:hover:not(:disabled) { background: rgba(255,255,255,0.3); }
.wc-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.wc-forecast {
  display: flex; gap: 8px; margin-top: 12px; padding-top: 12px;
  border-top: 1px solid rgba(255,255,255,0.18);
}
.fc-day {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
  font-size: 0.7rem; opacity: 0.95;
}
.fc-date { font-weight: 600; opacity: 0.9; }
.fc-emoji { font-size: 1.1rem; }
.fc-weather { font-size: 0.66rem; opacity: 0.85; }
.fc-temp { font-size: 0.68rem; opacity: 0.75; }

.scenic-map { position: relative; }
.map-container { width: 100%; height: 280px; }
.map-placeholder {
  position: absolute; inset: 0; height: 280px;
  background: linear-gradient(135deg, #e8efe6, #f0f4ed, #e4ece2);
  display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 1;
}
.map-placeholder.hidden { display: none; }
.ph-pin {
  width: 48px; height: 48px; border-radius: 16px; background: rgba(255,255,255,0.8);
  backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center;
  margin-bottom: 10px; box-shadow: 0 2px 12px rgba(45,106,79,0.12); color: var(--color-primary);
}
.map-placeholder p { font-size: 0.75rem; font-weight: 600; color: rgba(45,106,79,0.7); }
.map-placeholder span { font-size: 10px; color: var(--color-text-muted); margin-top: 4px; }

.map-toolbar {
  display: flex; gap: 8px; padding: 10px 16px; background: #fff; border-top: 1px solid rgba(0,0,0,0.04);
  flex-wrap: wrap;
}
.map-toolbar button {
  display: flex; align-items: center; gap: 6px; border: none; background: none;
  cursor: pointer; font-size: 0.75rem; color: var(--color-text-secondary); padding: 4px 8px; border-radius: 6px;
  position: relative;
}
.map-toolbar button:hover { color: var(--color-primary); background: var(--color-primary-bg); }
.route-status { font-size: 0.7rem; color: var(--color-primary); margin-left: auto; align-self: center; }

.filter-badge {
  position: absolute; top: -2px; right: -2px;
  min-width: 14px; height: 14px; padding: 0 3px;
  background: #B07D4F; color: #fff; font-size: 9px; font-weight: 700;
  border-radius: 7px; display: flex; align-items: center; justify-content: center;
  border: 1.5px solid #fff; line-height: 1;
}

.filter-quick-actions {
  display: flex; gap: 6px; margin-bottom: 12px; padding-bottom: 12px;
  border-bottom: 1px solid rgba(0,0,0,0.06);
}
.filter-link {
  border: none; background: none; cursor: pointer;
  font-size: 0.78rem; color: var(--color-primary); padding: 4px 10px; border-radius: 6px;
  transition: background 0.15s;
}
.filter-link:hover { background: var(--color-primary-bg); }

.filter-group { margin-bottom: 14px; }
.filter-group-label {
  font-size: 0.72rem; font-weight: 700; color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px;
  padding: 2px 0;
}
.filter-checkboxes { display: flex; flex-wrap: wrap; gap: 6px; }
.filter-checkbox-item { margin-right: 0 !important; margin-bottom: 0 !important; }
:deep(.filter-checkbox-item .el-checkbox__label) { font-size: 0.8rem; padding-left: 4px; }

.filter-btn {
  border: none; border-radius: 8px; padding: 8px 18px;
  font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: background 0.2s;
}
.filter-btn--cancel {
  background: #f5f5f5; color: var(--color-text-secondary); margin-right: 8px;
}
.filter-btn--cancel:hover { background: #e8e8e8; }
.filter-btn--apply {
  background: #B07D4F; color: #fff;
}
.filter-btn--apply:hover { background: #9a6b3f; }

.toolbar-active { color: var(--color-primary) !important; background: var(--color-primary-bg) !important; }
.pin-mode-hint { font-size: 0.68rem; color: var(--color-primary); align-self: center; flex: 1; text-align: center; }
.pin-delete-tip { font-size: 0.72rem; color: var(--color-text-muted); margin-top: 8px; }

.geofence-notif {
  position: absolute; bottom: 56px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 8px;
  background: #fff; border-radius: 12px; padding: 10px 14px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15); z-index: 400;
  min-width: 240px; max-width: 88vw;
}
.gf-icon { font-size: 1.4rem; flex-shrink: 0; }
.gf-text { flex: 1; min-width: 0; }
.gf-title { font-size: 0.82rem; font-weight: 700; color: #1a3a2a; }
.gf-sub { font-size: 0.7rem; color: #5a6c5d; }
.gf-guide {
  border: none; border-radius: 8px; background: #B07D4F; color: #fff;
  font-size: 0.75rem; font-weight: 600; padding: 5px 10px; cursor: pointer; flex-shrink: 0;
}
.gf-dismiss { border: none; background: none; color: #999; font-size: 0.72rem; cursor: pointer; flex-shrink: 0; }
.gf-slide-enter-active, .gf-slide-leave-active { transition: all 0.3s ease; }
.gf-slide-enter-from, .gf-slide-leave-to { opacity: 0; transform: translateX(-50%) translateY(12px); }
</style>

<!-- InfoWindow 与 marker 的 HTML 注入到地图容器内，不能用 scoped，需全局样式 -->
<style>
.map-pin-wrap {
  /* 36 宽 44 高：badge 36x36 居中靠上，尖端由 ::after 三角补在底部中心 (18,44) */
  position: relative; width: 36px; height: 44px; cursor: pointer;
  filter: drop-shadow(0 3px 6px rgba(45,106,79,0.35));
}
.map-pin-badge {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #2D6A4F, #40916C);
  display: flex; align-items: center; justify-content: center;
  border: 2px solid #fff;
  box-sizing: border-box;
}
.map-pin-badge span {
  font-size: 16px; line-height: 1;
}
/* 水滴尖端：三角，顶点在 wrap 底部中心 (18,44)，与 offset:{x:-18,y:-44} 对齐 */
.map-pin-wrap::after {
  content: ''; position: absolute; left: 50%; top: 32px;
  transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-top: 12px solid #fff;
}
.map-pin-wrap::before {
  content: ''; position: absolute; left: 50%; top: 34px;
  transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 9px solid #2D6A4F;
  z-index: 1;
}
.map-pin-num {
  position: absolute; top: -4px; right: -4px;
  min-width: 16px; height: 16px; padding: 0 4px;
  background: #B07D4F; color: #fff; font-size: 10px; font-weight: 700;
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  border: 1.5px solid #fff;
  z-index: 2;
}

/* 缩略图标记：替换 emoji 为圆形图片 */
.map-pin-badge--thumb {
  background: #fff;
  padding: 2px;
  overflow: hidden;
}
.map-pin-thumb-img {
  width: 100%; height: 100%; object-fit: cover;
  border-radius: 50%; display: block;
}
.map-pin-thumb-fallback {
  width: 100%; height: 100%; border-radius: 50%;
  background: linear-gradient(135deg, #2D6A4F, #40916C);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
}

/* 点击路线景点名后的定位反馈：放大回弹 + 光晕脉冲 */
.map-pin-bounce { z-index: 10; }
.map-pin-bounce .map-pin-badge {
  animation: pin-bounce 0.9s ease;
}
@keyframes pin-bounce {
  0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(176,125,79,0.55); }
  30% { transform: scale(1.45); box-shadow: 0 0 0 8px rgba(176,125,79,0.25); }
  60% { transform: scale(0.95); box-shadow: 0 0 0 14px rgba(176,125,79,0); }
  100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(176,125,79,0); }
}
@media (prefers-reduced-motion: reduce) {
  .map-pin-bounce .map-pin-badge { animation: none; }
}

/* 路线方向动效箭头：朝右绘制，由高德 autoRotation 自动沿路线旋转。 */
.route-moving-arrow {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: #B07D4F; color: #fff;
  border: 2px solid #fff;
  font-size: 17px; line-height: 1;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(71, 43, 20, 0.35);
}

/* InfoWindow 卡片 */
.iw-card {
  width: 220px; border-radius: 12px; overflow: hidden;
  background: #fff; font-family: -apple-system, "PingFang SC", sans-serif;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.iw-thumb {
  width: 100%; height: 110px; object-fit: cover; display: block;
}
.iw-body { padding: 10px 12px 12px; }
.iw-body h3 {
  margin: 0 0 6px; font-size: 14px; font-weight: 700; color: #1a3a2a;
}
.iw-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.iw-tags span {
  font-size: 10px; color: #2D6A4F; background: #e8f3ee;
  padding: 1px 6px; border-radius: 4px;
}
.iw-desc {
  margin: 0 0 10px; font-size: 12px; line-height: 1.5; color: #5a6c5d;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.iw-btn {
  width: 100%; padding: 7px; border: none; border-radius: 8px;
  background: #B07D4F; color: #fff; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: background 0.2s;
}
.iw-btn:hover { background: #9a6b3f; }

/* 高德 InfoWindow 默认样式微调 */
.amap-info-content { padding: 0 !important; border-radius: 12px !important; overflow: hidden; }
.amap-info-close { display: none !important; }
.amap-info-sharp { display: none !important; }

/* GPS用户位置蓝点 */
.user-location-dot {
  width: 24px; height: 24px; border-radius: 50%;
  background: #4A90E2; border: 3px solid #fff;
  box-shadow: 0 0 0 6px rgba(74,144,226,0.25);
  animation: loc-pulse 2s ease-in-out infinite;
}
@keyframes loc-pulse {
  0%, 100% { box-shadow: 0 0 0 6px rgba(74,144,226,0.25); }
  50% { box-shadow: 0 0 0 12px rgba(74,144,226,0.08); }
}
@media (prefers-reduced-motion: reduce) { .user-location-dot { animation: none; } }

/* 自定义标记 */
.custom-pin-wrap {
  background: #fff; border: 2px solid #B07D4F; color: #B07D4F;
  font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 10px;
  white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  cursor: pointer; user-select: none; position: relative;
}
.custom-pin-wrap::after {
  content: ''; position: absolute; left: 50%; bottom: -8px;
  transform: translateX(-50%);
  width: 0; height: 0;
  border-left: 5px solid transparent; border-right: 5px solid transparent;
  border-top: 8px solid #B07D4F;
}
</style>