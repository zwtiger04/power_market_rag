# 모니터링 및 로깅 시스템

전력시장 RAG 시스템의 포괄적인 모니터링과 로깅을 제공하는 통합 시스템입니다.

## 🏗️ 시스템 구조

```
monitoring/
├── logging/               # 구조화된 로깅 시스템
│   ├── logger.py         # 메인 로거 클래스
│   ├── formatters.py     # 로그 포맷터 (JSON, 구조화)
│   └── handlers.py       # 로그 핸들러 (파일, 콘솔)
├── metrics/              # 메트릭 수집 시스템
│   ├── collector.py      # 메트릭 수집기
│   ├── prometheus_metrics.py  # Prometheus 메트릭
│   ├── decorators.py     # 메트릭 데코레이터
│   └── system_metrics.py # 시스템 메트릭
├── alerts/               # 실시간 알림 시스템
│   ├── alert_manager.py  # 알림 관리자
│   ├── rules.py          # 알림 규칙
│   ├── channels.py       # 알림 채널 (이메일, Slack 등)
│   └── triggers.py       # 알림 트리거
└── dashboard/            # 웹 대시보드
    ├── dashboard_api.py  # 대시보드 API
    ├── websocket_manager.py  # WebSocket 관리
    └── chart_data.py     # 차트 데이터 제공자
```

## 🚀 주요 기능

### 1. 구조화된 로깅 시스템

**특징:**
- JSON 및 구조화된 텍스트 포맷 지원
- 컨텍스트 기반 로깅 (요청 ID, 사용자 ID 등)
- 자동 로그 로테이션
- 민감한 데이터 마스킹
- 환경별 설정 (개발/프로덕션)

**사용법:**
```python
from monitoring import get_logger, setup_logging

# 로깅 설정
setup_logging(
    level="INFO",
    log_dir="./logs",
    environment="production"
)

# 로거 사용
logger = get_logger(__name__)
logger.info("애플리케이션 시작")

# 컨텍스트와 함께 로깅
with logger.bind(user_id="123", request_id="req-456"):
    logger.info("사용자 요청 처리")
```

### 2. 메트릭 수집 시스템

**특징:**
- Prometheus 메트릭 자동 생성
- 시스템 리소스 모니터링 (CPU, 메모리, 디스크, 네트워크)
- API 성능 메트릭 (응답시간, 처리량, 에러율)
- RAG 시스템 전용 메트릭 (검색 성능, 신뢰도)
- 캐시 성능 메트릭

**메트릭 예시:**
```
# API 메트릭
rag_api_requests_total{method="POST", endpoint="/ask", status_code="200"}
rag_api_request_duration_seconds{method="POST", endpoint="/ask"}

# RAG 메트릭
rag_search_duration_seconds{search_method="hybrid"}
rag_confidence_score{search_method="hybrid"}

# 시스템 메트릭
rag_system_cpu_usage_percent
rag_system_memory_usage_percent
```

**사용법:**
```python
from monitoring import get_metrics_collector, time_metric

# 메트릭 수집기 사용
metrics = get_metrics_collector()
metrics.record_search_metrics("hybrid", 0.5, 10, True)

# 데코레이터 사용
@time_metric(labels={'component': 'rag'})
def search_documents(query):
    # 검색 로직
    return results
```

### 3. 실시간 알림 시스템

**특징:**
- YAML 기반 알림 규칙 설정
- 다양한 알림 채널 (이메일, Slack, Discord, 웹훅)
- 임계값, 변화율, 이상치 탐지 트리거
- 알림 중복 방지 및 억제
- 알림 발송 이력 추적

**알림 규칙 예시:**
```yaml
rules:
  - name: high_cpu_usage
    description: CPU 사용률이 높습니다
    severity: warning
    metric_name: cpu.usage_percent
    condition: "cpu.usage_percent > 80"
    duration: 300  # 5분
    channels: [console, email]
    
  - name: critical_error_rate
    description: API 에러율이 매우 높습니다
    severity: critical
    metric_name: api.error_rate
    condition: "api.error_rate > 0.05"
    channels: [console, email, slack]
```

