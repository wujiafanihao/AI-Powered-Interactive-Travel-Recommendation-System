<template>
  <!-- 景点详情页面容器，v-loading 显示加载状态 -->
  <div class="spot-detail-container" v-loading="loading">
    <!-- 页面头部，包含返回按钮和景点名称 -->
    <el-page-header @back="goBack" class="page-header" :content="spot?.name" />

    <!-- 主要内容区域，使用 el-row 和 el-col 进行布局 -->
    <el-row :gutter="30" class="detail-content" v-if="spot">
      <!-- 左侧：图片和基本信息 -->
      <el-col :md="12" :lg="10" class="left-col">
        <!-- 景点图片卡片 -->
        <el-card class="image-card" shadow="hover">
          <div class="image-wrapper">
            <img 
              :src="cleanUrl(spot.image_url) || 'https://via.placeholder.com/600x400?text=暂无图片'" 
              class="spot-image" 
              @error="handleImageError"
            />
            <!-- 评分悬浮标签 -->
            <div class="rating-badge">
              <el-icon><StarFilled /></el-icon>
              <span class="rating-number">{{ typeof spot.rating === 'number' ? spot.rating.toFixed(1) : spot.rating }}</span>
            </div>
          </div>
        </el-card>

        <!-- 基本信息卡片 -->
        <el-card class="basic-info-card" shadow="hover">
          <template #header>
            <div class="card-header-title">
              <el-icon><InfoFilled /></el-icon>
              基本信息
            </div>
          </template>
          
          <!-- 地址信息 -->
          <div class="info-item">
            <div class="info-icon-wrapper location">
              <el-icon><Location /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">地址</span>
              <span class="value">{{ spot.address || '暂无信息' }}</span>
            </div>
          </div>
          
          <!-- 建议游玩时间 -->
          <div class="info-item">
            <div class="info-icon-wrapper time">
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">建议游玩时间</span>
              <span class="value">{{ spot.suggest_time || '暂无信息' }}</span>
            </div>
          </div>
          
          <!-- 所属城市 -->
          <div class="info-item">
            <div class="info-icon-wrapper city">
              <el-icon><MapLocation /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">所属城市</span>
              <span class="value">
                <el-tag type="primary" size="small" class="city-tag">{{ spot.city }}</el-tag>
              </span>
            </div>
          </div>
          
          <!-- 景点类型 -->
          <div class="info-item" v-if="spot.spot_type && spot.spot_type.length">
            <div class="info-icon-wrapper type">
              <el-icon><Tickets /></el-icon>
            </div>
            <div class="info-content">
              <span class="label">景点类型</span>
              <span class="value">
                <el-tag v-for="type in spot.spot_type" :key="type" size="small" type="info" class="type-tag">{{ type }}</el-tag>
              </span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：详细介绍和操作 -->
      <el-col :md="12" :lg="14" class="right-col">
        <el-card class="main-info-card" shadow="never">
          <!-- 标题和收藏按钮 -->
          <div class="header-action">
            <h1 class="title">{{ spot.name }}</h1>
            <div class="actions">
              <!-- 收藏按钮，根据是否收藏显示不同状态 -->
              <el-tooltip :content="isCollected ? '取消收藏' : '加入收藏'" placement="top">
                <el-button
                  :type="isCollected ? 'danger' : 'default'"
                  :icon="isCollected ? StarFilled : Star"
                  circle
                  size="large"
                  @click="toggleCollect"
                  class="collect-btn"
                />
              </el-tooltip>
            </div>
          </div>

          <!-- 评分区域 -->
          <div class="rating-box">
            <!-- 景点评分 -->
            <div class="score-display">
              <div class="score">{{ spot.rating || '暂无' }}</div>
              <div class="score-details">
                <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
                <span class="score-label">综合评分</span>
              </div>
            </div>
            <!-- 用户评分（只有登录后才显示） -->
            <div class="user-rating" v-if="userStore.token">
              <span class="user-rating-label">您的评分：</span>
              <el-rate v-model="userRating" allow-half @change="handleRate" class="user-rate-star" />
            </div>
          </div>

          <el-divider class="custom-divider" />

          <!-- 景点介绍 -->
          <div class="section">
            <h3 class="section-title">
              <el-icon><Document /></el-icon>
              景点介绍
            </h3>
            <p class="description">{{ spot.description || '暂无介绍' }}</p>
          </div>

          <!-- 开放时间（如果有） -->
          <div class="section" v-if="spot.open_time">
            <h3 class="section-title">
              <el-icon><Timer /></el-icon>
              开放时间
            </h3>
            <div class="info-box">
              <p>{{ spot.open_time }}</p>
            </div>
          </div>

          <!-- 门票信息（如果有） -->
          <div class="section" v-if="spot.ticket_info">
            <h3 class="section-title">
              <el-icon><Ticket /></el-icon>
              门票信息
            </h3>
            <div class="info-box">
              <p>{{ spot.ticket_info }}</p>
            </div>
          </div>

          <!-- 游玩小贴士（如果有） -->
          <div class="section" v-if="spot.tips">
            <h3 class="section-title">
              <el-icon><Warning /></el-icon>
              游玩小贴士
            </h3>
            <div class="info-box tips-box">
              <p>{{ spot.tips }}</p>
            </div>
          </div>

          <!-- 用户评论区域 -->
          <div class="section comments-section">
            <h3 class="section-title">
              <el-icon><ChatDotRound /></el-icon>
              用户评价 ({{ comments.length }})
            </h3>
            <!-- 评论加载中 -->
            <div v-if="commentsLoading" class="comments-loading">
              <el-skeleton :rows="3" animated />
            </div>
            <!-- 评论列表 -->
            <div v-else-if="comments.length > 0" class="comments-list">
              <div v-for="comment in comments" :key="comment.id" class="comment-item">
                <div class="comment-header">
                  <div class="comment-user">
                    <el-avatar :size="36" :icon="User" class="avatar-icon" />
                    <div class="user-info">
                      <span class="nickname">{{ comment.nickname || comment.username }}</span>
                      <span class="comment-time">{{ formatDate(comment.created_at) }}</span>
                    </div>
                  </div>
                  <div class="comment-rating">
                    <el-rate v-model="comment.rating" disabled show-score text-color="#ff9900" size="small" />
                  </div>
                </div>
                <div class="comment-content">{{ comment.content }}</div>
                <el-divider border-style="dashed" class="comment-divider" />
              </div>
            </div>
            <!-- 暂无评论 -->
            <div v-else class="no-comments">
              <el-empty description="暂无评价，快来抢沙发吧！" :image-size="80" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 专属 AI 悬浮按钮 -->
    <div class="ai-fab" @click="toggleAIChat" v-if="spot">
      <el-tooltip content="专属景点AI导游" placement="left">
        <div class="fab-button" :class="{ 'active': aiChatVisible }">
          <el-icon><Headset /></el-icon>
        </div>
      </el-tooltip>
    </div>

    <!-- 复用型专属 AI 聊天抽屉 -->
    <SpotAssistantDrawer
      v-model="aiChatVisible"
      mode="spot"
      :spot-id="spotId"
      :title="aiDrawerTitle"
      :welcome-message="aiWelcomeMessage"
      :input-placeholder="aiInputPlaceholder"
    />
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { computed, ref, onMounted, onUnmounted } from 'vue'
// 引入路由
import { useRoute, useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'
// 引入 Element Plus 的图标
import {
  Location, Calendar, MapLocation, Tickets,
  Document, Timer, Ticket, Warning,
  Star, StarFilled, ChatDotRound, User, Headset,
  InfoFilled
} from '@element-plus/icons-vue'

type SpotDetailData = {
  id: number
  name: string
  city?: string
  rating?: number | string
  image_url?: string
  address?: string
  suggest_time?: string
  spot_type?: string[]
  description?: string
  open_time?: string
  ticket_info?: string
  tips?: string
}

type CollectionItem = {
  id: number
}

type SpotComment = {
  id: number
  nickname?: string
  username?: string
  created_at: string
  rating: number
  content: string
}
// 引入 API 接口
import { getSpotDetail, getCollections, toggleCollection, recordBehavior, getSpotComments, recordRecommendFeedback } from '../../api/spots'
// 引入用户状态管理
import { useUserStore } from '../../store/user'
import SpotAssistantDrawer from '../../components/SpotAssistantDrawer.vue'

// 获取路由和路由参数
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 获取景点 ID
const spotId = Number(route.params.id)
// 加载状态
const loading = ref(true)
// 景点详情数据
const spot = ref<SpotDetailData | null>(null)
// 是否已收藏
const isCollected = ref(false)
// 用户评分
const userRating = ref(0)
// 开始浏览时间（用于计算浏览时长）
const startTime = ref(0)

// 获取景点详情
const fetchDetail = async () => {
  try {
    const res = await getSpotDetail(spotId)
    spot.value = res

    // 如果已登录，检查是否已收藏并记录浏览行为
    if (userStore.token) {
      checkCollection()
      recordUserBehavior('view')
    }
  } catch (error: unknown) {
    console.error('获取详情失败:', error)
    const status = (error as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      ElMessage.error('景点不存在')
      router.push('/spots')
    } else {
      ElMessage.error('获取详情失败')
    }
  } finally {
    loading.value = false
  }
}

// 检查是否已收藏
const checkCollection = async () => {
  try {
    const res = await getCollections()
    const items = Array.isArray(res?.items) ? (res.items as CollectionItem[]) : []
    isCollected.value = items.some((item) => item.id === spotId)
  } catch (error) {
    console.error('检查收藏状态失败:', error)
  }
}

// 切换收藏状态
const toggleCollect = async () => {
  if (!userStore.token) {
    ElMessage.warning('请先登录后再收藏')
    router.push(`/login?redirect=${route.path}`)
    return
  }

  try {
    const res = await toggleCollection(spotId)
    isCollected.value = res.collected
    if (res.collected) {
      recordRecommendFeedback({
        spot_id: spotId,
        event_type: 'collect',
        source: 'spot-detail'
      }).catch((error) => {
        console.error('上报收藏反馈失败:', error)
      })
    }
    ElMessage.success(res.message)
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败')
  }
}

// 用户评分
const handleRate = async (val: number) => {
  if (!userStore.token) {
    ElMessage.warning('请先登录后再评分')
    userRating.value = 0
    return
  }

  recordUserBehavior('rate', val)
  recordRecommendFeedback({
    spot_id: spotId,
    event_type: 'rate',
    source: 'spot-detail',
    score: val
  }).catch((error) => {
    console.error('上报评分反馈失败:', error)
  })
  ElMessage.success('评分成功，感谢您的评价！')
}

// 记录用户行为（浏览、评分、时长等）
const recordUserBehavior = async (type: string, rating?: number, duration?: number) => {
  if (!userStore.token) return

  try {
    await recordBehavior({
      spot_id: spotId,
      behavior_type: type,
      rating: rating,
      duration: duration
    })
  } catch (error) {
    console.error('记录行为失败:', error)
  }
}

// 返回上一页
const goBack = () => {
  router.back()
}

// 评论相关逻辑
const comments = ref<SpotComment[]>([])
const commentsLoading = ref(false)

// 获取评论列表
const fetchComments = async () => {
  commentsLoading.value = true
  try {
    const res = await getSpotComments(spotId)
    comments.value = res.items || []
  } catch (error) {
    console.error('获取评论失败:', error)
  } finally {
    commentsLoading.value = false
  }
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

// AI 聊天抽屉相关逻辑（复用组件）
const aiChatVisible = ref(false)

const toggleAIChat = () => {
  aiChatVisible.value = !aiChatVisible.value
}

const aiDrawerTitle = computed(() => `🤖 ${spot.value?.name || '景点'} 专属导游`)

const aiWelcomeMessage = computed(() => {
  const name = spot.value?.name || '这个景点'
  return `你好！我是 ${name} 的专属AI导游。你可以问我最佳游玩路线、避坑建议、门票和交通问题。`
})

const aiInputPlaceholder = computed(() => `问我关于 ${spot.value?.name || '该景点'} 的问题吧...`)

// 清理图片 URL 的函数，去除反引号和空格
const cleanUrl = (url: string) => {
  if (!url) return ''
  return url.trim().replace(/[` ]/g, '')
}

// 图片加载失败时的处理函数
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'https://via.placeholder.com/600x400?text=暂无图片'
}

// 组件挂载时执行
onMounted(() => {
  fetchDetail()
  fetchComments()
  startTime.value = Date.now()
})

// 组件卸载时执行
onUnmounted(() => {
  // 离开页面时记录浏览时长
  if (userStore.token && spotId) {
    const duration = Math.round((Date.now() - startTime.value) / 1000)
    if (duration > 5) { // 停留超过5秒才算有效浏览
      recordUserBehavior('duration', undefined, duration)
    }
  }
})
</script>

<style scoped>
/* 景点详情页面容器样式 */
.spot-detail-container {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
  background: linear-gradient(180deg, #f0f4f8 0%, #e9ecef 50%, #f8f9fa 100%);
  min-height: calc(100vh - 60px);
  animation: fadeIn 0.6s ease;
}

/* 页面头部样式 */
.page-header {
  margin-bottom: 24px;
  padding: 16px 24px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  animation: fadeInDown 0.6s ease;
}

/* 详情内容区域样式 */
.detail-content {
  margin-top: 20px;
}

/* 左侧列 */
.left-col {
  animation: fadeInLeft 0.8s cubic-bezier(0.23, 1, 0.32, 1);
}

/* 右侧列 */
.right-col {
  animation: fadeInRight 0.8s cubic-bezier(0.23, 1, 0.32, 1);
  animation-delay: 0.2s;
  animation-fill-mode: both;
}

/* 图片卡片样式 */
.image-card {
  margin-bottom: 24px;
  border-radius: 20px;
  border: none;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.image-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

/* 图片包装器 */
.image-wrapper {
  position: relative;
  overflow: hidden;
}

/* 景点图片样式 */
.spot-image {
  width: 100%;
  height: 400px;
  object-fit: cover;
  display: block;
  transition: transform 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.image-wrapper:hover .spot-image {
  transform: scale(1.08);
}

/* 评分标签 */
.rating-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  background: linear-gradient(135deg, #ff9900 0%, #ffb347 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 24px;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 4px 16px rgba(255, 153, 0, 0.4);
  backdrop-filter: blur(10px);
}

.rating-number {
  font-size: 18px;
}

/* 基本信息卡片样式 */
.basic-info-card {
  margin-bottom: 24px;
  border-radius: 20px;
  border: none;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.basic-info-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

/* 卡片头部标题 */
.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* 信息项样式 */
.info-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
  line-height: 1.6;
  transition: all 0.3s ease;
  padding: 12px;
  border-radius: 12px;
}

.info-item:hover {
  background: #f5f7fa;
  transform: translateX(4px);
}

.info-item:last-child {
  margin-bottom: 0;
}

/* 信息图标包装器 */
.info-icon-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 14px;
  flex-shrink: 0;
}

.info-icon-wrapper.location {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
}

.info-icon-wrapper.time {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
  color: white;
}

.info-icon-wrapper.city {
  background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%);
  color: white;
}

.info-icon-wrapper.type {
  background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%);
  color: white;
}

/* 信息内容 */
.info-content {
  flex: 1;
}

.label {
  display: block;
  color: #909399;
  font-size: 13px;
  margin-bottom: 4px;
}

.value {
  color: #303133;
  font-size: 15px;
  font-weight: 500;
}

/* 城市标签 */
.city-tag {
  border-radius: 20px;
  padding: 4px 12px;
}

.type-tag {
  margin-right: 6px;
  margin-bottom: 6px;
  border-radius: 16px;
}

/* 主要信息卡片样式 */
.main-info-card {
  height: 100%;
  border-radius: 20px;
  border: none;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
}

.main-info-card:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
}

/* 标题和操作区域样式 */
.header-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  margin: 0;
  font-size: 30px;
  color: #303133;
  font-weight: 700;
  background: linear-gradient(135deg, #303133 0%, #409eff 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 收藏按钮 */
.collect-btn {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.collect-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}

/* 评分区域样式 */
.rating-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #fff7e6 0%, #fffaeb 100%);
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #ffcc80;
}

/* 评分显示 */
.score-display {
  display: flex;
  align-items: center;
  gap: 16px;
}

.score {
  font-size: 42px;
  font-weight: 700;
  color: #ff9900;
  line-height: 1;
}

.score-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-label {
  font-size: 13px;
  color: #909399;
}

/* 用户评分 */
.user-rating {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-rating-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

.user-rate-star {
  cursor: pointer;
}

/* 自定义分割线 */
.custom-divider {
  margin: 24px 0;
  border-color: #ebeef5;
}

/* 通用区块样式 */
.section {
  margin-bottom: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 18px;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 12px;
  border-left: 4px solid #409eff;
  font-weight: 600;
}

.section-title .el-icon {
  margin-right: 8px;
  color: #409eff;
}

.description {
  line-height: 1.9;
  color: #606266;
  text-align: justify;
  white-space: pre-line;
  font-size: 15px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 12px;
}

/* 信息框 */
.info-box {
  padding: 16px;
  background: #f0f9ff;
  border-radius: 12px;
  border-left: 4px solid #409eff;
}

.info-box p {
  margin: 0;
  color: #303133;
  line-height: 1.8;
  font-size: 15px;
}

/* 小贴士框 */
.tips-box {
  background: #fff7e6;
  border-left-color: #ff9900;
}

/* 评论区域样式 */
.comments-section {
  margin-top: 36px;
}

.comment-item {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.comment-item:hover {
  background: #f5f7fa;
  transform: translateX(4px);
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.comment-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar-icon {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nickname {
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.comment-time {
  font-size: 12px;
  color: #909399;
}

.comment-rating {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.comment-content {
  color: #606266;
  line-height: 1.8;
  margin-bottom: 12px;
  font-size: 14px;
}

.comment-divider {
  margin: 12px 0 0;
}

.no-comments {
  padding: 40px 0;
}

/* AI 悬浮按钮样式 */
.ai-fab {
  position: fixed;
  right: 40px;
  bottom: 100px;
  z-index: 100;
  cursor: pointer;
  animation: float 3s ease-in-out infinite;
}

.fab-button {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #79bbff 100%);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 30px;
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fab-button:hover {
  transform: scale(1.15);
  box-shadow: 0 8px 28px rgba(64, 158, 255, 0.5);
}

.fab-button.active {
  background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%);
  box-shadow: 0 6px 20px rgba(144, 147, 153, 0.4);
}

/* 动画定义 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInLeft {
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}
</style>
