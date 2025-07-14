"""
Prometheus 메트릭 정의 및 관리
전력시장 RAG 시스템 전용 메트릭
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from typing import Dict, Any, Optional
import time
import psutil
import threading
from datetime import datetime


class PrometheusMetrics:
    """Prometheus 메트릭 컬렉션"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Prometheus 메트릭 초기화
        
        Args:
            registry: 메트릭 레지스트리 (None인 경우 기본 레지스트리 사용)
        """
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        self._last_system_update = 0
        self._system_update_interval = 10  # 10초마다 시스템 메트릭 업데이트
    
    def _setup_metrics(self):
        """메트릭 정의"""
        
        # === API 메트릭 ===
        self.api_requests_total = Counter(
            'rag_api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.api_request_duration = Histogram(
            'rag_api_request_duration_seconds',
            'API request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.api_active_requests = Gauge(
            'rag_api_active_requests',
            'Number of active API requests',
            registry=self.registry
        )
        
        # === RAG 시스템 메트릭 ===
        self.rag_search_requests_total = Counter(
            'rag_search_requests_total',
            'Total number of document search requests',
            ['search_method'],
            registry=self.registry
        )
        
        self.rag_search_duration = Histogram(
            'rag_search_duration_seconds',
            'Document search duration in seconds',
            ['search_method'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.rag_search_results_count = Histogram(
            'rag_search_results_count',
            'Number of search results returned',
            ['search_method'],
            buckets=[1, 5, 10, 20, 50, 100],
            registry=self.registry
        )
        
        self.rag_query_requests_total = Counter(
            'rag_query_requests_total',
            'Total number of Q&A requests',
            ['search_method', 'success'],
            registry=self.registry
        )
        
        self.rag_query_duration = Histogram(
            'rag_query_duration_seconds',
            'Q&A processing duration in seconds',
            ['search_method'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            registry=self.registry
        )
        
        self.rag_confidence_score = Histogram(
            'rag_confidence_score',
            'RAG response confidence score',
            ['search_method'],
            buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 1.0],
            registry=self.registry
        )
        
        # === 캐시 메트릭 ===
        self.cache_operations_total = Counter(
            'rag_cache_operations_total',
            'Total number of cache operations',
            ['operation', 'namespace', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'rag_cache_hit_ratio',
            'Cache hit ratio by namespace',
            ['namespace'],
            registry=self.registry
        )
        
        self.cache_keys_count = Gauge(
            'rag_cache_keys_count',
            'Number of cache keys by namespace',
            ['namespace'],
            registry=self.registry
        )
        
        self.cache_memory_usage = Gauge(
            'rag_cache_memory_usage_bytes',
            'Cache memory usage in bytes',
            registry=self.registry
        )
        
        # === 문서 메트릭 ===
        self.documents_total = Gauge(
            'rag_documents_total',
            'Total number of documents in the system',
            registry=self.registry
        )
        
        self.documents_processed_total = Counter(
            'rag_documents_processed_total',
            'Total number of documents processed',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.document_processing_duration = Histogram(
            'rag_document_processing_duration_seconds',
            'Document processing duration in seconds',
            ['operation'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
            registry=self.registry
        )
        
        # === 사용자 메트릭 ===
        self.active_users = Gauge(
            'rag_active_users',
            'Number of active users',
            registry=self.registry
        )
        
        self.user_sessions_total = Counter(
            'rag_user_sessions_total',
            'Total number of user sessions',
            ['authentication_method'],
            registry=self.registry
        )
        
        self.user_actions_total = Counter(
            'rag_user_actions_total',
            'Total number of user actions',
            ['action_type', 'user_type'],
            registry=self.registry
        )
        
        # === 시스템 메트릭 ===
        self.system_cpu_usage = Gauge(
            'rag_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'rag_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )
        
        self.system_memory_usage_percent = Gauge(
            'rag_system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'rag_system_disk_usage_bytes',
            'System disk usage in bytes',
            ['device'],
            registry=self.registry
        )
        
        self.system_network_bytes = Counter(
            'rag_system_network_bytes_total',
            'System network bytes transferred',
            ['direction'],  # sent, received
            registry=self.registry
        )
        
        # === 에러 메트릭 ===
        self.errors_total = Counter(
            'rag_errors_total',
            'Total number of errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        self.error_rate = Gauge(
            'rag_error_rate',
            'Error rate by component',
            ['component'],
            registry=self.registry
        )
        
        # === 애플리케이션 정보 ===
        self.app_info = Info(
            'rag_app_info',
            'Application information',
            registry=self.registry
        )
        
        self.app_status = Enum(
            'rag_app_status',
            'Application status',
            states=['starting', 'healthy', 'degraded', 'unhealthy'],
            registry=self.registry
        )
        
        # 애플리케이션 정보 설정
        self.app_info.info({
            'version': '1.0.0',
            'service': 'power_market_rag',
            'environment': 'development'
        })
        
        self.app_status.state('healthy')
    
    def update_system_metrics(self):
        """시스템 메트릭 업데이트"""
        current_time = time.time()
        
        # 업데이트 주기 체크
        if current_time - self._last_system_update < self._system_update_interval:
            return
        
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_cpu_usage.set(cpu_percent)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            self.system_memory_usage_percent.set(memory.percent)
            
            # 디스크 사용률
            disk_partitions = psutil.disk_partitions()
            for partition in disk_partitions:
                try:
                    disk_usage = psutil.disk_usage(partition.mountpoint)
                    self.system_disk_usage.labels(device=partition.device).set(disk_usage.used)
                except (PermissionError, FileNotFoundError):
                    # 접근할 수 없는 디스크는 건너뜀
                    continue
            
            # 네트워크 통계
            network = psutil.net_io_counters()
            if network:
                self.system_network_bytes.labels(direction='sent').inc(network.bytes_sent)
                self.system_network_bytes.labels(direction='received').inc(network.bytes_recv)
            
            self._last_system_update = current_time
            
        except Exception as e:
            # 시스템 메트릭 수집 실패는 로그만 남기고 계속 진행
            print(f"시스템 메트릭 업데이트 실패: {e}")
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """API 요청 메트릭 기록"""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint, 
            status_code=status_code
        ).inc()
        
        self.api_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_search_request(self, search_method: str, duration: float, result_count: int):
        """검색 요청 메트릭 기록"""
        self.rag_search_requests_total.labels(search_method=search_method).inc()
        self.rag_search_duration.labels(search_method=search_method).observe(duration)
        self.rag_search_results_count.labels(search_method=search_method).observe(result_count)
    
    def record_query_request(self, search_method: str, duration: float, confidence: float, success: bool):
        """질의 요청 메트릭 기록"""
        self.rag_query_requests_total.labels(
            search_method=search_method,
            success=str(success)
        ).inc()
        
        self.rag_query_duration.labels(search_method=search_method).observe(duration)
        self.rag_confidence_score.labels(search_method=search_method).observe(confidence)
    
    def record_cache_operation(self, operation: str, namespace: str, result: str):
        """캐시 작업 메트릭 기록"""
        self.cache_operations_total.labels(
            operation=operation,
            namespace=namespace,
            result=result
        ).inc()
    
    def update_cache_metrics(self, hit_ratios: Dict[str, float], key_counts: Dict[str, int], memory_usage: int):
        """캐시 메트릭 업데이트"""
        for namespace, ratio in hit_ratios.items():
            self.cache_hit_ratio.labels(namespace=namespace).set(ratio)
        
        for namespace, count in key_counts.items():
            self.cache_keys_count.labels(namespace=namespace).set(count)
        
        self.cache_memory_usage.set(memory_usage)
    
    def record_error(self, error_type: str, component: str):
        """에러 메트릭 기록"""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def update_error_rate(self, component: str, rate: float):
        """에러율 업데이트"""
        self.error_rate.labels(component=component).set(rate)
    
    def set_document_count(self, count: int):
        """문서 수 설정"""
        self.documents_total.set(count)
    
    def record_document_processing(self, operation: str, duration: float, status: str):
        """문서 처리 메트릭 기록"""
        self.documents_processed_total.labels(operation=operation, status=status).inc()
        self.document_processing_duration.labels(operation=operation).observe(duration)
    
    def set_active_users(self, count: int):
        """활성 사용자 수 설정"""
        self.active_users.set(count)
    
    def record_user_session(self, auth_method: str):
        """사용자 세션 기록"""
        self.user_sessions_total.labels(authentication_method=auth_method).inc()
    
    def record_user_action(self, action_type: str, user_type: str):
        """사용자 행동 기록"""
        self.user_actions_total.labels(action_type=action_type, user_type=user_type).inc()
    
    def set_app_status(self, status: str):
        """애플리케이션 상태 설정"""
        self.app_status.state(status)
    
    def get_metrics(self) -> str:
        """Prometheus 형식 메트릭 반환"""
        # 시스템 메트릭 업데이트
        self.update_system_metrics()
        
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """메트릭 컨텐츠 타입 반환"""
        return CONTENT_TYPE_LATEST


# 전역 메트릭 인스턴스
_metrics: Optional[PrometheusMetrics] = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """전역 Prometheus 메트릭 인스턴스 반환"""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics