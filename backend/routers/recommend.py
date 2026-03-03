"""
推荐API路由 - 个性化推荐、场景推荐

大白话说明：
    - GET /recommend → 获取个性化推荐
    - GET /recommend/scene/{scene} → 场景化推荐
    - POST /recommend/behavior → 记录用户行为
    - GET /recommend/collections → 获取用户收藏
    - POST /recommend/collect/{spot_id} → 收藏/取消收藏
"""

import json
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from models.user import BehaviorRecord, RecommendFeedbackEvent
from routers.auth import get_current_user
from database import DB_PATH
from algorithms.hybrid_recommender import HybridRecommender

router = APIRouter(prefix="/recommend", tags=["推荐"])

# 推荐引擎单例（延迟初始化）
_recommender = None

def get_recommender() -> HybridRecommender:
    """获取推荐引擎单例"""
    global _recommender
    if _recommender is None:
        _recommender = HybridRecommender(DB_PATH)
    return _recommender


@router.get("", summary="获取个性化推荐")
async def get_recommendations(
    n: int = Query(10, ge=1, le=50, description="推荐数量"),
    current_user: dict = Depends(get_current_user),
):
    """
    获取个性化推荐列表

    大白话：根据用户的历史行为，用混合推荐算法生成个性化推荐
    """
    recommender = get_recommender()
    result = recommender.get_recommendation_with_details(current_user["id"], n)
    
    # 终端打印推荐的混合得分结果
    items = result.get("items", [])
    if items:
        print("\n============ 🔥 平常用户浏览 - 混合得分结果排布 ============")
        for idx, s in enumerate(items[:10]):
            score = s.get('score', 0)
            score_display = score if score > 1 else score * 100
            print(f" [Top {idx+1}] {s.get('name', '未知')} - 混合/推荐得分: {score_display:.2f}")
        print("============================================================\n")

    return result


