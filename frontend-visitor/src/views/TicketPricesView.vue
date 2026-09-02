<template>
  <div class="quick-page">
    <header><button @click="router.back()">‹</button><h1>{{ t('tickets.title') }}</h1><span /></header>
    <main>
      <article v-for="item in items" :key="item.title" class="card ticket-card">
        <div><h2>{{ item.title }}</h2><p>{{ item.desc }}</p></div>
        <strong>{{ item.price }}</strong>
      </article>
      <p class="note">{{ t('tickets.note') }}</p>
      <button class="action" @click="ElMessage.info(t('tickets.buy'))">{{ t('tickets.buy') }}</button>
    </main>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
const router = useRouter()
const { t } = useI18n()
const items = computed(() => [
  { title: t('tickets.adult'), price: t('tickets.adultPrice'), desc: '' },
  { title: t('tickets.concession'), price: t('tickets.concessionPrice'), desc: '' },
  { title: t('tickets.free'), price: '—', desc: t('tickets.freeDesc') },
])
</script>
<style scoped>
.quick-page { max-width:672px; min-height:100vh; margin:auto; }
header { display:flex; align-items:center; padding:12px 16px; background:rgba(255,255,255,.95); position:sticky; top:0; }
header button, header span { width:36px; } header button { border:0; background:none; font-size:1.6rem; cursor:pointer; } header h1 { flex:1; text-align:center; font-size:1.125rem; }
main { padding:20px 16px; display:flex; flex-direction:column; gap:12px; }
.ticket-card { padding:18px; display:flex; align-items:center; justify-content:space-between; gap:16px; }
h2 { font-size:.9375rem; } p { margin-top:4px; color:var(--color-text-muted); font-size:.75rem; line-height:1.6; } strong { color:var(--color-accent); white-space:nowrap; }
.note { padding:4px; }.action { padding:13px; border:0; border-radius:12px; color:#fff; background:var(--color-primary); font-weight:600; cursor:pointer; }
</style>
