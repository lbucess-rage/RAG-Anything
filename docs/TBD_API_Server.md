# RAG-Anything API 서버 기술 설계 문서 (TBD)

**문서 버전**: 2.0
**작성일**: 2024-01-13
**상태**: In Progress
**Skill**: `.claude/skills/rag-api-server-generator`

---

## 1. 개요

### 1.1 목적
컨택센터 상담사 및 관리자를 위한 지식 검색 및 상담 지원 API 서버 구축

### 1.2 주요 사용자
| 사용자 | 역할 | 주요 기능 |
|--------|------|----------|
| 상담사 | 고객 문의 대응 | 지식 검색, 상담 스크립트 조회, 유사 사례 검색 |
| 관리자 | 시스템 운영 | 문서 관리, 시스템 모니터링, 로그 확인 |
| 외부 시스템 | API 연동 | REST API 호출을 통한 지식 검색 |

### 1.3 핵심 요구사항
| 구분 | 요구사항 | 상세 |
|------|----------|------|
| 기능 | 멀티모달 문서 처리 | PDF, 이미지, 테이블 자동 분석 |
| 기능 | 지식 검색 | hybrid/local/global 검색 모드 |
| 기능 | 상담 지원 | 스크립트 추천, 유사 사례, 참조 문서 |
| 성능 | 응답 지연시간 | 캐시 히트 <100ms, 일반 <2초 |
| 성능 | 동시 사용자 | 50+ 동시 요청 처리 |
| 테스트 | Web UI | API 테스트, 로그 뷰어, 대시보드 |
| 운영 | 모니터링 | 실시간 로그, 헬스체크, 메트릭 |

### 1.4 기술 스택 (확정)
| 구분 | 기술 | 버전 |
|------|------|------|
| Backend Framework | FastAPI | 0.115+ |
| Frontend Framework | React + Vite | React 19, Vite 6 |
| UI Library | Tailwind CSS + shadcn/ui | Tailwind 3 |
| 스토리지 | PostgreSQL + Neo4j | 기존 인프라 활용 |
| 캐시 | Redis | 7.x |
| RAG Core | RAG-Anything + LightRAG | 현재 프로젝트 |

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              클라이언트 계층                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  컨택센터 시스템  │  │  관리자 시스템   │  │  테스트 Web UI (React)       │  │
│  │  (REST API)     │  │  (REST API)     │  │  - Dashboard                │  │
│  │                 │  │                 │  │  - Query Tester             │  │
│  │                 │  │                 │  │  - Log Viewer               │  │
│  │                 │  │                 │  │  - Document Manager         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API Gateway (FastAPI)                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐ │
│  │   CORS      │ │  Logging    │ │ Rate Limit  │ │  Request Tracking     │ │
│  │ Middleware  │ │ Middleware  │ │ Middleware  │ │  (request_id 발급)    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Routers (v1)                            │   │
│  │  /query  │  /document  │  /consultation  │  /system                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              서비스 계층                                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐   │
│  │  RAGService     │ │  QueryService   │ │  ConsultationService        │   │
│  │  (싱글톤)       │ │  (쿼리 처리)    │ │  (상담 지원)                 │   │
│  │                 │ │                 │ │  - 스크립트 생성             │   │
│  │  RAG-Anything   │ │  - 캐시 조회    │ │  - 유사 사례 검색            │   │
│  │  인스턴스 관리  │ │  - 모드별 쿼리  │ │  - 컨텍스트 처리             │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐   │
│  │ DocumentService │ │  CacheService   │ │  LogService                 │   │
│  │ (문서 처리)     │ │  (3단계 캐시)   │ │  (로그 관리)                 │   │
│  │                 │ │  L1: Memory     │ │  - 구조화 로깅               │   │
│  │  - 업로드       │ │  L2: Redis      │ │  - SSE 스트리밍              │   │
│  │  - 상태 관리    │ │  L3: LightRAG   │ │  - 파일 롤링                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         인프라 계층 (10.62.130.84)                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐ │
│  │    LLM    │ │    VLM    │ │ Embedding │ │  Reranker │ │    Redis      │ │
│  │  :18002   │ │  :18006   │ │  :19006   │ │  :19003   │ │   :6379       │ │
│  │lbu-slm-v3│ │qwen3-vl-8b│ │ bge-m3    │ │bge-rerank │ │               │ │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────────┘ │
│  ┌─────────────────────────┐ ┌─────────────────────────────────────────┐   │
│  │      PostgreSQL         │ │              Neo4j                      │   │
│  │        :5432            │ │             :7687                       │   │
│  │  - PGKVStorage          │ │  - Neo4JStorage                         │   │
│  │  - PGVectorStorage      │ │  - 지식 그래프 (15,000+ 노드)           │   │
│  │  - PGDocStatusStorage   │ │                                         │   │
│  └─────────────────────────┘ └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 디렉토리 구조 (확정)