### 4. 웹 대시보드

**특징:**
- 실시간 메트릭 시각화
- WebSocket 기반 실시간 업데이트
- 반응형 웹 디자인
- Chart.js 기반 차트
- 시스템 상태 개요

**접근 방법:**
```
http://localhost:8000/monitoring
```

**API 엔드포인트:**
- `GET /monitoring/api/metrics` - 현재 메트릭
- `GET /monitoring/api/dashboard` - 대시보드 데이터
- `GET /monitoring/api/alerts` - 알림 통계
- `WebSocket /monitoring/ws/{client_id}` - 실시간 업데이트

## 📦 설치 및 설정

### 1. 의존성 설치

```bash
pip install prometheus-client psutil loguru pyyaml fastapi websockets
```

### 2. 기본 설정

```python
from monitoring import setup_logging, get_metrics_collector, get_alert_manager

# 로깅 설정
setup_logging(
    level="INFO",
    log_dir="./logs",
    app_name="power_market_rag",
    environment="production"
)

# 메트릭 수집기 초기화
metrics_collector = get_metrics_collector()

# 알림 관리자 초기화
alert_manager = get_alert_manager()
alert_manager.set_metrics_collector(metrics_collector)
alert_manager.start_monitoring()
```

### 3. FastAPI 통합

```python
from fastapi import FastAPI
from monitoring.dashboard import setup_dashboard_api

app = FastAPI()

# 대시보드 API 설정
dashboard_api = setup_dashboard_api(app)

# 메트릭 업데이트 (주기적으로 호출)
dashboard_api.update_metrics({
    'cpu': {'usage_percent': 75.0},
    'memory': {'virtual': {'percent': 68.0}},
    'api': {'active_requests': 10}
})
```

## 🔧 설정 파일

### 로깅 설정 (.env)
```bash
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
LOG_MAX_SIZE=10MB
LOG_BACKUP_COUNT=5
```

### 알림 규칙 (monitoring/alert_rules.yaml)
```yaml
rules:
  - name: high_cpu_usage
    description: CPU 사용률이 높습니다
    severity: warning
    metric_name: cpu.usage_percent
    condition: "cpu.usage_percent > 80"
    duration: 300
    channels: [console, email]
    labels:
      component: system
    annotations:
      summary: "CPU 사용률 {{ .value }}%가 임계값을 초과했습니다"
```

### 알림 채널 설정
```python
from monitoring.alerts import EmailChannel, SlackChannel

# 이메일 채널
email_config = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'username': 'your-email@gmail.com',
    'password': 'app-password',
    'to_emails': ['admin@company.com']
}
email_channel = EmailChannel('email', email_config)

# Slack 채널
slack_config = {
    'webhook_url': 'https://hooks.slack.com/services/...',
    'channel': '#alerts'
}
slack_channel = SlackChannel('slack', slack_config)

# 알림 관리자에 채널 추가
alert_manager.add_channel(email_channel)
alert_manager.add_channel(slack_channel)
```

## 📊 메트릭 카테고리

### API 메트릭
- `rag_api_requests_total` - 총 API 요청 수
- `rag_api_request_duration_seconds` - API 응답 시간
- `rag_api_active_requests` - 활성 요청 수

### RAG 시스템 메트릭
- `rag_search_requests_total` - 검색 요청 수
- `rag_search_duration_seconds` - 검색 시간
- `rag_confidence_score` - 응답 신뢰도

### 캐시 메트릭
- `rag_cache_operations_total` - 캐시 작업 수
- `rag_cache_hit_ratio` - 캐시 히트율
- `rag_cache_memory_usage_bytes` - 캐시 메모리 사용량

