"""
意图识别与智能帮搜模块

大白话说明：
    这个模块负责"听懂用户在说什么"。

    用户可能说各种话，比如：
    - "北京有什么好玩的？" → 搜索意图
    - "故宫几点开门？" → 问答意图
    - "怎么收藏景点？" → 系统帮助意图
    - "你好" → 闲聊

    这个模块的工作：
    1. 判断用户的"意图"是什么（搜索/问答/帮助/闲聊）
    2. 如果是搜索，提取搜索条件（城市、类型、季节、人群等）
    3. 根据条件到数据库里查找匹配的景点
"""

import os
import re
import sys
import json
import sqlite3
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings

try:
    from ai.llm_client import get_llm_client
    from ai.rag_engine import get_rag_engine
    from database import DB_PATH
    from algorithms.user_profile_recommender import UserProfileRecommender
except ImportError:
    from llm_client import get_llm_client
    from rag_engine import get_rag_engine
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database import DB_PATH
    from algorithms.user_profile_recommender import UserProfileRecommender

settings = get_settings()


# 意图类型定义
INTENT_SEARCH = "search"       # 搜索景点
INTENT_QA = "qa"               # 景点问答
INTENT_HELP = "help"           # 系统使用帮助
INTENT_CHAT = "chat"           # 闲聊


class IntentRecognizer:
    """
    意图识别器

    大白话说明：
        用 LLM 判断用户说的话属于哪种意图，
        然后把请求分发到对应的处理流程。
    """

    def __init__(self):
        self.llm_client = get_llm_client()

    async def recognize(self, user_message: str) -> dict:
        """
        识别用户意图

        大白话说明：
            让 AI 分析用户的话，判断是搜索、问答、帮助还是闲聊。
            返回意图类型和置信度。

        参数：
            user_message: 用户输入的文本
        返回：
            {"intent": "search/qa/help/chat", "confidence": 0.0-1.0}
        """
        # 先用规则快速判断（比AI快很多）
        rule_result = self._rule_based_intent(user_message)
        if rule_result["confidence"] > 0.8:
            return rule_result

        # 规则判断不确定时，用 LLM 判断（但要有降级处理）
        try:
            instruction = """请判断以下用户输入属于哪种意图：
1. search - 用户想搜索/推荐景点（如"推荐几个xxx"、"有什么好玩的"、"想去xxx"）
2. qa - 用户在问某个景点的具体信息（如"几点开门"、"门票多少钱"、"怎么去"）
3. help - 用户在问系统怎么使用（如"怎么收藏"、"怎么注册"）
4. chat - 普通闲聊（如"你好"、"谢谢"）

请返回JSON格式：{"intent": "search/qa/help/chat", "confidence": 0.0-1.0}"""

            result = await self.llm_client.extract_json(user_message, instruction)

            if result and "intent" in result:
                return {
                    "intent": result["intent"],
                    "confidence": result.get("confidence", 0.7),
                }
        except Exception as e:
            print(f"⚠️ LLM意图识别失败，使用规则结果: {e}")
        
        # 兜底：使用规则判断的结果
        return rule_result

    def _rule_based_intent(self, text: str) -> dict:
        """
        基于规则的快速意图识别

        大白话说明：
            不需要调AI，直接看关键词就能判断。
            比如包含"推荐"、"有什么好玩的"就是搜索意图；
            包含"几点"、"门票"就是问答意图。
            这样大部分请求可以跳过AI调用，响应更快。
        """
        # 搜索意图的关键词（包含地名+动词模式也算搜索）
        search_keywords = [
            "推荐", "有什么好玩", "想去", "带孩子", "带老人",
            "适合", "哪里好玩", "去哪", "旅游", "度假",
            "亲子", "风景", "景点推荐", "哪些景点",
            "赏花", "赏红叶", "看雪", "泡温泉",
            "有什么", "哪里有", "哪里的", "什么好", "好去处",
            "玩什么", "逛什么", "吃什么", "最多", "最好",
            "游玩", "打卡", "网红", "必去", "值得去",
            # ✅ 新增：更自然的表达方式
            "我在", "现在在", "我想要", "我希望", "希望",
            "历史文化", "自然风光", "人文", "古迹", "博物馆",
            "找个", "找几个", "给我推", "帮我找", "想看",
            "逛逛", "散步", "周末", "假期", "出游",
        ]

        # 问答意图的关键词
        qa_keywords = [
            "几点", "开放时间", "门票", "怎么去", "地址",
            "介绍一下", "评分", "多少钱", "在哪",
            "开不开", "免费吗", "需要预约",
            "营业时间", "票价", "预约", "排队",
        ]

        # 系统帮助的关键词
        help_keywords = [
            "怎么注册", "怎么登录", "怎么收藏", "怎么评分",
            "怎么使用", "怎么操作", "字体", "设置",
        ]

        # 闲聊的关键词
        chat_keywords = [
            "你好", "嗨", "hello", "谢谢", "感谢", "再见",
            "你是谁", "你叫什么",
        ]

        # 按优先级匹配
        for kw in help_keywords:
            if kw in text:
                return {"intent": INTENT_HELP, "confidence": 0.9}

        for kw in search_keywords:
            if kw in text:
                return {"intent": INTENT_SEARCH, "confidence": 0.85}

        for kw in qa_keywords:
            if kw in text:
                return {"intent": INTENT_QA, "confidence": 0.85}

        for kw in chat_keywords:
            if kw in text:
                return {"intent": INTENT_CHAT, "confidence": 0.9}

        # 都不匹配，置信度低，需要LLM判断
        return {"intent": INTENT_QA, "confidence": 0.3}


