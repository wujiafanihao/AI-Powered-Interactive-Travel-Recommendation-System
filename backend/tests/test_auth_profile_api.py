"""
Task 2: 资料模型与头像上传接口测试（TDD）

本测试文件只覆盖 Task 2 后端目标：
1) PUT /api/auth/me 对非法 phone 返回 422
2) POST /api/auth/avatar 对超 5MB 文件返回 400
"""

from pathlib import Path
import sys
import uuid

import pytest
from fastapi.testclient import TestClient


# 让测试可以直接导入 backend 目录下的模块
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import database  # noqa: E402
import main  # noqa: E402
from routers import auth as auth_router  # noqa: E402


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """把数据库路径切到临时文件，避免污染真实数据。"""
    test_db = tmp_path / "task2_auth_profile.db"

    monkeypatch.setattr(database, "DB_PATH", str(test_db))
    monkeypatch.setattr(auth_router, "DB_PATH", str(test_db))

    return test_db


@pytest.fixture
def client(isolated_db):
    """创建测试客户端。"""
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def token(client):
    """先注册一个用户，拿到登录 token。"""
    username = f"task2_user_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "12345678",
            "nickname": "测试用户",
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_update_me_rejects_invalid_phone(client, token):
    """非法手机号应在模型校验阶段被拒绝（422）。"""
    resp = client.put(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "abc-not-phone"},
    )
    assert resp.status_code == 422


def test_upload_avatar_rejects_large_file(client, token):
    """头像超过 5MB 时应返回 400。"""
    big_content = b"x" * (5 * 1024 * 1024 + 1)

    resp = client.post(
        "/api/auth/avatar",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("avatar.png", big_content, "image/png")},
    )
    assert resp.status_code == 400
