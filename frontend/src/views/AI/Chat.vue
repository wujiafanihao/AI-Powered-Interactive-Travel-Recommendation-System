<template>
  <!-- AI 聊天页面容器 -->
  <div class="chat-container">
    <el-container class="chat-layout">
      <!-- 左侧：历史会话列表 -->
      <el-aside width="250px" class="chat-sidebar">
        <div class="sidebar-header">
          <!-- 新对话按钮 -->
          <el-button type="primary" class="new-chat-btn" @click="startNewChat">
            <el-icon><Plus /></el-icon> 新对话
          </el-button>
        </div>
        <!-- 会话列表菜单 -->
        <el-menu :default-active="currentSessionId" class="session-menu" @select="handleSessionSelect">
          <el-menu-item v-for="session in sessions" :key="session.id" :index="session.id">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>
              <!-- 会话标题，显示在菜单中 -->
              <span class="session-title" :title="session.title">{{ session.title }}</span>
              <!-- 删除会话图标，鼠标悬停时显示 -->
              <el-icon class="delete-icon" @click.stop="handleDeleteSession(session.id)"><Delete /></el-icon>
            </template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 右侧：聊天内容区 -->
      <el-main class="chat-main" v-loading="loading">
        <!-- 聊天消息区域 -->
        <div class="chat-messages" ref="messagesContainer">
          <!-- 遍历所有消息，根据角色显示不同样式 -->
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <el-avatar class="avatar" :size="40" :icon="msg.role === 'user' ? User : Service" />
            <div class="message-content">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>

              <!-- AI 回复 -->
              <div v-else class="ai-reply">
                <!-- AI 回复的文本内容，使用 Markdown 渲染 -->
                <div class="text markdown-body" v-html="formatMessage(msg.content)"></div>

                <!-- 意图标签（如果有） -->
                <div v-if="msg.intent" class="intent-tag">
                  <el-tag size="small" type="info">{{ msg.intent }}</el-tag>
                </div>

                <!-- 推荐景点卡片（如果有） -->
                <div v-if="msg.spots && msg.spots.length > 0" class="spot-cards">
                  <el-row :gutter="10">
                    <!-- 只显示前 3 个景点 -->
                    <el-col :span="8" v-for="spot in msg.spots.slice(0, 3)" :key="spot.id">
                      <el-card class="spot-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToSpot(spot.id)">
                        <img :src="spot.image_url || 'https://via.placeholder.com/150x100?text=暂无图片'" class="spot-img" />
                        <div class="spot-info">
                          <div class="spot-name" :title="spot.name">{{ spot.name }}</div>
                          <div class="spot-rating">
                            <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
                          </div>
                          <div v-if="spot.hybrid_score" class="spot-hybrid-score">
                            🔥 混合得分: {{ Number(spot.hybrid_score).toFixed(0) }}
                          </div>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                  <!-- 如果有超过 3 个景点，显示查看全部按钮 -->
                  <div class="more-spots" v-if="msg.spots.length > 3">
                    <el-button link type="primary" @click="showMoreSpots(msg.spots)">查看全部 {{ msg.spots.length }} 个推荐景点 >></el-button>
                  </div>
                </div>

                <!-- 来源引用（如果有） -->
                <div v-if="msg.sources && msg.sources.length > 0" class="sources">
                  <div class="source-title">参考来源：</div>
                  <ul>
                    <li v-for="(source, i) in msg.sources" :key="i">
                      <a :href="`/spot/${source.id}`" target="_blank">{{ source.name }} ({{ source.city }})</a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
          <!-- AI 正在输入的动画 -->
          <div v-show="isReplying" class="message assistant typing">
            <el-avatar class="avatar" :size="40" :icon="Service" />
            <div class="message-content">
              <div class="text">正在思考...<span class="dot">...</span></div>
            </div>
          </div>
        </div>

        <!-- 底部输入框 -->
        <div class="chat-input-area">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :rows="3"
            placeholder="问问我：'带孩子去哪玩比较好？' 或 '北京有哪些好玩的景点？'"
            resize="none"
            @keyup.enter.prevent="sendMessage"
            :disabled="isReplying"
          />
          <div class="input-actions">
            <span class="hint">按 Enter 发送，Shift + Enter 换行</span>
            <el-button type="primary" @click="sendMessage" :loading="isReplying" :disabled="!inputMessage.trim()">
              发送 <el-icon class="el-icon--right"><Promotion /></el-icon>
            </el-button>
          </div>
        </div>
      </el-main>
    </el-container>

    <!-- 更多景点抽屉 -->
    <el-drawer v-model="drawerVisible" title="推荐景点列表" size="400px">
      <div class="drawer-spot-list">
        <el-card v-for="spot in currentSpots" :key="spot.id" class="drawer-spot-card" @click="goToSpot(spot.id)">
           <div class="drawer-spot-content">
            <img :src="spot.image_url || 'https://via.placeholder.com/100x100?text=暂无图片'" class="drawer-spot-img" />
            <div class="drawer-spot-info">
              <h4>{{ spot.name }}</h4>
              <p>{{ spot.city }}</p>
              <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
              <div v-if="spot.hybrid_score" class="drawer-spot-hybrid-score">
                🔥 混合得分: {{ Number(spot.hybrid_score).toFixed(0) }}
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, onMounted, nextTick } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示和确认框
import { ElMessage, ElMessageBox } from 'element-plus'
// 引入 Element Plus 的图标
import { Plus, ChatDotRound, User, Service, Promotion, Delete } from '@element-plus/icons-vue'
// 引入 API 接口
import { getChatHistory, chatWithAI, deleteChatSession } from '../../api/spots'
// 引入用户状态管理
import { useUserStore } from '../../store/user'
// 引入 Markdown 解析库
import { marked } from 'marked'