@router.get("/scene/{scene}", summary="场景化推荐")
async def get_scene_recommendations(
    scene: str,
    n: int = Query(10, ge=1, le=50),
):
    """
    场景化推荐（不需要登录）

    大白话：按场景（亲子游/老年游等）推荐景点
    """
    valid_scenes = ["亲子游", "老年游", "历史文化游", "自然风光游", "摄影打卡", "探险运动"]
    if scene not in valid_scenes:
        raise HTTPException(status_code=400, detail=f"无效的场景，支持的场景：{valid_scenes}")

    recommender = get_recommender()
    items = recommender.recommend(user_id=0, n=n, scene=scene)

    # 补充景点详细信息
    if items:
        spot_ids = [item["spot_id"] for item in items]
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(spot_ids))
        cursor.execute(f"""
            SELECT id, name, city, rating, image_url, spot_type, suggest_time
            FROM spots WHERE id IN ({placeholders})
        """, spot_ids)
        spot_map = {row["id"]: dict(row) for row in cursor.fetchall()}
        
        # 计算每个景点的综合评分
        for spot_id in spot_ids:
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as count 
                FROM spot_comments 
                WHERE spot_id = ?
            """, (spot_id,))
            comment_result = cursor.fetchone()
            comment_avg = comment_result[0] if comment_result[0] else None
            base_rating = spot_map[spot_id]["rating"] if spot_map[spot_id]["rating"] else 3.0
            
            # 使用综合评分
            if comment_avg:
                spot_map[spot_id]["composite_rating"] = comment_avg
            else:
                spot_map[spot_id]["composite_rating"] = base_rating
        
        conn.close()

        for item in items:
            info = spot_map.get(item["spot_id"], {})
            item.update({
                "name": info.get("name", ""),
                "city": info.get("city", ""),
                "rating": info.get("composite_rating"),  # 使用综合评分
                "image_url": info.get("image_url", ""),
            })

    return {"items": items, "scene": scene}


@router.post("/behavior", summary="记录用户行为")
async def record_behavior(
    data: BehaviorRecord,
    current_user: dict = Depends(get_current_user),
):
    """
    记录用户行为（浏览、评分、搜索）

    大白话：前端在用户浏览/评分/搜索景点时调这个接口，记录用户行为
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查景点是否存在
    cursor.execute("SELECT id FROM spots WHERE id = ?", (data.spot_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="景点不存在")

    cursor.execute("""
        INSERT INTO user_behaviors (user_id, spot_id, behavior_type, rating, search_query, duration)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (current_user["id"], data.spot_id, data.behavior_type,
          data.rating, data.search_query, data.duration))

    conn.commit()
    conn.close()

    return {"message": "行为记录成功", "behavior_type": data.behavior_type}


@router.get("/collections", summary="获取用户收藏")
async def get_collections(
    current_user: dict = Depends(get_current_user),
):
    """获取用户收藏的所有景点"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.name, s.city, s.rating, s.image_url, s.spot_type,
               uc.created_at as collected_at
        FROM user_collections uc
        JOIN spots s ON uc.spot_id = s.id
        WHERE uc.user_id = ?
        ORDER BY uc.created_at DESC
    """, (current_user["id"],))

    rows = cursor.fetchall()
    conn.close()

    items = [dict(row) for row in rows]
    return {"items": items, "total": len(items)}


@router.post("/feedback", summary="记录推荐反馈")
async def record_feedback(
    data: RecommendFeedbackEvent,
    current_user: dict = Depends(get_current_user),
):
    """记录推荐曝光/点击/收藏/评分反馈。"""
    
    # 终端打印用户的点击/交互事件
    if data.event_type in ["click", "exposure"]:
        action_name = "点击" if data.event_type == "click" else "曝光"
        score_info = f"，相关得分: {data.score}" if data.score else ""
        print(f"👋 [行为反馈] 用户 {current_user['username']} 触发了卡片的 {action_name} 操作 -> 景点: {data.spot_id}, 来源: {data.source}{score_info}")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM spots WHERE id = ?", (data.spot_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="景点不存在")

    context = json.dumps(
        {
            "rec_session_id": data.rec_session_id,
            "source": data.source,
        },
        ensure_ascii=False,
    )

    cursor.execute(
        """
        INSERT INTO recommend_feedback (user_id, spot_id, event_type, event_value, context)
        VALUES (?, ?, ?, ?, ?)
        """,
        (current_user["id"], data.spot_id, data.event_type, data.score, context),
    )

    conn.commit()
    conn.close()

    return {"message": "feedback recorded"}


@router.post("/collect/{spot_id}", summary="收藏/取消收藏")
async def toggle_collection(
    spot_id: int,
    current_user: dict = Depends(get_current_user),
):
    """
    收藏或取消收藏景点

    大白话：如果没收藏就收藏，已经收藏了就取消。像一个开关
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查是否已收藏
    cursor.execute(
        "SELECT id FROM user_collections WHERE user_id = ? AND spot_id = ?",
        (current_user["id"], spot_id)
    )
    existing = cursor.fetchone()

    if existing:
        # 已收藏 → 取消
        cursor.execute(
            "DELETE FROM user_collections WHERE user_id = ? AND spot_id = ?",
            (current_user["id"], spot_id)
        )
        conn.commit()
        conn.close()
        return {"collected": False, "message": "已取消收藏"}
    else:
        # 未收藏 → 添加
        cursor.execute(
            "INSERT INTO user_collections (user_id, spot_id) VALUES (?, ?)",
            (current_user["id"], spot_id)
        )
        # 同时记录收藏行为
        cursor.execute("""
            INSERT INTO user_behaviors (user_id, spot_id, behavior_type)
            VALUES (?, ?, 'collect')
        """, (current_user["id"], spot_id))
        conn.commit()
        conn.close()
        return {"collected": True, "message": "收藏成功 ❤️"}
