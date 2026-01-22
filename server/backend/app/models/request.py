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
        description="검색 결과 개수 (엔티티/관계)"
    )
    only_need_context: bool = Field(
        default=False,
        description="컨텍스트만 반환"
    )
    only_need_prompt: bool = Field(
        default=False,
        description="프롬프트만 반환"
    )
    # 프롬프팅 관련 파라미터
    user_prompt: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="사용자 정의 프롬프트 (기본 템플릿 대신 사용)"
    )
    response_type: Optional[str] = Field(
        default=None,
        description="응답 형식: 'Multiple Paragraphs', 'Single Paragraph', 'Bullet Points'"
    )
    hl_keywords: Optional[List[str]] = Field(
        default=None,
        description="고수준 키워드 (검색 우선순위)"
    )
    ll_keywords: Optional[List[str]] = Field(
        default=None,
        description="저수준 키워드 (검색 세분화)"
    )
    # 검색/토큰 제어 파라미터
    chunk_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=500,
        description="벡터 검색에서 가져올 텍스트 청크 수"
    )
    max_token_for_text_unit: Optional[int] = Field(
        default=None,
        ge=100,
        le=10000,
        description="텍스트 유닛 최대 토큰"
    )
    max_token_for_global_context: Optional[int] = Field(
        default=None,
        ge=100,
        le=10000,
        description="글로벌 컨텍스트 최대 토큰"
    )
    max_token_for_local_context: Optional[int] = Field(
        default=None,
        ge=100,
        le=10000,
        description="로컬 컨텍스트 최대 토큰"
    )
    enable_rerank: Optional[bool] = Field(
        default=None,
        description="리랭킹 활성화 여부"
    )
    include_references: bool = Field(
        default=True,
        description="참조 목록 포함 여부"
    )
    include_chunk_content: bool = Field(
        default=False,
        description="청크 내용 포함 여부"
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