// 获取路由实例
const router = useRouter()
const userStore = useUserStore()

// 状态定义
const loading = ref(false)
const isReplying = ref(false)
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const messages = ref<any[]>([])
const currentSessionId = ref('')
const sessions = ref<{id: string, title: string}[]>([])

// 更多景点抽屉相关状态
const drawerVisible = ref(false)
const currentSpots = ref<any[]>([])

// 获取历史会话列表（简化版：从聊天历史中提取）
const fetchSessions = async () => {
  try {
    const res = await getChatHistory()

    // 提取不重复的 session_id
    const sessionMap = new Map()
    res.messages.forEach((msg: any) => {
      if (msg.session_id && !sessionMap.has(msg.session_id)) {
        sessionMap.set(msg.session_id, {
          id: msg.session_id,
          title: msg.content.substring(0, 15) + '...' // 用第一条消息做标题
        })
      }
    })

    sessions.value = Array.from(sessionMap.values())
    if (sessions.value.length > 0 && !currentSessionId.value) {
      const firstSessionId = sessions.value[0]?.id
      if (firstSessionId) {
        currentSessionId.value = firstSessionId
        loadHistory(currentSessionId.value)
      }
    } else if (sessions.value.length === 0) {
      startNewChat()
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
  }
}

// 加载指定会话的历史记录
const loadHistory = async (sessionId: string) => {
  loading.value = true
  try {
    const res = await getChatHistory({ session_id: sessionId })
    messages.value = res.messages
    scrollToBottom()
  } catch (error) {
    console.error('加载历史记录失败:', error)
  } finally {
    loading.value = false
  }
}

// 开始新对话
const startNewChat = () => {
  // 生成简单的 UUID 作为新会话 ID
  currentSessionId.value = 'session_' + Date.now() + '_' + Math.floor(Math.random() * 1000)
  messages.value = [{
    role: 'assistant',
    content: '你好！我是 TravelAI 智能助手。你可以问我：\n- 帮我找找北京适合带孩子去玩的景点\n- 我想去海边度蜜月，有什么推荐？\n- 故宫博物院要怎么预约门票？'
  }]

  // 添加到侧边栏
  sessions.value.unshift({
    id: currentSessionId.value,
    title: '新对话'
  })
}

// 切换会话
const handleSessionSelect = (index: string) => {
  currentSessionId.value = index
  loadHistory(index)
}

// 删除会话
const handleDeleteSession = async (sessionId: string) => {
  try {
    // 显示确认对话框
    await ElMessageBox.confirm('确定要删除这个会话吗？删除后无法恢复。', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    // 调用删除 API
    await deleteChatSession(sessionId)
    ElMessage.success('会话已删除')

    // 更新本地会话列表
    sessions.value = sessions.value.filter(s => s.id !== sessionId)

    // 如果删除的是当前会话
    if (currentSessionId.value === sessionId) {
      if (sessions.value.length > 0 && sessions.value[0]) {
        // 切换到第一个会话
        handleSessionSelect(sessions.value[0].id)
      } else {
        // 没有会话了，创建新会话
        startNewChat()
      }
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除会话失败:', error)
      ElMessage.error('删除失败，请稍后重试')
    }
  }
}

// 发送消息
const sendMessage = async (e?: KeyboardEvent) => {
  // 处理 Shift+Enter 换行
  if (e && e.shiftKey) return

  const text = inputMessage.value.trim()
  if (!text || isReplying.value) return

  // 更新当前对话标题（如果是新对话）
  const currentSession = sessions.value.find(s => s.id === currentSessionId.value)
  if (currentSession && currentSession.title === '新对话') {
    currentSession.title = text.substring(0, 15) + '...'
  }

  // 添加用户消息到列表
  messages.value.push({ role: 'user', content: text })
  inputMessage.value = ''
  isReplying.value = true
  scrollToBottom()

  try {
    // 调用 AI 聊天 API
    const res = await chatWithAI({
      message: text,
      session_id: currentSessionId.value
    })

    // 添加 AI 回复到列表
    messages.value.push({
      role: 'assistant',
      content: res.reply,
      intent: res.intent,
      spots: res.spots,
      sources: res.sources
    })
  } catch (error) {
    console.error('发送消息失败:', error)
    messages.value.push({
      role: 'assistant',
      content: '抱歉，网络开小差了，请稍后再试。'
    })
  } finally {
    isReplying.value = false
    scrollToBottom()
  }
}

// 使用 marked 格式化 Markdown 消息
const formatMessage = (content: string) => {
  if (!content) return ''
  const result = marked.parse(content)
  return (result instanceof Promise ? '' : result) as string
}

// 滚动到聊天底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 跳转到景点详情页
const goToSpot = (id: number) => {
  const spotId = Number(id)
  // 防御 NaN：无效 ID 不跳转
  if (Number.isNaN(spotId) || spotId <= 0) return
  router.push(`/spot/${spotId}`)
}

// 显示更多景点
const showMoreSpots = (spots: any[]) => {
  currentSpots.value = spots
  drawerVisible.value = true
}

// 组件挂载时执行
onMounted(() => {
  // 如果未登录，跳转到登录页
  if (!userStore.token) {
    ElMessage.warning('请先登录后使用AI帮搜')
    router.push('/login?redirect=/ai')
    return
  }
  // 获取历史会话
  fetchSessions()
})
</script>

<style scoped>
/* AI 聊天页面容器样式 */
.chat-container {
  height: calc(100vh - 60px);
  background: linear-gradient(180deg, #f0f4f8 0%, #e9ecef 50%, #f8f9fa 100%);
  padding: 20px;
  box-sizing: border-box;
  animation: fadeIn 0.5s ease;
}

/* 聊天布局样式 */
.chat-layout {
  height: 100%;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* 聊天侧边栏样式 */
.chat-sidebar {
  border-right: 1px solid #e4e7ed;
  background: linear-gradient(180deg, #fafafa 0%, #f5f7fa 100%);
  display: flex;
  flex-direction: column;
}

/* 侧边栏头部样式 */
.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.new-chat-btn {
  width: 100%;
  border-radius: 12px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.3);
}

/* 会话菜单样式 */
.session-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  background-color: transparent;
}

/* 会话标题样式 */
.session-title {
  margin-left: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  width: 120px;
}

/* 删除图标样式 */
.delete-icon {
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s;
}

/* 菜单项悬停时显示删除图标 */
.el-menu-item:hover .delete-icon {
  opacity: 1;
  color: #f56c6c;
}

/* 聊天主区域样式 */
.chat-main {
  display: flex;
  flex-direction: column;
  padding: 0;
  height: 100%;
}

/* 聊天消息区域样式 */
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

/* 消息样式 */
.message {
  display: flex;
  margin-bottom: 24px;
  animation: fadeInUp 0.5s cubic-bezier(0.23, 1, 0.32, 1);
}

/* 用户消息样式（反向排列） */
.message.user {
  flex-direction: row-reverse;
}

/* 头像样式 */
.avatar {
  flex-shrink: 0;
  margin: 0 15px;
  background: linear-gradient(135deg, #409EFF 0%, #66b1ff 100%);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

/* 用户头像颜色 */
.message.user .avatar {
  background: linear-gradient(135deg, #67C23A 0%, #85ce61 100%);
  box-shadow: 0 4px 12px rgba(103, 194, 58, 0.3);
}

/* 消息内容区域样式 */
.message-content {
  max-width: 70%;
}

/* 用户消息文本样式 */
.message.user .text {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  padding: 14px 18px;
  border-radius: 16px 4px 16px 16px;
  word-break: break-all;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
  transition: all 0.3s ease;
}

.message.user .text:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.3);
}

/* AI 回复样式 */
.message.assistant .ai-reply {
  background: white;
  border: 1px solid #e4e7ed;
  padding: 18px;
  border-radius: 4px 16px 16px 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.message.assistant .ai-reply:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

/* Markdown 文本样式 */
.markdown-body {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
}

/* 覆盖一些默认 markdown 样式 */
.markdown-body :deep(p) {
  margin-top: 0;
  margin-bottom: 10px;
}
.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

/* 意图标签样式 */
.intent-tag {
  margin-top: 10px;
  margin-bottom: 10px;
}

/* 景点卡片样式 */
.spot-cards {
  margin-top: 15px;
  border-top: 1px dashed #e4e7ed;
  padding-top: 15px;
}

.spot-card {
  cursor: pointer;
  height: 100%;
  border-radius: 6px;
  transition: all 0.2s;
}

.spot-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
}

.spot-img {
  width: 100%;
  height: 100px;
  object-fit: cover;
}

.spot-info {
  padding: 8px;
}

.spot-name {
  font-size: 13px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 5px;
}

.spot-hybrid-score {
  font-size: 11px;
  color: #f56c6c;
  margin-top: 4px;
}

.more-spots {
  text-align: center;
  margin-top: 10px;
}

/* 来源引用样式 */
.sources {
  margin-top: 15px;
  font-size: 12px;
  color: #909399;
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
}

.source-title {
  font-weight: bold;
  margin-bottom: 5px;
}

.sources ul {
  margin: 0;
  padding-left: 20px;
}

.sources a {
  color: #409EFF;
  text-decoration: none;
}

.sources a:hover {
  text-decoration: underline;
}

/* 正在输入样式 */
.typing .text {
  background-color: #f4f4f5;
  padding: 12px 16px;
  border-radius: 0 8px 8px 8px;
  color: #909399;
}

/* 淡入动画 */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 输入框区域样式 */
.chat-input-area {
  padding: 24px;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
  border-top: 1px solid #e4e7ed;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.hint {
  font-size: 12px;
  color: #909399;
}

/* 更多景点抽屉样式 */
.drawer-spot-list {
  padding: 10px;
}

.drawer-spot-card {
  margin-bottom: 15px;
  cursor: pointer;
}

.drawer-spot-content {
  display: flex;
}

.drawer-spot-img {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  margin-right: 15px;
}

.drawer-spot-info h4 {
  margin: 0 0 5px 0;
  font-size: 16px;
}

.drawer-spot-info p {
  margin: 0 0 10px 0;
  font-size: 13px;
  color: #909399;
}

.drawer-spot-hybrid-score {
  font-size: 11px;
  color: #f56c6c;
  margin-top: 5px;
}
</style>
