"""
로그 핸들러 구현
파일, 콘솔, 원격 로그 핸들러 제공
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Union
from .formatters import JSONFormatter, StructuredFormatter, DevelopmentFormatter, ProductionFormatter


def get_console_handler(
    level: Union[str, int] = logging.INFO,
    use_colors: bool = True,
    formatter_type: str = "structured"
) -> logging.StreamHandler:
    """
    콘솔 로그 핸들러 생성
    
    Args:
        level: 로그 레벨
        use_colors: 색상 사용 여부
        formatter_type: 포맷터 타입 (structured, json, compact)
    
    Returns:
        설정된 콘솔 핸들러
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # 포맷터 선택
    if formatter_type == "json":
        formatter = JSONFormatter()
    elif formatter_type == "compact":
        from .formatters import CompactFormatter
        formatter = CompactFormatter()
    elif formatter_type == "development":
        formatter = DevelopmentFormatter()
    else:  # structured
        formatter = StructuredFormatter(include_context=True, colorize=use_colors)
    
    handler.setFormatter(formatter)
    return handler


def get_file_handler(
    file_path: Union[str, Path],
    level: Union[str, int] = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    formatter_type: str = "json",
    encoding: str = "utf-8"
) -> logging.handlers.RotatingFileHandler:
    """
    파일 로그 핸들러 생성 (로테이션 지원)
    
    Args:
        file_path: 로그 파일 경로
        level: 로그 레벨
        max_bytes: 최대 파일 크기 (바이트)
        backup_count: 백업 파일 개수
        formatter_type: 포맷터 타입
        encoding: 파일 인코딩
    
    Returns:
        설정된 파일 핸들러
    """
    # 디렉토리 생성
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        filename=file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding
    )
    handler.setLevel(level)
    
    # 포맷터 선택
    if formatter_type == "json":
        formatter = JSONFormatter()
    elif formatter_type == "structured":
        formatter = StructuredFormatter(include_context=True, colorize=False)
    elif formatter_type == "production":
        formatter = ProductionFormatter()
    else:
        formatter = JSONFormatter()  # 기본값
    
    handler.setFormatter(formatter)
    return handler


def get_timed_rotating_handler(
    file_path: Union[str, Path],
    level: Union[str, int] = logging.INFO,
    when: str = "midnight",
    interval: int = 1,
    backup_count: int = 30,
    formatter_type: str = "json",
    encoding: str = "utf-8"
) -> logging.handlers.TimedRotatingFileHandler:
    """
    시간 기반 로테이션 파일 핸들러 생성
    
    Args:
        file_path: 로그 파일 경로
        level: 로그 레벨
        when: 로테이션 주기 (midnight, H, D, W0-W6)
        interval: 로테이션 간격
        backup_count: 백업 파일 개수
        formatter_type: 포맷터 타입
        encoding: 파일 인코딩
    
    Returns:
        설정된 시간 기반 파일 핸들러
    """
    # 디렉토리 생성
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.TimedRotatingFileHandler(
        filename=file_path,
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding=encoding
    )
    handler.setLevel(level)
    
    # 파일명 접미사 설정 (날짜)
    handler.suffix = "%Y-%m-%d"
    
    # 포맷터 선택
    if formatter_type == "json":
        formatter = JSONFormatter()
    elif formatter_type == "structured":
        formatter = StructuredFormatter(include_context=True, colorize=False)
    else:
        formatter = JSONFormatter()
    
    handler.setFormatter(formatter)
    return handler


def get_error_file_handler(
    file_path: Union[str, Path],
    max_bytes: int = 50 * 1024 * 1024,  # 50MB (에러 로그는 더 크게)
    backup_count: int = 10,
    encoding: str = "utf-8"
) -> logging.handlers.RotatingFileHandler:
    """
    에러 전용 파일 핸들러 생성
    
    Args:
        file_path: 에러 로그 파일 경로
        max_bytes: 최대 파일 크기
        backup_count: 백업 파일 개수
        encoding: 파일 인코딩
    
    Returns:
        에러 레벨 파일 핸들러
    """
    handler = get_file_handler(
        file_path=file_path,
        level=logging.ERROR,
        max_bytes=max_bytes,
        backup_count=backup_count,
        formatter_type="json",
        encoding=encoding
    )
    
    # 에러 레벨만 필터링
    handler.addFilter(lambda record: record.levelno >= logging.ERROR)
    
    return handler


class RequestContextFilter(logging.Filter):
    """요청 컨텍스트 필터 - FastAPI 요청 정보 추가"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """로그 레코드에 요청 컨텍스트 추가"""
        try:
            # FastAPI의 contextvars에서 요청 정보 가져오기 시도
            # 실제 구현에서는 contextvars를 사용하여 요청 ID 등을 추가
            
            # 기본값 설정
            if not hasattr(record, 'ctx_request_id'):
                record.ctx_request_id = "unknown"
            
            if not hasattr(record, 'ctx_user_id'):
                record.ctx_user_id = "anonymous"
                
            if not hasattr(record, 'ctx_endpoint'):
                record.ctx_endpoint = "unknown"
                
        except Exception:
            # 컨텍스트 정보를 가져올 수 없는 경우 기본값 사용
            pass
        
        return True


class PerformanceFilter(logging.Filter):
    """성능 관련 로그만 필터링"""
    
    def __init__(self, min_duration: float = 1.0):
        """
        성능 필터 초기화
        
        Args:
            min_duration: 최소 실행 시간 (초)
        """
        super().__init__()
        self.min_duration = min_duration
    
    def filter(self, record: logging.LogRecord) -> bool:
        """성능 관련 로그만 통과"""
        # duration 필드가 있고 임계값 이상인 경우만 통과
        duration = getattr(record, 'ctx_duration', 0)
        return duration >= self.min_duration


class SensitiveDataFilter(logging.Filter):
    """민감한 데이터 마스킹 필터"""
    
    def __init__(self):
        super().__init__()
        self.sensitive_patterns = [
            'password', 'token', 'secret', 'key', 'auth',
            'credential', 'session', 'cookie'
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """민감한 데이터 마스킹"""
        message = record.getMessage().lower()
        
        # 민감한 패턴이 포함된 경우 마스킹
        for pattern in self.sensitive_patterns:
            if pattern in message:
                # 실제로는 더 정교한 마스킹 로직 구현
                record.msg = record.msg.replace(pattern, f"{pattern[:2]}***")
        
        return True