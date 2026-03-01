<template>
  <div class="home-container">
    <el-container>
      <!-- 头部导航 -->
      <el-header>
        <div class="logo">
          <el-icon class="logo-icon"><Promotion /></el-icon>
          TravelAI 智能旅游推荐系统
        </div>

        <div class="nav-menu">
          <el-menu mode="horizontal" :default-active="$route.path" router>
            <el-menu-item index="/">首页推荐</el-menu-item>
            <el-menu-item index="/spots">探索景点</el-menu-item>
            <el-menu-item index="/ai">AI智能帮搜</el-menu-item>
          </el-menu>
        </div>

        <div class="user-info" v-if="userStore.token">
          <el-dropdown>
            <span class="el-dropdown-link">
              <el-avatar :size="32" :icon="User" class="avatar-icon" />
              {{ userStore.userInfo.username || '用户' }}
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/collections')"><el-icon><Star /></el-icon> 我的收藏</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout"><el-icon><SwitchButton /></el-icon> 退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="user-info" v-else>
          <el-button type="primary" plain @click="$router.push('/login')">登录 / 注册</el-button>
        </div>
      </el-header>

      <!-- 主要内容区 -->
      <el-main>
        <!-- 欢迎横幅 -->
        <div class="banner">
          <h1 class="title">发现你的下一段完美旅程</h1>
          <p class="subtitle">基于大语言模型与混合推荐算法，为你量身定制的旅游体验</p>
          <div class="banner-actions">
            <el-button type="primary" size="large" @click="$router.push('/ai')" class="action-btn">
              <el-icon><ChatDotRound /></el-icon> 试试AI帮搜
            </el-button>
            <el-button size="large" @click="$router.push('/spots')" class="action-btn outline">
              <el-icon><Search /></el-icon> 浏览全部景点
            </el-button>
          </div>
        </div>

        <!-- 场景推荐卡片区 -->
        <div class="section-container scene-section">
          <h2 class="section-title">
            <span class="title-text">想玩什么？主题场景推荐</span>
            <span class="title-desc">不用纠结，选个主题直接出发</span>
          </h2>

          <el-tabs v-model="activeScene" class="scene-tabs" @tab-click="handleSceneClick">
            <el-tab-pane v-for="scene in scenes" :key="scene.name" :label="scene.name" :name="scene.name">
              <template #label>
                <span class="custom-tabs-label">
                  <el-icon><component :is="components[scene.icon as keyof typeof components]" /></el-icon>
                  <span>{{ scene.name }}</span>
                </span>
              </template>

              <div class="spot-scroll-container" v-loading="sceneLoading">
                <div class="spot-scroll-list">
                  <el-card v-for="spot in sceneSpots" :key="spot.id" class="spot-mini-card" shadow="hover" @click="goToSpot(spot.spot_id || spot.id)">
                    <img :src="spot.image_url || 'https://via.placeholder.com/200x150?text=暂无图片'" class="spot-mini-img" />
                    <div class="spot-mini-info">
                      <h4 class="spot-mini-name" :title="spot.name">{{ spot.name }}</h4>
                      <div class="spot-mini-meta">
                        <span class="city"><el-icon><Location /></el-icon> {{ spot.city }}</span>
                        <span class="rating"><el-icon><StarFilled /></el-icon> {{ spot.rating }}</span>
                      </div>
                    </div>
                  </el-card>
                  <el-empty v-if="!sceneLoading && sceneSpots.length === 0" description="该场景暂无数据" class="scene-empty" />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 个性化推荐区 (需登录) -->
        <div class="section-container recommend-section" v-if="userStore.token">
          <h2 class="section-title">
            <span class="title-text">为你推荐</span>
            <span class="title-desc">基于你的浏览与收藏历史计算</span>
          </h2>

          <div v-loading="recommendLoading" class="recommend-grid">
            <el-row :gutter="20" v-if="recommendations.length > 0">
              <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="(item, index) in recommendations" :key="index" class="recommend-col">
                <el-card class="recommend-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToSpot(item.spot_id)">
                  <div class="recommend-badge" :class="item.algorithm">{{ getAlgorithmName(item.algorithm) }}</div>
                  <img :src="item.details?.image_url || 'https://via.placeholder.com/300x200?text=暂无图片'" class="recommend-img" />
                  <div class="recommend-info">
                    <h3 class="recommend-name" :title="item.details?.name">{{ item.details?.name || '未知景点' }}</h3>
                    <div class="recommend-meta">
                      <el-tag size="small" type="info">{{ item.details?.city || '未知城市' }}</el-tag>
                      <span class="score-text">推荐度: {{(item.score * 100).toFixed(0)}}%</span>
                    </div>
                    <p class="recommend-desc">{{ getRecommendReason(item) }}</p>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <el-empty v-else-if="!recommendLoading" description="暂无个性化推荐，快去浏览一些景点吧！">
              <el-button type="primary" @click="$router.push('/spots')">去浏览</el-button>
            </el-empty>
          </div>
        </div>

        <!-- 未登录提示区 -->
        <div class="section-container login-prompt" v-else>
          <el-result icon="info" title="解锁个性化推荐" sub-title="登录后，TravelAI 将根据你的偏好为你推荐专属景点">
            <template #extra>
              <el-button type="primary" @click="$router.push('/login')">立即登录</el-button>
            </template>
          </el-result>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Promotion, User, ArrowDown, SwitchButton, Star,
  Search, ChatDotRound, Location, StarFilled,
  Present, Sunset, MostlyCloudy, Camera, MapLocation, Bicycle
} from '@element-plus/icons-vue'