```
rag-api-server/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 앱 진입점
│   │   ├── config.py                  # 환경설정 (Pydantic Settings)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py                # 의존성 주입 (get_rag, get_cache 등)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py          # 라우터 통합
│   │   │       ├── query.py           # 질의 API
│   │   │       ├── document.py        # 문서 관리 API
│   │   │       ├── consultation.py    # 상담 지원 API
│   │   │       └── system.py          # 시스템 API
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── rag_service.py         # RAG-Anything 싱글톤 관리
│   │   │   ├── query_service.py       # 쿼리 처리 로직
│   │   │   ├── document_service.py    # 문서 처리 로직
│   │   │   ├── consultation_service.py # 상담 지원 로직
│   │   │   ├── cache_service.py       # 캐시 관리
│   │   │   └── log_service.py         # 로그 관리
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── request.py             # 요청 모델
│   │   │   ├── response.py            # 응답 모델
│   │   │   └── enums.py               # Enum 정의
│   │   │
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── logging.py             # 요청/응답 로깅
│   │   │   ├── request_id.py          # Request ID 발급
│   │   │   └── rate_limit.py          # 속도 제한
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py              # 로거 설정
│   │       └── helpers.py             # 유틸리티 함수
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # pytest 설정
│   │   ├── test_query.py
│   │   ├── test_document.py
│   │   └── test_consultation.py
│   │
│   ├── logs/                          # 로그 디렉토리
│   ├── uploads/                       # 업로드 임시 디렉토리
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # 메인 앱
│   │   ├── main.jsx                   # 진입점
│   │   ├── index.css                  # 글로벌 스타일
│   │   │
│   │   ├── components/
│   │   │   ├── Layout.jsx             # 레이아웃 (사이드바 + 콘텐츠)
│   │   │   ├── Sidebar.jsx            # 사이드바 메뉴
│   │   │   ├── Dashboard.jsx          # 대시보드
│   │   │   ├── QueryTester.jsx        # 쿼리 테스터
│   │   │   ├── LogViewer.jsx          # 로그 뷰어
│   │   │   ├── DocumentManager.jsx    # 문서 관리
│   │   │   ├── ConsultationSim.jsx    # 상담 시뮬레이터
│   │   │   └── ui/                    # shadcn/ui 컴포넌트
│   │   │       ├── button.jsx
│   │   │       ├── card.jsx
│   │   │       ├── input.jsx
│   │   │       ├── select.jsx
│   │   │       ├── textarea.jsx
│   │   │       └── badge.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useApi.js              # API 호출 훅
│   │   │   ├── useSSE.js              # SSE 연결 훅
│   │   │   └── useHealth.js           # 헬스체크 훅
│   │   │
│   │   ├── lib/
│   │   │   ├── utils.js               # 유틸리티 (cn 함수 등)
│   │   │   └── api.js                 # Axios 인스턴스
│   │   │
│   │   └── pages/                     # 페이지 (라우팅 시)
│   │
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 3. 백엔드 상세 설계

### 3.1 환경설정 (config.py)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 앱 설정
    APP_NAME: str = "RAG-Anything API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # RAG-Anything
    WORKING_DIR: str = "./rag_storage"
    PARSER: str = "mineru"
    ENABLE_IMAGE_PROCESSING: bool = True
    ENABLE_TABLE_PROCESSING: bool = True

    # LLM
    LLM_MODEL: str = "lbu-slm-v3-qw-max"
    LLM_BINDING_HOST: str = "http://10.62.130.84:18002/v1"
    LLM_BINDING_API_KEY: str = "EMPTY"

    # VLM
    VLM_MODEL: str = "qwen3-vl-8b"
    VLM_BINDING_HOST: str = "http://10.62.130.84:18006/v1"
    VLM_BINDING_API_KEY: str = "EMPTY"

    # Embedding
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_BINDING_HOST: str = "http://10.62.130.84:19006"

    # Storage
    LIGHTRAG_KV_STORAGE: str = "PGKVStorage"
    LIGHTRAG_VECTOR_STORAGE: str = "PGVectorStorage"
    LIGHTRAG_DOC_STATUS_STORAGE: str = "PGDocStatusStorage"
    LIGHTRAG_GRAPH_STORAGE: str = "Neo4JStorage"

    # PostgreSQL
    POSTGRES_HOST: str = "10.62.130.84"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "lightrag"
    POSTGRES_PASSWORD: str = "lightrag_secure_2024"
    POSTGRES_DATABASE: str = "lightrag"

    # Neo4j
    NEO4J_URI: str = "neo4j://10.62.130.84:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_secure_2024"

    # Redis
    REDIS_HOST: str = "10.62.130.84"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # Cache TTL (seconds)
    CACHE_TTL_QUERY: int = 3600      # 1시간
    CACHE_TTL_METADATA: int = 86400  # 24시간
    CACHE_TTL_MEMORY: int = 300      # 5분

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"

    # Rate Limiting
    RATE_LIMIT_READ: int = 100       # req/min
    RATE_LIMIT_WRITE: int = 20       # req/min

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### 3.2 Pydantic 모델 정의

#### 3.2.1 요청 모델 (request.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class QueryMode(str, Enum):
    LOCAL = "local"
    GLOBAL = "global"
    HYBRID = "hybrid"
    NAIVE = "naive"
    MIX = "mix"

class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

# 질의 요청
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="질문 내용")
    mode: QueryMode = Field(default=QueryMode.HYBRID, description="검색 모드")
    top_k: int = Field(default=10, ge=1, le=50, description="최대 결과 수")

# 상담 질의 요청
class ConsultationContext(BaseModel):
    customer_type: str = Field(default="일반", description="고객 유형")
    service_type: str = Field(default="", description="서비스 유형 (예: 반값택배)")
    previous_queries: List[str] = Field(default=[], description="이전 질의 (멀티턴)")
    urgency: Urgency = Field(default=Urgency.NORMAL, description="긴급도")

class ConsultationOptions(BaseModel):
    include_script: bool = Field(default=True, description="상담 스크립트 포함")
    include_references: bool = Field(default=True, description="참조 문서 포함")
    include_similar_cases: bool = Field(default=False, description="유사 사례 포함")
    max_results: int = Field(default=3, ge=1, le=10, description="최대 결과 수")

class ConsultationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    context: ConsultationContext = Field(default_factory=ConsultationContext)
    options: ConsultationOptions = Field(default_factory=ConsultationOptions)
    mode: QueryMode = Field(default=QueryMode.HYBRID)

# 문서 업로드 요청 (메타데이터)
class DocumentUploadMeta(BaseModel):
    title: str | None = Field(default=None, description="문서 제목")
    category: str | None = Field(default=None, description="문서 카테고리")
    tags: List[str] = Field(default=[], description="태그")
```

