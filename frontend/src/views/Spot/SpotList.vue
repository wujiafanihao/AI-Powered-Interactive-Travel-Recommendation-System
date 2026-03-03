<template>
  <!-- 景点列表页面容器 -->
  <div class="spot-list-container">
    <!-- 筛选条件卡片 -->
    <el-card class="filter-card" shadow="hover">
      <!-- 筛选表单，:inline 表示内联布局 -->
      <el-form :inline="true" :model="filters" class="filter-form">
        <!-- 搜索景点输入框 -->
        <el-form-item label="搜索景点">
          <el-input 
            v-model="filters.q" 
            placeholder="请输入景点名称或关键词" 
            clearable 
            @keyup.enter="handleSearch"
            class="search-input"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <!-- 城市选择下拉框 -->
        <el-form-item label="城市">
          <el-select 
            v-model="filters.city" 
            placeholder="选择城市" 
            clearable 
            @change="fetchSpots"
            class="city-select"
          >
            <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
          </el-select>
        </el-form-item>
        <!-- 最低评分选择 -->
        <el-form-item label="最低评分">
          <div class="rating-selector">
            <el-rate 
              v-model="filters.min_rating" 
              allow-half 
              @change="handleRatingChange"
              show-score
              text-color="#ff9900"
              class="rating-star"
            />
            <span class="rating-text" v-if="filters.min_rating > 0">
              {{ filters.min_rating }} 分及以上
            </span>
            <span class="rating-text" v-else>
              不限
            </span>
          </div>
        </el-form-item>
        <!-- 排序方式选择 -->
        <el-form-item label="排序">
          <el-select v-model="filters.sort_by" @change="fetchSpots" class="sort-select">
            <el-option label="评分最高" value="rating" />
            <el-option label="名称正序" value="name" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="handleSearch" class="search-btn">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters" class="reset-btn">
            <el-icon><RefreshLeft /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 个性化推荐 Tab（仅登录用户可见） -->
      <div class="recommend-tab" v-if="userStore.token">
        <el-tabs v-model="activeTab" @tab-click="handleTabClick">
          <el-tab-pane label="全部景点" name="all">
            <span class="tab-desc">浏览所有景点，支持筛选和搜索</span>
          </el-tab-pane>
          <el-tab-pane label="为你推荐" name="recommend">
            <span class="tab-desc">基于您的城市、偏好和行为智能推荐</span>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>

    <!-- 统计信息栏 -->
    <div class="stats-bar" v-if="!loading && spots.length > 0">
      <span class="stats-text">
        <el-icon><TrendCharts /></el-icon>
        共找到 <strong>{{ total }}</strong> 个景点
      </span>
    </div>

    <!-- 景点列表网格，v-loading 显示加载状态 -->
    <div class="spot-grid" v-loading="loading" element-loading-text="加载中...">
      <el-row :gutter="24">
        <!-- 遍历景点列表，生成卡片 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="(spot, index) in spots" :key="spot.id" class="spot-col">
          <el-card 
            class="spot-card" 
            :body-style="{ padding: '0px' }" 
            shadow="hover" 
            @click="goToDetail(spot.id, spot)"
            :style="{ animationDelay: `${index * 0.05}s` }"
          >
            <!-- 景点图片 -->
            <div class="image-wrapper">
              <img 
                :src="cleanUrl(spot.image_url) || 'https://via.placeholder.com/300x200?text=暂无图片'" 
                class="spot-image" 
                :alt="spot.name"
                @error="handleImageError"
              />
              <!-- 评分标签 -->
              <div class="rating-badge">
                <el-icon><StarFilled /></el-icon>
                <span>{{ formatRating(spot.rating) }}</span>
              </div>
            </div>
            <!-- 景点信息 -->
            <div class="spot-info">
              <h3 class="spot-name" :title="spot.name">{{ spot.name }}</h3>
              <div class="spot-meta">
                <el-tag size="small" type="info" class="city-tag">
                  <el-icon><Location /></el-icon>
                  {{ spot.city }}
                </el-tag>
              </div>
              <p class="spot-address" :title="spot.address">
                <el-icon><Position /></el-icon>
                {{ spot.address || '地址未知' }}
              </p>
              <!-- 查看详情按钮 -->
              <div class="view-detail-btn">
                <el-button type="primary" size="small" link>
                  查看详情
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 空状态：没有找到景点时显示 -->
      <div v-if="!loading && spots.length === 0" class="empty-state">
        <el-empty description="没有找到符合条件的景点">
          <el-button type="primary" @click="resetFilters">
            <el-icon><RefreshLeft /></el-icon>
            重置筛选
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- 分页组件，只有在非搜索模式下显示 -->
    <div class="pagination-container" v-if="total > 0 && !isSearchMode">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[12, 24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        class="custom-pagination"
      />
    </div>

    <!-- 列表页 AI 客服入口 -->
    <div class="list-ai-fab" @click="toggleAssistant">
      <el-tooltip content="AI 帮你找景点" placement="left">
        <div class="fab-button" :class="{ active: assistantVisible }">
          <el-icon><Headset /></el-icon>
        </div>
      </el-tooltip>
    </div>

    <!-- 复用型 AI 客服抽屉 -->
    <SpotAssistantDrawer
      v-model="assistantVisible"
      mode="search"
      title="🤖 景点帮搜助手"
      welcome-message="你好！我是景点帮搜助手。告诉我你想去哪、和谁去、预算和季节，我会直接给你推荐卡片。"
      input-placeholder="例如：成都适合亲子游、交通方便的景点"
      @recommend-event="handleAssistantRecommendEvent"
    />
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, reactive, onMounted, computed } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入用户状态管理
import { useUserStore } from '../../store/user'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'
// 引入 Element Plus 的图标
import {
  Location, Search, RefreshLeft, ArrowRight,
  StarFilled, Position, TrendCharts, Headset
} from '@element-plus/icons-vue'
// 引入 API 接口
import { getCities, getSpots, searchSpots as apiSearchSpots, recordRecommendFeedback, getRecommendations } from '../../api/spots'
import SpotAssistantDrawer from '../../components/SpotAssistantDrawer.vue'