// 注册组件给 component :is 用
const components = {
  Promotion, User, ArrowDown, SwitchButton, Star,
  Search, ChatDotRound, Location, StarFilled,
  Present, Sunset, MostlyCloudy, Camera, MapLocation, Bicycle
}
import { getSceneRecommendations, getRecommendations } from '../api/spots'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

// 场景定义
const scenes = [
  { name: '亲子游', icon: 'Present' },
  { name: '老年游', icon: 'Sunset' },
  { name: '历史文化游', icon: 'MostlyCloudy' },
  { name: '自然风光游', icon: 'Camera' },
  { name: '摄影打卡', icon: 'MapLocation' },
  { name: '探险运动', icon: 'Bicycle' }
]

const activeScene = ref('亲子游')
const sceneSpots = ref<any[]>([])
const sceneLoading = ref(false)

const recommendations = ref<any[]>([])
const recommendLoading = ref(false)

// 加载场景推荐
const loadSceneSpots = async (sceneName: string) => {
  sceneLoading.value = true
  try {
    const res = await getSceneRecommendations(sceneName, 8)
    sceneSpots.value = res.items
  } catch (error) {
    console.error('加载场景推荐失败:', error)
  } finally {
    sceneLoading.value = false
  }
}

// 加载个性化推荐
const loadRecommendations = async () => {
  if (!userStore.token) return

  recommendLoading.value = true
  try {
    const res = await getRecommendations(8)
    recommendations.value = res.items || res
  } catch (error) {
    console.error('加载个性化推荐失败:', error)
  } finally {
    recommendLoading.value = false
  }
}

const handleSceneClick = (tab: any) => {
  loadSceneSpots(tab.paneName)
}

const goToSpot = (id: number) => {
  if (id) router.push(`/spot/${id}`)
}

const handleLogout = () => {
  userStore.logout()
  recommendations.value = [] // 清空推荐
  ElMessage.success('已退出登录')
}

// 辅助函数
const getAlgorithmName = (algo: string) => {
  const map: Record<string, string> = {
    'collaborative': '猜你喜欢',
    'content': '相似内容',
    'hot': '热门推荐',
    'scene': '场景匹配'
  }
  return map[algo] || '推荐'
}

const getRecommendReason = (item: any) => {
  if (item.algorithm === 'collaborative') return '与你品味相似的用户也喜欢'
  if (item.algorithm === 'content') return '根据你最近的浏览历史推荐'
  if (item.algorithm === 'hot') return '近期大家都在去的热门景点'
  return '系统精选推荐'
}

onMounted(() => {
  loadSceneSpots(activeScene.value)
  if (userStore.token) {
    loadRecommendations()
  }
})
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.el-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  padding: 0 40px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 22px;
  font-weight: bold;
  color: #409EFF;
  display: flex;
  align-items: center;
}

