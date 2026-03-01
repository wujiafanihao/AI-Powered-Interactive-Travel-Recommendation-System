<template>
  <!-- 景点详情页面容器，v-loading 显示加载状态 -->
  <div class="spot-detail-container" v-loading="loading">
    <!-- 页面头部，包含返回按钮和景点名称 -->
    <el-page-header @back="goBack" class="page-header" :content="spot?.name" />

    <!-- 主要内容区域，使用 el-row 和 el-col 进行布局 -->
    <el-row :gutter="30" class="detail-content" v-if="spot">
      <!-- 左侧：图片和基本信息 -->
      <el-col :md="12" :lg="10">
        <!-- 景点图片卡片 -->
        <el-card class="image-card" :body-style="{ padding: '0px' }">
          <img :src="spot.image_url || 'https://via.placeholder.com/600x400?text=暂无图片'" class="spot-image" />
        </el-card>

        <!-- 基本信息卡片 -->
        <el-card class="basic-info-card" shadow="hover">
          <!-- 地址信息 -->
          <div class="info-item">
            <el-icon><Location /></el-icon>
            <span class="label">地址：</span>
            <span class="value">{{ spot.address || '暂无信息' }}</span>
          </div>
          <!-- 建议游玩时间 -->
          <div class="info-item">
            <el-icon><Calendar /></el-icon>
            <span class="label">建议游玩时间：</span>
            <span class="value">{{ spot.suggest_time || '暂无信息' }}</span>
          </div>
          <!-- 所属城市 -->
          <div class="info-item">
            <el-icon><MapLocation /></el-icon>
            <span class="label">所属城市：</span>
            <span class="value"><el-tag>{{ spot.city }}</el-tag></span>
          </div>
          <!-- 景点类型 -->
          <div class="info-item" v-if="spot.spot_type && spot.spot_type.length">
            <el-icon><Tickets /></el-icon>
            <span class="label">景点类型：</span>
            <span class="value">
              <el-tag v-for="type in spot.spot_type" :key="type" size="small" type="info" class="type-tag">{{ type }}</el-tag>
            </span>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：详细介绍和操作 -->
      <el-col :md="12" :lg="14">
        <el-card class="main-info-card" shadow="never">
          <!-- 标题和收藏按钮 -->
          <div class="header-action">
            <h1 class="title">{{ spot.name }}</h1>
            <div class="actions">
              <!-- 收藏按钮，根据是否收藏显示不同状态 -->
              <el-button
                :type="isCollected ? 'danger' : 'default'"
                :icon="isCollected ? StarFilled : Star"
                circle
                size="large"
                @click="toggleCollect"
                :title="isCollected ? '取消收藏' : '加入收藏'"
              />
            </div>
          </div>

          <!-- 评分区域 -->
          <div class="rating-box">
            <!-- 景点评分 -->
            <div class="score">{{ spot.rating || '暂无评分' }}</div>
            <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
            <!-- 用户评分（只有登录后才显示） -->
            <div class="user-rating" v-if="userStore.token">
              <span>您的评分：</span>
              <el-rate v-model="userRating" allow-half @change="handleRate" />
            </div>
          </div>

          <el-divider />

          <!-- 景点介绍 -->
          <div class="section">
            <h3 class="section-title"><el-icon><Document /></el-icon> 景点介绍</h3>
            <p class="description">{{ spot.description || '暂无介绍' }}</p>
          </div>

          <!-- 开放时间（如果有） -->
          <div class="section" v-if="spot.open_time">
            <h3 class="section-title"><el-icon><Timer /></el-icon> 开放时间</h3>
            <p>{{ spot.open_time }}</p>
          </div>

          <!-- 门票信息（如果有） -->
          <div class="section" v-if="spot.ticket_info">
            <h3 class="section-title"><el-icon><Ticket /></el-icon> 门票信息</h3>
            <p>{{ spot.ticket_info }}</p>
          </div>

          <!-- 游玩小贴士（如果有） -->
          <div class="section" v-if="spot.tips">
            <h3 class="section-title"><el-icon><Warning /></el-icon> 游玩小贴士</h3>
            <p>{{ spot.tips }}</p>
          </div>

          <!-- 用户评论区域 -->
          <div class="section comments-section">
            <h3 class="section-title"><el-icon><ChatDotRound /></el-icon> 用户评价 ({{ comments.length }})</h3>
            <!-- 评论加载中 -->
            <div v-if="commentsLoading" class="comments-loading">
              <el-skeleton :rows="3" animated />
            </div>
            <!-- 评论列表 -->
            <div v-else-if="comments.length > 0" class="comments-list">
              <div v-for="comment in comments" :key="comment.id" class="comment-item">
                <div class="comment-header">
                  <div class="comment-user">
                    <el-avatar :size="32" :icon="User" class="avatar-icon" />
                    <span class="nickname">{{ comment.nickname || comment.username }}</span>
                  </div>
                  <div class="comment-meta">
                    <el-rate v-model="comment.rating" disabled show-score text-color="#ff9900" size="small" />
                    <span class="time">{{ formatDate(comment.created_at) }}</span>
                  </div>
                </div>
                <div class="comment-content">{{ comment.content }}</div>
                <el-divider border-style="dashed" />
              </div>
            </div>
            <!-- 暂无评论 -->
            <div v-else class="no-comments">
              <el-empty description="暂无评价，快来抢沙发吧！" :image-size="60" />
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

    <!-- 专属 AI 聊天抽屉 -->
    <el-drawer
      v-model="aiChatVisible"
      :title="`🤖 ${spot?.name} 专属导游`"
      size="400px"
      direction="rtl"
      class="spot-ai-drawer"
      :append-to-body="true"
    >
      <!-- AI 聊天容器 -->
      <div class="ai-chat-container" v-loading="aiLoading">
        <!-- 聊天消息区域 -->
        <div class="chat-messages" ref="aiMessagesContainer">
          <!-- 遍历所有消息 -->
          <div v-for="(msg, index) in aiMessages" :key="index" :class="['message', msg.role]">
            <el-avatar class="avatar" :size="32" :icon="msg.role === 'user' ? User : Service" />
            <div class="message-content">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>
              <!-- AI 回复，使用 marked 渲染 Markdown -->
              <div v-else class="text ai-reply markdown-body" v-html="formatMessage(msg.content)"></div>
            </div>
          </div>
          <!-- AI 正在输入的动画 -->
          <div v-show="isReplying" class="message assistant typing">
            <el-avatar class="avatar" :size="32" :icon="Service" />
            <div class="message-content">
              <div class="text">正在思考...<span class="dot">...</span></div>
            </div>
          </div>
        </div>

        <!-- 输入框区域 -->
        <div class="chat-input-area">
          <el-input
            v-model="aiInput"
            type="textarea"
            :rows="2"
            :placeholder="`问我关于 ${spot?.name} 的问题吧...`"
            resize="none"
            @keyup.enter.prevent="sendAIMessage"
            :disabled="isReplying"
          />
          <div class="input-actions">
            <el-button type="primary" size="small" @click="sendAIMessage" :loading="isReplying" :disabled="!aiInput.trim()">
              发送 <el-icon class="el-icon--right"><Promotion /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
