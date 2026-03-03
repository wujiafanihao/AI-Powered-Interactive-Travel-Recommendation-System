<template>
  <!-- 注册页面容器 -->
  <div class="login-container">
    <!-- 注册卡片 -->
    <el-card class="box-card">
      <!-- 卡片头部 -->
      <template #header>
        <div class="card-header">
          <span>TravelAI - 账号注册</span>
        </div>
      </template>
      <!-- 注册表单，ref 用于表单验证，:model 绑定表单数据，:rules 绑定验证规则 -->
      <el-form ref="registerFormRef" :model="registerForm" :rules="rules" label-width="80px">
        <!-- 用户名输入框 -->
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <!-- 密码输入框，type="password" 隐藏输入内容 -->
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <!-- 昵称输入框 -->
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="registerForm.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <!-- 年龄输入框，使用数字输入组件 -->
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="registerForm.age" :min="1" :max="120" />
        </el-form-item>
        <!-- 性别单选框组 -->
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="registerForm.gender">
            <el-radio label="男">男</el-radio>
            <el-radio label="女">女</el-radio>
            <el-radio label="未知">保密</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 旅行偏好输入框，用逗号分隔 -->
        <el-form-item label="旅行偏好">
          <el-input v-model="registerForm.travel_style" placeholder="如：自然风光,历史文化,美食" />
        </el-form-item>
        <!-- 注册按钮，:loading 显示加载状态 -->
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleRegister" style="width: 100%">
            注册
          </el-button>
        </el-form-item>
      </el-form>
      <!-- 登录链接，跳转到登录页面 -->
      <div class="login-link">
        已有账号？<el-link type="primary" @click="$router.push('/login')">立即登录</el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的响应式函数
import { reactive, ref } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入 API 请求实例
import api from '../api/request'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'

// 获取路由实例
const router = useRouter()

// 表单引用，用于调用表单验证方法
const registerFormRef = ref()
// 注册表单数据，使用 reactive 定义响应式对象
const registerForm = reactive({
  username: '',
  password: '',
  nickname: '',
  age: 25,
  gender: '未知',
  travel_style: ''
})

// 表单验证规则
const rules = reactive({
  // 用户名必填验证
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  // 密码必填验证
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
})

// 注册按钮的加载状态
const loading = ref(false)

// 处理注册的函数
const handleRegister = async () => {
  // 确保表单引用存在
  if (!registerFormRef.value) return
  // 调用表单验证方法
  await registerFormRef.value.validate(async (valid: boolean) => {
    // 如果验证通过
    if (valid) {
      // 显示加载状态
      loading.value = true
      try {
        // 处理旅行偏好数据，将逗号分隔的字符串转换为数组
        const data = {
          ...registerForm,
          travel_style: registerForm.travel_style ? registerForm.travel_style.split(',').map((s: string) => s.trim()).filter((s: string) => s) : []
        }
        // 调用注册 API
        await api.post('/auth/register', data)
        // 显示注册成功消息
        ElMessage.success('注册成功，请登录')
        // 跳转到登录页面
        router.push('/login')
      } catch (error: any) {
        // 处理错误，显示错误消息
        const msg = error.response?.data?.detail || '注册失败'
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
/* 注册页面容器样式：垂直水平居中，全屏高度，渐变背景动画 */
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

/* 注册卡片宽度 */
.box-card {
  width: 500px;
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
/* 登录链接样式：居中，上边距，字体大小 */
.login-link {
  text-align: center;
  margin-top: 15px;
  font-size: 14px;
}
</style>
