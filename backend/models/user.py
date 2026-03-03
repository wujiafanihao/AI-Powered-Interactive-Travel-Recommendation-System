"""
Pydantic 数据模型 - 用户相关

大白话说明：
    定义API请求和响应的数据格式。
    Pydantic会自动校验数据类型和格式，
    确保前端传过来的数据是合法的。
"""

from pydantic import BaseModel, Field, constr
from typing import Optional, Literal
from datetime import datetime


# 严格手机号：必须是 1 开头的 11 位数字，且不做类型宽松转换
PhoneStr = constr(strict=True, pattern=r"^1\d{10}$")


# ==================== 请求模型 ====================

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: Optional[str] = Field(None, max_length=20, description="昵称")
    age: Optional[int] = Field(None, ge=1, le=120, description="年龄")
    gender: Optional[str] = Field(None, description="性别：男/女/未知")
    city: Optional[str] = Field(None, description="所在城市")
    travel_style: Optional[list[str]] = Field(None, description="旅行风格偏好列表")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """用户信息更新请求"""
    nickname: Optional[str] = Field(None, max_length=20)
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = None
    city: Optional[str] = None
    travel_style: Optional[list[str]] = None
    accessibility: Optional[str] = None
    phone: Optional[PhoneStr] = None
    bio: Optional[str] = Field(None, max_length=500)
    birthday: Optional[str] = None
    avatar_url: Optional[str] = None


# ==================== 响应模型 ====================

class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    nickname: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    travel_style: Optional[list[str]] = None
    accessibility: str = "normal"
    phone: Optional[str] = None
    bio: Optional[str] = None
    birthday: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    """登录成功返回的Token"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChatMessage(BaseModel):
    """聊天消息请求"""
    message: str = Field(..., min_length=1, max_length=500, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str
    intent: str
    spots: Optional[list[dict]] = None
    sources: Optional[list[dict]] = None
    session_id: Optional[str] = None


class BehaviorRecord(BaseModel):
    """用户行为记录请求"""
    spot_id: int = Field(..., description="景点ID")
    behavior_type: str = Field(..., description="行为类型：browse/rate/collect/search")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="评分(1-5)")
    search_query: Optional[str] = Field(None, description="搜索关键词")
    duration: Optional[int] = Field(None, ge=0, description="浏览时长(秒)")


class RecommendRequest(BaseModel):
    """推荐请求"""
    n: int = Field(10, ge=1, le=50, description="推荐数量")
    scene: Optional[str] = Field(None, description="场景标签")


class RecommendFeedbackEvent(BaseModel):
    """推荐反馈事件请求"""
    spot_id: int = Field(..., description="景点ID")
    event_type: Literal["exposure", "click", "collect", "rate"] = Field(..., description="事件类型")
    rec_session_id: Optional[str] = Field(None, max_length=64, description="推荐会话ID")
    source: Optional[str] = Field(None, max_length=32, description="推荐来源")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="推荐分")
