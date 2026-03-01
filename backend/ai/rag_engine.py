"""
RAG 检索增强生成引擎

大白话说明：
    RAG = Retrieval Augmented Generation（检索增强生成）
    
    它解决的问题是：AI大模型虽然很聪明，但它不知道我们系统里
    有哪些景点、景点的具体信息是什么。
    
    RAG的工作方式：
    1. 用户问"北京有什么好玩的？"
    2. 先把这个问题变成向量
    3. 在 ChromaDB 里找最相关的几个景点文档
    4. 把这些文档作为"参考资料"连同问题一起发给AI
    5. AI参考这些资料生成回答
    
    这样AI的回答就不是"瞎编"，而是基于我们实际数据的。
"""

import os
import sys
import chromadb
from openai import OpenAI
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings

try:
    from ai.llm_client import get_llm_client
except ImportError:
    from llm_client import get_llm_client

settings = get_settings()


class RAGEngine:
    """
    RAG 检索增强生成引擎

    大白话说明：
        这个类把"检索"和"生成"两个步骤串起来：
        - 检索：从 ChromaDB 里找相关文档
        - 生成：让 LLM 参考文档回答问题
    """

    def __init__(self):
        """初始化 RAG 引擎"""
        # ChromaDB 客户端
        chroma_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            settings.CHROMA_DB_PATH
        )
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=chromadb.config.Settings(anonymized_telemetry=False)
        )

        # OpenAI 嵌入客户端（用来把问题变成向量）
        self.embed_client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.embed_model = settings.EMBEDDING_MODEL_NAME

        # LLM 客户端（用来生成回答）
        self.llm_client = get_llm_client()

        # 尝试获取集合（如果还没构建向量库的话，先用None占位）
        try:
            self.spot_collection = self.chroma_client.get_collection("spot_knowledge")
        except Exception:
            self.spot_collection = None
            print("⚠️ spot_knowledge 集合不存在，RAG景点搜索不可用")

        try:
            self.faq_collection = self.chroma_client.get_collection("system_knowledge")
        except Exception:
            self.faq_collection = None
            print("⚠️ system_knowledge 集合不存在，FAQ搜索不可用")

    def _embed_query(self, text: str) -> list[float]:
        """
        把查询文本变成向量

        大白话：调用嵌入API，把一段文字变成一串数字（向量）
        """
        response = self.embed_client.embeddings.create(
            model=self.embed_model,
            input=text,
        )
        return response.data[0].embedding

    def search_spots(self, query: str, n_results: int = 5,
                     city_filter: str = None) -> list[dict]:
        """
        搜索相关景点文档

        大白话说明：
            根据用户问题，在景点知识库里找最相关的文档。
            可以按城市过滤。如果指定了城市但找不到结果，会自动取消过滤重试。

        参数：
            query: 搜索文本
            n_results: 返回数量
            city_filter: 城市过滤（可选）
        返回：
            [{document, metadata, distance}, ...]
        """
        if not self.spot_collection:
            return []

        # 把查询文本变成向量
        query_embedding = self._embed_query(query)

        # 如果有城市过滤，先尝试带城市过滤搜索
        if city_filter:
            where = {"city": city_filter}
            results = self.spot_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
            )
            # 如果城市过滤有结果，直接返回
            if results and results["documents"] and results["documents"][0]:
                print(f"  🏯 城市过滤 '{city_filter}' 命中 {len(results['documents'][0])} 条结果")
                return self._parse_results(results)
            else:
                print(f"  ⚠️ 城市过滤 '{city_filter}' 无结果，取消过滤重试...")

        # 不带城市过滤的搜索（全库检索）
        results = self.spot_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        return self._parse_results(results)

    def _parse_results(self, results) -> list[dict]:
        """解析 ChromaDB 查询结果为统一格式"""
        docs = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                docs.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                })
        return docs

    def search_faq(self, query: str, n_results: int = 3) -> list[dict]:
        """
        搜索系统FAQ

        大白话：在系统使用帮助知识库里找相关的FAQ
        """
        if not self.faq_collection:
            return []

        query_embedding = self._embed_query(query)

        results = self.faq_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        docs = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                docs.append({
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                })

        return docs

    async def answer_question(self, question: str, history: list[dict] = None,
                               city_filter: str = None) -> dict:
        """
        智能问答 - RAG核心方法

        大白话说明：
            用户问一个关于旅游/景点的问题，通过以下步骤生成回答：
            1. 先在景点知识库和FAQ知识库里搜索相关内容
            2. 把搜索到的内容作为"参考资料"
            3. 让AI参考这些资料回答问题

        参数：
            question: 用户问题
            history: 对话历史
            city_filter: 城市过滤（可选，用于提高检索精准度）
        返回：
            {
                "answer": AI的回答,
                "sources": 参考的文档来源,
                "type": "spot_qa" / "faq" / "general"
            }
        """
        # 第一步：同时搜索景点知识库和FAQ库
        spot_docs = self.search_spots(question, n_results=5, city_filter=city_filter)
        faq_docs = self.search_faq(question, n_results=2)

        # 第二步：判断应该参考哪些文档
        context_docs = []
        sources = []
        answer_type = "general"

        # 优先看FAQ（如果是系统使用问题）
        if faq_docs:
            for doc in faq_docs:
                context_docs.append(doc["document"])
                sources.append({
                    "type": "faq",
                    "question": doc["metadata"].get("question", ""),
                })
            answer_type = "faq"

        # 加入景点相关文档
        if spot_docs:
            for doc in spot_docs:
                context_docs.append(doc["document"])
                sources.append({
                    "type": "spot",
                    "name": doc["metadata"].get("name", ""),
                    "city": doc["metadata"].get("city", ""),
                })
            answer_type = "spot_qa"

        # 第三步：生成回答
        if context_docs:
            answer = await self.llm_client.chat_with_context(question, context_docs)
        else:
            # 没有相关文档，直接对话
            answer = await self.llm_client.chat(
                question,
                system_prompt="你是一个经验丰富的旅游向导，像熟悉当地的老朋友一样自然地回答问题。"
            )

        return {
            "answer": answer,
            "sources": sources[:5],  # 最多返回5个来源
            "type": answer_type,
        }


# 全局单例
_rag_engine = None

def get_rag_engine() -> RAGEngine:
    """获取 RAG 引擎单例"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
