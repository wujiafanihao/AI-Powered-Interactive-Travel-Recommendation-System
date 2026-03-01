"""
基于内容的推荐引擎

大白话说明：
    内容推荐的核心思想：
    "你以前喜欢什么类型的景点，就给你推荐同类型的景点"

    具体步骤：
    1. 把每个景点的属性提取成一个"特征向量"（一串数字）
       - 景点类型（自然风光/历史文化等）→ 8维
       - 适宜季节（春/夏/秋/冬）→ 4维
       - 区域（华北/华东等）→ 7维
       - 适合人群（亲子/老年/情侣等）→ 6维
       - 评分、游玩时长、价格等级 → 3维
       总共约 28维

    2. 看用户历史行为，综合他浏览/收藏/评分过的景点特征，
       算出一个"用户偏好向量"

    3. 用余弦相似度比较"用户偏好向量"和"候选景点特征向量"，
       越相似的景点越优先推荐
"""

import sqlite3
import json
import math
import re
from collections import defaultdict
from typing import Optional


# ============================================
# 特征编码定义
# 大白话：把文字描述转成数字，方便计算
# ============================================

# 景点类型的 one-hot 编码（8维）
SPOT_TYPES = ["自然风光", "历史文化", "宗教场所", "主题乐园", "博物馆", "现代都市", "园林公园", "乡村田园"]

# 季节的 one-hot 编码（4维）
SEASONS = ["春", "夏", "秋", "冬"]

# 区域的 one-hot 编码（7维）
# 根据省份/城市归类
REGIONS = ["华北", "华东", "华南", "华中", "西南", "西北", "东北"]

# 省份到区域的映射
CITY_REGION_MAP = {
    "华北": ["北京", "天津", "石家庄", "太原", "呼和浩特", "保定", "唐山", "邯郸", "邢台",
            "张家口", "承德", "沧州", "廊坊", "衡水", "大同", "阳泉", "长治", "晋城",
            "朔州", "晋中", "运城", "忻州", "临汾", "吕梁", "包头", "乌海", "赤峰",
            "通辽", "鄂尔多斯", "呼伦贝尔", "巴彦淖尔", "乌兰察布", "兴安盟",
            "锡林郭勒盟", "阿拉善盟", "雄安新区", "秦皇岛", "坝上"],
    "华东": ["上海", "南京", "杭州", "合肥", "福州", "南昌", "济南", "苏州", "无锡",
            "常州", "徐州", "南通", "扬州", "镇江", "泰州", "宿迁", "淮安", "盐城",
            "连云港", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山",
            "台州", "丽水", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆",
            "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "宣城", "泉州", "厦门",
            "漳州", "莆田", "宁德", "龙岩", "三明", "南平", "九江", "新余", "鹰潭",
            "赣州", "吉安", "上饶", "抚州", "景德镇", "萍乡", "宜春", "青岛", "烟台",
            "威海", "日照", "枣庄", "济宁", "泰安", "莱芜", "淄博", "菏泽", "潍坊",
            "聊城", "德州", "东营", "滨州", "巢湖", "太湖"],
    "华南": ["广州", "深圳", "珠海", "东莞", "中山", "佛山", "惠州", "江门", "肇庆",
            "茂名", "汕头", "汕尾", "潮州", "揭阳", "韶关", "清远", "云浮", "阳江",
            "梅州", "河源", "湛江", "南宁", "柳州", "桂林", "玉林", "贵港", "百色",
            "钦州", "防城港", "贺州", "河池", "来宾", "崇左", "北海", "海口", "三亚",
            "万宁", "琼海", "儋州", "五指山", "东方", "乐东", "临高", "澄迈", "定安",
            "屯昌", "昌江", "白沙", "保亭", "陵水", "琼中", "三沙"],
    "华中": ["武汉", "长沙", "郑州", "宜昌", "十堰", "荆州", "襄阳", "咸宁", "黄冈",
            "鄂州", "孝感", "随州", "恩施", "神农架", "仙桃", "天门", "潜江",
            "岳阳", "常德", "张家界", "衡阳", "株洲", "湘潭", "邵阳", "益阳",
            "郴州", "永州", "怀化", "娄底", "湘西", "开封", "洛阳", "安阳",
            "新乡", "焦作", "濮阳", "许昌", "漯河", "商丘", "周口", "驻马店",
            "信阳", "南阳", "三门峡", "平顶山", "鹤壁", "济源"],
    "西南": ["成都", "重庆", "昆明", "贵阳", "拉萨", "德阳", "绵阳", "乐山", "宜宾",
            "泸州", "南充", "达州", "广安", "内江", "自贡", "广元", "遂宁", "眉山",
            "资阳", "攀枝花", "巴中", "雅安", "凉山", "甘孜", "阿坝",
            "大理", "丽江", "西双版纳", "楚雄州", "红河", "曲靖", "文山",
            "普洱", "临沧", "保山", "昭通", "玉溪", "德宏", "怒江", "迪庆",
            "遵义", "毕节", "安顺", "六盘水", "铜仁", "黔东南", "黔南", "黔西南",
            "林芝", "山南", "日喀则", "那曲", "阿里"],
    "西北": ["西安", "兰州", "银川", "西宁", "乌鲁木齐", "咸阳", "宝鸡", "渭南",
            "延安", "榆林", "汉中", "安康", "商洛", "铜川", "天水", "嘉峪关",
            "金昌", "白银", "酒泉", "张掖", "武威", "庆阳", "定西", "陇南",
            "吴忠", "石嘴山", "中卫", "固原",
            "吐鲁番", "哈密", "昌吉", "伊犁", "塔城", "阿勒泰", "阿克苏",
            "喀什", "和田", "巴音郭楞", "博尔塔拉", "克拉玛依",
            "克孜勒苏柯尔克孜", "阿拉尔", "图木舒克", "五家渠", "北屯",
            "铁门关", "双河", "可克达拉", "石河子", "昆玉", "青木川"],
    "东北": ["哈尔滨", "长春", "沈阳", "大连", "吉林市", "齐齐哈尔", "大庆",
            "牡丹江", "佳木斯", "鸡西", "鹤岗", "双鸭山", "伊春", "七台河",
            "黑河", "绥化", "大兴安岭", "延边", "四平", "辽源", "通化",
            "白城", "白山", "松原", "鞍山", "抚顺", "本溪", "丹东",
            "锦州", "营口", "阜新", "辽阳", "盘锦", "铁岭", "朝阳",
            "葫芦岛", "长白山"],
}

