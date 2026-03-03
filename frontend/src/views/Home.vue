<template>
  <!-- 首页容器 -->
  <div class="home-container">
    <el-container>
      <!-- 顶部导航栏 -->
      <el-header>
        <!-- Logo 区域 -->
        <div class="logo">
          <el-icon class="logo-icon"><Promotion /></el-icon>
          TravelAI 智能旅游推荐系统
        </div>

        <!-- 导航菜单 -->
        <div class="nav-menu">
          <!-- 水平菜单，router 属性表示点击菜单项会自动跳转路由 -->
          <el-menu mode="horizontal" :default-active="$route.path" router>
            <el-menu-item index="/">首页推荐</el-menu-item>
            <el-menu-item index="/spots">探索景点</el-menu-item>
            <el-menu-item index="/ai">AI智能帮搜</el-menu-item>
          </el-menu>
        </div>

        <!-- 用户信息区域（已登录时显示） -->
        <div class="user-info" v-if="userStore.token">
          <!-- 下拉菜单 -->
          <el-dropdown>
            <span class="el-dropdown-link">
              <!-- 用户头像 -->
              <el-avatar :size="32" :icon="User" class="avatar-icon" />
              <!-- 用户名 -->
              {{ userStore.userInfo.username || '用户' }}
              <!-- 下拉箭头 -->
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </span>
            <!-- 下拉菜单内容 -->
            <template #dropdown>
              <el-dropdown-menu>
                <!-- 个人资料菜单项 -->
                <el-dropdown-item @click="$router.push('/profile')"><el-icon><User /></el-icon> 个人资料</el-dropdown-item>
                <!-- 我的收藏菜单项 -->
                <el-dropdown-item @click="$router.push('/collections')"><el-icon><Star /></el-icon> 我的收藏</el-dropdown-item>
                <!-- 退出登录菜单项，divided 属性表示有分隔线 -->
                <el-dropdown-item divided @click="handleLogout"><el-icon><SwitchButton /></el-icon> 退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <!-- 未登录时显示登录/注册按钮 -->
        <div class="user-info" v-else>
          <el-button type="primary" plain @click="$router.push('/login')">登录 / 注册</el-button>
        </div>
      </el-header>

      <!-- 主要内容区域 -->
      <el-main>
        <!-- 欢迎横幅区域 -->
        <div class="banner">
          <h1 class="title">发现你的下一段完美旅程</h1>
          <p class="subtitle">基于大语言模型与混合推荐算法，为你量身定制的旅游体验</p>
          <!-- 横幅上的操作按钮 -->
          <div class="banner-actions">
            <!-- AI 帮搜按钮 -->
            <el-button type="primary" size="large" @click="$router.push('/ai')" class="action-btn">
              <el-icon><ChatDotRound /></el-icon> 试试AI帮搜
            </el-button>
            <!-- 浏览全部景点按钮 -->
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

          <!-- 场景标签页 -->
          <el-tabs v-model="activeScene" class="scene-tabs" @tab-click="handleSceneClick">
            <!-- 遍历所有场景，生成标签页 -->
            <el-tab-pane v-for="scene in scenes" :key="scene.name" :label="scene.name" :name="scene.name">
              <!-- 自定义标签页显示内容：图标 + 文字 -->
              <template #label>
                <span class="custom-tabs-label">
                  <el-icon><component :is="components[scene.icon as keyof typeof components]" /></el-icon>
                  <span>{{ scene.name }}</span>
                </span>
              </template>

              <!-- 场景景点滚动列表容器，显示加载状态 -->
              <div class="spot-scroll-container" v-loading="sceneLoading">
                <div class="spot-scroll-list">
                  <!-- 遍历该场景下的景点，生成卡片 -->
                  <el-card v-for="spot in sceneSpots" :key="spot.id" class="spot-mini-card" shadow="hover" @click="goToSpot(spot.spot_id || spot.id, spot)">
                    <!-- 景点图片 -->
                    <img :src="spot.image_url || 'https://via.placeholder.com/200x150?text=暂无图片'" class="spot-mini-img" />
                    <!-- 景点信息 -->
                    <div class="spot-mini-info">
                      <h4 class="spot-mini-name" :title="spot.name">{{ spot.name }}</h4>
                      <div class="spot-mini-meta">
                        <span class="city"><el-icon><Location /></el-icon> {{ spot.city }}</span>
                        <span class="rating"><el-icon><StarFilled /></el-icon> {{ typeof spot.rating === 'number' ? spot.rating.toFixed(1) : spot.rating }}</span>
                      </div>
                    </div>
                  </el-card>
                  <!-- 如果没有数据且加载完成，显示空状态 -->
                  <el-empty v-if="!sceneLoading && sceneSpots.length === 0" description="该场景暂无数据" class="scene-empty" />
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- 个性化推荐区（只有登录后才显示） -->
        <div class="section-container recommend-section" v-if="userStore.token">
          <h2 class="section-title">
            <span class="title-text">为你推荐</span>
            <span class="title-desc">基于你的浏览与收藏历史计算</span>
          </h2>

          <!-- 推荐列表容器，显示加载状态 -->
          <div v-loading="recommendLoading" class="recommend-grid">
            <!-- 如果有推荐数据，显示推荐卡片 -->
            <el-row :gutter="20" v-if="recommendations.length > 0">
              <!-- 遍历推荐结果，生成卡片 -->
              <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="(item, index) in recommendations" :key="index" class="recommend-col">
                <el-card class="recommend-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToSpot(item.spot_id, item)">
                  <!-- 推荐算法标签，悬浮在卡片左上角 -->
                  <div class="recommend-badge" :class="item.source || item.algorithm">{{ getAlgorithmName(item.source || item.algorithm) }}</div>
                  <!-- 景点图片 -->
                  <img :src="(item.image_url || '').trim() || 'https://via.placeholder.com/300x200?text=暂无图片'" class="recommend-img" />
                  <!-- 推荐信息 -->
                  <div class="recommend-info">
                    <h3 class="recommend-name" :title="item.name">{{ item.name || '未知景点' }}</h3>
                    <div class="recommend-meta">
                      <!-- 城市标签 -->
                      <el-tag size="small" type="info">{{ item.city || '未知城市' }}</el-tag>
                      <!-- 推荐度分数 -->
                      <span class="score-text">推荐度: {{(item.score * 100).toFixed(0)}}%</span>
                    </div>
                    <div class="match-score" v-if="typeof item.match_score === 'number'">
                      匹配分：{{ item.match_score.toFixed(0) }}%
                    </div>
                    <!-- 推荐理由 -->
                    <p class="recommend-desc">{{ getRecommendReason(item) }}</p>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <!-- 如果没有推荐数据且加载完成，显示空状态 -->
            <el-empty v-else-if="!recommendLoading" description="暂无个性化推荐，快去浏览一些景点吧！">
              <el-button type="primary" @click="$router.push('/spots')">去浏览</el-button>
            </el-empty>
          </div>
        </div>

        <!-- 未登录提示区（未登录时显示） -->
        <div class="section-container login-prompt" v-else>
          <el-result icon="info" title="解锁个性化推荐" sub-title="登录后，TravelAI 将根据你的偏好为你推荐专属景点">
            <template #extra>
              <el-button type="primary" @click="$router.push('/login')">立即登录</el-button>
            </template>
          </el-result>
        </div>
      </el-main>
    </el-container>

    <!-- 首次登录引导弹窗 -->
    <el-dialog
      v-model="profileDialogVisible"
      title="🎉 完善资料，开启智能推荐"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="profile-dialog-content">
        <div class="dialog-header">
          <el-icon :size="48" color="#409EFF"><Present /></el-icon>
          <h3>欢迎使用 TravelAI！</h3>
        </div>
        <p class="dialog-text">
          告诉我们您的基本信息，我们将根据您的<strong>所在城市</strong>、<strong>旅行偏好</strong>等，
          为您推荐最适合的景点！
        </p>
        <div class="dialog-tips">
          <el-alert
            title="完善资料后，您将获得："
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <ul class="tip-list">
                <li>📍 <strong>同城推荐</strong>：优先推荐您所在城市的景点</li>
                <li>🎯 <strong>精准匹配</strong>：根据您的旅行偏好推荐</li>
                <li>🌸 <strong>季节推荐</strong>：推荐适合当前季节的景点</li>
                <li>👥 <strong>相似用户</strong>：品味相似的用户喜欢的景点</li>
              </ul>
            </template>
          </el-alert>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="goToProfile">去完善资料</el-button>
          <el-button type="primary" @click="closeProfileDialog">先逛逛</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, onMounted } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'
