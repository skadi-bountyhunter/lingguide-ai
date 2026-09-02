<template>
  <div class="spot-detail" v-if="notFound">
    <div class="empty-state">
      <p class="empty-icon">📍</p>
      <h2>{{ t('spotDetail.notFound') }}</h2>
      <p>{{ t('spotDetail.notFoundDesc', { name: route.params.name }) }}</p>
      <el-button type="primary" @click="router.push({ name: 'home' })">{{ t('spotDetail.home') }}</el-button>
    </div>
  </div>
  <div class="spot-detail" v-else-if="!spot">
    <div class="empty-state" v-loading="loading" />
  </div>
  <div class="spot-detail" v-else>
    <!-- Hero 大图 -->
    <div class="hero" :style="{ height: '320px' }">
      <div v-if="!imgLoaded" class="hero-skeleton" />
      <img
        :src="spot.image"
        :alt="spot.displayName"
        class="hero-img"
        @load="imgLoaded = true"
      />
      <div class="hero-gradient" />

      <!-- 返回 -->
      <button class="hero-back" @click="router.back()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>

      <!-- 标题覆盖层 -->
      <div class="hero-title-area">
        <div class="hero-title-row">
          <span class="hero-icon">{{ spot.icon }}</span>
          <h1>{{ spot.displayName }}</h1>
        </div>
        <div class="hero-tags">
          <span v-for="tag in spot.displayTags" :key="tag" class="hero-tag">{{ tag }}</span>
        </div>
      </div>
    </div>

    <!-- 快捷信息栏 -->
    <div class="quick-info card">
      <div class="qi-item">
        <div class="qi-icon qi-icon-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <span class="qi-label">{{ t('spotDetail.duration') }}</span>
        <span class="qi-value">{{ spot.duration }}</span>
      </div>
      <div class="qi-divider" />
      <div class="qi-item">
        <div class="qi-icon qi-icon-accent">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        </div>
        <span class="qi-label">{{ t('spotDetail.distance') }}</span>
        <span class="qi-value">{{ spot.distance }}</span>
      </div>
      <template v-if="showLocalizedDetails">
        <div class="qi-divider" />
        <div class="qi-item">
          <div class="qi-icon qi-icon-sage">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-sage, #8FAE8B)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </div>
          <span class="qi-label">{{ t('spotDetail.bestSeason') }}</span>
          <span class="qi-value qi-value-sm">{{ spot.bestSeason.length > 8 ? spot.bestSeason.substring(0, 8) + '…' : spot.bestSeason }}</span>
        </div>
      </template>
    </div>

    <!-- 景点介绍 -->
    <section v-if="showLocalizedIntro" class="card section-block">
      <h2 class="section-title"><span class="section-bar section-bar-primary" />{{ t('spotDetail.intro') }}</h2>
      <p v-for="(para, i) in localizedIntro.split('\n\n')" :key="i" class="desc-para">{{ para }}</p>
    </section>

    <!-- 核心亮点 -->
    <section v-if="showLocalizedDetails" class="card section-block">
      <h2 class="section-title"><span class="section-bar section-bar-accent" />{{ t('spotDetail.highlights') }}</h2>
      <div class="highlights-grid">
        <div v-for="(h, i) in spot.highlights" :key="i" class="highlight-item">
          <div class="highlight-num">{{ String(i + 1).padStart(2, '0') }}</div>
          <span class="highlight-text">{{ h }}</span>
        </div>
      </div>
    </section>

    <!-- 实用信息 -->
    <section v-if="showLocalizedDetails" class="card section-block">
      <h2 class="section-title"><span class="section-bar section-bar-mist" />{{ t('spotDetail.info') }}</h2>
      <div class="info-list">
        <div class="info-row">
          <div class="info-icon qi-icon-accent">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </div>
          <div>
            <p class="info-label">{{ t('spotDetail.hours') }}</p>
            <p class="info-value">{{ spot.hours }}</p>
          </div>
        </div>
        <div class="info-divider" />
        <div class="info-row">
          <div class="info-icon qi-icon-primary">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 10h20"/></svg>
          </div>
          <div>
            <p class="info-label">{{ t('spotDetail.ticket') }}</p>
            <p class="info-value">{{ spot.ticket }}</p>
          </div>
        </div>
        <div class="info-divider" />
        <div class="info-row">
          <div class="info-icon qi-icon-sage">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-sage, #8FAE8B)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
          </div>
          <div>
            <p class="info-label">{{ t('spotDetail.bestSeason') }}</p>
            <p class="info-value">{{ spot.bestSeason }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 游览贴士 -->
    <section v-if="showLocalizedDetails" class="card section-block">
      <h2 class="section-title"><span class="section-bar section-bar-sage" />{{ t('spotDetail.tips') }}</h2>
      <div class="tips-list">
        <div v-for="(tip, i) in spot.tips" :key="i" class="tip-row">
          <div class="tip-check">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <p class="tip-text">{{ tip }}</p>
        </div>
      </div>
    </section>

    <!-- 周边景点 -->
    <section v-if="nearbySpots.length" class="nearby-section">
      <div class="nearby-header">
        <h2 class="section-title" style="margin-bottom:0"><span class="section-bar section-bar-mist" />{{ t('spotDetail.nearby') }}</h2>
      </div>
      <div class="nearby-scroll">
        <div v-for="ns in nearbySpots" :key="ns.canonicalName" class="nearby-card" @click="goSpot(ns.canonicalName)">
          <div class="nearby-img">
            <img :src="ns.image" :alt="ns.displayName" />
          </div>
          <div class="nearby-info">
            <div class="nearby-name-row">
              <span class="nearby-icon">{{ ns.icon }}</span>
              <span class="nearby-name">{{ ns.displayName }}</span>
            </div>
            <span class="nearby-duration">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {{ ns.duration }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- 底部操作栏 -->
    <div class="bottom-bar">
      <div class="bottom-bar-inner">
        <FavoriteButton
          :item-id="spot.canonicalName"
          :item-name="spot.displayName"
          :item-cover="spot.image"
          :show-label="true"
        />
        <button class="bar-btn bar-btn-primary" @click="aiGuide">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
          {{ t('spotDetail.aiGuide') }}
        </button>
        <button class="bar-btn bar-btn-accent" @click="navigateTo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          {{ t('spotDetail.navigate') }}
        </button>
      </div>
    </div>

    <div style="height: 90px" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { fetchSpot, fetchSpots, type ScenicSpot } from '../data/spots'
import FavoriteButton from '../components/FavoriteButton.vue'
import { createVisit } from '../services/profile'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const imgLoaded = ref(false)
const loading = ref(true)
const notFound = ref(false)
const spot = ref<ScenicSpot | null>(null)
const allSpots = ref<ScenicSpot[]>([])

const showLocalizedDetails = computed(() => locale.value === 'zh-CN')
const showLocalizedIntro = computed(() => (
  locale.value === 'zh-CN' || spot.value?.translationStatus === 'translated'
))
const localizedIntro = computed(() => {
  if (!spot.value) return ''
  return showLocalizedDetails.value ? spot.value.fullDesc : spot.value.desc
})

const nearbySpots = computed(() => {
  if (!spot.value) return []
  return allSpots.value.filter(s => spot.value!.nearby.includes(s.canonicalName))
})

async function loadSpot(name: string) {
  loading.value = true
  notFound.value = false
  imgLoaded.value = false
  try {
    // 并行：详情 + 全量列表（补全周边景点卡片信息）
    const [detail, list] = await Promise.all([fetchSpot(name), fetchSpots()])
    spot.value = detail
    allSpots.value = list
    // 足迹写入失败不阻断景点详情浏览。
    void createVisit({
      item_type: 'spot',
      item_id: detail.canonicalName,
      item_name: detail.displayName,
      item_cover: detail.image,
    }).catch(() => {})
  } catch (e) {
    console.error('加载景点详情失败', e)
    notFound.value = true
  } finally {
    loading.value = false
  }
}

watch(() => [route.params.name, locale.value], ([name]) => {
  if (typeof name === 'string') loadSpot(name)
}, { immediate: true })

function goSpot(name: string) {
  router.push({ name: 'spot', params: { name } })
  window.scrollTo({ top: 0 })
}

function aiGuide() {
  if (!spot.value) return
  router.push({ name: 'chat', query: { q: t('spotDetail.guideQuestion', { name: spot.value.displayName }) } })
}

function navigateTo() {
  ElMessage.info(t('spotDetail.navigationDeveloping'))
}
</script>

<style scoped>
.spot-detail { max-width: 672px; margin: 0 auto; min-height: 100vh; background: var(--color-bg-page); }

/* ===== Hero ===== */
.hero { position: relative; overflow: hidden; }
.hero-skeleton { position: absolute; inset: 0; background: var(--color-primary-bg); animation: pulseSoft 1.5s ease-in-out infinite; }
.hero-img { width: 100%; height: 100%; object-fit: cover; }
.hero-gradient { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.7), rgba(0,0,0,0.2), transparent); }
.hero-back {
  position: absolute; top: 16px; left: 16px; width: 36px; height: 36px; border-radius: 50%;
  background: rgba(0,0,0,0.3); backdrop-filter: blur(8px); border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s;
}
.hero-back:hover { background: rgba(0,0,0,0.5); }
.hero-back:active { transform: scale(0.9); }

