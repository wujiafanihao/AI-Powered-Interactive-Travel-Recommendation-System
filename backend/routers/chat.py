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

    # 调用聊天服务处理消息（带上用户画像信息，用于个性化搜索）
    chat_service = get_chat_service()
    
    # 读取用户画像（城市、偏好），传给搜索流程做兜底
    conn2 = sqlite3.connect(DB_PATH)
    conn2.row_factory = sqlite3.Row
    c2 = conn2.cursor()
    c2.execute("""
        SELECT u.city, u.travel_style, up.interest_tags, up.preferred_season
        FROM users u
        LEFT JOIN user_profiles up ON up.user_id = u.id
        WHERE u.id = ?
    """, (user_id,))
    urow = c2.fetchone()
    conn2.close()
    user_profile_ctx = {}
    if urow:
        user_profile_ctx = {
            "city": urow["city"] or None,
            "travel_style": urow["travel_style"] or None,
            "interest_tags": urow["interest_tags"] or None,
            "preferred_season": urow["preferred_season"] or None,
        }
    
    print(f"\n========== AI 对话调试信息 ==========")
    print(f"👤 用户消息: {data.message}")
    print(f"🆔 用户ID: {user_id} | 用户画像: {user_profile_ctx}")
    print(f"📋 会话ID: {session_id}")
    
    result = await chat_service.process_message(
        user_message=data.message,
        user_id=user_id,
        history=history,
        user_profile=user_profile_ctx,
    )
    
    print(f"🎯 识别意图: {result.get('intent', 'unknown')}")
    print(f"📝 AI 回复: {result.get('reply', '')[:100]}...")
    print(f"🔍 搜索结果数量: {len(result.get('spots', []))}")
    if result.get('sources'):
        print(f"📚 参考来源: {result.get('sources')}")
    print(f"========================================\n")

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


@router.post("/spot/{spot_id}", summary="针对特定景点的AI对话")
async def spot_chat(
    spot_id: int,
    data: ChatMessage,
    current_user: dict = Depends(get_current_user),
):
    """
    针对特定景点的AI对话

    大白话：在景点详情页和AI对话，AI会带上这个景点的信息
    """
    user_id = current_user["id"]
    session_id = data.session_id or f"spot_{spot_id}_{uuid.uuid4()}"

    # 获取历史对话
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取景点信息作为上下文
    cursor.execute("SELECT * FROM spots WHERE id = ?", (spot_id,))
    spot = cursor.fetchone()

    if not spot:
        conn.close()
        raise HTTPException(status_code=404, detail="景点不存在")

    cursor.execute("""
        SELECT role, content FROM chat_history
        WHERE user_id = ? AND session_id = ?
        ORDER BY created_at DESC LIMIT 10
    """, (user_id, session_id))
    history = [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]
    history.reverse()

    # 保存用户消息
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, content, session_id)
        VALUES (?, 'user', ?, ?)
    """, (user_id, data.message, session_id))
    conn.commit()
    conn.close()

    # 构建特定景点的系统提示词
    spot_context = f"""当前正在讨论的景点是：{spot['name']}（位于{spot['city']}）。
景点介绍：{spot['description']}
开放时间：{spot['open_time'] or '未知'}
门票信息：{spot['ticket_info'] or '未知'}
游玩贴士：{spot['tips'] or '无'}"""

    # 调用聊天服务
    chat_service = get_chat_service()

    # 在这个特殊场景下，我们可以通过修改系统提示词或直接让大模型基于上下文回答
    # 这里直接调用底层的 chat_with_context 比较合适
    system_prompt = f"""你是一个专属的景点导游。{spot_context}
请友好、热情地回答游客关于这个景点的任何问题。如果游客问了其他景点，你可以简单回答并尝试把话题引回当前景点。"""

    from ai.llm_client import get_llm_client
    llm_client = get_llm_client()
    reply = await llm_client.chat(data.message, system_prompt=system_prompt, history=history)

    # 保存AI回复
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (user_id, role, content, session_id)
        VALUES (?, 'assistant', ?, ?)
    """, (user_id, reply, session_id))
    conn.commit()
    conn.close()

    return ChatResponse(
        reply=reply,
        intent="spot_qa",
        spots=[dict(spot)],  # 附带当前景点信息
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

@router.delete("/session/{session_id}", summary="删除会话聊天记录")
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    删除指定的会话聊天记录

    大白话：从数据库中清除该用户这个会话的所有聊天记录
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM chat_history
        WHERE user_id = ? AND session_id = ?
    """, (current_user["id"], session_id))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return {"message": "会话已删除", "deleted_count": deleted_count}
