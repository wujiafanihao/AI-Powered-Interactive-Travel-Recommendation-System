import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response?.status === 401) {
      // Token 过期或未登录
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    } else {
      ElMessage.error(error.response?.data?.detail || '请求失败，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default api
