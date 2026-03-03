"""
交互式用户推荐分析脚本

大白话说明：
    这个脚本让你通过账号密码登录，然后输入你的需求（如"推荐北京适合亲子游的高分免费景点"），
    系统会根据你的画像和提问，计算匹配评分并推荐景点。
"""

import sqlite3
import sys
import os
from getpass import getpass

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from algorithms.user_profile_recommender import UserProfileRecommender
from algorithms.hybrid_recommender import HybridRecommender
from database import DB_PATH


def authenticate_user(username: str, password: str) -> dict | None:
    """验证用户登录"""
    import bcrypt
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, nickname, city, travel_style, age, gender, password_hash
        FROM users
        WHERE username = ?
    """, (username,))
    
    user_row = cursor.fetchone()
    conn.close()
    
    if not user_row:
        return None
    
    # 验证密码
    password_hash = user_row["password_hash"]
    try:
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            user = dict(user_row)
            user.pop('password_hash', None)  # 移除密码哈希
            return user
    except Exception as e:
        print(f"密码验证失败：{e}")
        return None
    
    return None


def parse_user_query(query: str) -> dict:
    """解析用户提问，提取条件"""
    conditions = {
        'city': None,
        'spot_type': None,
        'target_group': None,
        'season': None,
        'free_only': False,
        'high_rating_only': False
    }
    
    # 提取城市
    cities = ['北京', '上海', '广州', '深圳', '南京', '杭州', '西安', '成都', '重庆', '武汉']
    for city in cities:
        if city in query:
            conditions['city'] = city
            break
    
    # 提取景点类型
    types = ['自然风光', '历史文化', '美食', '购物', '娱乐', '博物馆', '公园', '动物园', '游乐园']
    for t in types:
        if t in query:
            conditions['spot_type'] = t
            break
    
    # 提取人群
    groups = ['亲子', '情侣', '朋友', '老人', '学生', '一个人']
    for g in groups:
        if g in query:
            conditions['target_group'] = g
            break
    
    # 提取季节
    seasons = ['春', '夏', '秋', '冬', '四季']
    for s in seasons:
        if s in query:
            conditions['season'] = s
            break
    
    # 是否免费
    if '免费' in query or '不要钱' in query:
        conditions['free_only'] = True
    
    # 是否高分
    if '高分' in query or '评分高' in query:
        conditions['high_rating_only'] = True
    
    return conditions


def search_spots_with_conditions(conditions: dict, user_id: int, n: int = 15) -> list[dict]:
    """根据条件搜索景点"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 基础查询
    query = """
        SELECT id, name, city, spot_type, target_group, rating, suggest_season, ticket_info
        FROM spots
        WHERE 1=1
    """
    params = []
    
    # 添加条件
    if conditions.get('city'):
        query += " AND city = ?"
        params.append(conditions['city'])
    
    if conditions.get('spot_type'):
        query += " AND spot_type LIKE ?"
        params.append(f"%{conditions['spot_type']}%")
    
    if conditions.get('target_group'):
        query += " AND target_group LIKE ?"
        params.append(f"%{conditions['target_group']}%")
    
    if conditions.get('season'):
        query += " AND (suggest_season = ? OR suggest_season = '四季皆宜')"
        params.append(conditions['season'])
    
    if conditions.get('free_only'):
        query += " AND (ticket_info = 0 OR ticket_info LIKE '%免费%')"
    
    if conditions.get('high_rating_only'):
        query += " AND rating >= 4.0"
    
    query += " ORDER BY rating DESC LIMIT ?"
    params.append(n * 2)  # 多取一些，方便后续排序
    
    cursor.execute(query, params)
    spots = cursor.fetchall()
    
    # 使用画像推荐器计算匹配分
    recommender = UserProfileRecommender(DB_PATH)
    user_profile = recommender._load_user_profile(cursor, user_id)
    behavior_pref = recommender._load_behavior_preferences(cursor, user_id)
    
    results = []
    for spot in spots:
        spot_dict = dict(spot)
        
        # 计算画像匹配分
        spot_info = {
            'name': spot_dict['name'],
            'city': spot_dict['city'],
            'spot_types': recommender._parse_multi_value(spot_dict.get('spot_type', '[]')),
            'target_groups': recommender._parse_multi_value(spot_dict.get('target_group', '[]')),
            'suggest_season': spot_dict.get('suggest_season', '')
        }
        
        match_score = recommender._score(user_profile, behavior_pref, spot_info)
        spot_dict['match_score'] = match_score
        
        # 计算综合得分（搜索相关性 50% + 画像匹配 50%）
        base_score = spot_dict.get('rating', 0) or 0
        spot_dict['total_score'] = 0.5 * (base_score / 5.0) + 0.5 * (match_score / 100.0)
        
        results.append(spot_dict)
    
    conn.close()
    
    # 按综合得分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return results[:n]


