import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/auth',
      name: 'auth',
      component: () => import('./views/AuthView.vue'),
    },
    {
      path: '/',
      name: 'home',
      component: () => import('./views/HomeView.vue'),
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('./views/ChatView.vue'),
    },
    {
      path: '/route',
      name: 'route',
      component: () => import('./views/RouteView.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('./views/ProfileView.vue'),
    },
    {
      path: '/spot/:name',
      name: 'spot',
      component: () => import('./views/SpotDetailView.vue'),
    },
    {
      path: '/videos',
      name: 'videos',
      component: () => import('./views/VideoView.vue'),
    },
    // 个人中心子页面
    {
      path: '/profile/edit',
      name: 'profile-edit',
      component: () => import('./views/profile/EditProfileView.vue'),
    },
    {
      path: '/profile/visits',
      name: 'profile-visits',
      component: () => import('./views/profile/VisitRecordsView.vue'),
    },
    {
      path: '/profile/favorites',
      name: 'profile-favorites',
      component: () => import('./views/profile/FavoritesView.vue'),
    },
    {
      path: '/profile/notifications',
      name: 'profile-notifications',
      component: () => import('./views/profile/NotificationsView.vue'),
    },
    {
      path: '/profile/voice',
      name: 'profile-voice',
      component: () => import('./views/profile/VoiceSettingsView.vue'),
    },
    {
      path: '/profile/language',
      name: 'profile-language',
      component: () => import('./views/profile/LanguageView.vue'),
    },
    {
      path: '/profile/feedback',
      name: 'profile-feedback',
      component: () => import('./views/profile/FeedbackView.vue'),
    },
    {
      path: '/profile/privacy',
      name: 'profile-privacy',
      component: () => import('./views/profile/PrivacyView.vue'),
    },
    {
      path: '/profile/about',
      name: 'profile-about',
      component: () => import('./views/profile/AboutView.vue'),
    },
    {
      path: '/tickets',
      name: 'ticket-prices',
      component: () => import('./views/TicketPricesView.vue'),
    },
    {
      path: '/vegetarian-dining',
      name: 'vegetarian-dining',
      component: () => import('./views/VegetarianDiningView.vue'),
    },
  ],
})

// 路由守卫：未登录用户跳转登录页。
router.beforeEach((to) => {
  const token = localStorage.getItem('lingguide_token')
  if (!token && to.name !== 'auth') {
    return { name: 'auth' }
  }
})

export default router
