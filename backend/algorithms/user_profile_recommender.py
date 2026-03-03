"""
用户画像重排序引擎

大白话说明：
    这个模块负责给“用户-景点”算一个 0-100 的匹配分。
    匹配分用于混合推荐的第三路信号（w_profile），让推荐更贴近用户画像。
"""

import json
import sqlite3
from collections import Counter


class UserProfileRecommender:
    """用户画像匹配评分器"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _parse_multi_value(self, raw) -> list[str]:
        """把 JSON 字符串/逗号分隔字符串/列表统一转成字符串列表。"""
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(v).strip() for v in raw if str(v).strip()]

        text = str(raw).strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
            if isinstance(parsed, str):
                text = parsed
        except (json.JSONDecodeError, TypeError):
            pass

        for sep in ["、", "，", ",", "/", "|", " "]:
            text = text.replace(sep, ",")
        return [v.strip() for v in text.split(",") if v.strip()]

    def _load_user_profile(self, cursor: sqlite3.Cursor, user_id: int) -> dict:
        """读取用户基础画像（city/travel_style + user_profiles 扩展字段）。"""
        cursor.execute(
            """
            SELECT
                u.city,
                u.travel_style,
                up.preferred_season,
                up.interest_tags
            FROM users u
            LEFT JOIN user_profiles up ON up.user_id = u.id
            WHERE u.id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {
                "city": None,
                "travel_style": [],
                "preferred_season": None,
                "interest_tags": [],
            }

        return {
            "city": row[0],
            "travel_style": self._parse_multi_value(row[1]),
            "preferred_season": row[2],
            "interest_tags": self._parse_multi_value(row[3]),
        }

    def _load_behavior_preferences(self, cursor: sqlite3.Cursor, user_id: int) -> dict:
        """从历史行为和收藏中提取偏好城市/偏好类型。"""
        city_counter = Counter()
        type_counter = Counter()

        cursor.execute(
            """
            SELECT s.city, s.spot_type
            FROM user_behaviors ub
            JOIN spots s ON s.id = ub.spot_id
            WHERE ub.user_id = ?
            ORDER BY ub.created_at DESC
            LIMIT 300
            """,
            (user_id,),
        )
        for city, spot_type in cursor.fetchall():
            if city:
                city_counter[city] += 1
            for t in self._parse_multi_value(spot_type):
                type_counter[t] += 1

        cursor.execute(
            """
            SELECT s.city, s.spot_type
            FROM user_collections uc
            JOIN spots s ON s.id = uc.spot_id
            WHERE uc.user_id = ?
            ORDER BY uc.created_at DESC
            LIMIT 200
            """,
            (user_id,),
        )
        for city, spot_type in cursor.fetchall():
            if city:
                city_counter[city] += 2
            for t in self._parse_multi_value(spot_type):
                type_counter[t] += 2

        top_cities = {city for city, _ in city_counter.most_common(3)}
        top_types = {t for t, _ in type_counter.most_common(6)}

        return {
            "top_cities": top_cities,
            "top_types": top_types,
        }

    def _load_spot_snapshot(self, cursor: sqlite3.Cursor, spot_id: int) -> dict:
        """读取景点参与打分的核心字段。"""
        cursor.execute(
            """
            SELECT city, spot_type, target_group, suggest_season
            FROM spots
            WHERE id = ?
            """,
            (spot_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {
                "city": None,
                "spot_types": [],
                "target_groups": [],
                "suggest_season": None,
            }

        return {
            "city": row[0],
            "spot_types": self._parse_multi_value(row[1]),
            "target_groups": self._parse_multi_value(row[2]),
            "suggest_season": row[3],
        }

    def _score(self, user_profile: dict, behavior_pref: dict, spot: dict) -> float:
        """规则打分：0-100。"""
        score = 0.0

        user_city = user_profile.get("city")
        spot_city = spot.get("city")
        if user_city and spot_city and user_city in spot_city:
            score += 30.0

        preferred_season = user_profile.get("preferred_season")
        suggest_season = spot.get("suggest_season") or ""
        if preferred_season and preferred_season in suggest_season:
            score += 20.0

        user_interest = set(user_profile.get("travel_style", [])) | set(user_profile.get("interest_tags", []))
        spot_tags = set(spot.get("spot_types", [])) | set(spot.get("target_groups", []))
        overlap = len(user_interest & spot_tags)
        if overlap > 0:
            score += min(30.0, overlap * 10.0)

        if spot_city and spot_city in behavior_pref.get("top_cities", set()):
            score += 10.0

        behavior_overlap = len(behavior_pref.get("top_types", set()) & spot_tags)
        if behavior_overlap > 0:
            score += min(10.0, behavior_overlap * 5.0)

        return round(min(100.0, score), 2)

    def calculate_match_score(self, user_id: int, spot_id: int) -> float:
        """计算单个景点匹配分。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            user_profile = self._load_user_profile(cursor, user_id)
            behavior_pref = self._load_behavior_preferences(cursor, user_id)
            spot = self._load_spot_snapshot(cursor, spot_id)
            return self._score(user_profile, behavior_pref, spot)
        finally:
            conn.close()

    def recommend(self, user_id: int, n: int = 10) -> list[dict]:
        """根据用户画像推荐景点。"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            user_profile = self._load_user_profile(cursor, user_id)
            behavior_pref = self._load_behavior_preferences(cursor, user_id)

            # 查询所有景点
            cursor.execute("""
                SELECT id, name, city, spot_type, target_group, suggest_season
                FROM spots
            """)
            all_spots = cursor.fetchall()

            # 计算每个景点的匹配分
            scored_spots = []
            for row in all_spots:
                spot_id = row[0]
                spot = {
                    "name": row[1],
                    "city": row[2],
                    "spot_types": self._parse_multi_value(row[3]),
                    "target_groups": self._parse_multi_value(row[4]),
                    "suggest_season": row[5],
                }
                score = self._score(user_profile, behavior_pref, spot)
                if score > 0:
                    scored_spots.append({
                        "spot_id": spot_id,
                        "score": score,
                        "reason": f"画像匹配度 {int(score)}%",
                    })

            # 按匹配分排序
            scored_spots.sort(key=lambda x: x["score"], reverse=True)
            return scored_spots[:n]
        finally:
            conn.close()

    def calculate_batch_scores(self, user_id: int, spot_ids: set[int] | list[int]) -> dict[int, float]:
        """批量计算多个景点匹配分。"""
        ids = list(spot_ids)
        if not ids:
            return {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            user_profile = self._load_user_profile(cursor, user_id)
            behavior_pref = self._load_behavior_preferences(cursor, user_id)

            scores: dict[int, float] = {}
            for spot_id in ids:
                spot = self._load_spot_snapshot(cursor, spot_id)
                scores[spot_id] = self._score(user_profile, behavior_pref, spot)
            return scores
        finally:
            conn.close()
