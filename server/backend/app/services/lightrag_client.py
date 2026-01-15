"""
LightRAG API 클라이언트
외부 LightRAG API 서버와 통신하는 HTTP 클라이언트
"""
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator, List
import httpx
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LightRAGClient:
    """LightRAG API 서버 클라이언트"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.LIGHTRAG_API_HOST.rstrip("/")
        self.api_key = self.settings.LIGHTRAG_API_KEY
        self.timeout = self.settings.LIGHTRAG_API_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 반환 (lazy initialization)"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    def _get_headers(self) -> Dict[str, str]:
        """인증 헤더 생성"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """LightRAG API 로그인"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/login",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            result = response.json()
            self._token = result.get("access_token")
            logger.info("LightRAG API login successful")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"LightRAG login failed: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"LightRAG login error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """LightRAG API 상태 확인"""
        client = await self._get_client()
        try:
            response = await client.get("/health", headers=self._get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"LightRAG health check failed: {e}")
            return {"status": "error", "message": str(e)}

    # ===== Query API =====

    async def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 60,
        only_need_context: bool = False,
        only_need_prompt: bool = False,
        include_references: bool = True,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """RAG 쿼리 실행"""
        client = await self._get_client()
        payload = {
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "only_need_context": only_need_context,
            "only_need_prompt": only_need_prompt,
            "include_references": include_references,
        }
        if conversation_history:
            payload["conversation_history"] = conversation_history
        payload.update(kwargs)

        try:
            response = await client.post(
                "/query",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Query failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise

    async def query_stream(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 60,
        include_references: bool = True,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 RAG 쿼리 실행 (NDJSON)"""
        client = await self._get_client()
        payload = {
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "stream": True,
            "include_references": include_references,
        }
        payload.update(kwargs)

        try:
            async with client.stream(
                "POST",
                "/query/stream",
                json=payload,
                headers=self._get_headers(),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        yield line
        except Exception as e:
            logger.error(f"Stream query error: {e}")
            raise

    async def query_data(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 60,
        **kwargs,
    ) -> Dict[str, Any]:
        """RAG 데이터 조회 (LLM 응답 없이 검색 결과만)"""
        client = await self._get_client()
        payload = {
            "query": query,
            "mode": mode,
            "top_k": top_k,
        }
        payload.update(kwargs)

        try:
            response = await client.post(
                "/query/data",
                json=payload,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Query data error: {e}")
            raise

    # ===== Document API =====

    async def upload_document(
        self,
        file_path: str,
        file_content: bytes,
        file_name: str,
    ) -> Dict[str, Any]:
        """문서 업로드"""
        client = await self._get_client()
        try:
            files = {"file": (file_name, file_content)}
            headers = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            elif self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = await client.post(
                "/documents/upload",
                files=files,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            raise

    async def insert_text(self, text: str, file_source: str = "") -> Dict[str, Any]:
        """텍스트 삽입"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/documents/text",
                json={"text": text, "file_source": file_source},
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Text insert error: {e}")
            raise

    async def get_documents(
        self,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """문서 목록 조회"""
        client = await self._get_client()
        try:
            params = {}
            if status:
                params["status"] = status
            response = await client.get(
                "/documents",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Get documents error: {e}")
            raise

    async def delete_documents(
        self,
        doc_ids: List[str],
        delete_file: bool = True,
        delete_llm_cache: bool = False,
    ) -> Dict[str, Any]:
        """문서 삭제"""
        client = await self._get_client()
        try:
            response = await client.request(
                "DELETE",
                "/documents",
                json={
                    "doc_ids": doc_ids,
                    "delete_file": delete_file,
                    "delete_llm_cache": delete_llm_cache,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Delete documents error: {e}")
            raise

    # ===== Graph API =====

    async def get_graph(
        self,
        label: str,
        max_depth: int = 3,
        max_nodes: int = 1000,
    ) -> Dict[str, Any]:
        """지식 그래프 조회"""
        client = await self._get_client()
        try:
            response = await client.get(
                "/graphs",
                params={
                    "label": label,
                    "max_depth": max_depth,
                    "max_nodes": max_nodes,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Get graph error: {e}")
            raise

    async def get_graph_labels(self) -> List[str]:
        """그래프 레이블 목록 조회"""
        client = await self._get_client()
        try:
            response = await client.get(
                "/graph/label/list",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Get graph labels error: {e}")
            raise

    async def search_graph_labels(
        self,
        query: str,
        limit: int = 50,
    ) -> List[str]:
        """그래프 레이블 검색"""
        client = await self._get_client()
        try:
            response = await client.get(
                "/graph/label/search",
                params={"q": query, "limit": limit},
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Search graph labels error: {e}")
            raise

    async def create_entity(
        self,
        entity_name: str,
        entity_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """엔티티 생성"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/graph/entity/create",
                json={
                    "entity_name": entity_name,
                    "entity_data": entity_data,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Create entity error: {e}")
            raise

    async def edit_entity(
        self,
        entity_name: str,
        updated_data: Dict[str, Any],
        allow_rename: bool = False,
        allow_merge: bool = False,
    ) -> Dict[str, Any]:
        """엔티티 수정"""
        client = await self._get_client()
        try:
            response = await client.post(
                "/graph/entity/edit",
                json={
                    "entity_name": entity_name,
                    "updated_data": updated_data,
                    "allow_rename": allow_rename,
                    "allow_merge": allow_merge,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Edit entity error: {e}")
            raise

    async def close(self):
        """클라이언트 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("LightRAG client closed")


# 싱글톤 인스턴스
_client_instance: Optional[LightRAGClient] = None


def get_lightrag_client() -> LightRAGClient:
    """LightRAG 클라이언트 싱글톤 반환"""
    global _client_instance
    if _client_instance is None:
        _client_instance = LightRAGClient()
    return _client_instance
