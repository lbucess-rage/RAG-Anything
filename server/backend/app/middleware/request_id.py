"""
Request ID 미들웨어
모든 요청에 고유 ID 부여
"""
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 요청 ID 컨텍스트 변수
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_request_id() -> Optional[str]:
    """현재 요청 ID 반환"""
    return request_id_var.get()


def generate_request_id() -> str:
    """새 요청 ID 생성"""
    return str(uuid.uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Request ID 미들웨어"""

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        # 기존 Request ID 사용 또는 새로 생성
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = generate_request_id()

        # 컨텍스트 변수에 설정
        token = request_id_var.set(request_id)

        # 요청 상태에도 저장
        request.state.request_id = request_id

        try:
            response = await call_next(request)

            # 응답 헤더에 Request ID 추가
            response.headers[self.HEADER_NAME] = request_id

            return response

        finally:
            # 컨텍스트 변수 복원
            request_id_var.reset(token)
