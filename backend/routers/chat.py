"""
AI对话API路由 - 智能问答、帮搜

大白话说明：
    - POST /chat → 发送消息给AI助手
    - GET /chat/history → 获取对话历史
"""

import uuid
import sqlite3
from fastapi import APIRouter, Depends
from typing import Optional

from models.user import ChatMessage, ChatResponse
from routers.auth import get_current_user
from database import DB_PATH
from ai.intent_recognizer import get_chat_service

router = APIRouter(prefix="/chat", tags=["AI对话"])


@router.post("", response_model=ChatResponse, summary="发送消息给AI助手")
async def chat(
    data: ChatMessage,
    current_user: dict = Depends(get_current_user),
):
    """
    和AI助手对话

    大白话：
    1. 接收用户消息
    2. AI识别意图（搜索/问答/帮助/闲聊）
    3. 返回AI回复和相关结果
    """
    user_id = current_user["id"]
    session_id = data.session_id or str(uuid.uuid4())

    # 获取历史对话（最近10条）
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM chat_history 
        WHERE user_id = ? AND session_id = ?
        ORDER BY created_at DESC LIMIT 10
    """, (user_id, session_id))
    history = [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]
    history.reverse()  # 按时间正序

    # 保存用户消息到历史
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, content, session_id)
        VALUES (?, 'user', ?, ?)
    """, (user_id, data.message, session_id))
    conn.commit()
    conn.close()

    # 调用聊天服务处理消息
    chat_service = get_chat_service()
    result = await chat_service.process_message(
        user_message=data.message,
        user_id=user_id,
        history=history,
    )

    # 保存AI回复到历史
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, content, session_id)
        VALUES (?, 'assistant', ?, ?)
    """, (user_id, result["reply"], session_id))
    conn.commit()
    conn.close()

    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        spots=result.get("spots"),
        sources=result.get("sources"),
        session_id=session_id,
    )


@router.get("/history", summary="获取对话历史")
async def get_chat_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """
    获取用户的对话历史

    大白话：返回最近的聊天记录，前端用来显示对话气泡
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if session_id:
        cursor.execute("""
            SELECT role, content, created_at FROM chat_history
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at ASC LIMIT ?
        """, (current_user["id"], session_id, limit))
    else:
        cursor.execute("""
            SELECT role, content, session_id, created_at FROM chat_history
            WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (current_user["id"], limit))

    rows = cursor.fetchall()
    conn.close()

    messages = [dict(row) for row in rows]
    if not session_id:
        messages.reverse()

    return {"messages": messages, "total": len(messages)}
