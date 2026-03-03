"""
TravelAI 数据库初始化模块

大白话说明：
    这个文件负责两件事：
    1. 创建 SQLite 数据库和所有需要的表（如果还没创建的话）
    2. 提供一个"获取数据库连接"的函数，供其他模块调用

    数据库一共有 7 张表：
    - users: 存用户信息（用户名、密码、年龄、性别、旅行偏好等）
    - spots: 存景点信息（名称、城市、地址、介绍、评分等）
    - user_behaviors: 存用户行为记录（谁浏览了哪个景点、打了几分等）
    - user_collections: 存用户收藏（谁收藏了哪个景点）
    - user_similarity: 存用户之间的相似度（协同过滤算法用的）
    - spot_features: 存景点的特征向量（内容推荐算法用的）
    - chat_history: 存 AI 对话记录
"""

import os
import sqlite3
import aiosqlite
from config import get_settings

# 拿到全局配置
settings = get_settings()

# 计算数据库文件的绝对路径
# __file__ 是当前文件的路径，往上找到 backend 目录，再拼上 data/travel.db
DB_PATH = os.path.join(os.path.dirname(__file__), settings.DATABASE_PATH)


# ============================================
# 建表 SQL 语句（共 7 张表）
# ============================================

# 所有建表语句放在一个列表里，方便一次性执行
CREATE_TABLES_SQL = [
    # -------------------- 表1: 用户表 --------------------
    # 存储每个用户的基本信息和偏好设置
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT    NOT NULL UNIQUE,
        password_hash   TEXT    NOT NULL,
        nickname        TEXT,
        age             INTEGER,
        gender          TEXT    CHECK(gender IN ('男','女','未知')),
        city            TEXT,
        travel_style    TEXT,
        accessibility   TEXT    DEFAULT 'normal',
        phone           TEXT,
        bio             TEXT,
        avatar_url      TEXT,
        birthday        TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # -------------------- 表2: 景点表 --------------------
    # 存储从 citydata CSV 导入的所有景点数据
    """
    CREATE TABLE IF NOT EXISTS spots (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        city            TEXT    NOT NULL,
        address         TEXT,
        description     TEXT,
        open_time       TEXT,
        image_url       TEXT,
        rating          REAL,
        suggest_time    TEXT,
        suggest_season  TEXT,
        ticket_info     TEXT,
        tips            TEXT,
        spot_type       TEXT,
        target_group    TEXT,
        source_url      TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # -------------------- 表3: 用户行为记录表 --------------------
    # 记录用户的每一次行为（浏览、评分、收藏、搜索）
    """
    CREATE TABLE IF NOT EXISTS user_behaviors (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        spot_id         INTEGER NOT NULL,
        behavior_type   TEXT    NOT NULL,
        rating          REAL,
        search_query    TEXT,
        duration        INTEGER,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES spots(id)
    );
    """,

    # -------------------- 表4: 用户收藏表 --------------------
    # 用户收藏的景点，一个用户对同一景点只能收藏一次
    """
    CREATE TABLE IF NOT EXISTS user_collections (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        spot_id         INTEGER NOT NULL,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES spots(id),
        UNIQUE(user_id, spot_id)
    );
    """,

    # -------------------- 表5: 用户相似度矩阵表 --------------------
    # 存储任意两个用户之间的相似度得分（协同过滤算法预计算的结果）
    """
    CREATE TABLE IF NOT EXISTS user_similarity (
        user_id_a       INTEGER NOT NULL,
        user_id_b       INTEGER NOT NULL,
        similarity      REAL    NOT NULL,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id_a, user_id_b),
        FOREIGN KEY (user_id_a) REFERENCES users(id),
        FOREIGN KEY (user_id_b) REFERENCES users(id)
    );
    """,

    # -------------------- 表6: 景点特征向量表 --------------------
    # 存储每个景点提取出的特征向量（内容推荐算法用的）
    """
    CREATE TABLE IF NOT EXISTS spot_features (
        spot_id         INTEGER PRIMARY KEY,
        feature_vector  TEXT    NOT NULL,
        feature_labels  TEXT    NOT NULL,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (spot_id) REFERENCES spots(id)
    );
    """,

    # -------------------- 表7: AI 对话历史表 --------------------
    # 存储用户和 AI 助手的聊天记录
    """
    CREATE TABLE IF NOT EXISTS chat_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        role            TEXT    NOT NULL CHECK(role IN ('user','assistant','system')),
        content         TEXT    NOT NULL,
        session_id      TEXT    NOT NULL,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,

    # -------------------- 表8: 用户评论表 --------------------
    # 存储用户对景点的评论
    """
    CREATE TABLE IF NOT EXISTS spot_comments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        spot_id         INTEGER NOT NULL,
        rating          REAL    NOT NULL CHECK(rating >= 1 AND rating <= 5),
        content         TEXT    NOT NULL,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES spots(id)
    );
    """,

    # -------------------- 表9: 用户扩展画像表 --------------------
    # 存储用户长期画像和偏好信息（和 users 基础信息分离）
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id             INTEGER PRIMARY KEY,
        preferred_budget    TEXT,
        preferred_distance  TEXT,
        preferred_season    TEXT,
        interest_tags       TEXT,
        updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """,

    # -------------------- 表10: 推荐反馈事件表 --------------------
    # 存储推荐曝光、点击、跳过、转化等事件，供推荐系统学习
    """
    CREATE TABLE IF NOT EXISTS recommend_feedback (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        spot_id         INTEGER NOT NULL,
        event_type      TEXT    NOT NULL,
        event_value     REAL,
        context         TEXT,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (spot_id) REFERENCES spots(id)
    );
    """,
]

# 索引语句单独放，因为索引是用来加速查询的，和建表是两件事
CREATE_INDEXES_SQL = [
    # 按城市查景点会很快
    "CREATE INDEX IF NOT EXISTS idx_spots_city ON spots(city);",
    # 按评分排序会很快
    "CREATE INDEX IF NOT EXISTS idx_spots_rating ON spots(rating);",
    # 按景点类型筛选会很快
    "CREATE INDEX IF NOT EXISTS idx_spots_type ON spots(spot_type);",
    # 查某个用户的所有行为会很快
    "CREATE INDEX IF NOT EXISTS idx_behaviors_user ON user_behaviors(user_id);",
    # 查某个景点被多少人看过会很快
    "CREATE INDEX IF NOT EXISTS idx_behaviors_spot ON user_behaviors(spot_id);",
    # 按行为类型筛选会很快
    "CREATE INDEX IF NOT EXISTS idx_behaviors_type ON user_behaviors(behavior_type);",
    # 查某个用户的聊天记录会很快
    "CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);",
    # 按会话ID查聊天记录会很快
    "CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_history(session_id);",
    # 查某个景点的评论会很快
    "CREATE INDEX IF NOT EXISTS idx_comments_spot ON spot_comments(spot_id);",
    # 查某个用户的评论会很快
    "CREATE INDEX IF NOT EXISTS idx_comments_user ON spot_comments(user_id);",
    # 推荐反馈按用户查询会很快
    "CREATE INDEX IF NOT EXISTS idx_feedback_user ON recommend_feedback(user_id);",
    # 推荐反馈按景点查询会很快
    "CREATE INDEX IF NOT EXISTS idx_feedback_spot ON recommend_feedback(spot_id);",
    # 推荐反馈按事件类型查询会很快
    "CREATE INDEX IF NOT EXISTS idx_feedback_event ON recommend_feedback(event_type);",
]


def ensure_schema_upgrades(conn: sqlite3.Connection):
    """
    旧库升级保护：确保 users 表补齐新字段。

    大白话说明：
        老数据库如果是在新增字段之前创建的，users 表里会缺列。
        这里通过 PRAGMA table_info 拿到现有列，再按需执行 ALTER TABLE ADD COLUMN。
    """
    cursor = conn.cursor()

    existing_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(users);").fetchall()
    }

    required_columns = {
        "phone": "ALTER TABLE users ADD COLUMN phone TEXT;",
        "bio": "ALTER TABLE users ADD COLUMN bio TEXT;",
        "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url TEXT;",
        "birthday": "ALTER TABLE users ADD COLUMN birthday TEXT;",
    }

    for column_name, alter_sql in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(alter_sql)


def init_db_sync():
    """
    同步方式初始化数据库（用于脚本场景）

    大白话说明：
        这个函数会：
        1. 确保 data 目录存在（不存在就创建）
        2. 创建 SQLite 数据库文件
        3. 执行所有建表和建索引的 SQL 语句
        用于命令行脚本（如导入数据、生成用户等）
    """
    # 确保存放数据库文件的目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    # 连接数据库（如果文件不存在，sqlite3 会自动创建）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 开启外键约束（SQLite 默认不开启外键检查，需要手动开）
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 挨个执行建表语句
    for sql in CREATE_TABLES_SQL:
        cursor.execute(sql)

    # 挨个执行建索引语句
    for sql in CREATE_INDEXES_SQL:
        cursor.execute(sql)

    # 老库补丁：补齐 users 新字段
    ensure_schema_upgrades(conn)

    # 提交并关闭
    conn.commit()
    conn.close()

    print(f"✅ 数据库初始化完成: {DB_PATH}")


async def init_db_async():
    """
    异步方式初始化数据库（用于 FastAPI 启动时）

    大白话说明：
        和上面的同步版本功能一样，区别是用了 aiosqlite（异步库），
        不会阻塞 FastAPI 的事件循环。
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        for sql in CREATE_TABLES_SQL:
            await db.execute(sql)

        for sql in CREATE_INDEXES_SQL:
            await db.execute(sql)

        # 老库补丁：补齐 users 新字段（异步版本）
        cursor = await db.execute("PRAGMA table_info(users);")
        rows = await cursor.fetchall()
        existing_columns = {
            row[1] for row in rows
        }

        required_columns = {
            "phone": "ALTER TABLE users ADD COLUMN phone TEXT;",
            "bio": "ALTER TABLE users ADD COLUMN bio TEXT;",
            "avatar_url": "ALTER TABLE users ADD COLUMN avatar_url TEXT;",
            "birthday": "ALTER TABLE users ADD COLUMN birthday TEXT;",
        }

        for column_name, alter_sql in required_columns.items():
            if column_name not in existing_columns:
                await db.execute(alter_sql)

        await db.commit()

    print(f"✅ 数据库初始化完成: {DB_PATH}")


async def get_db():
    """
    获取数据库连接（FastAPI 依赖注入用）

    大白话说明：
        这是一个"生成器"函数，FastAPI 会自动管理连接的生命周期：
        - 请求开始 → 打开连接
        - 请求结束 → 自动关闭连接
        这样就不用担心忘了关连接导致数据库被锁住。

    使用方式：
        @app.get("/xxx")
        async def some_api(db = Depends(get_db)):
            await db.execute("SELECT ...")
    """
    db = await aiosqlite.connect(DB_PATH)
    # 让查询结果返回字典格式（可以用列名访问），而不是元组
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


# ============================================
# 如果直接运行这个文件，就执行数据库初始化
# ============================================
if __name__ == "__main__":
    init_db_sync()
