"""
RAG-Anything 서비스 - 싱글톤 패턴
"""
import asyncio
import time
from typing import Optional, Dict, Any, AsyncGenerator
from pathlib import Path

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGService:
    """RAG-Anything 싱글톤 서비스"""

    _instance: Optional["RAGService"] = None
    _lock = asyncio.Lock()
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_init_done"):
            self._init_done = False
            self.rag = None
            self.lightrag = None  # 직접 LightRAG 인스턴스
            self.settings = get_settings()
            self._start_time = time.time()

    async def initialize(self) -> None:
        """RAG 시스템 초기화 (비동기)"""
        async with self._lock:
            if self._initialized:
                logger.info("RAG service already initialized")
                return

            logger.info("Initializing RAG-Anything service...")
            start = time.time()

            try:
                # LightRAG 직접 초기화 (쿼리 전용 모드)
                from lightrag import LightRAG, QueryParam
                from lightrag.llm.openai import openai_complete_if_cache, openai_embed
                from lightrag.utils import EmbeddingFunc
                from lightrag.kg.shared_storage import initialize_pipeline_status

                # QueryParam 클래스 저장 (쿼리 시 사용)
                self.QueryParam = QueryParam

                # 작업 디렉토리 생성
                working_dir = Path(self.settings.WORKING_DIR)
                working_dir.mkdir(parents=True, exist_ok=True)

                # LLM 함수
                async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
                    return await openai_complete_if_cache(
                        model=self.settings.LLM_MODEL,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        history_messages=history_messages,
                        base_url=self.settings.LLM_BINDING_HOST,
                        api_key=self.settings.LLM_BINDING_API_KEY,
                        **kwargs
                    )

                # 임베딩 함수 정의 (언랩된 함수 사용)
                # openai_embed은 이미 @wrap_embedding_func_with_attrs로 데코레이트되어 있어
                # .func를 사용하여 언랩된 함수에 접근해야 함
                async def embed_func(texts):
                    return await openai_embed.func(
                        texts,
                        model=self.settings.EMBEDDING_MODEL,
                        base_url=self.settings.EMBEDDING_BINDING_HOST,
                        api_key=self.settings.EMBEDDING_BINDING_API_KEY,
                    )

                # 임베딩 함수 래퍼
                embedding_func = EmbeddingFunc(
                    embedding_dim=self.settings.EMBEDDING_DIM,  # 1024
                    max_token_size=self.settings.MAX_EMBED_TOKENS,
                    func=embed_func,
                    model_name=self.settings.EMBEDDING_MODEL,  # BAAI/bge-m3
                )

                # LightRAG 인스턴스 생성
                self.lightrag = LightRAG(
                    working_dir=str(working_dir),
                    llm_model_func=llm_func,
                    embedding_func=embedding_func,
                    kv_storage=self.settings.LIGHTRAG_KV_STORAGE,
                    vector_storage=self.settings.LIGHTRAG_VECTOR_STORAGE,
                    doc_status_storage=self.settings.LIGHTRAG_DOC_STATUS_STORAGE,
                    graph_storage=self.settings.LIGHTRAG_GRAPH_STORAGE,
                )

                # 스토리지 초기화
                await self.lightrag.initialize_storages()
                await initialize_pipeline_status()

                self._initialized = True
                elapsed = time.time() - start
                logger.info(f"RAG service initialized in {elapsed:.2f}s")
                logger.info(f"Connected to storage: {self.settings.LIGHTRAG_KV_STORAGE}, {self.settings.LIGHTRAG_GRAPH_STORAGE}")

            except Exception as e:
                logger.error(f"Failed to initialize RAG service: {e}")
                raise

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 60,
        only_need_context: bool = False,
        only_need_prompt: bool = False,
    ) -> Dict[str, Any]:
        """검색 쿼리 실행"""
        if not self._initialized or self.lightrag is None:
            raise RuntimeError("RAG service not initialized")

        start = time.time()

        try:
            # QueryParam 객체 생성
            param = self.QueryParam(
                mode=mode,
                top_k=top_k,
                only_need_context=only_need_context,
                only_need_prompt=only_need_prompt,
            )

            result = await self.lightrag.aquery(query=query, param=param)

            elapsed = (time.time() - start) * 1000  # ms

            # 결과가 문자열인 경우 직접 반환, dict인 경우 answer 추출
            answer = result if isinstance(result, str) else str(result)

            return {
                "answer": answer,
                "mode": mode,
                "latency_ms": elapsed,
                "context": None,
                "prompt": None,
            }

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    async def query_stream(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 60,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 쿼리"""
        if not self._initialized or self.lightrag is None:
            raise RuntimeError("RAG service not initialized")

        try:
            param = self.QueryParam(mode=mode, top_k=top_k, stream=True)
            # aquery는 스트리밍 모드에서 AsyncIterator를 반환
            result = await self.lightrag.aquery(query=query, param=param)

            # 결과가 AsyncIterator인 경우 (스트리밍)
            if hasattr(result, '__aiter__'):
                async for chunk in result:
                    yield chunk
            else:
                # 문자열인 경우 한 번에 반환
                yield result if isinstance(result, str) else str(result)

        except Exception as e:
            logger.error(f"Stream query failed: {e}")
            raise

    async def insert_text(self, text: str) -> Dict[str, Any]:
        """텍스트 삽입"""
        if not self._initialized or self.lightrag is None:
            raise RuntimeError("RAG service not initialized")

        start = time.time()

        try:
            await self.lightrag.ainsert(text)
            elapsed = (time.time() - start) * 1000

            return {
                "status": "completed",
                "latency_ms": elapsed,
            }

        except Exception as e:
            logger.error(f"Text insertion failed: {e}")
            raise

    async def finalize(self) -> None:
        """리소스 정리"""
        if self.lightrag:
            try:
                await self.lightrag.finalize_storages()
                logger.info("RAG service finalized")
            except Exception as e:
                logger.error(f"Failed to finalize RAG service: {e}")

    @property
    def is_initialized(self) -> bool:
        """초기화 상태"""
        return self._initialized

    @property
    def uptime(self) -> float:
        """가동 시간 (초)"""
        return time.time() - self._start_time

    async def health_check(self) -> Dict[str, Any]:
        """상태 확인"""
        return {
            "initialized": self._initialized,
            "uptime_seconds": self.uptime,
            "working_dir": self.settings.WORKING_DIR,
        }


# 싱글톤 인스턴스 접근
def get_rag_service() -> RAGService:
    """RAG 서비스 싱글톤 반환"""
    return RAGService()
