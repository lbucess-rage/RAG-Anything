"""
캐시 서비스 - 3계층 캐싱 (Memory + Redis + LightRAG)
"""
import asyncio
import hashlib
import json
import time
from typing import Optional, Any, Dict
from collections import OrderedDict
from functools import wraps

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """스레드 세이프 LRU 캐시 (L1)"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        async with self._lock:
            if key in self._cache:
                # LRU: 최근 사용된 항목을 끝으로 이동
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]["value"]
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """캐시에 값 저장"""
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # 가장 오래된 항목 제거
                    self._cache.popitem(last=False)

            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }

    async def delete(self, key: str) -> bool:
        """캐시에서 키 삭제"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """전체 캐시 삭제"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """만료된 항목 정리"""
        async with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if v["expires_at"] < now
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    @property
    def stats(self) -> Dict[str, int]:
        """캐시 통계"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0,
        }


class RedisCache:
    """Redis 캐시 (L2)"""

    def __init__(self):
        self._client = None
        self._connected = False
        self.settings = get_settings()

    async def connect(self) -> bool:
        """Redis 연결"""
        try:
            import redis.asyncio as redis

            self._client = redis.Redis(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
                db=self.settings.REDIS_DB,
                password=self.settings.REDIS_PASSWORD,
                decode_responses=True,
            )

            # 연결 테스트
            await self._client.ping()
            self._connected = True
            logger.info("Redis connected successfully")
            return True

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[str]:
        """Redis에서 값 조회"""
        if not self._connected:
            return None

        try:
            value = await self._client.get(f"rag:{key}")
            return value
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Redis에 값 저장"""
        if not self._connected:
            return False

        try:
            await self._client.setex(f"rag:{key}", ttl, value)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Redis에서 키 삭제"""
        if not self._connected:
            return False

        try:
            await self._client.delete(f"rag:{key}")
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 키 삭제"""
        if not self._connected:
            return 0

        try:
            keys = await self._client.keys(f"rag:{pattern}")
            if keys:
                await self._client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis delete pattern error: {e}")
            return 0

    async def keys_count(self) -> Optional[int]:
        """키 수 조회"""
        if not self._connected:
            return None

        try:
            keys = await self._client.keys("rag:*")
            return len(keys)
        except Exception:
            return None

    @property
    def is_connected(self) -> bool:
        return self._connected


class CacheService:
    """3계층 캐시 서비스"""

    _instance: Optional["CacheService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_init_done"):
            self._init_done = True
            self.settings = get_settings()

            # L1: Memory Cache
            self.memory_cache = LRUCache(max_size=self.settings.CACHE_MAX_SIZE)

            # L2: Redis Cache
            self.redis_cache = RedisCache()

    async def initialize(self) -> None:
        """캐시 서비스 초기화"""
        await self.redis_cache.connect()
        logger.info("Cache service initialized")

    @staticmethod
    def _make_key(prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        hash_value = hashlib.md5(key_data.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회 (L1 -> L2 순서)"""
        # L1 체크
        value = await self.memory_cache.get(key)
        if value is not None:
            logger.debug(f"L1 cache hit: {key}")
            return value

        # L2 체크
        redis_value = await self.redis_cache.get(key)
        if redis_value is not None:
            logger.debug(f"L2 cache hit: {key}")
            # L1에 저장
            parsed = json.loads(redis_value)
            await self.memory_cache.set(key, parsed, ttl=self.settings.CACHE_TTL_MEMORY)
            return parsed

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_memory: Optional[int] = None,
        ttl_redis: Optional[int] = None,
    ) -> None:
        """캐시에 값 저장 (L1 + L2)"""
        ttl_memory = ttl_memory or self.settings.CACHE_TTL_MEMORY
        ttl_redis = ttl_redis or self.settings.CACHE_TTL_QUERY

        # L1 저장
        await self.memory_cache.set(key, value, ttl=ttl_memory)

        # L2 저장
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        await self.redis_cache.set(key, serialized, ttl=ttl_redis)

    async def invalidate(self, key: str) -> None:
        """캐시 무효화"""
        await self.memory_cache.delete(key)
        await self.redis_cache.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """패턴에 매칭되는 캐시 무효화"""
        # L1은 전체 삭제 (패턴 매칭 미지원)
        await self.memory_cache.clear()

        # L2 패턴 삭제
        count = await self.redis_cache.delete_pattern(pattern)
        return count

    async def clear_all(self) -> None:
        """전체 캐시 삭제"""
        await self.memory_cache.clear()
        await self.redis_cache.delete_pattern("*")
        logger.info("All cache cleared")

    @property
    def stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "memory_cache": self.memory_cache.stats,
            "redis_connected": self.redis_cache.is_connected,
        }


def get_cache_service() -> CacheService:
    """캐시 서비스 싱글톤 반환"""
    return CacheService()


def cached(
    prefix: str = "query",
    ttl_memory: int = 300,
    ttl_redis: int = 3600,
):
    """캐시 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache_service()

            # 캐시 키 생성
            key = CacheService._make_key(prefix, *args, **kwargs)

            # 캐시 조회
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value

            # 함수 실행
            result = await func(*args, **kwargs)

            # 캐시 저장
            await cache.set(key, result, ttl_memory=ttl_memory, ttl_redis=ttl_redis)

            return result

        return wrapper
    return decorator