.hero-title-area { position: absolute; bottom: 0; left: 0; right: 0; padding: 20px; color: #fff; }
.hero-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.hero-icon { font-size: 1.5rem; }
.hero-title-row h1 { font-size: 1.5rem; font-weight: 700; }
.hero-tags { display: flex; gap: 8px; }
.hero-tag { font-size: 11px; color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.2); backdrop-filter: blur(4px); padding: 4px 10px; border-radius: 999px; font-weight: 500; }

/* ===== Quick Info ===== */
.quick-info {
  margin: -20px 16px 0; position: relative; z-index: 10;
  padding: 16px; display: flex; align-items: center; justify-content: space-around;
  gap: 0;
}
.qi-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; }
.qi-icon { width: 36px; height: 36px; border-radius: 12px; display: flex; align-items: center; justify-content: center; }
.qi-icon-primary { background: var(--color-primary-bg); }
.qi-icon-accent { background: var(--color-accent-bg); }
.qi-icon-sage { background: rgba(143,174,139,0.15); }
.qi-label { font-size: 11px; color: var(--color-text-muted); }
.qi-value { font-size: 0.875rem; font-weight: 700; color: var(--color-text-primary); }
.qi-value-sm { font-size: 11px; }
.qi-divider { width: 1px; height: 40px; background: rgba(0,0,0,0.06); }

