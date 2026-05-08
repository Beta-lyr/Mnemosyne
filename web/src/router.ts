import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('./views/Login.vue') },
    { path: '/', component: () => import('./views/Dashboard.vue'), meta: { requiresAuth: true } },
    { path: '/characters', component: () => import('./views/Characters.vue'), meta: { requiresAuth: true } },
    { path: '/characters/:id', component: () => import('./views/CharacterDetail.vue'), meta: { requiresAuth: true } },
    { path: '/chat/:id', component: () => import('./views/Chat.vue'), meta: { requiresAuth: true } },
    { path: '/memories/:id', component: () => import('./views/Memories.vue'), meta: { requiresAuth: true } },
    { path: '/analytics/:id', component: () => import('./views/Analytics.vue'), meta: { requiresAuth: true } },
    { path: '/settings', component: () => import('./views/Settings.vue'), meta: { requiresAuth: true } },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/login'
  }
  if (to.path === '/login' && auth.isLoggedIn) {
    return '/'
  }
})

export default router