class SmartSearcher:
    """
    智能帮搜器

    大白话说明：
        当用户说"我想带孩子去北京玩"这种自然语言时，
        这个类负责：
        1. 提取搜索条件：城市=北京，人群=亲子
        2. 到数据库里查找匹配的景点
        3. 返回排序后的结果
    """

    def __init__(self):
        self.llm_client = get_llm_client()

    def _normalize_city(self, city_raw: str) -> str:
        """
        城市名归一化

        大白话说明：
            用户可能说"厦门市思明区"、"北京市海淀区"，
            但我们数据库里存的是"厦门""北京"。
            这个方法把用户说的城市名清理成数据库能匹配的格式。
        """
        if not city_raw:
            return city_raw
        # 去掉"市""区""县""自治州"等行政后缀，保留核心城市名
        city = re.sub(r'(市|区|县|自治州|自治县|地区|特别行政区).*', '', city_raw)
        # 如果清理后为空（比如输入就是"区"），返回原始值
        return city.strip() if city.strip() else city_raw

    async def extract_conditions(self, user_message: str) -> dict:
        """
        从自然语言中提取搜索条件

        大白话说明：
            让 AI 从用户的话里提取出结构化的搜索条件。
            比如 "秋天带老人去南京看枫叶" 提取出：
            {
                "city": "南京",
                "season": "秋",
                "target_group": "老年",
                "keywords": ["枫叶"]
            }
        """
        instruction = """请从用户的旅游需求描述中提取搜索条件，返回JSON格式：
{
    "city": "目标城市名，只写城市核心名称，不要带'市''区''县'后缀。比如用户说'厦门市思明区'就填'厦门'，说'北京市海淀区'就填'北京'。如果没提到城市就填null",
    "spot_type": "景点类型：自然风光/历史文化/宗教场所/主题乐园/博物馆/现代都市/园林公园/乡村田园（如果能判断的话，否则为null）",
    "season": "推荐季节：春/夏/秋/冬（如果提到的话，否则为null）",
    "target_group": "适合人群：亲子/老年/情侣/学生/摄影/探险（如果能判断的话，否则为null）",
    "keywords": ["关键词列表，提取用户需求中有实际搜索价值的词，去掉'最多''好玩'这类虚词"]
}
注意：
1. city 只填城市名，不要带行政区划后缀
2. keywords 要提取有利于搜索匹配的实体词（如'咖啡''海滩''古镇'），过滤掉纯修饰词
3. 如果某个字段无法判断就填null"""

        result = await self.llm_client.extract_json(user_message, instruction)
        if not result:
            return {}

        # 对城市名做二次归一化（兜底，防止 LLM 不听话）
        if result.get("city"):
            result["city"] = self._normalize_city(result["city"])

        return result

    def search_spots(self, conditions: dict, limit: int = 10) -> list[dict]:
        """
        根据结构化条件搜索景点

        大白话说明：
            拿到提取的搜索条件后，构建SQL查询语句，
            从数据库里找出匹配的景点，按评分排序返回。
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 构建动态 WHERE 条件
        where_parts = ["1=1"]  # 永真条件（方便后续 AND 拼接）
        params = []

        # 城市过滤（用 LIKE 模糊匹配，兼容"厦门"匹配"厦门"的情况）
        city = conditions.get("city")
        if city:
            # 先归一化城市名
            city = self._normalize_city(city)
            where_parts.append("city LIKE ?")
            params.append(f"%{city}%")

        # 景点类型过滤
        spot_type = conditions.get("spot_type")
        if spot_type:
            where_parts.append("spot_type LIKE ?")
            params.append(f"%{spot_type}%")

        # 季节过滤
        season = conditions.get("season")
        if season:
            where_parts.append("suggest_season LIKE ?")
            params.append(f"%{season}%")

        # 人群过滤
        target_group = conditions.get("target_group")
        if target_group:
            where_parts.append("target_group LIKE ?")
            params.append(f"%{target_group}%")

        # 关键词搜索（在名称和介绍中搜索）
        keywords = conditions.get("keywords", [])
        for kw in keywords[:3]:  # 最多3个关键词
            where_parts.append("(name LIKE ? OR description LIKE ?)")
            params.append(f"%{kw}%")
            params.append(f"%{kw}%")

        where_clause = " AND ".join(where_parts)
        params.append(limit)

        sql = f"""
            SELECT id, name, city, rating, image_url, spot_type,
                   target_group, suggest_time, open_time, address, description, tips
            FROM spots
            WHERE {where_clause}
            ORDER BY
                CASE WHEN rating IS NOT NULL THEN 0 ELSE 1 END,
                rating DESC
            LIMIT ?
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "spot_id": row[0],
                "name": row[1],
                "city": row[2],
                "rating": row[3],
                "image_url": row[4],
                "spot_type": row[5],
                "target_group": row[6],
                "suggest_time": row[7],
                "open_time": row[8],
                "address": row[9],
                "description": row[10],
                "tips": row[11],
            })

        return results