def print_recommendation_table(recommendations: list[dict], user_city: str, query: str = ""):
    """打印推荐结果表格"""
    if not recommendations:
        print("\n❌ 未找到符合条件的景点")
        return
    
    print("\n" + "=" * 130)
    if query:
        print(f"🔍 查询：{query}")
    print(f"🎯 推荐结果 Top{len(recommendations)}:")
    print("=" * 130)
    
    # 表头
    print(f"{'序号':<4} {'名字':<40} {'城市':<10} {'类型':<15} {'人群':<10} {'评分':<6} {'匹配分':<8} {'总分':<10} {'门票':<15} {'季节':<12}")
    print("-" * 130)
    
    # 遍历推荐结果
    for i, rec in enumerate(recommendations, 1):
        name = rec.get('name', '未知')[:39]
        city = rec.get('city', '未知')
        
        # 景点类型
        spot_type_raw = rec.get('spot_type', '[]')
        if isinstance(spot_type_raw, str):
            import json
            try:
                spot_types = json.loads(spot_type_raw)
                spot_type = spot_types[0] if spot_types else '未知'
            except:
                spot_type = '未知'
        else:
            spot_type = '未知'
        
        # 适合人群
        target_raw = rec.get('target_group', '[]')
        if isinstance(target_raw, str):
            import json
            try:
                targets = json.loads(target_raw)
                target_group = targets[0] if targets else '大众'
            except:
                target_group = '大众'
        else:
            target_group = '大众'
        
        rating = rec.get('rating', 0)
        if rating:
            rating_str = f"{rating:.1f}"
        else:
            rating_str = "N/A"
        
        match_score = rec.get('match_score', 0)
        total_score = rec.get('total_score', 0)
        
        # 门票
        ticket = rec.get('ticket_info', '未知')
        if ticket and len(str(ticket)) > 14:
            ticket = str(ticket)[:13] + "…"
        
        # 季节
        season = rec.get('suggest_season', '未知')
        
        # 同城标记
        city_mark = "🏠" if city == user_city else ""
        
        print(f"{i:<4} {name:<40} {city:<10} {spot_type:<15} {target_group:<10} {rating_str:<6} {match_score:>6.1f}% {total_score:<10.4f} {str(ticket):<15} {season:<12} {city_mark}")
    
    print("=" * 130)


def print_user_profile(user: dict):
    """打印用户画像信息"""
    print("\n" + "=" * 80)
    print("👤 用户画像信息")
    print("=" * 80)
    print(f"用户名：{user['username']}")
    print(f"昵称：{user.get('nickname', '未设置')}")
    print(f"城市：{user.get('city', '未设置')}")
    print(f"年龄：{user.get('age', '未设置')}")
    print(f"性别：{user.get('gender', '未设置')}")
    print(f"旅行偏好：{user.get('travel_style', '未设置')}")
    print("=" * 80)


