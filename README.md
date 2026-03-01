# TravelAI 智能旅游推荐系统

基于 FastAPI (后端) 和 Vue 3 + Element Plus (前端) 的智能旅游推荐系统。支持基于大语言模型的 AI 帮搜，以及协同过滤和内容推荐的混合推荐算法。

## 技术栈

- **后端**: Python 3.14.3 + FastAPI
- **前端**: Vue 3 + Vite + Element Plus + Pinia
- **数据库**: SQLite + ChromaDB (向量数据库)
- **AI**: LangChain + ModelScope API (DeepSeek-V3.2 + Qwen3-Embedding-8B)

## 项目结构

- `/backend/`: Python FastAPI 后端
- `/frontend/`: Vue 3 + Vite 前端
- `/citydata/`: 原始景点数据

## 核心功能

- **用户认证**: 注册、登录系统。
- **景点探索**: 按城市、评分等条件过滤浏览景点，查看详情。
- **混合推荐**: 基于协同过滤（猜你喜欢）、基于内容（相似内容）、以及场景和热门推荐。
- **AI 帮搜**: 基于 RAG 技术与意图识别的 AI 对话页面，不仅能问答，还可以推荐景点卡片并提供引用来源。

## 运行说明

1. 确保在根目录创建 `.env` 文件，并填写正确的模型 API Key 和相关配置。
2. 启动后端服务 (FastAPI)：
   ```bash
   cd backend
   uvicorn main:app --reload
   ```
3. 启动前端服务 (Vite)：
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. 访问 `http://localhost:5173` 进行体验。
