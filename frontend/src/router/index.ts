import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/Home.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue')
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/Register.vue')
    },
    {
      path: '/spots',
      name: 'spot-list',
      component: () => import('../views/Spot/SpotList.vue')
    },
    {
      path: '/spot/:id',
      name: 'spot-detail',
      component: () => import('../views/Spot/SpotDetail.vue')
    },
    {
      path: '/ai',
      name: 'ai-chat',
      component: () => import('../views/AI/Chat.vue')
    },
    {
      path: '/collections',
      name: 'collections',
      component: () => import('../views/Collections.vue')
    }
  ]
})

export default router
