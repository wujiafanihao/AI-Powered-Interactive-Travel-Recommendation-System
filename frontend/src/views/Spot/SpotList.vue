<template>
  <div class="spot-list-container">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="搜索景点">
          <el-input v-model="filters.q" placeholder="请输入景点名称或关键词" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="城市">
          <el-select v-model="filters.city" placeholder="选择城市" clearable @change="fetchSpots">
            <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
          </el-select>
        </el-form-item>
        <el-form-item label="最低评分">
          <el-rate v-model="filters.min_rating" allow-half @change="fetchSpots" />
        </el-form-item>
        <el-form-item label="排序">
          <el-select v-model="filters.sort_by" @change="fetchSpots">
            <el-option label="评分最高" value="rating" />
            <el-option label="名称正序" value="name" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div class="spot-grid" v-loading="loading">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="spot in spots" :key="spot.id" class="spot-col">
          <el-card class="spot-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToDetail(spot.id)">
            <img :src="spot.image_url || 'https://via.placeholder.com/300x200?text=暂无图片'" class="spot-image" />
            <div class="spot-info">
              <h3 class="spot-name">{{ spot.name }}</h3>
              <div class="spot-meta">
                <el-tag size="small" type="info">{{ spot.city }}</el-tag>
                <el-rate v-model="spot.rating" disabled show-score text-color="#ff9900" />
              </div>
              <p class="spot-address" :title="spot.address"><el-icon><Location /></el-icon> {{ spot.address || '地址未知' }}</p>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && spots.length === 0" description="没有找到符合条件的景点" />
    </div>

    <div class="pagination-container" v-if="total > 0 && !isSearchMode">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :page-sizes="[12, 24, 48, 96]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Location } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const API_BASE = 'http://localhost:8000/api' // 根据实际后端地址调整，可以写在 axios 拦截器里，这里为了简便

// 状态定义
const loading = ref(false)
const spots = ref<any[]>([])
const cities = ref<string[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)

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
    const res = await axios.get(`${API_BASE}/spots/cities`)
    cities.value = res.data.cities
  } catch (error) {
    console.error('获取城市列表失败:', error)
  }
}

// 获取景点列表
const fetchSpots = async () => {
  loading.value = true
  try {
    let url = ''
    let params: any = {}

    if (isSearchMode.value) {
      // 搜索模式
      url = `${API_BASE}/spots/search`
      params = { q: filters.q, limit: pageSize.value }
    } else {
      // 列表模式
      url = `${API_BASE}/spots`
      params = {
        page: page.value,
        page_size: pageSize.value,
        sort_by: filters.sort_by
      }
      if (filters.city) params.city = filters.city
      if (filters.min_rating > 0) params.min_rating = filters.min_rating
    }

    const res = await axios.get(url, { params })
    spots.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error('获取景点失败:', error)
    ElMessage.error('获取景点列表失败')
  } finally {
    loading.value = false
  }
}

// 事件处理
const handleSearch = () => {
  page.value = 1
  fetchSpots()
}

const resetFilters = () => {
  filters.q = ''
  filters.city = ''
  filters.min_rating = 0
  filters.sort_by = 'rating'
  page.value = 1
  fetchSpots()
}

const handleSizeChange = (val: number) => {
  pageSize.value = val
  fetchSpots()
}

const handleCurrentChange = (val: number) => {
  page.value = val
  fetchSpots()
}

const goToDetail = (id: number) => {
  router.push(`/spot/${id}`)
}

// 初始化
onMounted(() => {
  fetchCities()
  fetchSpots()
})
</script>

<style scoped>
.spot-list-container {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
}

.spot-grid {
  min-height: 400px;
}

.spot-col {
  margin-bottom: 20px;
}

.spot-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.spot-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1) !important;
}

.spot-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.spot-info {
  padding: 15px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.spot-name {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spot-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.spot-address {
  margin: auto 0 0;
  font-size: 12px;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>