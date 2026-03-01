"""
模拟用户数据生成脚本

大白话说明：
    这个脚本负责生成"假的但逼真的"用户数据，用来测试推荐算法。
    生成的数据包括：
    1. 150 个用户（不同年龄、性别、旅行偏好）
    2. ~15000 条行为记录（浏览、评分、搜索）
    3. ~2000 条收藏记录
    
    关键设计思路：
    - 用户的行为要和他的偏好"对得上号"（比如喜欢自然风光的用户，大部分浏览记录应该是自然景点）
    - 不同活跃度的用户行为数量不同（活跃用户行为多，新用户行为少）
    - 新用户（行为很少）用来测试"冷启动"问题

    生成完的数据会：
    1. 保存为 JSON 文件到 citydata/ 目录
    2. 同时导入 SQLite 数据库

运行方式：
    cd backend
    python scripts/generate_mock_users.py
"""

import os
import sys
import json
import random
import sqlite3
from datetime import datetime, timedelta
from tqdm import tqdm

# 把 backend 目录加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings
from database import DB_PATH, init_db_sync

# 输出目录：citydata/
CITYDATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "citydata"
)

# 设置随机种子，保证每次运行生成的数据一致（可复现）
random.seed(42)


# ============================================
# 用户生成的配置参数
# ============================================

# 总用户数
TOTAL_USERS = 150

# 用户昵称前缀池（随机组合用的）
NICKNAME_PREFIXES = [
    "背包客", "旅行者", "探险家", "漫步者", "驴友",
    "摄影师", "美食家", "文艺青年", "自驾侠", "观光客",
    "徒步党", "度假狂", "寻宝者", "追风人", "赶海人",
]

NICKNAME_SUFFIXES = [
    "小明", "小红", "小刚", "大伟", "志强", "丽华", "秀英", "建国",
    "芳芳", "婷婷", "杰哥", "磊哥", "静静", "洋洋", "悦悦",
    "阿飞", "阿杰", "阿花", "小鱼", "小熊", "小鹿", "阿宝",
    "云朵", "星辰", "月亮", "风筝", "浪花", "彩虹", "雪花",
    "大山", "小溪", "翠花", "铁柱", "二狗", "旺财",
]

# 城市池（用于分配用户所在城市）
USER_CITIES = [
    # 一线城市
    "北京", "上海", "广州", "深圳",
    # 二线城市
    "杭州", "南京", "成都", "武汉", "西安", "重庆", "长沙", "青岛",
    "大连", "厦门", "昆明", "哈尔滨", "郑州", "合肥", "济南", "福州",
    # 三线及以下
    "洛阳", "桂林", "丽江", "三亚", "黄山", "张家界", "九江", "泉州",
    "扬州", "绍兴", "威海", "秦皇岛", "大理", "呼伦贝尔", "拉萨",
]

# 旅行风格选项
TRAVEL_STYLES = ["自然风光", "历史文化", "美食探店", "亲子游", "摄影打卡", "休闲度假", "探险运动", "宗教朝圣"]

# 年龄段分布配置
# 格式：(最小年龄, 最大年龄, 占比, 偏好的旅行风格倾向)
AGE_GROUPS = [
    (18, 25, 0.25, ["自然风光", "摄影打卡", "美食探店", "探险运动"]),
    (26, 35, 0.30, ["自然风光", "美食探店", "休闲度假", "摄影打卡", "历史文化"]),
    (36, 50, 0.25, ["亲子游", "历史文化", "休闲度假", "自然风光"]),
    (51, 70, 0.20, ["历史文化", "宗教朝圣", "休闲度假", "自然风光"]),
]

# 用户活跃度分布
# 格式：(活跃度标签, 占比, 行为数量范围)
ACTIVITY_LEVELS = [
    ("高活跃", 0.20, (150, 300)),
    ("普通",  0.50, (50, 150)),
    ("低活跃", 0.20, (10, 50)),
    ("新用户", 0.10, (0, 10)),
]


