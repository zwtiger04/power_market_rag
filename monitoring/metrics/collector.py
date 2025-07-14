"""
메트릭 수집기 메인 클래스
다양한 메트릭 소스를 통합 관리
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict

from .prometheus_metrics import get_prometheus_metrics, PrometheusMetrics


class MetricsCollector:
    """중앙 메트릭 수집기"""
    
    def __init__(self):
        """메트릭 수집기 초기화"""
        self.prometheus = get_prometheus_metrics()
        self._active_requests = 0
        self._request_queue = deque(maxlen=1000)  # 최근 1000개 요청 추적
        self._error_queue = deque(maxlen=1000)    # 최근 1000개 에러 추적
        self._custom_metrics = defaultdict(list)
        self._metrics_lock = threading.Lock()
        
        # 성능 카운터
        self._performance_counters = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'search_requests': 0,
            'query_requests': 0,
            'errors': 0
        }
    
    def start_request(self) -> str:
        """API 요청 시작 추적"""
        request_id = f"req_{int(time.time() * 1000000)}"
        
        with self._metrics_lock:
            self._active_requests += 1
            self._performance_counters['api_calls'] += 1
        
        self.prometheus.api_active_requests.set(self._active_requests)
        return request_id
    
    def end_request(self, request_id: str, method: str, endpoint: str, 
                   status_code: int, duration: float):
        """API 요청 종료 추적"""
        with self._metrics_lock:
            self._active_requests = max(0, self._active_requests - 1)
            
            # 요청 이력 저장
            request_data = {
                'id': request_id,
                'method': method,
                'endpoint': endpoint,
                'status_code': status_code,
                'duration': duration,
                'timestamp': datetime.now()
            }
            self._request_queue.append(request_data)
        
        # Prometheus 메트릭 기록
        self.prometheus.api_active_requests.set(self._active_requests)
        self.prometheus.record_api_request(method, endpoint, status_code, duration)
    
    def record_search_metrics(self, search_method: str, duration: float, 
                            result_count: int, success: bool = True):
        """검색 메트릭 기록"""
        with self._metrics_lock:
            self._performance_counters['search_requests'] += 1
        
        self.prometheus.record_search_request(search_method, duration, result_count)
        
        if not success:
            self.record_error('search_failed', 'rag_search')
    
    def record_query_metrics(self, search_method: str, duration: float, 
                           confidence: float, success: bool = True):
        """질의 메트릭 기록"""
        with self._metrics_lock:
            self._performance_counters['query_requests'] += 1
        
        self.prometheus.record_query_request(search_method, duration, confidence, success)
        
        if not success:
            self.record_error('query_failed', 'rag_query')
    
    def record_cache_hit(self, namespace: str):
        """캐시 히트 기록"""
        with self._metrics_lock:
            self._performance_counters['cache_hits'] += 1
        
        self.prometheus.record_cache_operation('get', namespace, 'hit')
    
    def record_cache_miss(self, namespace: str):
        """캐시 미스 기록"""
        with self._metrics_lock:
            self._performance_counters['cache_misses'] += 1
        
        self.prometheus.record_cache_operation('get', namespace, 'miss')
    
    def record_cache_set(self, namespace: str, success: bool = True):
        """캐시 저장 기록"""
        result = 'success' if success else 'failed'
        self.prometheus.record_cache_operation('set', namespace, result)
    
    def record_cache_delete(self, namespace: str, count: int = 1):
        """캐시 삭제 기록"""
        for _ in range(count):
            self.prometheus.record_cache_operation('delete', namespace, 'success')
    
    def update_cache_statistics(self, cache_stats: Dict[str, Any]):
        """캐시 통계 업데이트"""
        # 네임스페이스별 히트율 계산
        hit_ratios = {}
        key_counts = {}
        
        # cache_stats에서 네임스페이스별 정보 추출
        # 실제 구현에서는 캐시 시스템에서 제공하는 통계 사용
        operations = cache_stats.get('operations', {})
        total_hits = operations.get('hits', 0)
        total_misses = operations.get('misses', 0)
        
        if total_hits + total_misses > 0:
            overall_hit_ratio = total_hits / (total_hits + total_misses)
            # 기본 네임스페이스들에 대해 동일한 비율 적용 (실제로는 개별 추적)
            for namespace in ['search', 'query', 'user', 'system']:
                hit_ratios[namespace] = overall_hit_ratio
                key_counts[namespace] = 10  # 임시값
        
        memory_usage = cache_stats.get('redis_info', {}).get('used_memory', 0)
        if isinstance(memory_usage, str):
            # 문자열 형태의 메모리 크기를 바이트로 변환
            memory_usage = self._parse_memory_size(memory_usage)
        
        self.prometheus.update_cache_metrics(hit_ratios, key_counts, memory_usage)
    
    def record_error(self, error_type: str, component: str):
        """에러 기록"""
        with self._metrics_lock:
            self._performance_counters['errors'] += 1
            
            error_data = {
                'type': error_type,
                'component': component,
                'timestamp': datetime.now()
            }
            self._error_queue.append(error_data)
        
        self.prometheus.record_error(error_type, component)
    
    def record_document_processing(self, operation: str, duration: float, 
                                 success: bool = True):
        """문서 처리 메트릭 기록"""
        status = 'success' if success else 'failed'
        self.prometheus.record_document_processing(operation, duration, status)
    
    def update_document_count(self, count: int):
        """문서 수 업데이트"""
        self.prometheus.set_document_count(count)
    
    def record_user_activity(self, user_id: str, action: str, user_type: str = 'regular'):
        """사용자 활동 기록"""
        self.prometheus.record_user_action(action, user_type)
    
    def update_active_users(self, count: int):
        """활성 사용자 수 업데이트"""
        self.prometheus.set_active_users(count)
    
    def record_user_session(self, auth_method: str = 'jwt'):
        """사용자 세션 기록"""
        self.prometheus.record_user_session(auth_method)
    
    def add_custom_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """커스텀 메트릭 추가"""
        metric_data = {
            'value': value,
            'labels': labels or {},
            'timestamp': datetime.now()
        }
        
        with self._metrics_lock:
            self._custom_metrics[name].append(metric_data)
            # 최대 100개까지만 보관
            if len(self._custom_metrics[name]) > 100:
                self._custom_metrics[name] = self._custom_metrics[name][-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """성능 요약 정보 반환"""
        with self._metrics_lock:
            counters = self._performance_counters.copy()
            active_requests = self._active_requests
        
        # 최근 요청들의 평균 응답시간 계산
        recent_requests = list(self._request_queue)[-100:]  # 최근 100개
        avg_response_time = 0
        if recent_requests:
            total_duration = sum(req['duration'] for req in recent_requests)
            avg_response_time = total_duration / len(recent_requests)
        
        # 최근 에러율 계산
        now = datetime.now()
        recent_errors = [
            err for err in self._error_queue 
            if now - err['timestamp'] < timedelta(minutes=5)
        ]
        recent_requests_5min = [
            req for req in self._request_queue
            if now - req['timestamp'] < timedelta(minutes=5)
        ]
        
        error_rate = 0
        if recent_requests_5min:
            error_rate = len(recent_errors) / len(recent_requests_5min) * 100
        
        # 캐시 히트율 계산
        cache_hit_rate = 0
        total_cache_ops = counters['cache_hits'] + counters['cache_misses']
        if total_cache_ops > 0:
            cache_hit_rate = counters['cache_hits'] / total_cache_ops * 100
        
        return {
            'active_requests': active_requests,
            'total_api_calls': counters['api_calls'],
            'total_search_requests': counters['search_requests'],
            'total_query_requests': counters['query_requests'],
            'total_errors': counters['errors'],
            'avg_response_time': round(avg_response_time, 4),
            'error_rate_5min': round(error_rate, 2),
            'cache_hit_rate': round(cache_hit_rate, 2),
            'cache_hits': counters['cache_hits'],
            'cache_misses': counters['cache_misses']
        }
    
    def get_error_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """에러 요약 정보 반환"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=minutes)
        
        recent_errors = [
            err for err in self._error_queue
            if err['timestamp'] > cutoff
        ]
        
        # 에러 타입별 집계
        error_by_type = defaultdict(int)
        error_by_component = defaultdict(int)
        
        for error in recent_errors:
            error_by_type[error['type']] += 1
            error_by_component[error['component']] += 1
        
        return {
            'total_errors': len(recent_errors),
            'time_window_minutes': minutes,
            'errors_by_type': dict(error_by_type),
            'errors_by_component': dict(error_by_component),
            'latest_errors': recent_errors[-10:]  # 최근 10개 에러
        }
    
    def get_request_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """요청 요약 정보 반환"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=minutes)
        
        recent_requests = [
            req for req in self._request_queue
            if req['timestamp'] > cutoff
        ]
        
        if not recent_requests:
            return {
                'total_requests': 0,
                'time_window_minutes': minutes
            }
        
        # 통계 계산
        durations = [req['duration'] for req in recent_requests]
        status_codes = defaultdict(int)
        endpoints = defaultdict(int)
        
        for req in recent_requests:
            status_codes[req['status_code']] += 1
            endpoints[req['endpoint']] += 1
        
        return {
            'total_requests': len(recent_requests),
            'time_window_minutes': minutes,
            'avg_duration': round(sum(durations) / len(durations), 4),
            'min_duration': round(min(durations), 4),
            'max_duration': round(max(durations), 4),
            'requests_by_status': dict(status_codes),
            'requests_by_endpoint': dict(endpoints)
        }
    
    def get_prometheus_metrics(self) -> str:
        """Prometheus 형식 메트릭 반환"""
        return self.prometheus.get_metrics()
    
    def _parse_memory_size(self, size_str: str) -> int:
        """메모리 크기 문자열을 바이트로 변환"""
        if not size_str:
            return 0
        
        size_str = size_str.upper()
        multipliers = {
            'B': 1,
            'K': 1024,
            'M': 1024 ** 2,
            'G': 1024 ** 3
        }
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    number = float(size_str[:-1])
                    return int(number * multiplier)
                except ValueError:
                    return 0
        
        # 숫자만 있는 경우 바이트로 간주
        try:
            return int(float(size_str))
        except ValueError:
            return 0


# 전역 메트릭 수집기 인스턴스
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """전역 메트릭 수집기 인스턴스 반환"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector