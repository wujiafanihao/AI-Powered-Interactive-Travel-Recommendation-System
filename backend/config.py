"""
TravelAI 配置管理模块

大白话说明：
    这个文件的作用就是把 .env 文件里的配置读出来，
    让其他模块可以方便地使用这些配置（比如数据库路径、API密钥等）。
    用 pydantic-settings 来做，好处是自动校验配置项是否合法。
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    项目全局配置类

    大白话说明：
        所有的配置项都在这里定义，程序启动时会自动从 .env 文件里读取对应的值。
        如果 .env 里没有，就用这里写的默认值。
    """

    # --- AI 模型配置 ---
    # ModelScope API 的地址（兼容 OpenAI 格式，可以直接用 langchain-openai 来调用）
    LLM_BASE_URL: str = "https://api-inference.modelscope.cn/v1/"
    # API 密钥，千万别硬编码到代码里，要从 .env 读
    LLM_API_KEY: str = ""
    # 大语言模型的名字，用来聊天和生成回答
    LLM_MODEL_NAME: str = "deepseek-ai/DeepSeek-V3.2"
    # 嵌入模型的名字，用来把文本变成向量（数字数组）
    EMBEDDING_MODEL_NAME: str = "Qwen/Qwen3-Embedding-8B"

    # --- 数据库配置 ---
    # SQLite 数据库文件的路径（相对于 backend 目录）
    DATABASE_PATH: str = "data/travel.db"
    # ChromaDB（向量数据库）的存储路径
    CHROMA_DB_PATH: str = "data/chroma_db"

    # --- JWT 认证配置 ---
    # JWT 加密用的密钥
    JWT_SECRET_KEY: str = "travelai-secret-key-2026-xianyu-graduation"
    # JWT 加密算法
    JWT_ALGORITHM: str = "HS256"
    # Token 过期时间（分钟），1440分钟 = 24小时
    JWT_EXPIRE_MINUTES: int = 1440

    # --- 应用配置 ---
    # 服务监听地址，0.0.0.0 表示允许外部访问
    APP_HOST: str = "0.0.0.0"
    # 服务端口号
    APP_PORT: int = 8000
    # 是否开启调试模式
    APP_DEBUG: bool = True

    class Config:
        """
        告诉 pydantic-settings 去哪里找 .env 文件
        """
        # .env 文件放在项目根目录（即 backend 的上一级）
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置的单例函数

    大白话说明：
        用 lru_cache 装饰器，保证整个程序运行期间只创建一次 Settings 对象，
        后面再调用就直接返回之前创建好的，避免重复读文件。
    """
    return Settings()
