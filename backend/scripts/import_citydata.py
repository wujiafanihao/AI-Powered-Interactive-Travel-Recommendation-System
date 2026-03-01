"""
景点数据导入脚本 - 把 citydata 目录下的 CSV 文件导入 SQLite 数据库

大白话说明：
    这个脚本做的事情很简单：
    1. 遍历 citydata 目录下的 352 个城市 CSV 文件
    2. 读取每个 CSV 里的景点数据
    3. 清洗数据（去掉多余的换行、提取有用的信息）
    4. 自动识别景点类型标签（自然风光/历史文化/主题乐园等）
    5. 自动识别适合哪些人群（亲子/老年/情侣等）
    6. 把清洗后的数据写入 SQLite 的 spots 表

运行方式：
    cd backend
    python scripts/import_citydata.py
"""

import os
import sys
import csv
import re
import sqlite3
import json
from tqdm import tqdm

# 把 backend 目录加到 Python 路径里，这样才能导入 config 和 database
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_settings
from database import DB_PATH, init_db_sync

# citydata 目录的路径
CITYDATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "citydata"
)


# ============================================
# 景点类型关键词映射表
# 大白话：看景点名字和介绍里有没有这些关键词，来判断景点属于什么类型
# ============================================
SPOT_TYPE_KEYWORDS = {
    "自然风光": ["山", "湖", "河", "海", "瀑布", "峡谷", "森林", "草原", "沙漠",
                "岛", "溪", "泉", "潭", "洞", "峰", "岭", "滩", "湾", "林",
                "国家公园", "地质", "自然保护", "风景区", "生态"],
    "历史文化": ["故宫", "古城", "古镇", "遗址", "陵", "墓", "庙", "塔", "城墙",
                "故居", "纪念", "历史", "文化", "革命", "战役", "古迹", "文物",
                "长城", "石窟", "碑", "祠", "府", "衙"],
    "宗教场所": ["寺", "庙", "观", "教堂", "清真", "佛", "道观", "禅", "香火",
                "菩萨", "神殿", "宗教"],
    "主题乐园": ["乐园", "游乐", "世界", "欢乐", "水上", "动物园", "海洋馆",
                "植物园", "水族", "游乐场", "主题公园", "冒险"],
    "博物馆": ["博物馆", "展览", "美术馆", "科技馆", "纪念馆", "艺术馆",
              "陈列", "展馆", "画廊"],
    "现代都市": ["广场", "商业", "步行街", "夜市", "CBD", "摩天", "都市",
               "购物", "中心", "大厦", "现代"],
    "园林公园": ["公园", "园林", "花园", "植物", "绿地", "湿地公园"],
    "乡村田园": ["古村", "田园", "农庄", "乡村", "农家", "梯田", "村落"],
}

# ============================================
# 适合人群关键词映射表
# ============================================
TARGET_GROUP_KEYWORDS = {
    "亲子": ["亲子", "儿童", "小朋友", "孩子", "动物园", "游乐", "乐园",
            "海洋馆", "科技馆", "水族"],
    "老年": ["休闲", "养生", "温泉", "公园", "寺庙", "慢游", "轻松"],
    "情侣": ["浪漫", "夜景", "海滩", "日落", "花海", "薰衣草", "约会"],
    "学生": ["免费", "博物馆", "历史", "文化", "校园", "科教", "纪念馆"],
    "摄影": ["日出", "日落", "风光", "云海", "星空", "夜景", "摄影",
            "全景", "观景台"],
    "探险": ["徒步", "攀岩", "漂流", "探险", "穿越", "越野", "极限"],
}


def clean_address(raw_address: str) -> str:
    """
    清洗地址字段 - 从原始的多行文本中提取纯地址

    大白话说明：
        原始 CSV 里的"地址"字段其实包含了地址、电话、官网好几个信息，
        中间用换行符隔开。这个函数只提取"地址:"后面的部分。

    示例：
        输入: "\\n\\n地址:\\n北京市东城区景山前街4号\\n\\n\\n电话:\\n010-xxx"
        输出: "北京市东城区景山前街4号"
    """
    if not raw_address:
        return ""

    # 尝试匹配 "地址:" 后面的内容
    match = re.search(r'地址[:：]\s*\n?(.*?)(?:\n\n|\n电话|\n官网|$)', raw_address, re.DOTALL)
    if match:
        addr = match.group(1).strip()
        # 去掉多余的换行
        addr = addr.replace('\n', ' ').strip()
        return addr

    # 如果没有"地址:"标记，就返回清洗后的原文
    return raw_address.replace('\n', ' ').strip()[:200]


def extract_rating(raw_rating: str) -> float | None:
    """
    提取评分 - 把字符串转成浮点数

    大白话说明：
        CSV 里的评分是字符串格式（如 "4.8"），需要转成数字。
        如果评分为空或者格式不对，就返回 None。
    """
    if not raw_rating or not raw_rating.strip():
        return None
    try:
        rating = float(raw_rating.strip())
        # 评分应该在 1.0 到 5.0 之间
        if 1.0 <= rating <= 5.0:
            return rating
        return None
    except ValueError:
        return None


