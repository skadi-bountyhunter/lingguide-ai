<template>
  <div class="video-page">
    <!-- Header -->
    <header class="video-header">
      <button class="back-btn" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <h1>{{ t('video.title') }}</h1>
      <div class="header-spacer" />
    </header>

    <!-- 视频列表 -->
    <div class="video-list">
      <a v-for="video in videos" :key="video.id"
        :href="video.shareUrl" target="_blank"
        class="video-card card">
        <div class="video-thumb">
          <img :src="video.cover" :alt="video.title" />
          <div class="play-icon">▶</div>
        </div>
        <div class="video-info">
          <h3>{{ video.title }}</h3>
          <p>{{ video.desc }}</p>
          <div class="video-meta">
            <span class="video-hint">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              {{ t('video.hint') }}
            </span>
            <span class="video-source">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>
              {{ video.source }}
            </span>
          </div>
        </div>
      </a>
    </div>

    <div style="height: 80px" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const { t } = useI18n()
const videos = ref<VideoItem[]>([])

interface VideoItem {
  id: string
  title: string
  desc: string
  cover: string
  duration: string
  views: string
  source: string
  category: string
  shareUrl: string
}

const categories = ['全部', '大佛风光', '梵宫艺术', '九龙灌浴', '景区四季']

onMounted(async () => {
  try {
    const resp = await fetch('/data/douyin_videos.json')
    const data = await resp.json()
    videos.value = data.videos || []
  } catch (e) {
    console.error('加载视频数据失败:', e)
    videos.value = []
  }
})
</script>

<style scoped>
.video-page { max-width: 672px; margin: 0 auto; min-height: 100vh; background: var(--color-bg-page); }

.video-header { display: flex; align-items: center; padding: 12px 16px; background: rgba(255,255,255,0.95); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(0,0,0,0.04); position: sticky; top: 0; z-index: 10; }
.back-btn { width: 36px; height: 36px; border-radius: 50%; border: none; background: none; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--color-text-primary); }
.back-btn:hover { background: var(--color-primary-bg); }
.video-header h1 { flex: 1; text-align: center; font-size: 1.125rem; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.header-spacer { width: 36px; }

.video-list { padding: 0 16px 16px; display: flex; flex-direction: column; gap: 12px; }
.video-card { display: flex; overflow: hidden; text-decoration: none; color: inherit; transition: transform 0.2s, box-shadow 0.2s; background: #fff; border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.video-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.video-card:active { transform: scale(0.98); }
.video-thumb { width: 140px; height: 100px; flex-shrink: 0; position: relative; overflow: hidden; background: var(--color-bg-muted); }
.video-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.play-icon { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 28px; height: 28px; border-radius: 50%; background: rgba(0,0,0,0.5); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; }
.video-info { flex: 1; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; }
.video-info h3 { font-size: 0.875rem; font-weight: 600; color: var(--color-text-primary); margin: 0 0 4px 0; }
.video-info p { font-size: 0.75rem; color: var(--color-text-muted); margin: 0; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.video-meta { display: flex; gap: 12px; margin-top: 8px; align-items: center; }
.video-hint { display: flex; align-items: center; gap: 4px; font-size: 0.6875rem; color: var(--color-primary); font-weight: 500; }
.video-source { display: flex; align-items: center; gap: 4px; font-size: 0.6875rem; color: var(--color-text-muted); margin-left: auto; }

/* 移动端适配 */
@media (max-width: 480px) {
  .video-card { border-radius: 12px; }
  .video-thumb { width: 120px; height: 90px; }
  .video-info { padding: 10px; }
  .video-info h3 { font-size: 0.8125rem; }
  .video-info p { font-size: 0.6875rem; -webkit-line-clamp: 2; }
  .play-icon { width: 24px; height: 24px; font-size: 0.6rem; }
}
</style>
