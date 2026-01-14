"""
로깅 설정 및 유틸리티
구조화된 JSON 로깅 지원
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """JSON 포맷 로그 포매터"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 추가 필드
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "component"):
            log_data["component"] = record.component
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "details"):
            log_data["details"] = record.details

        # 예외 정보
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """콘솔용 컬러 포매터"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Request ID가 있으면 표시
        request_id = getattr(record, "request_id", None)
        req_str = f"[{request_id[:8]}] " if request_id else ""

        return f"{color}{timestamp} {record.levelname:8}{self.RESET} {req_str}{record.getMessage()}"


def setup_logging() -> None:
    """로깅 시스템 초기화"""
    settings = get_settings()

    # 로그 디렉토리 생성
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 기존 핸들러 제거
    root_logger.handlers.clear()

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (전체 로그)
    app_log_path = log_dir / "app.log"
    app_handler = RotatingFileHandler(
        app_log_path,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(app_handler)

    # 에러 전용 핸들러
    error_log_path = log_dir / "error.log"
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # 쿼리 전용 핸들러
    query_log_path = log_dir / "query.log"
    query_handler = RotatingFileHandler(
        query_log_path,
        maxBytes=200 * 1024 * 1024,  # 200MB
        backupCount=14,
        encoding="utf-8",
    )
    query_handler.setLevel(logging.INFO)
    query_handler.setFormatter(JSONFormatter())
    query_handler.addFilter(lambda record: getattr(record, "component", None) == "query")
    root_logger.addHandler(query_handler)

    # 라이브러리 로깅 레벨 조정
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 반환"""
    return logging.getLogger(name)


class LogContext:
    """로그 컨텍스트 관리자"""

    def __init__(
        self,
        logger: logging.Logger,
        request_id: Optional[str] = None,
        component: Optional[str] = None,
    ):
        self.logger = logger
        self.request_id = request_id
        self.component = component
        self.start_time: Optional[float] = None

    def log(
        self,
        level: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """컨텍스트 정보가 포함된 로그 출력"""
        extra = {
            "request_id": self.request_id,
            "component": self.component,
        }
        if details:
            extra["details"] = details

        self.logger.log(level, message, extra=extra, **kwargs)

    def info(self, message: str, **kwargs):
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log(logging.DEBUG, message, **kwargs)
