import request from './request'

// 删除会话聊天记录
export const deleteSession = (sessionId: string) => {
  return request.delete(`/api/chat/session/${sessionId}`)
}
