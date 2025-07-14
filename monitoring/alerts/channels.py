"""
알림 채널 구현
이메일, Slack, 웹훅 등 다양한 알림 채널 지원
"""

import json
import smtplib
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dataclasses import dataclass

from .rules import AlertRule, Severity


@dataclass
class AlertMessage:
    """알림 메시지 클래스"""
    rule: AlertRule
    timestamp: datetime
    metrics: Dict[str, Any]
    message: str
    title: str
    severity: Severity
    labels: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'rule_name': self.rule.name,
            'timestamp': self.timestamp.isoformat(),
            'message': self.message,
            'title': self.title,
            'severity': self.severity.value,
            'labels': self.labels,
            'metrics': self.metrics
        }


class AlertChannel(ABC):
    """알림 채널 추상 클래스"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        알림 채널 초기화
        
        Args:
            name: 채널 이름
            config: 채널 설정
        """
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    async def send_alert(self, message: AlertMessage) -> bool:
        """
        알림 발송
        
        Args:
            message: 알림 메시지
            
        Returns:
            발송 성공 여부
        """
        pass
    
    def format_message(self, message: AlertMessage) -> str:
        """메시지 포맷팅"""
        severity_emoji = {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️", 
            Severity.ERROR: "❌",
            Severity.CRITICAL: "🚨"
        }
        
        emoji = severity_emoji.get(message.severity, "📊")
        timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        formatted = f"{emoji} **{message.title}**\n\n"
        formatted += f"**심각도:** {message.severity.value.upper()}\n"
        formatted += f"**시간:** {timestamp}\n"
        formatted += f"**메시지:** {message.message}\n"
        
        if message.labels:
            formatted += f"**라벨:** {', '.join(f'{k}={v}' for k, v in message.labels.items())}\n"
        
        # 관련 메트릭 표시
        if message.metrics:
            formatted += f"\n**관련 메트릭:**\n"
            for key, value in message.metrics.items():
                if isinstance(value, (int, float)):
                    formatted += f"- {key}: {value:.2f}\n"
                else:
                    formatted += f"- {key}: {value}\n"
        
        return formatted


class ConsoleChannel(AlertChannel):
    """콘솔 알림 채널"""
    
    async def send_alert(self, message: AlertMessage) -> bool:
        """콘솔에 알림 출력"""
        try:
            formatted = self.format_message(message)
            print(f"\n{'='*60}")
            print("🔔 ALERT NOTIFICATION")
            print('='*60)
            print(formatted)
            print('='*60)
            return True
        except Exception as e:
            print(f"콘솔 알림 발송 실패: {e}")
            return False


