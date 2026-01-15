"""
지식 그래프 API 라우터 - LightRAG API 프록시
"""
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.services.lightrag_client import get_lightrag_client, LightRAGClient
from app.middleware.request_id import get_request_id
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/graph", tags=["Graph"])


# ===== Request Models =====

class EntityCreateRequest(BaseModel):
    """엔티티 생성 요청"""
    entity_name: str
    entity_data: Dict[str, Any]


class EntityEditRequest(BaseModel):
    """엔티티 수정 요청"""
    entity_name: str
    updated_data: Dict[str, Any]
    allow_rename: bool = False
    allow_merge: bool = False


# ===== Dependencies =====

def get_lightrag() -> LightRAGClient:
    """LightRAG 클라이언트 의존성"""
    return get_lightrag_client()


# ===== Endpoints =====

@router.get("")
async def get_graph(
    label: str = Query(..., description="시작 노드 레이블"),
    max_depth: int = Query(3, ge=1, le=10, description="탐색 깊이"),
    max_nodes: int = Query(1000, ge=1, le=10000, description="최대 노드 수"),
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    지식 그래프 조회

    특정 레이블에서 시작하여 연결된 그래프 반환
    """
    request_id = get_request_id()

    try:
        result = await lightrag.get_graph(
            label=label,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )

        return {
            "success": True,
            "data": result,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Get graph error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels")
async def get_labels(
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    그래프 레이블 목록 조회
    """
    request_id = get_request_id()

    try:
        result = await lightrag.get_graph_labels()

        return {
            "success": True,
            "labels": result,
            "total": len(result),
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Get labels error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/labels/search")
async def search_labels(
    q: str = Query(..., description="검색어"),
    limit: int = Query(50, ge=1, le=500),
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    그래프 레이블 검색
    """
    request_id = get_request_id()

    try:
        result = await lightrag.search_graph_labels(
            query=q,
            limit=limit,
        )

        return {
            "success": True,
            "labels": result,
            "total": len(result),
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Search labels error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entity")
async def create_entity(
    request: EntityCreateRequest,
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    엔티티 생성
    """
    request_id = get_request_id()

    try:
        result = await lightrag.create_entity(
            entity_name=request.entity_name,
            entity_data=request.entity_data,
        )

        return {
            "success": True,
            "data": result,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Create entity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/entity")
async def edit_entity(
    request: EntityEditRequest,
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    엔티티 수정
    """
    request_id = get_request_id()

    try:
        result = await lightrag.edit_entity(
            entity_name=request.entity_name,
            updated_data=request.updated_data,
            allow_rename=request.allow_rename,
            allow_merge=request.allow_merge,
        )

        return {
            "success": True,
            "data": result,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Edit entity error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
