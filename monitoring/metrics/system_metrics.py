"""
시스템 메트릭 수집기
서버 리소스 및 시스템 상태 모니터링
"""

import psutil
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path


class SystemMetricsCollector:
    """시스템 메트릭 수집기"""
    
    def __init__(self, collection_interval: int = 30):
        """
        시스템 메트릭 수집기 초기화
        
        Args:
            collection_interval: 수집 주기 (초)
        """
        self.collection_interval = collection_interval
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._metrics_history: List[Dict[str, Any]] = []
        self._max_history = 2880  # 24시간 분량 (30초 간격)
        
        # 이전 네트워크/디스크 IO 통계 (증분 계산용)
        self._prev_network_io = None
        self._prev_disk_io = None
        self._prev_timestamp = None
    
    def start(self):
        """메트릭 수집 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """메트릭 수집 중지"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _collect_loop(self):
        """메트릭 수집 루프"""
        while self.is_running:
            try:
                metrics = self.collect_metrics()
                self._store_metrics(metrics)
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"시스템 메트릭 수집 오류: {e}")
                time.sleep(self.collection_interval)
    
    def collect_metrics(self) -> Dict[str, Any]:
        """현재 시스템 메트릭 수집"""
        timestamp = datetime.now()
        
        try:
            metrics = {
                'timestamp': timestamp,
                'cpu': self._get_cpu_metrics(),
                'memory': self._get_memory_metrics(),
                'disk': self._get_disk_metrics(),
                'network': self._get_network_metrics(),
                'process': self._get_process_metrics(),
                'system': self._get_system_info()
            }
            
            return metrics
        except Exception as e:
            return {
                'timestamp': timestamp,
                'error': str(e)
            }
    
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """CPU 메트릭 수집"""
        return {
            'usage_percent': psutil.cpu_percent(interval=None),
            'usage_per_core': psutil.cpu_percent(interval=None, percpu=True),
            'count_physical': psutil.cpu_count(logical=False),
            'count_logical': psutil.cpu_count(logical=True),
            'freq_current': psutil.cpu_freq().current if psutil.cpu_freq() else None,
            'freq_max': psutil.cpu_freq().max if psutil.cpu_freq() else None,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        }
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """메모리 메트릭 수집"""
        virtual_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()
        
        return {
            'virtual': {
                'total': virtual_memory.total,
                'available': virtual_memory.available,
                'used': virtual_memory.used,
                'free': virtual_memory.free,
                'percent': virtual_memory.percent,
                'active': getattr(virtual_memory, 'active', None),
                'inactive': getattr(virtual_memory, 'inactive', None),
                'buffers': getattr(virtual_memory, 'buffers', None),
                'cached': getattr(virtual_memory, 'cached', None)
            },
            'swap': {
                'total': swap_memory.total,
                'used': swap_memory.used,
                'free': swap_memory.free,
                'percent': swap_memory.percent,
                'sin': swap_memory.sin,
                'sout': swap_memory.sout
            }
        }
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """디스크 메트릭 수집"""
        disk_usage = {}
        disk_io = psutil.disk_io_counters()
        
        # 디스크 사용량
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                }
            except (PermissionError, FileNotFoundError):
                continue
        
        # 디스크 IO 통계
        disk_io_metrics = {}
        if disk_io:
            current_time = time.time()
            
            disk_io_metrics = {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            }
            
            # 이전 데이터가 있으면 증분 계산
            if self._prev_disk_io and self._prev_timestamp:
                time_delta = current_time - self._prev_timestamp
                if time_delta > 0:
                    disk_io_metrics['read_bytes_per_sec'] = (
                        disk_io.read_bytes - self._prev_disk_io.read_bytes
                    ) / time_delta
                    disk_io_metrics['write_bytes_per_sec'] = (
                        disk_io.write_bytes - self._prev_disk_io.write_bytes
                    ) / time_delta
            
            self._prev_disk_io = disk_io
            self._prev_timestamp = current_time
        
        return {
            'usage': disk_usage,
            'io': disk_io_metrics
        }
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """네트워크 메트릭 수집"""
        network_io = psutil.net_io_counters()
        network_connections = len(psutil.net_connections())
        
        network_metrics = {}
        if network_io:
            current_time = time.time()
            
            network_metrics = {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv,
                'errin': network_io.errin,
                'errout': network_io.errout,
                'dropin': network_io.dropin,
                'dropout': network_io.dropout,
                'connections_count': network_connections
            }
            
            # 이전 데이터가 있으면 증분 계산
            if self._prev_network_io and self._prev_timestamp:
                time_delta = current_time - self._prev_timestamp
                if time_delta > 0:
                    network_metrics['bytes_sent_per_sec'] = (
                        network_io.bytes_sent - self._prev_network_io.bytes_sent
                    ) / time_delta
                    network_metrics['bytes_recv_per_sec'] = (
                        network_io.bytes_recv - self._prev_network_io.bytes_recv
                    ) / time_delta
            
            self._prev_network_io = network_io
        
        return network_metrics
    
    def _get_process_metrics(self) -> Dict[str, Any]:
        """프로세스 메트릭 수집"""
        current_process = psutil.Process()
        
        try:
            with current_process.oneshot():
                return {
                    'pid': current_process.pid,
                    'cpu_percent': current_process.cpu_percent(),
                    'memory_info': current_process.memory_info()._asdict(),
                    'memory_percent': current_process.memory_percent(),
                    'num_threads': current_process.num_threads(),
                    'num_fds': current_process.num_fds() if hasattr(current_process, 'num_fds') else None,
                    'create_time': current_process.create_time(),
                    'status': current_process.status(),
                    'cmdline': ' '.join(current_process.cmdline()) if current_process.cmdline() else None
                }
        except psutil.NoSuchProcess:
            return {'error': 'Process not found'}
    
    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        boot_time = psutil.boot_time()
        
        return {
            'boot_time': datetime.fromtimestamp(boot_time),
            'uptime_seconds': time.time() - boot_time,
            'platform': psutil.LINUX if hasattr(psutil, 'LINUX') else 'unknown',
            'python_version': psutil.version_info if hasattr(psutil, 'version_info') else None
        }
    
    def _store_metrics(self, metrics: Dict[str, Any]):
        """메트릭을 내부 저장소에 저장"""
        self._metrics_history.append(metrics)
        
        # 최대 저장 개수 제한
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 반환"""
        return self.collect_metrics()
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """지정된 시간 동안의 메트릭 이력 반환"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        return [
            metrics for metrics in self._metrics_history
            if metrics.get('timestamp', datetime.min) > cutoff_time
        ]
    
    def get_average_metrics(self, minutes: int = 10) -> Dict[str, Any]:
        """지정된 시간 동안의 평균 메트릭 반환"""
        recent_metrics = self.get_metrics_history(minutes)
        
        if not recent_metrics:
            return {}
        
        # CPU 평균
        cpu_values = [m.get('cpu', {}).get('usage_percent', 0) for m in recent_metrics if 'cpu' in m]
        cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        
        # 메모리 평균
        memory_values = [m.get('memory', {}).get('virtual', {}).get('percent', 0) for m in recent_metrics if 'memory' in m]
        memory_avg = sum(memory_values) / len(memory_values) if memory_values else 0
        
        # 네트워크 속도 평균
        network_sent_values = [m.get('network', {}).get('bytes_sent_per_sec', 0) for m in recent_metrics if 'network' in m]
        network_recv_values = [m.get('network', {}).get('bytes_recv_per_sec', 0) for m in recent_metrics if 'network' in m]
        
        network_sent_avg = sum(network_sent_values) / len(network_sent_values) if network_sent_values else 0
        network_recv_avg = sum(network_recv_values) / len(network_recv_values) if network_recv_values else 0
        
        return {
            'time_window_minutes': minutes,
            'cpu_usage_percent_avg': round(cpu_avg, 2),
            'memory_usage_percent_avg': round(memory_avg, 2),
            'network_sent_bytes_per_sec_avg': round(network_sent_avg, 2),
            'network_recv_bytes_per_sec_avg': round(network_recv_avg, 2),
            'sample_count': len(recent_metrics)
        }
    
    def get_peak_metrics(self, minutes: int = 60) -> Dict[str, Any]:
        """지정된 시간 동안의 최대값 메트릭 반환"""
        recent_metrics = self.get_metrics_history(minutes)
        
        if not recent_metrics:
            return {}
        
        # 최대값 계산
        cpu_peak = max(m.get('cpu', {}).get('usage_percent', 0) for m in recent_metrics if 'cpu' in m)
        memory_peak = max(m.get('memory', {}).get('virtual', {}).get('percent', 0) for m in recent_metrics if 'memory' in m)
        
        network_sent_peak = max(m.get('network', {}).get('bytes_sent_per_sec', 0) for m in recent_metrics if 'network' in m)
        network_recv_peak = max(m.get('network', {}).get('bytes_recv_per_sec', 0) for m in recent_metrics if 'network' in m)
        
        return {
            'time_window_minutes': minutes,
            'cpu_usage_percent_peak': round(cpu_peak, 2),
            'memory_usage_percent_peak': round(memory_peak, 2),
            'network_sent_bytes_per_sec_peak': round(network_sent_peak, 2),
            'network_recv_bytes_per_sec_peak': round(network_recv_peak, 2),
            'sample_count': len(recent_metrics)
        }
    
    def check_resource_alerts(self) -> List[Dict[str, Any]]:
        """리소스 알림 체크"""
        alerts = []
        current = self.get_current_metrics()
        
        # CPU 사용률 체크
        cpu_usage = current.get('cpu', {}).get('usage_percent', 0)
        if cpu_usage > 90:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'critical',
                'message': f'CPU 사용률이 매우 높습니다: {cpu_usage:.1f}%',
                'value': cpu_usage,
                'threshold': 90
            })
        elif cpu_usage > 75:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f'CPU 사용률이 높습니다: {cpu_usage:.1f}%',
                'value': cpu_usage,
                'threshold': 75
            })
        
        # 메모리 사용률 체크
        memory_usage = current.get('memory', {}).get('virtual', {}).get('percent', 0)
        if memory_usage > 95:
            alerts.append({
                'type': 'memory_high',
                'severity': 'critical',
                'message': f'메모리 사용률이 매우 높습니다: {memory_usage:.1f}%',
                'value': memory_usage,
                'threshold': 95
            })
        elif memory_usage > 85:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f'메모리 사용률이 높습니다: {memory_usage:.1f}%',
                'value': memory_usage,
                'threshold': 85
            })
        
        # 디스크 사용률 체크
        disk_usage = current.get('disk', {}).get('usage', {})
        for device, info in disk_usage.items():
            if info.get('percent', 0) > 95:
                alerts.append({
                    'type': 'disk_full',
                    'severity': 'critical',
                    'message': f'디스크가 거의 가득참: {device} ({info["percent"]:.1f}%)',
                    'value': info['percent'],
                    'threshold': 95,
                    'device': device
                })
            elif info.get('percent', 0) > 85:
                alerts.append({
                    'type': 'disk_full',
                    'severity': 'warning',
                    'message': f'디스크 사용률이 높습니다: {device} ({info["percent"]:.1f}%)',
                    'value': info['percent'],
                    'threshold': 85,
                    'device': device
                })
        
        return alerts
    
    def get_health_status(self) -> Dict[str, Any]:
        """전체 시스템 건강 상태 반환"""
        current = self.get_current_metrics()
        alerts = self.check_resource_alerts()
        
        # 건강 점수 계산 (0-100)
        health_score = 100
        
        cpu_usage = current.get('cpu', {}).get('usage_percent', 0)
        memory_usage = current.get('memory', {}).get('virtual', {}).get('percent', 0)
        
        # CPU 점수 차감
        if cpu_usage > 90:
            health_score -= 30
        elif cpu_usage > 75:
            health_score -= 15
        elif cpu_usage > 50:
            health_score -= 5
        
        # 메모리 점수 차감
        if memory_usage > 95:
            health_score -= 40
        elif memory_usage > 85:
            health_score -= 20
        elif memory_usage > 70:
            health_score -= 10
        
        # 디스크 점수 차감
        disk_usage = current.get('disk', {}).get('usage', {})
        for device, info in disk_usage.items():
            if info.get('percent', 0) > 95:
                health_score -= 20
            elif info.get('percent', 0) > 85:
                health_score -= 10
        
        health_score = max(0, health_score)
        
        # 상태 결정
        if health_score >= 90:
            status = 'healthy'
        elif health_score >= 70:
            status = 'warning'
        elif health_score >= 50:
            status = 'degraded'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'health_score': health_score,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'alerts_count': len(alerts),
            'critical_alerts': len([a for a in alerts if a['severity'] == 'critical']),
            'warning_alerts': len([a for a in alerts if a['severity'] == 'warning']),
            'alerts': alerts[:5],  # 최대 5개 알림만 포함
            'timestamp': current.get('timestamp')
        }


# 전역 시스템 메트릭 수집기 인스턴스
_system_metrics: Optional[SystemMetricsCollector] = None


def get_system_metrics_collector() -> SystemMetricsCollector:
    """전역 시스템 메트릭 수집기 인스턴스 반환"""
    global _system_metrics
    if _system_metrics is None:
        _system_metrics = SystemMetricsCollector()
    return _system_metrics