### 시스템 메트릭
- `rag_system_cpu_usage_percent` - CPU 사용률
- `rag_system_memory_usage_percent` - 메모리 사용률
- `rag_system_disk_usage_bytes` - 디스크 사용량

## 🎯 모니터링 모범 사례

### 1. 로깅
```python
# 좋은 예
logger.info("사용자 인증 성공", extra={
    'user_id': user.id,
    'login_method': 'jwt',
    'ip_address': request.remote_addr
})

# 나쁜 예
logger.info(f"User {user.id} logged in")
```

### 2. 메트릭
```python
# 데코레이터 사용 (권장)
@time_metric(labels={'operation': 'search'})
@error_tracking('rag_system')
def search_documents(query):
    return results

# 수동 메트릭 (필요시)
start_time = time.time()
try:
    result = expensive_operation()
    metrics.record_operation_success('expensive_op', time.time() - start_time)
except Exception as e:
    metrics.record_error('expensive_op_failed', 'rag_system')
    raise
```

### 3. 알림
- 중요도에 따른 채널 분리
- 알림 피로도 방지를 위한 적절한 임계값 설정
- 알림 메시지에 충분한 컨텍스트 포함

## 🔍 트러블슈팅

### 로그 파일이 생성되지 않는 경우
```bash
# 로그 디렉토리 권한 확인
ls -la ./logs/

# 디렉토리 생성
mkdir -p ./logs
chmod 755 ./logs
```

### Prometheus 메트릭이 보이지 않는 경우
```python
# 메트릭 엔드포인트 확인
curl http://localhost:8000/monitoring/api/prometheus

# 메트릭 수집기 상태 확인
metrics = get_metrics_collector()
print(metrics.get_performance_summary())
```

### 알림이 발송되지 않는 경우
```python
# 알림 규칙 상태 확인
alert_manager = get_alert_manager()
stats = alert_manager.get_alert_statistics()
print(stats)

# 테스트 알림 발송
await alert_manager.test_alert('high_cpu_usage')
```

## 📈 성능 고려사항

- **로깅**: 프로덕션에서는 DEBUG 레벨 비활성화
- **메트릭**: 고빈도 메트릭은 샘플링 고려
- **알림**: 중복 알림 방지를 위한 적절한 repeat_interval 설정
- **대시보드**: WebSocket 연결 수 제한

## 🔐 보안 고려사항

- 로그에서 민감한 정보 자동 마스킹
- 알림 채널 인증 정보 안전한 저장
- 대시보드 접근 제어 (프로덕션 환경)
- 메트릭 엔드포인트 접근 제한

## 📝 로그 레벨 가이드

- **DEBUG**: 개발 시 상세 디버깅 정보
- **INFO**: 일반적인 애플리케이션 흐름
- **WARNING**: 주의가 필요한 상황 (성능 저하 등)
- **ERROR**: 에러 발생 (복구 가능)
- **CRITICAL**: 심각한 오류 (서비스 중단 위험)

## 🎨 대시보드 커스터마이징

대시보드는 HTML 템플릿으로 구현되어 있어 쉽게 커스터마이징할 수 있습니다:

1. `dashboard_api.py`의 `_get_dashboard_html()` 메서드 수정
2. Chart.js 설정 변경으로 차트 스타일 조정
3. CSS 스타일 수정으로 UI 개선
4. 새로운 메트릭 차트 추가

## 🤝 기여 가이드

1. 새로운 메트릭 추가: `prometheus_metrics.py` 수정
2. 새로운 알림 채널: `channels.py`에 채널 클래스 추가
3. 새로운 트리거 타입: `triggers.py`에 트리거 클래스 추가
4. 대시보드 기능 추가: `dashboard_api.py` 및 HTML 템플릿 수정

이 모니터링 시스템을 통해 전력시장 RAG 시스템의 건강 상태를 실시간으로 모니터링하고, 문제 발생 시 신속하게 대응할 수 있습니다.