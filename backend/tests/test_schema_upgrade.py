"""
Task 1: 数据库 schema 升级测试（TDD-RED/GREEN）

只覆盖本任务要求：
1) users 表包含 phone/bio/avatar_url/birthday
2) 存在 user_profiles 与 recommend_feedback 表
3) 存在 idx_feedback_user/idx_feedback_spot/idx_feedback_event 三个索引
4) 旧库 users 缺列场景可被 init_db_sync 自动补齐（ALTER 迁移保护）
5) 异步初始化路径也能完成升级（避免不安全内部连接用法）
"""

import asyncio
from pathlib import Path
import sqlite3
import sys


# 让测试可以直接导入 backend 目录下的 database.py / config.py
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database  # noqa: E402


REQUIRED_USER_COLUMNS = {"phone", "bio", "avatar_url", "birthday"}
REQUIRED_FEEDBACK_INDEXES = {
    "idx_feedback_user",
    "idx_feedback_spot",
    "idx_feedback_event",
}


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """获取指定表的字段名集合。"""
    rows = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    return {row[1] for row in rows}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """判断表是否存在。"""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    ).fetchone()
    return row is not None


def _index_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """获取某张表上已存在的索引名。"""
    rows = conn.execute(f"PRAGMA index_list({table_name});").fetchall()
    return {row[1] for row in rows}


def test_init_db_sync_should_upgrade_task1_schema(tmp_path):
    """调用 init_db_sync 后，Task1 目标表结构与索引必须存在。"""
    test_db_path = tmp_path / "task1_schema_upgrade.db"

    # 指向临时数据库，避免污染真实数据，并在测试后恢复全局 DB_PATH
    original_db_path = database.DB_PATH
    try:
        database.DB_PATH = str(test_db_path)
        database.init_db_sync()

        conn = sqlite3.connect(test_db_path)
        try:
            users_columns = _table_columns(conn, "users")
            assert REQUIRED_USER_COLUMNS.issubset(users_columns)

            assert _table_exists(conn, "user_profiles")
            assert _table_exists(conn, "recommend_feedback")

            feedback_indexes = _index_names(conn, "recommend_feedback")
            assert REQUIRED_FEEDBACK_INDEXES.issubset(feedback_indexes)
        finally:
            conn.close()
    finally:
        database.DB_PATH = original_db_path


def test_init_db_sync_should_migrate_legacy_users_columns(tmp_path):
    """旧库 users 缺少新列时，init_db_sync 必须通过 ALTER 自动补齐。"""
    test_db_path = tmp_path / "legacy_schema.db"

    # 手工创建一个旧版 users 表（不含 Task1 新增四列）
    conn = sqlite3.connect(test_db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                nickname      TEXT,
                age           INTEGER,
                gender        TEXT,
                city          TEXT,
                travel_style  TEXT,
                accessibility TEXT    DEFAULT 'normal',
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    original_db_path = database.DB_PATH
    try:
        database.DB_PATH = str(test_db_path)
        database.init_db_sync()

        conn = sqlite3.connect(test_db_path)
        try:
            users_columns = _table_columns(conn, "users")
            assert REQUIRED_USER_COLUMNS.issubset(users_columns)
        finally:
            conn.close()
    finally:
        database.DB_PATH = original_db_path


def test_init_db_async_should_upgrade_task1_schema(tmp_path):
    """异步初始化也必须完成 Task1 升级，避免内部连接不安全操作。"""
    test_db_path = tmp_path / "task1_schema_upgrade_async.db"

    original_db_path = database.DB_PATH
    try:
        database.DB_PATH = str(test_db_path)
        asyncio.run(database.init_db_async())

        conn = sqlite3.connect(test_db_path)
        try:
            users_columns = _table_columns(conn, "users")
            assert REQUIRED_USER_COLUMNS.issubset(users_columns)

            assert _table_exists(conn, "user_profiles")
            assert _table_exists(conn, "recommend_feedback")

            feedback_indexes = _index_names(conn, "recommend_feedback")
            assert REQUIRED_FEEDBACK_INDEXES.issubset(feedback_indexes)
        finally:
            conn.close()
    finally:
        database.DB_PATH = original_db_path


def test_init_db_async_should_migrate_legacy_users_columns(tmp_path):
    """旧库 users 缺少新列时，init_db_async 也必须通过 ALTER 自动补齐。"""
    test_db_path = tmp_path / "legacy_schema_async.db"

    # 手工创建一个旧版 users 表（不含 Task1 新增四列）
    conn = sqlite3.connect(test_db_path)
    try:
        conn.execute(
            """
            CREATE TABLE users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                nickname      TEXT,
                age           INTEGER,
                gender        TEXT,
                city          TEXT,
                travel_style  TEXT,
                accessibility TEXT    DEFAULT 'normal',
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    original_db_path = database.DB_PATH
    try:
        database.DB_PATH = str(test_db_path)
        asyncio.run(database.init_db_async())

        conn = sqlite3.connect(test_db_path)
        try:
            users_columns = _table_columns(conn, "users")
            assert REQUIRED_USER_COLUMNS.issubset(users_columns)
        finally:
            conn.close()
    finally:
        database.DB_PATH = original_db_path
