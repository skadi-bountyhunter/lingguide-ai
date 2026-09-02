<template>
  <div class="sub-page">
    <header class="sub-header"><button @click="router.back()">‹</button><h1>{{ t('visits.title') }}</h1><span /></header>
    <main>
      <div v-if="loading" class="state">{{ t('common.loading') }}</div>
      <div v-else-if="visits.length===0" class="state"><b>🚶</b><p>{{ t('visits.empty') }}</p><small>{{ t('visits.hint') }}</small></div>
      <article v-for="visit in visits" v-else :key="visit.id" class="card visit" @click="open(visit)">
        <img :src="visit.item_cover || '/images/lingshan_3.jpeg'" :alt="visit.item_name" />
        <div><h2>{{ visit.item_name }}</h2><p>{{ t('visits.visitedAt', { time: formatDate(visit.last_visited_at || visit.first_visited_at) }) }}</p><small v-if="visit.visit_count">{{ visit.visit_count }}×</small></div>
      </article>
    </main>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getVisits, type VisitRecord } from '../../services/profile'
const router=useRouter(); const {t,locale}=useI18n(); const visits=ref<VisitRecord[]>([]); const loading=ref(true)
function formatDate(value?:string){if(!value)return '—';const d=new Date(value);return Number.isNaN(d.getTime())?value:new Intl.DateTimeFormat(locale.value,{dateStyle:'medium',timeStyle:'short'}).format(d)}
function open(visit:VisitRecord){if(visit.item_type==='spot')router.push({name:'spot',params:{name:visit.item_id}});else router.push({name:'route'})}
onMounted(async()=>{try{visits.value=await getVisits()}catch(error:any){ElMessage.error(error.response?.data?.detail||t('visits.loadFailed'))}finally{loading.value=false}})
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95);position:sticky;top:0;z-index:10}.sub-header button,.sub-header span{width:36px}.sub-header button{border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}main{padding:16px;display:flex;flex-direction:column;gap:12px}.state{text-align:center;padding:48px 0;color:var(--color-text-secondary)}.state b{display:block;font-size:3rem;margin-bottom:10px}.state small{color:var(--color-text-muted)}.visit{display:flex;overflow:hidden;cursor:pointer}.visit img{width:100px;height:80px;object-fit:cover}.visit div{padding:14px}.visit h2{font-size:.875rem}.visit p{margin-top:8px;font-size:.75rem;color:var(--color-text-muted)}
</style>
