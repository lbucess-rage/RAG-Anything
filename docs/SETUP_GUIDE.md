# RAG-Anything 개발 서버 설정 가이드

다른 개발 서버에서 프로젝트를 이어서 개발하기 위한 설정 가이드입니다.

## 1. 사전 요구사항

### 시스템 요구사항
- **OS**: Linux (Ubuntu 20.04+ 권장)
- **GPU**: NVIDIA GPU (MinerU 파서 사용 시 필수)
- **RAM**: 최소 16GB (권장 32GB+)
- **저장공간**: 최소 50GB

### 런타임 버전
```bash
Python 3.11+
Node.js 22+
uv 0.7+
```

### 외부 서비스 (별도 서버 또는 Docker로 구성)
| 서비스 | 포트 | 용도 |
|--------|------|------|
| PostgreSQL | 5432 | 벡터/KV 저장소 |
| Neo4j | 7687 | 지식 그래프 저장소 |
| Redis | 6379 | 캐시 (선택) |
| LLM API | 18002 | 텍스트 생성 |
| VLM API | 18006 | 이미지 분석 |
| Embedding API | 19006 | 임베딩 생성 |
| LightRAG API | 9621 | RAG 쿼리 엔진 |

---

## 2. 프로젝트 클론

```bash
# 저장소 클론
git clone git@github.com:lbucess-rage/RAG-Anything.git
cd RAG-Anything

# 개발 브랜치로 전환
git checkout feature/raganything-multimodal
git pull origin feature/raganything-multimodal
```

---

## 3. Python 환경 설정

### uv 설치 (권장)
```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv sync --all-extras

# 가상환경 활성화
source .venv/bin/activate
```

### pip 사용 시
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
```

---

## 4. 환경 변수 설정

### .env 파일 생성
```bash
cp env.example .env
```

### 주요 설정값 수정 (.env)

```bash
# === LLM 설정 ===
LLM_BINDING=openai
LLM_MODEL=lbu-slm-v3-qw-max
LLM_BINDING_HOST=http://<LLM_SERVER_IP>:18002/v1
LLM_BINDING_API_KEY=EMPTY

# === VLM 설정 (이미지 처리용) ===
VLM_MODEL=qwen3-vl-8b
VLM_BINDING_HOST=http://<VLM_SERVER_IP>:18006/v1

# === Embedding 설정 ===
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DIM=1024
EMBEDDING_BINDING_HOST=http://<EMBEDDING_SERVER_IP>:19006

# === PostgreSQL 설정 ===
POSTGRES_HOST=<POSTGRES_IP>
POSTGRES_PORT=5432
POSTGRES_USER=lightrag
POSTGRES_PASSWORD=<YOUR_PASSWORD>
POSTGRES_DATABASE=lightrag

# === Neo4j 설정 ===
NEO4J_URI=neo4j://<NEO4J_IP>:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<YOUR_PASSWORD>
```

---

## 5. 프론트엔드 설정

```bash
cd server/frontend

# 의존성 설치
npm install

# 환경 변수 (선택사항)
# .env 파일에서 VITE_API_URL 설정 가능
# 기본값: 프록시를 통해 localhost:15001로 연결
```

### 포트 변경 (필요시)
`server/frontend/vite.config.js` 수정:
```javascript
server: {
  port: 15003,  // 원하는 포트로 변경
  host: '0.0.0.0',
  proxy: {
    '/api': {
      target: 'http://localhost:15001',
      changeOrigin: true,
    },
  },
},
```

---

## 6. 서버 실행

### 방법 1: 스크립트 사용 (권장)

```bash
# 백엔드 서버 (포트 15001)
./server/scripts/backend.sh start

# 프론트엔드 서버 (포트 15003)
./server/scripts/frontend.sh start

# 상태 확인
./server/scripts/backend.sh status
./server/scripts/frontend.sh status

# 중지
./server/scripts/backend.sh stop
./server/scripts/frontend.sh stop
```

### 방법 2: 수동 실행

```bash
# 백엔드 서버
cd server/backend
export PATH="$(pwd)/../../.venv/bin:$PATH"
python -m uvicorn app.main:app --host 0.0.0.0 --port 15001 --reload

# 프론트엔드 서버 (새 터미널)
cd server/frontend
npm run dev
```

### 방법 3: 백그라운드 실행

```bash
# 백엔드
cd server/backend
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 15001 > logs/backend.log 2>&1 &

# 프론트엔드
cd server/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
```

---

## 7. 서비스 포트 요약

| 서비스 | 포트 | 설명 |
|--------|------|------|
| 프론트엔드 | 15003 | React 대시보드 |
| 백엔드 API | 15001 | FastAPI 서버 |
| LightRAG API | 9621 | RAG 쿼리 엔진 |

---

## 8. 상태 확인

```bash
# 포트 리스닝 확인
ss -tlnp | grep -E "(15001|15003|9621)"

# 백엔드 헬스체크
curl http://localhost:15001/docs

# LightRAG 헬스체크
curl http://localhost:9621/health

# 프론트엔드 접속
# 브라우저에서 http://<SERVER_IP>:15003
```

---

## 9. 백엔드 설정 커스터마이징

백엔드 설정은 `server/backend/app/config.py`에서 관리됩니다.
환경 변수 또는 `.env` 파일로 오버라이드 가능합니다.

### 주요 설정 항목
```python
# 서버
HOST = "0.0.0.0"
PORT = 15001

# LightRAG 프록시 대상
LIGHTRAG_API_HOST = "http://10.62.130.84:9621"

# 문서 처리
PARSER = "docling"  # 또는 "mineru"
ENABLE_IMAGE_PROCESSING = True
ENABLE_TABLE_PROCESSING = True

# MinerU 백엔드 (mineru 파서 사용 시)
MINERU_BACKEND = "vlm-http-client"  # 가장 빠름
MINERU_VLM_URL = "http://<VLM_SERVER>:18006/v1"
```

---

## 10. 문제 해결

### 포트 충돌
```bash
# 포트 사용 중인 프로세스 확인
ss -tlnp | grep <PORT>

# 프로세스 종료
kill <PID>
# 또는
pkill -f "node.*vite"  # 프론트엔드
pkill -f "uvicorn.*app.main"  # 백엔드
```

### MinerU GPU 오류
```bash
# CUDA 확인
nvidia-smi

# PyTorch CUDA 확인
python -c "import torch; print(torch.cuda.is_available())"
```

### LibreOffice 설치 (Office 문서 처리용)
```bash
# Ubuntu/Debian
sudo apt install libreoffice

# CentOS/RHEL
sudo yum install libreoffice
```

---

## 11. 개발 워크플로우

```bash
# 1. 최신 코드 가져오기
git pull origin feature/raganything-multimodal

# 2. 의존성 업데이트
uv sync --all-extras
cd server/frontend && npm install

# 3. 서버 재시작
./server/scripts/backend.sh restart
./server/scripts/frontend.sh restart

# 4. 코드 포맷팅 (커밋 전)
ruff format .
ruff check --fix --ignore=E402 .

# 5. 커밋 & 푸시
git add .
git commit -m "feat: your feature description"
git push origin feature/raganything-multimodal
```

---

## 부록: Docker 서비스 구성 (참고)

외부 서비스들은 별도의 Docker Compose로 구성되어 있을 수 있습니다.
필요 시 인프라 담당자에게 문의하세요.

```yaml
# docker-compose.yml 예시 (참고용)
services:
  postgres:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: lightrag
      POSTGRES_PASSWORD: lightrag_secure_2024
      POSTGRES_DB: lightrag

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/neo4j_secure_2024

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```
