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
- **上次更新时间**: 2026-03-01 (初始化)
- **核心功能**: 项目初始化中
- **目录结构说明**: 待任务全清后更新
