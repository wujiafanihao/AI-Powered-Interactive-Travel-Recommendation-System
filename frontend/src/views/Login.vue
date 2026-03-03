<template>
  <!-- 登录页面容器 -->
  <div class="login-container">
    <!-- 登录卡片 -->
    <el-card class="box-card">
      <!-- 卡片头部 -->
      <template #header>
        <div class="card-header">
          <span>TravelAI 智能旅游推荐系统</span>
        </div>
      </template>
      <!-- 登录表单，ref 用于表单验证，:model 绑定表单数据，:rules 绑定验证规则 -->
      <el-form ref="loginFormRef" :model="loginForm" :rules="rules" label-width="80px">
        <!-- 用户名输入框 -->
        <el-form-item label="用户名" prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <!-- 密码输入框，type="password" 隐藏输入内容，@keyup.enter 绑定回车键登录 -->
        <el-form-item label="密码" prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" @keyup.enter="handleLogin" />
        </el-form-item>
        <!-- 登录按钮，:loading 显示加载状态 -->
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <!-- 注册链接，跳转到注册页面 -->
      <div class="register-link">
        还没有账号？<el-link type="primary" @click="$router.push('/register')">立即注册</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的响应式函数
import { reactive, ref } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入用户状态管理
import { useUserStore } from '../store/user'
// 引入 API 请求实例
import api from '../api/request'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'

// 获取路由实例
const router = useRouter()
// 获取用户状态管理实例
const userStore = useUserStore()

// 表单引用，用于调用表单验证方法
const loginFormRef = ref()
// 登录表单数据，使用 reactive 定义响应式对象
const loginForm = reactive({
  username: '',
  password: ''
})

// 表单验证规则
const rules = reactive({
  // 用户名必填验证
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  // 密码必填验证
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
})

// 登录按钮的加载状态
const loading = ref(false)

// 处理登录的函数
const handleLogin = async () => {
  // 确保表单引用存在
  if (!loginFormRef.value) return
  // 调用表单验证方法
  await loginFormRef.value.validate(async (valid: boolean) => {
    // 如果验证通过
    if (valid) {
      // 显示加载状态
      loading.value = true
      try {
        // 调用登录 API
        const res = await api.post('/auth/login', {
          username: loginForm.username,
          password: loginForm.password
        })

        // 保存 token 到用户状态管理
        userStore.setToken(res.data.access_token)

        // 请求后台获取用户信息接口
        const userRes = await api.get('/auth/me')
        // 保存用户信息到用户状态管理
        userStore.setUserInfo(userRes.data)

        // 显示登录成功消息
        ElMessage.success('登录成功')
        // 跳转到首页
        router.push('/')
      } catch (error: any) {
        // 处理错误，显示错误消息
        const msg = error.response?.data?.detail || '登录失败'
        ElMessage.error(msg)
      } finally {
        // 无论成功或失败，都关闭加载状态
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
/* 登录页面容器样式：垂直水平居中，全屏高度，渐变背景动画 */
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  background-size: 400% 400%;
  animation: gradientAnimation 8s ease infinite;
}

@keyframes gradientAnimation {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

/* 登录卡片宽度 */
.box-card {
  width: 400px;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
/* 卡片头部样式：居中，加粗字体 */
.card-header {
  text-align: center;
  font-size: 18px;
  font-weight: bold;
}
/* 注册链接样式：居中，上边距，字体大小 */
.register-link {
  text-align: center;
  margin-top: 15px;
  font-size: 14px;
}
</style>
