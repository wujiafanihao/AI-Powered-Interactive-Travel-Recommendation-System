"""
向量数据库构建脚本 - 把景点数据和系统FAQ嵌入到 ChromaDB

大白话说明：
    这个脚本做的事情：
    1. 从 SQLite 读取所有景点数据
    2. 把每个景点的"介绍+小贴士+建议季节"拼成一段文本
    3. 用 Qwen3-Embedding-8B 模型把文本变成向量（一串数字）
    4. 把向量存到 ChromaDB（向量数据库）里
    5. 同时把系统使用FAQ也向量化存进去

    这样后面用户问问题的时候，就可以：
    用户问题 → 变成向量 → 在 ChromaDB 里找最相似的景点文档 → 给 AI 做参考

    为什么要分批处理？
    因为一次性发 33000 个文本给 API 会超时，所以分成小批次（每批32条）发送。

运行方式：
    cd backend
    python scripts/build_vectors.py
"""

import os
import sys
import time
import sqlite3
import chromadb
from openai import OpenAI
from tqdm import tqdm

# 把 backend 目录加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings
from database import DB_PATH

settings = get_settings()

# ChromaDB 存储路径
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.CHROMA_DB_PATH)

# 每批处理的文档数量（太大会超时或超过 API 限制）
BATCH_SIZE = 64

# 最大文本长度（超过的截断，避免 token 超限）
MAX_TEXT_LENGTH = 800


# ============================================
# 系统使用 FAQ 知识库
# 大白话：用户问"怎么用这个系统"时，AI可以参考这些回答
# ============================================
SYSTEM_FAQ = [
    {
        "question": "怎么注册账号？",
        "answer": "点击首页右上角的「注册」按钮，填写用户名、密码和基本信息即可完成注册。注册时可以选择您的旅行偏好，系统会据此为您推荐合适的景点。"
    },
    {
        "question": "怎么登录系统？",
        "answer": "点击首页右上角的「登录」按钮，输入您的用户名和密码即可登录。登录后系统会记住您的偏好和历史，提供个性化推荐。"
    },
    {
        "question": "怎么收藏景点？",
        "answer": "在景点详情页，点击右上角的❤️爱心按钮即可收藏。收藏的景点可以在「个人中心」→「我的收藏」中查看。"
    },
    {
        "question": "怎么给景点评分？",
        "answer": "在景点详情页下方，有一个星级评分组件，点击星星即可打分（1-5分）。评分会帮助系统更好地了解您的偏好。"
    },
    {
        "question": "推荐是怎么生成的？",
        "answer": "系统使用混合推荐算法，综合考虑：1) 与您品味相似的用户喜欢的景点（协同过滤）；2) 与您历史浏览景点特征相似的景点（内容推荐）。两种方法动态加权融合。"
    },
    {
        "question": "什么是场景化推荐？",
        "answer": "首页提供「亲子游」「老年游」「历史文化游」「自然风光游」等场景入口，点击即可查看该场景下的精选景点推荐，方便您快速找到合适的旅游目的地。"
    },
    {
        "question": "AI助手能做什么？",
        "answer": "AI助手可以：1) 智能搜索 - 用自然语言描述您的需求，如「带孩子去北京玩」；2) 景点问答 - 回答关于景点的具体问题，如开放时间、门票等；3) 旅行建议 - 提供个性化的旅行规划建议。"
    },
    {
        "question": "怎么使用智能搜索？",
        "answer": "在AI对话界面输入您的需求，比如「推荐几个适合老年人的杭州景点」或「秋天去哪里赏红叶」，系统会理解您的意图并返回匹配的景点列表。"
    },
    {
        "question": "系统支持哪些城市？",
        "answer": "系统目前收录了全国352个城市的景点数据，涵盖所有省会城市和热门旅游城市，共计超过33000个景点。"
    },
    {
        "question": "怎么修改个人信息？",
        "answer": "登录后进入「个人中心」，点击「编辑资料」按钮，可以修改昵称、年龄、旅行偏好等信息。修改偏好后，推荐结果会自动更新。"
    },
    {
        "question": "景点信息准确吗？",
        "answer": "景点信息来源于公开的旅游平台数据，包括开放时间、门票价格等。但这些信息可能会变动，建议出行前通过景点官方渠道确认最新信息。"
    },
    {
        "question": "为什么我的推荐不太准？",
        "answer": "推荐准确度与您的使用频率有关。新用户因为历史数据少，推荐会偏向热门景点。随着您浏览、收藏、评分更多景点，推荐会越来越精准。"
    },
    {
        "question": "系统字体太小怎么办？",
        "answer": "系统支持适老化设计。在「个人中心」→「设置」中可以开启「大字体模式」，字体和按钮都会变大，方便阅读和操作。"
    },
    {
        "question": "怎么查看浏览历史？",
        "answer": "登录后进入「个人中心」→「浏览历史」，可以查看您最近浏览过的景点列表，方便回顾和再次访问。"
    },
    {
        "question": "数据安全吗？",
        "answer": "系统采用JWT加密认证，密码经过bcrypt哈希存储，不会保存明文密码。您的个人信息仅用于提供推荐服务，不会泄露给第三方。"
    },
]


