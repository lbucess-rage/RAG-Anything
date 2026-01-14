"""
RAG-Anything 백엔드 API 서버
- FastAPI 기반
- 기존 LightRAG (PostgreSQL + Neo4j) 연동
- 질문 응답 및 문서 업로드 API 제공
"""
import os
import asyncio
import tempfile
import shutil
from typing import Optional, List
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc


# ========== Pydantic Models ==========

class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # local, global, hybrid, naive, mix


class QueryResponse(BaseModel):
    query: str
    answer: str
    mode: str


class UploadResponse(BaseModel):
    filename: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    storage: dict


# ========== RAG-Anything 초기화 ==========

rag_instance: Optional[RAGAnything] = None


async def get_rag() -> RAGAnything:
    """RAG-Anything 인스턴스 반환 (싱글톤)"""
    global rag_instance
    if rag_instance is None:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    return rag_instance


async def init_rag():
    """RAG-Anything 초기화"""
    global rag_instance

    # LLM 함수
    async def llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return await openai_complete_if_cache(
            model=os.getenv("LLM_MODEL"),
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            base_url=os.getenv("LLM_BINDING_HOST"),
            api_key=os.getenv("LLM_BINDING_API_KEY", "EMPTY"),
            **kwargs
        )

    # VLM 함수
    async def vision_func(prompt, system_prompt=None, history_messages=[],
                         image_data=None, messages=None, **kwargs):
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=os.getenv("VLM_BINDING_HOST"),
            api_key=os.getenv("VLM_BINDING_API_KEY", "EMPTY")
        )
        try:
            if messages:
                response = await client.chat.completions.create(
                    model=os.getenv("VLM_MODEL"),
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
                    model=os.getenv("VLM_MODEL"),
                    messages=messages_list,
                    max_tokens=kwargs.get("max_tokens", 500),
                )
                return response.choices[0].message.content
            else:
                return await llm_func(prompt, system_prompt, history_messages, **kwargs)
        finally:
            await client.close()

    # 임베딩 함수
    embedding_func = EmbeddingFunc(
        embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
        max_token_size=int(os.getenv("MAX_EMBED_TOKENS", "8192")),
        func=lambda texts: openai_embed(
            texts,
            model=os.getenv("EMBEDDING_MODEL"),
            base_url=os.getenv("EMBEDDING_BINDING_HOST"),
            api_key=os.getenv("EMBEDDING_BINDING_API_KEY", "EMPTY"),
        )
    )

    # RAG-Anything 설정
    config = RAGAnythingConfig(
        working_dir=os.getenv("WORKING_DIR", "./rag_storage"),
        parser="mineru",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )

    # 인스턴스 생성
    rag_instance = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        vision_model_func=vision_func,
        embedding_func=embedding_func,
        lightrag_kwargs={
            "kv_storage": os.getenv("LIGHTRAG_KV_STORAGE", "PGKVStorage"),
            "vector_storage": os.getenv("LIGHTRAG_VECTOR_STORAGE", "PGVectorStorage"),
            "doc_status_storage": os.getenv("LIGHTRAG_DOC_STATUS_STORAGE", "PGDocStatusStorage"),
            "graph_storage": os.getenv("LIGHTRAG_GRAPH_STORAGE", "Neo4JStorage"),
        }
    )

    # LightRAG 스토리지 초기화 (기존 데이터 연결)
    await rag_instance._ensure_lightrag_initialized()

    print("RAG-Anything initialized successfully")


async def close_rag():
    """RAG-Anything 종료"""
    global rag_instance
    if rag_instance:
        await rag_instance.finalize_storages()
        rag_instance = None
        print("RAG-Anything closed")


# ========== FastAPI App ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 RAG 초기화/정리"""
    await init_rag()
    yield
    await close_rag()


app = FastAPI(
    title="RAG-Anything API",
    description="멀티모달 RAG 시스템 API - PostgreSQL + Neo4j 연동",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API Endpoints ==========

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서버 상태 확인"""
    rag = await get_rag()
    return HealthResponse(
        status="healthy",
        storage={
            "kv": os.getenv("LIGHTRAG_KV_STORAGE"),
            "vector": os.getenv("LIGHTRAG_VECTOR_STORAGE"),
            "graph": os.getenv("LIGHTRAG_GRAPH_STORAGE"),
            "postgres_host": os.getenv("POSTGRES_HOST"),
            "neo4j_uri": os.getenv("NEO4J_URI"),
        }
    )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    질문에 대한 답변 생성

    - **query**: 질문 내용
    - **mode**: 검색 모드 (local, global, hybrid, naive, mix)
    """
    rag = await get_rag()

    try:
        answer = await rag.aquery(request.query, mode=request.mode)
        return QueryResponse(
            query=request.query,
            answer=answer,
            mode=request.mode,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    문서 업로드 및 처리

    지원 형식: PDF, DOCX, PPTX, XLSX, 이미지 등
    """
    rag = await get_rag()

    # 임시 파일로 저장
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 문서 처리 (백그라운드에서 실행할 수도 있음)
        await rag.process_document(temp_path)

        return UploadResponse(
            filename=file.filename,
            status="success",
            message=f"문서 '{file.filename}' 처리 완료",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 처리 실패: {str(e)}")

    finally:
        # 임시 파일 정리
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/query/multimodal")
async def query_multimodal(
    query: str,
    mode: str = "hybrid",
    file: Optional[UploadFile] = File(None),
):
    """
    멀티모달 쿼리 (이미지와 함께 질문)

    - **query**: 질문 내용
    - **mode**: 검색 모드
    - **file**: 이미지 파일 (선택)
    """
    rag = await get_rag()

    try:
        if file:
            # 이미지와 함께 쿼리
            import base64
            content = await file.read()
            image_base64 = base64.b64encode(content).decode("utf-8")

            answer = await rag.aquery_with_multimodal(
                query,
                multimodal_content=[{
                    "type": "image",
                    "image_data": image_base64,
                }],
                mode=mode,
            )
        else:
            # 텍스트만 쿼리
            answer = await rag.aquery(query, mode=mode)

        return {
            "query": query,
            "answer": answer,
            "mode": mode,
            "has_image": file is not None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 실행 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발용
    )