def detect_spot_types(name: str, description: str) -> list[str]:
    """
    自动检测景点类型 - 根据名称和介绍中的关键词判断

    大白话说明：
        遍历所有类型的关键词，如果景点名称或介绍里包含某个关键词，
        就认为这个景点属于那个类型。一个景点可以属于多个类型。
    """
    text = (name or "") + (description or "")
    types = []

    for type_name, keywords in SPOT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                types.append(type_name)
                break  # 一个类型只要匹配到一个关键词就够了

    # 如果一个类型都没匹配到，标记为"其他"
    if not types:
        types = ["其他"]

    return types


def detect_target_groups(name: str, description: str, tips: str) -> list[str]:
    """
    自动检测适合人群 - 根据关键词判断

    大白话说明：
        和上面检测景点类型的逻辑类似，看关键词来判断适合哪些人群。
    """
    text = (name or "") + (description or "") + (tips or "")
    groups = []

    for group_name, keywords in TARGET_GROUP_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                groups.append(group_name)
                break

    return groups


def import_city_csv(csv_path: str, city_name: str, cursor: sqlite3.Cursor) -> int:
    """
    导入单个城市的 CSV 文件

    大白话说明：
        读取一个城市的 CSV 文件，清洗数据后插入 spots 表。
        返回成功导入的景点数量。

    参数：
        csv_path: CSV 文件的路径
        city_name: 城市名（从文件名提取）
        cursor: 数据库游标
    """
    imported = 0

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # 提取并清洗各个字段
                    name = (row.get('名字') or '').strip()
                    if not name:
                        continue  # 没有名字的跳过

                    address = clean_address(row.get('地址', ''))
                    description = (row.get('介绍') or '').strip()
                    open_time = (row.get('开放时间') or '').strip()
                    image_url = (row.get('图片链接') or '').strip()
                    rating = extract_rating(row.get('评分', ''))
                    suggest_time = (row.get('建议游玩时间') or '').strip()
                    suggest_season = (row.get('建议季节') or '').strip()
                    ticket_info = (row.get('门票') or '').strip()
                    tips = (row.get('小贴士') or '').strip()
                    source_url = (row.get('链接') or '').strip()

                    # 自动识别景点类型和适合人群
                    spot_types = detect_spot_types(name, description)
                    target_groups = detect_target_groups(name, description, tips)

                    # 插入数据库
                    cursor.execute("""
                        INSERT INTO spots 
                        (name, city, address, description, open_time, image_url,
                         rating, suggest_time, suggest_season, ticket_info, tips,
                         spot_type, target_group, source_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        name, city_name, address, description, open_time, image_url,
                        rating, suggest_time, suggest_season, ticket_info, tips,
                        json.dumps(spot_types, ensure_ascii=False),
                        json.dumps(target_groups, ensure_ascii=False),
                        source_url
                    ))
                    imported += 1

                except Exception as e:
                    # 单条记录出错不影响整体，打印错误继续
                    print(f"  ⚠️ 跳过一条记录（{city_name}）: {e}")
                    continue

    except Exception as e:
        print(f"❌ 读取文件失败: {csv_path} -> {e}")

    return imported


def main():
    """
    主函数 - 执行完整的数据导入流程

    大白话说明：
        1. 先初始化数据库（建表）
        2. 清空旧的景点数据（避免重复导入）
        3. 遍历所有城市 CSV，逐个导入
        4. 打印导入统计信息
    """
    print("=" * 60)
    print("🗺️  TravelAI 景点数据导入工具")
    print("=" * 60)

    # 第一步：确保数据库和表已创建
    init_db_sync()

    # 第二步：连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 第三步：清空旧数据（如果之前导入过的话）
    cursor.execute("DELETE FROM spots")
    conn.commit()
    print(f"📂 数据源目录: {CITYDATA_DIR}")

    # 第四步：获取所有 CSV 文件
    csv_files = [f for f in os.listdir(CITYDATA_DIR) if f.endswith('.csv')]
    csv_files.sort()
    print(f"📊 发现 {len(csv_files)} 个城市文件")
    print("-" * 60)

    # 第五步：逐个导入
    total_imported = 0
    for csv_file in tqdm(csv_files, desc="导入进度"):
        # 从文件名提取城市名（去掉 .csv 后缀）
        city_name = csv_file.replace('.csv', '')
        csv_path = os.path.join(CITYDATA_DIR, csv_file)

        count = import_city_csv(csv_path, city_name, cursor)
        total_imported += count

    # 第六步：提交并关闭
    conn.commit()
    conn.close()

    # 打印统计信息
    print("-" * 60)
    print(f"✅ 导入完成！共导入 {total_imported} 条景点数据")
    print(f"💾 数据库路径: {DB_PATH}")

    # 验证导入结果
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 统计各项数据
    cursor.execute("SELECT COUNT(*) FROM spots")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT city) FROM spots")
    cities = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(rating) FROM spots WHERE rating IS NOT NULL")
    avg_rating = cursor.fetchone()[0]

    print(f"\n📊 数据库统计:")
    print(f"  总景点数: {total}")
    print(f"  覆盖城市: {cities}")
    print(f"  平均评分: {avg_rating:.2f}" if avg_rating else "  平均评分: N/A")

    # 展示几条样例
    cursor.execute("SELECT name, city, rating, spot_type FROM spots LIMIT 5")
    print(f"\n📋 样例数据:")
    for row in cursor.fetchall():
        print(f"  {row[1]} - {row[0]} | 评分:{row[2]} | 类型:{row[3]}")

    conn.close()


if __name__ == "__main__":
    main()
