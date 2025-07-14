"""
WebSocket 관리자
실시간 메트릭 스트리밍
"""

import json
import asyncio
import weakref
from typing import Dict, Any, Set, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from ..logging import get_logger


class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        """WebSocket 관리자 초기화"""
        self.logger = get_logger(__name__)
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of metric names
        self._broadcast_task: Optional[asyncio.Task] = None
        self._is_broadcasting = False
        
        # 차트 데이터 제공자 참조
        self._chart_data_provider = None
    
    def set_chart_data_provider(self, provider):
        """차트 데이터 제공자 설정"""
        self._chart_data_provider = provider
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """WebSocket 연결 수락"""
        try:
            await websocket.accept()
            
            self.active_connections[client_id] = websocket
            self.connection_metadata[client_id] = {
                'connected_at': datetime.now(),
                'ip_address': websocket.client.host if websocket.client else 'unknown',
                'user_agent': websocket.headers.get('user-agent', 'unknown')
            }
            self.subscriptions[client_id] = set()
            
            self.logger.info(f"WebSocket 연결 수락: {client_id}")
            
            # 브로드캐스트 시작
            if not self._is_broadcasting:
                self.start_broadcasting()
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket 연결 실패: {e}")
            return False
    
    def disconnect(self, client_id: str):
        """WebSocket 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
        
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
        
        self.logger.info(f"WebSocket 연결 해제: {client_id}")
        
        # 연결이 없으면 브로드캐스트 중지
        if not self.active_connections and self._is_broadcasting:
            self.stop_broadcasting()
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str) -> bool:
        """특정 클라이언트에게 메시지 발송"""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False
        
        try:
            await websocket.send_text(json.dumps(message))
            return True
        except WebSocketDisconnect:
            self.disconnect(client_id)
            return False
        except Exception as e:
            self.logger.error(f"WebSocket 메시지 발송 실패 ({client_id}): {e}")
            return False
    
    async def broadcast(self, message: Dict[str, Any], exclude_clients: Set[str] = None):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        if not self.active_connections:
            return
        
        exclude_clients = exclude_clients or set()
        message_text = json.dumps(message)
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if client_id in exclude_clients:
                continue
            
            try:
                await websocket.send_text(message_text)
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                self.logger.error(f"브로드캐스트 실패 ({client_id}): {e}")
                disconnected_clients.append(client_id)
        
        # 연결 해제된 클라이언트 정리
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def handle_message(self, client_id: str, message: str):
        """클라이언트 메시지 처리"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                await self._handle_subscribe(client_id, data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, data)
            elif message_type == 'get_dashboard_data':
                await self._handle_get_dashboard_data(client_id)
            elif message_type == 'get_metrics_history':
                await self._handle_get_metrics_history(client_id, data)
            elif message_type == 'ping':
                await self._handle_ping(client_id)
            else:
                await self.send_personal_message({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }, client_id)
                
        except json.JSONDecodeError:
            await self.send_personal_message({
                'type': 'error',
                'message': 'Invalid JSON format'
            }, client_id)
        except Exception as e:
            self.logger.error(f"메시지 처리 실패 ({client_id}): {e}")
            await self.send_personal_message({
                'type': 'error',
                'message': 'Message processing failed'
            }, client_id)
    
    async def _handle_subscribe(self, client_id: str, data: Dict[str, Any]):
        """메트릭 구독 처리"""
        metrics = data.get('metrics', [])
        if not isinstance(metrics, list):
            await self.send_personal_message({
                'type': 'error',
                'message': 'Metrics must be a list'
            }, client_id)
            return
        
        self.subscriptions[client_id].update(metrics)
        
        await self.send_personal_message({
            'type': 'subscription_confirmed',
            'subscribed_metrics': list(self.subscriptions[client_id])
        }, client_id)
        
        self.logger.info(f"클라이언트 {client_id} 메트릭 구독: {metrics}")
    
    async def _handle_unsubscribe(self, client_id: str, data: Dict[str, Any]):
        """메트릭 구독 해제 처리"""
        metrics = data.get('metrics', [])
        if not isinstance(metrics, list):
            return
        
        self.subscriptions[client_id].difference_update(metrics)
        
        await self.send_personal_message({
            'type': 'unsubscription_confirmed',
            'remaining_metrics': list(self.subscriptions[client_id])
        }, client_id)
        
        self.logger.info(f"클라이언트 {client_id} 메트릭 구독 해제: {metrics}")
    
    async def _handle_get_dashboard_data(self, client_id: str):
        """대시보드 데이터 요청 처리"""
        if not self._chart_data_provider:
            await self.send_personal_message({
                'type': 'error',
                'message': 'Chart data provider not available'
            }, client_id)
            return
        
        try:
            dashboard_data = self._chart_data_provider.get_dashboard_data()
            
            await self.send_personal_message({
                'type': 'dashboard_data',
                'data': dashboard_data,
                'timestamp': datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            self.logger.error(f"대시보드 데이터 조회 실패: {e}")
            await self.send_personal_message({
                'type': 'error',
                'message': 'Failed to get dashboard data'
            }, client_id)
    
    async def _handle_get_metrics_history(self, client_id: str, data: Dict[str, Any]):
        """메트릭 이력 데이터 요청 처리"""
        if not self._chart_data_provider:
            await self.send_personal_message({
                'type': 'error',
                'message': 'Chart data provider not available'
            }, client_id)
            return
        
        try:
            metric_names = data.get('metrics', [])
            minutes = data.get('minutes', 60)
            
            if not isinstance(metric_names, list):
                await self.send_personal_message({
                    'type': 'error',
                    'message': 'Metrics must be a list'
                }, client_id)
                return
            
            history_data = self._chart_data_provider.get_metric_history(metric_names, minutes)
            
            await self.send_personal_message({
                'type': 'metrics_history',
                'data': history_data,
                'timestamp': datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            self.logger.error(f"메트릭 이력 조회 실패: {e}")
            await self.send_personal_message({
                'type': 'error',
                'message': 'Failed to get metrics history'
            }, client_id)
    
    async def _handle_ping(self, client_id: str):
        """핑 요청 처리"""
        await self.send_personal_message({
            'type': 'pong',
            'timestamp': datetime.now().isoformat()
        }, client_id)
    
    def start_broadcasting(self):
        """실시간 브로드캐스트 시작"""
        if self._is_broadcasting:
            return
        
        self._is_broadcasting = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        self.logger.info("실시간 브로드캐스트 시작")
    
    def stop_broadcasting(self):
        """실시간 브로드캐스트 중지"""
        if not self._is_broadcasting:
            return
        
        self._is_broadcasting = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
        
        self.logger.info("실시간 브로드캐스트 중지")
    
    async def _broadcast_loop(self):
        """브로드캐스트 루프"""
        try:
            while self._is_broadcasting:
                if self.active_connections and self._chart_data_provider:
                    try:
                        # 실시간 메트릭 데이터 가져오기
                        real_time_data = self._chart_data_provider.get_real_time_metrics()
                        
                        # 브로드캐스트 메시지 생성
                        message = {
                            'type': 'real_time_metrics',
                            'data': real_time_data,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # 모든 클라이언트에게 브로드캐스트
                        await self.broadcast(message)
                        
                    except Exception as e:
                        self.logger.error(f"브로드캐스트 루프 오류: {e}")
                
                # 5초마다 업데이트
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            self.logger.info("브로드캐스트 루프 취소됨")
        except Exception as e:
            self.logger.error(f"브로드캐스트 루프 예외: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계 반환"""
        return {
            'total_connections': len(self.active_connections),
            'active_connections': list(self.active_connections.keys()),
            'is_broadcasting': self._is_broadcasting,
            'connections_detail': [
                {
                    'client_id': client_id,
                    'connected_at': metadata['connected_at'].isoformat(),
                    'ip_address': metadata['ip_address'],
                    'subscriptions': list(self.subscriptions.get(client_id, []))
                }
                for client_id, metadata in self.connection_metadata.items()
            ]
        }
    
    async def send_alert_notification(self, alert_data: Dict[str, Any]):
        """알림 메시지 브로드캐스트"""
        message = {
            'type': 'alert_notification',
            'data': alert_data,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.broadcast(message)
        self.logger.info(f"알림 브로드캐스트: {alert_data.get('title', 'Unknown')}")
    
    async def send_system_status_update(self, status_data: Dict[str, Any]):
        """시스템 상태 업데이트 브로드캐스트"""
        message = {
            'type': 'system_status_update',
            'data': status_data,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.broadcast(message)


# 전역 WebSocket 관리자 인스턴스
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """전역 WebSocket 관리자 인스턴스 반환"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager