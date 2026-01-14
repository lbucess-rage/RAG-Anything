"""
시스템 API 라우터
헬스체크, 메트릭스, 캐시 관리
"""
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from app.config import get_settings
from app.models.response import (
    HealthResponse,
    SystemHealth,
    ComponentHealth,
    CacheStatsResponse,
    CacheStats,
    BaseResponse,
)
from app.models.enums import ComponentStatus
from app.services.rag_service import get_rag_service, RAGService
from app.services.cache_service import get_cache_service, CacheService
from app.middleware.request_id import get_request_id
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["System"])

settings = get_settings()
_start_time = time.time()


def get_rag() -> RAGService:
    """RAG 서비스 의존성"""
    return get_rag_service()


def get_cache() -> CacheService:
    """캐시 서비스 의존성"""
    return get_cache_service()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    rag: RAGService = Depends(get_rag),
    cache: CacheService = Depends(get_cache),
):
    """
    시스템 상태 확인

    전체 시스템 및 각 컴포넌트의 상태를 반환
    """
    request_id = get_request_id()
    components = []

    # RAG 서비스 상태
    rag_status = ComponentStatus.HEALTHY if rag.is_initialized else ComponentStatus.UNHEALTHY
    components.append(ComponentHealth(
        name="rag_service",
        status=rag_status,
        message="Initialized" if rag.is_initialized else "Not initialized",
    ))

    # 캐시 서비스 상태
    cache_stats = cache.stats
    redis_status = ComponentStatus.HEALTHY if cache_stats["redis_connected"] else ComponentStatus.DEGRADED
    components.append(ComponentHealth(
        name="cache_service",
        status=redis_status,
        message="Redis connected" if cache_stats["redis_connected"] else "Redis disconnected (memory only)",
        details=cache_stats["memory_cache"],
    ))

    # PostgreSQL 상태 체크 (간략화)
    try:
        # TODO: 실제 PostgreSQL 연결 체크
        components.append(ComponentHealth(
            name="postgresql",
            status=ComponentStatus.HEALTHY,
            message="Connection available",
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="postgresql",
            status=ComponentStatus.UNHEALTHY,
            message=str(e),
        ))

    # Neo4j 상태 체크 (간략화)
    try:
        # TODO: 실제 Neo4j 연결 체크
        components.append(ComponentHealth(
            name="neo4j",
            status=ComponentStatus.HEALTHY,
            message="Connection available",
        ))
    except Exception as e:
        components.append(ComponentHealth(
            name="neo4j",
            status=ComponentStatus.UNHEALTHY,
            message=str(e),
        ))

    # 전체 상태 결정
    unhealthy_count = sum(1 for c in components if c.status == ComponentStatus.UNHEALTHY)
    degraded_count = sum(1 for c in components if c.status == ComponentStatus.DEGRADED)

    if unhealthy_count > 0:
        overall_status = ComponentStatus.UNHEALTHY
    elif degraded_count > 0:
        overall_status = ComponentStatus.DEGRADED
    else:
        overall_status = ComponentStatus.HEALTHY

    return HealthResponse(
        success=True,
        data=SystemHealth(
            status=overall_status,
            version=settings.APP_VERSION,
            uptime_seconds=time.time() - _start_time,
            components=components,
        ),
        request_id=request_id,
    )


@router.get("/health/ready")
async def readiness_check(rag: RAGService = Depends(get_rag)):
    """
    준비 상태 확인 (Kubernetes readiness probe용)
    """
    if not rag.is_initialized:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    """
    생존 상태 확인 (Kubernetes liveness probe용)
    """
    return {"status": "alive"}


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(cache: CacheService = Depends(get_cache)):
    """
    캐시 통계 조회
    """
    request_id = get_request_id()
    stats = cache.stats

    return CacheStatsResponse(
        success=True,
        data=CacheStats(
            memory_cache_size=stats["memory_cache"]["size"],
            memory_cache_hits=stats["memory_cache"]["hits"],
            memory_cache_misses=stats["memory_cache"]["misses"],
            redis_connected=stats["redis_connected"],
            redis_keys_count=await cache.redis_cache.keys_count() if stats["redis_connected"] else None,
        ),
        request_id=request_id,
    )


@router.delete("/cache")
async def clear_cache(
    pattern: str = None,
    cache: CacheService = Depends(get_cache),
):
    """
    캐시 삭제

    - pattern: 삭제할 키 패턴 (미지정 시 전체 삭제)
    """
    request_id = get_request_id()

    if pattern:
        count = await cache.invalidate_pattern(pattern)
        message = f"Invalidated {count} keys matching '{pattern}'"
    else:
        await cache.clear_all()
        message = "All cache cleared"

    logger.info(f"Cache cleared: {message}")

    return BaseResponse(
        success=True,
        data={"message": message},
        request_id=request_id,
    )


@router.get("/info")
async def get_system_info():
    """
    시스템 정보 조회
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "uptime_seconds": time.time() - _start_time,
        "settings": {
            "llm_model": settings.LLM_MODEL,
            "vlm_model": settings.VLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "working_dir": settings.WORKING_DIR,
        },
    }
