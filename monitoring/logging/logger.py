"""
메인 로거 클래스 및 설정
전력시장 RAG 시스템의 중앙 로깅 관리
"""

import logging
import uuid
import time
import functools
from contextlib import contextmanager
from typing import Dict, Any, Optional, Union, Callable
from pathlib import Path
from datetime import datetime

from .handlers import (
    get_console_handler, 
    get_file_handler, 
    get_timed_rotating_handler,
    get_error_file_handler,
    RequestContextFilter,
    SensitiveDataFilter
)


class LogContext:
    """로그 컨텍스트 관리 클래스"""
    
    def __init__(self):
        self._context: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any) -> None:
        """컨텍스트 값 설정"""
        self._context[f"ctx_{key}"] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """컨텍스트 값 조회"""
        return self._context.get(f"ctx_{key}", default)
    
    def update(self, **kwargs) -> None:
        """여러 컨텍스트 값 업데이트"""
        for key, value in kwargs.items():
            self.set(key, value)
    
    def clear(self) -> None:
        """컨텍스트 초기화"""
        self._context.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """컨텍스트를 딕셔너리로 반환"""
        return self._context.copy()
    
    @contextmanager
    def bind(self, **kwargs):
        """임시 컨텍스트 바인딩"""
        old_context = self._context.copy()
        try:
            self.update(**kwargs)
            yield self
        finally:
            self._context = old_context


