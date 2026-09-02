<template>
  <div class="profile-page">
    <header class="profile-header"><h1>{{ t('profile.title') }}</h1></header>
    <div class="profile-content">
      <button class="card user-card" @click="router.push({ name: 'profile-edit' })">
        <div class="user-avatar"><span>🧑</span></div>
        <div class="user-info"><h2>{{ profile.nickname || t('profile.defaultName') }}</h2><p>{{ maskedPhone || t('profile.subtitle') }}</p><span>{{ t('profile.editName') }}</span></div>
        <el-icon class="arrow-icon"><ArrowRight /></el-icon>
      </button>

      <div class="stats-grid">
        <div v-for="s in stats" :key="s.label" class="card stat-card"><span class="stat-icon">{{ s.icon }}</span><p class="stat-val">{{ s.value }}</p><p class="stat-label">{{ s.label }}</p></div>
      </div>

      <div class="card quick-card">
        <div class="qc-title"><span>⚡</span><h3>{{ t('profile.quick') }}</h3></div>
        <div class="qc-grid">
          <button v-for="a in quickActions" :key="a.label" @click="a.action"><span>{{ a.icon }}</span><span class="qc-label">{{ a.label }}</span></button>
        </div>
      </div>

      <div class="card menu-card">
        <button v-for="item in menuItems" :key="item.label" @click="goTo(item.route, item.label)">
          <span class="menu-icon">{{ item.icon }}</span><div class="menu-info"><p>{{ item.label }}</p><span>{{ item.desc }}</span></div>
          <span v-if="item.badge" class="menu-badge">{{ item.badge }}</span><el-icon class="menu-arrow"><ArrowRight /></el-icon>
        </button>
      </div>

      <div class="card menu-card">
        <button v-for="item in settingsItems" :key="item.label" @click="goTo(item.route, item.label)">
          <span class="menu-icon">{{ item.icon }}</span><p class="menu-label">{{ item.label }}</p><el-icon class="menu-arrow"><ArrowRight /></el-icon>
        </button>
      </div>

      <button class="logout-btn" @click="handleLogout">{{ t('profile.logout') }}</button>
      <div class="version-info"><p>LINGGUIDE · v1.0.0</p><span>{{ t('profile.system') }}</span></div>
    </div>
    <div style="height:80px" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getMyProfile, getUnreadNotificationCount, type UserProfile } from '../services/profile'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const chatStore = useChatStore()
const { t } = useI18n()
const profile = ref<UserProfile>({})
const unreadCount = ref(0)

const maskedPhone = computed(() => profile.value.phone?.replace(/^(\d{3})\d{4}(\d+)$/, '$1****$2') || '')
const stats = computed(() => [
  { icon: '🚶', value: profile.value.stats?.visits ?? profile.value.stats?.visit_count ?? profile.value.visit_count ?? 0, label: t('profile.visitsStat') },
  { icon: '❤️', value: profile.value.stats?.favorites ?? profile.value.stats?.spot_favorite_count ?? profile.value.favorite_count ?? 0, label: t('profile.favoritesStat') },
  { icon: '🗺️', value: profile.value.stats?.routes ?? profile.value.stats?.saved_route_count ?? profile.value.route_count ?? 0, label: t('profile.routesStat') },
  { icon: '💬', value: profile.value.stats?.conversations ?? profile.value.stats?.interaction_count ?? profile.value.conversation_count ?? 0, label: t('profile.conversationsStat') },
])
const developing = (name: string) => ElMessage.info(t('profile.developing', { name }))
const quickActions = computed(() => [
  { icon: '🎫', label: t('profile.ticket'), action: () => router.push({ name: 'ticket-prices' }) },
  { icon: '🅿️', label: t('profile.parking'), action: () => developing(t('profile.parking')) },
  { icon: '🍜', label: t('profile.vegetarian'), action: () => router.push({ name: 'vegetarian-dining' }) },
  { icon: '📞', label: t('profile.emergency'), action: () => developing(t('profile.emergency')) },
])
const menuItems = computed(() => [
  { icon: '🕐', label: t('profile.visits'), desc: t('profile.visitsDesc'), badge: 0, route: 'profile-visits' },
  { icon: '❤️', label: t('profile.favorites'), desc: t('profile.favoritesDesc'), badge: 0, route: 'profile-favorites' },
  { icon: '🔔', label: t('profile.notifications'), desc: t('profile.notificationsDesc'), badge: unreadCount.value, route: 'profile-notifications' },
  { icon: '🎙️', label: t('profile.voice'), desc: t('profile.voiceDesc'), badge: 0, route: 'profile-voice' },
  { icon: '🌐', label: t('profile.language'), desc: t('profile.languageDesc'), badge: 0, route: 'profile-language' },
  { icon: '📱', label: t('profile.offline'), desc: t('profile.offlineDesc'), badge: 0, route: null },
])
const settingsItems = computed(() => [
  { icon: '🔒', label: t('profile.privacy'), route: 'profile-privacy' },
  { icon: 'ℹ️', label: t('profile.about'), route: 'profile-about' },
  { icon: '💬', label: t('profile.feedback'), route: 'profile-feedback' },
])