// 获取路由实例
const router = useRouter()
const userStore = useUserStore()

const normalizeRecommendSource = (item: any, fallback: string) => {
  const source = String(item?.source || item?.algorithm || '').trim()
  if (!source) return fallback
  if (['scene', 'recommend-tab', 'spot-detail', 'ai-search'].includes(source)) return source
  if (source === 'search') return 'ai-search'
  if (source === 'cf') return 'collaborative'
  if (source === 'cb') return 'content'
  return source
}

// 状态定义
const loading = ref(false)
const spots = ref<any[]>([])
const cities = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const assistantVisible = ref(false)
const activeTab = ref('all')
const recommendLoading = ref(false)

// Tab 切换处理
const handleTabClick = (tab: any) => {
  if (tab.props.name === 'recommend') {
    loadRecommendations()
  } else {
    fetchSpots()
  }
}

// 加载个性化推荐
const loadRecommendations = async () => {
  if (!userStore.token) return

  recommendLoading.value = true
  loading.value = true
  try {
    const res = await getRecommendations(50)
    const items = Array.isArray(res?.items) ? res.items : []
    spots.value = items
    total.value = items.length

    // 上报推荐曝光（同一轮去重）
    const exposed = new Set<number>()
    for (const item of items) {
      const spotId = Number(item?.spot_id || item?.id || 0)
      if (!spotId || exposed.has(spotId)) continue
      exposed.add(spotId)

      recordRecommendFeedback({
        spot_id: spotId,
        event_type: 'exposure',
        source: normalizeRecommendSource(item, 'recommend-tab'),
        score: typeof item?.score === 'number' ? item.score : undefined
      }).catch((error) => {
        console.error('上报推荐曝光失败:', error)
      })
    }
  } catch (error) {
    console.error('加载推荐失败:', error)
    ElMessage.error('加载推荐失败')
  } finally {
    loading.value = false
    recommendLoading.value = false
  }
}

// 筛选条件
const filters = reactive({
  q: '',
  city: '',
  min_rating: 0,
  sort_by: 'rating'
})

