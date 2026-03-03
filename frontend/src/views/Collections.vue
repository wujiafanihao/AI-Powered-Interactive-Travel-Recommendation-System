<template>
  <!-- 收藏页面的容器 -->
  <div class="collections-container">
    <!-- 页面标题区域 -->
    <div class="header">
      <h2>我的收藏</h2>
      <!-- 显示收藏的景点数量 -->
      <span class="count">共 {{ collections.length }} 个景点</span>
    </div>

    <!-- 加载中状态：显示加载动画 -->
    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <!-- 空状态：如果没有收藏任何景点，显示提示 -->
    <div v-else-if="collections.length === 0" class="empty">
      <el-empty description="还没有收藏任何景点">
        <!-- 去逛逛按钮，点击跳转到景点列表页 -->
        <el-button type="primary" @click="$router.push('/spots')">去逛逛</el-button>
      </el-empty>
    </div>

    <!-- 收藏列表：显示所有收藏的景点 -->
    <div v-else class="spots-grid">
      <!-- 遍历每个收藏的景点，生成卡片 -->
      <div v-for="spot in collections" :key="spot.id" class="spot-card" @click="goToSpot(spot.id)">
        <!-- 景点图片区域 -->
        <div class="spot-image">
          <!-- 显示景点图片，使用 cleanUrl 函数清理 URL，图片加载失败时显示占位图 -->
          <img :src="cleanUrl(spot.image_url) || 'https://via.placeholder.com/300x200?text=No+Image'" :alt="spot.name" @error="handleImageError" />
          <!-- 景点评分标签，悬浮在图片右上角 -->
          <div class="spot-rating">
            <span class="rating-star">⭐</span>
            <span>{{ spot.rating }}</span>
          </div>
        </div>
        <!-- 景点基本信息 -->
        <div class="spot-info">
          <h3>{{ spot.name }}</h3>
          <p class="spot-city">{{ spot.city }}</p>
          <!-- 格式化显示景点类型 -->
          <p class="spot-type">{{ formatType(spot.spot_type) }}</p>
        </div>
        <!-- 操作按钮区域 -->
        <div class="spot-actions">
          <!-- 取消收藏按钮，@click.stop 阻止事件冒泡，避免触发卡片的点击事件 -->
          <el-button type="danger" size="small" @click.stop="handleRemove(spot.id)">
            取消收藏
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, onMounted } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示和确认对话框
import { ElMessage, ElMessageBox } from 'element-plus'
// 引入 Element Plus 的加载图标
import { Loading } from '@element-plus/icons-vue'
// 引入收藏相关的 API 接口
import { getCollections, toggleCollection } from '../api/spots'

// 获取路由实例
const router = useRouter()
// 收藏列表数据，响应式变量
const collections = ref<any[]>([])
// 加载状态，响应式变量
const loading = ref(true)

// 加载收藏列表的函数
const loadCollections = async () => {
  loading.value = true
  try {
    // 调用 API 获取收藏列表
    const res = await getCollections()
    console.log('收藏数据:', res)
    // 将 API 返回的数据赋值给 collections，兼容不同的数据结构
    collections.value = res.items || res || []
  } catch (error: any) {
    console.error('加载收藏失败:', error)
    ElMessage.error('加载收藏失败')
  } finally {
    // 无论成功或失败，都关闭加载状态
    loading.value = false
  }
}

// 取消收藏的函数
const handleRemove = async (spotId: number) => {
  try {
    // 弹出确认对话框，询问用户是否确定取消收藏
    await ElMessageBox.confirm('确定要取消收藏吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    // 调用 API 取消收藏
    await toggleCollection(spotId)
    ElMessage.success('取消收藏成功')
    // 从本地列表中移除该景点，不用重新加载整个列表
    collections.value = collections.value.filter(s => s.id !== spotId)
  } catch (error: any) {
    // 如果用户点击了取消，不显示错误提示
    if (error !== 'cancel') {
      ElMessage.error('取消收藏失败')
    }
  }
}

// 跳转到景点详情页的函数
const goToSpot = (id: number) => {
  const spotId = Number(id)
  // 防御 NaN：无效 ID 不跳转
  if (Number.isNaN(spotId) || spotId <= 0) return
  router.push(`/spot/${spotId}`)
}

// 格式化景点类型的函数，将 JSON 字符串转换为可读的文本
const formatType = (types: string) => {
  if (!types) return ''
  try {
    // 尝试解析 JSON 字符串
    const arr = JSON.parse(types)
    // 只取前 3 个类型，用斜杠连接
    return arr.slice(0, 3).join(' / ')
  } catch {
    // 如果解析失败，直接返回原字符串
    return types
  }
}

// 清理图片 URL 的函数，去除反引号和空格
const cleanUrl = (url: string) => {
  if (!url) return ''
  return url.trim().replace(/[` ]/g, '')
}

// 图片加载失败时的处理函数，显示占位图
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'https://via.placeholder.com/300x200?text=No+Image'
}

// 组件挂载时执行，加载收藏列表
onMounted(() => {
  loadCollections()
})
</script>

<style scoped>
.collections-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 30px;
}

.header h2 {
  margin: 0;
}

.count {
  color: #909399;
  font-size: 14px;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 50px;
  color: #909399;
}

.empty {
  padding: 50px 0;
}

.spots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.spot-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.spot-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.spot-image {
  position: relative;
  height: 180px;
  overflow: hidden;
}

.spot-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.spot-rating {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.spot-info {
  padding: 15px;
}

.spot-info h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spot-city {
  margin: 0 0 5px 0;
  color: #606266;
  font-size: 14px;
}

.spot-type {
  margin: 0;
  color: #909399;
  font-size: 12px;
}

.spot-actions {
  padding: 10px 15px 15px;
}
</style>
