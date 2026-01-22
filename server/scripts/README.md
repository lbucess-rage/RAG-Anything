# RAG-Anything Server Management Scripts

서버를 쉽게 시작, 중지, 재시작할 수 있는 관리 스크립트입니다.

## 서버 정보

| 서비스 | 포트 | 서비스 이름 | 설명 |
|--------|------|-------------|------|
| Backend | 15001 | raganything-backend | FastAPI 백엔드 서버 |
| Frontend | 19005 | raganything-frontend | Vite React 프론트엔드 서버 |

## 사용법

### 전체 서버 관리

```bash
# 모든 서버 시작
./raganything.sh start

# 모든 서버 중지
./raganything.sh stop

# 모든 서버 재시작
./raganything.sh restart

# 모든 서버 상태 확인
./raganything.sh status
```

### 개별 서버 관리

```bash
# 백엔드만 시작/중지/재시작
./raganything.sh start backend
./raganything.sh stop backend
./raganything.sh restart backend

# 프론트엔드만 시작/중지/재시작
./raganything.sh start frontend
./raganything.sh stop frontend
./raganything.sh restart frontend

# 로그 확인 (tail -f)
./raganything.sh logs backend
./raganything.sh logs frontend
```

### 개별 스크립트 직접 실행

```bash
# 백엔드 스크립트
./backend.sh start|stop|restart|status|logs

# 프론트엔드 스크립트
./frontend.sh start|stop|restart|status|logs
```

## 파일 구조

```
server/scripts/
├── raganything.sh    # 통합 관리 스크립트
├── backend.sh        # 백엔드 서버 관리
├── frontend.sh       # 프론트엔드 서버 관리
└── README.md         # 이 파일
```

## PID 및 로그 파일 위치

| 서비스 | PID 파일 | 로그 파일 |
|--------|----------|-----------|
| Backend | `server/backend/.raganything-backend.pid` | `server/backend/logs/backend.log` |
| Frontend | `server/frontend/.raganything-frontend.pid` | `server/frontend/logs/frontend.log` |

## 예시

```bash
# 프로젝트 루트에서 실행
cd /home/kms-rag/RAG-Anything

# 전체 서버 시작
./server/scripts/raganything.sh start

# 출력 예시:
# ======================================
#   RAG-Anything Server Manager
# ======================================
#
# Starting all servers...
#
# [raganything-backend] Starting on 0.0.0.0:15001...
# [raganything-backend] Started successfully (PID: 12345)
#
# [raganything-frontend] Starting on port 19005...
# [raganything-frontend] Started successfully (PID: 12346)
#
# ======================================
# All servers started!
#   Backend:  http://0.0.0.0:15001
#   Frontend: http://0.0.0.0:19005
# ======================================

# 상태 확인
./server/scripts/raganything.sh status

# 출력 예시:
# [raganything-backend] Running (PID: 12345)
# [raganything-backend] URL: http://0.0.0.0:15001
#
# [raganything-frontend] Running (PID: 12346)
# [raganything-frontend] URL: http://0.0.0.0:19005
```

## 참고사항

- 백엔드 서버는 `.venv/bin`을 PATH에 추가하여 MinerU 명령어를 사용할 수 있도록 합니다.
- 프론트엔드 서버는 Vite dev 서버를 사용하며, `vite.config.js`의 설정을 따릅니다.
- 서버 중지 시 graceful shutdown을 시도하고, 10초 후에도 종료되지 않으면 강제 종료합니다.
