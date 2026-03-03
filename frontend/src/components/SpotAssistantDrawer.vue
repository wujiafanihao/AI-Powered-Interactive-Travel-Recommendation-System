<template>
  <el-drawer
    v-model="visibleProxy"
    :title="title"
    size="420px"
    direction="rtl"
    class="spot-assistant-drawer"
    :append-to-body="true"
  >
    <div class="assistant-chat-container">
      <div class="assistant-messages" ref="messagesContainer">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['assistant-message', msg.role]"
        >
          <el-avatar
            class="avatar"
            :size="36"
            :icon="msg.role === 'user' ? User : Service"
          />

          <div class="message-content">
            <div v-if="msg.role === 'user'" class="bubble user-bubble">
              {{ msg.content }}
            </div>

            <div v-else class="bubble assistant-bubble">
              <div
                v-if="msg.content"
                class="markdown-body"
                v-html="formatMessage(msg.content)"
              ></div>

              <div v-if="msg.intent" class="intent-line">
                <el-tag size="small" type="info">{{ msg.intent }}</el-tag>
              </div>

              <div v-if="msg.searchState === 'loading'" class="cards-state loading">
                <el-skeleton :rows="2" animated />
                <span class="state-text">正在为你检索景点...</span>
              </div>

              <div v-else-if="msg.searchState === 'empty'" class="cards-state empty">
                <el-empty description="没有找到匹配景点" :image-size="56" />
              </div>

              <div v-else-if="msg.searchState === 'error'" class="cards-state error">
                <el-result
                  icon="error"
                  title="搜索失败"
                  sub-title="请稍后重试或换个描述"
                />
              </div>

              <div v-if="msg.spots && msg.spots.length > 0" class="spot-cards-section">
                <div class="spot-cards-scroll">
                  <el-card
                    v-for="spot in msg.spots"
                    :key="spot.id"
                    class="spot-card"
                    :body-style="{ padding: '0px' }"
                    shadow="hover"
                    @click="goToSpot(spot.id, msg.source)"
                  >
                    <img
                      :src="cleanUrl(spot.image_url) || 'https://via.placeholder.com/320x180?text=暂无图片'"
                      class="spot-cover"
                      :alt="spot.name"
                    />

                    <div class="spot-body">
                      <h4 class="spot-name" :title="spot.name">{{ spot.name }}</h4>
                      <p class="spot-brief">{{ spot.brief || '系统推荐景点' }}</p>

                      <div class="spot-meta">
                        <span class="city">
                          <el-icon><Location /></el-icon>
                          {{ spot.city || '未知城市' }}
                        </span>
                        <span
                          v-if="spot.rating !== undefined && spot.rating !== null"
                          class="rating"
                        >
                          <el-icon><StarFilled /></el-icon>
                          {{ typeof spot.rating === 'number' ? spot.rating.toFixed(1) : spot.rating }}
                        </span>
                      </div>

                      <div v-if="spot.tags && spot.tags.length > 0" class="tag-row">
                        <el-tag
                          v-for="tag in spot.tags"
                          :key="tag"
                          size="small"
                          type="info"
                          class="tag-item"
                        >
                          {{ tag }}
                        </el-tag>
                      </div>
                    </div>
                  </el-card>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-show="isReplying && isSpotMode" class="assistant-message assistant typing">
          <el-avatar class="avatar" :size="36" :icon="Service" />
          <div class="message-content">
            <div class="bubble assistant-bubble typing-bubble">
              正在思考<span class="dot">...</span>
            </div>
          </div>
        </div>
      </div>

      <div class="assistant-input-area">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          :placeholder="inputPlaceholder"
          resize="none"
          :disabled="isReplying"
          @keyup.enter.prevent="sendMessage"
        />

        <div class="input-actions">
          <span class="hint">按 Enter 发送，Shift + Enter 换行</span>
          <el-button
            type="primary"
            size="small"
            :loading="isReplying"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          >
            发送
            <el-icon class="el-icon--right"><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Service, Promotion, Location, StarFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { chatWithAI, chatWithSpotAI } from '../api/spots'

type AssistantMode = 'search' | 'spot'
type SearchState = 'loading' | 'empty' | 'error'

interface SpotCard {
  id: number
  spot_id?: number
  name: string
  brief?: string
  tags?: string[]
  image_url?: string
  city?: string
  rating?: number | string
}

interface ChatItem {
  role: 'user' | 'assistant'
  content: string
  intent?: string
  spots?: SpotCard[]
  searchState?: SearchState
  source?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    mode?: AssistantMode
    spotId?: number | null
    title?: string
    welcomeMessage?: string
    inputPlaceholder?: string
  }>(),
  {
    mode: 'search',
    spotId: null,
    title: 'AI 智能助手',
    welcomeMessage: '你好！我是 TravelAI 智能助手，你可以直接告诉我想去哪里、和谁去、什么季节出行。',
    inputPlaceholder: '例如：周末在杭州找适合亲子游的景点'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  recommendEvent: [payload: { spot_id: number; event_type: 'exposure' | 'click'; source?: string }]
}>()

