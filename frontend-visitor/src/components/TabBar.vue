<template>
  <nav class="tab-bar">
    <button v-for="tab in tabs" :key="tab.key" class="tab-item"
      :class="{ active: $route.name === tab.key }"
      @click="$router.push({ name: tab.key })">
      <span class="tab-icon" v-html="tab.icon($route.name === tab.key)" />
      <span class="tab-label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const svgHome = (active: boolean) => `<svg width="24" height="24" viewBox="0 0 24 24" fill="${active ? '#2D6A4F' : 'none'}" stroke="${active ? '#2D6A4F' : '#94A3B8'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`
const svgChat = (active: boolean) => `<svg width="24" height="24" viewBox="0 0 24 24" fill="${active ? '#2D6A4F' : 'none'}" stroke="${active ? '#2D6A4F' : '#94A3B8'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`
const svgRoute = (active: boolean) => `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${active ? '#2D6A4F' : '#94A3B8'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>`
const svgProfile = (active: boolean) => `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${active ? '#2D6A4F' : '#94A3B8'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`

const tabs = computed(() => [
  { key: 'home', label: t('tab.home'), icon: svgHome },
  { key: 'chat', label: t('tab.chat'), icon: svgChat },
  { key: 'route', label: t('tab.route'), icon: svgRoute },
  { key: 'profile', label: t('tab.profile'), icon: svgProfile },
])
</script>

<style scoped>
.tab-bar {
  position: fixed; bottom: 0; left: 0; right: 0;
  background: rgba(255,255,255,0.95); backdrop-filter: blur(24px);
  border-top: 1px solid rgba(0,0,0,0.06); z-index: 1001;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  box-shadow: 0 -2px 20px rgba(0,0,0,0.06);
  display: flex; justify-content: space-around; height: 56px; max-width: 100vw;
}
.tab-item {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; flex: 1; height: 100%; border: none; background: none; cursor: pointer; transition: all 0.2s;
}
.tab-item:active { transform: scale(0.9); }
.tab-icon { transition: transform 0.2s; display: flex; }
.tab-item.active .tab-icon { transform: scale(1.1); }
.tab-label { font-size: 10px; font-weight: 600; transition: color 0.2s; color: var(--color-text-muted); }
.tab-item.active .tab-label { color: var(--color-primary); }
</style>
