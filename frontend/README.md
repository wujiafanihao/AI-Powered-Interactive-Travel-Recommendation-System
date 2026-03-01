# AI 交互旅游推荐系统 - 前端

这是一个基于 Vue 3 + TypeScript + Vite 构建的智能旅游推荐系统前端项目，配合后端 API 使用，为用户提供景点浏览、AI 聊天、个性化推荐等功能。

## 项目简介

本项目是一个旅游推荐系统的前端部分，主要功能包括：

- 🎨 **美观的界面**：使用 Element Plus UI 组件库，界面简洁大方
- 🔍 **景点浏览**：查看所有景点、按城市筛选、搜索景点
- 🤖 **AI 聊天**：与 AI 智能助手对话，获取旅游建议
- 💝 **收藏管理**：收藏喜欢的景点，随时查看
- 🎯 **个性化推荐**：基于用户行为和偏好推荐景点
- 👤 **用户系统**：用户注册、登录、个人信息管理

## 技术栈

- **框架**：Vue 3（使用 Composition API 和 `<script setup>` 语法）
- **语言**：TypeScript
- **构建工具**：Vite
- **UI 组件库**：Element Plus
- **路由管理**：Vue Router
- **状态管理**：Pinia
- **HTTP 请求**：Axios
- **Markdown 解析**：Marked（用于显示 AI 返回的 markdown 内容）

## 项目结构

```
frontend/
├── public/                 # 静态资源
│   ├── favicon.svg        # 网站图标
│   └── vite.svg           # Vite 默认图标
├── src/
│   ├── api/               # API 接口封装
│   │   ├── index.ts       # Axios 实例配置和拦截器
│   │   ├── spots.ts       # 景点、推荐、聊天等 API
│   │   ├── chat.ts        # 聊天相关 API
│   │   └── request.ts     # 备用的请求配置
│   ├── assets/            # 静态资源
│   │   └── vue.svg
│   ├── components/        # 公共组件
│   │   └── HelloWorld.vue
│   ├── router/            # 路由配置
│   │   └── index.ts       # 路由定义
│   ├── store/             # 状态管理
│   │   └── user.ts        # 用户状态管理
│   ├── views/             # 页面组件
│   │   ├── AI/
│   │   │   └── Chat.vue   # AI 聊天页
│   │   ├── Spot/
│   │   │   ├── SpotDetail.vue  # 景点详情页
│   │   │   └── SpotList.vue    # 景点列表页
│   │   ├── Home.vue        # 首页
│   │   ├── Login.vue       # 登录页
│   │   ├── Register.vue    # 注册页
│   │   └── Collections.vue # 我的收藏页
│   ├── App.vue             # 根组件
│   ├── main.ts             # 入口文件
│   └── style.css           # 全局样式
├── .gitignore
├── index.html              # HTML 入口
├── package.json            # 项目依赖和脚本
├── tsconfig.json           # TypeScript 配置
├── tsconfig.node.json
├── vite.config.ts          # Vite 配置
└── README.md               # 本文件
```

## 环境要求

- **Node.js**：建议 16.x 或更高版本
- **npm** 或 **yarn** 或 **pnpm**：包管理器
- **后端服务**：需要先启动后端 API 服务（默认运行在 http://localhost:8000）

## 快速开始

### 1. 安装依赖

首先进入前端目录，然后安装项目依赖：

```bash
cd frontend
npm install
```

如果你使用 yarn：

```bash
yarn install
```

如果你使用 pnpm：

```bash
pnpm install
```

### 2. 配置后端地址（可选）

默认情况下，前端会连接到 `http://localhost:8000/api`。如果你的后端运行在其他地址，请修改 `src/api/index.ts` 文件：

```typescript
const api = axios.create({
  baseURL: 'http://你的后端地址/api',  // 修改这里
  timeout: 10000
})
```

### 3. 启动后端服务

在启动前端之前，请确保后端服务已经启动。后端启动方法请参考项目根目录的 README.md。

### 4. 启动开发服务器

运行以下命令启动开发服务器：

```bash
npm run dev
```

或者使用 yarn：

```bash
yarn dev
```

启动成功后，终端会显示类似这样的信息：

```
  VITE v8.0.0-beta.13  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

打开浏览器访问 `http://localhost:5173` 就可以看到网站了！

## 页面说明

### 首页 (`/`)
- 欢迎横幅和介绍
- 场景推荐（带孩子、情侣约会、自然风光等）
- 个性化推荐（需要登录）

### 登录页 (`/login`)
- 用户登录
- 跳转到注册页

### 注册页 (`/register`)
- 新用户注册
- 跳转到登录页

### 景点列表页 (`/spots`)
- 查看所有景点
- 按城市筛选
- 搜索景点
- 点击卡片查看详情

### 景点详情页 (`/spot/:id`)
- 景点详细信息
- 景点图片
- 用户评论
- AI 聊天（关于这个景点）
- 收藏/取消收藏

### AI 聊天页 (`/ai`)
- 与 AI 智能助手对话
- 获取旅游建议
- 查看聊天历史

### 我的收藏页 (`/collections`)
- 查看已收藏的景点
- 取消收藏
- 点击跳转到景点详情

## 可用脚本

在项目目录下，你可以运行以下命令：

### `npm run dev`
启动开发服务器，支持热更新（修改代码后浏览器会自动刷新）。

### `npm run build`
构建生产版本，构建结果会输出到 `dist` 目录。

### `npm run preview`
预览生产构建的结果，需要先运行 `npm run build`。

## 开发指南

### 添加新页面

1. 在 `src/views/` 目录下创建新的 Vue 组件
2. 在 `src/router/index.ts` 中添加路由配置
3. 如果需要导航链接，在首页或其他页面添加跳转按钮

### 添加新的 API 接口

在 `src/api/spots.ts` 文件中添加新的接口函数，例如：

```typescript
// 获取某个景点的图片
export const getSpotImages = (id: number): Promise<any> => api.get(`/spots/${id}/images`)
```

### 使用用户状态

在组件中使用 Pinia 管理的用户状态：

```typescript
import { useUserStore } from '../store/user'

const userStore = useUserStore()

// 获取 token
console.log(userStore.token)

// 设置用户信息
userStore.setUserInfo({ username: '张三', id: 1 })

// 退出登录
userStore.logout()
```

## 常见问题

### Q: 前端启动了，但页面显示空白？
A: 请检查浏览器控制台是否有错误信息，通常是因为后端服务没有启动或者 API 地址配置错误。

### Q: 登录后刷新页面又退出了？
A: 这是正常的，因为 token 保存在 localStorage 中，刷新页面后会自动从 localStorage 读取。

### Q: 如何修改端口号？
A: 在 `vite.config.ts` 中添加 server 配置：

```typescript
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000  // 修改为你想要的端口
  }
})
```

### Q: AI 聊天没有反应？
A: 请确保后端服务已启动，并且 AI 相关的配置（如 API Key）已正确设置。

## 技术支持

如果在使用过程中遇到问题，请：
1. 检查浏览器控制台的错误信息
2. 确认后端服务是否正常运行
3. 查看后端日志了解详细错误

## 许可证

本项目仅供学习和研究使用。