#### 3.2.2 응답 모델 (response.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 기본 응답
class BaseResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 질의 응답
class QueryResponse(BaseResponse):
    query: str
    answer: str
    mode: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

# 상담 스크립트
class ConsultationScript(BaseModel):
    greeting: str = Field(description="인사말")
    main_response: str = Field(description="본문 응답")
    closing: str = Field(description="마무리 멘트")

# 참조 문서
class Reference(BaseModel):
    doc_id: str
    title: str
    relevance_score: float
    excerpt: str

# 유사 사례
class SimilarCase(BaseModel):
    case_id: str
    summary: str
    resolution: str

# 상담 응답 메타데이터
class ConsultationMetadata(BaseModel):
    query_id: str
    response_time_ms: int
    mode: str
    confidence: float
    cache_hit: bool = False

# 상담 응답
class ConsultationResponse(BaseResponse):
    query: str
    answer: str
    script: ConsultationScript | None = None
    references: List[Reference] = []
    similar_cases: List[SimilarCase] = []
    metadata: ConsultationMetadata

# 문서 상태
class DocumentStatus(BaseModel):
    doc_id: str
    filename: str
    status: str  # pending, processing, completed, failed
    progress: int = 0  # 0-100
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

# 문서 목록 응답
class DocumentListResponse(BaseResponse):
    documents: List[DocumentStatus]
    total: int
    page: int
    page_size: int

# 헬스체크 응답
class ComponentHealth(BaseModel):
    status: str  # healthy, unhealthy, degraded
    latency_ms: int
    details: Dict[str, Any] = {}

class HealthResponse(BaseResponse):
    status: str
    uptime_seconds: int
    components: Dict[str, ComponentHealth]
    metrics: Dict[str, Any] = {}

# 로그 항목
class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    component: str
    message: str
    request_id: str | None = None
    details: Dict[str, Any] = {}