// 引入 Element Plus 的图标
import {
  Promotion, User, ArrowDown, SwitchButton, Star,
  Search, ChatDotRound, Location, StarFilled,
  Present, Sunset, MostlyCloudy, Camera, MapLocation, Bicycle
} from '@element-plus/icons-vue'

// 注册组件，给 component :is 动态组件使用
const components = {
  Promotion, User, ArrowDown, SwitchButton, Star,
  Search, ChatDotRound, Location, StarFilled,
  Present, Sunset, MostlyCloudy, Camera, MapLocation, Bicycle
}
// 引入推荐相关的 API 接口
import { getSceneRecommendations, getRecommendations, recordRecommendFeedback, getProfileStatus } from '../api/spots'
// 引入用户状态管理
import { useUserStore } from '../store/user'

// 获取路由实例
const router = useRouter()
// 获取用户状态管理实例
const userStore = useUserStore()

// 首次登录引导弹窗
const profileDialogVisible = ref(false)

// 去完善资料
const goToProfile = () => {
  profileDialogVisible.value = false
  router.push('/profile')
}

// 关闭弹窗
const closeProfileDialog = () => {
  profileDialogVisible.value = false
  // 标记用户已看过弹窗（使用 sessionStorage）
  sessionStorage.setItem('hasSeenProfileDialog', 'true')
}

