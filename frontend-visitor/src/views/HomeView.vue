<template>
  <div class="home-page">
    <!-- Header -->
    <header class="home-header">
      <div class="header-left">
        <div class="brand-icon"><img src="/images/logo.png" alt="logo" /></div>
        <div>
          <h1>{{ t('home.scenic') }}</h1>
          <p>{{ t('home.subtitle') }}</p>
        </div>
      </div>
      <button class="notify-btn" :title="t('home.notifications')" @click="router.push({ name: 'profile-notifications' })">
        <el-icon><Bell /></el-icon>
      </button>
    </header>

    <!-- Carousel -->
    <div class="carousel" @touchstart="onTouchStart" @touchend="onTouchEnd">
      <div class="carousel-track" :style="{ transform: `translateX(-${currentSlide * 100}%)` }">
        <div v-for="item in carouselItems" :key="item.canonicalName" class="carousel-slide" @click="goSpot(item.canonicalName)">
          <img :src="item.image" :alt="item.displayName" />
          <div class="slide-overlay" />
          <div class="slide-text">
            <h2>{{ item.displayName }}</h2>
            <p>{{ item.subtitle }}</p>
          </div>
        </div>
      </div>
      <div class="carousel-dots">
        <button v-for="(_, i) in carouselItems" :key="i"
          :class="{ active: currentSlide === i }" @click="currentSlide = i" />
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <button v-for="act in actions" :key="act.label" @click="act.action">
        <img class="act-img" :src="act.image" :alt="act.label" />
        <span class="act-label">{{ act.label }}</span>
      </button>
    </div>

    <!-- Scenic Spots -->
    <section class="spots-section">
      <div class="section-header">
        <div class="sec-left"><span>🏔️</span><h2>{{ t('home.spots') }}</h2></div>
        <span class="sec-count">{{ t('home.spotCount', { count: spots.length }) }}</span>
      </div>
      <div class="spots-list">
        <div v-for="(spot, idx) in spots" :key="spot.canonicalName" class="card card-interactive spot-card"
          :style="{ animationDelay: `${0.1 + idx * 0.05}s` }"
          @click="goSpot(spot.canonicalName)">
          <div class="spot-img">
            <img :src="spot.image" :alt="spot.displayName" />
          </div>
          <div class="spot-info">
            <h3>{{ spot.displayName }}</h3>
            <p class="spot-desc">{{ spot.desc }}</p>
            <div class="spot-meta">
              <span><el-icon><Clock /></el-icon>{{ spot.duration }}</span>
              <span><el-icon><LocationFilled /></el-icon>{{ spot.distance }}</span>
              <div class="spot-tags">
                <span v-for="tag in spot.displayTags" :key="tag">{{ tag }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Info Banner -->
    <section class="info-banner card">
      <div class="banner-icon"><span>📢</span></div>
      <div>
        <p class="banner-title">{{ t('home.notice') }}</p>
        <p class="banner-text">{{ t('home.noticeText') }}</p>
      </div>
    </section>

    <div style="height: 80px" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchSpots, fetchCarousel, type ScenicSpot, type CarouselItem } from '../data/spots'

const router = useRouter()
const { t, locale } = useI18n()

const spots = ref<ScenicSpot[]>([])
const carouselItems = ref<CarouselItem[]>([])
const loading = ref(true)

const actions = computed(() => [
  { image: '/images/features/ai-guide.jpg', label: t('home.aiGuide'), action: () => router.push({ name: 'chat' }) },
  { image: '/images/features/route.jpg', label: t('home.routePlan'), action: () => router.push({ name: 'route' }) },
  { image: '/images/features/videos.jpg', label: t('home.videos'), action: () => router.push({ name: 'videos' }) },
  { image: '/images/features/map.jpg', label: t('home.map'), action: () => ElMessage.info(t('home.mapDeveloping')) },
])

const currentSlide = ref(0)
let autoTimer: ReturnType<typeof setInterval> | null = null
let touchStartX = 0