const router = useRouter()

const visibleProxy = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

const isSpotMode = computed(() => props.mode === 'spot')
const inputMessage = ref('')
const isReplying = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const sessionId = ref('')

const createWelcomeMessage = (): ChatItem => ({
  role: 'assistant',
  content: props.welcomeMessage
})

const messages = ref<ChatItem[]>([createWelcomeMessage()])

watch(
  () => visibleProxy.value,
  (visible) => {
    if (visible) {
      scrollToBottom()
    }
  }
)

watch(
  () => [props.mode, props.spotId, props.welcomeMessage] as const,
  () => {
    if (!visibleProxy.value) {
      sessionId.value = ''
      inputMessage.value = ''
      messages.value = [createWelcomeMessage()]
    }
  }
)

const formatMessage = (content: string) => {
  if (!content) return ''
  const parsed = marked.parse(content)
  return (parsed instanceof Promise ? '' : parsed) as string
}

const cleanUrl = (url?: string) => {
  if (!url) return ''
  return url.trim().replace(/[` ]/g, '')
}

const normalizeSpots = (raw: unknown): SpotCard[] => {
  if (!Array.isArray(raw)) return []

  return raw
    .map((item: unknown) => {
      const obj = item as Record<string, unknown>
      const spotId = Number(obj.spot_id ?? obj.id ?? 0)
      const rawTags = Array.isArray(obj.tags) ? obj.tags : []

      return {
        id: spotId,
        spot_id: spotId,
        name: String(obj.name || '未知景点'),
        brief: String(obj.brief || obj.description || '').slice(0, 50),
        tags: rawTags.slice(0, 3).map((tag) => String(tag)),
        image_url: typeof obj.image_url === 'string' ? obj.image_url : '',
        city: typeof obj.city === 'string' ? obj.city : '',
        rating: obj.rating as number | string | undefined
      }
    })
    .filter((item: SpotCard) => item.id > 0)
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const normalizeRecommendSource = (source?: string, intent?: string) => {
  const raw = String(source || intent || '').trim()
  if (!raw) return 'ai-search'
  if (['scene', 'recommend-tab', 'spot-detail', 'ai-search'].includes(raw)) return raw
  if (raw === 'search') return 'ai-search'
  if (raw === 'cf') return 'collaborative'
  if (raw === 'cb') return 'content'
  return raw
}

const goToSpot = (id: number, source?: string) => {
  if (!id) return
  if (!isSpotMode.value) {
    emit('recommendEvent', {
      spot_id: id,
      event_type: 'click',
      source: normalizeRecommendSource(source)
    })
  }
  visibleProxy.value = false
  router.push(`/spot/${id}`)
}

const sendMessage = async (e?: KeyboardEvent) => {
  if (e?.shiftKey) return

  const text = inputMessage.value.trim()
  if (!text || isReplying.value) return

  if (isSpotMode.value && !props.spotId) {
    ElMessage.warning('景点信息缺失，暂时无法提问')
    return
  }

  messages.value.push({ role: 'user', content: text })
  inputMessage.value = ''
  isReplying.value = true
  await scrollToBottom()

  const placeholder: ChatItem | null = !isSpotMode.value
    ? { role: 'assistant', content: '', searchState: 'loading' }
    : null

  if (placeholder) {
    messages.value.push(placeholder)
    await scrollToBottom()
  }

  try {
    const res = isSpotMode.value
      ? await chatWithSpotAI(props.spotId || 0, { message: text, session_id: sessionId.value || undefined })
      : await chatWithAI({ message: text, session_id: sessionId.value || undefined })

    sessionId.value = res.session_id || sessionId.value

    const cards = normalizeSpots(res.spots)
    const normalizedSource = normalizeRecommendSource(
      typeof res.source === 'string' ? res.source : undefined,
      typeof res.intent === 'string' ? res.intent : undefined
    )

    const assistantMessage: ChatItem = {
      role: 'assistant',
      content: res.reply || '我整理了一些建议给你。',
      intent: res.intent,
      spots: cards,
      source: normalizedSource
    }

    if (!isSpotMode.value && cards.length > 0) {
      const source = assistantMessage.source
      cards.forEach((card) => {
        emit('recommendEvent', {
          spot_id: card.id,
          event_type: 'exposure',
          source
        })
      })
    }

    if (!isSpotMode.value && res.intent === 'search' && cards.length === 0) {
      assistantMessage.searchState = 'empty'
      assistantMessage.content = res.reply || '我这次没有找到完全匹配的景点，你可以换个关键词再试试。'
    }

    if (placeholder) {
      messages.value.splice(messages.value.length - 1, 1, assistantMessage)
    } else {
      messages.value.push(assistantMessage)
    }
  } catch (error) {
    console.error('AI 对话失败:', error)

    const errorMessage: ChatItem = {
      role: 'assistant',
      content: isSpotMode.value
        ? '抱歉，我暂时无法回答这个问题，请稍后重试。'
        : '抱歉，我暂时无法完成检索，请稍后再试。',
      searchState: !isSpotMode.value ? 'error' : undefined
    }

    if (placeholder) {
      messages.value.splice(messages.value.length - 1, 1, errorMessage)
    } else {
      messages.value.push(errorMessage)
    }

    ElMessage.error('AI 服务暂时不可用，请稍后重试')
  } finally {
    isReplying.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
/* ==================== 抽屉整体 ==================== */
.spot-assistant-drawer :deep(.el-drawer__header) {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  padding: 16px 20px;
  margin-bottom: 0;
}

.spot-assistant-drawer :deep(.el-drawer__body) {
  padding: 0;
}

.assistant-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ==================== 消息列表区域 ==================== */
.assistant-messages {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
  background: linear-gradient(180deg, #f5f7fa 0%, #f0f2f5 100%);
}

/* 每条消息 */
.assistant-message {
  display: flex;
  margin-bottom: 18px;
  align-items: flex-start;
}

.assistant-message.user {
  flex-direction: row-reverse;
}

/* 头像 */
.avatar {
  margin: 0 8px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
}

.assistant-message.user .avatar {
  background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%);
}

/* ==================== 消息气泡 ==================== */
/* 关键修复：允许消息内容占满更多宽度，避免文字过于拥挤 */
.message-content {
  max-width: 85%;
  min-width: 0;
}

.bubble {
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.75;
  /* 关键修复：确保中文和长文本正确换行 */
  word-break: break-word;
  overflow-wrap: break-word;
}

.user-bubble {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: white;
  border-radius: 14px 4px 14px 14px;
}

.assistant-bubble {
  background: white;
  color: #303133;
  border-radius: 4px 14px 14px 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  /* 关键修复：防止内部元素溢出 */
  overflow: hidden;
}

/* ==================== Markdown 正文 ==================== */
.markdown-body {
  word-break: break-word;
  overflow-wrap: break-word;
}

.markdown-body :deep(p) {
  margin: 0 0 8px 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 18px;
  margin: 4px 0 8px;
}

.markdown-body :deep(li) {
  margin-bottom: 2px;
}

/* ==================== 意图标签 ==================== */
.intent-line {
  margin-top: 8px;
}

/* ==================== 加载 / 空 / 错误状态 ==================== */
.cards-state {
  margin-top: 10px;
}

.cards-state.loading {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.state-text {
  font-size: 12px;
  color: #909399;
}

.cards-state.error :deep(.el-result) {
  padding: 0;
}

.cards-state.error :deep(.el-result__title) {
  font-size: 14px;
}

.cards-state.error :deep(.el-result__subtitle) {
  font-size: 12px;
}

/* ==================== 景点推荐卡片区域 ==================== */
.spot-cards-section {
  margin-top: 12px;
  border-top: 1px dashed #dcdfe6;
  padding-top: 12px;
}

/* 关键修复：改为纵向堆叠排列，不再横向滚动（窄抽屉内横向滚动体验差） */
.spot-cards-scroll {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 关键修复：卡片占满气泡宽度，不再固定 210px */
.spot-card {
  flex: none;
  width: 100%;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
  overflow: hidden;
}

.spot-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12) !important;
}

/* 景点封面图 */
.spot-cover {
  width: 100%;
  height: 120px;
  object-fit: cover;
  display: block;
}

/* 景点信息区 */
.spot-body {
  padding: 10px 12px;
}

.spot-name {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spot-brief {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 城市 + 评分 */
.spot-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.spot-meta .city,
.spot-meta .rating {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.spot-meta .rating {
  color: #e6a23c;
  font-weight: 600;
}

/* 标签行 */
.tag-row {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.tag-item {
  margin: 0;
  border-radius: 4px;
}

/* ==================== 正在输入动画 ==================== */
.typing-bubble {
  color: #909399;
  background: #f4f4f5;
  font-style: italic;
}

.dot {
  animation: blink 1.5s infinite;
}

@keyframes blink {
  0%   { opacity: .2; }
  20%  { opacity: 1; }
  100% { opacity: .2; }
}

/* ==================== 底部输入区域 ==================== */
.assistant-input-area {
  padding: 14px;
  background: #fff;
  border-top: 1px solid #ebeef5;
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
</style>
