// 引入 Pinia 的 defineStore 函数，用来定义状态管理
import { defineStore } from 'pinia'
// 引入 Vue 的 ref，用来创建响应式数据
import { ref } from 'vue'

// 定义用户状态管理，名字叫 'user'
export const useUserStore = defineStore('user', () => {
  // 用户登录后的 token，从本地存储读取，如果没有就为空
  const token = ref(localStorage.getItem('token') || '')
  // 用户信息，从本地存储读取，如果没有就为空对象
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || '{}'))

  // 设置 token 的函数，同时保存到本地存储
  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  // 设置用户信息的函数，同时保存到本地存储
  const setUserInfo = (info: any) => {
    userInfo.value = info
    localStorage.setItem('user', JSON.stringify(info))
  }

  // 退出登录函数，清空 token 和用户信息，同时删除本地存储
  const logout = () => {
    token.value = ''
    userInfo.value = {}
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  // 把这些数据和函数暴露出去，让其他组件可以用
  return {
    token,
    userInfo,
    setToken,
    setUserInfo,
    logout
  }
})
