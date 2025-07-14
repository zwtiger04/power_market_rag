"""
알림 트리거 구현
다양한 알림 조건 평가 로직
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class AlertTrigger(ABC):
    """알림 트리거 추상 클래스"""
    
    @abstractmethod
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """트리거 조건 평가"""
        pass


class ThresholdTrigger(AlertTrigger):
    """임계값 기반 트리거"""
    
    def __init__(self, metric_path: str, operator: str, threshold: float):
        """
        임계값 트리거 초기화
        
        Args:
            metric_path: 메트릭 경로 (예: "cpu.usage_percent")
            operator: 비교 연산자 (>, <, >=, <=, ==, !=)
            threshold: 임계값
        """
        self.metric_path = metric_path
        self.operator = operator
        self.threshold = threshold
    
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """임계값 조건 평가"""
        try:
            value = self._get_metric_value(metrics, self.metric_path)
            if value is None:
                return False
            
            return self._compare_values(value, self.operator, self.threshold)
        except Exception:
            return False
    
    def _get_metric_value(self, metrics: Dict[str, Any], path: str) -> Optional[float]:
        """메트릭 값 추출"""
        try:
            keys = path.split('.')
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


class RateTrigger(AlertTrigger):
    """변화율 기반 트리거"""
    
    def __init__(self, metric_path: str, rate_threshold: float, window_size: int = 5):
        """
        변화율 트리거 초기화
        
        Args:
            metric_path: 메트릭 경로
            rate_threshold: 변화율 임계값 (초당)
            window_size: 윈도우 크기 (데이터 포인트 수)
        """
        self.metric_path = metric_path
        self.rate_threshold = rate_threshold
        self.window_size = window_size
        self._history: List[Dict[str, Any]] = []
    
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """변화율 조건 평가"""
        try:
            value = self._get_metric_value(metrics, self.metric_path)
            if value is None:
                return False
            
            # 현재 시간과 값을 히스토리에 추가
            current_time = datetime.now()
            self._history.append({
                'timestamp': current_time,
                'value': value
            })
            
            # 윈도우 크기 유지
            if len(self._history) > self.window_size:
                self._history = self._history[-self.window_size:]
            
            # 최소 2개 데이터 포인트 필요
            if len(self._history) < 2:
                return False
            
            # 변화율 계산
            first_point = self._history[0]
            last_point = self._history[-1]
            
            time_diff = (last_point['timestamp'] - first_point['timestamp']).total_seconds()
            if time_diff <= 0:
                return False
            
            value_diff = last_point['value'] - first_point['value']
            rate = value_diff / time_diff
            
            return abs(rate) > self.rate_threshold
            
        except Exception:
            return False
    
    def _get_metric_value(self, metrics: Dict[str, Any], path: str) -> Optional[float]:
        """메트릭 값 추출 (ThresholdTrigger와 동일)"""
        try:
            keys = path.split('.')
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


class AnomalyTrigger(AlertTrigger):
    """이상치 탐지 트리거"""
    
    def __init__(self, metric_path: str, sensitivity: float = 2.0, window_size: int = 20):
        """
        이상치 트리거 초기화
        
        Args:
            metric_path: 메트릭 경로
            sensitivity: 민감도 (표준편차의 배수)
            window_size: 윈도우 크기
        """
        self.metric_path = metric_path
        self.sensitivity = sensitivity
        self.window_size = window_size
        self._history: List[float] = []
    
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """이상치 조건 평가"""
        try:
            value = self._get_metric_value(metrics, self.metric_path)
            if value is None:
                return False
            
            # 히스토리에 추가
            self._history.append(value)
            
            # 윈도우 크기 유지
            if len(self._history) > self.window_size:
                self._history = self._history[-self.window_size:]
            
            # 최소 10개 데이터 포인트 필요
            if len(self._history) < 10:
                return False
            
            # 통계 계산 (현재 값 제외)
            historical_values = self._history[:-1]
            mean = sum(historical_values) / len(historical_values)
            
            # 표준편차 계산
            variance = sum((x - mean) ** 2 for x in historical_values) / len(historical_values)
            std_dev = variance ** 0.5
            
            # Z-score 계산
            if std_dev == 0:
                return False
            
            z_score = abs(value - mean) / std_dev
            
            return z_score > self.sensitivity
            
        except Exception:
            return False
    
    def _get_metric_value(self, metrics: Dict[str, Any], path: str) -> Optional[float]:
        """메트릭 값 추출"""
        try:
            keys = path.split('.')
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


class CompositeTrigger(AlertTrigger):
    """복합 트리거 (AND/OR 조건)"""
    
    def __init__(self, triggers: List[AlertTrigger], operator: str = "AND"):
        """
        복합 트리거 초기화
        
        Args:
            triggers: 하위 트리거 목록
            operator: 결합 연산자 ("AND" 또는 "OR")
        """
        self.triggers = triggers
        self.operator = operator.upper()
    
    def evaluate(self, metrics: Dict[str, Any]) -> bool:
        """복합 조건 평가"""
        if not self.triggers:
            return False
        
        results = [trigger.evaluate(metrics) for trigger in self.triggers]
        
        if self.operator == "AND":
            return all(results)
        elif self.operator == "OR":
            return any(results)
        else:
            return False