"""
문서 관리 서비스
- 로컬 파일 저장 및 외부 URL 접근
- 버전 관리
- 중복 검사 (Content Hash + Filename Pattern)
- RAG-Anything 멀티모달 처리 연동
"""
import asyncio
import hashlib
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    """문서 관리 서비스"""

    _instance: Optional["DocumentService"] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_init_done"):
            self._init_done = True
            self.settings = get_settings()
            self.storage_path = Path(self.settings.DOCUMENT_STORAGE_PATH)
            self._documents: Dict[str, Dict[str, Any]] = {}  # In-memory cache
            self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """저장소 디렉토리 생성"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Document storage initialized at: {self.storage_path}")

    def _get_raganything_service(self):
        """RAG-Anything 서비스 가져오기 (지연 로딩)"""
        from app.services.raganything_service import get_raganything_service
        return get_raganything_service()

    # ===== Hash & Duplicate Detection =====

    def calculate_content_hash(self, content: bytes) -> str:
        """파일 콘텐츠의 SHA256 해시 계산"""
        return hashlib.sha256(content).hexdigest()

    def normalize_filename(self, filename: str) -> str:
        """
        파일명 정규화 - 버전 패턴 제거
        예: report_v2.pdf -> report.pdf
        """
        name, ext = os.path.splitext(filename)
        patterns = self.settings.DOCUMENT_VERSION_PATTERNS
        for pattern in patterns:
            name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        name = re.sub(r"[_-]+", "_", name)
        name = name.strip("_-")
        return f"{name}{ext}".lower()

    def find_duplicate_by_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """콘텐츠 해시로 중복 문서 찾기"""
        for doc_id, doc in self._documents.items():
            if doc.get("content_hash") == content_hash:
                return {"doc_id": doc_id, **doc}
        return None

    def find_similar_by_filename(self, normalized_name: str) -> List[Dict[str, Any]]:
        """정규화된 파일명으로 유사 문서 찾기"""
        similar_docs = []
        for doc_id, doc in self._documents.items():
            if doc.get("normalized_name") == normalized_name:
                similar_docs.append({"doc_id": doc_id, **doc})
        return similar_docs

    def check_duplicate(
        self, content: bytes, filename: str
    ) -> Tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """중복 검사 수행"""
        content_hash = self.calculate_content_hash(content)
        normalized_name = self.normalize_filename(filename)
        exact_duplicate = self.find_duplicate_by_hash(content_hash)
        similar_files = []
        if not exact_duplicate:
            similar_files = self.find_similar_by_filename(normalized_name)
        return content_hash, exact_duplicate, similar_files

    # ===== File Storage =====

    def _generate_storage_path(self, filename: str) -> Tuple[str, Path]:
        """저장 경로 생성 (UUID 기반)"""
        doc_id = str(uuid.uuid4())
        date_folder = datetime.now().strftime("%Y/%m/%d")
        folder_path = self.storage_path / date_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        file_path = folder_path / f"{doc_id}_{filename}"
        return doc_id, file_path

    async def save_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """파일 저장"""
        doc_id, file_path = self._generate_storage_path(filename)
        async with asyncio.Lock():
            with open(file_path, "wb") as f:
                f.write(content)
        return {
            "doc_id": doc_id,
            "file_path": str(file_path),
            "relative_path": str(file_path.relative_to(self.storage_path)),
        }

    def get_file_url(self, doc_id: str) -> Optional[str]:
        """문서 ID로 접근 URL 반환"""
        doc = self._documents.get(doc_id)
        if doc:
            return f"/api/v1/documents/files/{doc_id}"
        return None

    def get_file_path(self, doc_id: str) -> Optional[Path]:
        """문서 ID로 파일 경로 반환"""
        doc = self._documents.get(doc_id)
        if doc:
            return Path(doc.get("file_path"))
        return None

    # ===== Document Management with RAG-Anything =====

    async def upload_document(
        self,
        filename: str,
        content: bytes,
        replace_if_duplicate: bool = False,
        replace_if_similar: bool = False,
    ) -> Dict[str, Any]:
        """
        문서 업로드 및 RAG-Anything 멀티모달 처리

        Args:
            filename: 원본 파일명
            content: 파일 바이너리 콘텐츠
            replace_if_duplicate: 완전 중복시 대체 여부
            replace_if_similar: 유사 파일 발견시 대체 여부
        """
        # 파일 크기 검증
        max_size = self.settings.DOCUMENT_MAX_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise ValueError(f"File size exceeds maximum limit ({self.settings.DOCUMENT_MAX_SIZE_MB}MB)")

        # 확장자 검증
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.settings.DOCUMENT_ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is not allowed")

        # 중복 검사
        content_hash, exact_duplicate, similar_files = self.check_duplicate(content, filename)
        normalized_name = self.normalize_filename(filename)

        result = {
            "status": "pending",
            "original_filename": filename,
            "normalized_filename": normalized_name,
            "content_hash": content_hash,
            "file_size": len(content),
            "duplicate_check": {
                "exact_duplicate": exact_duplicate,
                "similar_files": similar_files,
            },
        }

        # 완전 중복 처리
        if exact_duplicate:
            if replace_if_duplicate:
                await self._replace_document(exact_duplicate["doc_id"], filename, content, content_hash, normalized_name)
                result["status"] = "replaced"
                result["replaced_doc_id"] = exact_duplicate["doc_id"]
            else:
                result["status"] = "duplicate_found"
                result["message"] = "동일한 내용의 파일이 이미 존재합니다."
                return result

        # 유사 파일 처리
        elif similar_files:
            if replace_if_similar:
                replaced_ids = []
                for similar_doc in similar_files:
                    await self._delete_document_internal(similar_doc["doc_id"])
                    replaced_ids.append(similar_doc["doc_id"])
                doc_info = await self._upload_new_document(filename, content, content_hash, normalized_name)
                result["status"] = "replaced"
                result["replaced_doc_ids"] = replaced_ids
                result["doc_id"] = doc_info["doc_id"]
            else:
                result["status"] = "similar_found"
                result["message"] = "유사한 파일명의 문서가 이미 존재합니다. 대체하시겠습니까?"
                return result

        # 새 문서 업로드
        else:
            doc_info = await self._upload_new_document(filename, content, content_hash, normalized_name)
            result["status"] = "uploaded"
            result["doc_id"] = doc_info["doc_id"]

        return result

    async def _upload_new_document(
        self,
        filename: str,
        content: bytes,
        content_hash: str,
        normalized_name: str,
    ) -> Dict[str, Any]:
        """새 문서 업로드 및 RAG-Anything 처리"""
        # 로컬 파일 저장
        file_info = await self.save_file(filename, content)
        doc_id = file_info["doc_id"]

        # RAG-Anything 멀티모달 처리
        raganything_result = None
        raganything_service = self._get_raganything_service()

        if raganything_service.is_initialized:
            try:
                logger.info(f"Processing document with RAG-Anything: {filename}")
                raganything_result = await raganything_service.process_document(
                    file_path=file_info["file_path"],
                    file_name=filename,
                )
                logger.info(f"RAG-Anything processing complete: {filename}")
            except Exception as e:
                logger.error(f"RAG-Anything processing failed: {e}")
                raganything_result = {"status": "error", "error": str(e)}
        else:
            logger.warning("RAG-Anything service not initialized, skipping multimodal processing")
            raganything_result = {"status": "skipped", "reason": "service_not_initialized"}

        # 메타데이터 저장
        doc_metadata = {
            "original_filename": filename,
            "normalized_name": normalized_name,
            "content_hash": content_hash,
            "file_path": file_info["file_path"],
            "relative_path": file_info["relative_path"],
            "file_size": len(content),
            "raganything_result": raganything_result,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
        }
        self._documents[doc_id] = doc_metadata

        logger.info(f"Document uploaded: {doc_id} ({filename})")
        return {"doc_id": doc_id, **doc_metadata}

    async def _replace_document(
        self,
        doc_id: str,
        filename: str,
        content: bytes,
        content_hash: str,
        normalized_name: str,
    ) -> Dict[str, Any]:
        """기존 문서 대체"""
        old_doc = self._documents.get(doc_id)
        if not old_doc:
            raise ValueError(f"Document not found: {doc_id}")

        # 기존 문서 삭제 (스토리지에서는 유지, 메타데이터만)
        new_version = old_doc.get("version", 1) + 1

        # 새 파일 저장
        file_info = await self.save_file(filename, content)

        # RAG-Anything 처리
        raganything_result = None
        raganything_service = self._get_raganything_service()

        if raganything_service.is_initialized:
            try:
                raganything_result = await raganything_service.process_document(
                    file_path=file_info["file_path"],
                    file_name=filename,
                )
            except Exception as e:
                logger.error(f"RAG-Anything processing failed: {e}")
                raganything_result = {"status": "error", "error": str(e)}

        # 메타데이터 업데이트
        self._documents[doc_id] = {
            "original_filename": filename,
            "normalized_name": normalized_name,
            "content_hash": content_hash,
            "file_path": file_info["file_path"],
            "relative_path": file_info["relative_path"],
            "file_size": len(content),
            "raganything_result": raganything_result,
            "created_at": old_doc.get("created_at"),
            "updated_at": datetime.now().isoformat(),
            "version": new_version,
            "previous_versions": old_doc.get("previous_versions", []) + [
                {
                    "version": old_doc.get("version", 1),
                    "file_path": old_doc.get("file_path"),
                    "updated_at": old_doc.get("updated_at"),
                }
            ],
        }

        logger.info(f"Document replaced: {doc_id} (v{new_version})")
        return {"doc_id": doc_id, **self._documents[doc_id]}

    async def _delete_document_internal(self, doc_id: str) -> None:
        """내부 문서 삭제"""
        if doc_id in self._documents:
            del self._documents[doc_id]

    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """문서 삭제"""
        doc = self._documents.get(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")

        # 로컬 파일 삭제
        file_path = Path(doc.get("file_path"))
        if file_path.exists():
            file_path.unlink()

        # 메타데이터 삭제
        del self._documents[doc_id]

        logger.info(f"Document deleted: {doc_id}")
        return {"status": "deleted", "doc_id": doc_id}

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """문서 메타데이터 조회"""
        doc = self._documents.get(doc_id)
        if doc:
            return {"doc_id": doc_id, **doc}
        return None

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """문서 목록 조회"""
        docs = list(self._documents.items())

        if search:
            search_lower = search.lower()
            docs = [
                (doc_id, doc) for doc_id, doc in docs
                if search_lower in doc.get("original_filename", "").lower()
            ]

        docs.sort(key=lambda x: x[1].get("created_at", ""), reverse=True)
        total = len(docs)
        docs = docs[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "documents": [{"doc_id": doc_id, **doc} for doc_id, doc in docs],
        }


# 싱글톤 인스턴스
def get_document_service() -> DocumentService:
    """DocumentService 싱글톤 반환"""
    return DocumentService()