# 反转映射：城市 → 区域
_CITY_TO_REGION = {}
for region, cities in CITY_REGION_MAP.items():
    for city in cities:
        _CITY_TO_REGION[city] = region

# 适合人群（6维）
TARGET_GROUPS = ["亲子", "老年", "情侣", "学生", "摄影", "探险"]


class ContentBasedRecommender:
    """
    基于内容的推荐引擎

    大白话说明：
        核心工作就是：
        1. 给每个景点画一个"数字画像"（特征向量）
        2. 根据用户历史行为画一个"用户画像"（偏好向量）
        3. 找和用户画像最像的景点推荐出来
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        # 景点特征向量缓存: {spot_id: [特征向量]}
        self.spot_features = {}
        # 特征标签（方便理解每一维代表什么）
        self.feature_labels = (
            [f"类型_{t}" for t in SPOT_TYPES] +     # 8维
            [f"季节_{s}" for s in SEASONS] +          # 4维
            [f"区域_{r}" for r in REGIONS] +          # 7维
            [f"人群_{g}" for g in TARGET_GROUPS] +    # 6维
            ["评分", "游玩时长", "价格等级"]           # 3维
        )
        # 总维度
        self.feature_dim = len(self.feature_labels)  # 28维

    def extract_features(self, spot: dict) -> list[float]:
        """
        从景点数据中提取特征向量

        大白话说明：
            把一个景点的各种属性编码成一个28维的数字向量。
            每一维代表一个特征，值域是0-1。

        参数：
            spot: 景点信息字典（包含 spot_type, city, suggest_season 等字段）
        返回：
            28维特征向量
        """
        features = []

        # === 1. 景点类型（8维 one-hot） ===
        # 比如景点类型是["自然风光","历史文化"]，那第0维和第1维是1，其余是0
        spot_types = self._parse_json_field(spot.get("spot_type", "[]"))
        for t in SPOT_TYPES:
            features.append(1.0 if t in spot_types else 0.0)

        # === 2. 适宜季节（4维 one-hot） ===
        season_text = spot.get("suggest_season", "") or ""
        for s in SEASONS:
            features.append(1.0 if s in season_text else 0.0)

        # === 3. 区域（7维 one-hot） ===
        city = spot.get("city", "")
        region = _CITY_TO_REGION.get(city, "")
        for r in REGIONS:
            features.append(1.0 if r == region else 0.0)

        # === 4. 适合人群（6维 multi-hot） ===
        target_groups = self._parse_json_field(spot.get("target_group", "[]"))
        for g in TARGET_GROUPS:
            features.append(1.0 if g in target_groups else 0.0)

        # === 5. 评分（1维，归一化到0-1） ===
        rating = spot.get("rating") or 0.0
        features.append(rating / 5.0)  # 5.0 → 1.0, 4.0 → 0.8

        # === 6. 游玩时长（1维，归一化到0-1） ===
        suggest_time = spot.get("suggest_time", "") or ""
        hours = self._parse_hours(suggest_time)
        features.append(min(hours / 8.0, 1.0))  # 8小时以上都算1.0

        # === 7. 价格等级（1维，归一化到0-1） ===
        ticket_info = spot.get("ticket_info", "") or ""
        price_level = self._parse_price_level(ticket_info)
        features.append(price_level)

        return features

    def _parse_json_field(self, value: str) -> list[str]:
        """
        解析 JSON 字符串字段

        大白话：JSON 格式的字段解析成 Python 列表，解析失败就返回空列表
        """
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_hours(self, suggest_time: str) -> float:
        """
        从"建议游玩时间"文本中提取小时数

        大白话说明：
            文本格式各种各样，比如 "3小时 - 4小时"、"1天"、"半天" 等，
            这里尽量提取出一个小时数。

        示例：
            "建议游览时间：3小时 - 4小时" → 3.5
            "1天" → 8.0
            "半天" → 4.0
        """
        if not suggest_time:
            return 2.0  # 默认2小时

        if "天" in suggest_time or "全天" in suggest_time:
            # 找数字
            nums = re.findall(r'(\d+)\s*天', suggest_time)
            if nums:
                return float(nums[0]) * 8.0
            return 8.0

        if "半天" in suggest_time:
            return 4.0

        # 找小时数
        hours = re.findall(r'(\d+(?:\.\d+)?)\s*(?:小时|h|H)', suggest_time)
        if hours:
            # 如果有范围，取平均
            hour_values = [float(h) for h in hours]
            return sum(hour_values) / len(hour_values)

        return 2.0  # 默认

    def _parse_price_level(self, ticket_info: str) -> float:
        """
        从门票信息中提取价格等级

        大白话说明：
            把门票价格分成几档：
            - 免费 → 0.0
            - 便宜(≤50元) → 0.25
            - 中等(50-150元) → 0.5
            - 偏贵(150-300元) → 0.75
            - 很贵(>300元) → 1.0
        """
        if not ticket_info:
            return 0.25  # 默认便宜

        if "免费" in ticket_info or "免门票" in ticket_info:
            return 0.0

        # 尝试提取价格数字
        prices = re.findall(r'¥(\d+)', ticket_info)
        if not prices:
            prices = re.findall(r'(\d+)\s*(?:元|块)', ticket_info)

        if prices:
            min_price = min(int(p) for p in prices)
            if min_price <= 0:
                return 0.0
            elif min_price <= 50:
                return 0.25
            elif min_price <= 150:
                return 0.5
            elif min_price <= 300:
                return 0.75
            else:
                return 1.0

        return 0.25

    def load_and_compute_features(self):
        """
        从数据库加载所有景点并计算特征向量

        大白话说明：
            遍历数据库中的所有景点，为每个景点计算28维特征向量，
            并把结果缓存在内存中（也存入数据库）。
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, city, spot_type, target_group, rating,
                   suggest_time, suggest_season, ticket_info
            FROM spots
        """)
        rows = cursor.fetchall()

        # 清空旧的特征数据
        cursor.execute("DELETE FROM spot_features")

        for row in rows:
            spot = {
                "id": row[0], "name": row[1], "city": row[2],
                "spot_type": row[3], "target_group": row[4],
                "rating": row[5], "suggest_time": row[6],
                "suggest_season": row[7], "ticket_info": row[8],
            }

            features = self.extract_features(spot)
            self.spot_features[spot["id"]] = features

            # 存入数据库
            cursor.execute("""
                INSERT OR REPLACE INTO spot_features (spot_id, feature_vector, feature_labels)
                VALUES (?, ?, ?)
            """, (
                spot["id"],
                json.dumps(features),
                json.dumps(self.feature_labels, ensure_ascii=False),
            ))

        conn.commit()
        conn.close()

        print(f"  ✅ 计算了 {len(self.spot_features)} 个景点的特征向量 ({self.feature_dim}维)")

    def load_features_from_db(self):
        """
        从数据库加载已计算好的特征向量

        大白话说明：如果之前已经算过了，直接从数据库读
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT spot_id, feature_vector FROM spot_features")
        for spot_id, feature_str in cursor.fetchall():
            self.spot_features[spot_id] = json.loads(feature_str)

        conn.close()
        print(f"  ✅ 从数据库加载了 {len(self.spot_features)} 个景点特征")

    def build_user_profile(self, user_id: int) -> Optional[list[float]]:
        """
        根据用户历史行为构建用户偏好向量

        大白话说明：
            看用户以前浏览/收藏/评分过哪些景点，把这些景点的特征向量
            加权平均，得到一个代表用户偏好的向量。

            权重规则：
            - 浏览: 权重=1
            - 收藏: 权重=3（收藏说明很喜欢）
            - 评分: 权重=评分值×2（评分越高说明越喜欢）

            公式：
                        Σ w_i × f_i
            p_u = ─────────────────
                        Σ w_i

            其中 w_i 是行为权重，f_i 是景点特征向量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取用户的所有行为记录
        cursor.execute("""
            SELECT spot_id, behavior_type, rating
            FROM user_behaviors
            WHERE user_id = ?
        """, (user_id,))
        behaviors = cursor.fetchall()

        # 获取用户的收藏
        cursor.execute("SELECT spot_id FROM user_collections WHERE user_id = ?", (user_id,))
        collections = {row[0] for row in cursor.fetchall()}

        conn.close()

        if not behaviors and not collections:
            return None  # 纯新用户，没有任何行为

        # 加权求和
        weighted_sum = [0.0] * self.feature_dim
        total_weight = 0.0

        # 已处理的景点（避免重复计算）
        processed_spots = {}

        for spot_id, behavior_type, rating in behaviors:
            if spot_id not in self.spot_features:
                continue

            features = self.spot_features[spot_id]

            # 确定权重
            if behavior_type == "rate" and rating:
                weight = rating * 2.0  # 5分→权重10
            elif behavior_type == "collect" or spot_id in collections:
                weight = 3.0
            elif behavior_type == "browse":
                weight = 1.0
            else:
                weight = 0.5

            # 取该景点最高权重
            if spot_id in processed_spots:
                if weight <= processed_spots[spot_id]:
                    continue
            processed_spots[spot_id] = weight

            # 累加
            for d in range(self.feature_dim):
                weighted_sum[d] += weight * features[d]
            total_weight += weight

        if total_weight == 0:
            return None

        # 归一化：除以总权重
        user_profile = [ws / total_weight for ws in weighted_sum]

        return user_profile

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """
        计算两个向量的余弦相似度

        大白话说明：和协同过滤里的公式一样，就是看两个向量方向是否一致
        """
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def recommend(self, user_id: int, n: int = 10) -> list[dict]:
        """
        为用户生成基于内容的推荐列表

        大白话说明：
            1. 先构建用户偏好向量
            2. 计算用户偏好与每个候选景点的相似度
            3. 相似度最高的 N 个景点就是推荐结果

        返回：
            [{spot_id, similarity, reason}, ...]
        """
        # 构建用户偏好
        user_profile = self.build_user_profile(user_id)
        if user_profile is None:
            return []  # 冷启动，交给热门推荐

        # 获取用户已浏览过的景点（排除用）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT spot_id FROM user_behaviors WHERE user_id = ?
        """, (user_id,))
        visited = {row[0] for row in cursor.fetchall()}
        conn.close()

        # 计算与所有候选景点的相似度
        candidates = []
        for spot_id, features in self.spot_features.items():
            if spot_id in visited:
                continue

            sim = self.cosine_similarity(user_profile, features)

            # 生成推荐理由（找出最匹配的特征维度）
            reason = self._generate_reason(user_profile, features)

            candidates.append({
                "spot_id": spot_id,
                "similarity": round(sim, 4),
                "reason": reason,
            })

        # 按相似度排序
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:n]

    def _generate_reason(self, user_profile: list[float], spot_features: list[float]) -> str:
        """
        生成推荐理由

        大白话说明：
            找出用户偏好和景点特征中，双方都得分较高的维度，
            用来解释"为什么推荐这个景点给你"。
        """
        # 找出重叠最强的特征
        matched_features = []
        for i, (up, sf) in enumerate(zip(user_profile, spot_features)):
            if up > 0.3 and sf > 0.3:  # 双方都有明显倾向
                matched_features.append(self.feature_labels[i])

        if matched_features:
            # 取前3个最匹配的特征
            top_matches = matched_features[:3]
            # 清理标签名（去掉前缀）
            clean_names = [m.split("_")[-1] if "_" in m else m for m in top_matches]
            return f"因为您喜欢{'、'.join(clean_names)}类型的景点"
        else:
            return "根据您的综合浏览偏好推荐"


def compute_and_save(db_path: str):
    """
    计算并保存所有景点特征向量（独立脚本入口）
    """
    print("=" * 60)
    print("📊 内容推荐 - 景点特征计算")
    print("=" * 60)

    cbr = ContentBasedRecommender(db_path)

    print("\n🧮 计算景点特征向量...")
    cbr.load_and_compute_features()

    # 测试推荐
    print("\n🔍 推荐测试（用户1）:")
    results = cbr.recommend(user_id=1, n=5)
    for i, item in enumerate(results):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, city FROM spots WHERE id = ?", (item["spot_id"],))
        row = cursor.fetchone()
        conn.close()
        name = row[0] if row else "未知"
        city = row[1] if row else "未知"
        print(f"  Top-{i+1}: {name}({city}) "
              f"(相似度:{item['similarity']}, {item['reason']})")

    print("\n✅ 内容推荐引擎初始化完成！")
    return cbr


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from database import DB_PATH
    compute_and_save(DB_PATH)