// 检查是否需要显示引导弹窗
const checkProfileDialog = async () => {
  if (!userStore.token) return
  
  // 如果已经看过弹窗，不再显示
  if (sessionStorage.getItem('hasSeenProfileDialog') === 'true') return
  
  try {
    const status = await getProfileStatus()
    // 如果是首次登录且资料不完善，显示弹窗
    if (status.is_first_login && !status.is_complete) {
      profileDialogVisible.value = true
    }
  } catch (error) {
    console.error('检查资料状态失败:', error)
  }
}

// 定义场景列表，每个场景有名称和对应的图标
const scenes = [
  { name: '亲子游', icon: 'Present' },
  { name: '老年游', icon: 'Sunset' },
  { name: '历史文化游', icon: 'MostlyCloudy' },
  { name: '自然风光游', icon: 'Camera' },
  { name: '摄影打卡', icon: 'MapLocation' },
  { name: '探险运动', icon: 'Bicycle' }
]

// 当前激活的场景
const activeScene = ref('亲子游')
// 场景景点列表
const sceneSpots = ref<any[]>([])
// 场景加载状态
const sceneLoading = ref(false)

// 个性化推荐列表
const recommendations = ref<any[]>([])
// 推荐加载状态
const recommendLoading = ref(false)

// 加载场景推荐的函数
const loadSceneSpots = async (sceneName: string) => {
  sceneLoading.value = true
  try {
    // 调用 API 获取场景推荐，默认返回 8 个景点
    const res = await getSceneRecommendations(sceneName, 8)
    const items = Array.isArray(res?.items) ? res.items : []
    sceneSpots.value = items

    // 登录用户上报场景推荐曝光（同一轮去重）
    if (userStore.token) {
      const exposed = new Set<number>()
      for (const item of items) {
        const spotId = Number(item?.spot_id || item?.id || 0)
        if (!spotId || exposed.has(spotId)) continue
        exposed.add(spotId)

        recordRecommendFeedback({
          spot_id: spotId,
          event_type: 'exposure',
          source: item?.source || item?.algorithm || 'scene',
          score: typeof item?.score === 'number' ? item.score : undefined
        }).catch((error) => {
          console.error('上报场景推荐曝光失败:', error)
        })
      }
    }
  } catch (error) {
    console.error('加载场景推荐失败:', error)
  } finally {
    // 无论成功或失败，都关闭加载状态
    sceneLoading.value = false
  }
}

