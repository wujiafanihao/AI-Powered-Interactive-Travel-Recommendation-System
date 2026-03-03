"""
用户画像匹配评分分析脚本

大白话说明：
    这个脚本用于分析数据库中所有用户的画像匹配评分指标，
    帮助了解推荐算法对不同用户的匹配情况。
"""

import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from algorithms.user_profile_recommender import UserProfileRecommender
from database import DB_PATH


def analyze_user_scores():
    """分析所有用户的画像匹配评分"""
    print("=" * 80)
    print("用户画像匹配评分分析报告")
    print("=" * 80)
    
    # 初始化推荐器
    recommender = UserProfileRecommender(DB_PATH)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有用户
    cursor.execute("""
        SELECT id, username, city, travel_style
        FROM users
        ORDER BY id
    """)
    users = cursor.fetchall()
    
    print(f"\n📊 共有 {len(users)} 个用户\n")
    
    # 统计信息
    total_users = 0
    users_with_high_scores = 0  # 有 60%+ 匹配景点的用户数
    users_with_medium_scores = 0  # 有 40-60% 匹配景点的用户数
    users_with_low_scores = 0  # 只有 40% 以下匹配景点的用户数
    
    all_scores = []  # 所有用户的所有景点匹配分
    
    # 遍历每个用户
    for user in users:
        user_id = user["id"]
        username = user["username"]
        city = user["city"] or "未知"
        travel_style = user["travel_style"] or "未设置"
        
        try:
            # 获取该用户的推荐景点（前 100 个）
            recommendations = recommender.recommend(user_id, n=100)
            
            if not recommendations:
                print(f"⚠️  用户 {username} (ID: {user_id}) 没有推荐景点")
                continue
            
            total_users += 1
            
            # 统计该用户的匹配分分布
            scores = [rec["score"] for rec in recommendations]
            all_scores.extend(scores)
            
            max_score = max(scores)
            min_score = min(scores)
            avg_score = sum(scores) / len(scores)
            
            # 统计不同分数段的景点数量
            high_count = sum(1 for s in scores if s >= 60)  # 60%+
            medium_count = sum(1 for s in scores if 40 <= s < 60)  # 40-60%
            low_count = sum(1 for s in scores if s < 40)  # 40% 以下
            
            if high_count > 0:
                users_with_high_scores += 1
            elif medium_count > 0:
                users_with_medium_scores += 1
            else:
                users_with_low_scores += 1
            
            # 打印用户详情
            print(f"👤 用户：{username} (ID: {user_id})")
            print(f"   城市：{city}")
            print(f"   旅行偏好：{travel_style}")
            print(f"   推荐景点数：{len(recommendations)}")
            print(f"   匹配分范围：{min_score}% - {max_score}%")
            print(f"   平均匹配分：{avg_score:.1f}%")
            print(f"   高分景点 (60%+): {high_count} 个")
            print(f"   中等景点 (40-60%): {medium_count} 个")
            print(f"   低分景点 (<40%): {low_count} 个")
            
            # 显示前 5 个推荐景点
            if recommendations:
                print(f"   前 5 个推荐景点:")
                for i, rec in enumerate(recommendations[:5], 1):
                    spot_id = rec["spot_id"]
                    
                    # 获取景点名称和城市
                    cursor.execute("SELECT name, city FROM spots WHERE id = ?", (spot_id,))
                    spot_row = cursor.fetchone()
                    if spot_row:
                        spot_name = spot_row["name"]
                        spot_city = spot_row["city"]
                        print(f"      {i}. {spot_name} ({spot_city}) - {rec['score']}%")
            
            print()
            
        except Exception as e:
            print(f"❌ 用户 {username} (ID: {user_id}) 分析失败：{e}")
            print()
    
    # 总体统计
    print("=" * 80)
    print("📈 总体统计")
    print("=" * 80)
    print(f"总用户数：{total_users}")
    print(f"有高分景点的用户：{users_with_high_scores} ({users_with_high_scores/total_users*100:.1f}%)")
    print(f"只有中等景点的用户：{users_with_medium_scores} ({users_with_medium_scores/total_users*100:.1f}%)")
    print(f"只有低分景点的用户：{users_with_low_scores} ({users_with_low_scores/total_users*100:.1f}%)")
    
    if all_scores:
        print(f"\n所有景点匹配分统计:")
        print(f"   平均分：{sum(all_scores)/len(all_scores):.1f}%")
        print(f"   最高分：{max(all_scores)}%")
        print(f"   最低分：{min(all_scores)}%")
        
        # 分数段分布
        score_ranges = [
            (90, 100, "90-100% (极高匹配)"),
            (70, 90, "70-90% (高匹配)"),
            (50, 70, "50-70% (中等匹配)"),
            (30, 50, "30-50% (低匹配)"),
            (0, 30, "0-30% (极低匹配)")
        ]
        
        print(f"\n匹配分分布:")
        for low, high, label in score_ranges:
            count = sum(1 for s in all_scores if low <= s < high)
            percentage = count / len(all_scores) * 100
            print(f"   {label}: {count} 个 ({percentage:.1f}%)")
    
    conn.close()
    print("\n✅ 分析完成")


if __name__ == "__main__":
    analyze_user_scores()
