<template>
  <!-- 景点列表页面容器 -->
  <div class="spot-list-container">
    <!-- 筛选条件卡片 -->
    <el-card class="filter-card">
      <!-- 筛选表单，:inline 表示内联布局 -->
      <el-form :inline="true" :model="filters" class="filter-form">
        <!-- 搜索景点输入框 -->
        <el-form-item label="搜索景点">
          <el-input v-model="filters.q" placeholder="请输入景点名称或关键词" clearable @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 城市选择下拉框 -->
        <el-form-item label="城市">
          <el-select v-model="filters.city" placeholder="选择城市" clearable @change="fetchSpots">
            <el-option v-for="city in cities" :key="city" :label="city" :value="city" />
          </el-select>
        </el-form-item>
        <!-- 最低评分选择 -->
        <el-form-item label="最低评分">
          <el-rate v-model="filters.min_rating" allow-half @change="fetchSpots" />
        </el-form-item>
        <!-- 排序方式选择 -->
        <el-form-item label="排序">
          <el-select v-model="filters.sort_by" @change="fetchSpots">
            <el-option label="评分最高" value="rating" />
            <el-option label="名称正序" value="name" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 景点列表网格，v-loading 显示加载状态 -->
    <div class="spot-grid" v-loading="loading">
      <el-row :gutter="20">
        <!-- 遍历景点列表，生成卡片 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="spot in spots" :key="spot.id" class="spot-col">
          <el-card class="spot-card" :body-style="{ padding: '0px' }" shadow="hover" @click="goToDetail(spot.id)">
            <!-- 景点图片 -->
            <img :src="spot.image_url || 'https://via.placeholder.com/300x200?text=暂无图片'" class="spot-image" />
            <!-- 景点信息 -->
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

      <!-- 空状态：没有找到景点时显示 -->
      <el-empty v-if="!loading && spots.length === 0" description="没有找到符合条件的景点" />
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
      />
    </div>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 的核心函数
import { ref, reactive, onMounted, computed } from 'vue'
// 引入路由，用于页面跳转
import { useRouter } from 'vue-router'
// 引入 Element Plus 的消息提示
import { ElMessage } from 'element-plus'
// 引入 Element Plus 的图标
import { Location } from '@element-plus/icons-vue'
// 引入 API 接口
import { getCities, getSpots, searchSpots as apiSearchSpots } from '../../api/spots'

// 获取路由实例
const router = useRouter()

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
const goToDetail = (id: number) => {
  router.push(`/spot/${id}`)
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
  padding: 20px;
}

/* 筛选卡片样式 */
.filter-card {
  margin-bottom: 20px;
}

/* 筛选表单样式 */
.filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
}

/* 景点网格样式 */
.spot-grid {
  min-height: 400px;
}

/* 景点列样式 */
.spot-col {
  margin-bottom: 20px;
}

/* 景点卡片样式 */
.spot-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

/* 卡片悬停效果 */
.spot-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1) !important;
}

/* 景点图片样式 */
.spot-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

/* 景点信息区域样式 */
.spot-info {
  padding: 15px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 景点名称样式 */
.spot-name {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 景点元信息样式 */
.spot-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

/* 景点地址样式 */
.spot-address {
  margin: auto 0 0;
  font-size: 12px;
  color: #999;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 分页容器样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
