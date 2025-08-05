import hashlib
import json
import aioredis
from typing import Optional

class CacheService:
    def __init__(self):
        self.redis = None
        self.ttl = 3600  # 1 hora
    
    async def connect(self):
        self.redis = await aioredis.create_redis_pool(
            'redis://localhost:6379',
            encoding='utf-8'
        )
    
    async def get_response(self, message: str, level: str) -> Optional[str]:
        """Busca resposta em cache"""
        key = self._generate_key(message, level)
        cached = await self.redis.get(key)
        return json.loads(cached) if cached else None
    
    async def save_response(self, message: str, level: str, response: dict):
        """Salva resposta em cache"""
        key = self._generate_key(message, level)
        await self.redis.setex(
            key, 
            self.ttl,
            json.dumps(response)
        )
    
    def _generate_key(self, message: str, level: str) -> str:
        """Gera chave única para cache"""
        content = f"{message.lower()}:{level}"
        return f"response:{hashlib.md5(content.encode()).hexdigest()}"
