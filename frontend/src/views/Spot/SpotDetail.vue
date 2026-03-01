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
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Location, Calendar, MapLocation, Tickets,
  Document, Timer, Ticket, Warning,
  Star, StarFilled
} from '@element-plus/icons-vue'
import { getSpotDetail, getCollections, toggleCollection, recordBehavior } from '../../api/spots'
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

onMounted(() => {
  fetchDetail()
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
</style>