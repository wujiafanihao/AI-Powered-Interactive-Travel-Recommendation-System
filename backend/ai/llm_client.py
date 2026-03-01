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
import time
import random
import re
from typing import Optional, Callable, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings

settings = get_settings()


async def retry_with_exponential_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Any:
    """
    带有指数退避和抖动的重试装饰器
    
    大白话说明：
        当API调用失败时，自动重试，每次等待时间越来越长。
        还会添加随机抖动，避免多个请求同时重试。
    """
    retries = 0
    last_exception = None
    
    while retries < max_retries:
        try:
            return await func()
        except Exception as e:
            last_exception = e
            retries += 1
            
            if retries >= max_retries:
                break
            
            # 计算延迟时间
            delay = min(base_delay * (exponential_base ** (retries - 1)), max_delay)
            
            # 添加抖动
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)
            
            print(f"⚠️ API调用失败，{delay:.1f}秒后重试 (重试 {retries}/{max_retries}): {str(e)}")
            await asyncio_sleep(delay)
    
    raise last_exception


def asyncio_sleep(seconds: float):
    """异步睡眠辅助函数"""
    import asyncio
    return asyncio.sleep(seconds)


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

        # 调用 LLM，带有重试机制
        try:
            async def _call():
                response = await self.llm.ainvoke(messages)
                return response.content
            
            return await retry_with_exponential_backoff(_call)
        except Exception as e:
            print(f"❌ LLM调用失败，使用降级回复: {str(e)}")
            return self._get_fallback_chat_response(user_message)

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
        # 默认系统提示：让AI像一个经验丰富的旅游向导自然地回答
        if not system_prompt:
            system_prompt = """你是一个经验丰富、热情友好的旅游向导，名叫"旅行小助手"。
你对中国各地的景点、美食、文化了如指掌，就像一个在当地生活多年的老朋友。

关于回答风格的要求（非常重要）：
1. 用自然、流畅的口吻回答，就像面对面聊天一样
2. 绝对不要说"根据参考资料"、"根据您提供的信息"、"参考资料显示"这类话
3. 绝对不要暴露你是在查阅数据库或文档，要让用户感觉你就是知道这些
4. 直接回答问题，语气像个热心的当地朋友："哎这个我太熟了！"、"说起这个地方..."
5. 适当使用emoji让回答更生动亲切
6. 如果涉及门票、开放时间等信息，自然地提醒：最好出发前再确认一下哦
7. 如果参考信息不够用，就大方结合你的知识补充，别说"抱歉资料有限"这种话"""

        # 把参考文档拼成一段文字
        context_text = "\n\n---\n\n".join(context_docs)

        # 组装完整提示（不要让AI知道这是"参考资料"，而是当作它自己的"记忆"）
        full_prompt = f"""{system_prompt}

以下是你对相关景点和地方的了解（这些是你的知识，不需要告诉用户你是从哪里知道的）：
{context_text}

请根据你的了解，自然流畅地回答用户的问题。"""

        messages = [
            SystemMessage(content=full_prompt),
            HumanMessage(content=user_message),
        ]

        # 调用 LLM，带有重试机制
        try:
            async def _call():
                response = await self.llm.ainvoke(messages)
                return response.content
            
            return await retry_with_exponential_backoff(_call)
        except Exception as e:
            print(f"❌ LLM调用失败，使用降级回复: {str(e)}")
            return self._get_fallback_rag_response(user_message, context_docs)

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

        # 调用 LLM，带有重试机制
        try:
            async def _call():
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
            
            return await retry_with_exponential_backoff(_call)
        except Exception as e:
            print(f"❌ JSON提取失败，使用本地规则提取: {str(e)}")
            return self._extract_json_locally(user_message, instruction)

    def _get_fallback_chat_response(self, user_message: str) -> str:
        """
        当LLM不可用时，返回一个降级回复
        
        大白话说明：
            API挂了的时候，用本地的简单回复来救场。
        """
        # 简单的关键词匹配回复
        user_lower = user_message.lower()
        
        if any(kw in user_lower for kw in ["你好", "嗨", "hello", "hi"]):
            return "你好！😊 我是旅行小助手，很高兴为你服务！有什么旅游问题可以问我哦～"
        
        if any(kw in user_lower for kw in ["推荐", "好玩", "去哪", "旅游"]):
            return "这个问题很有意思！让我帮你想想... 你可以试试在探索景点页面浏览，或者告诉我具体想去哪个城市，我来帮你推荐！🗺️"
        
        if any(kw in user_lower for kw in ["谢谢", "感谢"]):
            return "不客气！😊 能帮到你我很开心！还有其他问题随时问我哦～"
        
        # 默认回复
        return "我明白你的意思了！不过我现在稍微有点忙，你可以稍后再试，或者直接去探索景点页面看看有什么好玩的地方～ 🎈"

    def _get_fallback_rag_response(self, user_message: str, context_docs: list[str]) -> str:
        """
        当RAG的LLM调用失败时，返回基于上下文的简单回复
        """
        if context_docs:
            # 从上下文中提取一些信息
            first_doc = context_docs[0][:200] + "..." if len(context_docs[0]) > 200 else context_docs[0]
            return f"关于这个问题，我找到了一些相关信息：\n\n{first_doc}\n\n希望这些信息对你有帮助！😊"
        
        return self._get_fallback_chat_response(user_message)

    def _extract_json_locally(self, user_message: str, instruction: str) -> dict:
        """
        当LLM不可用时，用本地规则简单提取一些信息
        
        大白话说明：
            API挂了的时候，用简单的关键词匹配来提取搜索条件。
        """
        result = {}
        
        # 提取城市名
        city_pattern = r'(北京|上海|广州|深圳|杭州|南京|成都|重庆|西安|武汉|长沙|青岛|大连|厦门|苏州|无锡|宁波|福州|泉州|珠海|佛山|东莞|中山|惠州|温州|嘉兴|绍兴|台州|金华|衢州|舟山|丽水|合肥|芜湖|蚌埠|淮南|马鞍山|淮北|铜陵|安庆|黄山|滁州|阜阳|宿州|六安|亳州|池州|宣城|南昌|景德镇|萍乡|九江|新余|鹰潭|赣州|吉安|宜春|抚州|上饶|济南|青岛|淄博|枣庄|东营|烟台|潍坊|济宁|泰安|威海|日照|临沂|德州|聊城|滨州|菏泽|郑州|开封|洛阳|平顶山|安阳|鹤壁|新乡|焦作|濮阳|许昌|漯河|三门峡|南阳|商丘|信阳|周口|驻马店|武汉|黄石|十堰|宜昌|襄阳|鄂州|荆门|孝感|荆州|黄冈|咸宁|随州|长沙|株洲|湘潭|衡阳|邵阳|岳阳|常德|张家界|益阳|郴州|永州|怀化|娄底|广州|韶关|深圳|珠海|汕头|佛山|江门|湛江|茂名|肇庆|惠州|梅州|汕尾|河源|阳江|清远|东莞|中山|潮州|揭阳|云浮|南宁|柳州|桂林|梧州|北海|防城港|钦州|贵港|玉林|百色|贺州|河池|来宾|崇左|海口|三亚|三沙|儋州|成都|自贡|攀枝花|泸州|德阳|绵阳|广元|遂宁|内江|乐山|南充|眉山|宜宾|广安|达州|雅安|巴中|资阳|贵阳|六盘水|遵义|安顺|昆明|曲靖|玉溪|保山|昭通|丽江|普洱|临沧|拉萨|日喀则|昌都|林芝|山南|那曲|西安|铜川|宝鸡|咸阳|渭南|延安|汉中|榆林|安康|商洛|兰州|嘉峪关|金昌|白银|天水|武威|张掖|平凉|酒泉|庆阳|定西|陇南|西宁|海东|银川|石嘴山|吴忠|固原|中卫|乌鲁木齐|克拉玛依|吐鲁番|哈密)'
        city_match = re.search(city_pattern, user_message)
        if city_match:
            result["city"] = city_match.group(1)
        
        # 提取人群
        if any(kw in user_message for kw in ["孩子", "小孩", "亲子", "宝宝", "儿童"]):
            result["target_group"] = "亲子"
        elif any(kw in user_message for kw in ["老人", "老年", "爸妈", "父母"]):
            result["target_group"] = "老年"
        elif any(kw in user_message for kw in ["情侣", "约会", "爱人", "女朋友", "男朋友"]):
            result["target_group"] = "情侣"
        elif any(kw in user_message for kw in ["学生", "同学", "校园"]):
            result["target_group"] = "学生"
        
        # 提取景点类型
        if any(kw in user_message for kw in ["山", "水", "自然", "风景", "公园", "森林"]):
            result["spot_type"] = "自然风光"
        elif any(kw in user_message for kw in ["历史", "文化", "古迹", "博物馆", "寺庙"]):
            result["spot_type"] = "历史文化"
        elif any(kw in user_message for kw in ["主题乐园", "游乐场", "迪士尼", "欢乐谷"]):
            result["spot_type"] = "主题乐园"
        
        # 提取关键词
        keywords = []
        for kw in ["古镇", "海滩", "温泉", "滑雪", "赏花", "红叶", "咖啡", "美食", "购物"]:
            if kw in user_message:
                keywords.append(kw)
        if keywords:
            result["keywords"] = keywords
        
        return result


# 全局单例
_llm_client = None

def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
