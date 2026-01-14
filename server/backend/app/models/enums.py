"""
Enum 정의
"""
from enum import Enum


class QueryMode(str, Enum):
    """검색 모드"""
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    NAIVE = "naive"
    MIX = "mix"


class Urgency(str, Enum):
    """긴급도"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class DocumentStatus(str, Enum):
    """문서 처리 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComponentStatus(str, Enum):
    """컴포넌트 상태"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
