"""
메트릭 수집 데코레이터
함수 및 메서드에 쉽게 메트릭을 추가할 수 있는 데코레이터 제공
"""

import time
import functools
from typing import Callable, Optional, Dict, Any
from .collector import get_metrics_collector


def time_metric(
    metric_name: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    include_success: bool = True
):
    """
    함수 실행 시간을 측정하는 데코레이터
    
    Args:
        metric_name: 메트릭 이름 (None인 경우 함수명 사용)
        labels: 추가 라벨
        include_success: 성공/실패 여부 포함
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            name = metric_name or f"{func.__module__}.{func.__qualname__}"
            
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                
                # 기본 라벨
                metric_labels = labels.copy() if labels else {}
                if include_success:
                    metric_labels['success'] = str(success)
                    if error_type:
                        metric_labels['error_type'] = error_type
                
                # 커스텀 메트릭으로 기록
                metrics.add_custom_metric(f"{name}_duration", duration, metric_labels)
                
                # 함수 유형별 특별 처리
                if 'search' in name.lower():
                    metrics.record_search_metrics(
                        search_method=metric_labels.get('method', 'unknown'),
                        duration=duration,
                        result_count=metric_labels.get('result_count', 0),
                        success=success
                    )
                elif 'query' in name.lower() or 'ask' in name.lower():
                    metrics.record_query_metrics(
                        search_method=metric_labels.get('method', 'unknown'),
                        duration=duration,
                        confidence=metric_labels.get('confidence', 0.0),
                        success=success
                    )
        
        return wrapper
    return decorator


def count_metric(
    metric_name: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    increment: int = 1
):
    """
    함수 호출 횟수를 카운트하는 데코레이터
    
    Args:
        metric_name: 메트릭 이름
        labels: 추가 라벨
        increment: 증가값
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            name = metric_name or f"{func.__module__}.{func.__qualname__}_calls"
            
            # 함수 실행 전 카운트
            metric_labels = labels.copy() if labels else {}
            metrics.add_custom_metric(name, increment, metric_labels)
            
            try:
                result = func(*args, **kwargs)
                
                # 성공 카운트
                success_labels = metric_labels.copy()
                success_labels['status'] = 'success'
                metrics.add_custom_metric(f"{name}_success", increment, success_labels)
                
                return result
            except Exception as e:
                # 에러 카운트
                error_labels = metric_labels.copy()
                error_labels['status'] = 'error'
                error_labels['error_type'] = type(e).__name__
                metrics.add_custom_metric(f"{name}_error", increment, error_labels)
                raise
        
        return wrapper
    return decorator


def gauge_metric(
    metric_name: Optional[str] = None,
    value_func: Optional[Callable] = None,
    labels: Optional[Dict[str, str]] = None
):
    """
    게이지 메트릭을 기록하는 데코레이터
    
    Args:
        metric_name: 메트릭 이름
        value_func: 값을 계산하는 함수 (None인 경우 반환값 사용)
        labels: 추가 라벨
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            name = metric_name or f"{func.__module__}.{func.__qualname__}_gauge"
            
            result = func(*args, **kwargs)
            
            # 게이지 값 계산
            if value_func:
                value = value_func(result)
            elif isinstance(result, (int, float)):
                value = float(result)
            elif isinstance(result, (list, tuple)):
                value = float(len(result))
            elif isinstance(result, dict) and 'count' in result:
                value = float(result['count'])
            else:
                value = 1.0  # 기본값
            
            # 메트릭 기록
            metric_labels = labels.copy() if labels else {}
            metrics.add_custom_metric(name, value, metric_labels)
            
            return result
        
        return wrapper
    return decorator


def api_metrics(
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    track_active: bool = True
):
    """
    API 엔드포인트 메트릭을 자동으로 기록하는 데코레이터
    
    Args:
        endpoint: API 엔드포인트 이름
        method: HTTP 메서드
        track_active: 활성 요청 추적 여부
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            
            # API 정보 추출
            api_endpoint = endpoint or func.__name__
            api_method = method or 'GET'
            
            # 요청 시작
            request_id = metrics.start_request() if track_active else None
            start_time = time.time()
            status_code = 200
            
            try:
                result = func(*args, **kwargs)
                
                # FastAPI Response 객체에서 상태 코드 추출 시도
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                
                return result
            except Exception as e:
                status_code = 500
                # 특정 예외 타입에 따른 상태 코드 매핑
                if 'NotFound' in type(e).__name__:
                    status_code = 404
                elif 'Unauthorized' in type(e).__name__:
                    status_code = 401
                elif 'Forbidden' in type(e).__name__:
                    status_code = 403
                elif 'ValidationError' in type(e).__name__:
                    status_code = 422
                
                raise
            finally:
                duration = time.time() - start_time
                
                # 요청 종료
                if track_active and request_id:
                    metrics.end_request(
                        request_id, api_method, api_endpoint, status_code, duration
                    )
        
        return wrapper
    return decorator


