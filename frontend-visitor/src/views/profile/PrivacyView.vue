<template>
  <div class="sub-page">
    <header><button @click="router.back()">‹</button><h1>{{ t('privacy.title') }}</h1><span /></header>
    <main><h2>{{ t('privacy.policy') }}</h2><p class="date">{{ t('privacy.updated') }}</p>
      <section><h3>{{ t('privacy.collectTitle') }}</h3><p>{{ t('privacy.collectIntro') }}</p><ul><li>{{ t('privacy.collect1') }}</li><li>{{ t('privacy.collect2') }}</li><li>{{ t('privacy.collect3') }}</li></ul></section>
      <section><h3>{{ t('privacy.useTitle') }}</h3><p>{{ t('privacy.useIntro') }}</p><ul><li>{{ t('privacy.use1') }}</li><li>{{ t('privacy.use2') }}</li><li>{{ t('privacy.use3') }}</li></ul></section>
      <section><h3>{{ t('privacy.protectTitle') }}</h3><p>{{ t('privacy.protect') }}</p></section>
      <section><h3>{{ t('privacy.contactTitle') }}</h3><p>{{ t('privacy.contact') }}</p></section>
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
.sub-page{max-width:672px;margin:auto;min-height:100vh}header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95);position:sticky;top:0}header button,header span{width:36px}header button{border:0;background:none;font-size:1.6rem;cursor:pointer}header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:20px 16px}main h2{font-size:1.125rem}.date{margin:4px 0 24px;color:var(--color-text-muted);font-size:.75rem}section{margin-bottom:24px}section h3{margin-bottom:8px;font-size:.9375rem}section p,li{color:var(--color-text-secondary);font-size:.8125rem;line-height:1.7}ul{padding-left:20px}
</style>
