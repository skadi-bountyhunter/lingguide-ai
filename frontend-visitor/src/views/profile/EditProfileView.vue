<template>
  <div class="sub-page">
    <header class="sub-header">
      <button class="back-btn" @click="router.back()">‹</button>
      <h1>{{ t('profile.editName') }}</h1>
      <div class="header-spacer" />
    </header>
    <div class="sub-content card">
      <label for="nickname">{{ t('profile.nickname') }}</label>
      <input id="nickname" v-model="nickname" maxlength="30" :placeholder="t('profile.nicknamePlaceholder')" />
      <button class="submit-btn" :disabled="saving || !nickname.trim()" @click="save">{{ t('profile.save') }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getMyProfile, updateMyProfile } from '../../services/profile'

const router = useRouter()
const { t } = useI18n()
const nickname = ref('')
const saving = ref(false)

onMounted(async () => {
  try { nickname.value = (await getMyProfile()).nickname || '' } catch {}
})

async function save() {
  if (!nickname.value.trim() || saving.value) return
  saving.value = true
  try {
    const profile = await updateMyProfile({ nickname: nickname.value.trim() })
    localStorage.setItem('lingguide_user', JSON.stringify(profile))
    ElMessage.success(t('profile.saved'))
    router.back()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || t('profile.saveFailed'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.sub-page { max-width: 672px; margin: 0 auto; min-height: 100vh; }
.sub-header { display: flex; align-items: center; padding: 12px 16px; background: rgba(255,255,255,.95); position: sticky; top: 0; z-index: 10; }
.back-btn, .header-spacer { width: 36px; }
.back-btn { height: 36px; border: 0; border-radius: 50%; background: none; font-size: 1.6rem; cursor: pointer; }
.sub-header h1 { flex: 1; text-align: center; font-size: 1.125rem; }
.sub-content { margin: 20px 16px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
label { font-size: .8125rem; font-weight: 600; color: var(--color-text-secondary); }
input { width: 100%; padding: 13px 14px; border: 1px solid rgba(0,0,0,.08); border-radius: 12px; background: var(--color-bg-input); font: inherit; outline: none; }
input:focus { border-color: var(--color-primary); }
.submit-btn { margin-top: 8px; padding: 13px; border: 0; border-radius: 12px; color: #fff; background: var(--color-primary); font-weight: 600; cursor: pointer; }
.submit-btn:disabled { opacity: .45; cursor: not-allowed; }
</style>
