import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('./views/DashboardView.vue'),
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('./views/KnowledgeView.vue'),
    },
    {
      path: '/rag-diagnostics',
      name: 'rag-diagnostics',
      component: () => import('./views/RagDiagnosticsView.vue'),
    },
    {
      path: '/spots',
      name: 'spots',
      component: () => import('./views/SpotsView.vue'),
    },
    {
      path: '/routes',
      name: 'routes',
      component: () => import('./views/RoutesView.vue'),
    },
    {
      path: '/avatar',
      name: 'avatar',
      component: () => import('./views/AvatarView.vue'),
    },
    {
      path: '/report',
      name: 'report',
      component: () => import('./views/ReportView.vue'),
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('./views/UsersView.vue'),
    },
    {
      path: '/feedback',
      name: 'feedback',
      component: () => import('./views/FeedbackView.vue'),
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('./views/NotificationsView.vue'),
    },
  ],
})

export default router
