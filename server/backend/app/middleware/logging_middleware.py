"""
로깅 미들웨어
요청/응답 로깅 및 성능 측정
"""
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logger import get_logger, LogContext
from app.middleware.request_id import get_request_id

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """요청/응답 로깅 미들웨어"""

    # 로깅 제외 경로
    EXCLUDE_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 제외 경로 체크
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        request_id = get_request_id()
        start_time = time.time()

        # 요청 정보 로깅
        log_ctx = LogContext(logger, request_id=request_id, component="http")
        log_ctx.info(
            f"Request: {request.method} {request.url.path}",
            details={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )

        # 요청 처리
        try:
            response = await call_next(request)

            # 응답 시간 계산
            duration_ms = (time.time() - start_time) * 1000

            # 응답 로깅
            log_level = "info" if response.status_code < 400 else "warning"
            if response.status_code >= 500:
                log_level = "error"

            getattr(log_ctx, log_level)(
                f"Response: {response.status_code} ({duration_ms:.2f}ms)",
                details={
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # 응답 헤더에 처리 시간 추가
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_ctx.error(
                f"Request failed: {str(e)}",
                details={
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                },
            )
            raise


class QueryLoggingMiddleware:
    """쿼리 전용 로깅 (데코레이터용)"""

    @staticmethod
    def log_query(
        query: str,
        mode: str,
        latency_ms: float,
        success: bool = True,
        cached: bool = False,
        error: str = None,
    ) -> None:
        """쿼리 로그 기록"""
        request_id = get_request_id()
        log_ctx = LogContext(logger, request_id=request_id, component="query")

        details = {
            "query": query[:200],  # 쿼리 길이 제한
            "mode": mode,
            "latency_ms": round(latency_ms, 2),
            "cached": cached,
        }

        if success:
            log_ctx.info(f"Query completed ({latency_ms:.2f}ms)", details=details)
        else:
            details["error"] = error
            log_ctx.error(f"Query failed: {error}", details=details)
