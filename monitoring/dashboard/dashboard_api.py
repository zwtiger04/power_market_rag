"""
대시보드 API 엔드포인트
웹 대시보드를 위한 REST API 및 WebSocket 엔드포인트
"""

import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List, Optional
from datetime import datetime

from .websocket_manager import get_websocket_manager
from .chart_data import get_chart_data_provider
from ..metrics import get_metrics_collector
from ..alerts import get_alert_manager
from ..logging import get_logger


class DashboardAPI:
    """대시보드 API 클래스"""
    
    def __init__(self, app: FastAPI):
        """
        대시보드 API 초기화
        
        Args:
            app: FastAPI 애플리케이션 인스턴스
        """
        self.app = app
        self.logger = get_logger(__name__)
        self.websocket_manager = get_websocket_manager()
        self.chart_data_provider = get_chart_data_provider()
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
        
        # WebSocket 관리자에 차트 데이터 제공자 설정
        self.websocket_manager.set_chart_data_provider(self.chart_data_provider)
        
        # API 라우트 등록
        self._register_routes()
        
        # 정적 파일 서빙 (대시보드 웹 파일들)
        # self.app.mount("/static", StaticFiles(directory="monitoring/dashboard/static"), name="static")
    
    def _register_routes(self):
        """API 라우트 등록"""
        
        @self.app.get("/monitoring", response_class=HTMLResponse)
        async def dashboard_home():
            """대시보드 홈페이지"""
            return self._get_dashboard_html()
        
        @self.app.websocket("/monitoring/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket 엔드포인트"""
            await self._handle_websocket(websocket, client_id)
        
        @self.app.get("/monitoring/api/metrics")
        async def get_current_metrics():
            """현재 메트릭 조회"""
            return self._get_current_metrics()
        
        @self.app.get("/monitoring/api/dashboard")
        async def get_dashboard_data():
            """대시보드 데이터 조회"""
            return self.chart_data_provider.get_dashboard_data()
        
        @self.app.get("/monitoring/api/metrics/history")
        async def get_metrics_history(
            metrics: str = "cpu.usage_percent,memory.virtual.percent",
            minutes: int = 60
        ):
            """메트릭 이력 조회"""
            metric_list = [m.strip() for m in metrics.split(',')]
            return self.chart_data_provider.get_metric_history(metric_list, minutes)
        
        @self.app.get("/monitoring/api/performance")
        async def get_performance_summary():
            """성능 요약 조회"""
            return self.metrics_collector.get_performance_summary()
        
        @self.app.get("/monitoring/api/alerts")
        async def get_alerts(hours: int = 24):
            """알림 통계 조회"""
            return self.alert_manager.get_alert_statistics(hours)
        
        @self.app.get("/monitoring/api/alerts/recent")
        async def get_recent_alerts(limit: int = 50):
            """최근 알림 조회"""
            return self.alert_manager.get_recent_alerts(limit)
        
        @self.app.post("/monitoring/api/alerts/test/{rule_name}")
        async def test_alert(rule_name: str):
            """알림 테스트"""
            success = await self.alert_manager.test_alert(rule_name)
            if success:
                return {"message": f"알림 테스트 성공: {rule_name}"}
            else:
                raise HTTPException(status_code=404, detail="알림 규칙을 찾을 수 없습니다")
        
        @self.app.get("/monitoring/api/system")
        async def get_system_status():
            """시스템 상태 조회"""
            try:
                from ..metrics.system_metrics import get_system_metrics_collector
                system_collector = get_system_metrics_collector()
                return system_collector.get_health_status()
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.get("/monitoring/api/connections")
        async def get_websocket_connections():
            """WebSocket 연결 정보 조회"""
            return self.websocket_manager.get_connection_stats()
        
        @self.app.get("/monitoring/api/prometheus")
        async def get_prometheus_metrics():
            """Prometheus 메트릭 조회"""
            try:
                from ..metrics.prometheus_metrics import get_prometheus_metrics
                prometheus = get_prometheus_metrics()
                return {
                    "metrics": prometheus.get_metrics(),
                    "content_type": prometheus.get_content_type()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/monitoring/api/alerts/history")
        async def clear_alert_history():
            """알림 이력 초기화"""
            self.alert_manager.clear_alert_history()
            return {"message": "알림 이력이 초기화되었습니다"}
    
    async def _handle_websocket(self, websocket: WebSocket, client_id: str):
        """WebSocket 연결 처리"""
        # 클라이언트 ID가 제공되지 않은 경우 생성
        if not client_id or client_id == "auto":
            client_id = str(uuid.uuid4())
        
        # 연결 수락
        connected = await self.websocket_manager.connect(websocket, client_id)
        if not connected:
            return
        
        try:
            # 초기 대시보드 데이터 전송
            dashboard_data = self.chart_data_provider.get_dashboard_data()
            await self.websocket_manager.send_personal_message({
                'type': 'initial_data',
                'data': dashboard_data,
                'timestamp': datetime.now().isoformat()
            }, client_id)
            
            # 메시지 수신 루프
            while True:
                data = await websocket.receive_text()
                await self.websocket_manager.handle_message(client_id, data)
                
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket 연결 종료: {client_id}")
        except Exception as e:
            self.logger.error(f"WebSocket 처리 오류: {e}")
        finally:
            self.websocket_manager.disconnect(client_id)
    
    def _get_current_metrics(self) -> Dict[str, Any]:
        """현재 메트릭 조회"""
        try:
            # 메트릭 수집기에서 성능 요약
            performance = self.metrics_collector.get_performance_summary()
            
            # 시스템 메트릭
            system_metrics = {}
            try:
                from ..metrics.system_metrics import get_system_metrics_collector
                system_collector = get_system_metrics_collector()
                system_metrics = system_collector.get_current_metrics()
            except Exception:
                pass
            
            # 차트 데이터 제공자의 최신 값
            latest_values = self.chart_data_provider.get_latest_values()
            
            return {
                'performance': performance,
                'system': system_metrics,
                'latest_values': latest_values,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"메트릭 조회 실패: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_dashboard_html(self) -> str:
        """대시보드 HTML 페이지 반환"""
        return '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전력시장 RAG 시스템 모니터링</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .status-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        
        .status-card h3 {
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            font-weight: 500;
        }
        
        .status-value {
            font-size: 2rem;
            font-weight: 700;
            color: #333;
        }
        
        .status-change {
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }
        
        .chart-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .chart-card h3 {
            margin-bottom: 1rem;
            color: #333;
            font-size: 1.1rem;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            z-index: 1000;
        }
        
        .connected {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .disconnected {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .healthy { color: #28a745; }
        .warning { color: #ffc107; }
        .critical { color: #dc3545; }
        
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .charts-grid { grid-template-columns: 1fr; }
            .status-grid { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>⚡ 전력시장 RAG 시스템 모니터링</h1>
    </div>
    
    <div class="connection-status" id="connectionStatus">
        🔄 연결 중...
    </div>
    
    <div class="container">
        <div class="status-grid">
            <div class="status-card">
                <h3>시스템 상태</h3>
                <div class="status-value" id="systemStatus">-</div>
            </div>
            <div class="status-card">
                <h3>활성 요청</h3>
                <div class="status-value" id="activeRequests">-</div>
            </div>
            <div class="status-card">
                <h3>CPU 사용률</h3>
                <div class="status-value" id="cpuUsage">-</div>
            </div>
            <div class="status-card">
                <h3>메모리 사용률</h3>
                <div class="status-value" id="memoryUsage">-</div>
            </div>
            <div class="status-card">
                <h3>응답 시간</h3>
                <div class="status-value" id="responseTime">-</div>
            </div>
            <div class="status-card">
                <h3>캐시 히트율</h3>
                <div class="status-value" id="cacheHitRate">-</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h3>📊 CPU 사용률</h3>
                <div class="chart-container">
                    <canvas id="cpuChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>💾 메모리 사용률</h3>
                <div class="chart-container">
                    <canvas id="memoryChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>🌐 API 요청</h3>
                <div class="chart-container">
                    <canvas id="requestsChart"></canvas>
                </div>
            </div>
            <div class="chart-card">
                <h3>⚡ 응답 시간</h3>
                <div class="chart-container">
                    <canvas id="responseTimeChart"></canvas>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // WebSocket 연결
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/monitoring/ws/dashboard-${Date.now()}`;
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        
        // 차트 설정
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
        
        const chartConfig = {
            type: 'line',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute'
                        }
                    },
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        };
        
        // 차트 초기화
        const charts = {
            cpu: new Chart(document.getElementById('cpuChart'), {
                ...chartConfig,
                data: {
                    datasets: [{
                        label: 'CPU %',
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        data: []
                    }]
                },
                options: {
                    ...chartConfig.options,
                    scales: {
                        ...chartConfig.options.scales,
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            }),
            memory: new Chart(document.getElementById('memoryChart'), {
                ...chartConfig,
                data: {
                    datasets: [{
                        label: 'Memory %',
                        borderColor: '#f093fb',
                        backgroundColor: 'rgba(240, 147, 251, 0.1)',
                        data: []
                    }]
                },
                options: {
                    ...chartConfig.options,
                    scales: {
                        ...chartConfig.options.scales,
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            }),
            requests: new Chart(document.getElementById('requestsChart'), {
                ...chartConfig,
                data: {
                    datasets: [{
                        label: 'Active Requests',
                        borderColor: '#4ecdc4',
                        backgroundColor: 'rgba(78, 205, 196, 0.1)',
                        data: []
                    }]
                }
            }),
            responseTime: new Chart(document.getElementById('responseTimeChart'), {
                ...chartConfig,
                data: {
                    datasets: [{
                        label: 'Response Time (ms)',
                        borderColor: '#fce38a',
                        backgroundColor: 'rgba(252, 227, 138, 0.1)',
                        data: []
                    }]
                }
            })
        };
        
        function connectWebSocket() {
            try {
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function() {
                    console.log('WebSocket 연결됨');
                    updateConnectionStatus(true);
                    reconnectAttempts = 0;
                    
                    // 대시보드 데이터 요청
                    ws.send(JSON.stringify({ type: 'get_dashboard_data' }));
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                };
                
                ws.onclose = function() {
                    console.log('WebSocket 연결 종료');
                    updateConnectionStatus(false);
                    attemptReconnect();
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket 오류:', error);
                    updateConnectionStatus(false);
                };
                
            } catch (error) {
                console.error('WebSocket 연결 실패:', error);
                updateConnectionStatus(false);
                attemptReconnect();
            }
        }
        
        function attemptReconnect() {
            if (reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`재연결 시도 ${reconnectAttempts}/${maxReconnectAttempts}`);
                setTimeout(connectWebSocket, 2000 * reconnectAttempts);
            }
        }
        
        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connectionStatus');
            if (connected) {
                statusEl.textContent = '🟢 연결됨';
                statusEl.className = 'connection-status connected';
            } else {
                statusEl.textContent = '🔴 연결 끊김';
                statusEl.className = 'connection-status disconnected';
            }
        }
        
        function handleWebSocketMessage(data) {
            switch (data.type) {
                case 'initial_data':
                case 'dashboard_data':
                    updateDashboard(data.data);
                    break;
                case 'real_time_metrics':
                    updateRealTimeMetrics(data.data);
                    break;
                case 'alert_notification':
                    showAlert(data.data);
                    break;
            }
        }
        
        function updateDashboard(data) {
            if (data.overview) {
                const overview = data.overview;
                updateStatusCard('systemStatus', overview.system_status, getStatusClass(overview.system_status));
                updateStatusCard('activeRequests', overview.active_requests);
                updateStatusCard('cpuUsage', `${overview.cpu_usage.toFixed(1)}%`);
                updateStatusCard('memoryUsage', `${overview.memory_usage.toFixed(1)}%`);
                updateStatusCard('responseTime', `${(overview.avg_response_time * 1000).toFixed(0)}ms`);
                updateStatusCard('cacheHitRate', `${overview.cache_hit_rate.toFixed(1)}%`);
            }
            
            if (data.charts) {
                updateCharts(data.charts);
            }
        }
        
        function updateRealTimeMetrics(data) {
            if (data.metrics) {
                const metrics = data.metrics;
                updateStatusCard('cpuUsage', `${metrics.cpu_usage.toFixed(1)}%`);
                updateStatusCard('memoryUsage', `${metrics.memory_usage.toFixed(1)}%`);
                updateStatusCard('activeRequests', metrics.active_requests);
                updateStatusCard('responseTime', `${(metrics.response_time * 1000).toFixed(0)}ms`);
                updateStatusCard('cacheHitRate', `${metrics.cache_hit_rate.toFixed(1)}%`);
                
                // 차트에 새 데이터 포인트 추가
                const timestamp = new Date(data.timestamp);
                addDataPoint(charts.cpu, timestamp, metrics.cpu_usage);
                addDataPoint(charts.memory, timestamp, metrics.memory_usage);
                addDataPoint(charts.requests, timestamp, metrics.active_requests);
                addDataPoint(charts.responseTime, timestamp, metrics.response_time * 1000);
            }
        }
        
        function updateStatusCard(id, value, className = '') {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
                if (className) {
                    el.className = `status-value ${className}`;
                }
            }
        }
        
        function getStatusClass(status) {
            switch (status) {
                case 'healthy': return 'healthy';
                case 'warning': case 'degraded': return 'warning';
                case 'critical': return 'critical';
                default: return '';
            }
        }
        
        function updateCharts(chartData) {
            Object.keys(charts).forEach(chartName => {
                const data = chartData[`${chartName}_usage`] || chartData[chartName];
                if (data && Array.isArray(data)) {
                    charts[chartName].data.datasets[0].data = data.map(point => ({
                        x: new Date(point.timestamp),
                        y: point.value
                    }));
                    charts[chartName].update('none');
                }
            });
        }
        
        function addDataPoint(chart, timestamp, value) {
            const data = chart.data.datasets[0].data;
            data.push({ x: timestamp, y: value });
            
            // 최대 50개 데이터 포인트 유지
            if (data.length > 50) {
                data.shift();
            }
            
            chart.update('none');
        }
        
        function showAlert(alertData) {
            // 간단한 알림 표시 (실제로는 더 정교한 UI 구현)
            console.log('Alert:', alertData);
        }
        
        // 초기 연결
        connectWebSocket();
        
        // 주기적으로 연결 상태 확인
        setInterval(() => {
            if (!ws || ws.readyState === WebSocket.CLOSED) {
                updateConnectionStatus(false);
                if (reconnectAttempts === 0) {
                    attemptReconnect();
                }
            }
        }, 5000);
    </script>
</body>
</html>
        '''
    
    def update_metrics(self, metrics: Dict[str, Any]):
        """메트릭 업데이트 (외부에서 호출)"""
        # 차트 데이터 제공자에 메트릭 추가
        self.chart_data_provider.add_metrics(metrics)


# 전역 대시보드 API 인스턴스
_dashboard_api: Optional[DashboardAPI] = None


def setup_dashboard_api(app: FastAPI) -> DashboardAPI:
    """대시보드 API 설정"""
    global _dashboard_api
    if _dashboard_api is None:
        _dashboard_api = DashboardAPI(app)
    return _dashboard_api


def get_dashboard_api() -> Optional[DashboardAPI]:
    """대시보드 API 인스턴스 반환"""
    return _dashboard_api