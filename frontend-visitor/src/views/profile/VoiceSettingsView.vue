<template>
  <div class="sub-page">
    <header class="sub-header"><button @click="router.back()">‹</button><h1>{{ t('voice.title') }}</h1><span /></header>
    <main>
      <section><p>{{ t('voice.type') }}</p><div class="options voices"><button v-for="voice in voiceOptions" :key="voice.key" :class="{active:settings.voiceKey===voice.key}" @click="settings.voiceKey=voice.key">{{ t(voice.labelKey) }}</button></div></section>
      <section><p>{{ t('voice.rate') }}</p><div class="options"><button v-for="rate in rateOptions" :key="rate.value" :class="{active:settings.rate===rate.value}" @click="settings.rate=rate.value">{{ t(rate.labelKey) }}</button></div></section>
      <section><p>{{ t('voice.volume') }}</p><div class="range"><input v-model="volumePercent" type="range" min="0" max="100" /><strong>{{ volumePercent }}%</strong></div></section>
      <small>{{ t('voice.savedHint') }}</small>
    </main>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useVoiceSettings } from '../../composables/useVoiceSettings'
const router=useRouter();const {t}=useI18n();const {settings,volumePercent,voiceOptions,rateOptions}=useVoiceSettings()
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95)}.sub-header button,.sub-header span{width:36px}.sub-header button{border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:20px 16px}section{margin-bottom:26px}section>p{margin-bottom:12px;color:var(--color-text-secondary);font-size:.8125rem;font-weight:600}.options{display:flex;gap:8px}.options.voices{display:grid;grid-template-columns:1fr 1fr}.options button{flex:1;padding:11px 8px;border:1px solid rgba(0,0,0,.08);border-radius:10px;background:#fff;color:var(--color-text-secondary);cursor:pointer}.options button.active{background:var(--color-primary-bg);color:var(--color-primary);border-color:var(--color-primary-border);font-weight:600}.range{display:flex;align-items:center;gap:12px}.range input{flex:1}.range strong{min-width:42px;font-size:.875rem}small{display:block;padding:12px;border-radius:10px;background:var(--color-primary-bg);color:var(--color-text-muted);line-height:1.6}
</style>
