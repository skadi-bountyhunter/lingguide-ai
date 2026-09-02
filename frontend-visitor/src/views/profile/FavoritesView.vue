<template>
  <div class="sub-page">
    <header class="sub-header"><button class="back-btn" @click="router.back()">‹</button><h1>{{ t('favorites.title') }}</h1><div class="header-spacer" /></header>
    <div class="sub-content">
      <div v-if="loading" class="state">{{ t('common.loading') }}</div>
      <div v-else-if="favorites.length === 0" class="state"><span>❤️</span><p>{{ t('favorites.empty') }}</p><small>{{ t('favorites.hint') }}</small></div>
      <div v-else class="fav-list">
        <article v-for="fav in favorites" :key="fav.id" class="fav-card card" @click="openFavorite(fav)">
          <img :src="fav.item_cover || '/images/lingshan_3.jpeg'" :alt="fav.item_name" />
          <div><h3>{{ fav.item_name }}</h3><p>{{ fav.item_type === 'spot' ? t('common.spot') : t('common.route') }}</p></div>
          <button @click.stop="remove(fav.id)">×</button>
        </article>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { deleteFavorite, getFavorites, type FavoriteRecord } from '../../services/profile'
const router = useRouter(); const { t } = useI18n(); const favorites = ref<FavoriteRecord[]>([]); const loading = ref(true)
async function load() { loading.value=true; try { favorites.value=await getFavorites() } catch(error:any) { ElMessage.error(error.response?.data?.detail || t('favorites.loadFailed')) } finally { loading.value=false } }
async function remove(id:number) { try { await deleteFavorite(id); favorites.value=favorites.value.filter(item=>item.id!==id); ElMessage.success(t('favorite.removeSuccess')) } catch(error:any) { ElMessage.error(error.response?.data?.detail || t('common.operationFailed')) } }
function openFavorite(fav:FavoriteRecord) {
  if (fav.item_type === 'spot') router.push({ name: 'spot', params: { name: fav.item_id } })
  else if (fav.item_type === 'route') router.push({ name: 'route' })
  else ElMessage.info(t('favorites.routeUnavailable'))
}
onMounted(load)
</script>
<style scoped>
.sub-page{max-width:672px;margin:auto;min-height:100vh}.sub-header{display:flex;align-items:center;padding:12px 16px;background:rgba(255,255,255,.95);position:sticky;top:0;z-index:10}.back-btn,.header-spacer{width:36px}.back-btn{height:36px;border:0;background:none;font-size:1.6rem;cursor:pointer}.sub-header h1{flex:1;text-align:center;font-size:1.125rem}.sub-content{padding:16px}.state{text-align:center;padding:48px 0;color:var(--color-text-secondary)}.state span{display:block;font-size:3rem;margin-bottom:10px}.state small{color:var(--color-text-muted)}.fav-list{display:flex;flex-direction:column;gap:12px}.fav-card{display:flex;align-items:center;overflow:hidden;cursor:pointer}.fav-card img{width:100px;height:80px;object-fit:cover}.fav-card>div{flex:1;padding:12px}.fav-card h3{font-size:.875rem}.fav-card p{margin-top:4px;font-size:.75rem;color:var(--color-text-muted)}.fav-card button{width:42px;align-self:stretch;border:0;background:none;color:var(--color-error);font-size:1.25rem;cursor:pointer}
</style>
