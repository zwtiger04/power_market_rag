"""
로그 포맷터 구현
JSON 및 구조화된 로그 포맷 제공
"""

import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON 형식 로그 포맷터"""
    
    def __init__(self, include_extra: bool = True):
        """
        JSON 포맷터 초기화
        
        Args:
            include_extra: 추가 필드 포함 여부
        """
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 포맷"""
        # 기본 로그 데이터
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "pathname": record.pathname,
            "filename": record.filename
        }
        
        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # 스택 정보 추가
        if record.stack_info:
            log_data["stack_info"] = record.stack_info
        
        # 추가 필드 포함
        if self.include_extra:
            # 커스텀 필드들 추가
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in log_data and not key.startswith('_'):
                    # 표준 로그 레코드 필드가 아닌 것들만 추가
                    if key not in ['name', 'msg', 'args', 'levelno', 'created', 
                                   'msecs', 'relativeCreated', 'exc_text', 'getMessage']:
                        extra_fields[key] = value
            
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False, default=self._json_serializer)
    
    def _json_serializer(self, obj: Any) -> str:
        """JSON 직렬화가 불가능한 객체 처리"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return repr(obj)


class StructuredFormatter(logging.Formatter):
    """구조화된 텍스트 로그 포맷터"""
    
    def __init__(self, include_context: bool = True, colorize: bool = False):
        """
        구조화된 포맷터 초기화
        
        Args:
            include_context: 컨텍스트 정보 포함 여부
            colorize: 색상 적용 여부 (콘솔 출력용)
        """
        super().__init__()
        self.include_context = include_context
        self.colorize = colorize
        
        # 색상 코드
        self.colors = {
            'DEBUG': '\033[36m',     # 청록색
            'INFO': '\033[32m',      # 녹색
            'WARNING': '\033[33m',   # 노란색
            'ERROR': '\033[31m',     # 빨간색
            'CRITICAL': '\033[35m',  # 마젠타
            'RESET': '\033[0m'       # 리셋
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 구조화된 텍스트로 포맷"""
        # 기본 포맷
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()
        
        # 색상 적용
        if self.colorize:
            level_color = self.colors.get(level, '')
            reset_color = self.colors['RESET']
            level = f"{level_color}{level}{reset_color}"
        
        # 기본 로그 라인
        log_line = f"{timestamp} [{level}] {logger_name}: {message}"
        
        # 컨텍스트 정보 추가
        if self.include_context:
            context_parts = []
            
            # 파일 및 함수 정보
            context_parts.append(f"📍 {record.filename}:{record.lineno} in {record.funcName}()")
            
            # 스레드/프로세스 정보 (기본값이 아닌 경우만)
            if record.thread != 0 or record.process != 0:
                context_parts.append(f"🧵 Thread: {record.threadName}({record.thread}) Process: {record.process}")
            
            # 커스텀 컨텍스트 정보
            custom_context = []
            for key, value in record.__dict__.items():
                if key.startswith('ctx_'):  # ctx_ 접두사로 컨텍스트 필드 식별
                    field_name = key[4:]  # ctx_ 제거
                    custom_context.append(f"{field_name}={value}")
            
            if custom_context:
                context_parts.append(f"🏷️  {', '.join(custom_context)}")
            
            if context_parts:
                log_line += "\n" + "\n".join(f"    {part}" for part in context_parts)
        
        # 예외 정보 추가
        if record.exc_info:
            exc_text = traceback.format_exception(*record.exc_info)
            log_line += "\n" + "".join(exc_text)
        
        # 스택 정보 추가
        if record.stack_info:
            log_line += f"\nStack Info:\n{record.stack_info}"
        
        return log_line


class CompactFormatter(logging.Formatter):
    """간결한 로그 포맷터 (프로덕션용)"""
    
    def format(self, record: logging.LogRecord) -> str:
        """간결한 형식으로 로그 포맷"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        level_short = record.levelname[0]  # 레벨 첫 글자만
        message = record.getMessage()
        
        # 간결한 포맷: HH:MM:SS [L] module: message
        return f"{timestamp} [{level_short}] {record.module}: {message}"


class DevelopmentFormatter(StructuredFormatter):
    """개발 환경용 포맷터 (색상 + 상세 정보)"""
    
    def __init__(self):
        super().__init__(include_context=True, colorize=True)


class ProductionFormatter(JSONFormatter):
    """프로덕션 환경용 포맷터 (JSON + 모든 정보)"""
    
    def __init__(self):
        super().__init__(include_extra=True)