/* ===== Sections ===== */
.section-block { margin: 20px 16px; padding: 16px; }
.section-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; color: var(--color-text-primary); margin-bottom: 12px; }
.section-bar { width: 3px; height: 16px; border-radius: 2px; }
.section-bar-primary { background: var(--color-primary); }
.section-bar-accent { background: var(--color-accent); }
.section-bar-mist { background: var(--color-mist, #C5D5E0); }
.section-bar-sage { background: var(--color-sage, #8FAE8B); }

.desc-para { font-size: 13px; color: var(--color-text-secondary); line-height: 1.8; margin-bottom: 12px; }
.desc-para:last-child { margin-bottom: 0; }

/* ===== Highlights ===== */
.highlights-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.highlight-item { display: flex; align-items: center; gap: 10px; background: var(--color-primary-bg); border-radius: 12px; padding: 10px 12px; }
.highlight-num { width: 28px; height: 28px; border-radius: 8px; background: rgba(45,106,79,0.1); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; color: var(--color-primary); flex-shrink: 0; }
.highlight-text { font-size: 12px; color: var(--color-text-primary); font-weight: 500; line-height: 1.3; }

/* ===== Info List ===== */
.info-list { display: flex; flex-direction: column; }
.info-row { display: flex; align-items: flex-start; gap: 12px; padding: 4px 0; }
.info-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.info-label { font-size: 12px; color: var(--color-text-muted); margin-bottom: 2px; }
.info-value { font-size: 13px; color: var(--color-text-primary); font-weight: 500; }
.info-divider { height: 1px; background: rgba(0,0,0,0.04); margin: 8px 0; }

/* ===== Tips ===== */
.tips-list { display: flex; flex-direction: column; gap: 10px; }
.tip-row { display: flex; align-items: flex-start; gap: 10px; }
.tip-check { width: 20px; height: 20px; border-radius: 50%; background: var(--color-accent-bg); display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.tip-text { font-size: 12px; color: var(--color-text-secondary); line-height: 1.6; }

/* ===== Nearby ===== */
.nearby-section { margin-top: 16px; }
.nearby-header { padding: 0 16px; margin-bottom: 12px; }
.nearby-scroll { display: flex; gap: 12px; overflow-x: auto; padding: 0 16px 8px; scroll-behavior: smooth; }
.nearby-scroll::-webkit-scrollbar { display: none; }
.nearby-card { flex-shrink: 0; width: 144px; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.05); cursor: pointer; transition: transform 0.2s; }
.nearby-card:active { transform: scale(0.97); }
.nearby-img { height: 96px; overflow: hidden; }
.nearby-img img { width: 100%; height: 100%; object-fit: cover; }
.nearby-info { padding: 10px; }
.nearby-name-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.nearby-icon { font-size: 0.875rem; }
.nearby-name { font-size: 12px; font-weight: 700; color: var(--color-text-primary); }
.nearby-duration { display: flex; align-items: center; gap: 2px; font-size: 10px; color: var(--color-text-muted); }

/* ===== Bottom Bar ===== */
.bottom-bar {
  position: fixed; bottom: 0; left: 0; right: 0; z-index: 50;
  background: rgba(255,255,255,0.9); backdrop-filter: blur(12px);
  border-top: 1px solid rgba(0,0,0,0.04);
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.bottom-bar-inner { max-width: 672px; margin: 0 auto; display: flex; gap: 10px; padding: 12px 16px; align-items: center; }
.bar-btn {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 12px; border-radius: 12px; border: none; font-size: 0.875rem; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
}
.bar-btn:active { transform: scale(0.98); }
.bar-btn-primary { background: var(--color-primary); color: #fff; box-shadow: 0 4px 16px rgba(45,106,79,0.25); }
.bar-btn-accent { background: var(--color-accent); color: #fff; box-shadow: 0 4px 16px rgba(176,125,79,0.25); }

@keyframes pulseSoft { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* ===== 空态/加载 ===== */
.empty-state { max-width: 672px; margin: 0 auto; min-height: 60vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 40px; text-align: center; }
.empty-icon { font-size: 3rem; margin-bottom: 8px; }
.empty-state h2 { font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); }
.empty-state p { font-size: 0.875rem; color: var(--color-text-muted); }
</style>
