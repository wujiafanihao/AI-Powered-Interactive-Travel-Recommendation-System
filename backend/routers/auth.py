"""
用户认证路由 - 注册、登录、获取个人信息

大白话说明：
    这个文件处理所有和用户认证相关的API接口：
    - POST /auth/register → 注册新用户
    - POST /auth/login → 登录获取Token
    - GET /auth/me → 获取当前登录用户信息
    - PUT /auth/me → 修改个人信息
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from jose import JWTError, jwt
import bcrypt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.user import UserRegister, UserLogin, UserUpdate, UserResponse, TokenResponse
from config import get_settings
from database import DB_PATH

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["用户认证"])

# 头像上传目录：backend/uploads/avatars
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "avatars")
MAX_AVATAR_SIZE = 5 * 1024 * 1024
ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png"}


def hash_password(password: str) -> str:
    """用 bcrypt 加密密码"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Bearer Token 认证方案
security = HTTPBearer()


def create_token(user_id: int, username: str) -> str:
    """
    创建JWT Token

    大白话：把用户ID和过期时间打包加密成一个字符串，
    前端拿着这个字符串就能证明"我是某某用户"
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    从Token中解析出当前用户

    大白话：验证前端传来的Token是否合法，如果合法就返回用户信息
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token无效或已过期，请重新登录")

    # 从数据库查用户
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")

    return dict(row)


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(data: UserRegister):
    """
    注册新用户

    大白话：
    1. 检查用户名是否已被使用
    2. 把密码加密存起来
    3. 返回Token（注册完直接就登录了）
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查用户名是否已存在
    cursor.execute("SELECT id FROM users WHERE username = ?", (data.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="用户名已存在，换一个吧")

    # 加密密码
    password_hash = hash_password(data.password)

    # 处理旅行风格偏好
    travel_style_json = json.dumps(data.travel_style or [], ensure_ascii=False)

    # 插入用户
    cursor.execute("""
        INSERT INTO users (username, password_hash, nickname, age, gender, city, travel_style)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data.username, password_hash, data.nickname, data.age,
          data.gender, data.city, travel_style_json))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    # 生成Token
    token = create_token(user_id, data.username)

    # 解析旅行风格
    travel_style = data.travel_style or []

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            username=data.username,
            nickname=data.nickname,
            age=data.age,
            gender=data.gender,
            city=data.city,
            travel_style=travel_style,
        )
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(data: UserLogin):
    """
    用户登录

    大白话：验证用户名密码，正确的话返回Token
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (data.username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user = dict(row)
    token = create_token(user["id"], user["username"])

    # 解析旅行风格
    try:
        travel_style = json.loads(user.get("travel_style") or "[]")
    except json.JSONDecodeError:
        travel_style = []

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            nickname=user.get("nickname"),
            age=user.get("age"),
            gender=user.get("gender"),
            city=user.get("city"),
            travel_style=travel_style,
            accessibility=user.get("accessibility", "normal"),
            phone=user.get("phone"),
            bio=user.get("bio"),
            birthday=user.get("birthday"),
            avatar_url=user.get("avatar_url"),
        )
    )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    try:
        travel_style = json.loads(current_user.get("travel_style") or "[]")
    except json.JSONDecodeError:
        travel_style = []

    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        nickname=current_user.get("nickname"),
        age=current_user.get("age"),
        gender=current_user.get("gender"),
        city=current_user.get("city"),
        travel_style=travel_style,
        accessibility=current_user.get("accessibility", "normal"),
        phone=current_user.get("phone"),
        bio=current_user.get("bio"),
        birthday=current_user.get("birthday"),
        avatar_url=current_user.get("avatar_url"),
        created_at=current_user.get("created_at"),
    )


@router.get("/me/profile-status", summary="检查用户资料完善状态")
async def get_profile_status(current_user: dict = Depends(get_current_user)):
    """
    检查用户资料是否完善
    
    大白话：
    判断用户是否填写了关键信息（城市、旅行偏好等），
    用于前端决定是否弹窗引导用户完善资料
    """
    travel_style = current_user.get("travel_style")
    try:
        travel_style_list = json.loads(travel_style or "[]")
    except json.JSONDecodeError:
        travel_style_list = []
    
    # 判断是否完善了关键信息
    is_complete = bool(
        current_user.get("city") and 
        (travel_style_list and len(travel_style_list) > 0)
    )
    
    # 判断是否首次登录（通过是否有行为记录判断）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM user_behaviors WHERE user_id = ?",
        (current_user["id"],)
    )
    behavior_count = cursor.fetchone()[0]
    conn.close()
    
    is_first_login = behavior_count == 0
    
    return {
        "is_complete": is_complete,
        "is_first_login": is_first_login,
        "has_city": bool(current_user.get("city")),
        "has_travel_style": bool(travel_style_list and len(travel_style_list) > 0),
        "behavior_count": behavior_count,
    }


@router.put("/me", response_model=UserResponse, summary="修改个人信息")
async def update_me(data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """修改当前用户的个人信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 动态构建 UPDATE 语句（只更新传了值的字段）
    updates = []
    params = []

    if data.nickname is not None:
        updates.append("nickname = ?")
        params.append(data.nickname)
    if data.age is not None:
        updates.append("age = ?")
        params.append(data.age)
    if data.gender is not None:
        updates.append("gender = ?")
        params.append(data.gender)
    if data.city is not None:
        updates.append("city = ?")
        params.append(data.city)
    if data.travel_style is not None:
        updates.append("travel_style = ?")
        params.append(json.dumps(data.travel_style, ensure_ascii=False))
    if data.accessibility is not None:
        updates.append("accessibility = ?")
        params.append(data.accessibility)
    if data.phone is not None:
        updates.append("phone = ?")
        params.append(data.phone)
    if data.bio is not None:
        updates.append("bio = ?")
        params.append(data.bio)
    if data.birthday is not None:
        updates.append("birthday = ?")
        params.append(data.birthday)
    if data.avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(data.avatar_url)

    if updates:
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(current_user["id"])

        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)
        conn.commit()

    # 同步创建或更新 user_profiles 表
    # 大白话：确保 user_profiles 表有记录，这样推荐算法才能读取到扩展字段
    if data.travel_style is not None or data.city is not None:
        cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (current_user["id"],))
        existing_profile = cursor.fetchone()
        
        if existing_profile:
            # 更新现有记录
            cursor.execute("""
                UPDATE user_profiles 
                SET updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), current_user["id"]))
        else:
            cursor.execute("""
                INSERT INTO user_profiles (user_id, updated_at)
                VALUES (?, ?)
            """, (current_user["id"], datetime.now().isoformat()))
        
        conn.commit()

    conn.close()

    # 返回更新后的信息（重新查库，避免返回旧数据）
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")

    return await get_me(dict(row))


@router.post("/avatar", summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传头像：仅支持 JPG/PNG，且文件大小不超过 5MB。"""
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG 格式头像")

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="头像文件不能超过 5MB")

    os.makedirs(UPLOADS_DIR, exist_ok=True)

    ext = ".jpg" if file.content_type == "image/jpeg" else ".png"
    filename = f"user_{current_user['id']}_{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOADS_DIR, filename)

    with open(save_path, "wb") as f:
        f.write(content)

    avatar_url = f"/uploads/avatars/{filename}"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET avatar_url = ?, updated_at = ? WHERE id = ?",
        (avatar_url, datetime.now().isoformat(), current_user["id"]),
    )
    conn.commit()
    conn.close()

    return {"avatar_url": avatar_url}
