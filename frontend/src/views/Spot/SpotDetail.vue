<template>
  <div class="spot-detail-container" v-loading="loading">
    <el-page-header @back="goBack" class="page-header" :content="spot?.name" />

    <el-row :gutter="30" class="detail-content" v-if="spot">
      <!-- 左侧：图片和基本信息 -->
      <el-col :md="12" :lg="10">
        <el-card class="image-card" :body-style="{ padding: '0px' }">
          <img :src="spot.image_url || 'https://via.placeholder.com/600x400?text=暂无图片'" class="spot-image" />
        </el-card>

        <el-card class="basic-info-card" shadow="hover">
          <div class="info-item">
            <el-icon><Location /></el-icon>
            <span class="label">地址：</span>
            <span class="value">{{ spot.address || '暂无信息' }}</span>
          </div>
          <div class="info-item">
            <el-icon><Calendar /></el-icon>
            <span class="label">建议游玩时间：</span>
            <span class="value">{{ spot.suggest_time || '暂无信息' }}</span>
          </div>
          <div class="info-item">
            <el-icon><MapLocation /></el-icon>
            <span class="label">所属城市：</span>
            <span class="value"><el-tag>{{ spot.city }}</el-tag></span>
          </div>
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
          <div class="header-action">
            <h1 class="title">{{ spot.name }}</h1>
            <div class="actions">
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

          <div class="rating-box">
            <div class="score">{{ spot.rating || '暂无评分' }}</div>
            <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
            <!-- 用户评分 -->
            <div class="user-rating" v-if="userStore.token">
              <span>您的评分：</span>
              <el-rate v-model="userRating" allow-half @change="handleRate" />
            </div>
          </div>

          <el-divider />

          <div class="section">
            <h3 class="section-title"><el-icon><Document /></el-icon> 景点介绍</h3>
            <p class="description">{{ spot.description || '暂无介绍' }}</p>
          </div>

          <div class="section" v-if="spot.open_time">
            <h3 class="section-title"><el-icon><Timer /></el-icon> 开放时间</h3>
            <p>{{ spot.open_time }}</p>
          </div>

          <div class="section" v-if="spot.ticket_info">
            <h3 class="section-title"><el-icon><Ticket /></el-icon> 门票信息</h3>
            <p>{{ spot.ticket_info }}</p>
          </div>

          <div class="section" v-if="spot.tips">
            <h3 class="section-title"><el-icon><Warning /></el-icon> 游玩小贴士</h3>
            <p>{{ spot.tips }}</p>
          </div>

          <!-- 用户评论区域 -->
          <div class="section comments-section">
            <h3 class="section-title"><el-icon><ChatDotRound /></el-icon> 用户评价 ({{ comments.length }})</h3>
            <div v-if="commentsLoading" class="comments-loading">
              <el-skeleton :rows="3" animated />
            </div>
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
      <div class="ai-chat-container" v-loading="aiLoading">
        <div class="chat-messages" ref="aiMessagesContainer">
          <div v-for="(msg, index) in aiMessages" :key="index" :class="['message', msg.role]">
            <el-avatar class="avatar" :size="32" :icon="msg.role === 'user' ? User : Service" />
            <div class="message-content">
              <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>
              <div v-else class="text ai-reply markdown-body" v-html="formatMessage(msg.content)"></div>
            </div>
          </div>
          <div v-show="isReplying" class="message assistant typing">
            <el-avatar class="avatar" :size="32" :icon="Service" />
            <div class="message-content">
              <div class="text">正在思考...<span class="dot">...</span></div>
            </div>
          </div>
        </div>

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
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import {
  Location, Calendar, MapLocation, Tickets,
  Document, Timer, Ticket, Warning,
  Star, StarFilled, ChatDotRound, User, Headset, Service, Promotion
} from '@element-plus/icons-vue'
import { getSpotDetail, getCollections, toggleCollection, recordBehavior, getSpotComments, chatWithSpotAI } from '../../api/spots'
import { useUserStore } from '../../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const spotId = Number(route.params.id)
const loading = ref(true)
const spot = ref<any>(null)
const isCollected = ref(false)
const userRating = ref(0)
const startTime = ref(0)

// 获取景点详情
const fetchDetail = async () => {
  try {
    const res = await getSpotDetail(spotId)
    spot.value = res

    // 如果已登录，检查是否已收藏
    if (userStore.token) {
      checkCollection()
      recordUserBehavior('view') // 记录浏览行为
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

// 检查是否收藏
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

// 记录用户行为
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

const goBack = () => {
  router.back()
}

// Comments logic
const comments = ref<any[]>([])
const commentsLoading = ref(false)

const fetchComments = async () => {
  commentsLoading.value = true
  try {
    const res = await getSpotComments(spotId)
    comments.value = res.items || []
  } catch (error) {
    console.error('Failed to fetch comments:', error)
  } finally {
    commentsLoading.value = false
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

// AI Chat logic
const aiChatVisible = ref(false)
const aiLoading = ref(false)
const isReplying = ref(false)
const aiInput = ref('')
const aiMessages = ref<any[]>([
  { role: 'assistant', content: '你好！我是这个景点的专属AI导游。有什么我可以帮你的吗？' }
])
const aiMessagesContainer = ref<any>(null)
const aiSessionId = ref('')

const toggleAIChat = () => {
  aiChatVisible.value = !aiChatVisible.value
}

const formatMessage = (content: string) => {
  return marked(content)
}

const scrollToBottom = async () => {
  await nextTick()
  if (aiMessagesContainer.value) {
    aiMessagesContainer.value.scrollTop = aiMessagesContainer.value.scrollHeight
  }
}

const sendAIMessage = async () => {
  if (!aiInput.value.trim() || isReplying.value) return

  const userMsg = aiInput.value.trim()
  aiInput.value = ''

  aiMessages.value.push({ role: 'user', content: userMsg })
  scrollToBottom()

  isReplying.value = true

  try {
    const res = await chatWithSpotAI(spotId, {
      message: userMsg,
      session_id: aiSessionId.value
    })

    aiSessionId.value = res.session_id
    aiMessages.value.push({ role: 'assistant', content: res.reply })
  } catch (error) {
    console.error('Failed to send message:', error)
    ElMessage.error('发送消息失败，请稍后重试')
    aiMessages.value.push({ role: 'assistant', content: '抱歉，我遇到了一些问题，请稍后再试。' })
  } finally {
    isReplying.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  fetchDetail()
  fetchComments()
  startTime.value = Date.now()
})

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
.spot-detail-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.detail-content {
  margin-top: 20px;
}

.image-card {
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
}

.spot-image {
  width: 100%;
  height: 400px;
  object-fit: cover;
  display: block;
}

.basic-info-card {
  margin-bottom: 20px;
}

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

.main-info-card {
  height: 100%;
}

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

/* AI Chat Fab */
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

/* AI Drawer */
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