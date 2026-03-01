"""
LLM 客户端 - 封装 ModelScope API 调用

大白话说明：
    这个模块封装了和大语言模型（DeepSeek-V3.2）通信的功能。
    使用 LangChain + OpenAI 兼容格式的接口调用 ModelScope API。

    主要功能：
    1. 普通对话（直接和AI聊天）
    2. 带上下文的对话（把检索到的文档一起发给AI，让它参考着回答）
    3. 结构化输出（让AI返回JSON格式的结果，比如提取搜索条件）
"""

import os
import sys
import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings

settings = get_settings()


class LLMClient:
    """
    大语言模型客户端

    大白话说明：
        这就是和AI对话的"传话筒"。
        你把问题和参考资料给它，它帮你发给AI，然后把AI的回答拿回来。
    """

    def __init__(self):
        """
        初始化LLM客户端

        大白话：连接到 ModelScope 的 DeepSeek-V3.2 模型
        """
        self.llm = ChatOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL_NAME,
            temperature=0.7,       # 创造性程度，0.7比较平衡
            max_tokens=2048,       # 最大回复长度
            timeout=30,            # 超时时间30秒
        )

    async def chat(self, user_message: str, system_prompt: str = None,
                   history: list[dict] = None) -> str:
        """
        和 AI 进行对话

        大白话说明：
            最基础的对话功能。发一句话，AI回一句话。
            可以携带聊天历史，实现多轮对话。

        参数：
            user_message: 用户说的话
            system_prompt: 系统提示词（告诉AI它的角色是什么）
            history: 历史对话 [{"role": "user/assistant", "content": "..."}]
        返回：
            AI的回答文本
        """
        messages = []

        # 系统提示
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        # 历史对话
        if history:
            for msg in history[-10:]:  # 最多带10轮历史，太多了AI会糊涂
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # 当前问题
        messages.append(HumanMessage(content=user_message))

        # 调用 LLM
        response = await self.llm.ainvoke(messages)
        return response.content

    async def chat_with_context(self, user_message: str, context_docs: list[str],
                                 system_prompt: str = None) -> str:
        """
        带上下文文档的对话（RAG核心）

        大白话说明：
            这是 RAG（检索增强生成）的核心方法。
            工作流程：
            1. 先从向量数据库检索出相关文档（context_docs）
            2. 把文档和用户问题一起发给AI
            3. AI参考文档内容回答问题

            这样AI回答的内容更准确，因为有"参考资料"做支撑。

        参数：
            user_message: 用户问题
            context_docs: 检索到的相关文档列表
            system_prompt: 系统提示词
        """
        # 默认系统提示：告诉AI要根据参考资料回答
        if not system_prompt:
            system_prompt = """你是一个专业的旅游助手，名叫"旅行小助手"。
请根据以下参考资料回答用户的问题。
回答要求：
1. 优先使用参考资料中的信息
2. 如果参考资料不足以回答，可以结合你的知识补充
3. 回答要简洁、实用、友好
4. 适当使用emoji让回答更生动
5. 如果涉及门票、开放时间等信息，提醒用户出行前确认最新信息"""

        # 把参考文档拼成一段文字
        context_text = "\n\n---\n\n".join(context_docs)

        # 组装完整提示
        full_prompt = f"""{system_prompt}

参考资料：
{context_text}

请根据以上参考资料回答用户问题。"""

        messages = [
            SystemMessage(content=full_prompt),
            HumanMessage(content=user_message),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content

    async def extract_json(self, user_message: str, instruction: str) -> dict:
        """
        让AI提取结构化JSON数据

        大白话说明：
            有时候我们需要AI不是"自由回答"，而是返回固定格式的数据。
            比如从"我想带孩子去北京玩"这句话里提取出：
            {"city": "北京", "target_group": "亲子"}

            这个方法就是干这个的。

        参数：
            user_message: 用户原始输入
            instruction: 提取指令（告诉AI要提取什么）
        返回：
            解析后的字典
        """
        prompt = f"""{instruction}

用户输入：{user_message}

请只返回JSON格式的结果，不要包含其他文字。确保JSON格式正确。"""

        messages = [
            SystemMessage(content="你是一个数据提取助手，只返回JSON格式的结果，不包含任何其他文字或标记。"),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        text = response.content.strip()

        # 尝试提取JSON块
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 如果解析失败，返回空字典
            return {}


# 全局单例
_llm_client = None

def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
