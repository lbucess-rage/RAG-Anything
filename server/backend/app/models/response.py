"""
API 응답 모델 정의
"""
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.enums import QueryMode, DocumentStatus, ComponentStatus

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """기본 응답 구조"""
    success: bool = Field(default=True, description="성공 여부")
    data: Optional[T] = Field(default=None, description="응답 데이터")
    error: Optional[str] = Field(default=None, description="에러 메시지")
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SourceInfo(BaseModel):
    """출처 정보"""
    document_id: str = Field(..., description="문서 ID")
    document_name: Optional[str] = Field(default=None, description="문서 이름")
    chunk_id: Optional[str] = Field(default=None, description="청크 ID")
    relevance_score: Optional[float] = Field(default=None, description="관련도 점수")
    content_preview: Optional[str] = Field(default=None, description="내용 미리보기")


class QueryResult(BaseModel):
    """검색 결과"""
    answer: str = Field(..., description="생성된 답변")
    mode: QueryMode = Field(..., description="사용된 검색 모드")
    sources: List[SourceInfo] = Field(default_factory=list, description="출처 목록")
    context: Optional[str] = Field(default=None, description="검색된 컨텍스트")
    prompt: Optional[str] = Field(default=None, description="생성된 프롬프트")
    latency_ms: float = Field(..., description="응답 시간 (ms)")
    token_usage: Optional[Dict[str, int]] = Field(default=None, description="토큰 사용량")
    cached: bool = Field(default=False, description="캐시 히트 여부")


class QueryResponse(BaseResponse[QueryResult]):
    """검색 응답"""
    pass


class ConsultationResult(BaseModel):
    """상담 결과"""
    answer: str = Field(..., description="답변")
    session_id: str = Field(..., description="세션 ID")
    confidence: float = Field(default=0.0, ge=0, le=1, description="신뢰도")
    sources: List[SourceInfo] = Field(default_factory=list, description="참고 문서")
    suggestions: List[str] = Field(default_factory=list, description="추가 질문 제안")
    latency_ms: float = Field(..., description="응답 시간")


class ConsultationResponse(BaseResponse[ConsultationResult]):
    """상담 응답"""
    pass


class DocumentInfo(BaseModel):
    """문서 정보"""
    document_id: str = Field(..., description="문서 ID")
    filename: str = Field(..., description="파일명")
    status: DocumentStatus = Field(..., description="처리 상태")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    created_at: datetime = Field(..., description="업로드 시간")
    updated_at: Optional[datetime] = Field(default=None, description="수정 시간")
    chunk_count: Optional[int] = Field(default=None, description="청크 수")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="메타데이터")


class DocumentUploadResponse(BaseResponse[DocumentInfo]):
    """문서 업로드 응답"""
    pass


class DocumentListResponse(BaseResponse[List[DocumentInfo]]):
    """문서 목록 응답"""
    total: int = Field(default=0, description="전체 문서 수")
    page: int = Field(default=1, description="현재 페이지")
    page_size: int = Field(default=20, description="페이지 크기")


class ComponentHealth(BaseModel):
    """컴포넌트 상태"""
    name: str = Field(..., description="컴포넌트 이름")
    status: ComponentStatus = Field(..., description="상태")
    latency_ms: Optional[float] = Field(default=None, description="응답 시간")
    message: Optional[str] = Field(default=None, description="상태 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")


class SystemHealth(BaseModel):
    """시스템 건강 상태"""
    status: ComponentStatus = Field(..., description="전체 상태")
    version: str = Field(..., description="API 버전")
    uptime_seconds: float = Field(..., description="가동 시간")
    components: List[ComponentHealth] = Field(default_factory=list, description="컴포넌트 상태")


class HealthResponse(BaseResponse[SystemHealth]):
    """헬스체크 응답"""
    pass


class CacheStats(BaseModel):
    """캐시 통계"""
    memory_cache_size: int = Field(default=0, description="메모리 캐시 크기")
    memory_cache_hits: int = Field(default=0, description="메모리 캐시 히트")
    memory_cache_misses: int = Field(default=0, description="메모리 캐시 미스")
    redis_connected: bool = Field(default=False, description="Redis 연결 상태")
    redis_keys_count: Optional[int] = Field(default=None, description="Redis 키 수")


class CacheStatsResponse(BaseResponse[CacheStats]):
    """캐시 통계 응답"""
    pass


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = Field(default=False)
    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(default=None, description="에러 코드")
    details: Optional[Dict[str, Any]] = Field(default=None, description="상세 정보")
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
