"""
문서 관리 API 라우터
- 문서 업로드/삭제/조회
- 중복 검사
- 파일 다운로드
"""
import os
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.services.document_service import get_document_service, DocumentService
from app.services.lightrag_client import get_lightrag_client, LightRAGClient
from app.middleware.request_id import get_request_id
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


# ===== Request/Response Models =====

class UploadOptions(BaseModel):
    """업로드 옵션"""
    replace_if_duplicate: bool = False
    replace_if_similar: bool = False


class DocumentUploadResponse(BaseModel):
    """문서 업로드 응답"""
    success: bool
    status: str
    doc_id: Optional[str] = None
    original_filename: str
    normalized_filename: str
    content_hash: str
    file_size: int
    message: Optional[str] = None
    duplicate_check: Optional[dict] = None
    replaced_doc_id: Optional[str] = None
    replaced_doc_ids: Optional[List[str]] = None
    request_id: Optional[str] = None


class DocumentListResponse(BaseModel):
    """문서 목록 응답"""
    success: bool
    total: int
    limit: int
    offset: int
    documents: List[dict]
    request_id: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """문서 상세 응답"""
    success: bool
    document: Optional[dict] = None
    request_id: Optional[str] = None


# ===== Dependencies =====

def get_doc_service() -> DocumentService:
    """문서 서비스 의존성"""
    return get_document_service()


def get_lightrag() -> LightRAGClient:
    """LightRAG 클라이언트 의존성"""
    return get_lightrag_client()


# ===== Endpoints =====

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    replace_if_duplicate: bool = Query(False, description="완전 중복시 대체 여부"),
    replace_if_similar: bool = Query(False, description="유사 파일 발견시 대체 여부"),
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    문서 업로드

    - 중복 검사 수행 (Content Hash + Filename Pattern)
    - replace_if_duplicate: 완전히 동일한 파일 발견시 대체
    - replace_if_similar: 유사한 파일명 발견시 대체
    """
    request_id = get_request_id()

    try:
        # 파일 읽기
        content = await file.read()
        filename = file.filename or "unnamed_file"

        # 업로드 처리
        result = await doc_service.upload_document(
            filename=filename,
            content=content,
            replace_if_duplicate=replace_if_duplicate,
            replace_if_similar=replace_if_similar,
        )

        return DocumentUploadResponse(
            success=True,
            status=result["status"],
            doc_id=result.get("doc_id"),
            original_filename=result["original_filename"],
            normalized_filename=result["normalized_filename"],
            content_hash=result["content_hash"],
            file_size=result["file_size"],
            message=result.get("message"),
            duplicate_check=result.get("duplicate_check"),
            replaced_doc_id=result.get("replaced_doc_id"),
            replaced_doc_ids=result.get("replaced_doc_ids"),
            request_id=request_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/confirm")
async def confirm_upload(
    file: UploadFile = File(...),
    action: str = Query(..., description="confirm_replace 또는 cancel"),
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    중복/유사 파일 발견 후 확인 업로드

    - action=confirm_replace: 기존 파일 대체 후 업로드
    - action=cancel: 업로드 취소
    """
    request_id = get_request_id()

    if action == "cancel":
        return {"success": True, "status": "cancelled", "request_id": request_id}

    if action != "confirm_replace":
        raise HTTPException(status_code=400, detail="Invalid action. Use 'confirm_replace' or 'cancel'")

    try:
        content = await file.read()
        filename = file.filename or "unnamed_file"

        result = await doc_service.upload_document(
            filename=filename,
            content=content,
            replace_if_duplicate=True,
            replace_if_similar=True,
        )

        return {
            "success": True,
            **result,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Confirm upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="파일명 검색"),
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    문서 목록 조회
    """
    request_id = get_request_id()

    result = doc_service.list_documents(
        limit=limit,
        offset=offset,
        search=search,
    )

    return DocumentListResponse(
        success=True,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
        documents=result["documents"],
        request_id=request_id,
    )


@router.get("/lightrag")
async def list_lightrag_documents(
    status: Optional[str] = Query(None, description="문서 상태 필터"),
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    LightRAG 문서 목록 조회 (프록시)
    """
    request_id = get_request_id()

    try:
        result = await doc_service.get_lightrag_documents(status=status)
        return {
            "success": True,
            "data": result,
            "request_id": request_id,
        }
    except Exception as e:
        logger.error(f"LightRAG documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    문서 상세 조회
    """
    request_id = get_request_id()

    doc = doc_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        success=True,
        document=doc,
        request_id=request_id,
    )


@router.get("/files/{doc_id}")
async def download_file(
    doc_id: str,
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    문서 파일 다운로드
    """
    file_path = doc_service.get_file_path(doc_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    doc = doc_service.get_document(doc_id)
    filename = doc.get("original_filename", "file") if doc else "file"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    문서 삭제

    로컬 파일 및 LightRAG에서 모두 삭제
    """
    request_id = get_request_id()

    try:
        result = await doc_service.delete_document(doc_id)
        return {
            "success": True,
            **result,
            "request_id": request_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-duplicate")
async def check_duplicate(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_doc_service),
):
    """
    중복 검사만 수행 (업로드 없음)

    업로드 전 미리 중복 여부 확인
    """
    request_id = get_request_id()

    try:
        content = await file.read()
        filename = file.filename or "unnamed_file"

        content_hash, exact_duplicate, similar_files = doc_service.check_duplicate(
            content=content,
            filename=filename,
        )

        normalized_name = doc_service.normalize_filename(filename)

        return {
            "success": True,
            "original_filename": filename,
            "normalized_filename": normalized_name,
            "content_hash": content_hash,
            "file_size": len(content),
            "exact_duplicate": exact_duplicate,
            "similar_files": similar_files,
            "has_duplicate": exact_duplicate is not None,
            "has_similar": len(similar_files) > 0,
            "request_id": request_id,
        }

    except Exception as e:
        logger.error(f"Check duplicate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/text")
async def insert_text(
    text: str = Query(..., description="삽입할 텍스트"),
    file_source: str = Query("", description="출처 정보"),
    lightrag: LightRAGClient = Depends(get_lightrag),
):
    """
    텍스트 직접 삽입 (LightRAG 프록시)
    """
    request_id = get_request_id()

    try:
        result = await lightrag.insert_text(text=text, file_source=file_source)
        return {
            "success": True,
            **result,
            "request_id": request_id,
        }
    except Exception as e:
        logger.error(f"Insert text error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