class Logger:
    """중앙 로거 클래스"""
    
    def __init__(self, name: str):
        """
        로거 초기화
        
        Args:
            name: 로거 이름
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.context = LogContext()
        
        # 기본 컨텍스트 설정
        self.context.set("service", "power_market_rag")
        self.context.set("version", "1.0.0")
    
    def _log_with_context(self, level: int, message: str, *args, **kwargs):
        """컨텍스트와 함께 로그 기록"""
        # 현재 컨텍스트를 extra에 추가
        context_data = self.context.to_dict()
        
        # 추가 컨텍스트 정보
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(context_data)
        
        self.logger.log(level, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        """디버그 로그"""
        self._log_with_context(logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """정보 로그"""
        self._log_with_context(logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """경고 로그"""
        self._log_with_context(logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """에러 로그"""
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """심각한 에러 로그"""
        self._log_with_context(logging.CRITICAL, message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """예외 로그 (스택 트레이스 포함)"""
        kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, *args, **kwargs)
    
    @contextmanager
    def bind(self, **kwargs):
        """임시 컨텍스트 바인딩"""
        with self.context.bind(**kwargs):
            yield self
    
    def bind_context(self, **kwargs) -> 'Logger':
        """새로운 컨텍스트로 바인딩된 로거 반환"""
        new_logger = Logger(self.name)
        new_logger.context._context = self.context.to_dict()
        new_logger.context.update(**kwargs)
        return new_logger
    
    def timer(self, operation: str):
        """시간 측정 컨텍스트 매니저"""
        return LogTimer(self, operation)
    
    def log_function_call(
        self, 
        include_args: bool = True, 
        include_result: bool = False,
        log_level: int = logging.DEBUG
    ):
        """함수 호출 로깅 데코레이터"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                func_name = f"{func.__module__}.{func.__qualname__}"
                
                # 함수 호출 시작 로그
                log_data = {"function": func_name}
                if include_args:
                    log_data["args"] = str(args)
                    log_data["kwargs"] = str(kwargs)
                
                with self.bind(**log_data):
                    start_time = time.time()
                    self._log_with_context(log_level, f"함수 호출 시작: {func_name}")
                    
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        # 함수 호출 완료 로그
                        completion_data = {
                            "function": func_name,
                            "duration": round(duration, 4),
                            "status": "success"
                        }
                        
                        if include_result:
                            completion_data["result"] = str(result)
                        
                        with self.bind(**completion_data):
                            self._log_with_context(
                                log_level, 
                                f"함수 호출 완료: {func_name} ({duration:.4f}s)"
                            )
                        
                        return result
                        
                    except Exception as e:
                        duration = time.time() - start_time
                        error_data = {
                            "function": func_name,
                            "duration": round(duration, 4),
                            "status": "error",
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                        
                        with self.bind(**error_data):
                            self.exception(f"함수 호출 실패: {func_name} ({duration:.4f}s)")
                        
                        raise
            
            return wrapper
        return decorator


class LogTimer:
    """로그 타이머 컨텍스트 매니저"""
    
    def __init__(self, logger: Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"작업 시작: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # 성공
            with self.logger.bind(operation=self.operation, duration=duration, status="success"):
                self.logger.info(f"작업 완료: {self.operation} ({duration:.4f}s)")
        else:
            # 실패
            with self.logger.bind(operation=self.operation, duration=duration, status="error"):
                self.logger.error(f"작업 실패: {self.operation} ({duration:.4f}s)")


# 전역 로거 인스턴스 관리
_loggers: Dict[str, Logger] = {}


def get_logger(name: str = None) -> Logger:
    """
    로거 인스턴스 반환 (싱글톤)
    
    Args:
        name: 로거 이름 (기본: 호출 모듈명)
    
    Returns:
        Logger 인스턴스
    """
    if name is None:
        # 호출자의 모듈명 사용
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get('__name__', 'unknown')
    
    if name not in _loggers:
        _loggers[name] = Logger(name)
    
    return _loggers[name]


def setup_logging(
    level: Union[str, int] = logging.INFO,
    log_dir: Union[str, Path] = "./logs",
    app_name: str = "power_market_rag",
    enable_console: bool = True,
    enable_file: bool = True,
    enable_error_file: bool = True,
    console_format: str = "development",
    file_format: str = "json",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    environment: str = "development"
) -> None:
    """
    전역 로깅 설정
    
    Args:
        level: 로그 레벨
        log_dir: 로그 파일 디렉토리
        app_name: 애플리케이션 이름
        enable_console: 콘솔 로그 활성화
        enable_file: 파일 로그 활성화
        enable_error_file: 에러 파일 로그 활성화
        console_format: 콘솔 포맷터 타입
        file_format: 파일 포맷터 타입
        max_file_size: 최대 파일 크기
        backup_count: 백업 파일 개수
        environment: 환경 (development, production)
    """
    # 로그 디렉토리 생성
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handlers = []
    
    # 콘솔 핸들러
    if enable_console:
        console_handler = get_console_handler(
            level=level,
            use_colors=(environment == "development"),
            formatter_type=console_format
        )
        handlers.append(console_handler)
    
    # 파일 핸들러
    if enable_file:
        app_log_file = log_dir / f"{app_name}.log"
        file_handler = get_file_handler(
            file_path=app_log_file,
            level=level,
            max_bytes=max_file_size,
            backup_count=backup_count,
            formatter_type=file_format
        )
        handlers.append(file_handler)
    
    # 에러 파일 핸들러
    if enable_error_file:
        error_log_file = log_dir / f"{app_name}_error.log"
        error_handler = get_error_file_handler(
            file_path=error_log_file,
            max_bytes=max_file_size * 5,  # 에러 로그는 더 크게
            backup_count=backup_count * 2
        )
        handlers.append(error_handler)
    
    # 핸들러들에 필터 추가
    request_filter = RequestContextFilter()
    sensitive_filter = SensitiveDataFilter()
    
    for handler in handlers:
        handler.addFilter(request_filter)
        handler.addFilter(sensitive_filter)
        root_logger.addHandler(handler)
    
    # 라이브러리 로그 레벨 조정
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # 시작 로그
    logger = get_logger("setup")
    logger.info(f"로깅 시스템 초기화 완료 - 환경: {environment}, 레벨: {logging.getLevelName(level)}")


# 편의 함수들
def log_performance(operation: str):
    """성능 측정 데코레이터"""
    def decorator(func: Callable):
        logger = get_logger(func.__module__)
        return logger.log_function_call(
            include_args=False,
            include_result=False,
            log_level=logging.INFO
        )(func)
    return decorator


def log_api_call(include_request: bool = True, include_response: bool = False):
    """API 호출 로깅 데코레이터"""
    def decorator(func: Callable):
        logger = get_logger(func.__module__)
        return logger.log_function_call(
            include_args=include_request,
            include_result=include_response,
            log_level=logging.INFO
        )(func)
    return decorator