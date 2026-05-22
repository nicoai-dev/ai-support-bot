import redis.asyncio as redis
import json
from typing import Optional

class RedisCache:
    def __init__(self, url: str = "redis://localhost:6379"):
        self._redis = redis.from_url(url, decode_responses=True)
    
    async def get(self, key: str) -> Optional[str]:
        return await self._redis.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        await self._redis.set(key, value, ex=ttl)
    
    async def get_json(self, key: str) -> Optional[dict]:
        data = await self._redis.get(key)
        return json.loads(data) if data else None
    
    async def set_json(self, key: str, value: dict, ttl: int = 3600) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl)
    
    async def close(self):
        await self._redis.close()

from config import REDIS_URL
redis_cache = RedisCache(REDIS_URL)
