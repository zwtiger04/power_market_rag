"""
알림 규칙 정의 및 관리
"""

import yaml
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class Severity(str, Enum):
    """알림 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """알림 상태"""
    INACTIVE = "inactive"
    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """알림 규칙 클래스"""
    
    # 기본 정보
    name: str
    description: str
    severity: Severity
    
    # 조건
    metric_name: str
    condition: str  # 예: "cpu_usage > 80", "error_rate > 0.05"
    duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # 알림 설정
    channels: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # 상태 관리
    state: AlertState = AlertState.INACTIVE
    last_triggered: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    firing_count: int = 0
    
    # 억제 설정
    repeat_interval: timedelta = field(default_factory=lambda: timedelta(hours=1))
    max_alerts_per_day: int = 10
    
    # 조건 평가 함수
    evaluation_func: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if isinstance(self.severity, str):
            self.severity = Severity(self.severity)
        if isinstance(self.state, str):
            self.state = AlertState(self.state)
        if isinstance(self.duration, (int, float)):
            self.duration = timedelta(seconds=self.duration)
        if isinstance(self.repeat_interval, (int, float)):
            self.repeat_interval = timedelta(seconds=self.repeat_interval)
    
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """알림 조건 평가"""
        if self.evaluation_func:
            return self.evaluation_func(metrics)
        
        # 기본 조건 평가 (간단한 표현식 파싱)
        return self._evaluate_condition(metrics)
    
    def _evaluate_condition(self, metrics: Dict[str, Any]) -> bool:
        """조건 문자열 평가"""
        try:
            # 메트릭 값 추출
            metric_value = self._get_metric_value(metrics, self.metric_name)
            if metric_value is None:
                return False
            
            # 조건 파싱 및 평가
            condition = self.condition.strip()
            
            # 간단한 조건 파싱 (예: "cpu_usage > 80")
            operators = ['>=', '<=', '!=', '>', '<', '==']
            
            for op in operators:
                if op in condition:
                    parts = condition.split(op, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        
                        # 좌변이 메트릭 이름인지 확인
                        if left == self.metric_name:
                            try:
                                threshold = float(right)
                                return self._compare_values(metric_value, op, threshold)
                            except ValueError:
                                return False
            
            return False
            
        except Exception:
            return False
    
    def _get_metric_value(self, metrics: Dict[str, Any], metric_path: str) -> Optional[float]:
        """중첩된 딕셔너리에서 메트릭 값 추출"""
        try:
            # 점 표기법으로 중첩 딕셔너리 접근 (예: "cpu.usage_percent")
            keys = metric_path.split('.')
            value = metrics
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            # 숫자로 변환 시도
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
    
    def _compare_values(self, value: float, operator: str, threshold: float) -> bool:
        """값 비교"""
        if operator == '>':
            return value > threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<':
            return value < threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        return False
    
    def should_fire(self, current_time: datetime) -> bool:
        """알림을 발생시켜야 하는지 확인"""
        if self.state != AlertState.FIRING:
            return False
        
        # 처음 발생하는 경우
        if self.last_triggered is None:
            return True
        
        # 반복 간격 체크
        if current_time - self.last_triggered >= self.repeat_interval:
            return True
        
        # 일일 최대 알림 수 체크
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.last_triggered and self.last_triggered < today_start:
            self.firing_count = 0  # 새로운 날 시작
        
        return self.firing_count < self.max_alerts_per_day
    
    def fire(self, current_time: datetime):
        """알림 발생"""
        self.state = AlertState.FIRING
        self.last_triggered = current_time
        self.firing_count += 1
        self.resolved_at = None
    
    def resolve(self, current_time: datetime):
        """알림 해결"""
        self.state = AlertState.RESOLVED
        self.resolved_at = current_time
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'name': self.name,
            'description': self.description,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'condition': self.condition,
            'duration': self.duration.total_seconds(),
            'channels': self.channels,
            'labels': self.labels,
            'annotations': self.annotations,
            'state': self.state.value,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'firing_count': self.firing_count,
            'repeat_interval': self.repeat_interval.total_seconds(),
            'max_alerts_per_day': self.max_alerts_per_day
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertRule':
        """딕셔너리에서 생성"""
        # 필수 필드
        rule = cls(
            name=data['name'],
            description=data['description'],
            severity=Severity(data['severity']),
            metric_name=data['metric_name'],
            condition=data['condition']
        )
        
        # 선택적 필드
        if 'duration' in data:
            rule.duration = timedelta(seconds=data['duration'])
        if 'channels' in data:
            rule.channels = data['channels']
        if 'labels' in data:
            rule.labels = data['labels']
        if 'annotations' in data:
            rule.annotations = data['annotations']
        if 'state' in data:
            rule.state = AlertState(data['state'])
        if 'last_triggered' in data and data['last_triggered']:
            rule.last_triggered = datetime.fromisoformat(data['last_triggered'])
        if 'resolved_at' in data and data['resolved_at']:
            rule.resolved_at = datetime.fromisoformat(data['resolved_at'])
        if 'firing_count' in data:
            rule.firing_count = data['firing_count']
        if 'repeat_interval' in data:
            rule.repeat_interval = timedelta(seconds=data['repeat_interval'])
        if 'max_alerts_per_day' in data:
            rule.max_alerts_per_day = data['max_alerts_per_day']
        
        return rule


class AlertRuleManager:
    """알림 규칙 관리자"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        알림 규칙 관리자 초기화
        
        Args:
            config_file: 설정 파일 경로
        """
        self.config_file = config_file or "monitoring/alert_rules.yaml"
        self.rules: Dict[str, AlertRule] = {}
        self._load_rules()
    
    def _load_rules(self):
        """설정 파일에서 규칙 로드"""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            self._create_default_rules()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            rules_data = config.get('rules', [])
            for rule_data in rules_data:
                rule = AlertRule.from_dict(rule_data)
                self.rules[rule.name] = rule
                
        except Exception as e:
            print(f"알림 규칙 로드 실패: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """기본 알림 규칙 생성"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                description="CPU 사용률이 높습니다",
                severity=Severity.WARNING,
                metric_name="cpu.usage_percent",
                condition="cpu.usage_percent > 80",
                duration=timedelta(minutes=5),
                channels=["console", "email"],
                labels={"component": "system"},
                annotations={"summary": "CPU 사용률 {{ .value }}%가 임계값을 초과했습니다"}
            ),
            AlertRule(
                name="critical_cpu_usage",
                description="CPU 사용률이 매우 높습니다",
                severity=Severity.CRITICAL,
                metric_name="cpu.usage_percent",
                condition="cpu.usage_percent > 95",
                duration=timedelta(minutes=2),
                channels=["console", "email", "slack"],
                labels={"component": "system"},
                annotations={"summary": "긴급: CPU 사용률 {{ .value }}%가 위험 수준입니다"}
            ),
            AlertRule(
                name="high_memory_usage",
                description="메모리 사용률이 높습니다",
                severity=Severity.WARNING,
                metric_name="memory.virtual.percent",
                condition="memory.virtual.percent > 85",
                duration=timedelta(minutes=5),
                channels=["console", "email"],
                labels={"component": "system"},
                annotations={"summary": "메모리 사용률 {{ .value }}%가 임계값을 초과했습니다"}
            ),
            AlertRule(
                name="high_error_rate",
                description="API 에러율이 높습니다",
                severity=Severity.ERROR,
                metric_name="api.error_rate",
                condition="api.error_rate > 0.05",
                duration=timedelta(minutes=3),
                channels=["console", "email", "slack"],
                labels={"component": "api"},
                annotations={"summary": "API 에러율 {{ .value }}%가 임계값을 초과했습니다"}
            ),
            AlertRule(
                name="slow_response_time",
                description="API 응답 시간이 느립니다",
                severity=Severity.WARNING,
                metric_name="api.avg_response_time",
                condition="api.avg_response_time > 2.0",
                duration=timedelta(minutes=5),
                channels=["console", "email"],
                labels={"component": "api"},
                annotations={"summary": "API 평균 응답시간이 {{ .value }}초입니다"}
            ),
            AlertRule(
                name="cache_hit_rate_low",
                description="캐시 히트율이 낮습니다",
                severity=Severity.WARNING,
                metric_name="cache.hit_rate",
                condition="cache.hit_rate < 50",
                duration=timedelta(minutes=10),
                channels=["console", "email"],
                labels={"component": "cache"},
                annotations={"summary": "캐시 히트율이 {{ .value }}%로 낮습니다"}
            ),
            AlertRule(
                name="rag_confidence_low",
                description="RAG 응답 신뢰도가 낮습니다",
                severity=Severity.WARNING,
                metric_name="rag.avg_confidence",
                condition="rag.avg_confidence < 0.7",
                duration=timedelta(minutes=10),
                channels=["console", "email"],
                labels={"component": "rag"},
                annotations={"summary": "RAG 평균 신뢰도가 {{ .value }}로 낮습니다"}
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
        
        # 기본 설정 파일 저장
        self.save_rules()
    
    def add_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        self.rules[rule.name] = rule
    
    def remove_rule(self, rule_name: str) -> bool:
        """알림 규칙 제거"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            return True
        return False
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """알림 규칙 조회"""
        return self.rules.get(rule_name)
    
    def get_all_rules(self) -> List[AlertRule]:
        """모든 알림 규칙 조회"""
        return list(self.rules.values())
    
    def get_rules_by_severity(self, severity: Severity) -> List[AlertRule]:
        """심각도별 알림 규칙 조회"""
        return [rule for rule in self.rules.values() if rule.severity == severity]
    
    def get_active_rules(self) -> List[AlertRule]:
        """활성 상태인 알림 규칙 조회"""
        return [
            rule for rule in self.rules.values() 
            if rule.state in [AlertState.PENDING, AlertState.FIRING]
        ]
    
    def evaluate_rules(self, metrics: Dict[str, Any]) -> List[AlertRule]:
        """모든 규칙 평가하고 발생된 알림 반환"""
        triggered_rules = []
        current_time = datetime.now()
        
        for rule in self.rules.values():
            if rule.evaluate(metrics):
                if rule.state == AlertState.INACTIVE:
                    rule.state = AlertState.PENDING
                elif rule.state == AlertState.PENDING:
                    # 지속 시간 체크
                    if (rule.last_triggered and 
                        current_time - rule.last_triggered >= rule.duration):
                        rule.fire(current_time)
                        triggered_rules.append(rule)
                    elif not rule.last_triggered:
                        rule.last_triggered = current_time
                elif rule.state == AlertState.RESOLVED:
                    # 다시 발생
                    rule.state = AlertState.PENDING
                    rule.last_triggered = current_time
            else:
                # 조건이 해결됨
                if rule.state in [AlertState.PENDING, AlertState.FIRING]:
                    rule.resolve(current_time)
        
        return triggered_rules
    
    def save_rules(self):
        """규칙을 파일에 저장"""
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        rules_data = [rule.to_dict() for rule in self.rules.values()]
        config = {'rules': rules_data}
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"알림 규칙 저장 실패: {e}")
    
    def reload_rules(self):
        """규칙 다시 로드"""
        self.rules.clear()
        self._load_rules()