"""
混合推荐系统效果评估脚本

大白话说明：
    这个脚本用来测试推荐系统到底"准不准"。

    核心逻辑：
    1. 给定一个用户提问（如"推荐北京周边适合亲子游的高分免费景点，四季皆宜"）
    2. 解析提问，提取搜索条件（城市、人群、季节、免费、高分等）
    3. 调用混合推荐引擎，拿到 Top-N 推荐结果
    4. 同时从数据库中按条件查出"真正符合要求的景点"作为 Ground Truth（真实相关集）
    5. 对比推荐结果和 Ground Truth，计算三个关键指标：
       - 准确率(Precision)：推荐的景点中，有多少是真正相关的 → 推荐的准不准
       - 召回率(Recall)：所有相关的景点中，有多少被推荐出来了 → 有没有漏掉好东西
       - F分数(F1-Score)：准确率和召回率的调和平均 → 综合表现

    输出效果类似：
        混合推荐结果 Top10:
          名字  景点类型  评分  建议季节  门票  地域  混合得分
          ...

        推荐效果评估:
          准确率: 0.6
          召回率: 0.3
          F分数: 0.4

使用方式：
    cd backend
    python scripts/evaluate_hybrid_recommender.py
"""

import sqlite3
import json
import sys
import os
import time
from collections import defaultdict
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from algorithms.hybrid_recommender import HybridRecommender
from algorithms.user_profile_recommender import UserProfileRecommender
from database import DB_PATH


# ============================================
# 一、用户提问解析器
# 大白话：把自然语言提问拆成结构化条件
# ============================================

def parse_query(query: str) -> dict:
    """
    解析用户提问，提取搜索条件

    大白话：
        用户说"推荐北京周边适合亲子游的高分免费景点，四季皆宜"，
        就提取出：城市=北京，人群=亲子，高分=True，免费=True，季节=四季
    """
    conditions = {
        'city': None,          # 城市
        'spot_type': None,     # 景点类型
        'target_group': None,  # 目标人群
        'season': None,        # 季节
        'free_only': False,    # 是否仅免费
        'high_rating': False,  # 是否仅高评分
    }

    # ---- 提取城市 ----
    # 覆盖主流城市（可按需扩展）
    cities = [
        '北京', '上海', '广州', '深圳', '南京', '杭州', '西安', '成都',
        '重庆', '武汉', '长沙', '厦门', '青岛', '大连', '苏州', '天津',
        '三亚', '桂林', '昆明', '哈尔滨', '丽江', '拉萨', '洛阳', '郑州',
        '济南', '福州', '合肥', '南昌', '贵阳', '兰州', '银川', '西宁',
        '海口', '沈阳', '长春', '太原', '呼和浩特', '乌鲁木齐',
    ]
    for city in cities:
        if city in query:
            conditions['city'] = city
            break

    # ---- 提取景点类型 ----
    type_mapping = {
        '自然风光': '自然风光', '风景': '自然风光', '山水': '自然风光',
        '历史文化': '历史文化', '古迹': '历史文化', '古城': '历史文化',
        '博物馆': '博物馆', '展览': '博物馆',
        '主题乐园': '主题乐园', '游乐园': '主题乐园', '乐园': '主题乐园',
        '园林公园': '园林公园', '公园': '园林公园',
        '宗教场所': '宗教场所', '寺庙': '宗教场所',
        '现代都市': '现代都市', '城市': '现代都市',
        '乡村田园': '乡村田园', '农家': '乡村田园',
    }
    for keyword, spot_type in type_mapping.items():
        if keyword in query:
            conditions['spot_type'] = spot_type
            break

    # ---- 提取目标人群 ----
    group_mapping = {
        '亲子': '亲子', '带孩子': '亲子', '小孩': '亲子', '儿童': '亲子', '遛娃': '亲子',
        '老人': '老年', '老年': '老年', '父母': '老年', '长辈': '老年',
        '情侣': '情侣', '约会': '情侣', '浪漫': '情侣',
        '学生': '学生', '毕业': '学生',
        '摄影': '摄影', '拍照': '摄影', '打卡': '摄影',
        '探险': '探险', '冒险': '探险', '户外': '探险',
    }
    for keyword, group in group_mapping.items():
        if keyword in query:
            conditions['target_group'] = group
            break

    # ---- 提取季节 ----
    season_mapping = {
        '春天': '春', '春季': '春', '春游': '春',
        '夏天': '夏', '夏季': '夏', '避暑': '夏',
        '秋天': '秋', '秋季': '秋', '赏秋': '秋',
        '冬天': '冬', '冬季': '冬', '赏雪': '冬',
        '四季皆宜': '四季皆宜', '四季': '四季皆宜', '全年': '四季皆宜',
    }
    for keyword, season in season_mapping.items():
        if keyword in query:
            conditions['season'] = season
            break

    # ---- 是否免费 ----
    if '免费' in query or '不要钱' in query or '不收费' in query:
        conditions['free_only'] = True

    # ---- 是否高评分 ----
    if '高分' in query or '评分高' in query or '好评' in query:
        conditions['high_rating'] = True

    return conditions


