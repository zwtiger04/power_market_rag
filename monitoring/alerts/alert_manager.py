"""
알림 관리자 - 중앙 알림 처리 및 발송
"""

import asyncio
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .rules import AlertRule, AlertRuleManager, AlertState
from .channels import AlertChannel, AlertMessage, create_channel
from ..logging import get_logger


class AlertManager:
    """알림 관리자"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        알림 관리자 초기화
        
        Args:
            config_file: 설정 파일 경로
        """
        self.logger = get_logger(__name__)
        self.rule_manager = AlertRuleManager(config_file)
        self.channels: Dict[str, AlertChannel] = {}
        self.is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_interval = 30  # 30초마다 체크
        
        # 알림 발송 이력
        self._alert_history: List[AlertMessage] = []
        self._max_history = 1000
        
        # 메트릭 수집기 참조
        self._metrics_collector = None
        
        # 기본 채널 설정
        self._setup_default_channels()
    
    def _setup_default_channels(self):
        """기본 알림 채널 설정"""
        # 콘솔 채널 (항상 활성화)
        from .channels import ConsoleChannel
        self.channels['console'] = ConsoleChannel('console', {'enabled': True})
        
        # 이메일 채널 (설정이 있는 경우)
        self._setup_email_channel()
        
        # Slack 채널 (설정이 있는 경우)
        self._setup_slack_channel()
    
    def _setup_email_channel(self):
        """이메일 채널 설정"""
        # 환경 변수나 설정 파일에서 이메일 설정 로드
        email_config = {
            'enabled': False,  # 기본적으로 비활성화
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': '',  # 실제 사용시 설정 필요
            'password': '',  # 실제 사용시 설정 필요
            'from_email': 'rag-system@company.com',
            'to_emails': ['admin@company.com'],
            'use_tls': True
        }
        
        try:
            from .channels import EmailChannel
            self.channels['email'] = EmailChannel('email', email_config)
        except Exception as e:
            self.logger.warning(f"이메일 채널 설정 실패: {e}")
    
    def _setup_slack_channel(self):
        """Slack 채널 설정"""
        slack_config = {
            'enabled': False,  # 기본적으로 비활성화
            'webhook_url': '',  # 실제 사용시 설정 필요
            'channel': '#alerts',
            'username': 'RAG Alert Bot',
            'icon_emoji': ':rotating_light:'
        }
        
        try:
            from .channels import SlackChannel
            self.channels['slack'] = SlackChannel('slack', slack_config)
        except Exception as e:
            self.logger.warning(f"Slack 채널 설정 실패: {e}")
    
    def add_channel(self, channel: AlertChannel):
        """알림 채널 추가"""
        self.channels[channel.name] = channel
        self.logger.info(f"알림 채널 추가: {channel.name}")
    
    def remove_channel(self, channel_name: str) -> bool:
        """알림 채널 제거"""
        if channel_name in self.channels:
            del self.channels[channel_name]
            self.logger.info(f"알림 채널 제거: {channel_name}")
            return True
        return False
    
    def get_channel(self, channel_name: str) -> Optional[AlertChannel]:
        """알림 채널 조회"""
        return self.channels.get(channel_name)
    
    def set_metrics_collector(self, metrics_collector):
        """메트릭 수집기 설정"""
        self._metrics_collector = metrics_collector
    
    async def process_metrics(self, metrics: Dict[str, Any]):
        """메트릭 처리 및 알림 평가"""
        try:
            # 알림 규칙 평가
            triggered_rules = self.rule_manager.evaluate_rules(metrics)
            
            # 발생된 알림 처리
            for rule in triggered_rules:
                if rule.should_fire(datetime.now()):
                    await self._send_alert(rule, metrics)
                    
        except Exception as e:
            self.logger.error(f"메트릭 처리 중 오류: {e}")
    
    async def _send_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """알림 발송"""
        try:
            # 알림 메시지 생성
            message = self._create_alert_message(rule, metrics)
            
            # 지정된 채널들에 알림 발송
            sent_channels = []
            failed_channels = []
            
            for channel_name in rule.channels:
                channel = self.channels.get(channel_name)
                if channel and channel.enabled:
                    try:
                        success = await channel.send_alert(message)
                        if success:
                            sent_channels.append(channel_name)
                        else:
                            failed_channels.append(channel_name)
                    except Exception as e:
                        self.logger.error(f"채널 {channel_name} 알림 발송 실패: {e}")
                        failed_channels.append(channel_name)
                else:
                    self.logger.warning(f"채널 {channel_name}을 찾을 수 없거나 비활성화됨")
                    failed_channels.append(channel_name)
            
            # 알림 발송 이력 저장
            self._store_alert_history(message, sent_channels, failed_channels)
            
            # 규칙 상태 업데이트
            rule.fire(datetime.now())
            
            self.logger.info(
                f"알림 발송 완료 - 규칙: {rule.name}, "
                f"성공: {sent_channels}, 실패: {failed_channels}"
            )
            
        except Exception as e:
            self.logger.error(f"알림 발송 중 오류: {e}")
    
    def _create_alert_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> AlertMessage:
        """알림 메시지 생성"""
        # 메시지 템플릿 처리
        message_text = rule.annotations.get('summary', rule.description)
        
        # 간단한 템플릿 변수 치환
        if '{{ .value }}' in message_text and rule.metric_name in metrics:
            metric_value = self._get_metric_value(metrics, rule.metric_name)
            if metric_value is not None:
                message_text = message_text.replace('{{ .value }}', str(metric_value))
        
        # 제목 생성
        title = f"{rule.name}: {rule.description}"
        
        return AlertMessage(
            rule=rule,
            timestamp=datetime.now(),
            metrics=metrics,
            message=message_text,
            title=title,
            severity=rule.severity,
            labels=rule.labels
        )
    
    def _get_metric_value(self, metrics: Dict[str, Any], metric_path: str) -> Optional[float]:
        """메트릭 값 추출"""
        try:
            keys = metric_path.split('.')
            value = metrics
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                try:
                    return float(value)
                except ValueError:
                    return None
            
            return None
        except Exception:
            return None
    
    def _store_alert_history(self, message: AlertMessage, sent_channels: List[str], failed_channels: List[str]):
        """알림 이력 저장"""
        # 메타데이터 추가
        message.labels['sent_channels'] = ','.join(sent_channels)
        message.labels['failed_channels'] = ','.join(failed_channels)
        message.labels['total_channels'] = str(len(sent_channels) + len(failed_channels))
        
        # 이력에 추가
        self._alert_history.append(message)
        
        # 최대 이력 수 제한
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        self.logger.info("알림 모니터링 시작")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("알림 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.is_running:
            try:
                if self._metrics_collector:
                    # 메트릭 수집기에서 현재 메트릭 가져오기
                    metrics = self._get_current_metrics()
                    if metrics:
                        # 비동기 처리를 위한 이벤트 루프 실행
                        asyncio.run(self.process_metrics(metrics))
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(self._monitor_interval)
    
    def _get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """현재 메트릭 수집"""
        try:
            if not self._metrics_collector:
                return None
            
            # 성능 요약 가져오기
            performance = self._metrics_collector.get_performance_summary()
            
            # 시스템 메트릭 가져오기
            system_metrics = {}
            try:
                from ..metrics.system_metrics import get_system_metrics_collector
                system_collector = get_system_metrics_collector()
                system_metrics = system_collector.get_current_metrics()
            except Exception:
                pass
            
            # 캐시 통계 가져오기
            cache_stats = {}
            try:
                from ...cache import get_cache_manager
                cache_manager = get_cache_manager()
                cache_stats = cache_manager.get_cache_stats()
            except Exception:
                pass
            
            # 통합 메트릭 구성
            metrics = {
                'api': {
                    'active_requests': performance.get('active_requests', 0),
                    'total_requests': performance.get('total_api_calls', 0),
                    'avg_response_time': performance.get('avg_response_time', 0),
                    'error_rate': performance.get('error_rate_5min', 0) / 100  # 비율로 변환
                },
                'cache': {
                    'hit_rate': performance.get('cache_hit_rate', 0),
                    'hits': performance.get('cache_hits', 0),
                    'misses': performance.get('cache_misses', 0)
                },
                'rag': {
                    'search_requests': performance.get('total_search_requests', 0),
                    'query_requests': performance.get('total_query_requests', 0),
                    'avg_confidence': 0.8  # 임시값, 실제로는 RAG 시스템에서 가져와야 함
                }
            }
            
            # 시스템 메트릭 추가
            if system_metrics and 'error' not in system_metrics:
                metrics['cpu'] = system_metrics.get('cpu', {})
                metrics['memory'] = system_metrics.get('memory', {})
                metrics['disk'] = system_metrics.get('disk', {})
                metrics['network'] = system_metrics.get('network', {})
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"메트릭 수집 실패: {e}")
            return None
    
    async def test_alert(self, rule_name: str) -> bool:
        """알림 테스트"""
        rule = self.rule_manager.get_rule(rule_name)
        if not rule:
            self.logger.error(f"알림 규칙을 찾을 수 없음: {rule_name}")
            return False
        
        # 테스트 메트릭 생성
        test_metrics = {
            'cpu': {'usage_percent': 95.0},
            'memory': {'virtual': {'percent': 90.0}},
            'api': {'error_rate': 0.1, 'avg_response_time': 5.0},
            'cache': {'hit_rate': 30.0}
        }
        
        # 테스트 알림 발송
        await self._send_alert(rule, test_metrics)
        return True
    
    def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """알림 통계 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self._alert_history
            if alert.timestamp > cutoff_time
        ]
        
        # 심각도별 집계
        severity_counts = {}
        for alert in recent_alerts:
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # 규칙별 집계
        rule_counts = {}
        for alert in recent_alerts:
            rule_name = alert.rule.name
            rule_counts[rule_name] = rule_counts.get(rule_name, 0) + 1
        
        # 채널별 성공률
        channel_stats = {}
        for alert in recent_alerts:
            sent_channels = alert.labels.get('sent_channels', '').split(',')
            failed_channels = alert.labels.get('failed_channels', '').split(',')
            
            for channel in sent_channels:
                if channel:
                    if channel not in channel_stats:
                        channel_stats[channel] = {'sent': 0, 'failed': 0}
                    channel_stats[channel]['sent'] += 1
            
            for channel in failed_channels:
                if channel:
                    if channel not in channel_stats:
                        channel_stats[channel] = {'sent': 0, 'failed': 0}
                    channel_stats[channel]['failed'] += 1
        
        return {
            'time_window_hours': hours,
            'total_alerts': len(recent_alerts),
            'alerts_by_severity': severity_counts,
            'alerts_by_rule': rule_counts,
            'channel_statistics': channel_stats,
            'active_rules': len(self.rule_manager.get_active_rules()),
            'total_rules': len(self.rule_manager.get_all_rules())
        }
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """최근 알림 조회"""
        recent = self._alert_history[-limit:] if limit > 0 else self._alert_history
        return [alert.to_dict() for alert in reversed(recent)]
    
    def clear_alert_history(self):
        """알림 이력 초기화"""
        self._alert_history.clear()
        self.logger.info("알림 이력 초기화 완료")


# 전역 알림 관리자 인스턴스
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """전역 알림 관리자 인스턴스 반환"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager