# RAG-Anything API Server 개발 가이드

## 프로젝트 개요

RAG-Anything 기반의 멀티모달 지식 검색 API 서버입니다. 컨택센터 상담사/관리자를 위한 지식 검색 시스템 구축을 목표로 합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Server (15001)                                 │
│  - Document Upload → RAG-Anything (멀티모달 처리)        │
│  - Query/Graph → LightRAG API (9621) 프록시             │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ PostgreSQL   │  │ Neo4j        │  │ LightRAG API │
│ (Vector/KV)  │  │ (Graph)      │  │ (9621)       │
└──────────────┘  └──────────────┘  └──────────────┘
```

## 현재 구현 상태 (Phase 1 완료)

### 완료된 기능
- [x] FastAPI 기반 REST API 서버
- [x] 문서 업로드 API (POST /api/v1/documents/upload)
- [x] 문서 관리 API (목록, 상세, 삭제)
- [x] 중복 검사 (SHA256 해시 + 파일명 유사도)
- [x] LightRAG API 프록시 (쿼리, 그래프)
- [x] RAG-Anything 멀티모달 서비스 통합
- [x] MinerU 파서 연동

### 테스트 결과 (2026-01-15)
| 기능 | 상태 | 비고 |
|------|------|------|
| 서버 시작 | ✅ | uvicorn 15001 포트 |
| LightRAG 로그인 | ✅ | admin/admin123 |
| 쿼리 API | ✅ | hybrid 모드 동작 |
| 그래프 API | ✅ | 레이블 조회 성공 |
| 문서 업로드 | ✅ | 파일 저장 성공 |
| MinerU 파싱 | ⚠️ | GPU 필요 (CPU에서 매우 느림) |

## 핵심 파일 구조

```
server/backend/
├── app/
│   ├── api/v1/
│   │   ├── documents.py    # 문서 업로드/관리 API
│   │   ├── graph.py        # 지식그래프 API (LightRAG 프록시)
│   │   ├── query.py        # 검색 API (LightRAG 프록시)
│   │   └── router.py       # 라우터 통합
│   ├── services/
│   │   ├── document_service.py     # 문서 저장/버전관리
│   │   ├── raganything_service.py  # 멀티모달 처리
│   │   └── lightrag_client.py      # LightRAG HTTP 클라이언트
│   ├── config.py           # 환경설정 (VLM/LLM/DB 엔드포인트)
│   └── main.py             # FastAPI 앱 엔트리포인트
```

## 주요 설정 (config.py)

```python
# 외부 서비스 엔드포인트
LLM_BINDING_HOST = "http://10.62.130.84:18002/v1"   # LLM API
VLM_BINDING_HOST = "http://10.62.130.84:18006/v1"   # VLM API
EMBEDDING_BINDING_HOST = "http://10.62.130.84:19006" # Embedding API
LIGHTRAG_API_HOST = "http://10.62.146.92:9621"       # LightRAG API

# 스토리지
POSTGRES_HOST = "10.62.130.84"
NEO4J_URI = "neo4j://10.62.130.84:7687"
```

## 서버 실행 방법

```bash
cd /path/to/RAG-Anything/server/backend

# PATH에 .venv/bin 추가 필요 (MinerU 명령어 접근)
export PATH="/path/to/RAG-Anything/.venv/bin:$PATH"

# 서버 시작
python -m uvicorn app.main:app --host 0.0.0.0 --port 15001 --reload
```

## 다음 개발 단계 (Phase 2)

### 우선순위 높음
1. **백그라운드 처리 큐 도입**
   - 문서 업로드 시 즉시 응답, 처리는 백그라운드에서
   - Celery 또는 asyncio Task Queue 검토

2. **문서 처리 상태 추적**
   - 처리 진행률 API 추가
   - WebSocket으로 실시간 상태 알림

3. **메타데이터 영속화**
   - DocumentService._documents를 Redis/DB로 이동
   - 서버 재시작 시에도 문서 목록 유지

### 우선순위 중간
4. **텍스트 파일 직접 처리**
   - MinerU 없이 .txt/.md 파일 직접 LightRAG에 삽입
   - PDF만 MinerU로 파싱

5. **캐싱 개선**
   - Redis 모듈 설치 및 연동
   - 쿼리 결과 캐싱

### 우선순위 낮음
6. **프론트엔드 테스트 UI**
7. **실시간 로그 뷰어**
8. **상담 지원 API**

## 알려진 이슈

### MinerU CPU 성능 문제
- Mac Mini (CPU 전용)에서 10페이지 PDF 처리에 10분+ 소요
- GPU 서버에서 개발 권장
- MinerU는 `gpu_memory`를 감지하여 배치 크기 결정

### 의존성 주의사항
- `python-multipart`: FastAPI 파일 업로드에 필요
- `redis`: 캐싱 기능 활성화에 필요 (선택)
- MinerU: PATH에 .venv/bin 포함 필요

## API 문서

서버 실행 후 접속:
- Swagger UI: http://localhost:15001/docs
- ReDoc: http://localhost:15001/redoc
