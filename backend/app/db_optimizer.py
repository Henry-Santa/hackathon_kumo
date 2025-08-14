from __future__ import annotations

import snowflake.connector
from typing import Set, Dict, List, Optional
import pandas as pd
import logging
from .db import get_connection

logger = logging.getLogger("uvicorn")


class BatchedQueries:
    """Optimized database queries with batching and caching."""
    
    @staticmethod
    def fetch_user_interactions(user_id: str) -> Dict[str, Set[int]]:
        """Fetch both likes and dislikes in a single query."""
        try:
            with get_connection() as conn:
                with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
                    # Single query to get both likes and dislikes
                    cur.execute(
                        """
                        SELECT 
                            'like' as interaction_type,
                            UNITID
                        FROM DATA_LAKE.PUBLIC.USER_LIKES 
                        WHERE USER_ID = %s
                        UNION ALL
                        SELECT 
                            'dislike' as interaction_type,
                            UNITID
                        FROM DATA_LAKE.PUBLIC.USER_DISLIKES 
                        WHERE USER_ID = %s
                        """,
                        (user_id, user_id)
                    )
                    
                    likes = set()
                    dislikes = set()
                    
                    for row in cur.fetchall():
                        unitid = int(row["UNITID"])
                        if row["INTERACTION_TYPE"] == "like":
                            likes.add(unitid)
                        else:
                            dislikes.add(unitid)
                    
                    logger.info(f"Fetched {len(likes)} likes and {len(dislikes)} dislikes for user {user_id}")
                    return {"likes": likes, "dislikes": dislikes}
                    
        except Exception as e:
            logger.error(f"Failed to fetch user interactions: {e}")
            return {"likes": set(), "dislikes": set()}
    
    @staticmethod
    def fetch_universities_batch(unitids: List[int], columns: List[str]) -> List[Dict]:
        """Fetch multiple universities in a single query."""
        if not unitids:
            return []
            
        try:
            with get_connection() as conn:
                with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
                    cols = ", ".join(columns)
                    placeholders = ", ".join(["%s"] * len(unitids))
                    
                    cur.execute(
                        f"""
                        SELECT {cols}
                        FROM DATA_LAKE.PUBLIC.UNIVERSITY_DATA
                        WHERE UNITID IN ({placeholders})
                        """,
                        unitids
                    )
                    
                    return cur.fetchall()
                    
        except Exception as e:
            logger.error(f"Failed to fetch universities batch: {e}")
            return []
    
    @staticmethod
    def get_data_stats() -> Dict[str, any]:
        """Get statistics about the data for cache invalidation."""
        try:
            with get_connection() as conn:
                with conn.cursor(snowflake.connector.DictCursor) as cur:  # type: ignore
                    cur.execute(
                        """
                        SELECT 
                            (SELECT COUNT(*) FROM DATA_LAKE.PUBLIC.USERS) as user_count,
                            (SELECT COUNT(*) FROM DATA_LAKE.PUBLIC.USER_LIKES) as like_count,
                            (SELECT COUNT(*) FROM DATA_LAKE.PUBLIC.USER_DISLIKES) as dislike_count,
                            (SELECT MAX(CREATED_AT) FROM DATA_LAKE.PUBLIC.USER_LIKES) as latest_like,
                            (SELECT MAX(CREATED_AT) FROM DATA_LAKE.PUBLIC.USER_DISLIKES) as latest_dislike
                        """
                    )
                    
                    result = cur.fetchone()
                    return dict(result) if result else {}
                    
        except Exception as e:
            logger.error(f"Failed to fetch data stats: {e}")
            return {}