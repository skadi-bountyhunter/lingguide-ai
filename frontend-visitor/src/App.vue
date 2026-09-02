<template>
  <el-config-provider :locale="elementLocale">
    <div id="lingguide-app">
      <router-view />
      <TabBar v-if="showTabBar" />
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import ja from 'element-plus/es/locale/lang/ja'
import ko from 'element-plus/es/locale/lang/ko'
import TabBar from './components/TabBar.vue'

const route = useRoute()
const { locale } = useI18n()
const elementLocales = { 'zh-CN': zhCn, en, ja, ko }
const elementLocale = computed(() => elementLocales[locale.value as keyof typeof elementLocales] || zhCn)
// 登录页和详情类页面不显示底部导航。
const hideTabBarRoutes = [
  'auth', 'spot', 'videos', 'profile-edit', 'profile-visits', 'profile-favorites',
  'profile-notifications', 'profile-voice', 'profile-language', 'profile-feedback', 'profile-privacy',
  'profile-about', 'ticket-prices', 'vegetarian-dining',
]
const showTabBar = computed(() => !hideTabBarRoutes.includes(route.name as string))
</script>

<style>
#lingguide-app {
  min-height: 100vh;
  background: var(--color-bg-page);
}
</style>