```

### 3.3 서비스 클래스 상세

#### 3.3.1 RAG Service (rag_service.py)

```python
from typing import Optional
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class RAGService:
    """RAG-Anything 싱글톤 관리"""

    _instance: Optional[RAGAnything] = None
    _initialized: bool = False

    @classmethod
    async def get_instance(cls) -> RAGAnything:
        if cls._instance is None:
            await cls._initialize()
        return cls._instance

    @classmethod
    async def _initialize(cls):
        settings = get_settings()
        logger.info("Initializing RAG-Anything instance...")

        # LLM 함수
        async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return await openai_complete_if_cache(
                model=settings.LLM_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                base_url=settings.LLM_BINDING_HOST,
                api_key=settings.LLM_BINDING_API_KEY,
                **kwargs
            )

        # VLM 함수
        async def vision_func(prompt, system_prompt=None, history_messages=[],
                             image_data=None, messages=None, **kwargs):
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                base_url=settings.VLM_BINDING_HOST,
                api_key=settings.VLM_BINDING_API_KEY
            )
            try:
                if messages:
                    response = await client.chat.completions.create(
                        model=settings.VLM_MODEL,
                        messages=messages,
                        max_tokens=kwargs.get("max_tokens", 500),
                    )
                    return response.choices[0].message.content
                elif image_data:
                    msg_content = [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                    messages_list = []
                    if system_prompt:
                        messages_list.append({"role": "system", "content": system_prompt})
                    messages_list.append({"role": "user", "content": msg_content})
                    response = await client.chat.completions.create(
                        model=settings.VLM_MODEL,
                        messages=messages_list,
                        max_tokens=kwargs.get("max_tokens", 500),
                    )
                    return response.choices[0].message.content
                else:
                    return await llm_func(prompt, system_prompt, history_messages, **kwargs)
            finally:
                await client.close()

        # Embedding 함수
        embedding_func = EmbeddingFunc(
            embedding_dim=settings.EMBEDDING_DIM,
            max_token_size=8192,
            func=lambda texts: openai_embed(
                texts,
                model=settings.EMBEDDING_MODEL,
                base_url=settings.EMBEDDING_BINDING_HOST,
                api_key="EMPTY",
            )
        )

        # RAG-Anything 설정
        config = RAGAnythingConfig(
            working_dir=settings.WORKING_DIR,
            parser=settings.PARSER,
            enable_image_processing=settings.ENABLE_IMAGE_PROCESSING,
            enable_table_processing=settings.ENABLE_TABLE_PROCESSING,
        )

        # 인스턴스 생성
        cls._instance = RAGAnything(
            config=config,
            llm_model_func=llm_func,
            vision_model_func=vision_func,
            embedding_func=embedding_func,
            lightrag_kwargs={
                "kv_storage": settings.LIGHTRAG_KV_STORAGE,
                "vector_storage": settings.LIGHTRAG_VECTOR_STORAGE,
                "doc_status_storage": settings.LIGHTRAG_DOC_STATUS_STORAGE,
                "graph_storage": settings.LIGHTRAG_GRAPH_STORAGE,
            }
        )

        # 스토리지 초기화
        await cls._instance._ensure_lightrag_initialized()
        cls._initialized = True
        logger.info("RAG-Anything initialized successfully")

    @classmethod
    async def close(cls):
        if cls._instance:
            await cls._instance.finalize_storages()
            cls._instance = None
            cls._initialized = False
            logger.info("RAG-Anything closed")
```

#### 3.3.2 Consultation Service (consultation_service.py)

```python
from typing import Optional
from app.models.request import ConsultationRequest, QueryMode
from app.models.response import (
    ConsultationResponse, ConsultationScript, Reference,
    SimilarCase, ConsultationMetadata
)
from app.services.rag_service import RAGService
from app.services.cache_service import CacheService
import time
import uuid
import logging

logger = logging.getLogger(__name__)

class ConsultationService:
    """상담 지원 서비스"""

    # 상담 스크립트 템플릿
    SCRIPT_TEMPLATES = {
        "greeting": {
            "default": "안녕하세요, {service_type} 관련 문의 도와드리겠습니다.",
            "complaint": "고객님, 불편을 드려 대단히 죄송합니다.",
            "inquiry": "네, {service_type} 관련하여 안내 드리겠습니다.",
        },
        "closing": {
            "default": "추가로 궁금하신 점이 있으시면 말씀해 주세요.",
            "resolved": "문제가 해결되셨길 바랍니다. 다른 문의사항 있으시면 연락 주세요.",
            "escalate": "담당 부서에서 확인 후 연락드리겠습니다.",
        }
    }

    @classmethod
    async def ask(cls, request: ConsultationRequest) -> ConsultationResponse:
        start_time = time.time()
        query_id = str(uuid.uuid4())[:8]

        # 캐시 확인
        cache_key = cls._build_cache_key(request)
        cached = await CacheService.get(cache_key)
        if cached:
            logger.info(f"Cache hit for consultation query: {query_id}")
            cached["metadata"]["cache_hit"] = True
            return ConsultationResponse(**cached)

        # RAG 인스턴스
        rag = await RAGService.get_instance()

        # 컨텍스트 기반 프롬프트 구성
        enhanced_query = cls._build_enhanced_query(request)

        # RAG 쿼리 실행
        answer = await rag.aquery(enhanced_query, mode=request.mode.value)

        # 스크립트 생성
        script = None
        if request.options.include_script:
            script = cls._generate_script(request, answer)

        # 참조 문서 (TODO: LightRAG에서 추출)
        references = []
        if request.options.include_references:
            references = cls._extract_references(answer)

        # 유사 사례 (TODO: 별도 검색)
        similar_cases = []
        if request.options.include_similar_cases:
            similar_cases = await cls._find_similar_cases(request.query)

        # 응답 생성
        response_time = int((time.time() - start_time) * 1000)

        response = ConsultationResponse(
            query=request.query,
            answer=answer,
            script=script,
            references=references,
            similar_cases=similar_cases,
            metadata=ConsultationMetadata(
                query_id=query_id,
                response_time_ms=response_time,
                mode=request.mode.value,
                confidence=0.85,  # TODO: 실제 confidence 계산
                cache_hit=False
            )
        )

        # 캐시 저장
        await CacheService.set(cache_key, response.model_dump(), ttl=3600)

        return response

    @classmethod
    def _build_enhanced_query(cls, request: ConsultationRequest) -> str:
        """컨텍스트 기반 쿼리 강화"""
        parts = [request.query]

        ctx = request.context
        if ctx.service_type:
            parts.append(f"서비스 유형: {ctx.service_type}")
        if ctx.customer_type:
            parts.append(f"고객 유형: {ctx.customer_type}")
        if ctx.previous_queries:
            parts.append(f"이전 문의: {', '.join(ctx.previous_queries[-3:])}")

        return "\n".join(parts)

    @classmethod
    def _generate_script(cls, request: ConsultationRequest, answer: str) -> ConsultationScript:
        """상담 스크립트 생성"""
        service_type = request.context.service_type or "서비스"

        # 인사말 선택
        greeting_type = "default"
        if any(kw in request.query for kw in ["불만", "화나", "문제", "안되"]):
            greeting_type = "complaint"

        greeting = cls.SCRIPT_TEMPLATES["greeting"][greeting_type].format(
            service_type=service_type
        )

        # 마무리 선택
        closing_type = "default"
        if any(kw in answer for kw in ["확인 후", "담당자", "연락드리"]):
            closing_type = "escalate"

        closing = cls.SCRIPT_TEMPLATES["closing"][closing_type]

        return ConsultationScript(
            greeting=greeting,
            main_response=answer[:1000],  # 본문 제한
            closing=closing
        )

    @classmethod
    def _extract_references(cls, answer: str) -> list[Reference]:
        """응답에서 참조 문서 추출"""
        # TODO: LightRAG 응답에서 실제 참조 추출
        references = []

        # 간단한 패턴 매칭 (실제 구현 시 개선 필요)
        if "References" in answer or "참조" in answer:
            # 파싱 로직
            pass

        return references

    @classmethod
    async def _find_similar_cases(cls, query: str) -> list[SimilarCase]:
        """유사 사례 검색"""
        # TODO: 별도 사례 DB 또는 RAG 검색
        return []

    @classmethod
    def _build_cache_key(cls, request: ConsultationRequest) -> str:
        import hashlib
        content = f"{request.query}:{request.mode}:{request.context.service_type}"
        hash_val = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"consultation:{hash_val}"
```

### 3.4 API 라우터 상세

#### 3.4.1 Query Router (query.py)

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.models.request import QueryRequest
from app.models.response import QueryResponse
from app.services.rag_service import RAGService
from app.services.cache_service import CacheService
from app.api.deps import get_request_id
import time
import logging

router = APIRouter(prefix="/query", tags=["Query"])
logger = logging.getLogger(__name__)

@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    request_id: str = Depends(get_request_id)
):
    """일반 지식 검색"""
    start_time = time.time()

    # 캐시 확인
    cache_key = f"query:{request.mode}:{hash(request.query)}"
    cached = await CacheService.get(cache_key)
    if cached:
        logger.info(f"[{request_id}] Cache hit for query")
        return QueryResponse(**cached)

    # RAG 쿼리
    rag = await RAGService.get_instance()
    answer = await rag.aquery(request.query, mode=request.mode.value)

    response_time = int((time.time() - start_time) * 1000)

    response = QueryResponse(
        query=request.query,
        answer=answer,
        mode=request.mode.value,
        metadata={
            "request_id": request_id,
            "response_time_ms": response_time,
            "cache_hit": False
        }
    )

    # 캐시 저장
    await CacheService.set(cache_key, response.model_dump())

    logger.info(f"[{request_id}] Query completed in {response_time}ms")
    return response

@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    request_id: str = Depends(get_request_id)
):
    """스트리밍 응답 (TODO: LLM 스트리밍 지원 시 구현)"""
    raise HTTPException(status_code=501, detail="Streaming not implemented yet")
```

#### 3.4.2 System Router (system.py)

```python
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.models.response import HealthResponse, ComponentHealth
from app.services.rag_service import RAGService
from app.services.log_service import LogService
from app.config import get_settings
import asyncio
import time
import json

router = APIRouter(prefix="/system", tags=["System"])
start_time = time.time()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """간단한 헬스체크"""
    return HealthResponse(
        status="healthy",
        uptime_seconds=int(time.time() - start_time),
        components={},
        metrics={}
    )

@router.get("/health/detail", response_model=HealthResponse)
async def health_check_detail():
    """상세 헬스체크 (모든 컴포넌트)"""
    settings = get_settings()
    components = {}

    # PostgreSQL 체크
    try:
        import asyncpg
        pg_start = time.time()
        conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DATABASE,
        )
        await conn.fetchval("SELECT 1")
        await conn.close()
        pg_latency = int((time.time() - pg_start) * 1000)
        components["postgresql"] = ComponentHealth(
            status="healthy", latency_ms=pg_latency
        )
    except Exception as e:
        components["postgresql"] = ComponentHealth(
            status="unhealthy", latency_ms=0, details={"error": str(e)}
        )

    # Neo4j 체크
    try:
        from neo4j import AsyncGraphDatabase
        neo_start = time.time()
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
        async with driver.session() as session:
            await session.run("RETURN 1")
        await driver.close()
        neo_latency = int((time.time() - neo_start) * 1000)
        components["neo4j"] = ComponentHealth(
            status="healthy", latency_ms=neo_latency
        )
    except Exception as e:
        components["neo4j"] = ComponentHealth(
            status="unhealthy", latency_ms=0, details={"error": str(e)}
        )

    # LLM 체크
    try:
        from openai import AsyncOpenAI
        llm_start = time.time()
        client = AsyncOpenAI(
            base_url=settings.LLM_BINDING_HOST,
            api_key=settings.LLM_BINDING_API_KEY
        )
        await client.models.list()
        await client.close()
        llm_latency = int((time.time() - llm_start) * 1000)
        components["llm"] = ComponentHealth(
            status="healthy", latency_ms=llm_latency,
            details={"model": settings.LLM_MODEL}
        )
    except Exception as e:
        components["llm"] = ComponentHealth(
            status="unhealthy", latency_ms=0, details={"error": str(e)}
        )

    # 전체 상태 판단
    unhealthy = [k for k, v in components.items() if v.status == "unhealthy"]
    overall_status = "unhealthy" if unhealthy else "healthy"

    return HealthResponse(
        status=overall_status,
        uptime_seconds=int(time.time() - start_time),
        components=components,
        metrics={
            "unhealthy_components": unhealthy
        }
    )

@router.get("/logs/stream")
async def logs_stream(
    level: str = Query(default="INFO"),
    component: str = Query(default=None),
):
    """실시간 로그 스트리밍 (SSE)"""
    async def event_generator():
        async for log_entry in LogService.stream_logs(level, component):
            yield f"event: log\ndata: {json.dumps(log_entry)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

---

## 4. 프론트엔드 상세 설계

### 4.1 주요 컴포넌트

#### 4.1.1 Layout.jsx

```jsx
import { useState } from 'react';
import Sidebar from './Sidebar';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>
    </div>
  );
}
```

#### 4.1.2 Dashboard.jsx

```jsx
import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { useHealth } from '../hooks/useHealth';

