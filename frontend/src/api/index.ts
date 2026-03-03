// 引入 axios，用来发送 HTTP 请求
import axios from 'axios'
// 引入 Element Plus 的消息提示组件
import { ElMessage } from 'element-plus'

// 创建 axios 实例，配置基础信息
const api = axios.create({
  // 后端 API 的基础地址，所有请求都会在前面加上这个
  baseURL: 'http://localhost:8000/api',
  // 请求超时时间，10秒后如果还没响应就报错
  timeout: 10000
})

// 请求拦截器：在发送请求前会执行这里的代码
api.interceptors.request.use(
  config => {
    // 从本地存储里拿到用户的 token
    const token = localStorage.getItem('token')
    // 如果有 token，就加到请求头里，这样后端就知道是谁在请求了
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 把配置返回，继续发送请求
    return config
  },
  error => {
    // 如果请求出错了，就把错误传出去
    return Promise.reject(error)
  }
)

// 响应拦截器：收到后端响应后会执行这里的代码
api.interceptors.response.use(
  response => {
    // 直接返回响应的数据部分（去掉 axios 包装的那层）
    return response.data
  },
  error => {
    // 如果是 401 错误，说明 token 过期了或者没登录
    if (error.response?.status === 401) {
      // 清空本地存储的 token 和用户信息
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // 跳转到登录页
      window.location.href = '/login'
    } else {
      // 其他错误就显示提示消息
      ElMessage.error(error.response?.data?.detail || '请求失败，请稍后重试')
    }
    // 把错误传出去
    return Promise.reject(error)
  }
)

const ABSOLUTE_URL_PATTERN = /^(https?:)?\/\//i

// 解析后端资源绝对地址（例如 /uploads/avatars/xxx.png）
export const resolveApiAssetUrl = (rawPath?: string) => {
  const value = String(rawPath || '').trim()
  if (!value) return ''

  // 已经是绝对地址或浏览器本地地址，直接返回
  if (ABSOLUTE_URL_PATTERN.test(value) || value.startsWith('blob:') || value.startsWith('data:')) {
    return value
  }

  const baseURL = String(api.defaults.baseURL || '').trim()
  if (!baseURL) return value

  try {
    const origin = new URL(baseURL, window.location.origin).origin
    return `${origin}${value.startsWith('/') ? '' : '/'}${value}`
  } catch {
    return value
  }
}

// 导出配置好的 axios 实例，给其他文件用
export default api
