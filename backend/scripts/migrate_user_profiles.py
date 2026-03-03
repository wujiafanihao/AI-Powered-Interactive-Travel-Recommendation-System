"""
数据库迁移脚本：为所有已有用户创建 user_profiles 记录

大白话说明：
    这个脚本会检查 users 表中的所有用户，
    如果某个用户在 user_profiles 表中没有记录，
    就为他创建一条空记录。
    
    这样可以确保推荐算法能正确读取用户画像数据。

使用方法：
    python backend/scripts/migrate_user_profiles.py
"""

import sqlite3
import os
from datetime import datetime

# 获取数据库路径（相对于脚本所在目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(BACKEND_DIR, "data", "travel.db")


def migrate_user_profiles():
    """为所有没有 user_profiles 记录的用户创建记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 查询所有没有 user_profiles 记录的用户
    cursor.execute("""
        SELECT u.id, u.username, u.city, u.travel_style
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id = u.id
        WHERE up.user_id IS NULL
    """)
    users_without_profile = cursor.fetchall()
    
    if not users_without_profile:
        print("✅ 所有用户都已经有 user_profiles 记录")
        conn.close()
        return
    
    print(f"发现 {len(users_without_profile)} 个用户没有 user_profiles 记录")
    print("开始创建记录...\n")
    
    created_count = 0
    for user_id, username, city, travel_style in users_without_profile:
        try:
            cursor.execute("""
                INSERT INTO user_profiles (user_id, updated_at)
                VALUES (?, ?)
            """, (user_id, datetime.now().isoformat()))
            created_count += 1
            print(f"✅ 用户 {username}(ID:{user_id}) - 城市：{city or '未设置'}")
        except Exception as e:
            print(f"❌ 用户 {username}(ID:{user_id}) 创建失败：{e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n迁移完成！共创建 {created_count}/{len(users_without_profile)} 条记录")


if __name__ == "__main__":
    migrate_user_profiles()