// 是否为搜索模式（搜索接口没有分页）
const isSearchMode = computed(() => !!filters.q)

// 获取城市列表
const fetchCities = async () => {
  try {
    const res = await getCities()
    cities.value = res.cities
  } catch (error) {
    console.error('获取城市列表失败:', error)
  }
}

// 获取景点列表
const fetchSpots = async () => {
  loading.value = true
  try {
    let res: any;

    if (isSearchMode.value) {
      // 搜索模式
      res = await apiSearchSpots(filters.q, pageSize.value)
    } else {
      // 列表模式
      let params: any = {
        page: page.value,
        page_size: pageSize.value,
        sort_by: filters.sort_by
      }
      if (filters.city) params.city = filters.city
      if (filters.min_rating > 0) params.min_rating = filters.min_rating
      res = await getSpots(params)
    }

    spots.value = res.items
    total.value = res.total
  } catch (error) {
    console.error('获取景点失败:', error)
    ElMessage.error('获取景点列表失败')
  } finally {
    loading.value = false
  }
}

// 处理评分变化
const handleRatingChange = (val: number) => {
  page.value = 1
  fetchSpots()
}

// 事件处理：搜索按钮点击
const handleSearch = () => {
  page.value = 1
  fetchSpots()
}

// 事件处理：重置筛选条件
const resetFilters = () => {
  filters.q = ''
  filters.city = ''
  filters.min_rating = 0
  filters.sort_by = 'rating'
  page.value = 1
  fetchSpots()
}

// 事件处理：每页显示数量改变
const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchSpots()
}

// 事件处理：当前页改变
const handleCurrentChange = (val: number) => {
  page.value = val
  fetchSpots()
}

// 跳转到景点详情页
const goToDetail = (id: number, item?: any) => {
  const spotId = Number(item?.spot_id || item?.id || id)
  // 防御 NaN：如果解析出来的 spotId 无效，直接返回不跳转
  if (Number.isNaN(spotId) || spotId <= 0) return

  if (userStore.token && activeTab.value === 'recommend' && spotId) {
    recordRecommendFeedback({
      spot_id: spotId,
      event_type: 'click',
      source: normalizeRecommendSource(item, 'recommend-tab'),
      score: typeof item?.score === 'number' ? item.score : undefined
    }).catch((error) => {
      console.error('上报推荐点击失败:', error)
    })
  }

  router.push(`/spot/${spotId}`)
}

// 切换列表页 AI 助手抽屉
const toggleAssistant = () => {
  assistantVisible.value = !assistantVisible.value
}

const handleAssistantRecommendEvent = (payload: {
  spot_id: number
  event_type: 'exposure' | 'click'
  source?: string
}) => {
  const token = userStore.token || localStorage.getItem('token')
  if (!token) return

  recordRecommendFeedback({
    ...payload,
    source: payload.source || 'ai-search'
  }).catch((error) => {
    console.error('上报推荐反馈失败:', error)
  })
}

// 评分统一显示 1 位小数
const formatRating = (rating: unknown) => {
  if (rating === null || rating === undefined || rating === '') return '暂无'
  if (typeof rating === 'number') return rating.toFixed(1)

  const parsed = Number(rating)
  if (!Number.isNaN(parsed)) return parsed.toFixed(1)

  return String(rating)
}

