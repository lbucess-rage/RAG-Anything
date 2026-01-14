"""
RAG-Anything API Server
FastAPI 애플리케이션 메인 엔트리포인트
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
from app.services.rag_service import get_rag_service
from app.services.cache_service import get_cache_service
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    startup/shutdown 이벤트 처리
    """
    # === Startup ===
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 로깅 설정
    setup_logging()

    # 캐시 서비스 초기화
    cache_service = get_cache_service()
    await cache_service.initialize()

    # RAG 서비스 초기화
    rag_service = get_rag_service()
    try:
        await rag_service.initialize()
        logger.info("RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")
        # 서비스는 계속 실행되지만 RAG 기능은 비활성화됨

    logger.info("Application startup complete")

    yield

    # === Shutdown ===
    logger.info("Shutting down application...")

    # RAG 서비스 정리
    try:
        await rag_service.finalize()
    except Exception as e:
        logger.error(f"Error finalizing RAG service: {e}")

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """FastAPI 애플리케이션 팩토리"""

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="RAG-Anything based Knowledge Search API",
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

    # === 미들웨어 등록 (역순으로 실행됨) ===
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # === API 라우터 등록 ===
    app.include_router(api_router)

    # === 예외 핸들러 ===
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """전역 예외 핸들러"""
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
        """API 루트"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "Disabled in production",
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