.logo-icon {
  margin-right: 8px;
  font-size: 26px;
}

.nav-menu {
  flex: 1;
  margin: 0 40px;
}

.nav-menu .el-menu {
  border-bottom: none;
}

.nav-menu .el-menu-item {
  font-size: 16px;
  font-weight: 500;
}

.user-info {
  display: flex;
  align-items: center;
}

.el-dropdown-link {
  cursor: pointer;
  color: #303133;
  display: flex;
  align-items: center;
  font-weight: 500;
}

.avatar-icon {
  margin-right: 8px;
  background-color: #409EFF;
}

.el-main {
  padding: 0;
}

/* 欢迎横幅 */
.banner {
  background: linear-gradient(135deg, #409EFF 0%, #3a8ee6 100%);
  color: white;
  padding: 80px 40px;
  text-align: center;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.banner .title {
  font-size: 42px;
  margin: 0 0 20px;
  font-weight: 700;
  letter-spacing: 2px;
}

.banner .subtitle {
  font-size: 18px;
  margin: 0 0 40px;
  opacity: 0.9;
}

.banner-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.action-btn {
  padding: 12px 30px;
  font-size: 16px;
  border-radius: 30px;
  transition: all 0.3s;
}

.action-btn.outline {
  background: transparent;
  color: white;
  border: 2px solid white;
}

.action-btn.outline:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* 通用区块样式 */
.section-container {
  max-width: 1200px;
  margin: 40px auto;
  padding: 0 20px;
}

.section-title {
  display: flex;
  align-items: baseline;
  margin-bottom: 25px;
  border-bottom: 2px solid #ebeef5;
  padding-bottom: 15px;
}

.title-text {
  font-size: 24px;
  color: #303133;
  font-weight: bold;
  margin-right: 15px;
}

.title-desc {
  font-size: 14px;
  color: #909399;
}

/* 场景推荐区域 */
.scene-section {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.custom-tabs-label {
  display: flex;
  align-items: center;
  font-size: 15px;
}

.custom-tabs-label .el-icon {
  margin-right: 5px;
}

.spot-scroll-container {
  margin-top: 20px;
  min-height: 220px;
}

.spot-scroll-list {
  display: flex;
  overflow-x: auto;
  padding-bottom: 15px;
  gap: 20px;
  scroll-behavior: smooth;
}

.spot-scroll-list::-webkit-scrollbar {
  height: 8px;
}

.spot-scroll-list::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 4px;
}

.spot-mini-card {
  flex: 0 0 240px;
  cursor: pointer;
  border-radius: 8px;
  transition: transform 0.3s;
}

.spot-mini-card:hover {
  transform: translateY(-5px);
}

.spot-mini-img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-radius: 8px 8px 0 0;
}

.spot-mini-info {
  padding: 12px;
}

.spot-mini-name {
  margin: 0 0 8px;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spot-mini-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #606266;
}

.spot-mini-meta .el-icon {
  color: #409EFF;
  margin-right: 3px;
}

.spot-mini-meta .rating .el-icon {
  color: #ff9900;
}

.scene-empty {
  width: 100%;
}

/* 个性化推荐区域 */
.recommend-section {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.recommend-col {
  margin-bottom: 25px;
}

.recommend-card {
  height: 100%;
  cursor: pointer;
  position: relative;
  border-radius: 8px;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.recommend-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1) !important;
}

.recommend-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
  z-index: 1;
  font-weight: bold;
}

.recommend-badge.collaborative { background-color: #f56c6c; }
.recommend-badge.content { background-color: #67c23a; }
.recommend-badge.hot { background-color: #e6a23c; }
.recommend-badge.scene { background-color: #409eff; }

.recommend-img {
  width: 100%;
  height: 180px;
  object-fit: cover;
}

.recommend-info {
  padding: 15px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.recommend-name {
  margin: 0 0 10px;
  font-size: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recommend-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.score-text {
  font-size: 12px;
  color: #f56c6c;
  font-weight: bold;
}

.recommend-desc {
  margin: auto 0 0;
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 6px 10px;
  border-radius: 4px;
}

.login-prompt {
  background: white;
  border-radius: 12px;
  padding: 20px;
}
</style>