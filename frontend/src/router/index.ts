// 引入 Vue Router 的核心函数
import { createRouter, createWebHistory } from 'vue-router'

// 创建路由实例
const router = createRouter({
  // 使用 HTML5 History 模式（URL 看起来更干净，没有 # 号）
  history: createWebHistory(import.meta.env.BASE_URL),
  // 路由配置：每个路由对应一个页面
  routes: [
    {
      // 首页路径
      path: '/',
      name: 'home',
      // 懒加载首页组件，只有访问时才加载，提高性能
      component: () => import('../views/Home.vue')
    },
    {
      // 登录页路径
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue')
    },
    {
      // 注册页路径
      path: '/register',
      name: 'register',
      component: () => import('../views/Register.vue')
    },
    {
      // 景点列表页路径
      path: '/spots',
      name: 'spot-list',
      component: () => import('../views/Spot/SpotList.vue')
    },
    {
      // 景点详情页路径，:id 是动态参数，会根据不同景点显示不同内容
      path: '/spot/:id',
      name: 'spot-detail',
      component: () => import('../views/Spot/SpotDetail.vue')
    },
    {
      // AI 聊天页路径
      path: '/ai',
      name: 'ai-chat',
      component: () => import('../views/AI/Chat.vue')
    },
    {
      // 我的收藏页路径
      path: '/collections',
      name: 'collections',
      component: () => import('../views/Collections.vue')
    }
  ]
})

// 导出路由，给 main.ts 用
export default router