onMounted(async () => {
  const fallback = localStorage.getItem('lingguide_user')
  if (fallback) try { profile.value = JSON.parse(fallback) } catch {}
  const [profileResult, unreadResult] = await Promise.allSettled([getMyProfile(), getUnreadNotificationCount()])
  if (profileResult.status === 'fulfilled') {
    profile.value = profileResult.value
    localStorage.setItem('lingguide_user', JSON.stringify(profile.value))
  }
  if (unreadResult.status === 'fulfilled') unreadCount.value = unreadResult.value
})

function goTo(routeName: string | null, label: string) {
  if (!routeName) return developing(label)
  router.push({ name: routeName })
}
function handleLogout() {
  localStorage.removeItem('lingguide_token'); localStorage.removeItem('lingguide_user'); chatStore.newSession(); router.replace({ name: 'auth' })
}
</script>

<style scoped>
.profile-page { max-width:672px; margin:0 auto; min-height:100vh; }.profile-header { padding:12px 16px; background:rgba(255,255,255,.8); backdrop-filter:blur(12px); border-bottom:1px solid rgba(0,0,0,.04); text-align:center; position:sticky; top:0; z-index:10; }.profile-header h1 { font-size:1.125rem; }.profile-content { padding:20px 16px; display:flex; flex-direction:column; gap:20px; }
.user-card { width:100%; border:1px solid rgba(27,42,61,.05); padding:20px; display:flex; align-items:center; gap:16px; text-align:left; cursor:pointer; }.user-avatar { width:64px; height:64px; border-radius:16px; background:linear-gradient(to bottom right,var(--color-primary),var(--color-primary-light)); display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 4px 16px rgba(45,106,79,.25); }.user-avatar span { font-size:1.875rem; }.user-info { flex:1; min-width:0; }.user-info h2 { font-size:1.125rem; margin-bottom:3px; }.user-info p { color:var(--color-text-muted); font-size:.75rem; }.user-info>span { display:inline-block; margin-top:7px; color:var(--color-primary); font-size:10px; }.arrow-icon,.menu-arrow { color:var(--color-text-muted); }
.stats-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; }.stat-card { padding:16px; text-align:center; }.stat-icon { font-size:1.125rem; }.stat-val { font-size:1.25rem; font-weight:700; }.stat-label { margin-top:2px; font-size:11px; color:var(--color-text-muted); }
.quick-card { padding:16px; }.qc-title { display:flex; gap:8px; align-items:center; margin-bottom:12px; }.qc-title h3 { font-size:.875rem; }.qc-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }.qc-grid button { display:flex; flex-direction:column; align-items:center; gap:6px; padding:8px 0; border:0; border-radius:12px; background:none; cursor:pointer; }.qc-grid button:hover { background:var(--color-primary-bg); }.qc-grid button span:first-child { font-size:1.5rem; }.qc-label { font-size:11px; color:var(--color-text-secondary); }
.menu-card { overflow:hidden; }.menu-card button { width:100%; display:flex; align-items:center; gap:12px; padding:14px 16px; border:0; border-bottom:1px solid rgba(0,0,0,.03); background:none; text-align:left; cursor:pointer; }.menu-card button:last-child { border-bottom:0; }.menu-card button:hover { background:rgba(45,106,79,.03); }.menu-icon { width:28px; text-align:center; }.menu-info { flex:1; }.menu-info p,.menu-label { font-size:.875rem; color:var(--color-text-primary); }.menu-info span { font-size:11px; color:var(--color-text-muted); }.menu-label { flex:1; }.menu-badge { min-width:20px; height:20px; padding:0 5px; border-radius:10px; background:var(--color-accent); color:#fff; font-size:10px; display:flex; align-items:center; justify-content:center; }
.logout-btn { width:100%; padding:14px; border:1px solid rgba(196,84,74,.15); border-radius:12px; background:#fff; color:var(--color-error); font-weight:600; cursor:pointer; }.version-info { text-align:center; padding:16px 0; color:var(--color-text-muted); font-size:10px; }.version-info p { letter-spacing:.15em; }
</style>
