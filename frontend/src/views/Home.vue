<template>
  <div class="home-container">
    <el-container>
      <el-header>
        <div class="logo">TravelAI 智能旅游推荐系统</div>
        <div class="user-info" v-if="userStore.token">
          <el-dropdown>
            <span class="el-dropdown-link">
              {{ userStore.userInfo.username || '用户' }}
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="user-info" v-else>
          <el-button type="primary" @click="$router.push('/login')">登录</el-button>
        </div>
      </el-header>
      <el-main>
        <h1>欢迎来到 TravelAI 智能旅游推荐系统</h1>
        <p>为你提供最智能的个性化旅游推荐</p>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '../store/user'
import { useRouter } from 'vue-router'

const userStore = useUserStore()
const router = useRouter()

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.home-container {
  height: 100vh;
}
.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
}
.logo {
  font-size: 20px;
  font-weight: bold;
  color: #409EFF;
}
.el-main {
  text-align: center;
  padding-top: 50px;
}
.el-dropdown-link {
  cursor: pointer;
  color: #409EFF;
  display: flex;
  align-items: center;
}
</style>