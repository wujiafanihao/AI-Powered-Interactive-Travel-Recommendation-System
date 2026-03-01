"""
景点API路由 - 景点列表、详情、搜索

大白话说明：
    提供景点数据的CRUD接口：
    - GET /spots → 景点列表（分页+筛选）
    - GET /spots/{id} → 景点详情
    - GET /spots/search → 搜索景点
    - GET /spots/cities → 获取所有城市列表
"""

import json
import sqlite3
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from database import DB_PATH

router = APIRouter(prefix="/spots", tags=["景点"])


def calculate_composite_rating(spot_id: int, conn) -> float:
    """
    计算景点的综合评分
    综合考虑：评论评分、用户行为评分、原始基础评分
    """
    cursor = conn.cursor()
    
    # 获取原始基础评分
    cursor.execute("SELECT rating FROM spots WHERE id = ?", (spot_id,))
    base_rating_row = cursor.fetchone()
    base_rating = base_rating_row[0] if base_rating_row and base_rating_row[0] is not None else None
    
    # 获取评论平均评分
    cursor.execute("""
        SELECT AVG(rating) as avg_rating, COUNT(*) as count 
        FROM spot_comments 
        WHERE spot_id = ?
    """, (spot_id,))
    comment_result = cursor.fetchone()
    comment_avg = comment_result[0] if comment_result[0] is not None else None
    comment_count = comment_result[1] if comment_result[1] else 0
    
    # 获取用户行为评分（浏览时长、收藏等）
    cursor.execute("""
        SELECT AVG(rating) as avg_behavior_rating, COUNT(*) as count 
        FROM user_behaviors 
        WHERE spot_id = ? AND rating IS NOT NULL
    """, (spot_id,))
    behavior_result = cursor.fetchone()
    behavior_avg = behavior_result[0] if behavior_result[0] is not None else None
    behavior_count = behavior_result[1] if behavior_result[1] else 0
    
    # 优先使用评论评分，其次用户行为评分，最后基础评分
    if comment_avg and comment_count >= 3:
        # 有足够多评论时，主要使用评论评分
        final_rating = comment_avg
    elif comment_avg and comment_count > 0:
        # 评论较少时，结合评论和基础评分
        if base_rating:
            final_rating = comment_avg * 0.7 + base_rating * 0.3
        else:
            final_rating = comment_avg
    elif behavior_avg and behavior_count > 0:
        # 使用用户行为评分
        final_rating = behavior_avg
    elif base_rating:
        # 使用基础评分
        final_rating = base_rating
    else:
        # 默认评分
        final_rating = 4.0
    
    final_rating = max(1.0, min(5.0, final_rating))  # 确保在 1-5 之间
    
    return round(final_rating, 1)


@router.get("", summary="获取景点列表")
async def get_spots(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    city: Optional[str] = Query(None, description="按城市筛选"),
    spot_type: Optional[str] = Query(None, description="按类型筛选"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="最低评分"),
    sort_by: str = Query("rating", description="排序字段：rating/name"),
):
    """
    获取景点列表（支持分页和筛选）

    大白话：类似电商的商品列表，支持按城市、类型、评分筛选
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 构建过滤条件（先不包含最低评分，因为我们需要先计算综合评分）
    where_parts = ["1=1"]
    params = []

    if city:
        where_parts.append("city = ?")
        params.append(city)
    if spot_type:
        where_parts.append("spot_type LIKE ?")
        params.append(f"%{spot_type}%")

    where_clause = " AND ".join(where_parts)

    # 查询所有符合条件的景点（先不限制数量）
    cursor.execute(f"""
        SELECT id, name, city, rating, image_url, spot_type, suggest_time, address
        FROM spots 
        WHERE {where_clause}
    """, params)

    rows = cursor.fetchall()

    # 计算每个景点的综合评分并进行筛选
    all_items = []
    for row in rows:
        spot_id = row["id"]
        composite_rating = calculate_composite_rating(spot_id, conn)
        
        # 最低评分筛选
        if min_rating and composite_rating < min_rating:
            continue
            
        all_items.append({
            "id": spot_id,
            "name": row["name"],
            "city": row["city"],
            "rating": composite_rating,
            "image_url": row["image_url"],
            "spot_type": row["spot_type"],
            "suggest_time": row["suggest_time"],
            "address": row["address"],
        })
    
    conn.close()

    # 排序
    if sort_by == "rating":
        all_items.sort(key=lambda x: (-x["rating"], x["name"]))
    else:
        all_items.sort(key=lambda x: x["name"])

    # 分页
    total = len(all_items)
    offset = (page - 1) * page_size
    items = all_items[offset:offset + page_size]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/cities", summary="获取所有城市列表")
async def get_cities():
    """获取数据库中所有城市名称（用于前端下拉选择）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city FROM spots ORDER BY city")
    cities = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"cities": cities, "total": len(cities)}


@router.get("/search", summary="搜索景点")
async def search_spots(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
):
    """
    关键词搜索景点

    大白话：在景点名称和介绍中搜索关键词
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, city, rating, image_url, spot_type, address
        FROM spots 
        WHERE name LIKE ? OR description LIKE ? OR city LIKE ?
        ORDER BY CASE WHEN rating IS NULL THEN 1 ELSE 0 END, rating DESC
        LIMIT ?
    """, (f"%{q}%", f"%{q}%", f"%{q}%", limit))

    rows = cursor.fetchall()

    items = []
    for row in rows:
        spot_id = row["id"]
        composite_rating = calculate_composite_rating(spot_id, conn)
        spot_dict = dict(row)
        spot_dict["rating"] = composite_rating
        items.append(spot_dict)
    
    conn.close()
    return {"items": items, "total": len(items), "query": q}


@router.get("/{spot_id}/comments", summary="获取景点评论")
async def get_spot_comments(spot_id: int):
    """获取景点的用户评论"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.rating, c.content, c.created_at, u.nickname, u.username
        FROM spot_comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.spot_id = ?
        ORDER BY c.created_at DESC
    """, (spot_id,))
    rows = cursor.fetchall()
    conn.close()

    return {"items": [dict(row) for row in rows], "total": len(rows)}
@router.get("/{spot_id}", summary="获取景点详情")
async def get_spot_detail(spot_id: int):
    """获取单个景点的完整信息"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM spots WHERE id = ?", (spot_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="景点不存在")

    spot = dict(row)
    
    # 使用综合评分
    spot["rating"] = calculate_composite_rating(spot_id, conn)
    
    # 解析JSON字段
    try:
        spot["spot_type"] = json.loads(spot.get("spot_type") or "[]")
    except json.JSONDecodeError:
        spot["spot_type"] = []
    try:
        spot["target_group"] = json.loads(spot.get("target_group") or "[]")
    except json.JSONDecodeError:
        spot["target_group"] = []
    
    conn.close()
    return spot
