"""
차트 데이터 제공자
메트릭을 차트에 적합한 형태로 변환
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict


class ChartDataProvider:
    """차트 데이터 제공자"""
    
    def __init__(self, max_data_points: int = 100):
        """
        차트 데이터 제공자 초기화
        
        Args:
            max_data_points: 최대 데이터 포인트 수
        """
        self.max_data_points = max_data_points
        self._time_series_data = defaultdict(lambda: deque(maxlen=max_data_points))
        self._latest_metrics = {}
    
    def add_metrics(self, metrics: Dict[str, Any], timestamp: Optional[datetime] = None):
        """메트릭 데이터 추가"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # 플랫 구조로 메트릭 변환
        flat_metrics = self._flatten_metrics(metrics)
        
        # 시계열 데이터에 추가
        for key, value in flat_metrics.items():
            if isinstance(value, (int, float)):
                data_point = {
                    'timestamp': timestamp.isoformat(),
                    'value': float(value)
                }
                self._time_series_data[key].append(data_point)
        
        # 최신 메트릭 업데이트
        self._latest_metrics = flat_metrics
        self._latest_metrics['timestamp'] = timestamp.isoformat()
    
    def _flatten_metrics(self, metrics: Dict[str, Any], prefix: str = '') -> Dict[str, Any]:
        """중첩된 메트릭을 플랫 구조로 변환"""
        result = {}
        
        for key, value in metrics.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # 재귀적으로 중첩된 딕셔너리 처리
                result.update(self._flatten_metrics(value, full_key))
            elif isinstance(value, (int, float)):
                result[full_key] = value
            elif isinstance(value, str):
                # 문자열을 숫자로 변환 시도
                try:
                    result[full_key] = float(value)
                except ValueError:
                    pass
        
        return result
    
    def get_time_series(self, metric_name: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """특정 메트릭의 시계열 데이터 반환"""
        data = list(self._time_series_data.get(metric_name, []))
        
        if not data:
            return []
        
        # 시간 필터링
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        filtered_data = [
            point for point in data
            if datetime.fromisoformat(point['timestamp']) > cutoff_time
        ]
        
        return filtered_data
    
    def get_latest_values(self) -> Dict[str, Any]:
        """최신 메트릭 값들 반환"""
        return self._latest_metrics.copy()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드용 통합 데이터 반환"""
        latest = self.get_latest_values()
        
        return {
            'overview': self._get_overview_data(latest),
            'system': self._get_system_data(latest),
            'api': self._get_api_data(latest),
            'rag': self._get_rag_data(latest),
            'cache': self._get_cache_data(latest),
            'errors': self._get_error_data(latest),
            'charts': self._get_chart_data()
        }
    
    def _get_overview_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """개요 데이터"""
        return {
            'system_status': self._determine_system_status(latest),
            'uptime': self._get_uptime(),
            'active_requests': latest.get('api.active_requests', 0),
            'total_requests': latest.get('api.total_requests', 0),
            'error_rate': latest.get('api.error_rate', 0),
            'cache_hit_rate': latest.get('cache.hit_rate', 0),
            'cpu_usage': latest.get('cpu.usage_percent', 0),
            'memory_usage': latest.get('memory.virtual.percent', 0)
        }
    
    def _get_system_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """시스템 메트릭 데이터"""
        return {
            'cpu': {
                'usage_percent': latest.get('cpu.usage_percent', 0),
                'load_average': latest.get('cpu.load_average', 0),
                'cores': latest.get('cpu.count_logical', 0)
            },
            'memory': {
                'usage_percent': latest.get('memory.virtual.percent', 0),
                'used_gb': latest.get('memory.virtual.used', 0) / (1024**3),
                'total_gb': latest.get('memory.virtual.total', 0) / (1024**3),
                'available_gb': latest.get('memory.virtual.available', 0) / (1024**3)
            },
            'disk': {
                'usage_percent': latest.get('disk.usage./.percent', 0),
                'used_gb': latest.get('disk.usage./.used', 0) / (1024**3),
                'free_gb': latest.get('disk.usage./.free', 0) / (1024**3)
            },
            'network': {
                'bytes_sent_per_sec': latest.get('network.bytes_sent_per_sec', 0),
                'bytes_recv_per_sec': latest.get('network.bytes_recv_per_sec', 0),
                'connections': latest.get('network.connections_count', 0)
            }
        }
    
    def _get_api_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """API 메트릭 데이터"""
        return {
            'requests': {
                'active': latest.get('api.active_requests', 0),
                'total': latest.get('api.total_requests', 0),
                'per_minute': self._calculate_rate('api.total_requests', 60)
            },
            'performance': {
                'avg_response_time': latest.get('api.avg_response_time', 0),
                'p95_response_time': latest.get('api.p95_response_time', 0),
                'error_rate': latest.get('api.error_rate', 0)
            },
            'endpoints': self._get_endpoint_stats(latest)
        }
    
    def _get_rag_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """RAG 시스템 메트릭 데이터"""
        return {
            'queries': {
                'total': latest.get('rag.query_requests', 0),
                'search_total': latest.get('rag.search_requests', 0),
                'avg_confidence': latest.get('rag.avg_confidence', 0)
            },
            'performance': {
                'avg_search_time': latest.get('rag.avg_search_time', 0),
                'avg_query_time': latest.get('rag.avg_query_time', 0),
                'success_rate': latest.get('rag.success_rate', 0)
            },
            'documents': {
                'total': latest.get('rag.document_count', 0),
                'processed_today': latest.get('rag.documents_processed_today', 0)
            }
        }
    
    def _get_cache_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """캐시 메트릭 데이터"""
        return {
            'performance': {
                'hit_rate': latest.get('cache.hit_rate', 0),
                'hits': latest.get('cache.hits', 0),
                'misses': latest.get('cache.misses', 0),
                'total_operations': latest.get('cache.hits', 0) + latest.get('cache.misses', 0)
            },
            'memory': {
                'used_mb': latest.get('cache.memory_usage', 0) / (1024**2),
                'keys_count': latest.get('cache.keys_count', 0)
            },
            'namespaces': self._get_cache_namespace_stats(latest)
        }
    
    def _get_error_data(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """에러 메트릭 데이터"""
        return {
            'total_errors': latest.get('errors.total', 0),
            'error_rate': latest.get('api.error_rate', 0),
            'errors_by_component': {
                'api': latest.get('errors.api', 0),
                'rag': latest.get('errors.rag', 0),
                'cache': latest.get('errors.cache', 0),
                'system': latest.get('errors.system', 0)
            },
            'recent_errors': self._get_recent_errors()
        }
    
    def _get_chart_data(self) -> Dict[str, Any]:
        """차트용 시계열 데이터"""
        return {
            'cpu_usage': self.get_time_series('cpu.usage_percent', 60),
            'memory_usage': self.get_time_series('memory.virtual.percent', 60),
            'api_requests': self.get_time_series('api.active_requests', 60),
            'response_time': self.get_time_series('api.avg_response_time', 60),
            'error_rate': self.get_time_series('api.error_rate', 60),
            'cache_hit_rate': self.get_time_series('cache.hit_rate', 60),
            'rag_confidence': self.get_time_series('rag.avg_confidence', 60)
        }
    
    def _determine_system_status(self, latest: Dict[str, Any]) -> str:
        """시스템 상태 결정"""
        cpu_usage = latest.get('cpu.usage_percent', 0)
        memory_usage = latest.get('memory.virtual.percent', 0)
        error_rate = latest.get('api.error_rate', 0)
        
        if cpu_usage > 90 or memory_usage > 95 or error_rate > 10:
            return 'critical'
        elif cpu_usage > 75 or memory_usage > 85 or error_rate > 5:
            return 'warning'
        elif cpu_usage > 50 or memory_usage > 70 or error_rate > 1:
            return 'degraded'
        else:
            return 'healthy'
    
    def _get_uptime(self) -> str:
        """시스템 업타임 반환 (임시 구현)"""
        # 실제로는 시스템 시작 시간을 추적해야 함
        return "2일 14시간 32분"
    
    def _calculate_rate(self, metric_name: str, window_minutes: int) -> float:
        """지정된 시간 창에서의 메트릭 변화율 계산"""
        data = self.get_time_series(metric_name, window_minutes)
        
        if len(data) < 2:
            return 0.0
        
        first_value = data[0]['value']
        last_value = data[-1]['value']
        
        if window_minutes > 0:
            return (last_value - first_value) / window_minutes
        
        return 0.0
    
    def _get_endpoint_stats(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """엔드포인트별 통계 (임시 구현)"""
        return {
            '/ask': {'requests': 1250, 'avg_time': 1.2, 'error_rate': 2.1},
            '/search': {'requests': 800, 'avg_time': 0.8, 'error_rate': 1.5},
            '/status': {'requests': 150, 'avg_time': 0.1, 'error_rate': 0.0}
        }
    
    def _get_cache_namespace_stats(self, latest: Dict[str, Any]) -> Dict[str, Any]:
        """캐시 네임스페이스별 통계 (임시 구현)"""
        return {
            'search': {'hit_rate': 82.5, 'keys': 1500},
            'query': {'hit_rate': 75.2, 'keys': 900},
            'user': {'hit_rate': 65.8, 'keys': 300},
            'system': {'hit_rate': 95.1, 'keys': 50}
        }
    
    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """최근 에러 목록 (임시 구현)"""
        return [
            {
                'timestamp': '2024-07-11T14:30:25',
                'type': 'TimeoutError',
                'component': 'rag_search',
                'message': 'Document search timeout'
            },
            {
                'timestamp': '2024-07-11T14:25:18',
                'type': 'ValidationError',
                'component': 'api',
                'message': 'Invalid request format'
            }
        ]
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """실시간 메트릭 (WebSocket용)"""
        latest = self.get_latest_values()
        
        return {
            'timestamp': latest.get('timestamp'),
            'metrics': {
                'cpu_usage': latest.get('cpu.usage_percent', 0),
                'memory_usage': latest.get('memory.virtual.percent', 0),
                'active_requests': latest.get('api.active_requests', 0),
                'response_time': latest.get('api.avg_response_time', 0),
                'error_rate': latest.get('api.error_rate', 0),
                'cache_hit_rate': latest.get('cache.hit_rate', 0)
            }
        }
    
    def get_metric_history(self, metric_names: List[str], minutes: int = 60) -> Dict[str, List[Dict[str, Any]]]:
        """여러 메트릭의 이력 데이터 반환"""
        result = {}
        
        for metric_name in metric_names:
            result[metric_name] = self.get_time_series(metric_name, minutes)
        
        return result
    
    def clear_old_data(self, hours: int = 24):
        """오래된 데이터 정리"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for metric_name, data in self._time_series_data.items():
            # deque에서 오래된 데이터 제거
            while data and datetime.fromisoformat(data[0]['timestamp']) < cutoff_time:
                data.popleft()


# 전역 차트 데이터 제공자 인스턴스
_chart_data_provider: Optional[ChartDataProvider] = None


def get_chart_data_provider() -> ChartDataProvider:
    """전역 차트 데이터 제공자 인스턴스 반환"""
    global _chart_data_provider
    if _chart_data_provider is None:
        _chart_data_provider = ChartDataProvider()
    return _chart_data_provider