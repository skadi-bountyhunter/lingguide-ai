<template>
  <div class="sub-page">
    <header class="sub-header"><button @click="router.back()">‹</button><h1>{{ t('language.title') }}</h1><span /></header>
    <main><button v-for="item in languages" :key="item.code" :class="{active:locale===item.code}" @click="change(item.code)"><span>{{ t(item.key) }}</span><small>{{ item.native }}</small></button></main>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { setLocale, type AppLocale } from '../../i18n'
const router=useRouter();const {t,locale:localeRef}=useI18n();const locale=localeRef;const languages=[{code:'zh-CN' as AppLocale,key:'language.zhCN',native:'简体中文'},{code:'en' as AppLocale,key:'language.en',native:'English'},{code:'ja' as AppLocale,key:'language.ja',native:'日本語'},{code:'ko' as AppLocale,key:'language.ko',native:'한국어'}]
function change(code:AppLocale){setLocale(code);ElMessage.success(t('language.changed'))}
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95)}.sub-header button,.sub-header>span{width:36px}.sub-header button{border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:20px 16px;display:flex;flex-direction:column;gap:8px}main button{display:flex;justify-content:space-between;padding:16px;border:1px solid rgba(0,0,0,.06);border-radius:12px;background:#fff;text-align:left;cursor:pointer}main button.active{background:var(--color-primary-bg);border-color:var(--color-primary-border)}main button span{font-weight:600;color:var(--color-text-primary)}main button small{color:var(--color-text-muted)}
</style>
