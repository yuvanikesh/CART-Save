"""
CartGuard AI - Redis Integration & In-Memory Fallback Service
Provides event streaming, session caching, and rate limiting with graceful fallback.
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional
import os

try:
    import redis.asyncio as redis
except ImportError:
    redis = None


class RedisService:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
        self.is_connected = False
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._memory_rate_limit: Dict[str, list] = {}

    async def connect(self):
        """Attempt to connect to Redis server."""
        if redis is None:
            self.is_connected = False
            return False

        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await self.client.ping()
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            self.client = None
            return False

    async def close(self):
        """Close Redis connection."""
        if self.client and self.is_connected:
            try:
                await self.client.close()
            except Exception:
                pass
            self.is_connected = False

    async def cache_get(self, key: str) -> Optional[Any]:
        """Get cached item."""
        if self.is_connected and self.client:
            try:
                val = await self.client.get(key)
                if val:
                    return json.loads(val)
            except Exception:
                pass

        # Fallback to in-memory cache
        item = self._memory_cache.get(key)
        if item:
            if item["expires_at"] and time.time() > item["expires_at"]:
                del self._memory_cache[key]
                return None
            return item["data"]
        return None

    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set cached item with TTL."""
        if self.is_connected and self.client:
            try:
                await self.client.set(key, json.dumps(value), ex=ttl_seconds)
                return True
            except Exception:
                pass

        # Fallback to in-memory
        expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else None
        self._memory_cache[key] = {"data": value, "expires_at": expires_at}
        return True

    async def is_rate_limited(self, identifier: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Rate limiting check."""
        now = time.time()
        if self.is_connected and self.client:
            try:
                key = f"rate_limit:{identifier}"
                pipe = self.client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                res = await pipe.execute()
                request_count = res[2]
                return request_count > max_requests
            except Exception:
                pass

        # Fallback in-memory rate limiter
        timestamps = self._memory_rate_limit.get(identifier, [])
        valid_timestamps = [ts for ts in timestamps if ts > now - window_seconds]
        valid_timestamps.append(now)
        self._memory_rate_limit[identifier] = valid_timestamps
        return len(valid_timestamps) > max_requests

    async def publish_event(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish event message."""
        if self.is_connected and self.client:
            try:
                await self.client.publish(channel, json.dumps(message))
                return True
            except Exception:
                pass
        return False


redis_service = RedisService()
