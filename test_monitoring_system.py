#!/usr/bin/env python3
"""
모니터링 및 로깅 시스템 테스트
"""

import asyncio
import time
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

async def test_monitoring_system():
    """모니터링 시스템 전체 테스트"""
    print("🔄 모니터링 및 로깅 시스템 테스트 시작...")
    
    try:
        # 1. 로깅 시스템 테스트
        print("\n1. 로깅 시스템 테스트")
        from monitoring import get_logger, setup_logging
        
        # 로깅 설정
        setup_logging(
            level="INFO",
            log_dir="./logs",
            app_name="test_monitoring",
            environment="development"
        )
        
        logger = get_logger("test_monitoring")
        logger.info("로깅 시스템 테스트 시작")
        logger.warning("테스트 경고 메시지")
        
        # 컨텍스트와 함께 로깅
        with logger.bind(test_id="123", operation="test"):
            logger.info("컨텍스트가 포함된 로그 메시지")
        
        print("   ✅ 로깅 시스템 정상 작동")
        
        # 2. 메트릭 수집 시스템 테스트
        print("\n2. 메트릭 수집 시스템 테스트")
        from monitoring import get_metrics_collector, time_metric
        
        metrics_collector = get_metrics_collector()
        
        # 기본 메트릭 기록
        request_id = metrics_collector.start_request()
        time.sleep(0.1)
        metrics_collector.end_request(request_id, "GET", "/test", 200, 0.1)
        
        # 캐시 메트릭 기록
        metrics_collector.record_cache_hit("test")
        metrics_collector.record_cache_miss("test")
        
        # 성능 요약 조회
        performance = metrics_collector.get_performance_summary()
        print(f"   - 총 API 호출: {performance['total_api_calls']}")
        print(f"   - 평균 응답시간: {performance['avg_response_time']:.4f}초")
        print(f"   - 캐시 히트율: {performance['cache_hit_rate']:.1f}%")
        
        print("   ✅ 메트릭 수집 시스템 정상 작동")
        
        # 3. 데코레이터 테스트
        print("\n3. 메트릭 데코레이터 테스트")
        
        @time_metric(labels={'component': 'test'})
        def test_function():
            time.sleep(0.05)
            return "테스트 완료"
        
        result = test_function()
        print(f"   - 함수 실행 결과: {result}")
        print("   ✅ 메트릭 데코레이터 정상 작동")
        
        # 4. 시스템 메트릭 테스트
        print("\n4. 시스템 메트릭 테스트")
        from monitoring.metrics.system_metrics import get_system_metrics_collector
        
        system_collector = get_system_metrics_collector()
        current_metrics = system_collector.get_current_metrics()
        
        if 'error' not in current_metrics:
            cpu_usage = current_metrics.get('cpu', {}).get('usage_percent', 0)
            memory_usage = current_metrics.get('memory', {}).get('virtual', {}).get('percent', 0)
            print(f"   - CPU 사용률: {cpu_usage:.1f}%")
            print(f"   - 메모리 사용률: {memory_usage:.1f}%")
            print("   ✅ 시스템 메트릭 정상 작동")
        else:
            print(f"   ⚠️ 시스템 메트릭 오류: {current_metrics['error']}")
        
        # 5. 알림 시스템 테스트
        print("\n5. 알림 시스템 테스트")
        from monitoring import get_alert_manager
        
        alert_manager = get_alert_manager()
        
        # 테스트 메트릭으로 알림 평가
        test_metrics = {
            'cpu': {'usage_percent': 95.0},  # 높은 CPU 사용률
            'memory': {'virtual': {'percent': 90.0}},
            'api': {'error_rate': 0.1}
        }
        
        await alert_manager.process_metrics(test_metrics)
        
        # 알림 통계 조회
        alert_stats = alert_manager.get_alert_statistics(1)
        print(f"   - 활성 규칙 수: {alert_stats['active_rules']}")
        print(f"   - 총 규칙 수: {alert_stats['total_rules']}")
        print("   ✅ 알림 시스템 정상 작동")
        
        # 6. 차트 데이터 제공자 테스트
        print("\n6. 차트 데이터 제공자 테스트")
        from monitoring.dashboard.chart_data import get_chart_data_provider
        
        chart_provider = get_chart_data_provider()
        
        # 테스트 메트릭 추가
        chart_provider.add_metrics({
            'cpu': {'usage_percent': 75.5},
            'memory': {'virtual': {'percent': 68.2}},
            'api': {'active_requests': 12, 'avg_response_time': 0.8}
        })
        
        # 대시보드 데이터 조회
        dashboard_data = chart_provider.get_dashboard_data()
        overview = dashboard_data.get('overview', {})
        
        print(f"   - 시스템 상태: {overview.get('system_status', 'unknown')}")
        print(f"   - CPU 사용률: {overview.get('cpu_usage', 0):.1f}%")
        print(f"   - 메모리 사용률: {overview.get('memory_usage', 0):.1f}%")
        print("   ✅ 차트 데이터 제공자 정상 작동")
        
        # 7. Prometheus 메트릭 테스트
        print("\n7. Prometheus 메트릭 테스트")
        from monitoring.metrics.prometheus_metrics import get_prometheus_metrics
        
        prometheus = get_prometheus_metrics()
        
        # 메트릭 기록
        prometheus.record_api_request("GET", "/test", 200, 0.5)
        prometheus.record_search_request("hybrid", 0.3, 5)
        
        # 메트릭 출력 (일부만)
        metrics_output = prometheus.get_metrics()
        if isinstance(metrics_output, bytes):
            metrics_output = metrics_output.decode('utf-8')
        
        metrics_lines = metrics_output.split('\n')[:10]  # 첫 10줄만
        
        print("   - Prometheus 메트릭 샘플:")
        for line in metrics_lines:
            if line.strip() and not line.startswith('#'):
                print(f"     {line}")
                break
        
        print("   ✅ Prometheus 메트릭 정상 작동")
        
        print("\n✅ 모니터링 및 로깅 시스템 테스트 완료!")
        print("\n📊 시스템 구성 요소:")
        print("   • 구조화된 로깅 시스템 (JSON + 콘솔)")
        print("   • 메트릭 수집 및 Prometheus 연동")
        print("   • 실시간 알림 시스템")
        print("   • 시스템 리소스 모니터링")
        print("   • 웹 대시보드 (실시간 차트)")
        print("   • WebSocket 기반 실시간 업데이트")
        
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 임포트 실패: {e}")
        print("💡 필요한 패키지를 설치하세요:")
        print("   pip install prometheus-client psutil loguru pyyaml")
        return False
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_monitoring_system())
    sys.exit(0 if success else 1)