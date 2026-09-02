<template>
  <div class="quick-page">
    <header><button @click="router.back()">‹</button><h1>{{ t('vegetarian.title') }}</h1><span /></header>
    <main>
      <section class="card intro"><span>🍜</span><p>{{ t('vegetarian.intro') }}</p></section>
      <h2>{{ t('vegetarian.places') }}</h2>
      <article class="card place"><h3>{{ t('vegetarian.place1') }}</h3><p>{{ t('vegetarian.place1Desc') }}</p></article>
      <article class="card place"><h3>{{ t('vegetarian.place2') }}</h3><p>{{ t('vegetarian.place2Desc') }}</p></article>
      <p class="note">{{ t('vegetarian.note') }}</p>
    </main>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
const router = useRouter()
const { t } = useI18n()
</script>
<style scoped>
.quick-page { max-width:672px; min-height:100vh; margin:auto; } header { display:flex; align-items:center; padding:12px 16px; background:rgba(255,255,255,.95); position:sticky; top:0; }
header button, header span { width:36px; } header button { border:0; background:none; font-size:1.6rem; cursor:pointer; } header h1 { flex:1; text-align:center; font-size:1.125rem; }
main { padding:20px 16px; display:flex; flex-direction:column; gap:12px; } .intro { display:flex; align-items:center; gap:14px; padding:18px; } .intro span { font-size:2rem; }
h2 { margin-top:8px; font-size:.9375rem; }.place { padding:18px; }.place h3 { font-size:.9375rem; }.place p,.intro p,.note { margin-top:5px; color:var(--color-text-secondary); font-size:.8125rem; line-height:1.7; }.note { color:var(--color-text-muted); }
</style>