def _extract_tags(spot: dict) -> list[str]:
    """从景点信息中提取 1-3 个标签。"""
    tags = []

    for field in ["spot_type", "target_group"]:
        raw = spot.get(field)
        if not raw:
            continue

        values = []
        if isinstance(raw, list):
            values = [str(v).strip() for v in raw if str(v).strip()]
        else:
            text = str(raw).strip()
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    values = [str(v).strip() for v in parsed if str(v).strip()]
                elif isinstance(parsed, str):
                    values = [parsed.strip()]
            except (json.JSONDecodeError, TypeError):
                for sep in ["、", "，", ",", "/", "|", " "]:
                    text = text.replace(sep, ",")
                values = [v.strip() for v in text.split(",") if v.strip()]

        for v in values:
            if v and v not in tags:
                tags.append(v)

    return tags[:3] if tags else ["精选推荐"]


def _to_card_spot(spot: dict) -> dict:
    """把搜索结果统一成前端卡片结构。"""
    spot_id = spot.get("id") or spot.get("spot_id")
    name = (spot.get("name") or "未知景点").strip()

    brief_source = (
        spot.get("description")
        or spot.get("tips")
        or spot.get("open_time")
        or ""
    )
    brief = str(brief_source).strip().replace("\n", " ")

    return {
        "id": spot_id,
        "spot_id": spot_id,
        "name": name[:18],
        "brief": brief[:50],
        "tags": _extract_tags(spot),
        "image_url": spot.get("image_url") or "",
        "city": spot.get("city") or "",
        "rating": spot.get("rating"),
    }


