from __future__ import annotations

import asyncio
import threading
import time
from typing import Dict, Any, Optional, Tuple
from collections import deque
import hashlib
import json
import logging

logger = logging.getLogger("uvicorn")


class GraphCache:
    """Thread-safe cache for KumoRFM graph and model with TTL and version tracking."""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute default TTL
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, Any, float, str]] = {}  # key -> (graph, model, timestamp, version)
        self._lock = threading.RLock()
        self._version_cache: Dict[str, str] = {}  # key -> version hash
        self._last_data_check: float = 0
        self._data_check_interval: float = 30  # Check for data changes every 30 seconds
        
    def _compute_data_version(self, user_id: Optional[str] = None) -> str:
        """Compute a version hash based on relevant data state."""
        # In production, this would query latest timestamps from DB
        # For now, we'll use a simpler approach
        version_parts = [
            str(time.time() // self._data_check_interval),  # Time bucket
            user_id or "global"
        ]
        version_str = json.dumps(version_parts, sort_keys=True)
        return hashlib.md5(version_str.encode()).hexdigest()
    
    def get(self, key: str = "default", user_id: Optional[str] = None) -> Tuple[Optional[Any], Optional[Any]]:
        """Get cached graph and model if valid."""
        with self._lock:
            if key not in self._cache:
                return None, None
                
            graph, model, timestamp, version = self._cache[key]
            
            # Check TTL
            if time.time() - timestamp > self.ttl_seconds:
                logger.info(f"Cache expired for key {key} (age: {time.time() - timestamp:.1f}s)")
                del self._cache[key]
                return None, None
            
            # Check version (simplified for now)
            current_version = self._compute_data_version(user_id)
            if version != current_version:
                logger.info(f"Cache invalidated for key {key} due to version change")
                del self._cache[key]
                return None, None
                
            logger.info(f"Cache hit for key {key} (age: {time.time() - timestamp:.1f}s)")
            return graph, model
    
    def set(self, key: str, graph: Any, model: Any, user_id: Optional[str] = None) -> None:
        """Store graph and model in cache."""
        with self._lock:
            version = self._compute_data_version(user_id)
            self._cache[key] = (graph, model, time.time(), version)
            logger.info(f"Cache set for key {key} with version {version}")
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                    logger.info(f"Cache invalidated for key {key}")
            else:
                self._cache.clear()
                logger.info("All cache entries invalidated")
    
    def invalidate_user(self, user_id: str) -> None:
        """Invalidate cache entries related to a specific user."""
        with self._lock:
            # For now, invalidate all since we don't track user-specific keys
            # In production, maintain user -> keys mapping
            self._cache.clear()
            logger.info(f"Cache invalidated for user {user_id}")


class RecommendationCache:
    """Thread-safe per-user recommendation cache with improved concurrency."""
    
    def __init__(self, max_size: int = 10, min_size: int = 3):
        self.max_size = max_size
        self.min_size = min_size
        self._cache: Dict[str, deque] = {}
        self._lock = threading.RLock()
        self._inflight: Dict[str, asyncio.Lock] = {}
        self._async_lock = asyncio.Lock()
        
    def push(self, user_id: str, recommendations: list) -> None:
        """Add recommendations to user's cache."""
        with self._lock:
            if user_id not in self._cache:
                self._cache[user_id] = deque(maxlen=self.max_size)
            
            queue = self._cache[user_id]
            existing_units = {item[0] for item in queue}
            
            for rec in recommendations:
                try:
                    unitid = int(rec.get("unitid"))
                    score = float(rec.get("score")) if rec.get("score") is not None else None
                    
                    # Avoid duplicates
                    if unitid not in existing_units:
                        queue.append((unitid, score))
                        existing_units.add(unitid)
                except (ValueError, TypeError, KeyError):
                    continue
                    
            logger.info(f"Recommendation cache push for user {user_id}: size={len(queue)}")
    
    def pop(self, user_id: str) -> Optional[Tuple[int, Optional[float]]]:
        """Pop a recommendation from user's cache."""
        with self._lock:
            if user_id not in self._cache or not self._cache[user_id]:
                return None
                
            item = self._cache[user_id].popleft()
            remaining = len(self._cache[user_id])
            logger.info(f"Recommendation cache pop for user {user_id}: remaining={remaining}")
            return item
    
    def remove_unit(self, user_id: str, unitid: int) -> None:
        """Remove a specific unit from user's cache."""
        with self._lock:
            if user_id not in self._cache:
                return
                
            old_queue = self._cache[user_id]
            new_queue = deque(maxlen=self.max_size)
            
            for uid, score in old_queue:
                if int(uid) != int(unitid):
                    new_queue.append((uid, score))
                    
            self._cache[user_id] = new_queue
            logger.info(f"Removed unit {unitid} from user {user_id} cache")
    
    def size(self, user_id: str) -> int:
        """Get cache size for user."""
        with self._lock:
            return len(self._cache.get(user_id, []))
    
    async def get_inflight_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create an async lock for user to prevent duplicate fetches."""
        async with self._async_lock:
            if user_id not in self._inflight:
                self._inflight[user_id] = asyncio.Lock()
            return self._inflight[user_id]
    
    def clear_user(self, user_id: str) -> None:
        """Clear cache for a specific user."""
        with self._lock:
            if user_id in self._cache:
                del self._cache[user_id]
                logger.info(f"Cleared cache for user {user_id}")


# Global cache instances
graph_cache = GraphCache(ttl_seconds=300)  # 5 minute TTL
rec_cache = RecommendationCache(max_size=10, min_size=3)