def generate_users() -> list[dict]:
    """
    生成 150 个模拟用户

    大白话说明：
        按照年龄段分布，生成不同特征的用户。
        每个用户有随机的昵称、年龄、性别、城市和旅行偏好。
        旅行偏好会和年龄段相关（比如老年人更可能喜欢历史文化和宗教）。
    """
    users = []
    user_id = 1

    for min_age, max_age, ratio, preferred_styles in AGE_GROUPS:
        # 计算这个年龄段需要生成多少用户
        count = int(TOTAL_USERS * ratio)

        for _ in range(count):
            # 随机生成年龄
            age = random.randint(min_age, max_age)

            # 随机生成性别（52%女 48%男）
            gender = random.choice(["男"] * 48 + ["女"] * 52)

            # 随机生成旅行风格（优先选本年龄段偏好的风格，再随机加几个）
            # 先从偏好里选1-3个
            style_count = random.randint(1, 3)
            styles = random.sample(preferred_styles, min(style_count, len(preferred_styles)))
            # 再有30%概率从全部风格里随机加1个
            if random.random() < 0.3:
                extra = random.choice(TRAVEL_STYLES)
                if extra not in styles:
                    styles.append(extra)

            # 随机生成昵称
            prefix = random.choice(NICKNAME_PREFIXES)
            suffix = random.choice(NICKNAME_SUFFIXES)
            nickname = f"{prefix}{suffix}"

            # 随机选城市（一线30%，二线40%，三线30%）
            city_pool_weights = [0.30 / 4] * 4 + [0.40 / 16] * 16 + [0.30 / 15] * 15
            city = random.choices(USER_CITIES, weights=city_pool_weights, k=1)[0]

            # 密码用 bcrypt 哈希（这里用固定哈希，反正是模拟数据）
            # 所有模拟用户的密码都是 "password123"
            password_hash = "$2b$12$LJ3UlGYN.xAHjYkH2y6jxOZxFnFNEPLGKwXxQdQv/J50.XE8BYpPu"

            user = {
                "id": user_id,
                "username": f"user_{user_id:03d}",
                "password_hash": password_hash,
                "nickname": nickname,
                "age": age,
                "gender": gender,
                "city": city,
                "travel_style": json.dumps(styles, ensure_ascii=False),
                "accessibility": "large_font" if age >= 55 else "normal",
                "created_at": (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            users.append(user)
            user_id += 1

    # 如果因为取整导致不够 150 个，补充到 150
    while len(users) < TOTAL_USERS:
        age = random.randint(20, 45)
        gender = random.choice(["男", "女"])
        styles = random.sample(TRAVEL_STYLES, random.randint(1, 3))
        user = {
            "id": user_id,
            "username": f"user_{user_id:03d}",
            "password_hash": password_hash,
            "nickname": f"{random.choice(NICKNAME_PREFIXES)}{random.choice(NICKNAME_SUFFIXES)}",
            "age": age,
            "gender": gender,
            "city": random.choice(USER_CITIES),
            "travel_style": json.dumps(styles, ensure_ascii=False),
            "accessibility": "normal",
            "created_at": (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 365))).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        users.append(user)
        user_id += 1

    print(f"✅ 生成了 {len(users)} 个用户")
    return users


def get_spots_by_type(cursor: sqlite3.Cursor) -> dict:
    """
    从数据库中获取按类型分组的景点 ID 列表

    大白话说明：
        把数据库里的景点按类型分个组，这样后面生成行为数据时，
        可以根据用户的旅行偏好，优先选择对应类型的景点。
    """
    cursor.execute("SELECT id, spot_type, rating FROM spots")
    rows = cursor.fetchall()

    # 按类型分组
    type_to_spots = {}
    all_spot_ids = []
    high_rating_spots = []  # 高分景点（给热门推荐用的）

    for row in rows:
        spot_id = row[0]
        spot_type_str = row[1] or "[]"
        rating = row[2]
        all_spot_ids.append(spot_id)

        # 高分景点
        if rating and rating >= 4.5:
            high_rating_spots.append(spot_id)

        # 按类型归类
        try:
            types = json.loads(spot_type_str)
        except json.JSONDecodeError:
            types = ["其他"]

        for t in types:
            if t not in type_to_spots:
                type_to_spots[t] = []
            type_to_spots[t].append(spot_id)

    return {
        "by_type": type_to_spots,
        "all": all_spot_ids,
        "high_rating": high_rating_spots,
    }


def pick_spots_for_user(user: dict, spots_info: dict, count: int) -> list[int]:
    """
    为用户选择景点（行为目标）

    大白话说明：
        根据用户的旅行偏好，生成他可能浏览的景点列表。
        规则：
        - 70% 的景点和用户偏好匹配（比如喜欢自然风光，就多选自然景点）
        - 30% 是随机的（人嘛，总会好奇看看别的）
    """
    user_styles = json.loads(user["travel_style"])

    # 类型名到景点数据类型的映射（用户偏好 → 景点分类的对应关系）
    style_to_type = {
        "自然风光": "自然风光",
        "历史文化": "历史文化",
        "美食探店": "现代都市",  # 美食探店的人一般也喜欢逛都市
        "亲子游": "主题乐园",
        "摄影打卡": "自然风光",
        "休闲度假": "园林公园",
        "探险运动": "自然风光",
        "宗教朝圣": "宗教场所",
    }

    # 70% 按偏好选
    preferred_count = int(count * 0.7)
    preferred_spots = []
    for style in user_styles:
        spot_type = style_to_type.get(style, "其他")
        available = spots_info["by_type"].get(spot_type, [])
        if available:
            sample_size = min(preferred_count // max(len(user_styles), 1), len(available))
            preferred_spots.extend(random.sample(available, max(1, sample_size)))

    # 30% 随机选
    random_count = count - len(preferred_spots)
    if random_count > 0:
        random_spots = random.sample(
            spots_info["all"],
            min(random_count, len(spots_info["all"]))
        )
        preferred_spots.extend(random_spots)

    # 去重并截断到目标数量
    seen = set()
    unique_spots = []
    for s in preferred_spots:
        if s not in seen:
            seen.add(s)
            unique_spots.append(s)
    
    return unique_spots[:count]


def generate_behaviors(users: list[dict], spots_info: dict) -> tuple[list[dict], list[dict]]:
    """
    生成用户行为记录和收藏记录

    大白话说明：
        为每个用户生成行为数据，包括浏览、评分、搜索。
        行为数量根据用户活跃度决定：
        - 活跃用户 150-300 条
        - 普通用户 50-150 条  
        - 低活跃用户 10-50 条
        - 新用户 0-10 条（用来测试冷启动）

    返回：
        (行为列表, 收藏列表)
    """
    all_behaviors = []
    all_collections = []
    behavior_id = 1
    collection_id = 1

    # 根据活跃度分配用户
    # 活跃20% 普通50% 低活跃20% 新用户10%
    activity_boundaries = [
        int(TOTAL_USERS * 0.20),                    # 0-30: 高活跃
        int(TOTAL_USERS * 0.70),                    # 30-105: 普通
        int(TOTAL_USERS * 0.90),                    # 105-135: 低活跃
        TOTAL_USERS,                                 # 135-150: 新用户
    ]

    # 搜索词池（模拟用户搜索过的关键词）
    search_queries = [
        "北京故宫", "上海外滩", "成都熊猫基地", "西安兵马俑",
        "杭州西湖", "三亚海滩", "丽江古城", "张家界玻璃桥",
        "桂林山水", "厦门鼓浪屿", "黄山日出", "九寨沟",
        "亲子游推荐", "老年人适合的景点", "免费景点",
        "周末去哪玩", "秋天赏红叶", "春天看花",
        "古镇推荐", "爬山好去处", "海边度假", "博物馆推荐",
        "情侣约会", "摄影好去处", "美食街", "夜景",
    ]

    for i, user in enumerate(tqdm(users, desc="生成行为数据")):
        user_id = user["id"]

        # 确定这个用户的活跃度级别和行为数量
        if i < activity_boundaries[0]:
            behavior_count = random.randint(150, 300)
        elif i < activity_boundaries[1]:
            behavior_count = random.randint(50, 150)
        elif i < activity_boundaries[2]:
            behavior_count = random.randint(10, 50)
        else:
            behavior_count = random.randint(0, 10)

        if behavior_count == 0:
            continue

        # 为这个用户选择行为目标景点
        target_spots = pick_spots_for_user(user, spots_info, behavior_count)

        # 用户的注册时间
        user_created = datetime.fromisoformat(user["created_at"])

        # 为每个景点生成行为
        collected_spots = set()  # 记录已收藏的景点（避免重复收藏）

        for spot_id in target_spots:
            # 随机生成行为发生时间（在用户注册之后）
            days_after = random.randint(0, 300)
            behavior_time = user_created + timedelta(
                days=days_after,
                hours=random.randint(6, 23),
                minutes=random.randint(0, 59)
            )

            # 行为类型分布：浏览60% 评分20% 搜索10% 收藏10%
            # 注意：收藏会同时生成到 collections 表
            rand = random.random()
            if rand < 0.60:
                # 浏览行为
                behavior = {
                    "id": behavior_id,
                    "user_id": user_id,
                    "spot_id": spot_id,
                    "behavior_type": "browse",
                    "rating": None,
                    "search_query": None,
                    "duration": random.randint(10, 600),  # 浏览时长 10-600秒
                    "created_at": behavior_time.isoformat(),
                }
                all_behaviors.append(behavior)
                behavior_id += 1

            elif rand < 0.80:
                # 评分行为（评分分布偏右偏高，毕竟去旅游的人大部分是愉快的）
                rating_weights = [0.05, 0.10, 0.25, 0.45, 0.15]  # 1星到5星的概率
                rating = random.choices([1.0, 2.0, 3.0, 4.0, 5.0], weights=rating_weights, k=1)[0]
                # 加点随机小数，让评分更真实
                rating = round(rating + random.uniform(-0.5, 0.5), 1)
                rating = max(1.0, min(5.0, rating))

                behavior = {
                    "id": behavior_id,
                    "user_id": user_id,
                    "spot_id": spot_id,
                    "behavior_type": "rate",
                    "rating": rating,
                    "search_query": None,
                    "duration": None,
                    "created_at": behavior_time.isoformat(),
                }
                all_behaviors.append(behavior)
                behavior_id += 1

            elif rand < 0.90:
                # 搜索行为
                behavior = {
                    "id": behavior_id,
                    "user_id": user_id,
                    "spot_id": spot_id,
                    "behavior_type": "search",
                    "rating": None,
                    "search_query": random.choice(search_queries),
                    "duration": None,
                    "created_at": behavior_time.isoformat(),
                }
                all_behaviors.append(behavior)
                behavior_id += 1

            else:
                # 收藏行为（同时记录到 behaviors 和 collections）
                behavior = {
                    "id": behavior_id,
                    "user_id": user_id,
                    "spot_id": spot_id,
                    "behavior_type": "collect",
                    "rating": None,
                    "search_query": None,
                    "duration": None,
                    "created_at": behavior_time.isoformat(),
                }
                all_behaviors.append(behavior)
                behavior_id += 1

                # 添加到收藏表（避免同一个用户重复收藏同一景点）
                if spot_id not in collected_spots:
                    collected_spots.add(spot_id)
                    collection = {
                        "id": collection_id,
                        "user_id": user_id,
                        "spot_id": spot_id,
                        "created_at": behavior_time.isoformat(),
                    }
                    all_collections.append(collection)
                    collection_id += 1

    print(f"✅ 生成了 {len(all_behaviors)} 条行为记录")
    print(f"✅ 生成了 {len(all_collections)} 条收藏记录")

    return all_behaviors, all_collections


def save_to_json(data: list[dict], filename: str):
    """
    保存数据到 JSON 文件

    大白话说明：
        把生成的数据保存成 JSON 文件，放到 citydata 目录下。
        这样即使数据库被删了，也可以从 JSON 文件重新导入。
    """
    filepath = os.path.join(CITYDATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存到: {filepath} ({len(data)} 条)")


def import_to_sqlite(users: list[dict], behaviors: list[dict], collections: list[dict]):
    """
    把生成的数据导入 SQLite 数据库

    大白话说明：
        把 JSON 格式的用户、行为、收藏数据写入数据库的对应表里。
        导入前先清空旧数据，避免重复。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 清空旧数据
    cursor.execute("DELETE FROM user_collections")
    cursor.execute("DELETE FROM user_behaviors")
    cursor.execute("DELETE FROM user_similarity")
    cursor.execute("DELETE FROM chat_history")
    cursor.execute("DELETE FROM users")
    conn.commit()

    # 导入用户
    for user in tqdm(users, desc="导入用户到数据库"):
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, nickname, age, gender,
                             city, travel_style, accessibility, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["id"], user["username"], user["password_hash"],
            user["nickname"], user["age"], user["gender"],
            user["city"], user["travel_style"], user["accessibility"],
            user["created_at"], user["updated_at"],
        ))

    # 导入行为记录（批量插入，速度快很多）
    behavior_data = [
        (b["user_id"], b["spot_id"], b["behavior_type"],
         b["rating"], b["search_query"], b["duration"], b["created_at"])
        for b in behaviors
    ]
    cursor.executemany("""
        INSERT INTO user_behaviors (user_id, spot_id, behavior_type,
                                   rating, search_query, duration, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, behavior_data)
    print(f"  ↳ 导入 {len(behavior_data)} 条行为记录")

    # 导入收藏记录
    collection_data = [
        (c["user_id"], c["spot_id"], c["created_at"])
        for c in collections
    ]
    cursor.executemany("""
        INSERT INTO user_collections (user_id, spot_id, created_at)
        VALUES (?, ?, ?)
    """, collection_data)
    print(f"  ↳ 导入 {len(collection_data)} 条收藏记录")

    conn.commit()
    conn.close()
    print("✅ 数据库导入完成")


def print_statistics(users, behaviors, collections):
    """
    打印数据统计信息

    大白话说明：
        展示生成数据的各项统计，让你一眼看出数据分布是否合理。
    """
    print("\n" + "=" * 60)
    print("📊 模拟数据统计报告")
    print("=" * 60)

    # 用户统计
    ages = [u["age"] for u in users]
    genders = [u["gender"] for u in users]
    print(f"\n👥 用户统计:")
    print(f"  总数: {len(users)}")
    print(f"  年龄范围: {min(ages)}-{max(ages)}, 平均: {sum(ages)/len(ages):.1f}")
    print(f"  性别分布: 男{genders.count('男')} 女{genders.count('女')}")

    # 年龄段分布
    age_groups = {"18-25": 0, "26-35": 0, "36-50": 0, "51-70": 0}
    for age in ages:
        if age <= 25: age_groups["18-25"] += 1
        elif age <= 35: age_groups["26-35"] += 1
        elif age <= 50: age_groups["36-50"] += 1
        else: age_groups["51-70"] += 1
    print(f"  年龄段分布: {age_groups}")

    # 行为统计
    behavior_types = {}
    for b in behaviors:
        bt = b["behavior_type"]
        behavior_types[bt] = behavior_types.get(bt, 0) + 1
    print(f"\n📝 行为统计:")
    print(f"  总行为数: {len(behaviors)}")
    for bt, count in sorted(behavior_types.items()):
        print(f"  {bt}: {count} ({count/len(behaviors)*100:.1f}%)")

    # 评分统计
    ratings = [b["rating"] for b in behaviors if b["rating"] is not None]
    if ratings:
        print(f"\n⭐ 评分统计:")
        print(f"  评分数: {len(ratings)}")
        print(f"  平均分: {sum(ratings)/len(ratings):.2f}")
        print(f"  最高分: {max(ratings)}, 最低分: {min(ratings)}")

    # 收藏统计
    print(f"\n❤️ 收藏统计:")
    print(f"  总收藏数: {len(collections)}")
    users_with_collections = len(set(c["user_id"] for c in collections))
    print(f"  有收藏的用户数: {users_with_collections}")
    if collections:
        print(f"  人均收藏: {len(collections)/users_with_collections:.1f}")


def main():
    """
    主函数 - 执行完整的模拟数据生成流程
    """
    print("=" * 60)
    print("🎭 TravelAI 模拟用户数据生成工具")
    print("=" * 60)
    print(f"📂 数据输出目录: {CITYDATA_DIR}")
    print(f"💾 数据库路径: {DB_PATH}")
    print()

    # 第一步：确保数据库已初始化
    init_db_sync()

    # 第二步：从数据库获取景点分类信息
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    spots_info = get_spots_by_type(cursor)
    total_spots = len(spots_info["all"])
    print(f"📊 数据库中共有 {total_spots} 个景点")
    print(f"📊 高分景点(≥4.5分): {len(spots_info['high_rating'])} 个")
    conn.close()

    if total_spots == 0:
        print("❌ 数据库中没有景点数据！请先运行 import_citydata.py")
        return

    # 第三步：生成用户数据
    print("\n--- 第1步：生成用户 ---")
    users = generate_users()

    # 第四步：生成行为和收藏数据
    print("\n--- 第2步：生成行为和收藏数据 ---")
    behaviors, collections = generate_behaviors(users, spots_info)

    # 第五步：保存到 JSON 文件
    print("\n--- 第3步：保存 JSON 文件 ---")
    save_to_json(users, "mock_users.json")
    save_to_json(behaviors, "mock_behaviors.json")
    save_to_json(collections, "mock_collections.json")

    # 第六步：导入数据库
    print("\n--- 第4步：导入数据库 ---")
    import_to_sqlite(users, behaviors, collections)

    # 第七步：打印统计报告
    print_statistics(users, behaviors, collections)

    print("\n" + "=" * 60)
    print("🎉 模拟数据生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