class ModelScopeEmbedding:
    """
    ModelScope 嵌入模型客户端

    大白话说明：
        这个类封装了调用 ModelScope API 计算文本向量的功能。
        用 OpenAI 兼容格式的接口，所以直接用 openai 库就行。
    """

    def __init__(self):
        """初始化 API 客户端"""
        self.client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
        self.model = settings.EMBEDDING_MODEL_NAME

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量计算文本的嵌入向量

        大白话说明：
            把一批文本发给 API，API 返回每个文本对应的向量。
            如果 API 调用失败，会自动重试 3 次。

        参数：
            texts: 文本列表
        返回：
            向量列表，每个向量是一个浮点数数组
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                # 按索引排序（API可能不保证返回顺序）
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_data]

            except Exception as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 3  # 递增等待 3s, 6s, 9s
                    print(f"  ⚠️ API 调用失败 (第{attempt+1}次)，{wait}秒后重试: {e}")
                    time.sleep(wait)
                else:
                    print(f"  ❌ API 调用失败（已重试{max_retries}次）: {e}")
                    raise


def build_spot_documents(cursor: sqlite3.Cursor) -> tuple[list[str], list[str], list[dict]]:
    """
    从数据库构建景点文档

    大白话说明：
        把每个景点的关键信息拼成一段文本，用于后续向量化。
        拼接格式：
            [景点名] - [城市]
            介绍：xxx
            建议季节：xxx
            小贴士：xxx

    返回：
        (文档ID列表, 文档文本列表, 元数据列表)
    """
    cursor.execute("""
        SELECT id, name, city, description, suggest_season, tips, 
               rating, spot_type, open_time, suggest_time
        FROM spots 
        WHERE description IS NOT NULL AND description != ''
    """)
    rows = cursor.fetchall()

    doc_ids = []
    doc_texts = []
    doc_metadatas = []

    for row in rows:
        spot_id, name, city, desc, season, tips, rating, spot_type, open_time, suggest_time = row

        # 拼接文档文本
        text_parts = [f"{name} - {city}"]
        if desc:
            text_parts.append(f"介绍：{desc}")
        if season:
            text_parts.append(f"建议季节：{season}")
        if tips:
            text_parts.append(f"小贴士：{tips}")
        if open_time:
            text_parts.append(f"开放时间：{open_time}")
        if suggest_time:
            text_parts.append(f"游玩时间：{suggest_time}")

        full_text = "\n".join(text_parts)

        # 截断过长的文本
        if len(full_text) > MAX_TEXT_LENGTH:
            full_text = full_text[:MAX_TEXT_LENGTH] + "..."

        doc_ids.append(f"spot_{spot_id}")
        doc_texts.append(full_text)
        doc_metadatas.append({
            "spot_id": spot_id,
            "name": name,
            "city": city,
            "rating": rating or 0.0,
            "spot_type": spot_type or "[]",
            "source": "citydata",
        })

    return doc_ids, doc_texts, doc_metadatas


def build_faq_documents() -> tuple[list[str], list[str], list[dict]]:
    """
    构建系统FAQ文档

    大白话说明：
        把上面定义的 FAQ 列表转成向量数据库需要的格式。
    """
    doc_ids = []
    doc_texts = []
    doc_metadatas = []

    for i, faq in enumerate(SYSTEM_FAQ):
        doc_ids.append(f"faq_{i}")
        doc_texts.append(f"问题：{faq['question']}\n回答：{faq['answer']}")
        doc_metadatas.append({
            "category": "system_faq",
            "question": faq["question"],
        })

    return doc_ids, doc_texts, doc_metadatas


