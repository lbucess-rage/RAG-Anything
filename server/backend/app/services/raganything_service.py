"""
RAG-Anything 멀티모달 처리 서비스
- MinerU 파싱으로 문서에서 텍스트/이미지/테이블/수식 추출
- VLM으로 이미지 분석
- LLM으로 테이블/수식 분석
- 동일 스토리지(PostgreSQL + Neo4j)에 저장하여 커스텀 LightRAG API와 공유
"""
import asyncio
import os
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGAnythingService:
    """RAG-Anything 멀티모달 처리 서비스 (싱글톤)"""

    _instance: Optional["RAGAnythingService"] = None
    _lock = asyncio.Lock()
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_init_done"):
            self._init_done = True
            self.settings = get_settings()
            self.rag: Optional[Any] = None  # RAGAnything instance
            self._processing_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """RAG-Anything 초기화"""
        async with self._lock:
            if self._initialized:
                logger.info("RAG-Anything service already initialized")
                return

            logger.info("Initializing RAG-Anything multimodal service...")

            try:
                # LightRAG가 요구하는 환경 변수 설정
                import os
                os.environ.setdefault("POSTGRES_HOST", self.settings.POSTGRES_HOST)
                os.environ.setdefault("POSTGRES_PORT", str(self.settings.POSTGRES_PORT))
                os.environ.setdefault("POSTGRES_USER", self.settings.POSTGRES_USER)
                os.environ.setdefault("POSTGRES_PASSWORD", self.settings.POSTGRES_PASSWORD)
                os.environ.setdefault("POSTGRES_DATABASE", self.settings.POSTGRES_DATABASE)
                os.environ.setdefault("NEO4J_URI", self.settings.NEO4J_URI)
                os.environ.setdefault("NEO4J_USERNAME", self.settings.NEO4J_USERNAME)
                os.environ.setdefault("NEO4J_PASSWORD", self.settings.NEO4J_PASSWORD)

                from raganything import RAGAnything, RAGAnythingConfig
                from lightrag.llm.openai import openai_complete_if_cache, openai_embed
                from lightrag.utils import EmbeddingFunc
                from openai import AsyncOpenAI

                # LLM 함수 정의
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

                # VLM 함수 정의 (이미지 분석용)
                async def vision_func(prompt, system_prompt=None, history_messages=[],
                                     image_data=None, messages=None, **kwargs):
                    client = AsyncOpenAI(
                        base_url=self.settings.VLM_BINDING_HOST,
                        api_key=self.settings.VLM_BINDING_API_KEY,
                    )
                    try:
                        if messages:
                            response = await client.chat.completions.create(
                                model=self.settings.VLM_MODEL,
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
                                model=self.settings.VLM_MODEL,
                                messages=messages_list,
                                max_tokens=kwargs.get("max_tokens", 500),
                            )
                            return response.choices[0].message.content
                        else:
                            return await llm_func(prompt, system_prompt, history_messages, **kwargs)
                    finally:
                        await client.close()

                # 임베딩 함수 정의
                async def embed_func(texts):
                    return await openai_embed.func(
                        texts,
                        model=self.settings.EMBEDDING_MODEL,
                        base_url=self.settings.EMBEDDING_BINDING_HOST,
                        api_key=self.settings.EMBEDDING_BINDING_API_KEY,
                    )

                embedding_func = EmbeddingFunc(
                    embedding_dim=self.settings.EMBEDDING_DIM,
                    max_token_size=self.settings.MAX_EMBED_TOKENS,
                    func=embed_func,
                )

                # RAG-Anything 설정
                config = RAGAnythingConfig(
                    working_dir=self.settings.WORKING_DIR,
                    parser=self.settings.PARSER,
                    parse_method=self.settings.PARSE_METHOD,
                    enable_image_processing=self.settings.ENABLE_IMAGE_PROCESSING,
                    enable_table_processing=self.settings.ENABLE_TABLE_PROCESSING,
                    enable_equation_processing=self.settings.ENABLE_EQUATION_PROCESSING,
                )

                # RAG-Anything 인스턴스 생성 (동일 스토리지 사용)
                self.rag = RAGAnything(
                    config=config,
                    llm_model_func=llm_func,
                    vision_model_func=vision_func,
                    embedding_func=embedding_func,
                    lightrag_kwargs={
                        "kv_storage": self.settings.LIGHTRAG_KV_STORAGE,
                        "vector_storage": self.settings.LIGHTRAG_VECTOR_STORAGE,
                        "doc_status_storage": self.settings.LIGHTRAG_DOC_STATUS_STORAGE,
                        "graph_storage": self.settings.LIGHTRAG_GRAPH_STORAGE,
                    }
                )

                # LightRAG 스토리지 초기화 (기존 데이터와 연결)
                await self.rag._ensure_lightrag_initialized()

                self._initialized = True
                logger.info("RAG-Anything multimodal service initialized")
                logger.info(f"  Parser: {self.settings.PARSER}")
                logger.info(f"  Image processing: {self.settings.ENABLE_IMAGE_PROCESSING}")
                logger.info(f"  Table processing: {self.settings.ENABLE_TABLE_PROCESSING}")
                logger.info(f"  Equation processing: {self.settings.ENABLE_EQUATION_PROCESSING}")
                logger.info(f"  Storage: {self.settings.LIGHTRAG_KV_STORAGE}, {self.settings.LIGHTRAG_GRAPH_STORAGE}")

            except Exception as e:
                logger.error(f"Failed to initialize RAG-Anything service: {e}")
                raise

    async def process_document(
        self,
        file_path: str,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        문서 처리 (멀티모달)

        - MinerU로 파싱 (텍스트, 이미지, 테이블, 수식 추출)
        - 텍스트는 LightRAG로 직접 삽입
        - 이미지는 VLM으로 분석 후 엔티티/관계 추출
        - 테이블/수식은 LLM으로 분석 후 엔티티/관계 추출
        - 모든 결과는 공유 스토리지에 저장
        """
        if not self._initialized or self.rag is None:
            raise RuntimeError("RAG-Anything service not initialized")

        async with self._processing_lock:
            logger.info(f"Processing document: {file_name or file_path}")

            try:
                # RAG-Anything의 process_document_complete 호출
                result = await self.rag.process_document_complete(
                    file_path=file_path,
                    file_name=file_name,
                )

                logger.info(f"Document processed: {file_name or file_path}")
                return {
                    "status": "success",
                    "file_path": file_path,
                    "file_name": file_name,
                    "result": result,
                }

            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                return {
                    "status": "error",
                    "file_path": file_path,
                    "file_name": file_name,
                    "error": str(e),
                }

    async def process_document_from_bytes(
        self,
        content: bytes,
        file_name: str,
    ) -> Dict[str, Any]:
        """
        바이트 데이터로부터 문서 처리

        임시 파일 생성 후 처리
        """
        if not self._initialized or self.rag is None:
            raise RuntimeError("RAG-Anything service not initialized")

        # 임시 디렉토리에 파일 저장
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file_name)

        try:
            with open(temp_path, "wb") as f:
                f.write(content)

            # 문서 처리
            result = await self.process_document(temp_path, file_name)
            return result

        finally:
            # 임시 파일 정리
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def get_document_status(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """문서 처리 상태 조회"""
        if not self._initialized or self.rag is None:
            return None

        try:
            status = await self.rag.lightrag.doc_status.get_by_id(doc_id)
            return status
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return None

    async def finalize(self) -> None:
        """리소스 정리"""
        if self.rag:
            try:
                await self.rag.finalize_storages()
                logger.info("RAG-Anything service finalized")
            except Exception as e:
                logger.error(f"Failed to finalize RAG-Anything service: {e}")

    @property
    def is_initialized(self) -> bool:
        """초기화 상태"""
        return self._initialized


# 싱글톤 인스턴스 접근
def get_raganything_service() -> RAGAnythingService:
    """RAG-Anything 서비스 싱글톤 반환"""
    return RAGAnythingService()