export default function Dashboard() {
  const { health, loading, error } = useHealth();

  const StatusBadge = ({ status }) => {
    const colors = {
      healthy: 'bg-green-500',
      unhealthy: 'bg-red-500',
      degraded: 'bg-yellow-500',
    };
    return (
      <Badge className={colors[status] || 'bg-gray-500'}>
        {status}
      </Badge>
    );
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="text-red-500">Error: {error}</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* 시스템 상태 */}
      <Card>
        <CardHeader>
          <CardTitle>시스템 상태</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(health?.components || {}).map(([name, comp]) => (
              <div key={name} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="font-medium capitalize">{name}</span>
                <div className="flex items-center gap-2">
                  <StatusBadge status={comp.status} />
                  <span className="text-sm text-gray-500">{comp.latency_ms}ms</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 메트릭 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Uptime</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {Math.floor((health?.uptime_seconds || 0) / 3600)}h
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">응답시간 (p95)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {health?.metrics?.avg_response_time_ms || '-'}ms
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">캐시 히트율</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {((health?.metrics?.cache_hit_rate || 0) * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

#### 4.1.3 QueryTester.jsx

```jsx
import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './ui/select';
import { useApi } from '../hooks/useApi';

export default function QueryTester() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [result, setResult] = useState(null);
  const { post, loading, error } = useApi();

  const handleSubmit = async () => {
    const response = await post('/api/v1/query', { query, mode });
    if (response) {
      setResult(response);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">쿼리 테스터</h1>

      <Card>
        <CardHeader>
          <CardTitle>질의 입력</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="질문을 입력하세요..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
          />

          <div className="flex items-center gap-4">
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="검색 모드" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="local">Local</SelectItem>
                <SelectItem value="global">Global</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
                <SelectItem value="naive">Naive</SelectItem>
                <SelectItem value="mix">Mix</SelectItem>
              </SelectContent>
            </Select>

            <Button onClick={handleSubmit} disabled={loading || !query}>
              {loading ? '처리 중...' : '전송'}
            </Button>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-600 rounded">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>응답 결과</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2 text-sm text-gray-500">
                <span>Mode: {result.mode}</span>
                <span>|</span>
                <span>Time: {result.metadata?.response_time_ms}ms</span>
                <span>|</span>
                <span>Cache: {result.metadata?.cache_hit ? 'Hit' : 'Miss'}</span>
              </div>

              <div className="p-4 bg-gray-50 rounded whitespace-pre-wrap">
                {result.answer}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

#### 4.1.4 LogViewer.jsx

```jsx
import { useEffect, useState, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './ui/select';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { useSSE } from '../hooks/useSSE';

export default function LogViewer() {
  const [level, setLevel] = useState('INFO');
  const [component, setComponent] = useState('');
  const [search, setSearch] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const logContainerRef = useRef(null);

  const { logs, connected } = useSSE(
    `/api/v1/system/logs/stream?level=${level}${component ? `&component=${component}` : ''}`
  );

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const filteredLogs = logs.filter(log =>
    !search || log.message.toLowerCase().includes(search.toLowerCase())
  );

  const levelColors = {
    DEBUG: 'bg-gray-400',
    INFO: 'bg-blue-500',
    WARNING: 'bg-yellow-500',
    ERROR: 'bg-red-500',
    CRITICAL: 'bg-purple-500',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">로그 뷰어</h1>
        <Badge className={connected ? 'bg-green-500' : 'bg-red-500'}>
          {connected ? 'Connected' : 'Disconnected'}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Select value={level} onValueChange={setLevel}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="레벨" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DEBUG">DEBUG</SelectItem>
                <SelectItem value="INFO">INFO</SelectItem>
                <SelectItem value="WARNING">WARNING</SelectItem>
                <SelectItem value="ERROR">ERROR</SelectItem>
              </SelectContent>
            </Select>

            <Select value={component} onValueChange={setComponent}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="컴포넌트" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">전체</SelectItem>
                <SelectItem value="query">Query</SelectItem>
                <SelectItem value="document">Document</SelectItem>
                <SelectItem value="system">System</SelectItem>
              </SelectContent>
            </Select>

            <Input
              placeholder="검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-60"
            />

            <Button
              variant={autoScroll ? 'default' : 'outline'}
              onClick={() => setAutoScroll(!autoScroll)}
            >
              자동 스크롤
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div
            ref={logContainerRef}
            className="h-[500px] overflow-auto bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm"
          >
            {filteredLogs.map((log, idx) => (
              <div key={idx} className="flex gap-2 py-1 border-b border-gray-800">
                <span className="text-gray-500 w-20">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <Badge className={`${levelColors[log.level]} w-16 justify-center`}>
                  {log.level}
                </Badge>
                <span className="text-cyan-400 w-24">[{log.component}]</span>
                <span className="flex-1">{log.message}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4.2 Custom Hooks

#### 4.2.1 useApi.js

```javascript
import { useState, useCallback } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const get = useCallback(async (url, params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(url, { params });
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const post = useCallback(async (url, data = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post(url, data);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { get, post, loading, error };
}
```

#### 4.2.2 useSSE.js

```javascript
import { useState, useEffect, useRef } from 'react';

export function useSSE(url, maxLogs = 500) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const fullUrl = `${baseUrl}${url}`;

    const eventSource = new EventSource(fullUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnected(true);
    };

    eventSource.addEventListener('log', (event) => {
      const logEntry = JSON.parse(event.data);
      setLogs(prev => {
        const newLogs = [...prev, logEntry];
        // 최대 로그 수 제한
        if (newLogs.length > maxLogs) {
          return newLogs.slice(-maxLogs);
        }
        return newLogs;
      });
    });

    eventSource.onerror = () => {
      setConnected(false);
    };

    return () => {
      eventSource.close();
    };
  }, [url, maxLogs]);

  const clearLogs = () => setLogs([]);

  return { logs, connected, clearLogs };
}
```

---

## 5. 개발 작업 목록 (상세)

### Phase 1: 핵심 기능 (P0)

| # | 작업 | 파일 | 상세 | 상태 |
|---|------|------|------|------|
| 1.1 | 프로젝트 구조 생성 | - | skill 템플릿 기반 생성 | TBD |
| 1.2 | 환경설정 구현 | `config.py` | Pydantic Settings 클래스 | TBD |
| 1.3 | RAG Service 구현 | `rag_service.py` | 싱글톤 패턴, 초기화/종료 | TBD |
| 1.4 | Query API 구현 | `api/v1/query.py` | POST /query 엔드포인트 | TBD |
| 1.5 | Health API 구현 | `api/v1/system.py` | 헬스체크 (간단/상세) | TBD |
| 1.6 | 로깅 미들웨어 | `middleware/logging.py` | 요청/응답 로깅 | TBD |
| 1.7 | Request ID 미들웨어 | `middleware/request_id.py` | UUID 발급 | TBD |
| 1.8 | 메인 앱 통합 | `main.py` | FastAPI 앱, 라이프사이클 | TBD |
| 1.9 | Frontend 기본 구조 | - | Vite + React + Tailwind | TBD |
| 1.10 | Dashboard 컴포넌트 | `Dashboard.jsx` | 시스템 상태 표시 | TBD |
| 1.11 | Query Tester 컴포넌트 | `QueryTester.jsx` | 쿼리 테스트 UI | TBD |

### Phase 2: 상담 지원 (P0-P1)

| # | 작업 | 파일 | 상세 | 상태 |
|---|------|------|------|------|
| 2.1 | Consultation Service | `consultation_service.py` | 상담 로직, 스크립트 생성 | TBD |
| 2.2 | Consultation API | `api/v1/consultation.py` | /ask, /script 엔드포인트 | TBD |
| 2.3 | Cache Service (Redis) | `cache_service.py` | 3단계 캐싱 구현 | TBD |
| 2.4 | Document Service | `document_service.py` | 문서 업로드/상태 관리 | TBD |
| 2.5 | Document API | `api/v1/document.py` | /upload, /list, /status | TBD |
| 2.6 | Log Service | `log_service.py` | SSE 스트리밍, 버퍼링 | TBD |
| 2.7 | Log Viewer 컴포넌트 | `LogViewer.jsx` | 실시간 로그 UI | TBD |
| 2.8 | Document Manager 컴포넌트 | `DocumentManager.jsx` | 문서 관리 UI | TBD |
| 2.9 | Consultation Simulator | `ConsultationSim.jsx` | 상담 테스트 UI | TBD |

### Phase 3: 최적화 및 배포 (P1-P2)

| # | 작업 | 파일 | 상세 | 상태 |
|---|------|------|------|------|
| 3.1 | Rate Limiting | `middleware/rate_limit.py` | 요청 제한 구현 | TBD |
| 3.2 | 캐시 최적화 | `cache_service.py` | TTL 조정, 키 최적화 | TBD |
| 3.3 | 스트리밍 응답 | `api/v1/query.py` | /query/stream 구현 | TBD |
| 3.4 | 에러 핸들링 강화 | `main.py` | 전역 예외 처리 | TBD |
| 3.5 | Dockerfile 작성 | `Dockerfile` | 멀티스테이지 빌드 | TBD |
| 3.6 | docker-compose | `docker-compose.yml` | 전체 스택 구성 | TBD |
| 3.7 | 테스트 코드 | `tests/` | pytest 기반 테스트 | TBD |
| 3.8 | API 문서화 | - | OpenAPI 스키마 보강 | TBD |

---

## 6. 결정 사항

| 항목 | 결정 | 이유 |
|------|------|------|
| Web UI 프레임워크 | React + Vite | skill 템플릿 활용, 빠른 개발 |
| UI 라이브러리 | Tailwind + shadcn/ui | 일관된 디자인, 커스터마이징 용이 |
| 상태 관리 | React Hooks | 간단한 앱에 적합 |
| 캐시 | Redis (10.62.130.84) | 기존 인프라 활용 |
| 인증 | API Key (Phase 1) | 초기 버전 단순화 |

---

## 7. 미결정 사항 (TBD)

| 항목 | 선택지 | 결정 필요 시점 |
|------|--------|---------------|
| Redis 포트 | 6379 / 별도 포트 | Phase 2 시작 전 |
| 로그 보관 기간 | 7일 / 14일 / 30일 | Phase 2 |
| 모니터링 도구 | 없음 / Prometheus | Phase 3 |
| JWT 인증 추가 | 필요 / 불필요 | Phase 2 완료 후 |

---

## 8. 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [RAG-Anything 프로젝트](https://github.com/HKUDS/RAG-Anything)
- [LightRAG 프로젝트](https://github.com/HKUDS/LightRAG)
- [shadcn/ui 문서](https://ui.shadcn.com/)
- Skill: `.claude/skills/rag-api-server-generator/SKILL.md`
- 기존 `.env` 설정 파일
