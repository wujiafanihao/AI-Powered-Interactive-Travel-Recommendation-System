// 引入我们配置好的 axios 实例
import api from './index'

// ==================== 景点相关的 API ====================

// 获取景点列表，可以传参数进行筛选
export const getSpots = (params: any): Promise<any> => api.get('/spots', { params })

// 获取所有城市列表
export const getCities = (): Promise<any> => api.get('/spots/cities')

// 搜索景点，q 是搜索关键词，limit 是返回结果数量
export const searchSpots = (q: string, limit: number = 20): Promise<any> => api.get('/spots/search', { params: { q, limit } })

// 获取某个景点的详细信息，id 是景点的编号
export const getSpotDetail = (id: number): Promise<any> => api.get(`/spots/${id}`)

// 获取某个景点的用户评论，id 是景点的编号
export const getSpotComments = (id: number): Promise<any> => api.get(`/spots/${id}/comments`)

// ==================== 推荐相关的 API ====================

// 获取个性化推荐景点，n 是推荐数量
export const getRecommendations = (n: number = 10): Promise<any> => api.get('/recommend', { params: { n } })

// 根据场景推荐景点，scene 是场景名称，n 是推荐数量
export const getSceneRecommendations = (scene: string, n: number = 10): Promise<any> => api.get(`/recommend/scene/${scene}`, { params: { n } })

// 记录用户的行为数据（比如点击、浏览等）
export const recordBehavior = (data: any): Promise<any> => api.post('/recommend/behavior', data)

// 获取用户收藏的景点列表
export const getCollections = (): Promise<any> => api.get('/recommend/collections')

// 收藏或取消收藏某个景点，spotId 是景点编号
export const toggleCollection = (spotId: number): Promise<any> => api.post(`/recommend/collect/${spotId}`)

// 上报推荐反馈（曝光/点击/收藏/评分）
export const recordRecommendFeedback = (data: {
  spot_id: number
  event_type: 'exposure' | 'click' | 'collect' | 'rate'
  rec_session_id?: string
  source?: string
  score?: number
}): Promise<any> => api.post('/recommend/feedback', data)

// ==================== 用户资料相关 API ====================

// 获取当前登录用户信息
export const getMe = (): Promise<any> => api.get('/auth/me')

// 检查用户资料完善状态
export const getProfileStatus = (): Promise<any> => api.get('/auth/me/profile-status')

// 更新用户资料
export const updateProfile = (data: any): Promise<any> => api.put('/auth/me', data)

// 上传用户头像
export const uploadAvatar = (file: File): Promise<any> => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/auth/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// ==================== AI 聊天相关的 API ====================

// 和 AI 进行普通对话
export const chatWithAI = (data: { message: string, session_id?: string }): Promise<any> => api.post('/chat', data, { timeout: 0 })

// 和 AI 聊某个具体景点，spotId 是景点编号
export const chatWithSpotAI = (spotId: number, data: { message: string, session_id?: string }): Promise<any> => api.post(`/chat/spot/${spotId}`, data, { timeout: 0 })

// 获取聊天历史记录
export const getChatHistory = (params?: any): Promise<any> => api.get('/chat/history', { params })

// 删除某个聊天会话，sessionId 是会话编号
export const deleteChatSession = (sessionId: string): Promise<any> => api.delete(`/chat/session/${sessionId}`)
