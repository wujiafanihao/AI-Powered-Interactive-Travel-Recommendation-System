"""
基于用户的协同过滤推荐引擎

大白话说明：
    协同过滤的核心思想就一句话：
    "和你品味相似的人喜欢的东西，你大概率也喜欢"

    具体步骤：
    1. 计算任意两个用户之间的"相似度"（用余弦相似度公式）
    2. 找出和目标用户最像的 K 个人（K=20）
    3. 看这些"近邻用户"喜欢哪些景点（但目标用户还没看过的）
    4. 用加权平均预测目标用户对这些景点的评分
    5. 按预测评分从高到低排序，输出推荐列表

    核心公式（余弦相似度）：
                    Σ(r_ui × r_vi)
    sim(u,v) = ──────────────────────────
               √(Σr_ui²) × √(Σr_vi²)

    其中 r_ui 表示用户u对景点i的评分

    复杂度分析：
    - 相似度矩阵计算: O(|U|² × |I|)  （U=用户数, I=景点数）
    - 推荐生成: O(K × |I|)
    - 空间复杂度: O(|U|²) 存储相似度矩阵

    因为用户数不多（150人），这个复杂度完全可以接受
"""

import sqlite3
import json
import math
from collections import defaultdict
from typing import Optional


class CollaborativeFilter:
    """
    基于用户的协同过滤推荐引擎

    大白话说明：
        这个类实现了完整的用户协同过滤推荐流程。
        使用时先调 compute_similarity() 计算用户相似度（可以离线跑），
        然后调 recommend() 就能给任意用户生成推荐列表了。
    """

    def __init__(self, db_path: str, k: int = 20, min_common: int = 3):
        """
        初始化协同过滤引擎

        参数：
            db_path: SQLite 数据库文件路径
            k: 近邻数量，默认20（选最相似的20个用户）
            min_common: 最少共同评分数，默认3（低于3个共同评分不算相似度）
        """
        self.db_path = db_path
        self.k = k
        self.min_common = min_common

        # 用户评分矩阵：{user_id: {spot_id: rating}}
        self.user_ratings = defaultdict(dict)
        # 用户平均评分：{user_id: avg_rating}
        self.user_avg_ratings = {}
        # 相似度矩阵：{user_id_a: {user_id_b: similarity}}
        self.similarity_matrix = defaultdict(dict)

    def load_ratings(self):
        """
        从数据库加载用户评分数据

        大白话说明：
            把用户的评分行为从数据库读出来，构建"用户-景点评分矩阵"。
            矩阵长这样：
                       景点1  景点2  景点3  ...
            用户1      4.5   3.0    -     ...
            用户2       -    5.0   4.0    ...
            用户3      3.5   4.0   4.5    ...
            （"-" 表示没评过分）

            额外处理：对于只浏览但没评分的行为，用默认分数3.5代替
            （因为愿意点进去看，说明至少有点兴趣）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 先读显式评分（用户主动打的分）
        cursor.execute("""
            SELECT user_id, spot_id, rating 
            FROM user_behaviors 
            WHERE behavior_type = 'rate' AND rating IS NOT NULL
        """)
        for user_id, spot_id, rating in cursor.fetchall():
            self.user_ratings[user_id][spot_id] = rating

        # 再读收藏行为（收藏 = 隐式好评，默认4.0分）
        cursor.execute("""
            SELECT user_id, spot_id FROM user_collections
        """)
        for user_id, spot_id in cursor.fetchall():
            if spot_id not in self.user_ratings[user_id]:
                self.user_ratings[user_id][spot_id] = 4.0

        # 再看浏览行为时间较长的（浏览超过120秒 = 有一定兴趣，默认3.5分）
        cursor.execute("""
            SELECT user_id, spot_id 
            FROM user_behaviors 
            WHERE behavior_type = 'browse' AND duration > 120
        """)
        for user_id, spot_id in cursor.fetchall():
            if spot_id not in self.user_ratings[user_id]:
                self.user_ratings[user_id][spot_id] = 3.5

        conn.close()

        # 计算每个用户的平均评分
        for user_id, ratings in self.user_ratings.items():
            if ratings:
                self.user_avg_ratings[user_id] = sum(ratings.values()) / len(ratings)
            else:
                self.user_avg_ratings[user_id] = 0.0

        print(f"  ✅ 加载了 {len(self.user_ratings)} 个用户的评分数据")
        total_ratings = sum(len(r) for r in self.user_ratings.values())
        print(f"  ✅ 共 {total_ratings} 条评分记录")

    def cosine_similarity(self, user_a: int, user_b: int) -> float:
        """
        计算两个用户之间的余弦相似度

        大白话说明：
            余弦相似度衡量的是"两个用户评分方向是否一致"。
            值域是 [-1, 1]：
            - 1 表示品味完全一致
            - 0 表示没什么关系
            - -1 表示品味完全相反

            计算公式：
                        Σ(r_ai × r_bi)
            sim = ─────────────────────────
                  √(Σr_ai²) × √(Σr_bi²)

            其中求和只在两个用户"共同评过分的景点"上进行
        """
        # 找出两个用户都评过分的景点（交集）
        ratings_a = self.user_ratings.get(user_a, {})
        ratings_b = self.user_ratings.get(user_b, {})
        common_spots = set(ratings_a.keys()) & set(ratings_b.keys())

        # 如果共同评分的景点太少，认为相似度无法计算，返回0
        if len(common_spots) < self.min_common:
            return 0.0

        # 计算余弦相似度的三个部分
        dot_product = 0.0   # 分子：点积 Σ(r_ai × r_bi)
        norm_a = 0.0        # 分母左边：Σ(r_ai²)
        norm_b = 0.0        # 分母右边：Σ(r_bi²)

        for spot_id in common_spots:
            ra = ratings_a[spot_id]
            rb = ratings_b[spot_id]
            dot_product += ra * rb
            norm_a += ra * ra
            norm_b += rb * rb

        # 防止除以零
        denominator = math.sqrt(norm_a) * math.sqrt(norm_b)
        if denominator == 0:
            return 0.0

        return dot_product / denominator

    def compute_similarity(self):
        """
        计算所有用户对之间的相似度矩阵

        大白话说明：
            遍历所有用户对(u, v)，计算他们之间的余弦相似度。
            结果保存到内存中的 similarity_matrix 里。

            这是一个 O(|U|²×|I|) 的操作，但因为用户只有150人，
            所以只需要做 150×149/2 = 11,175 次计算，秒级就能完成。

            计算完后同时存入数据库，供后续使用。
        """
        user_ids = list(self.user_ratings.keys())
        total_pairs = len(user_ids) * (len(user_ids) - 1) // 2

        print(f"  计算 {len(user_ids)} 个用户的相似度矩阵 ({total_pairs} 对)...")

        computed = 0
        for i in range(len(user_ids)):
            for j in range(i + 1, len(user_ids)):
                user_a = user_ids[i]
                user_b = user_ids[j]

                sim = self.cosine_similarity(user_a, user_b)

                # 只存储非零相似度（节省空间）
                if sim != 0.0:
                    self.similarity_matrix[user_a][user_b] = sim
                    self.similarity_matrix[user_b][user_a] = sim
                    computed += 1

        print(f"  ✅ 共计算 {total_pairs} 对，{computed} 对有效相似度")

        # 存入数据库
        self._save_similarity_to_db()

    def _save_similarity_to_db(self):
        """
        把相似度矩阵存入SQLite

        大白话说明：
            相似度计算比较耗时（虽然当前数据量不大），
            所以把结果存到数据库里，下次直接读就行，不用重新算。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM user_similarity")

        records = []
        for user_a, neighbors in self.similarity_matrix.items():
            for user_b, sim in neighbors.items():
                if user_a < user_b:  # 避免重复存储(a,b)和(b,a)
                    records.append((user_a, user_b, sim))

        cursor.executemany("""
            INSERT INTO user_similarity (user_id_a, user_id_b, similarity)
            VALUES (?, ?, ?)
        """, records)

        conn.commit()
        conn.close()
        print(f"  ✅ 已保存 {len(records)} 条相似度记录到数据库")

    def load_similarity_from_db(self):
        """
        从数据库加载已计算好的相似度矩阵

        大白话说明：
            如果之前已经算过相似度了（存在数据库里），直接读出来用就行。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT user_id_a, user_id_b, similarity FROM user_similarity")
        rows = cursor.fetchall()

        for user_a, user_b, sim in rows:
            self.similarity_matrix[user_a][user_b] = sim
            self.similarity_matrix[user_b][user_a] = sim

        conn.close()
        print(f"  ✅ 从数据库加载了 {len(rows)} 条相似度记录")

    def get_top_k_neighbors(self, user_id: int) -> list[tuple[int, float]]:
        """
        获取目标用户的 K 个最相似用户

        大白话说明：
            从相似度矩阵中找出和目标用户最像的 K 个人。
            返回格式：[(用户ID, 相似度), ...]，按相似度从高到低排序

        参数：
            user_id: 目标用户ID
        返回：
            最相似的K个用户及其相似度
        """
        neighbors = self.similarity_matrix.get(user_id, {})

        # 按相似度从高到低排序，取前K个
        sorted_neighbors = sorted(neighbors.items(), key=lambda x: x[1], reverse=True)
        return sorted_neighbors[:self.k]

    def predict_rating(self, user_id: int, spot_id: int) -> Optional[float]:
        """
        预测用户对某个景点的评分

        大白话说明：
            用加权平均法预测用户对一个没评过分的景点会打几分。

            公式：
                              Σ sim(u,v) × (r_vi - r̄_v)
            r̂_ui = r̄_u + ────────────────────────────────
                              Σ |sim(u,v)|

            翻译成人话就是：
            预测分 = 用户的平均分 + 近邻们对这个景点的"偏差"的加权平均

            比如：用户A平均给景点打3.5分，近邻B觉得这个景点比自己平均分高1分，
            近邻C觉得高0.5分，那用户A对这个景点的预测分就是 3.5 + 加权(1, 0.5)

        参数：
            user_id: 目标用户ID
            spot_id: 目标景点ID
        返回：
            预测评分（1.0-5.0），如果无法预测返回None
        """
        neighbors = self.get_top_k_neighbors(user_id)

        if not neighbors:
            return None

        user_avg = self.user_avg_ratings.get(user_id, 3.5)

        # 加权求和
        weighted_sum = 0.0      # 分子
        similarity_sum = 0.0    # 分母

        for neighbor_id, similarity in neighbors:
            # 检查近邻是否评过这个景点
            neighbor_ratings = self.user_ratings.get(neighbor_id, {})
            if spot_id not in neighbor_ratings:
                continue

            neighbor_avg = self.user_avg_ratings.get(neighbor_id, 3.5)
            neighbor_rating = neighbor_ratings[spot_id]

            # 近邻对这个景点的"偏差" = 近邻对这景点的评分 - 近邻的平均分
            deviation = neighbor_rating - neighbor_avg

            # 加权偏差
            weighted_sum += similarity * deviation
            similarity_sum += abs(similarity)

        if similarity_sum == 0:
            return None

        # 预测分 = 用户平均分 + 加权偏差
        predicted = user_avg + weighted_sum / similarity_sum

        # 限制在 1.0-5.0 范围内
        return max(1.0, min(5.0, predicted))

    def recommend(self, user_id: int, n: int = 10, exclude_visited: bool = True) -> list[dict]:
        """
        为用户生成推荐列表

        大白话说明：
            1. 找出目标用户还没看过的景点
            2. 预测用户对每个候选景点的评分
            3. 按预测评分从高到低排序
            4. 取前 N 个返回

        参数：
            user_id: 目标用户ID
            n: 推荐数量，默认10个
            exclude_visited: 是否排除已浏览景点，默认True

        返回：
            [{spot_id, predicted_rating, reason}, ...]
        """
        # 获取用户已经评过分/浏览过的景点
        visited_spots = set(self.user_ratings.get(user_id, {}).keys())

        # 获取近邻用户评过分的所有景点（候选池）
        neighbors = self.get_top_k_neighbors(user_id)
        candidate_spots = set()
        for neighbor_id, _ in neighbors:
            neighbor_ratings = self.user_ratings.get(neighbor_id, {})
            candidate_spots.update(neighbor_ratings.keys())

        # 排除已访问的景点
        if exclude_visited:
            candidate_spots -= visited_spots

        # 对每个候选景点预测评分
        predictions = []
        for spot_id in candidate_spots:
            predicted = self.predict_rating(user_id, spot_id)
            if predicted is not None:
                # 统计有多少近邻评过这个景点（越多越可信）
                neighbor_count = sum(
                    1 for nid, _ in neighbors
                    if spot_id in self.user_ratings.get(nid, {})
                )
                predictions.append({
                    "spot_id": spot_id,
                    "predicted_rating": round(predicted, 2),
                    "neighbor_count": neighbor_count,
                    "reason": f"与您品味相似的{neighbor_count}位用户都喜欢这里",
                })

        # 按预测评分排序
        predictions.sort(key=lambda x: x["predicted_rating"], reverse=True)

        return predictions[:n]


def compute_and_save(db_path: str):
    """
    计算并保存相似度矩阵（独立脚本入口）

    大白话说明：
        这个函数可以作为独立脚本运行，一次性计算所有用户相似度
        并存入数据库。后续推荐直接从数据库读取即可。
    """
    print("=" * 60)
    print("🔄 协同过滤 - 用户相似度计算")
    print("=" * 60)

    cf = CollaborativeFilter(db_path)

    print("\n📊 加载评分数据...")
    cf.load_ratings()

    print("\n🧮 计算相似度矩阵...")
    cf.compute_similarity()

    # 测试推荐
    print("\n🔍 推荐测试（用户1）:")
    results = cf.recommend(user_id=1, n=5)
    for i, item in enumerate(results):
        print(f"  Top-{i+1}: 景点{item['spot_id']} "
              f"(预测评分:{item['predicted_rating']}, "
              f"{item['reason']})")

    print("\n✅ 协同过滤初始化完成！")
    return cf


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database import DB_PATH
    compute_and_save(DB_PATH)