async function loadHomeData() {
  loading.value = true
  try {
    const [s, c] = await Promise.all([fetchSpots(), fetchCarousel()])
    spots.value = s
    carouselItems.value = c
    currentSlide.value = 0
  } catch (e) {
    console.error('加载景点数据失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadHomeData()
  if (carouselItems.value.length) {
    autoTimer = setInterval(() => {
      currentSlide.value = (currentSlide.value + 1) % carouselItems.value.length
    }, 4000)
  }
})
watch(locale, loadHomeData)
onUnmounted(() => { if (autoTimer) clearInterval(autoTimer) })

function onTouchStart(e: TouchEvent) { touchStartX = e.touches[0].clientX }
function onTouchEnd(e: TouchEvent) {
  const diff = touchStartX - e.changedTouches[0].clientX
  if (Math.abs(diff) > 50) {
    if (diff > 0) currentSlide.value = (currentSlide.value + 1) % carouselItems.value.length
    else currentSlide.value = (currentSlide.value - 1 + carouselItems.value.length) % carouselItems.value.length
  }
}

function goSpot(name: string) {
  router.push({ name: 'spot', params: { name } })
}
</script>

<style scoped>
.home-page { max-width: 672px; margin: 0 auto; min-height: 100vh; }
.home-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: rgba(255,255,255,0.8); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(0,0,0,0.04); position: sticky; top: 0; z-index: 10; }
.header-left { display: flex; align-items: center; gap: 8px; }
.brand-icon { width: 32px; height: 32px; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.brand-icon img { width: 100%; height: 100%; object-fit: contain; }
.header-left h1 { font-size: 1rem; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.header-left p { font-size: 10px; color: var(--color-text-muted); }
.notify-btn { width: 32px; height: 32px; border-radius: 8px; border: none; background: none; cursor: pointer; color: var(--color-text-muted); display: flex; align-items: center; justify-content: center; }
.notify-btn:hover { color: var(--color-primary); background: var(--color-primary-bg); }

/* Carousel */
.carousel { position: relative; overflow: hidden; }
.carousel-track { display: flex; transition: transform 0.5s ease-out; }
.carousel-slide { width: 100%; flex-shrink: 0; position: relative; height: 220px; cursor: pointer; }
.carousel-slide img { width: 100%; height: 100%; object-fit: cover; }
.slide-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.6), rgba(0,0,0,0.1), transparent); }
.slide-text { position: absolute; bottom: 0; left: 0; right: 0; padding: 20px; color: #fff; }
.slide-text h2 { font-size: 1.25rem; font-weight: 700; margin-bottom: 2px; }
.slide-text p { font-size: 0.75rem; opacity: 0.8; }
.carousel-dots { position: absolute; bottom: 12px; right: 16px; display: flex; gap: 6px; }
.carousel-dots button { border-radius: 50%; border: none; transition: all 0.3s; cursor: pointer; height: 6px; }
.carousel-dots button.active { width: 20px; height: 6px; border-radius: 3px; background: #fff; }
.carousel-dots button:not(.active) { width: 6px; background: rgba(255,255,255,0.5); }

/* Quick Actions */
.quick-actions { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 16px; }
.quick-actions button { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 12px 0; border-radius: 16px; border: none; background: #fff; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.04); transition: all 0.2s; }
.quick-actions button:active { transform: scale(0.95); }
.quick-actions button:hover { background: var(--color-primary-bg); }
.act-img { width: 40px; height: 40px; border-radius: 10px; object-fit: cover; }
.act-label { font-size: 11px; color: var(--color-text-secondary); font-weight: 500; }

/* Spots */
.spots-section { padding: 0 16px 16px; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sec-left { display: flex; align-items: center; gap: 8px; }
.sec-left h2 { font-size: 15px; font-weight: 700; color: var(--color-text-primary); }
.sec-count { font-size: 0.75rem; color: var(--color-text-muted); }
.spots-list { display: flex; flex-direction: column; gap: 12px; }
.spot-card { display: flex; overflow: hidden; animation: fadeUp 0.6s ease-out forwards; opacity: 0; cursor: pointer; }
.spot-img { width: 112px; height: 112px; flex-shrink: 0; position: relative; }
.spot-img img { width: 100%; height: 100%; object-fit: cover; }
.spot-info { flex: 1; padding: 14px; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; }
.spot-info h3 { font-size: 0.875rem; font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.spot-desc { font-size: 11px; color: var(--color-text-muted); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.spot-meta { display: flex; align-items: center; gap: 12px; margin-top: 8px; flex-wrap: wrap; }
.spot-meta span { display: flex; align-items: center; gap: 2px; font-size: 10px; color: var(--color-text-muted); }
.spot-tags { display: flex; gap: 4px; margin-left: auto; }
.spot-tags span { font-size: 9px; color: var(--color-primary); background: var(--color-primary-bg); padding: 2px 6px; border-radius: 4px; font-weight: 500; }

/* Banner */
.info-banner { margin: 0 16px 16px; padding: 16px; display: flex; gap: 12px; background: linear-gradient(135deg, rgba(45,106,79,0.05), rgba(176,125,79,0.05)); border-color: rgba(45,106,79,0.1); }
.banner-icon { width: 40px; height: 40px; border-radius: 12px; background: var(--color-primary-bg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 1.25rem; }
.banner-title { font-size: 0.75rem; font-weight: 600; color: var(--color-text-primary); margin-bottom: 2px; }
.banner-text { font-size: 11px; color: var(--color-text-muted); line-height: 1.6; }
</style>
