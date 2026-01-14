"""
API 요청 모델 정의
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

from app.models.enums import QueryMode, Urgency


class QueryRequest(BaseModel):
    """검색 쿼리 요청"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="검색 질문"
    )
    mode: QueryMode = Field(
        default=QueryMode.HYBRID,
        description="검색 모드"
    )
    stream: bool = Field(
        default=False,
        description="스트리밍 응답 여부"
    )
    top_k: int = Field(
        default=60,
        ge=1,
        le=200,
        description="검색 결과 개수"
    )
    only_need_context: bool = Field(
        default=False,
        description="컨텍스트만 반환"
    )
    only_need_prompt: bool = Field(
        default=False,
        description="프롬프트만 반환"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """쿼리 정리"""
        return v.strip()


class ConsultationRequest(BaseModel):
    """상담 질의 요청"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="상담 질문"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="세션 ID (대화 연속성)"
    )
    urgency: Urgency = Field(
        default=Urgency.NORMAL,
        description="긴급도"
    )
    category: Optional[str] = Field(
        default=None,
        description="질문 카테고리"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터"
    )


class DocumentUploadRequest(BaseModel):
    """문서 업로드 요청 메타데이터"""
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="문서 설명"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="태그 목록"
    )
    category: Optional[str] = Field(
        default=None,
        description="문서 카테고리"
    )


class BatchQueryRequest(BaseModel):
    """배치 쿼리 요청"""
    queries: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="쿼리 목록"
    )
    mode: QueryMode = Field(
        default=QueryMode.HYBRID,
        description="검색 모드"
    )


class CacheInvalidateRequest(BaseModel):
    """캐시 무효화 요청"""
    pattern: Optional[str] = Field(
        default=None,
        description="무효화할 캐시 키 패턴"
    )
    all_cache: bool = Field(
        default=False,
        description="전체 캐시 삭제"
    )