class ChatService:
    """
    聊天服务 - AI交互的统一入口

    大白话说明：
        这是前端调用AI功能的唯一入口。
        不管用户想干什么（搜索/问答/帮助/闲聊），都走这一个接口。
        内部会自动识别意图，分发到对应的处理器。
    """

    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.smart_searcher = SmartSearcher()
        self.profile_engine = UserProfileRecommender(DB_PATH)
        self.rag_engine = None  # 延迟初始化（因为可能向量库还没建好）

    def _get_rag(self):
        """延迟获取 RAG 引擎"""
        if self.rag_engine is None:
            try:
                self.rag_engine = get_rag_engine()
            except Exception as e:
                print(f"⚠️ RAG引擎初始化失败: {e}")
        return self.rag_engine

    async def process_message(self, user_message: str, user_id: int = None,
                               history: list[dict] = None,
                               user_profile: dict = None) -> dict:
        """
        处理用户消息（总入口）

        大白话说明：
            1. 先识别意图
            2. 根据意图分发处理（搜索意图会结合用户画像做个性化排序）
            3. 返回统一格式的结果

        参数：
            user_message: 用户消息文本
            user_id: 用户ID（可选，用于个性化）
            history: 对话历史
            user_profile: 用户画像字典（city/travel_style/interest_tags/preferred_season）
        返回：
            {
                "reply": "AI的回复文本",
                "intent": "识别的意图类型",
                "spots": [搜索到的景点列表]（如果是搜索意图）,
                "sources": [参考来源]（如果是问答意图）
            }
        """
        # 第一步：识别意图
        intent_result = await self.intent_recognizer.recognize(user_message)
        intent = intent_result["intent"]
        print(f"🎯 意图识别: {intent} (置信度: {intent_result.get('confidence', '?')})")

        # 第二步：根据意图分发处理
        if intent == INTENT_SEARCH:
            return await self._handle_search(user_message, user_id=user_id, user_profile=user_profile)
        elif intent == INTENT_QA:
            return await self._handle_qa(user_message, history)
        elif intent == INTENT_HELP:
            return await self._handle_help(user_message)
        elif intent == INTENT_CHAT:
            return await self._handle_chat(user_message)
        else:
            return await self._handle_qa(user_message, history)

    async def _handle_search(self, user_message: str, user_id: int = None,
                              user_profile: dict = None) -> dict:
        """
        处理搜索意图

        大白话：提取搜索条件 → （用户画像兜底城市）→ 查数据库 → 画像重排 → AI生成推荐语
        """
        print(f"\n🔧 进入 _handle_search 处理搜索意图")
        # 提取搜索条件（即使失败也继续，用空条件搜索）
        try:
            conditions = await self.smart_searcher.extract_conditions(user_message)
            print(f"🔎 提取的搜索条件（LLM）: {conditions}")
        except Exception as e:
            print(f"⚠️ 搜索条件提取失败，使用空条件: {e}")
            conditions = {}

        # ✅ 关键改进1：用户画像城市兜底
        # 如果对话里没有提到城市，但用户注册了所在城市，则用注册城市作为默认过滤
        profile = user_profile or {}
        if not conditions.get("city") and profile.get("city"):
            conditions["city"] = self.smart_searcher._normalize_city(profile["city"])
            print(f"📍 城市兜底（来自用户画像）: {conditions['city']}")

        # ✅ 关键改进2：用户偏好类型兜底
        # 如果对话没有提到景点类型，但用户有旅游风格设置，则作为辅助条件
        if not conditions.get("spot_type") and profile.get("travel_style"):
            import json as _json
            try:
                styles = _json.loads(profile["travel_style"]) if isinstance(profile["travel_style"], str) else []
                if styles:
                    conditions.setdefault("_preferred_types", styles)
            except Exception:
                pass

        # 搜索景点
        spots = self.smart_searcher.search_spots(conditions, limit=30)
        print(f"🔍 搜索到 {len(spots)} 个景点")

        # ✅ 关键改进3：只要有用户ID就做画像重排，并修复综合排序逻辑
        if user_id and spots:
            try:
                spot_ids = [s["spot_id"] for s in spots]
                score_map = self.profile_engine.calculate_batch_scores(user_id, spot_ids)

                # 给每个景点附上画像匹配分（0-100）
                for s in spots:
                    s["match_score"] = score_map.get(s["spot_id"], 0.0)

                # 归一化景点评分到 0-100（和匹配分同量纲，才能加权合并）
                max_rating = max((s.get("rating") or 0 for s in spots), default=5.0) or 5.0
                for s in spots:
                    rating_norm = ((s.get("rating") or 0) / max_rating) * 100
                    profile_score = s["match_score"]
                    # 综合分：评分权重 40% + 画像匹配权重 60%
                    s["combined_score"] = 0.4 * rating_norm + 0.6 * profile_score

                spots.sort(key=lambda s: s.get("combined_score", 0), reverse=True)
                print(f"🎯 画像重排完成，Top3匹配分: "
                      f"{[round(s.get('combined_score',0), 1) for s in spots[:3]]}")
            except Exception as e:
                print(f"⚠️ 画像重排失败，降级为评分排序: {e}")
                spots.sort(key=lambda s: s.get("rating") or 0, reverse=True)

        # 取前 5 条推荐
        card_spots_raw = spots[:5] if len(spots) >= 5 else spots
        card_spots = [_to_card_spot(s) for s in card_spots_raw]

        # 让AI生成个性化推荐语
        if card_spots:
            try:
                spot_names = [f"{s['name']}({s['city']})" for s in card_spots]
                # 把用户画像信息告诉 AI，让回复更贴心
                profile_info = ""
                if profile.get("city"):
                    profile_info += f"用户所在城市：{profile['city']}。"
                if profile.get("travel_style"):
                    profile_info += f"旅游风格：{profile['travel_style']}。"

                llm = get_llm_client()
                reply = await llm.chat(
                    f"用户说：{user_message}\n{profile_info}\n"
                    f"根据用户画像和语义理解，为他推荐了：{', '.join(spot_names)}\n"
                    f"请用友好自然的口吻（2-3句话）说明为什么这些景点适合他，突出与他需求/位置/偏好的契合点。",
                    system_prompt=(
                        "你是一个懂用户的旅游向导，了解他的位置和偏好，像老朋友一样推荐景点。"
                        "不要说'根据资料'或'为您查到'这类机械的话，直接说'这几个地方...'或'我觉得...'。"
                    )
                )
            except Exception as e:
                print(f"⚠️ AI推荐语生成失败: {e}")
                reply = f"我为你找到了 {len(card_spots)} 个不错的景点，快看看吧！🗺️"

            return {
                "reply": reply,
                "intent": INTENT_SEARCH,
                "spots": card_spots,
                "conditions": conditions,
            }
        else:
            # 结构化搜索没结果，退化到 RAG 向量检索
            city = conditions.get("city")
            print(f"⚠️ 结构化搜索未找到结果，退化为 RAG 问答（城市过滤: {city}）...")
            return await self._handle_qa_with_city(user_message, None, city_filter=city)

    async def _handle_qa(self, user_message: str, history: list[dict] = None) -> dict:
        """处理问答意图（不带城市过滤）"""
        return await self._handle_qa_with_city(user_message, history, city_filter=None)

    async def _handle_qa_with_city(self, user_message: str, history: list[dict] = None,
                                    city_filter: str = None) -> dict:
        """
        处理问答意图（支持城市过滤）

        大白话：用 RAG 检索相关文档 → 让AI参考文档回答
                可选带城市过滤，让向量检索更精准
        """
        print(f"\n🔧 进入 _handle_qa 处理问答意图 (城市过滤: {city_filter})")
        rag = self._get_rag()
        if rag:
            print(f"✅ RAG 引擎可用，准备检索...")
            result = await rag.answer_question(user_message, history, city_filter=city_filter)
            print(f"📚 RAG 检索返回 {len(result.get('sources', []))} 个来源")
            return {
                "reply": result["answer"],
                "intent": INTENT_QA,
                "sources": result.get("sources", []),
            }
        else:
            # RAG不可用，直接用LLM回答
            print(f"⚠️ RAG 引擎不可用，使用纯 LLM 回答")
            llm = get_llm_client()
            reply = await llm.chat(
                user_message,
                system_prompt="你是一个经验丰富的旅游向导，像熟悉当地的老朋友一样自然地回答问题。"
            )
            return {"reply": reply, "intent": INTENT_QA, "sources": []}

    async def _handle_help(self, user_message: str) -> dict:
        """
        处理系统帮助意图

        大白话：搜索FAQ知识库回答系统使用问题
        """
        rag = self._get_rag()
        if rag:
            faq_docs = rag.search_faq(user_message, n_results=3)
            if faq_docs:
                context = [doc["document"] for doc in faq_docs]
                llm = get_llm_client()
                reply = await llm.chat_with_context(
                    user_message, context,
                    system_prompt="你是旅行小助手的使用指南助手。请根据参考资料回答用户关于系统使用的问题。"
                )
                return {"reply": reply, "intent": INTENT_HELP}

        # 没有FAQ可用，用LLM直接回答
        llm = get_llm_client()
        reply = await llm.chat(
            user_message,
            system_prompt="你是旅行小助手。用户在问系统如何使用，请友好地回答。"
        )
        return {"reply": reply, "intent": INTENT_HELP}

    async def _handle_chat(self, user_message: str) -> dict:
        """
        处理闲聊意图

        大白话：随便聊聊，不需要搜索任何东西
        """
        llm = get_llm_client()
        reply = await llm.chat(
            user_message,
            system_prompt="你是旅行小助手🗺️，一个友好的旅游AI助手。简短地回应用户的闲聊，适当引导他们使用旅游推荐功能。"
        )
        return {"reply": reply, "intent": INTENT_CHAT}


# 全局单例
_chat_service = None

def get_chat_service() -> ChatService:
    """获取聊天服务单例"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