// 加载个性化推荐的函数
const loadRecommendations = async () => {
  // 如果没有登录，不加载推荐
  if (!userStore.token) return

  recommendLoading.value = true
  try {
    // 调用 API 获取个性化推荐，默认返回 8 个景点
    const res = await getRecommendations(8)
    const items = res.items || res
    recommendations.value = items

    // 上报曝光反馈（同一轮推荐去重）
    const exposed = new Set<number>()
    for (const item of items) {
      const spotId = Number(item?.spot_id || item?.id || 0)
      if (!spotId || exposed.has(spotId)) continue
      exposed.add(spotId)

      recordRecommendFeedback({
        spot_id: spotId,
        event_type: 'exposure',
        source: item?.source || item?.algorithm,
        score: typeof item?.score === 'number' ? item.score : undefined
      }).catch((error) => {
        console.error('上报推荐曝光失败:', error)
      })
    }
  } catch (error) {
    console.error('加载个性化推荐失败:', error)
  } finally {
    // 无论成功或失败，都关闭加载状态
    recommendLoading.value = false
  }
}

// 切换场景标签页时的处理函数
const handleSceneClick = (tab: any) => {
  loadSceneSpots(tab.paneName)
}

// 跳转到景点详情页的函数
const goToSpot = (id: number, item?: any) => {
  if (!id) return

  const spotId = Number(item?.spot_id || item?.id || id)
  if (userStore.token && spotId) {
    recordRecommendFeedback({
      spot_id: spotId,
      event_type: 'click',
      source: item?.source || item?.algorithm || 'scene',
      score: typeof item?.score === 'number' ? item.score : undefined
    }).catch((e) => {
      console.error('上报推荐点击失败:', e)
    })
  }

  router.push(`/spot/${id}`)
}

// 退出登录的函数
const handleLogout = () => {
  // 调用用户状态管理的退出登录函数
  userStore.logout()
  // 清空推荐列表
  recommendations.value = []
  ElMessage.success('已退出登录')
}

// 辅助函数：获取推荐算法的中文名称
const getAlgorithmName = (algo: string) => {
  const map: Record<string, string> = {
    'collaborative': '猜你喜欢',
    'content': '相似内容',
    'hot': '热门推荐',
    'scene': '场景匹配',
    'cb': '猜你喜欢',
    'cf': '相似用户',
    'profile': '画像匹配',
    'hybrid': '综合推荐'
  }
  return map[algo] || '推荐'
}

// 辅助函数：获取推荐理由
const getRecommendReason = (item: any) => {
  if (item.reason) return item.reason
  if (item.algorithm === 'collaborative' || item.source === 'cf') return '与你品味相似的用户也喜欢'
  if (item.algorithm === 'content' || item.source === 'cb') return '根据你最近的浏览历史推荐'
  if (item.algorithm === 'hot') return '近期大家都在去的热门景点'
  return '系统精选推荐'
}

// 组件挂载时执行
onMounted(() => {
  // 加载当前激活场景的推荐
  loadSceneSpots(activeScene.value)
  // 如果已登录，加载个性化推荐并检查资料
  if (userStore.token) {
    loadRecommendations()
    checkProfileDialog()
  }
})
</script>

<style scoped>
/* 首页容器样式 */
.home-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

/* 顶部导航栏样式 */
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

/* Logo 样式 */
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

/* 导航菜单样式 */
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

/* 用户信息区域样式 */
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

/* 欢迎横幅样式 */
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

/* 场景推荐区域样式 */
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

/* 个性化推荐区域样式 */
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

/* 不同推荐算法的标签颜色 */
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

.match-score {
  margin-bottom: 8px;
  font-size: 12px;
  color: #409eff;
  font-weight: 600;
}

/* 未登录提示区样式 */
.login-prompt {
  background: white;
  border-radius: 12px;
  padding: 20px;
}

/* 首次登录引导弹窗样式 */
.profile-dialog-content {
  text-align: center;
  padding: 20px 10px;
}

.dialog-header {
  margin-bottom: 20px;
}

.dialog-header h3 {
  margin-top: 10px;
  font-size: 20px;
  color: #303133;
}

.dialog-text {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 20px;
}

.dialog-tips {
  text-align: left;
  margin-top: 20px;
}

.tip-list {
  margin: 10px 0 0 0;
  padding-left: 20px;
  list-style: none;
}

.tip-list li {
  margin: 8px 0;
  font-size: 13px;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: center;
  gap: 10px;
}
</style>