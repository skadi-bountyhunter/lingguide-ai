<template>
  <div class="sub-page">
    <header><button @click="router.back()">‹</button><h1>{{ t('about.title') }}</h1><span /></header>
    <main><div class="logo"><img src="/images/logo.png" alt="logo" class="logo-img" /><h2>{{ t('auth.brand') }}</h2><p>{{ t('about.subtitle') }}</p><small>v1.0.0</small></div>
      <section><h3>{{ t('about.product') }}</h3><p>{{ t('about.intro') }}</p></section>
      <section><h3>{{ t('about.features') }}</h3><ul><li v-for="i in 5" :key="i">{{ t(`about.f${i}`) }}</li></ul></section>
      <section><h3>{{ t('about.demo') }}</h3><p>{{ t('about.demoText') }}</p></section>
      <section><h3>{{ t('about.contact') }}</h3><p>{{ t('about.email') }}</p></section>
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
.sub-page{max-width:672px;margin:auto;min-height:100vh}header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95)}header button,header span{width:36px}header button{border:0;background:none;font-size:1.6rem;cursor:pointer}header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:20px 16px}.logo{text-align:center;padding:20px 0 32px}.logo-img{display:block;width:80px;height:80px;border-radius:20px;object-fit:contain;margin:0 auto}.logo h2{margin-top:8px;font-size:1.25rem}.logo p,.logo small{color:var(--color-text-muted);font-size:.75rem}section{margin-bottom:20px}section h3{margin-bottom:6px;font-size:.9375rem}section p,li{color:var(--color-text-secondary);font-size:.8125rem;line-height:1.8}ul{padding-left:20px}
</style>
