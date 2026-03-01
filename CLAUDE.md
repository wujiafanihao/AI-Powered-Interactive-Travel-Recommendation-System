# CLAUDE.md - TravelAI 项目上下文文档

## 0. 技术栈
- **后端**: Python 3.14.3 + FastAPI
- **前端**: Vue 3 + Vite + Element Plus
- **数据库**: SQLite + ChromaDB (向量数据库)
- **AI**: LangChain + ModelScope API (DeepSeek-V3.2 + Qwen3-Embedding-8B)
- **Conda 环境**: `xianyu`
- **开发模式**: 测试驱动开发 (TDD)

## 1. AI 配置
- **API 地址**: `https://api-inference.modelscope.cn/v1/`
- **LLM 模型**: `deepseek-ai/DeepSeek-V3.2`
- **嵌入模型**: `Qwen/Qwen3-Embedding-8B`
- **密钥管理**: 存储于 `.env` 文件

## 2. 数据资产
- `citydata/` 目录包含 352 个城市 CSV 文件，共约 33,174 条景点数据
- CSV 字段：名字、链接、地址、介绍、开放时间、图片链接、评分、建议游玩时间、建议季节、门票、小贴士、Page
- 模拟用户数据：150用户 + 15000行为 + 2000收藏（待生成）

## 3. 编码规范
- **强制中文**: 所有对话、回答、解释以及生成的文档内容必须严格使用中文
- 所有注释使用大白话中文
- 注释覆盖率 ≥ 30%
- 遵循 PEP 8 规范
- 环境变量通过 `.env` 加载，严禁硬编码

## 7. 项目结构与上下文（自动维护）
- **上次更新时间**: 2026-03-01
- **核心功能**: 完成智能旅游推荐系统前后端闭环。后端提供用户认证、景点查询、混合推荐引擎（协同过滤+内容推荐+热门推荐+场景推荐）、LangChain RAG 智能帮搜问答管线。前端通过 Vue 3 + Element Plus 实现用户交互，包括登录/注册、首页（场景+个性化推荐）、景点探索（过滤和分页）、景点详情（收藏、打分、评论功能和专属AI导游）、我的收藏、以及 AI 智能帮搜对话页面（支持引用、意图标签和推荐卡片）。
- **目录结构说明**:
  - `backend/`: Python FastAPI 后端目录
    - `main.py`: 后端入口与 FastAPI 实例
    - `database.py`: SQLite 数据库连接
    - `routers/`: 路由目录（`auth.py`用户认证, `spots.py`景点接口, `recommend.py`推荐接口, `chat.py` AI对话接口）
    - `models/`: Pydantic 请求/响应模型定义
    - `ai/`: LangChain 与意图识别逻辑（`intent_recognizer.py`, `rag_pipeline.py`, `llm_client.py`, `rag_engine.py`）
    - `algorithms/`: 推荐算法实现（`collaborative.py`, `content_based.py`, `hybrid_recommender.py`）
    - `data/chroma_db/`: ChromaDB 向量数据库持久化目录
    - `data/travel.db`: SQLite 关系型数据库
    - `scripts/`: 数据生成和更新脚本（`update_db.py`, `generate_mock_comments.py`）
  - `frontend/`: Vue 3 + Vite 前端目录
    - `src/main.ts`: Vue 应用入口
    - `src/router/index.ts`: Vue 路由配置
    - `src/store/user.ts`: Pinia 用户状态管理
    - `src/api/`: API 请求模块 (`index.ts`, `spots.ts`, `chat.ts`)
    - `src/views/`: 页面视图
      - `Home.vue`: 首页与场景/个性化推荐
      - `Login.vue` / `Register.vue`: 用户认证
      - `Spot/SpotList.vue`: 景点列表与搜索过滤
      - `Spot/SpotDetail.vue`: 景点详情展示、打分、收藏、评论与专属 AI 导游抽屉
      - `AI/Chat.vue`: AI 智能帮搜与对话页面，支持会话管理
      - `Collections.vue`: 用户收藏列表
  - `citydata/`: 原始景点 CSV 数据
  - `.env`: 环境变量配置（包含 API Key 与数据库密码）
  - `task.json`: 任务追踪配置
  - `CLAUDE.md`: 本项目规范与上下文说明
