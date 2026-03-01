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

    # 构建过滤条件
    where_parts = ["1=1"]
    params = []

    if city:
        where_parts.append("city = ?")
        params.append(city)
    if spot_type:
        where_parts.append("spot_type LIKE ?")
        params.append(f"%{spot_type}%")
    if min_rating:
        where_parts.append("rating >= ?")
        params.append(min_rating)

    where_clause = " AND ".join(where_parts)

    # 排序
    order = "rating DESC" if sort_by == "rating" else "name ASC"

    # 总数
    cursor.execute(f"SELECT COUNT(*) FROM spots WHERE {where_clause}", params)
    total = cursor.fetchone()[0]

    # 分页查询
    offset = (page - 1) * page_size
    cursor.execute(f"""
        SELECT id, name, city, rating, image_url, spot_type, suggest_time, address
        FROM spots 
        WHERE {where_clause}
        ORDER BY CASE WHEN rating IS NULL THEN 1 ELSE 0 END, {order}
        LIMIT ? OFFSET ?
    """, params + [page_size, offset])

    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "name": row["name"],
            "city": row["city"],
            "rating": row["rating"],
            "image_url": row["image_url"],
            "spot_type": row["spot_type"],
            "suggest_time": row["suggest_time"],
            "address": row["address"],
        })

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
    conn.close()

    items = [dict(row) for row in rows]
    return {"items": items, "total": len(items), "query": q}


@router.get("/{spot_id}", summary="获取景点详情")
async def get_spot_detail(spot_id: int):
    """获取单个景点的完整信息"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM spots WHERE id = ?", (spot_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="景点不存在")

    spot = dict(row)
    # 解析JSON字段
    try:
        spot["spot_type"] = json.loads(spot.get("spot_type") or "[]")
    except json.JSONDecodeError:
        spot["spot_type"] = []
    try:
        spot["target_group"] = json.loads(spot.get("target_group") or "[]")
    except json.JSONDecodeError:
        spot["target_group"] = []

    return spot