// 清理图片 URL 的函数，去除反引号和空格
const cleanUrl = (url: string) => {
  if (!url) return ''
  return url.trim().replace(/[` ]/g, '')
}

// 图片加载失败时的处理函数
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'https://via.placeholder.com/300x200?text=暂无图片'
}

// 组件挂载时执行
onMounted(() => {
  fetchCities()
  fetchSpots()
})
</script>

<style scoped>
/* 景点列表页面容器样式 */
.spot-list-container {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
  background: linear-gradient(180deg, #f0f4f8 0%, #e9ecef 50%, #f8f9fa 100%);
  min-height: calc(100vh - 60px);
  animation: fadeIn 0.5s ease;
}

/* 筛选卡片样式 */
.filter-card {
  margin-bottom: 24px;
  border-radius: 20px;
  border: none;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  animation: slideDown 0.6s ease;
}

/* 筛选表单样式 */
.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px;
}

/* 搜索输入框样式 */
.search-input {
  width: 280px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.2);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 4px 20px rgba(64, 158, 255, 0.3);
}

/* 城市选择器样式 */
.city-select,
.sort-select {
  width: 150px;
}

.city-select :deep(.el-select__wrapper),
.sort-select :deep(.el-select__wrapper) {
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* 评分选择器样式 */
.rating-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: #f5f7fa;
  border-radius: 20px;
  transition: all 0.3s ease;
  position: relative;
  z-index: 10;
}

.rating-selector:hover {
  background: #ecf5ff;
}

.rating-star {
  cursor: pointer;
  position: relative;
  z-index: 20;
}

.rating-star :deep(.el-rate__item) {
  cursor: pointer;
}

.rating-star :deep(.el-rate__icon) {
  cursor: pointer;
}

.rating-text {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  min-width: 90px;
}

/* 按钮样式 */
.search-btn {
  border-radius: 20px;
  padding: 0 24px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: all 0.3s ease;
}

.search-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.reset-btn {
  border-radius: 20px;
  padding: 0 20px;
  transition: all 0.3s ease;
}

.reset-btn:hover {
  transform: translateY(-2px);
}

/* 统计信息栏 */
.stats-bar {
  margin-bottom: 20px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border-radius: 12px;
  color: white;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.stats-text {
  font-size: 14px;
}

.stats-text strong {
  font-size: 18px;
  font-weight: 600;
}

/* 景点网格样式 */
.spot-grid {
  min-height: 400px;
}

/* 景点列样式 */
.spot-col {
  margin-bottom: 24px;
}

/* 景点卡片样式 */
.spot-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  border: none;
  overflow: hidden;
  animation: fadeInUp 0.7s ease forwards;
  opacity: 0;
  background: white;
}

/* 卡片悬停效果 */
.spot-card:hover {
  transform: translateY(-12px) scale(1.02);
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.18) !important;
}

.spot-card:hover::before {
  opacity: 1;
}

/* 图片包装器 */
.image-wrapper {
  position: relative;
  overflow: hidden;
}

/* 景点图片样式 */
.spot-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.spot-card:hover .spot-image {
  transform: scale(1.1);
}

/* 评分标签 */
.rating-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: linear-gradient(135deg, #ff9900 0%, #ffb347 100%);
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  box-shadow: 0 4px 12px rgba(255, 153, 0, 0.4);
  backdrop-filter: blur(10px);
}

/* 景点信息区域样式 */
.spot-info {
  padding: 18px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 景点名称样式 */
.spot-name {
  margin: 0 0 12px;
  font-size: 17px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

/* 景点元信息样式 */
.spot-meta {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

/* 城市标签 */
.city-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 12px;
  padding: 4px 10px;
}

/* 景点地址样式 */
.spot-address {
  margin: 0 0 12px;
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 查看详情按钮 */
.view-detail-btn {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px dashed #ebeef5;
}

/* 分页容器样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding: 20px;
}

/* 自定义分页样式 */
.custom-pagination {
  background: white;
  padding: 16px 32px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

/* 空状态样式 */
.empty-state {
  padding: 60px 0;
}

/* 列表页 AI 悬浮按钮 */
.list-ai-fab {
  position: fixed;
  right: 36px;
  bottom: 96px;
  z-index: 110;
  cursor: pointer;
  animation: float 3s ease-in-out infinite;
}

.fab-button {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409eff 0%, #79bbff 100%);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 28px;
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.38);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fab-button:hover {
  transform: scale(1.12);
  box-shadow: 0 8px 26px rgba(64, 158, 255, 0.5);
}

.fab-button.active {
  background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%);
  box-shadow: 0 6px 20px rgba(144, 147, 153, 0.38);
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

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(40px);
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
    transform: translateY(-8px);
  }
}

/* 推荐 Tab 样式 */
.recommend-tab {
  margin-top: 20px;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

.tab-desc {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

:deep(.el-tabs__item) {
  font-size: 16px;
}

:deep(.el-tabs__content) {
  display: none;
}
</style>