class EmailChannel(AlertChannel):
    """이메일 알림 채널"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        이메일 채널 초기화
        
        Config 예시:
        {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "your-email@gmail.com",
            "password": "app-password",
            "from_email": "rag-system@company.com",
            "to_emails": ["admin@company.com", "ops@company.com"],
            "use_tls": true
        }
        """
        super().__init__(name, config)
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email', self.username)
        self.to_emails = config.get('to_emails', [])
        self.use_tls = config.get('use_tls', True)
    
    async def send_alert(self, message: AlertMessage) -> bool:
        """이메일 알림 발송"""
        if not self.enabled or not self.to_emails:
            return False
        
        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{message.severity.value.upper()}] {message.title}"
            
            # HTML 본문 생성
            html_body = self._create_html_body(message)
            msg.attach(MIMEText(html_body, 'html'))
            
            # SMTP 서버 연결 및 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.username and self.password:
                    server.login(self.username, self.password)
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"이메일 알림 발송 실패: {e}")
            return False
    
    def _create_html_body(self, message: AlertMessage) -> str:
        """HTML 이메일 본문 생성"""
        severity_colors = {
            Severity.INFO: "#17a2b8",
            Severity.WARNING: "#ffc107",
            Severity.ERROR: "#dc3545", 
            Severity.CRITICAL: "#721c24"
        }
        
        color = severity_colors.get(message.severity, "#6c757d")
        timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0;">
                    <h2 style="margin: 0;">🔔 RAG System Alert</h2>
                </div>
                
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 5px 5px;">
                    <h3 style="color: {color}; margin-top: 0;">{message.title}</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">심각도:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{message.severity.value.upper()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">시간:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{timestamp}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">규칙:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{message.rule.name}</td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 20px;">
                        <h4>메시지</h4>
                        <p style="background-color: #f8f9fa; padding: 10px; border-radius: 3px;">
                            {message.message}
                        </p>
                    </div>
        """
        
        # 라벨 추가
        if message.labels:
            html += """
                    <div style="margin-top: 15px;">
                        <h4>라벨</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 5px;">
            """
            for key, value in message.labels.items():
                html += f'<span style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 12px;">{key}={value}</span>'
            html += "</div></div>"
        
        # 메트릭 추가
        if message.metrics:
            html += """
                    <div style="margin-top: 15px;">
                        <h4>관련 메트릭</h4>
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            """
            for key, value in message.metrics.items():
                if isinstance(value, (int, float)):
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
                html += f"""
                            <tr>
                                <td style="padding: 4px; border-bottom: 1px solid #eee;">{key}</td>
                                <td style="padding: 4px; border-bottom: 1px solid #eee; text-align: right;">{formatted_value}</td>
                            </tr>
                """
            html += "</table></div>"
        
        html += """
                    <div style="margin-top: 20px; font-size: 12px; color: #6c757d;">
                        이 알림은 전력시장 RAG 시스템 모니터링에서 자동 발송되었습니다.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


class SlackChannel(AlertChannel):
    """Slack 알림 채널"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Slack 채널 초기화
        
        Config 예시:
        {
            "webhook_url": "https://hooks.slack.com/services/...",
            "channel": "#alerts",
            "username": "RAG Alert Bot",
            "icon_emoji": ":rotating_light:"
        }
        """
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#alerts')
        self.username = config.get('username', 'RAG Alert Bot')
        self.icon_emoji = config.get('icon_emoji', ':rotating_light:')
    
    async def send_alert(self, message: AlertMessage) -> bool:
        """Slack 알림 발송"""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            # Slack 메시지 페이로드 생성
            payload = self._create_slack_payload(message)
            
            # 웹훅 요청 발송
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Slack 알림 발송 실패: {e}")
            return False
    
    def _create_slack_payload(self, message: AlertMessage) -> Dict[str, Any]:
        """Slack 메시지 페이로드 생성"""
        severity_colors = {
            Severity.INFO: "#36a64f",     # 녹색
            Severity.WARNING: "#ff9500",  # 주황색
            Severity.ERROR: "#ff0000",    # 빨간색
            Severity.CRITICAL: "#800000"  # 진한 빨간색
        }
        
        color = severity_colors.get(message.severity, "#808080")
        timestamp = int(message.timestamp.timestamp())
        
        # 기본 페이로드
        payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "title": message.title,
                    "text": message.message,
                    "fields": [
                        {
                            "title": "심각도",
                            "value": message.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "규칙",
                            "value": message.rule.name,
                            "short": True
                        }
                    ],
                    "footer": "RAG System Monitoring",
                    "ts": timestamp
                }
            ]
        }
        
        # 라벨 추가
        if message.labels:
            labels_text = ", ".join(f"{k}={v}" for k, v in message.labels.items())
            payload["attachments"][0]["fields"].append({
                "title": "라벨",
                "value": labels_text,
                "short": False
            })
        
        # 주요 메트릭 추가
        if message.metrics:
            metrics_text = ""
            for key, value in list(message.metrics.items())[:5]:  # 최대 5개만
                if isinstance(value, (int, float)):
                    metrics_text += f"{key}: {value:.2f}\\n"
                else:
                    metrics_text += f"{key}: {value}\\n"
            
            if metrics_text:
                payload["attachments"][0]["fields"].append({
                    "title": "관련 메트릭",
                    "value": metrics_text,
                    "short": False
                })
        
        return payload