def print_score_distribution(recommendations: list[dict]):
    """打印分数分布统计"""
    if not recommendations:
        return
    
    scores = [rec.get('match_score', 0) for rec in recommendations]
    
    print("\n📊 匹配分分布统计:")
    print(f"   平均匹配分：{sum(scores)/len(scores):.1f}%")
    print(f"   最高分：{max(scores):.1f}%")
    print(f"   最低分：{min(scores):.1f}%")
    
    # 分数段统计
    ranges = [
        (60, 100, "高分景点 (60%+)", "🟢"),
        (40, 60, "中等景点 (40-60%)", "🟡"),
        (0, 40, "低分景点 (<40%)", "🔴")
    ]
    
    for low, high, label, icon in ranges:
        count = sum(1 for s in scores if low <= s < high)
        percentage = count / len(scores) * 100
        print(f"   {icon} {label}: {count} 个 ({percentage:.1f}%)")


def print_reason_analysis(recommendations: list[dict], conditions: dict):
    """打印推荐原因分析"""
    print("\n💡 推荐原因分析:")
    
    # 搜索条件分析
    print("   📍 搜索条件:")
    if conditions.get('city'):
        print(f"      • 城市：{conditions['city']}")
    if conditions.get('spot_type'):
        print(f"      • 类型：{conditions['spot_type']}")
    if conditions.get('target_group'):
        print(f"      • 人群：{conditions['target_group']}")
    if conditions.get('season'):
        print(f"      • 季节：{conditions['season']}")
    if conditions.get('free_only'):
        print(f"      • 免费景点")
    if conditions.get('high_rating_only'):
        print(f"      • 高分景点（4.0+）")
    
    # 画像匹配分析
    user_match_count = sum(1 for rec in recommendations if rec.get('match_score', 0) >= 50)
    print(f"\n   🎯 画像匹配：{user_match_count}/{len(recommendations)} 个景点匹配度≥50%")


def main():
    """主流程 - 交互式"""
    print("\n" + "=" * 80)
    print("  景点推荐系统 - 交互式查询工具")
    print("=" * 80)
    
    # ========== 配置区域：在这里修改账号密码 ==========
    # 提示：可以查看数据库 data/travel.db 中的 users 表找到真实用户
    # 或者使用下面的测试账号：
    print("\n📝 默认使用测试账号登录，如需修改请编辑脚本第 178-179 行")
    USERNAME = "test_admin"  # 用户名
    PASSWORD = "123456"        # 密码
    # ================================================
    
    # 验证用户
    print(f"\n⏳ 正在验证用户：{USERNAME}...")
    user = authenticate_user(USERNAME, PASSWORD)
    
    if not user:
        print("❌ 用户名或密码错误！")
        return
    
    print(f"✅ 登录成功！欢迎 {user.get('nickname', user['username'])}")
    
    # 打印用户画像
    print_user_profile(user)
    
    # 交互式查询
    print("\n" + "=" * 80)
    print("💬 请输入你的需求（例如：'推荐北京周边适合亲子游的高分免费景点，四季皆宜'）")
    print("   输入 'quit' 或 'exit' 退出程序")
    print("=" * 80)
    
    while True:
        try:
            # 获取用户输入
            query = input("\n🔍 你的需求：").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 感谢使用，再见！")
                break
            
            # 解析查询条件
            print("\n⏳ 正在分析需求...")
            conditions = parse_user_query(query)
            
            # 搜索景点
            print("⏳ 正在搜索景点并计算匹配分...")
            recommendations = search_spots_with_conditions(conditions, user['id'], n=15)
            
            # 打印推荐表格
            print_recommendation_table(recommendations, user.get('city', ''), query)
            
            # 打印分数分布
            print_score_distribution(recommendations)
            
            # 打印推荐原因
            print_reason_analysis(recommendations, conditions)
            
            # 同城景点统计
            user_city = user.get('city', '')
            if user_city:
                same_city_count = sum(1 for rec in recommendations if rec.get('city') == user_city)
                print(f"\n🏠 同城景点：{same_city_count}/{len(recommendations)} ({same_city_count/len(recommendations)*100:.1f}%)")
            
            print("\n✅ 查询完成")
            
        except KeyboardInterrupt:
            print("\n\n👋 已退出程序")
            break
        except Exception as e:
            print(f"\n❌ 发生错误：{e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已退出程序")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
