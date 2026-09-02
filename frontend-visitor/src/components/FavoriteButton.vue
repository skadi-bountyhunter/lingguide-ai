<template>
  <button class="favorite-btn" :class="{ active: isFav }" :disabled="loading" @click.stop="toggle">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
    <span v-if="showLabel">{{ isFav ? t('favorite.added') : t('favorite.add') }}</span>
  </button>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { checkFavorite, createFavorite, deleteFavorite } from '../services/profile'

const props = defineProps<{ itemId: string; itemName: string; itemCover?: string; showLabel?: boolean }>()
const emit = defineEmits<{ change: [isFav: boolean] }>()
const { t } = useI18n()
const isFav = ref(false)
const favoriteId = ref<number | null>(null)
const loading = ref(false)

async function checkStatus() {
  if (!props.itemId) return
  try {
    const data = await checkFavorite(props.itemId, 'spot')
    isFav.value = data.favorited
    favoriteId.value = data.id
  } catch {
    isFav.value = false; favoriteId.value = null
  }
}

async function toggle() {
  if (loading.value) return
  loading.value = true
  try {
    if (isFav.value && favoriteId.value != null) {
      await deleteFavorite(favoriteId.value)
      isFav.value = false; favoriteId.value = null
      ElMessage.success(t('favorite.removeSuccess'))
    } else {
      const favorite = await createFavorite({ item_type: 'spot', item_id: props.itemId, item_name: props.itemName, item_cover: props.itemCover || '' })
      isFav.value = true; favoriteId.value = favorite.id
      ElMessage.success(t('favorite.addSuccess'))
    }
    emit('change', isFav.value)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || t('common.operationFailed'))
  } finally { loading.value = false }
}

watch(() => props.itemId, checkStatus, { immediate: true })
</script>

<style scoped>
.favorite-btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:999px; border:1.5px solid var(--color-text-muted); background:transparent; color:var(--color-text-muted); cursor:pointer; transition:all .2s; font-size:.8125rem; font-weight:500; }.favorite-btn:hover { border-color:var(--color-error); color:var(--color-error); }.favorite-btn:active { transform:scale(.95); }.favorite-btn.active { border-color:var(--color-error); background:var(--color-error); color:#fff; }.favorite-btn:disabled { opacity:.5; cursor:not-allowed; }
</style>
