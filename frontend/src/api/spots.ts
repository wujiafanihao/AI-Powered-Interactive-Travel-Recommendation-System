import api from './index'

export const getSpots = (params: any): Promise<any> => api.get('/spots', { params })
export const getCities = (): Promise<any> => api.get('/spots/cities')
export const searchSpots = (q: string, limit: number = 20): Promise<any> => api.get('/spots/search', { params: { q, limit } })
export const getSpotDetail = (id: number): Promise<any> => api.get(`/spots/${id}`)

export const getRecommendations = (n: number = 10): Promise<any> => api.get('/recommend', { params: { n } })
export const getSceneRecommendations = (scene: string, n: number = 10): Promise<any> => api.get(`/recommend/scene/${scene}`, { params: { n } })
export const recordBehavior = (data: any): Promise<any> => api.post('/recommend/behavior', data)
export const getCollections = (): Promise<any> => api.get('/recommend/collections')
export const toggleCollection = (spotId: number): Promise<any> => api.post(`/recommend/collect/${spotId}`)

export const chatWithAI = (data: { message: string, session_id?: string }): Promise<any> => api.post('/chat', data)
export const getChatHistory = (params?: any): Promise<any> => api.get('/chat/history', { params })
