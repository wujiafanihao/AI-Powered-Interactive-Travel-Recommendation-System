import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "data/travel.db"

POSITIVE_COMMENTS = [
    "景色非常美，强烈推荐！",
    "带孩子来的，孩子玩得很开心",
    "环境很好，设施完善",
    "值得一去，拍照很出片",
    "服务态度很好，门票性价比高",
    "风景如画，不虚此行",
    "历史文化底蕴深厚，长知识了",
    "空气清新，适合周末出游",
    "交通便利，停车方便",
    "体验感很棒，还会再来",
    "适合家庭出游，推荐指数满分",
    "超出预期的好地方",
    "休闲放松的好去处",
    "景点很有特色，值得参观",
    "导游讲解很专业，学到很多",
]

NEUTRAL_COMMENTS = [
    "还行吧，一般般",
    "可以来看看，但没必要专门来",
    "感觉一般，没有想象中好",
    "中规中矩",
    "门票有点贵",
    "人太多了，体验一般",
    "还不错，就是地方有点小",
    "还行，适合拍照",
    "值得参观，但不建议旺季来",
    "可以消磨时间",
]

NEGATIVE_COMMENTS = [
    "有点失望，不推荐",
    "门票不值这个价",
    "人山人海，挤死了",
    "设施老旧，管理混乱",
    "体验很差，不会再来",
    "宣传过度，实际一般",
    "服务态度太差了",
    "停车太难了",
    "完全不值得",
    "后悔来这个地方",
]

USER_PRAISE = [
    "宝宝玩得超开心",
    "小朋友特别喜欢",
    "孩子学到了很多知识",
    "适合亲子游",
    "孩子的天堂",
    "小朋友不想走",
    "全家都玩得很高兴",
    "带孩子来准没错",
    "儿童设施很完善",
    "孩子增长了不少见识",
]

def generate_comment(rating):
    if rating is None:
        rating = 4.0
    
    if rating >= 4.5:
        templates = POSITIVE_COMMENTS + USER_PRAISE
    elif rating >= 3.5:
        templates = POSITIVE_COMMENTS
    elif rating >= 2.5:
        templates = NEUTRAL_COMMENTS
    else:
        templates = NEGATIVE_COMMENTS + NEUTRAL_COMMENTS
    
    base = random.choice(templates)
    
    extras = [
        "强烈推荐！",
        "大家快来呀！",
        "真的很不错！",
        "不容错过！",
        "太棒了！",
        "超赞！",
        "必须要来！",
        "良心推荐！",
        "真的爱了！",
        "绝绝子！",
    ]
    
    if random.random() > 0.5:
        return base + random.choice(extras)
    return base

def generate_rating_based_on_spot(spot_rating):
    """根据景点评分生成用户评论评分"""
    if spot_rating is None:
        spot_rating = 4.0
    
    if spot_rating >= 4.5:
        return round(random.uniform(3.5, 5.0), 1)
    elif spot_rating >= 4.0:
        return round(random.uniform(3.0, 5.0), 1)
    elif spot_rating >= 3.5:
        return round(random.uniform(2.5, 4.5), 1)
    elif spot_rating >= 3.0:
        return round(random.uniform(2.0, 4.0), 1)
    else:
        return round(random.uniform(1.5, 3.5), 1)

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM spots")
    spot_count = cursor.fetchone()[0]
    print(f"数据库共有 {spot_count} 个景点")
    
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    print(f"数据库共有 {len(user_ids)} 个用户")
    
    cursor.execute("SELECT COUNT(*) FROM spot_comments")
    existing = cursor.fetchone()[0]
    if existing > 0:
        print(f"已有 {existing} 条评论")
        response = input("是否继续生成新评论？(y/n): ")
        if response.lower() != 'y':
            print("取消操作")
            conn.close()
            return
    
    cursor.execute("SELECT id, rating FROM spots")
    spots = cursor.fetchall()
    
    comments_to_insert = []
    
    for spot_id, spot_rating in spots:
        num_comments = random.randint(3, 10)
        
        for _ in range(num_comments):
            user_id = random.choice(user_ids)
            
            rating = generate_rating_based_on_spot(spot_rating)
            
            content = generate_comment(rating)
            
            days_ago = random.randint(0, 365)
            created_at = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
            
            comments_to_insert.append((
                user_id, spot_id, rating, content, created_at, created_at
            ))
    
    cursor.executemany("""
        INSERT INTO spot_comments (user_id, spot_id, rating, content, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, comments_to_insert)
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM spot_comments")
    total = cursor.fetchone()[0]
    
    print(f"\n✅ 成功生成 {len(comments_to_insert)} 条评论")
    print(f"📊 数据库共有 {total} 条评论")
    
    cursor.execute("""
        SELECT s.name, s.rating, COUNT(c.id) as comment_count, AVG(c.rating) as avg_rating
        FROM spots s
        LEFT JOIN spot_comments c ON s.id = c.spot_id
        GROUP BY s.id
        ORDER BY comment_count DESC
        LIMIT 10
    """)
    print("\n📍 评论最多的景点 TOP 10:")
    print(f"{'景点名称':<30} {'景点评分':>8} {'评论数':>6} {'平均评论评分':>12}")
    print("-" * 60)
    for row in cursor.fetchall():
        name = row[0] or "未知景点"
        spot_rating = row[1] or 0.0
        comment_count = row[2] or 0
        avg_rating = row[3] or 0.0
        print(f"{name[:28]:<30} {spot_rating:>8.1f} {comment_count:>6} {avg_rating:>12.1f}")
    
    conn.close()

if __name__ == "__main__":
    main()
