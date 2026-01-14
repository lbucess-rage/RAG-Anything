"""
검색 API 라우터
"""
import time
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.models.request import QueryRequest, ConsultationRequest
from app.models.response import (
    QueryResponse,
    QueryResult,
    ConsultationResponse,
    ConsultationResult,
    SourceInfo,
)
from app.models.enums import QueryMode
from app.services.rag_service import get_rag_service, RAGService
from app.services.cache_service import get_cache_service, CacheService
from app.middleware.request_id import get_request_id
from app.middleware.logging_middleware import QueryLoggingMiddleware
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/query", tags=["Query"])


def get_rag() -> RAGService:
    """RAG 서비스 의존성"""
    service = get_rag_service()
    if not service.is_initialized:
        raise HTTPException(
            status_code=503,
            detail="RAG service not initialized"
        )
    return service


def get_cache() -> CacheService:
    """캐시 서비스 의존성"""
    return get_cache_service()


@router.post("/search", response_model=QueryResponse)
async def search(
    request: QueryRequest,
    rag: RAGService = Depends(get_rag),
    cache: CacheService = Depends(get_cache),
):
    """
    지식 검색 API

    - query: 검색 질문
    - mode: 검색 모드 (local, global, hybrid, naive, mix)
    - stream: 스트리밍 응답 여부
    - top_k: 검색 결과 개수
    """
    request_id = get_request_id()
    start_time = time.time()
    cached = False

    try:
        # 캐시 키 생성
        cache_key = f"query:{request.query}:{request.mode}:{request.top_k}"

        # 캐시 확인 (스트리밍이 아닌 경우만)
        if not request.stream:
            cached_result = await cache.get(cache_key)
            if cached_result:
                latency_ms = (time.time() - start_time) * 1000
                cached = True
                QueryLoggingMiddleware.log_query(
                    query=request.query,
                    mode=request.mode.value,
                    latency_ms=latency_ms,
                    cached=True,
                )
                return QueryResponse(
                    success=True,
                    data=QueryResult(
                        answer=cached_result["answer"],
                        mode=QueryMode(request.mode),
                        sources=[],
                        latency_ms=latency_ms,
                        cached=True,
                    ),
                    request_id=request_id,
                )

        # RAG 쿼리 실행
        result = await rag.query(
            query=request.query,
            mode=request.mode.value,
            top_k=request.top_k,
            only_need_context=request.only_need_context,
            only_need_prompt=request.only_need_prompt,
        )

        latency_ms = (time.time() - start_time) * 1000

        # 캐시 저장
        if not request.stream:
            await cache.set(cache_key, result)

        # 로깅
        QueryLoggingMiddleware.log_query(
            query=request.query,
            mode=request.mode.value,
            latency_ms=latency_ms,
            cached=False,
        )

        return QueryResponse(
            success=True,
            data=QueryResult(
                answer=result["answer"],
                mode=QueryMode(request.mode),
                sources=[],  # TODO: 출처 정보 추출
                context=result.get("context"),
                prompt=result.get("prompt"),
                latency_ms=latency_ms,
                cached=cached,
            ),
            request_id=request_id,
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        QueryLoggingMiddleware.log_query(
            query=request.query,
            mode=request.mode.value,
            latency_ms=latency_ms,
            success=False,
            error=str(e),
        )
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/stream")
async def search_stream(
    request: QueryRequest,
    rag: RAGService = Depends(get_rag),
):
    """
    스트리밍 검색 API

    Server-Sent Events (SSE) 형식으로 응답
    """
    request_id = get_request_id()
    start_time = time.time()

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for chunk in rag.query_stream(
                query=request.query,
                mode=request.mode.value,
                top_k=request.top_k,
            ):
                data = json.dumps({"chunk": chunk, "request_id": request_id})
                yield f"data: {data}\n\n"

            # 완료 이벤트
            latency_ms = (time.time() - start_time) * 1000
            QueryLoggingMiddleware.log_query(
                query=request.query,
                mode=request.mode.value,
                latency_ms=latency_ms,
            )
            yield f"data: {json.dumps({'done': True, 'latency_ms': latency_ms})}\n\n"

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            QueryLoggingMiddleware.log_query(
                query=request.query,
                mode=request.mode.value,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id or "",
        },
    )


@router.post("/consultation", response_model=ConsultationResponse)
async def consultation(
    request: ConsultationRequest,
    rag: RAGService = Depends(get_rag),
):
    """
    상담 질의 API

    세션 기반 대화 연속성 지원
    """
    request_id = get_request_id()
    start_time = time.time()

    try:
        # RAG 쿼리 실행
        result = await rag.query(
            query=request.query,
            mode="hybrid",
            top_k=60,
        )

        latency_ms = (time.time() - start_time) * 1000

        # 세션 ID 생성 또는 사용
        session_id = request.session_id or request_id

        return ConsultationResponse(
            success=True,
            data=ConsultationResult(
                answer=result["answer"],
                session_id=session_id,
                confidence=0.85,  # TODO: 신뢰도 계산
                sources=[],
                suggestions=[],  # TODO: 추가 질문 제안
                latency_ms=latency_ms,
            ),
            request_id=request_id,
        )

    except Exception as e:
        logger.error(f"Consultation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
