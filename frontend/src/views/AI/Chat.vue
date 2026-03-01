<template>
  <div class="chat-container">
    <el-container class="chat-layout">
      <!-- 左侧：历史会话列表 -->
      <el-aside width="250px" class="chat-sidebar">
        <div class="sidebar-header">
          <el-button type="primary" class="new-chat-btn" @click="startNewChat">
            <el-icon><Plus /></el-icon> 新对话
          </el-button>
        </div>
        <el-menu :default-active="currentSessionId" class="session-menu" @select="handleSessionSelect">
          <el-menu-item v-for="session in sessions" :key="session.id" :index="session.id">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>
              <span class="session-title" :title="session.title">{{ session.title }}</span>
              <el-icon class="delete-icon" @click.stop="handleDeleteSession(session.id)"><Delete /></el-icon>
            </template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 右侧：聊天内容区 -->
      <el-main class="chat-main" v-loading="loading">
        <div class="chat-messages" ref="messagesContainer">
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <el-avatar class="avatar" :size="40" :icon="msg.role === 'user' ? User : Service" />
            <div class="message-content">
              <!-- 用户消息 -->
              <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>

              <!-- AI 回复 -->
              <div v-else class="ai-reply">
                <div class="text markdown-body" v-html="formatMessage(msg.content)"></div>

                <!-- 意图标签 -->
                <div v-if="msg.intent" class="intent-tag">
                  <el-tag size="small" type="info">{{ msg.intent }}</el-tag>
                </div>

                <!-- 推荐景点卡片 -->
                <div v-if="msg.spots && msg.spots.length > 0" class="spot-cards">
                  <el-row :gutter="10">
                    <el-col :span="8" v-for="spot in msg.spots.slice(0, 3)" :key="spot.id">
                      <el-card class="spot-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToSpot(spot.id)">
                        <img :src="spot.image_url || 'https://via.placeholder.com/150x100?text=暂无图片'" class="spot-img" />
                        <div class="spot-info">
                          <div class="spot-name" :title="spot.name">{{ spot.name }}</div>
                          <div class="spot-rating"><el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" /></div>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                  <div class="more-spots" v-if="msg.spots.length > 3">
                    <el-button link type="primary" @click="showMoreSpots(msg.spots)">查看全部 {{ msg.spots.length }} 个推荐景点 >></el-button>
                  </div>
                </div>

                <!-- 来源引用 -->
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
            </div>
          </div>
        </el-card>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, ChatDotRound, User, Service, Promotion, Delete } from '@element-plus/icons-vue'
import { getChatHistory, chatWithAI, deleteChatSession } from '../../api/spots'
import { useUserStore } from '../../store/user'
import { marked } from 'marked'
import { ElMessageBox } from 'element-plus'

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

const drawerVisible = ref(false)
const currentSpots = ref<any[]>([])

// 获取历史会话列表（简化版：从本地或最近一条记录提取）
const fetchSessions = async () => {
  // 实际应该有个专门的 /chat/sessions 接口，这里用 /chat/history 模拟
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

// 新对话
const startNewChat = () => {
  // 生成简单的UUID作为新会话ID
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
    await ElMessageBox.confirm('确定要删除这个会话吗？删除后无法恢复。', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

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

    // 更新当前对话标题
    const currentSession = sessions.value.find(s => s.id === currentSessionId.value)
    if (currentSession && currentSession.title === '新对话') {
      currentSession.title = text.substring(0, 15) + '...'
    }

    // 添加用户消息
    messages.value.push({ role: 'user', content: text })
    inputMessage.value = ''
    isReplying.value = true
    scrollToBottom()

    try {
      const res = await chatWithAI({
        message: text,
        session_id: currentSessionId.value
      })

      // 添加 AI 回复
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

  // 格式化 Markdown
  const formatMessage = (content: string) => {
    if (!content) return ''
    const result = marked.parse(content)
    return (result instanceof Promise ? '' : result) as string
  }

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const goToSpot = (id: number) => {
  router.push(`/spot/${id}`)
}

const showMoreSpots = (spots: any[]) => {
  currentSpots.value = spots
  drawerVisible.value = true
}

onMounted(() => {
  if (!userStore.token) {
    ElMessage.warning('请先登录后使用AI帮搜')
    router.push('/login?redirect=/ai')
    return
  }
  fetchSessions()
})
</script>

<style scoped>
.chat-container {
  height: calc(100vh - 60px); /* 减去顶部导航高度 */
  background-color: #f5f7fa;
  padding: 20px;
  box-sizing: border-box;
}

.chat-layout {
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.chat-sidebar {
  border-right: 1px solid #e4e7ed;
  background-color: #fafafa;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.new-chat-btn {
  width: 100%;
}

.session-menu {
  flex: 1;
  overflow-y: auto;
  border-right: none;
  background-color: transparent;
}

.session-title {
  margin-left: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  width: 120px;
}

.delete-icon {
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s;
}

.el-menu-item:hover .delete-icon {
  opacity: 1;
  color: #f56c6c;
}

.chat-main {
  display: flex;
  flex-direction: column;
  padding: 0;
  height: 100%;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.message {
  display: flex;
  margin-bottom: 20px;
  animation: fadeIn 0.3s ease;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
  margin: 0 15px;
  background-color: #409EFF;
}

.message.user .avatar {
  background-color: #67C23A;
}

.message-content {
  max-width: 70%;
}

.message.user .text {
  background-color: #ecf5ff;
  color: #303133;
  padding: 12px 16px;
  border-radius: 8px 0 8px 8px;
  word-break: break-all;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.message.assistant .ai-reply {
  background-color: #fff;
  border: 1px solid #ebeef5;
  padding: 15px;
  border-radius: 0 8px 8px 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

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

.intent-tag {
  margin-top: 10px;
  margin-bottom: 10px;
}

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

.more-spots {
  text-align: center;
  margin-top: 10px;
}

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

.typing .text {
  background-color: #f4f4f5;
  padding: 12px 16px;
  border-radius: 0 8px 8px 8px;
  color: #909399;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-input-area {
  padding: 20px;
  background-color: #fff;
  border-top: 1px solid #e4e7ed;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

.hint {
  font-size: 12px;
  color: #909399;
}

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
</style>