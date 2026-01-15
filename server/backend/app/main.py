"""
RAG-Anything API Server
- RAG-Anything: 멀티모달 문서 처리 (이미지/테이블/수식 → VLM/LLM 분석)
- LightRAG API (9621): 쿼리 프록시 (커스텀 기능 활용)
- 공유 스토리지: PostgreSQL + Neo4j
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import get_settings
from app.api.v1.router import api_router
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.services.raganything_service import get_raganything_service
from app.services.lightrag_client import get_lightrag_client
from app.services.document_service import get_document_service
from app.services.cache_service import get_cache_service
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    """
    # === Startup ===
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("Mode: RAG-Anything (multimodal) + LightRAG API (query proxy)")

    # 로깅 설정
    setup_logging()

    # 캐시 서비스 초기화
    cache_service = get_cache_service()
    await cache_service.initialize()

    # RAG-Anything 서비스 초기화 (멀티모달 문서 처리)
    raganything_service = get_raganything_service()
    try:
        await raganything_service.initialize()
        logger.info("RAG-Anything multimodal service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize RAG-Anything: {e}")
        # 서비스는 계속 실행되지만 멀티모달 기능은 비활성화

    # LightRAG API 클라이언트 초기화 (쿼리 프록시)
    lightrag_client = get_lightrag_client()
    try:
        if settings.LIGHTRAG_API_USERNAME and settings.LIGHTRAG_API_PASSWORD:
            await lightrag_client.login(
                username=settings.LIGHTRAG_API_USERNAME,
                password=settings.LIGHTRAG_API_PASSWORD,
            )
            logger.info(f"LightRAG API login successful: {settings.LIGHTRAG_API_HOST}")
        else:
            health = await lightrag_client.health_check()
            if health.get("status") != "error":
                logger.info(f"LightRAG API connection OK: {settings.LIGHTRAG_API_HOST}")
    except Exception as e:
        logger.warning(f"LightRAG API connection failed: {e}")

    # 문서 서비스 초기화
    doc_service = get_document_service()
    logger.info(f"Document storage: {doc_service.storage_path}")

    logger.info("Application startup complete")
    logger.info("=" * 50)
    logger.info("Architecture:")
    logger.info("  - Document Upload → RAG-Anything (multimodal processing)")
    logger.info("  - Query → LightRAG API (9621) proxy")
    logger.info("  - Shared Storage: PostgreSQL + Neo4j")
    logger.info("=" * 50)

    yield

    # === Shutdown ===
    logger.info("Shutting down application...")

    # RAG-Anything 서비스 종료
    try:
        await raganything_service.finalize()
    except Exception as e:
        logger.error(f"Error finalizing RAG-Anything: {e}")

    # LightRAG 클라이언트 종료
    try:
        await lightrag_client.close()
    except Exception as e:
        logger.error(f"Error closing LightRAG client: {e}")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
RAG-Anything Multimodal API Server

- **Document Processing**: RAG-Anything (MinerU parsing, VLM image analysis)
- **Query**: Custom LightRAG API proxy (9621)
- **Storage**: Shared PostgreSQL + Neo4j
        """,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # === CORS 설정 ===
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === 미들웨어 등록 ===
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # === API 라우터 등록 ===
    app.include_router(api_router)

    # === 문서 스토리지 정적 파일 마운트 ===
    storage_path = Path(settings.DOCUMENT_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/storage",
        StaticFiles(directory=str(storage_path)),
        name="document_storage",
    )

    # === 예외 핸들러 ===
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else None,
            },
        )

    # === 루트 엔드포인트 ===
    @app.get("/")
    async def root():
        raganything = get_raganything_service()
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "mode": "raganything_multimodal",
            "services": {
                "raganything": {
                    "status": "active" if raganything.is_initialized else "inactive",
                    "features": ["image_processing", "table_processing", "equation_processing"],
                },
                "lightrag_api": {
                    "host": settings.LIGHTRAG_API_HOST,
                    "role": "query_proxy",
                },
            },
            "storage": {
                "type": "shared",
                "kv": settings.LIGHTRAG_KV_STORAGE,
                "vector": settings.LIGHTRAG_VECTOR_STORAGE,
                "graph": settings.LIGHTRAG_GRAPH_STORAGE,
            },
            "docs": "/docs" if settings.DEBUG else "Disabled",
        }

    return app


# 애플리케이션 인스턴스
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level="debug" if settings.DEBUG else "info",
    )
