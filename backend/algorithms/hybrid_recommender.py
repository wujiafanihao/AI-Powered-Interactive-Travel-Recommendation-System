"""
混合推荐融合引擎

大白话说明：
    这是推荐系统的"总指挥"，它把协同过滤和内容推荐两种方法的结果
    混合在一起，生成最终的推荐列表。

    核心策略：动态加权融合
    - 新用户（行为<5条）：完全用内容推荐（因为没有足够数据做协同过滤）
    - 普通用户（5-20条）：两种方法混合，内容推荐权重高
    - 活跃用户（>20条）：协同过滤为主(60%)，内容推荐为辅(40%)

    最终输出的每条推荐都附带"推荐理由"，让用户知道我们为什么推荐这个景点。

    公式：
    score_hybrid(u, i) = w_CF × score_CF(u, i) + w_CB × score_CB(u, i)

    其中 w_CF + w_CB = 1.0，权重根据用户行为数据量动态调整
"""

import sqlite3
import json
from typing import Optional

try:
    # 作为包的一部分导入（FastAPI 运行时）
    from algorithms.collaborative_filter import CollaborativeFilter
    from algorithms.content_based import ContentBasedRecommender
except ImportError:
    # 直接运行脚本时
    from collaborative_filter import CollaborativeFilter
    from content_based import ContentBasedRecommender