class WebhookChannel(AlertChannel):
    """웹훅 알림 채널"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        웹훅 채널 초기화
        
        Config 예시:
        {
            "url": "https://api.your-service.com/alerts",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer token",
                "Content-Type": "application/json"
            },
            "timeout": 10
        }
        """
        super().__init__(name, config)
        self.url = config.get('url')
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {'Content-Type': 'application/json'})
        self.timeout = config.get('timeout', 10)
    
    async def send_alert(self, message: AlertMessage) -> bool:
        """웹훅 알림 발송"""
        if not self.enabled or not self.url:
            return False
        
        try:
            # 페이로드 생성
            payload = message.to_dict()
            
            # HTTP 요청 발송
            response = requests.request(
                method=self.method,
                url=self.url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            return 200 <= response.status_code < 300
            
        except Exception as e:
            print(f"웹훅 알림 발송 실패: {e}")
            return False


class DiscordChannel(AlertChannel):
    """Discord 알림 채널"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Discord 채널 초기화
        
        Config 예시:
        {
            "webhook_url": "https://discord.com/api/webhooks/...",
            "username": "RAG Alert Bot",
            "avatar_url": "https://..."
        }
        """
        super().__init__(name, config)
        self.webhook_url = config.get('webhook_url')
        self.username = config.get('username', 'RAG Alert Bot')
        self.avatar_url = config.get('avatar_url')
    
    async def send_alert(self, message: AlertMessage) -> bool:
        """Discord 알림 발송"""
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            # Discord 임베드 생성
            embed = self._create_discord_embed(message)
            
            payload = {
                "username": self.username,
                "embeds": [embed]
            }
            
            if self.avatar_url:
                payload["avatar_url"] = self.avatar_url
            
            # 웹훅 요청 발송
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            return response.status_code == 204  # Discord는 204 반환
            
        except Exception as e:
            print(f"Discord 알림 발송 실패: {e}")
            return False
    
    def _create_discord_embed(self, message: AlertMessage) -> Dict[str, Any]:
        """Discord 임베드 생성"""
        severity_colors = {
            Severity.INFO: 0x17a2b8,
            Severity.WARNING: 0xffc107,
            Severity.ERROR: 0xdc3545,
            Severity.CRITICAL: 0x721c24
        }
        
        color = severity_colors.get(message.severity, 0x6c757d)
        timestamp = message.timestamp.isoformat()
        
        embed = {
            "title": message.title,
            "description": message.message,
            "color": color,
            "timestamp": timestamp,
            "footer": {
                "text": "RAG System Monitoring"
            },
            "fields": [
                {
                    "name": "심각도",
                    "value": message.severity.value.upper(),
                    "inline": True
                },
                {
                    "name": "규칙",
                    "value": message.rule.name,
                    "inline": True
                }
            ]
        }
        
        # 라벨 추가
        if message.labels:
            labels_text = ", ".join(f"{k}={v}" for k, v in message.labels.items())
            embed["fields"].append({
                "name": "라벨",
                "value": labels_text,
                "inline": False
            })
        
        return embed


# 채널 팩토리
def create_channel(channel_type: str, name: str, config: Dict[str, Any]) -> AlertChannel:
    """알림 채널 생성 팩토리 함수"""
    channel_classes = {
        'console': ConsoleChannel,
        'email': EmailChannel,
        'slack': SlackChannel,
        'webhook': WebhookChannel,
        'discord': DiscordChannel
    }
    
    channel_class = channel_classes.get(channel_type.lower())
    if not channel_class:
        raise ValueError(f"지원되지 않는 채널 타입: {channel_type}")
    
    return channel_class(name, config)