import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import i18n from '@/i18n'
import MainLayout from '@/layouts/MainLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, titleKey: 'login.title' },
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: { name: 'chat' } },
      {
        path: 'chat',
        name: 'chat',
        component: () => import('@/views/Chat.vue'),
        meta: { titleKey: 'nav.chat' },
      },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/Knowledge.vue'),
        meta: { titleKey: 'nav.knowledge' },
      },
      {
        path: 'models',
        name: 'models',
        component: () => import('@/views/Models.vue'),
        meta: { titleKey: 'nav.models' },
      },
      {
        path: 'api',
        name: 'api',
        component: () => import('@/views/Api.vue'),
        meta: { titleKey: 'nav.api' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('@/views/Settings.vue'),
        meta: { titleKey: 'nav.settings' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Global auth guard
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'chat' }
  }
  return true
})

// i18n document title
router.afterEach((to) => {
  const key = to.meta.titleKey
  document.title = key ? `${i18n.global.t(key)} · OLm-Mn-wed` : 'OLm-Mn-wed'
})

export default router