def build_collection(
    chroma_client: chromadb.ClientAPI,
    collection_name: str,
    doc_ids: list[str],
    doc_texts: list[str],
    doc_metadatas: list[dict],
    embedder: ModelScopeEmbedding,
):
    """
    构建一个 ChromaDB 集合

    大白话说明：
        1. 创建（或重置）一个集合
        2. 把文档分批发送给嵌入API计算向量
        3. 把向量和文档一起存入 ChromaDB
    """
    # 如果集合已存在，先删除再重建
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
    )

    print(f"\n📦 构建集合: {collection_name} ({len(doc_texts)} 条文档)")

    # 分批处理
    total_batches = (len(doc_texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in tqdm(range(total_batches), desc=f"  嵌入 {collection_name}"):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(doc_texts))

        batch_ids = doc_ids[start:end]
        batch_texts = doc_texts[start:end]
        batch_metadatas = doc_metadatas[start:end]

        # 调用 API 计算嵌入向量
        batch_embeddings = embedder.embed_texts(batch_texts)

        # 存入 ChromaDB
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas,
        )

        # 限速：避免 API 限流（每批之间等一小会儿）
        if batch_idx < total_batches - 1 and batch_idx % 5 == 0:
            time.sleep(0.1)

    print(f"  ✅ 集合 {collection_name} 构建完成: {collection.count()} 条向量")
    return collection


def main():
    """
    主函数 - 执行完整的向量数据库构建流程
    """
    print("=" * 60)
    print("🧬 TravelAI 向量数据库构建工具")
    print("=" * 60)

    # 第一步：初始化嵌入模型客户端
    print("\n📡 初始化 ModelScope 嵌入API...")
    embedder = ModelScopeEmbedding()
    # 测试一下 API 是否正常
    test_result = embedder.embed_texts(["测试文本"])
    print(f"  ✅ API 正常，嵌入维度: {len(test_result[0])}")

    # 第二步：初始化 ChromaDB
    print(f"\n💾 初始化 ChromaDB: {CHROMA_PATH}")
    os.makedirs(CHROMA_PATH, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # 第三步：从数据库读取景点数据
    print("\n📊 从 SQLite 读取景点数据...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    spot_ids, spot_texts, spot_metadatas = build_spot_documents(cursor)
    conn.close()
    print(f"  共 {len(spot_texts)} 条有效景点文档")

    # 第四步：构建景点知识库集合
    build_collection(
        chroma_client, "spot_knowledge",
        spot_ids, spot_texts, spot_metadatas,
        embedder
    )

    # 第五步：构建FAQ文档
    faq_ids, faq_texts, faq_metadatas = build_faq_documents()
    print(f"\n📋 FAQ 文档: {len(faq_texts)} 条")

    # 第六步：构建系统FAQ知识库集合
    build_collection(
        chroma_client, "system_knowledge",
        faq_ids, faq_texts, faq_metadatas,
        embedder
    )

    # 验证结果
    print("\n" + "=" * 60)
    print("📊 向量数据库统计:")
    for col_name in ["spot_knowledge", "system_knowledge"]:
        col = chroma_client.get_collection(col_name)
        print(f"  {col_name}: {col.count()} 条向量")

    # 做个简单的检索测试
    print("\n🔍 检索测试:")
    spot_col = chroma_client.get_collection("spot_knowledge")
    test_query_vec = embedder.embed_texts(["北京适合带孩子玩的地方"])[0]
    results = spot_col.query(
        query_embeddings=[test_query_vec],
        n_results=3,
    )
    print("  查询: '北京适合带孩子玩的地方'")
    for i, (doc_id, doc, metadata) in enumerate(
        zip(results["ids"][0], results["documents"][0], results["metadatas"][0])
    ):
        name = metadata.get("name", "未知")
        city = metadata.get("city", "未知")
        print(f"  Top-{i+1}: {name} ({city})")

    print("\n" + "=" * 60)
    print("🎉 向量数据库构建完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