def cache_metrics(namespace: str):
    """
    캐시 작업 메트릭을 자동으로 기록하는 데코레이터
    
    Args:
        namespace: 캐시 네임스페이스
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            func_name = func.__name__.lower()
            
            if 'get' in func_name or 'retrieve' in func_name:
                # 캐시 조회 작업
                result = func(*args, **kwargs)
                
                if result is not None:
                    metrics.record_cache_hit(namespace)
                else:
                    metrics.record_cache_miss(namespace)
                
                return result
            
            elif 'set' in func_name or 'cache' in func_name or 'store' in func_name:
                # 캐시 저장 작업
                try:
                    result = func(*args, **kwargs)
                    success = bool(result)
                    metrics.record_cache_set(namespace, success)
                    return result
                except Exception:
                    metrics.record_cache_set(namespace, False)
                    raise
            
            elif 'delete' in func_name or 'clear' in func_name or 'remove' in func_name:
                # 캐시 삭제 작업
                result = func(*args, **kwargs)
                count = result if isinstance(result, int) else 1
                metrics.record_cache_delete(namespace, count)
                return result
            
            else:
                # 기타 캐시 작업
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def error_tracking(component: str):
    """
    에러 추적 데코레이터
    
    Args:
        component: 컴포넌트 이름
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_type = type(e).__name__
                metrics.record_error(error_type, component)
                raise
        
        return wrapper
    return decorator


def performance_monitor(
    slow_threshold: float = 1.0,
    log_slow: bool = True
):
    """
    성능 모니터링 데코레이터
    
    Args:
        slow_threshold: 느린 함수 임계값 (초)
        log_slow: 느린 함수 로깅 여부
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                if duration > slow_threshold:
                    metrics = get_metrics_collector()
                    
                    # 느린 함수 메트릭 기록
                    metrics.add_custom_metric(
                        'slow_function_calls',
                        1.0,
                        {
                            'function': f"{func.__module__}.{func.__qualname__}",
                            'duration': str(round(duration, 4)),
                            'threshold': str(slow_threshold)
                        }
                    )
                    
                    if log_slow:
                        # 로깅 (실제 구현에서는 로거 사용)
                        print(f"느린 함수 감지: {func.__qualname__} ({duration:.4f}s)")
        
        return wrapper
    return decorator


# 자주 사용되는 메트릭 데코레이터 조합
def rag_search_metrics(search_method: str = 'unknown'):
    """RAG 검색 전용 메트릭 데코레이터"""
    return time_metric(
        labels={'method': search_method, 'operation': 'search'},
        include_success=True
    )


def rag_query_metrics(search_method: str = 'unknown'):
    """RAG 질의 전용 메트릭 데코레이터"""
    return time_metric(
        labels={'method': search_method, 'operation': 'query'},
        include_success=True
    )


def document_processing_metrics(operation: str):
    """문서 처리 전용 메트릭 데코레이터"""
    def decorator(func: Callable):
        @time_metric(labels={'operation': operation})
        @error_tracking('document_processor')
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_metrics_collector()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_document_processing(operation, duration, True)
                return result
            except Exception:
                duration = time.time() - start_time
                metrics.record_document_processing(operation, duration, False)
                raise
        
        return wrapper
    return decorator