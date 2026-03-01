"""
TravelAI 后端入口文件

大白话说明：
    这是整个后端服务的"大门"。
    FastAPI 应用从这里启动，所有的 API 路由都在这里注册。
    启动服务后，浏览器打开 http://localhost:8000/docs 就能看到 API 文档。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db_async
from config import get_settings

# 拿到全局配置
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    大白话说明：
        这个函数在 FastAPI 启动时执行一些初始化工作（比如创建数据库表），
        在关闭时执行清理工作。yield 之前的代码是"启动时执行"，之后的是"关闭时执行"。
    """
    # --- 启动时 ---
    print("🚀 TravelAI 后端服务启动中...")
    # 初始化数据库（建表、建索引）
    await init_db_async()
    print("✅ 所有初始化工作完成，服务就绪！")
    
    yield  # 把控制权交给 FastAPI，开始处理请求
    
    # --- 关闭时 ---
    print("👋 TravelAI 后端服务关闭中...")


# 创建 FastAPI 应用实例
app = FastAPI(
    title="TravelAI 智能旅游推荐系统",
    description="基于混合推荐算法的 AI 交互旅游推荐系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置跨域访问（CORS）
# 大白话：允许前端（Vue）从不同的端口/域名访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允许所有来源（开发环境用，生产环境要限制）
    allow_credentials=True,        # 允许携带 Cookie
    allow_methods=["*"],           # 允许所有 HTTP 方法（GET、POST、PUT、DELETE等）
    allow_headers=["*"],           # 允许所有请求头
)


# ============================================
# 注册 API 路由
# ============================================
from routers import auth, spots, recommend, chat

app.include_router(auth.router, prefix="/api")
app.include_router(spots.router, prefix="/api")
app.include_router(recommend.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/", tags=["系统"])
async def root():
    """
    根路径 - 用来检查服务是否正常运行

    大白话说明：
        浏览器打开 http://localhost:8000/ 看到这个响应，说明服务启动成功了
    """
    return {
        "message": "🗺️ TravelAI 智能旅游推荐系统 API 运行中",
        "version": "1.0.0",
        "docs": "访问 /docs 查看 API 文档",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查接口

    大白话说明：
        前端或者运维可以定期访问这个接口，检查后端是否还活着
    """
    return {"status": "healthy"}


# ============================================
# 如果直接运行这个文件，就启动服务
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",                    # 指定应用入口
        host=settings.APP_HOST,        # 监听地址
        port=settings.APP_PORT,        # 端口号
        reload=settings.APP_DEBUG,     # 开发模式下开启热重载
    )