class HybridRecommender:
    """
    混合推荐引擎 - 融合协同过滤和内容推荐

    大白话说明：
        这个类是对外的统一接口。
        不管用户是新用户还是老用户，调 recommend() 就能拿到推荐结果。
        内部会自动判断用哪种算法、怎么混合。
    """

    def __init__(self, db_path: str):
        """
        初始化混合推荐引擎

        大白话说明：
            创建协同过滤和内容推荐两个子引擎，作为"左右手"。
        """
        self.db_path = db_path

        # 左手：协同过滤引擎
        self.cf_engine = CollaborativeFilter(db_path)
        # 右手：内容推荐引擎
        self.cb_engine = ContentBasedRecommender(db_path)

        # 标记是否已经初始化过
        self._initialized = False

    def initialize(self):
        """
        初始化推荐引擎（加载数据和模型）

        大白话说明：
            从数据库加载协同过滤的相似度矩阵和内容推荐的特征向量。
            如果数据库里还没有这些数据，就现场计算。
        """
        if self._initialized:
            return

        print("🔄 初始化混合推荐引擎...")

        # 加载协同过滤数据
        self.cf_engine.load_ratings()
        try:
            self.cf_engine.load_similarity_from_db()
            if not self.cf_engine.similarity_matrix:
                raise ValueError("相似度矩阵为空")
        except Exception:
            print("  ⚠️ 相似度矩阵不存在，正在计算...")
            self.cf_engine.compute_similarity()

        # 加载内容推荐数据
        try:
            self.cb_engine.load_features_from_db()
            if not self.cb_engine.spot_features:
                raise ValueError("特征向量为空")
        except Exception:
            print("  ⚠️ 特征向量不存在，正在计算...")
            self.cb_engine.load_and_compute_features()

        self._initialized = True
        print("✅ 混合推荐引擎初始化完成")

    def _calculate_weights(self, user_id: int) -> tuple[float, float]:
        """
        根据用户数据丰富度动态计算权重

        大白话说明：
            用户行为数据越多，协同过滤就越准，权重就越高。
            反之，用户行为少的时候，主要靠内容推荐。

            具体规则：
            - 行为 < 5条：w_CF=0.0, w_CB=1.0（纯内容推荐）
            - 行为 5-20条：w_CF 从0逐渐增长到0.4，w_CB 从1逐渐下降到0.6
            - 行为 > 20条：w_CF=0.6, w_CB=0.4（协同过滤为主）

        返回：
            (协同过滤权重, 内容推荐权重)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 统计用户行为数量
        cursor.execute(
            "SELECT COUNT(*) FROM user_behaviors WHERE user_id = ?",
            (user_id,)
        )
        behavior_count = cursor.fetchone()[0]
        conn.close()

        if behavior_count < 5:
            # 冷启动阶段：完全依赖内容推荐
            w_cf, w_cb = 0.0, 1.0
        elif behavior_count < 20:
            # 数据积累阶段：渐进式混合
            # 行为数从5增长到20时，CF权重从0线性增长到0.4
            ratio = (behavior_count - 5) / 15.0  # 0.0 ~ 1.0
            w_cf = 0.4 * ratio
            w_cb = 1.0 - w_cf
        else:
            # 数据充足阶段：协同过滤为主
            w_cf, w_cb = 0.6, 0.4

        return w_cf, w_cb

    def _get_hot_recommendations(self, n: int = 10, exclude_ids: set = None) -> list[dict]:
        """
        获取热门推荐（兜底策略）

        大白话说明：
            当协同过滤和内容推荐都无法工作时（比如纯新用户），
            就推荐评分最高、最热门的景点。
            这是最后的"兜底"，保证用户总能看到推荐。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if exclude_ids:
            placeholders = ",".join(["?"] * len(exclude_ids))
            cursor.execute(f"""
                SELECT id, name, city, rating, spot_type
                FROM spots 
                WHERE rating IS NOT NULL AND id NOT IN ({placeholders})
                ORDER BY rating DESC 
                LIMIT ?
            """, list(exclude_ids) + [n])
        else:
            cursor.execute("""
                SELECT id, name, city, rating, spot_type
                FROM spots 
                WHERE rating IS NOT NULL
                ORDER BY rating DESC 
                LIMIT ?
            """, (n,))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "spot_id": row[0],
                "score": float(row[3]) / 5.0 if row[3] else 0.5,
                "reason": f"热门推荐 - 评分高达{row[3]}分，深受游客好评",
                "source": "hot",
            })

        return results

    def _get_scene_recommendations(self, scene: str, n: int = 10) -> list[dict]:
        """
        场景化推荐

        大白话说明：
            根据用户选择的场景（亲子游、老年游等），推荐匹配的景点。
            场景信息对应景点的 target_group 和 spot_type 字段。
        """
        # 场景到查询条件的映射
        scene_mapping = {
            "亲子游": {"target_group": "亲子", "spot_type": "主题乐园"},
            "老年游": {"target_group": "老年", "spot_type": "园林公园"},
            "历史文化游": {"spot_type": "历史文化"},
            "自然风光游": {"spot_type": "自然风光"},
            "摄影打卡": {"target_group": "摄影"},
            "探险运动": {"target_group": "探险", "spot_type": "自然风光"},
        }

        conditions = scene_mapping.get(scene, {})
        if not conditions:
            return self._get_hot_recommendations(n)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建查询条件
        where_parts = []
        params = []
        for field, value in conditions.items():
            where_parts.append(f"{field} LIKE ?")
            params.append(f"%{value}%")

        where_clause = " OR ".join(where_parts)
        params.append(n)

        cursor.execute(f"""
            SELECT id, name, city, rating, spot_type, target_group
            FROM spots 
            WHERE ({where_clause}) AND rating IS NOT NULL
            ORDER BY rating DESC 
            LIMIT ?
        """, params)

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "spot_id": row[0],
                "score": float(row[3]) / 5.0 if row[3] else 0.5,
                "reason": f"「{scene}」精选推荐",
                "source": "scene",
            })

        return results

    def recommend(
        self,
        user_id: int,
        n: int = 10,
        scene: Optional[str] = None,
    ) -> list[dict]:
        """
        生成混合推荐结果（对外主接口）

        大白话说明：
            这是推荐系统的核心入口函数。根据用户情况自动选择策略：
            1. 如果指定了场景（亲子游/老年游等），走场景推荐
            2. 如果是新用户（没有行为数据），走热门推荐
            3. 否则走混合推荐（协同过滤 + 内容推荐动态融合）

        参数：
            user_id: 用户ID
            n: 推荐数量
            scene: 场景标签（可选）

        返回：
            [
                {
                    "spot_id": 景点ID,
                    "score": 综合评分(0-1),
                    "reason": "推荐理由文本",
                    "source": "hybrid/cf/cb/hot/scene"
                },
                ...
            ]
        """
        self.initialize()

        # 场景化推荐
        if scene:
            return self._get_scene_recommendations(scene, n)

        # 计算动态权重
        w_cf, w_cb = self._calculate_weights(user_id)

        # --------- 获取两个引擎的推荐结果 ---------

        # 协同过滤推荐
        cf_results = {}
        if w_cf > 0:
            cf_recs = self.cf_engine.recommend(user_id, n=n * 3)
            for rec in cf_recs:
                # 把预测评分归一化到 0-1
                normalized_score = rec["predicted_rating"] / 5.0
                cf_results[rec["spot_id"]] = {
                    "score": normalized_score,
                    "reason": rec["reason"],
                }

        # 内容推荐
        cb_results = {}
        if w_cb > 0:
            cb_recs = self.cb_engine.recommend(user_id, n=n * 3)
            for rec in cb_recs:
                cb_results[rec["spot_id"]] = {
                    "score": rec["similarity"],
                    "reason": rec["reason"],
                }

        # --------- 融合两个结果 ---------
        # 取两个结果的并集
        all_spot_ids = set(cf_results.keys()) | set(cb_results.keys())

        if not all_spot_ids:
            # 两个引擎都没结果（冷启动），用热门推荐兜底
            return self._get_hot_recommendations(n)

        # 计算每个景点的融合分数
        merged_results = []
        for spot_id in all_spot_ids:
            cf_item = cf_results.get(spot_id)
            cb_item = cb_results.get(spot_id)

            # 融合分数
            cf_score = cf_item["score"] if cf_item else 0.0
            cb_score = cb_item["score"] if cb_item else 0.0
            hybrid_score = w_cf * cf_score + w_cb * cb_score

            # 融合推荐理由
            reasons = []
            source = "hybrid"

            if cf_item and w_cf > 0:
                reasons.append(cf_item["reason"])
                if not cb_item:
                    source = "cf"
            if cb_item and w_cb > 0:
                reasons.append(cb_item["reason"])
                if not cf_item:
                    source = "cb"

            # 合并去重理由
            reason_text = "；".join(dict.fromkeys(reasons))  # 去重保序

            merged_results.append({
                "spot_id": spot_id,
                "score": round(hybrid_score, 4),
                "reason": reason_text,
                "source": source,
                "cf_score": round(cf_score, 4),
                "cb_score": round(cb_score, 4),
                "w_cf": w_cf,
                "w_cb": w_cb,
            })

        # 按融合分数排序
        merged_results.sort(key=lambda x: x["score"], reverse=True)

        # 如果结果不够，用热门推荐补充
        if len(merged_results) < n:
            existing_ids = {r["spot_id"] for r in merged_results}
            hot_recs = self._get_hot_recommendations(
                n - len(merged_results),
                exclude_ids=existing_ids
            )
            merged_results.extend(hot_recs)

        return merged_results[:n]

    def get_recommendation_with_details(self, user_id: int, n: int = 10) -> dict:
        """
        获取推荐结果及详细信息（含景点名称等）

        大白话说明：
            在 recommend() 的基础上，把推荐结果里的 spot_id 替换成
            完整的景点信息（名称、城市、评分、图片等），方便前端直接展示。
        """
        recommendations = self.recommend(user_id, n)

        if not recommendations:
            return {"items": [], "strategy": "empty"}

        # 获取景点详细信息
        spot_ids = [r["spot_id"] for r in recommendations]
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ",".join(["?"] * len(spot_ids))
        cursor.execute(f"""
            SELECT id, name, city, rating, image_url, spot_type, suggest_time
            FROM spots 
            WHERE id IN ({placeholders})
        """, spot_ids)

        spot_info = {}
        for row in cursor.fetchall():
            spot_info[row[0]] = {
                "name": row[1],
                "city": row[2],
                "rating": row[3],
                "image_url": row[4],
                "spot_type": row[5],
                "suggest_time": row[6],
            }
        conn.close()

        # 组装完整结果
        items = []
        for rec in recommendations:
            info = spot_info.get(rec["spot_id"], {})
            items.append({
                "spot_id": rec["spot_id"],
                "name": info.get("name", "未知景点"),
                "city": info.get("city", ""),
                "rating": info.get("rating"),
                "image_url": info.get("image_url", ""),
                "spot_type": info.get("spot_type", "[]"),
                "suggest_time": info.get("suggest_time", ""),
                "score": rec["score"],
                "reason": rec["reason"],
                "source": rec["source"],
            })

        # 计算权重信息
        w_cf, w_cb = self._calculate_weights(user_id)

        return {
            "items": items,
            "strategy": {
                "w_cf": w_cf,
                "w_cb": w_cb,
                "description": self._describe_strategy(w_cf, w_cb),
            },
        }

    def _describe_strategy(self, w_cf: float, w_cb: float) -> str:
        """
        用文字描述当前使用的推荐策略

        大白话说明：
            告诉前端/用户现在用的是什么推荐策略，方便理解和调试。
        """
        if w_cf == 0:
            return "冷启动模式：基于您的偏好设置进行推荐，随着使用越多推荐越精准"
        elif w_cf < 0.4:
            return "成长模式：正在学习您的品味，推荐会越来越准"
        else:
            return "成熟模式：综合分析您的历史偏好和相似用户的喜好进行推荐"


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database import DB_PATH

    print("=" * 60)
    print("🔀 混合推荐引擎测试")
    print("=" * 60)

    engine = HybridRecommender(DB_PATH)

    # 测试不同用户的推荐
    test_users = [1, 50, 140]  # 活跃/普通/新用户
    for uid in test_users:
        print(f"\n--- 用户 {uid} 的推荐 ---")
        result = engine.get_recommendation_with_details(uid, n=5)
        print(f"策略: {result['strategy']}")
        for i, item in enumerate(result["items"]):
            print(f"  Top-{i+1}: {item['name']}({item['city']}) "
                  f"评分:{item['rating']} | 得分:{item['score']} | "
                  f"来源:{item['source']}")
            print(f"         理由: {item['reason']}")

    # 测试场景推荐
    print(f"\n--- 场景推荐：亲子游 ---")
    result = engine.get_recommendation_with_details(1, n=5)
    for i, item in enumerate(result["items"]):
        print(f"  {i+1}. {item['name']}({item['city']})")
