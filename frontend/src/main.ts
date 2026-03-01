// 引入 Vue 的核心函数，用来创建应用实例
import { createApp } from 'vue'
// 引入根组件 App.vue
import App from './App.vue'
// 引入路由配置，用来管理页面跳转
import router from './router'
// 引入 Pinia，用来管理全局状态（比如用户信息）
import { createPinia } from 'pinia'

// 引入 Element Plus UI 组件库，让我们可以直接用现成的漂亮组件
import ElementPlus from 'element-plus'
// 引入 Element Plus 的样式文件
import 'element-plus/dist/index.css'
// 引入 Element Plus 的图标库
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// 引入全局样式
import './style.css'

// 创建 Vue 应用实例，把根组件 App 传进去
const app = createApp(App)

// 把所有 Element Plus 的图标都注册成全局组件，这样在任何页面都能直接用
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 安装 Pinia 状态管理
app.use(createPinia())
// 安装路由
app.use(router)
// 安装 Element Plus UI 组件库
app.use(ElementPlus)

// 把应用挂载到 index.html 里的 #app 元素上
app.mount('#app')