# ============================================
# 二、Ground Truth 构建器
# 大白话：从数据库中查出"真正符合条件"的景点集合
# ============================================

def build_ground_truth(conditions: dict, limit: int = 100) -> set:
    """
    根据解析出的条件，从数据库中查出真正符合要求的景点 ID 集合

    大白话：
        这是"标准答案"。推荐系统推出来的景点，
        如果在这个集合里，就算推荐对了。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 构建 SQL 查询
    query = """
        SELECT id, name, city, spot_type, target_group, rating,
               suggest_season, ticket_info
        FROM spots
        WHERE 1=1
    """
    params = []

    # 按城市过滤
    if conditions.get('city'):
        query += " AND city = ?"
        params.append(conditions['city'])

    # 按景点类型过滤
    if conditions.get('spot_type'):
        query += " AND spot_type LIKE ?"
        params.append(f"%{conditions['spot_type']}%")

    # 按目标人群过滤
    if conditions.get('target_group'):
        query += " AND target_group LIKE ?"
        params.append(f"%{conditions['target_group']}%")

    # 按季节过滤
    if conditions.get('season'):
        if conditions['season'] == '四季皆宜':
            query += " AND (suggest_season LIKE '%四季%' OR suggest_season LIKE '%全年%' OR suggest_season LIKE '%一年%')"
        else:
            query += " AND (suggest_season LIKE ? OR suggest_season LIKE '%四季%' OR suggest_season LIKE '%全年%')"
            params.append(f"%{conditions['season']}%")

    # 免费过滤
    if conditions.get('free_only'):
        query += " AND (ticket_info LIKE '%免费%' OR ticket_info = '0' OR ticket_info LIKE '%免票%' OR ticket_info LIKE '%免门票%')"

    # 高评分过滤（4.0 以上算高分）
    if conditions.get('high_rating'):
        query += " AND rating >= 4.0"

    query += " ORDER BY rating DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    # 返回景点 ID 集合
    ground_truth_ids = {row[0] for row in results}
    return ground_truth_ids


# ============================================
# 三、混合推荐 + 条件重排序
# 大白话：先走混合推荐拿候选集，再按用户条件计算得分排序
# ============================================

def get_hybrid_recommendations(user_id: int, conditions: dict, top_n: int = 10) -> list[dict]:
    """
    获取混合推荐结果，并根据用户条件做二次重排序

    大白话：
        1. 混合推荐引擎给出候选景点+基础分
        2. 再根据用户提问的条件（城市、类型、人群等）计算匹配加分
        3. 基础分 + 匹配加分 = 混合得分，按混合得分排序
    """
    engine = HybridRecommender(DB_PATH)
    engine.initialize()

    # 如果条件里有特定城市或人群，可以传 scene 给引擎进行初始过滤
    scene = None
    if conditions.get('target_group'):
        scene = conditions['target_group'] + '游'
    
    # 获取推荐结果（候选池放大到 5000 以覆盖目标城市的候选数据）
    raw_recs = engine.recommend(user_id, n=top_n * 500, scene=scene)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    results = []
    for rec in raw_recs:
        spot_id = rec['spot_id']

        # 查景点详情
        cursor.execute("""
            SELECT id, name, city, spot_type, target_group, rating,
                   suggest_season, ticket_info, address
            FROM spots WHERE id = ?
        """, (spot_id,))
        spot_row = cursor.fetchone()
        if not spot_row:
            continue

        spot = dict(spot_row)

        # 计算条件匹配加分
        condition_bonus = 0.0

        # 城市匹配
        if conditions.get('city') and spot['city'] == conditions['city']:
            condition_bonus += 5000.0  # 极大增加城市匹配的权重，确保推荐结果不出城

        # 景点类型匹配
        if conditions.get('spot_type'):
            spot_types_raw = spot.get('spot_type', '[]')
            try:
                spot_types = json.loads(spot_types_raw) if spot_types_raw else []
            except (json.JSONDecodeError, TypeError):
                spot_types = []
            
            if conditions['spot_type'] in spot_types:
                # 判断是否是主类型（即第一个元素）
                if spot_types[0] == conditions['spot_type']:
                    condition_bonus += 800.0  # 主类型大幅加分
                else:
                    condition_bonus += 100.0  # 附带类型少量加分
            elif conditions['spot_type'] in str(spot_types_raw):
                condition_bonus += 100.0

        # 目标人群匹配
        if conditions.get('target_group'):
            target_raw = spot.get('target_group', '[]')
            try:
                targets = json.loads(target_raw) if target_raw else []
            except (json.JSONDecodeError, TypeError):
                targets = []
                
            if conditions['target_group'] in targets:
                if targets and targets[0] == conditions['target_group']:
                    condition_bonus += 800.0
                else:
                    condition_bonus += 200.0
            elif conditions['target_group'] in str(target_raw):
                condition_bonus += 100.0

        # 季节匹配
        if conditions.get('season'):
            season_text = str(spot.get('suggest_season', '') or '')
            if conditions['season'] in season_text or '四季' in season_text or '全年' in season_text:
                condition_bonus += 200.0

        # 免费匹配
        if conditions.get('free_only'):
            ticket = str(spot.get('ticket_info', '') or '')
            if '免费' in ticket or ticket == '0' or '免票' in ticket or '免门票' in ticket or ticket.strip() == '':
                condition_bonus += 200.0

        # 高评分匹配
        if conditions.get('high_rating'):
            rating = spot.get('rating') or 0
            if rating >= 4.0:
                condition_bonus += 100.0

        # 混合得分 = 推荐引擎基础分 × 加权系数 + 条件匹配加分
        base_score = rec.get('score', 0) * 100  # 归一化到 0-100
        hybrid_score = base_score + condition_bonus

        # 解析显示字段
        spot_type_display = '未知'
        try:
            types = json.loads(spot.get('spot_type', '[]') or '[]')
            if types:
                if conditions.get('spot_type') and conditions['spot_type'] in types and types[0] != conditions['spot_type']:
                    # 要求搜索的类型是副标签时，将它和主标签一起显示出来，缓解用户的错觉
                    spot_type_display = f"{types[0]},{conditions['spot_type']}"
                else:
                    spot_type_display = types[0]
        except (json.JSONDecodeError, TypeError):
            spot_type_display = '未知'

        results.append({
            'spot_id': spot_id,
            'name': spot['name'],
            'city': spot['city'],
            'spot_type': spot_type_display,
            'rating': spot.get('rating', 0) or 0,
            'suggest_season': spot.get('suggest_season', '未知'),
            'ticket_info': spot.get('ticket_info', '未知'),
            'address': spot.get('address', ''),
            'base_score': round(base_score, 4),
            'condition_bonus': round(condition_bonus, 4),
            'hybrid_score': round(hybrid_score, 6),
            'source': rec.get('source', 'hybrid'),
        })

    conn.close()

    # 按混合得分排序
    results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    return results[:top_n]


# ============================================
# 四、评估指标计算器
# 大白话：用推荐结果和标准答案算准确率、召回率、F 分数
# ============================================

def calculate_metrics(recommended_ids: set, ground_truth_ids: set) -> dict:
    """
    计算推荐评估指标

    公式：
        准确率 = |推荐 ∩ 相关| / |推荐|    （推荐了多少是对的）
        召回率 = |推荐 ∩ 相关| / |相关|    （真正相关的推了多少出来）
        F分数  = 2 × 准确率 × 召回率 / (准确率 + 召回率)
    """
    if not recommended_ids or not ground_truth_ids:
        return {'precision': 0.0, 'recall': 0.0, 'f1_score': 0.0, 'hit_count': 0}

    # 交集：推荐对了的景点
    hits = recommended_ids & ground_truth_ids
    hit_count = len(hits)

    # 准确率：推荐的里面有多少是对的
    precision = hit_count / len(recommended_ids) if recommended_ids else 0.0

    # 召回率：所有相关的里面有多少被推出来了
    recall = hit_count / len(ground_truth_ids) if ground_truth_ids else 0.0

    # F1 分数：准确率和召回率的调和平均
    if precision + recall > 0:
        f1_score = 2 * precision * recall / (precision + recall)
    else:
        f1_score = 0.0

    return {
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1_score': round(f1_score, 4),
        'hit_count': hit_count,
    }


# ============================================
# 五、漂亮打印函数
# 大白话：把结果用表格形式打印出来看
# ============================================

def print_conditions(conditions: dict):
    """打印解析出的搜索条件"""
    print("\n📋 解析出的搜索条件:")
    labels = {
        'city': '城市', 'spot_type': '景点类型', 'target_group': '目标人群',
        'season': '季节', 'free_only': '仅免费', 'high_rating': '仅高分',
    }
    for key, label in labels.items():
        value = conditions.get(key)
        if value:
            if isinstance(value, bool):
                print(f"   • {label}: {'是' if value else '否'}")
            else:
                print(f"   • {label}: {value}")


def print_recommendation_table(recommendations: list[dict], query: str):
    """打印推荐结果表格（类似图片中的格式）"""
    print(f"\n{'='*120}")
    print(f"用户需求：{query}")
    print(f"\n混合推荐结果 Top{len(recommendations)}:")

    # 表头
    header = f"{'名字':<30} {'景点类型':<12} {'评分':<6} {'建议季节':<10} {'门票':<12} {'地域':<12} {'混合得分':>12}"
    print(header)
    print("-" * 120)

    # 数据行
    for rec in recommendations:
        name = rec['name'][:28]
        spot_type = rec['spot_type'][:10]
        rating = f"{rec['rating']:.1f}" if rec['rating'] else "N/A"
        season = str(rec['suggest_season'] or '未知')[:8]

        # 门票显示处理
        ticket = str(rec['ticket_info'] or '未知')
        if len(ticket) > 10:
            ticket = ticket[:9] + "…"

        # 地域显示（城市+地区）
        city = rec['city']
        address = rec.get('address', '')
        # 尝试提取区
        district = ''
        if address:
            for suffix in ['区', '县', '市']:
                idx = address.find(suffix)
                if idx > 0:
                    # 往前找最近的城市名结束位置
                    start = max(0, idx - 4)
                    district = address[start:idx + 1]
                    break
        region = f"{city}{district}" if district else city

        hybrid_score = f"{rec['hybrid_score']:.6f}"

        print(f"{name:<30} {spot_type:<12} {rating:<6} {season:<10} {ticket:<12} {region:<12} {hybrid_score:>12}")

    print("=" * 120)


def print_metrics(metrics: dict, recommended_count: int, ground_truth_count: int):
    """打印评估指标"""
    print(f"\n📊 推荐效果评估:")
    print(f"   推荐数量: {recommended_count}")
    print(f"   相关景点总数: {ground_truth_count}")
    print(f"   命中数量: {metrics['hit_count']}")
    print(f"   准确率: {metrics['precision']}")
    print(f"   召回率: {metrics['recall']}")
    print(f"   F分数: {metrics['f1_score']}")


# ============================================
# 六、单次评估流程
# 大白话：输入一条提问，跑完整个评估流程
# ============================================

def evaluate_single_query(query: str, user_id: int = 1, top_n: int = 10):
    """
    对单条用户提问执行完整的推荐评估

    参数：
        query: 用户提问文本
        user_id: 使用哪个用户的画像来做推荐
        top_n: 推荐 Top-N 个结果
    返回：
        评估指标字典
    """
    print(f"\n{'#'*120}")
    print(f"# 用户提问：{query}")
    print(f"# 用户 ID：{user_id}  |  Top-N：{top_n}")
    print(f"{'#'*120}")

    # 1. 解析提问条件
    conditions = parse_query(query)
    print_conditions(conditions)

    # 2. 构建 Ground Truth（真实相关集）
    ground_truth_ids = build_ground_truth(conditions)
    print(f"\n🎯 Ground Truth（真实相关景点数量）: {len(ground_truth_ids)}")

    if not ground_truth_ids:
        print("⚠️  未找到符合条件的景点，请检查查询条件是否过于严格")
        return {'precision': 0.0, 'recall': 0.0, 'f1_score': 0.0, 'hit_count': 0}

    # 3. 获取混合推荐结果
    print(f"\n⏳ 正在运行混合推荐引擎...")
    start_time = time.time()
    recommendations = get_hybrid_recommendations(user_id, conditions, top_n)
    elapsed = time.time() - start_time
    print(f"✅ 推荐完成，耗时 {elapsed:.2f} 秒")

    # 4. 打印推荐结果表格
    print_recommendation_table(recommendations, query)

    # 5. 计算评估指标
    recommended_ids = {rec['spot_id'] for rec in recommendations}
    metrics = calculate_metrics(recommended_ids, ground_truth_ids)

    # 6. 打印评估结果
    print_metrics(metrics, len(recommended_ids), len(ground_truth_ids))

    # 7. 打印命中/未命中分析
    hits = recommended_ids & ground_truth_ids
    misses = recommended_ids - ground_truth_ids

    if hits:
        print(f"\n   ✅ 命中景点:")
        for rec in recommendations:
            if rec['spot_id'] in hits:
                print(f"      • {rec['name']}（{rec['city']}）混合得分: {rec['hybrid_score']:.4f}")

    if misses:
        print(f"\n   ❌ 未命中景点（推荐了但不在相关集中）:")
        for rec in recommendations:
            if rec['spot_id'] in misses:
                print(f"      • {rec['name']}（{rec['city']}）混合得分: {rec['hybrid_score']:.4f}")

    return metrics


# ============================================
# 七、批量评估（多条提问 + 多用户）
# 大白话：批量跑多条提问，算平均指标
# ============================================

def run_batch_evaluation():
    """
    批量评估：使用预设的测试用例，全面评估推荐系统效果
    """
    # 预设测试查询集
    test_queries = [
        "推荐北京周边适合亲子游的高分免费景点，四季皆宜",
        "上海有什么好玩的历史文化景点",
        "成都适合情侣去的免费公园",
        "西安有什么高分的历史文化景点",
        "杭州适合老人去的自然风光景点",
        "南京适合学生去的博物馆",
        "广州有什么亲子游乐园",
        "厦门适合拍照打卡的景点",
        "重庆有什么免费的自然风光景点",
        "武汉适合春天去的高分景点",
    ]

    # 使用多个用户测试（活跃用户 / 普通用户 / 新用户）
    test_user_ids = [1, 50, 100]

    print("\n" + "=" * 120)
    print("🔬 混合推荐系统批量评估")
    print(f"📅 评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 测试查询数: {len(test_queries)}")
    print(f"👥 测试用户数: {len(test_user_ids)}")
    print("=" * 120)

    all_metrics = []

    for user_id in test_user_ids:
        print(f"\n{'*'*120}")
        print(f"👤 当前测试用户 ID: {user_id}")
        print(f"{'*'*120}")

        user_metrics = []

        for query in test_queries:
            try:
                metrics = evaluate_single_query(query, user_id=user_id, top_n=10)
                metrics['query'] = query
                metrics['user_id'] = user_id
                user_metrics.append(metrics)
                all_metrics.append(metrics)
            except Exception as e:
                print(f"\n❌ 评估失败: {query}")
                print(f"   错误信息: {e}")
                import traceback
                traceback.print_exc()

        # 用户级汇总
        if user_metrics:
            avg_precision = sum(m['precision'] for m in user_metrics) / len(user_metrics)
            avg_recall = sum(m['recall'] for m in user_metrics) / len(user_metrics)
            avg_f1 = sum(m['f1_score'] for m in user_metrics) / len(user_metrics)

            print(f"\n{'='*80}")
            print(f"📊 用户 {user_id} 汇总（{len(user_metrics)} 条查询）:")
            print(f"   平均准确率: {avg_precision:.4f}")
            print(f"   平均召回率: {avg_recall:.4f}")
            print(f"   平均 F 分数: {avg_f1:.4f}")
            print(f"{'='*80}")

    # ---- 全局汇总 ----
    if all_metrics:
        print(f"\n{'#'*120}")
        print(f"📈 全局评估汇总")
        print(f"{'#'*120}")

        total_precision = sum(m['precision'] for m in all_metrics) / len(all_metrics)
        total_recall = sum(m['recall'] for m in all_metrics) / len(all_metrics)
        total_f1 = sum(m['f1_score'] for m in all_metrics) / len(all_metrics)

        print(f"\n   总测试数: {len(all_metrics)} 条")
        print(f"   平均准确率 (Precision): {total_precision:.4f}")
        print(f"   平均召回率 (Recall):    {total_recall:.4f}")
        print(f"   平均 F 分数 (F1-Score): {total_f1:.4f}")

        # 按查询分组的详细表格
        print(f"\n   📋 按查询分组详情:")
        print(f"   {'查询':<45} {'准确率':>8} {'召回率':>8} {'F分数':>8}")
        print(f"   {'-'*75}")

        # 按查询去重取平均
        query_groups = defaultdict(list)
        for m in all_metrics:
            query_groups[m['query']].append(m)

        for q, ms in query_groups.items():
            avg_p = sum(m['precision'] for m in ms) / len(ms)
            avg_r = sum(m['recall'] for m in ms) / len(ms)
            avg_f = sum(m['f1_score'] for m in ms) / len(ms)
            q_display = q[:43] if len(q) > 43 else q
            print(f"   {q_display:<45} {avg_p:>8.4f} {avg_r:>8.4f} {avg_f:>8.4f}")

        print(f"\n{'#'*120}")


# ============================================
# 八、交互式评估（支持用户自由输入）
# ============================================

def interactive_mode():
    """
    交互式模式：用户手动输入提问，实时查看推荐结果和评估指标
    """
    print("\n" + "=" * 80)
    print("🎮 混合推荐系统 - 交互式评估工具")
    print("=" * 80)
    print("💡 输入你的需求，查看推荐结果和评估指标")
    print("   输入 'batch' 运行批量评估")
    print("   输入 'quit' 或 'exit' 退出")
    print("=" * 80)

    # 默认用户 ID
    user_id = 1

    while True:
        try:
            query = input("\n🔍 你的需求：").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break

            if query.lower() == 'batch':
                run_batch_evaluation()
                continue

            # 支持切换用户 ID
            if query.startswith('user:'):
                try:
                    user_id = int(query.split(':')[1].strip())
                    print(f"✅ 已切换到用户 ID: {user_id}")
                except ValueError:
                    print("❌ 用户 ID 格式错误，请输入数字")
                continue

            # 执行评估
            evaluate_single_query(query, user_id=user_id, top_n=10)

        except KeyboardInterrupt:
            print("\n\n👋 已退出")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()


# ============================================
# 主入口
# ============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="混合推荐系统效果评估脚本")
    parser.add_argument(
        '--mode', '-m',
        choices=['interactive', 'batch', 'single'],
        default='interactive',
        help='运行模式: interactive(交互), batch(批量), single(单次)'
    )
    parser.add_argument(
        '--query', '-q',
        type=str,
        default='推荐北京周边适合亲子游的高分免费景点，四季皆宜',
        help='单次评估时的查询语句'
    )
    parser.add_argument(
        '--user-id', '-u',
        type=int,
        default=1,
        help='用户 ID（默认: 1）'
    )
    parser.add_argument(
        '--top-n', '-n',
        type=int,
        default=10,
        help='推荐结果数量（默认: 10）'
    )

    args = parser.parse_args()

    if args.mode == 'batch':
        run_batch_evaluation()
    elif args.mode == 'single':
        evaluate_single_query(args.query, user_id=args.user_id, top_n=args.top_n)
    else:
        interactive_mode()
