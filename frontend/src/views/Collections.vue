<template>
  <div class="collections-container">
    <div class="header">
      <h2>我的收藏</h2>
      <span class="count">共 {{ collections.length }} 个景点</span>
    </div>

    <div v-if="loading" class="loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div v-else-if="collections.length === 0" class="empty">
      <el-empty description="还没有收藏任何景点">
        <el-button type="primary" @click="$router.push('/spots')">去逛逛</el-button>
      </el-empty>
    </div>

    <div v-else class="spots-grid">
      <div v-for="spot in collections" :key="spot.id" class="spot-card" @click="goToSpot(spot.id)">
        <div class="spot-image">
          <img :src="cleanUrl(spot.image_url) || 'https://via.placeholder.com/300x200?text=No+Image'" :alt="spot.name" @error="handleImageError" />
          <div class="spot-rating">
            <span class="rating-star">⭐</span>
            <span>{{ spot.rating }}</span>
          </div>
        </div>
        <div class="spot-info">
          <h3>{{ spot.name }}</h3>
          <p class="spot-city">{{ spot.city }}</p>
          <p class="spot-type">{{ formatType(spot.spot_type) }}</p>
        </div>
        <div class="spot-actions">
          <el-button type="danger" size="small" @click.stop="handleRemove(spot.id)">
            取消收藏
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getCollections, toggleCollection } from '../api/spots'

const router = useRouter()
const collections = ref<any[]>([])
const loading = ref(true)

const loadCollections = async () => {
  loading.value = true
  try {
    const res = await getCollections()
    console.log('收藏数据:', res)
    collections.value = res.items || res || []
  } catch (error: any) {
    console.error('加载收藏失败:', error)
    ElMessage.error('加载收藏失败')
  } finally {
    loading.value = false
  }
}

const handleRemove = async (spotId: number) => {
  try {
    await ElMessageBox.confirm('确定要取消收藏吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await toggleCollection(spotId)
    ElMessage.success('取消收藏成功')
    collections.value = collections.value.filter(s => s.id !== spotId)
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('取消收藏失败')
    }
  }
}

const goToSpot = (id: number) => {
  router.push(`/spot/${id}`)
}

const formatType = (types: string) => {
  if (!types) return ''
  try {
    const arr = JSON.parse(types)
    return arr.slice(0, 3).join(' / ')
  } catch {
    return types
  }
}

const cleanUrl = (url: string) => {
  if (!url) return ''
  return url.trim().replace(/[` ]/g, '')
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.src = 'https://via.placeholder.com/300x200?text=No+Image'
}

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
