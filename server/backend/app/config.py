"""
환경설정 관리
Pydantic Settings를 사용하여 환경변수 및 .env 파일에서 설정을 로드
"""
import os
import sys
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field

# 프로젝트 루트 경로 설정 (RAG-Anything 패키지 사용을 위해)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 앱 설정
    APP_NAME: str = "RAG-Anything API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True  # API 문서 활성화

    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 15001
    WORKERS: int = 4

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]

    # LightRAG API 서버 설정 (Proxy 대상)
    LIGHTRAG_API_HOST: str = "http://10.62.130.84:9621"
    LIGHTRAG_API_KEY: Optional[str] = None
    LIGHTRAG_API_USERNAME: str = "admin"
    LIGHTRAG_API_PASSWORD: str = "admin123"
    LIGHTRAG_API_TIMEOUT: int = 300  # 5분

    # 문서 저장소 설정
    DOCUMENT_STORAGE_PATH: str = Field(default="./document_storage")
    DOCUMENT_MAX_SIZE_MB: int = 100  # 최대 파일 크기
    DOCUMENT_ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".doc", ".pptx", ".ppt",
        ".xlsx", ".xls", ".txt", ".md", ".csv"
    ]

    # 문서 중복 검사 설정
    DOCUMENT_SIMILARITY_THRESHOLD: float = 0.9  # 파일명 유사도 임계값
    DOCUMENT_VERSION_PATTERNS: List[str] = [
        r"_v\d+", r"_ver\d+", r"_version\d+",  # _v1, _ver2, _version3
        r"_\d{8}", r"_\d{4}-\d{2}-\d{2}",  # _20240101, _2024-01-01
        r"_최종", r"_final", r"_수정", r"_revised",
        r"\(\d+\)", r"_copy\d*",  # (1), _copy, _copy2
    ]

    # RAG-Anything 설정 (문서 처리용)
    WORKING_DIR: str = Field(default="./rag_storage")
    PARSER: str = "docling"
    PARSE_METHOD: str = "auto"
    ENABLE_IMAGE_PROCESSING: bool = True
    ENABLE_TABLE_PROCESSING: bool = True
    ENABLE_EQUATION_PROCESSING: bool = True

    # MinerU Performance Settings
    # vlm-http-client: Fastest (~11x faster than hybrid-auto-engine), requires VLM server
    # hybrid-auto-engine: Good accuracy, moderate speed (default)
    # pipeline: CPU compatible, basic accuracy
    MINERU_BACKEND: str = "vlm-http-client"
    MINERU_VLM_URL: str = "http://10.62.130.84:18006/v1"

    # LLM 설정
    LLM_BINDING: str = "openai"
    LLM_MODEL: str = "lbu-slm-v3-qw-max"
    LLM_BINDING_HOST: str = "http://10.62.130.84:18002/v1"
    LLM_BINDING_API_KEY: str = "EMPTY"
    TIMEOUT: int = 900
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 9000
    MAX_ASYNC: int = 4

    # VLM 설정
    VLM_BINDING: str = "openai"
    VLM_MODEL: str = "qwen3-vl-8b"
    VLM_BINDING_HOST: str = "http://10.62.130.84:18006/v1"
    VLM_BINDING_API_KEY: str = "EMPTY"
    VLM_RESPONSE_LANGUAGE: str = "Korean"

    # Embedding 설정
    EMBEDDING_BINDING: str = "openai"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_BINDING_HOST: str = "http://10.62.130.84:19006"
    EMBEDDING_BINDING_API_KEY: str = "EMPTY"
    MAX_EMBED_TOKENS: int = 8192

    # Rerank 설정
    RERANK_BINDING: str = "tei"
    RERANK_MODEL: str = "dragonkue/bge-reranker-v2-m3-ko"
    RERANK_BINDING_HOST: str = "http://10.62.130.84:19003/rerank"

    # Storage 설정
    LIGHTRAG_KV_STORAGE: str = "PGKVStorage"
    LIGHTRAG_DOC_STATUS_STORAGE: str = "PGDocStatusStorage"
    LIGHTRAG_VECTOR_STORAGE: str = "PGVectorStorage"
    LIGHTRAG_GRAPH_STORAGE: str = "Neo4JStorage"

    # PostgreSQL 설정
    POSTGRES_HOST: str = "10.62.130.84"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "lightrag"
    POSTGRES_PASSWORD: str = "lightrag_secure_2024"
    POSTGRES_DATABASE: str = "lightrag"
    POSTGRES_VECTOR_INDEX_TYPE: str = "HNSW"
    POSTGRES_HNSW_M: int = 16
    POSTGRES_HNSW_EF: int = 200

    # Neo4j 설정
    NEO4J_URI: str = "neo4j://10.62.130.84:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_secure_2024"
    NEO4J_DATABASE: str = "neo4j"
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = 50

    # Redis 설정
    REDIS_HOST: str = "10.62.130.84"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Cache TTL (seconds)
    CACHE_TTL_QUERY: int = 3600       # 1시간
    CACHE_TTL_METADATA: int = 86400   # 24시간
    CACHE_TTL_MEMORY: int = 300       # 5분
    CACHE_MAX_SIZE: int = 1000        # 인메모리 캐시 최대 크기

    # Logging 설정
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    VERBOSE: bool = False

    # Rate Limiting
    RATE_LIMIT_READ: int = 100        # req/min
    RATE_LIMIT_WRITE: int = 20        # req/min

    # Language
    SUMMARY_LANGUAGE: str = "Korean"

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환"""
    return Settings()