// 引入路由
import { useRoute, useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'
// 引入 Markdown 解析库
import { marked } from 'marked'
// 引入 Element Plus 的图标
import {
  Location, Calendar, MapLocation, Tickets,
  Document, Timer, Ticket, Warning,
  Star, StarFilled, ChatDotRound, User, Headset, Service, Promotion
} from '@element-plus/icons-vue'
// 引入 API 接口
import { getSpotDetail, getCollections, toggleCollection, recordBehavior, getSpotComments, chatWithSpotAI } from '../../api/spots'
// 引入用户状态管理
import { useUserStore } from '../../store/user'

// 获取路由和路由参数
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 获取景点 ID
const spotId = Number(route.params.id)
// 加载状态
const loading = ref(true)
// 景点详情数据
const spot = ref<any>(null)
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
  } catch (error: any) {
    console.error('获取详情失败:', error)
    if (error.response?.status === 404) {
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
    isCollected.value = res.items.some((item: any) => item.id === spotId)
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
const comments = ref<any[]>([])
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

// AI 聊天相关逻辑
const aiChatVisible = ref(false)
const aiLoading = ref(false)
const isReplying = ref(false)
const aiInput = ref('')
// AI 消息列表，初始有一条欢迎消息
const aiMessages = ref<any[]>([
  { role: 'assistant', content: '你好！我是这个景点的专属AI导游。有什么我可以帮你的吗？' }
])
const aiMessagesContainer = ref<any>(null)
const aiSessionId = ref('')

// 切换 AI 聊天抽屉显示/隐藏
const toggleAIChat = () => {
  aiChatVisible.value = !aiChatVisible.value
}

// 使用 marked 格式化 Markdown 消息
const formatMessage = (content: string) => {
  return marked(content)
}

// 滚动到聊天底部
const scrollToBottom = async () => {
  await nextTick()
  if (aiMessagesContainer.value) {
    aiMessagesContainer.value.scrollTop = aiMessagesContainer.value.scrollHeight
  }
}

// 发送 AI 消息
const sendAIMessage = async () => {
  if (!aiInput.value.trim() || isReplying.value) return

  const userMsg = aiInput.value.trim()
  aiInput.value = ''

  // 添加用户消息到列表
  aiMessages.value.push({ role: 'user', content: userMsg })
  scrollToBottom()

  isReplying.value = true

  try {
    // 调用 AI 聊天 API
    const res = await chatWithSpotAI(spotId, {
      message: userMsg,
      session_id: aiSessionId.value
    })

    // 保存会话 ID（用于上下文连贯）
    aiSessionId.value = res.session_id
    // 添加 AI 回复到列表
    aiMessages.value.push({ role: 'assistant', content: res.reply })
  } catch (error) {
    console.error('发送消息失败:', error)
    ElMessage.error('发送消息失败，请稍后重试')
    aiMessages.value.push({ role: 'assistant', content: '抱歉，我遇到了一些问题，请稍后再试。' })
  } finally {
    isReplying.value = false
    scrollToBottom()
  }
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
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 页面头部样式 */
.page-header {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

/* 详情内容区域样式 */
.detail-content {
  margin-top: 20px;
}

/* 图片卡片样式 */
.image-card {
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
}

/* 景点图片样式 */
.spot-image {
  width: 100%;
  height: 400px;
  object-fit: cover;
  display: block;
}

/* 基本信息卡片样式 */
.basic-info-card {
  margin-bottom: 20px;
}

/* 信息项样式 */
.info-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 15px;
  line-height: 1.5;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .el-icon {
  margin-top: 3px;
  margin-right: 8px;
  color: #409EFF;
}

.label {
  color: #606266;
  width: 110px;
  flex-shrink: 0;
  font-weight: bold;
}

.value {
  color: #303133;
  flex: 1;
}

.type-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

/* 主要信息卡片样式 */
.main-info-card {
  height: 100%;
}

/* 标题和操作区域样式 */
.header-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.title {
  margin: 0;
  font-size: 28px;
  color: #303133;
}

/* 评分区域样式 */
.rating-box {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
}

.score {
  font-size: 32px;
  font-weight: bold;
  color: #ff9900;
  margin-right: 15px;
}

.user-rating {
  margin-left: auto;
  display: flex;
  align-items: center;
  color: #606266;
  font-size: 14px;
}

.user-rating span {
  margin-right: 10px;
}

/* 通用区块样式 */
.section {
  margin-bottom: 25px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 18px;
  color: #303133;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 4px solid #409EFF;
}

.section-title .el-icon {
  margin-right: 8px;
  color: #409EFF;
}

.description {
  line-height: 1.8;
  color: #606266;
  text-align: justify;
  white-space: pre-line;
}

/* 评论区域样式 */
.comments-section {
  margin-top: 30px;
}

.comment-item {
  margin-bottom: 20px;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.comment-user {
  display: flex;
  align-items: center;
}

.avatar-icon {
  margin-right: 10px;
  background-color: #409EFF;
}

.nickname {
  font-weight: bold;
  color: #303133;
}

.comment-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.time {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.comment-content {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 15px;
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
}

.fab-button {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409EFF, #79bbff);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 28px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  transition: all 0.3s ease;
}

.fab-button:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.5);
}

.fab-button.active {
  background: #909399;
  box-shadow: 0 4px 12px rgba(144, 147, 153, 0.4);
}

/* AI 抽屉样式 */
.spot-ai-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f5f7fa;
}

.message {
  display: flex;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  background-color: #409EFF;
}

.message.assistant .avatar {
  background-color: #e6a23c;
  margin-right: 12px;
}

.message.user .avatar {
  margin-left: 12px;
}

.message-content {
  max-width: 75%;
}

.text {
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
}

.message.user .text {
  background-color: #409EFF;
  color: white;
  border-top-right-radius: 0;
}

.message.assistant .text {
  background-color: white;
  color: #303133;
  border-top-left-radius: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.typing .text {
  color: #909399;
  font-style: italic;
}

.dot {
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0% { opacity: .2; }
  20% { opacity: 1; }
  100% { opacity: .2; }
}

.chat-input-area {
  padding: 15px;
  background-color: white;
  border-top: 1px solid #ebeef5;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

/* Markdown 样式 */
.markdown-body :deep(p) {
  margin: 0 0 10px 0;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}
</style>
