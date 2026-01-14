"""
API v1 메인 라우터
"""
from fastapi import APIRouter

from app.api.v1.query import router as query_router
from app.api.v1.system import router as system_router

# API v1 루트 라우터
api_router = APIRouter(prefix="/api/v1")

# 서브 라우터 등록
api_router.include_router(query_router)
api_router.include_router(system_router)
