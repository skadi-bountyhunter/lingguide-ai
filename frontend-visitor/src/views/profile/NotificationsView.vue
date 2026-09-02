<template>
  <div class="sub-page">
    <header class="sub-header"><button @click="router.back()">‹</button><h1>{{ t('notifications.title') }}</h1><span /></header>
    <div class="socket-state" :class="{ connected }">{{ connected ? t('notifications.connected') : t('notifications.disconnected') }}</div>
    <main>
      <div v-if="loading" class="state">{{ t('common.loading') }}</div>
      <div v-else-if="notifications.length===0" class="state"><b>🔔</b><p>{{ t('notifications.empty') }}</p><small>{{ t('notifications.hint') }}</small></div>
      <article v-for="item in notifications" v-else :key="item.id" class="card notification" :class="{ unread: !isRead(item) }">
        <div class="notification-head"><h2>{{ item.title }}</h2><time>{{ formatDate(item.created_at) }}</time></div>
        <p>{{ item.content }}</p><button v-if="!isRead(item)" @click="read(item)">{{ t('notifications.markRead') }}</button>
      </article>
    </main>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getNotifications, markNotificationRead, type NotificationRecord } from '../../services/profile'
import { useNotificationSocket } from '../../composables/useNotificationSocket'
const router=useRouter();const {t,locale}=useI18n();const notifications=ref<NotificationRecord[]>([]);const loading=ref(true)
const {connected,connect}=useNotificationSocket({onNotification(item){notifications.value=[item,...notifications.value.filter(existing=>existing.id!==item.id)]}})
const isRead=(item:NotificationRecord)=>Boolean(item.is_read??item.read)
function formatDate(v?:string){if(!v)return '';const d=new Date(v);return Number.isNaN(d.getTime())?v:new Intl.DateTimeFormat(locale.value,{dateStyle:'medium',timeStyle:'short'}).format(d)}
async function read(item:NotificationRecord){try{await markNotificationRead(item.id);item.read=true;item.is_read=true}catch(error:any){ElMessage.error(error.response?.data?.detail||t('common.operationFailed'))}}
onMounted(async()=>{try{notifications.value=await getNotifications()}catch(error:any){ElMessage.error(error.response?.data?.detail||t('notifications.loadFailed'))}finally{loading.value=false}connect()})
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95);position:sticky;top:0;z-index:10}.sub-header button,.sub-header span{width:36px}.sub-header button{border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}.socket-state{padding:5px;text-align:center;background:rgba(212,146,58,.1);color:var(--color-warning);font-size:10px}.socket-state.connected{background:var(--color-primary-bg);color:var(--color-success)}main{padding:16px;display:flex;flex-direction:column;gap:12px}.state{text-align:center;padding:48px 0;color:var(--color-text-secondary)}.state b{display:block;font-size:3rem;margin-bottom:10px}.state small{color:var(--color-text-muted)}.notification{padding:16px;border-left:3px solid transparent}.notification.unread{border-left-color:var(--color-accent);background:linear-gradient(90deg,var(--color-accent-bg),#fff 28%)}.notification-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.notification h2{font-size:.875rem}.notification time{font-size:10px;color:var(--color-text-muted);white-space:nowrap}.notification p{margin-top:8px;color:var(--color-text-secondary);font-size:.8125rem;line-height:1.6}.notification button{margin-top:10px;border:0;background:none;color:var(--color-primary);font-size:.75rem;font-weight:600;cursor:pointer}
</style>
