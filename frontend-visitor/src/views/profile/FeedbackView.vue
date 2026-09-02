<template>
  <div class="sub-page">
    <header class="sub-header"><button @click="router.back()">‹</button><h1>{{ t('feedback.title') }}</h1><span /></header>
    <main>
      <select v-model="category" :aria-label="t('feedback.category')">
        <option value="suggestion">{{ t('feedback.categories.suggestion') }}</option>
        <option value="complaint">{{ t('feedback.categories.complaint') }}</option>
        <option value="consultation">{{ t('feedback.categories.consultation') }}</option>
        <option value="praise">{{ t('feedback.categories.praise') }}</option>
        <option value="other">{{ t('feedback.categories.other') }}</option>
      </select>
      <textarea v-model="content" :placeholder="t('feedback.placeholder')" rows="7" />
      <button class="submit" :disabled="submitting" @click="submit">{{ t('feedback.submit') }}</button>
      <h2>{{ t('feedback.history') }}</h2>
      <div v-if="loading" class="state">{{ t('common.loading') }}</div>
      <div v-else-if="history.length===0" class="state">{{ t('feedback.empty') }}</div>
      <article v-for="item in history" v-else :key="item.id" class="card feedback-card">
        <div><span>{{ item.status === 'resolved' || item.admin_reply ? t('feedback.replied') : t('feedback.pending') }}</span><time>{{ formatDate(item.created_at) }}</time></div>
        <p>{{ item.content }}</p><small v-if="item.admin_reply">{{ t('feedback.reply', { reply:item.admin_reply }) }}</small>
      </article>
    </main>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getFeedbackHistory, submitFeedback, type FeedbackRecord } from '../../services/profile'
const router=useRouter();const {t,locale}=useI18n();const category=ref('suggestion');const content=ref('');const history=ref<FeedbackRecord[]>([]);const loading=ref(true);const submitting=ref(false)
function formatDate(v?:string){if(!v)return '';const d=new Date(v);return Number.isNaN(d.getTime())?v:new Intl.DateTimeFormat(locale.value,{dateStyle:'medium'}).format(d)}
async function load(){try{history.value=await getFeedbackHistory()}catch(error:any){ElMessage.error(error.response?.data?.detail||t('feedback.loadFailed'))}finally{loading.value=false}}
async function submit(){if(!content.value.trim())return ElMessage.warning(t('feedback.required'));submitting.value=true;try{const item=await submitFeedback(content.value.trim(),category.value);history.value=[item,...history.value];content.value='';ElMessage.success(t('feedback.success'))}catch(error:any){ElMessage.error(error.response?.data?.detail||t('common.operationFailed'))}finally{submitting.value=false}}
onMounted(load)
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95);position:sticky;top:0}.sub-header button,.sub-header span{width:36px}.sub-header button{border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:20px 16px;display:flex;flex-direction:column;gap:12px}select,textarea{width:100%;padding:14px;border:1px solid rgba(0,0,0,.08);border-radius:12px;background:#fff;font:inherit;outline:none}select{appearance:auto}textarea{resize:vertical}select:focus,textarea:focus{border-color:var(--color-primary)}.submit{padding:14px;border:0;border-radius:12px;background:var(--color-primary);color:#fff;font-weight:600;cursor:pointer}.submit:disabled{opacity:.5}h2{margin-top:14px;font-size:.9375rem}.state{text-align:center;padding:20px;color:var(--color-text-muted);font-size:.8125rem}.feedback-card{padding:14px}.feedback-card>div{display:flex;justify-content:space-between;font-size:11px;color:var(--color-primary)}.feedback-card time{color:var(--color-text-muted)}.feedback-card p{margin-top:10px;font-size:.8125rem;line-height:1.6}.feedback-card small{display:block;margin-top:10px;padding:8px;border-radius:8px;background:var(--color-primary-bg);color:var(--color-text-secondary)}
</style>
