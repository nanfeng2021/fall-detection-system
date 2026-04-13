"""
告警通知模块 - 支持多种推送渠道

支持的推送方式:
- 微信（企业微信机器人/个人微信）
- 短信（腾讯云短信）
- 邮件（SMTP）
- Webhook（钉钉、飞书、自定义）
- 语音电话（可选）

使用方式:
1. 配置通知渠道
2. 在检测到跌倒时调用 notify()
3. 支持多渠道并发推送
"""

import asyncio
import smtplib
import requests
import json
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import hashlib
import hmac
import base64
import time


@dataclass
class AlertMessage:
    """告警消息结构"""
    title: str
    content: str
    alert_type: str  # 'fall_confirmed', 'fall_suspected', 'system_error'
    timestamp: datetime
    location: Optional[str] = None
    confidence: float = 0.0
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'title': self.title,
            'content': self.content,
            'alert_type': self.alert_type,
            'timestamp': self.timestamp.isoformat(),
            'location': self.location,
            'confidence': self.confidence,
            'metadata': self.metadata or {}
        }


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.send_count = 0
        self.error_count = 0
    
    @abstractmethod
    async def send(self, message: AlertMessage) -> bool:
        """
        发送告警消息
        
        Args:
            message: 告警消息
            
        Returns:
            bool: 是否发送成功
        """
        pass
    
    def _increment_send(self):
        self.send_count += 1
    
    def _increment_error(self):
        self.error_count += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'send_count': self.send_count,
            'error_count': self.error_count,
            'success_rate': (
                self.send_count / (self.send_count + self.error_count) * 100
                if (self.send_count + self.error_count) > 0 else 100
            )
        }


class WeComBotNotifier(NotificationChannel):
    """企业微信机器人通知"""
    
    def __init__(self, webhook_url: str, enabled: bool = True):
        """
        初始化企业微信机器人
        
        Args:
            webhook_url: 机器人 Webhook URL
        """
        super().__init__("企业微信机器人", enabled)
        self.webhook_url = webhook_url
    
    async def send(self, message: AlertMessage) -> bool:
        """发送 Markdown 格式消息到企业微信"""
        if not self.enabled:
            return False
        
        try:
            # 构建消息
            if message.alert_type == 'fall_confirmed':
                emoji = "🚨"
                color = "warning"
                title = f"{emoji} **确认摔倒告警**"
            elif message.alert_type == 'fall_suspected':
                emoji = "⚠️"
                color = "comment"
                title = f"{emoji} **疑似摔倒告警**"
            else:
                emoji = "ℹ️"
                color = "info"
                title = f"{emoji} **系统通知**"
            
            time_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            markdown = f"""## {title}

> **时间**: {time_str}
> **位置**: {message.location or '未知'}
> **置信度**: {message.confidence:.0%}

---

**详情**:
{message.content}

---
*摔倒检测系统自动发送*"""
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('errcode') == 0:
                self._increment_send()
                print(f"✅ 企业微信通知已发送")
                return True
            else:
                self._increment_error()
                print(f"❌ 企业微信通知失败：{result}")
                return False
                
        except Exception as e:
            self._increment_error()
            print(f"❌ 企业微信通知异常：{e}")
            return False


class FeishuBotNotifier(NotificationChannel):
    """飞书机器人通知"""
    
    def __init__(self, webhook_url: str, secret: str = None, enabled: bool = True):
        """
        初始化飞书机器人
        
        Args:
            webhook_url: 机器人 Webhook URL
            secret: 签名密钥（可选）
        """
        super().__init__("飞书机器人", enabled)
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_signature(self, timestamp: int) -> str:
        """生成飞书签名"""
        if not self.secret:
            return ""
        
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return sign
    
    async def send(self, message: AlertMessage) -> bool:
        """发送交互式卡片消息到飞书"""
        if not self.enabled:
            return False
        
        try:
            timestamp = int(time.time())
            
            # 构建卡片消息
            if message.alert_type == 'fall_confirmed':
                color = "red"
                title = "🚨 确认摔倒告警"
            elif message.alert_type == 'fall_suspected':
                color = "orange"
                title = "⚠️ 疑似摔倒告警"
            else:
                color = "blue"
                title = "ℹ️ 系统通知"
            
            time_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            card = {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "template": color,
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**⏰ 时间**\n{time_str}"
                                }
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**📍 位置**\n{message.location or '未知'}"
                                }
                            }
                        ]
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**📊 置信度**: {message.confidence:.0%}\n\n**📝 详情**:\n{message.content}"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "摔倒检测系统自动发送"
                            }
                        ]
                    }
                ]
            }
            
            payload = {
                "msg_type": "interactive",
                "card": card
            }
            
            # 添加签名
            if self.secret:
                payload["sign"] = self._generate_signature(timestamp)
                payload["timestamp"] = str(timestamp)
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                self._increment_send()
                print(f"✅ 飞书通知已发送")
                return True
            else:
                self._increment_error()
                print(f"❌ 飞书通知失败：{result}")
                return False
                
        except Exception as e:
            self._increment_error()
            print(f"❌ 飞书通知异常：{e}")
            return False


class EmailNotifier(NotificationChannel):
    """邮件通知"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        recipients: List[str],
        use_tls: bool = True,
        enabled: bool = True
    ):
        """
        初始化邮件通知
        
        Args:
            smtp_server: SMTP 服务器地址
            smtp_port: SMTP 端口
            username: 用户名
            password: 密码/授权码
            recipients: 收件人列表
            use_tls: 是否使用 TLS
        """
        super().__init__("邮件通知", enabled)
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
        self.use_tls = use_tls
    
    async def send(self, message: AlertMessage) -> bool:
        """发送 HTML 格式邮件"""
        if not self.enabled:
            return False
        
        try:
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[摔倒检测] {message.title}"
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            
            # 确定告警级别颜色
            if message.alert_type == 'fall_confirmed':
                color = "#f44336"
                level = "紧急"
            elif message.alert_type == 'fall_suspected':
                color = "#ff9800"
                level = "警告"
            else:
                color = "#2196f3"
                level = "提示"
            
            time_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: {color}; color: white; padding: 20px; border-radius: 5px;">
                        <h1 style="margin: 0;">{message.title}</h1>
                    </div>
                    
                    <div style="padding: 20px; background-color: #f5f5f5; margin-top: 10px; border-radius: 5px;">
                        <p><strong>⏰ 时间:</strong> {time_str}</p>
                        <p><strong>📍 位置:</strong> {message.location or '未知'}</p>
                        <p><strong>📊 置信度:</strong> {message.confidence:.0%}</p>
                        <p><strong>🔴 级别:</strong> {level}</p>
                    </div>
                    
                    <div style="padding: 20px; margin-top: 10px; border-radius: 5px; background-color: #fff; border: 1px solid #ddd;">
                        <h3>📝 详细信息</h3>
                        <p>{message.content}</p>
                    </div>
                    
                    <div style="text-align: center; color: #999; margin-top: 20px; font-size: 12px;">
                        <p>摔倒检测系统自动发送</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
{message.title}

时间：{time_str}
位置：{message.location or '未知'}
置信度：{message.confidence:.0%}
级别：{level}

详细信息:
{message.content}

---
摔倒检测系统自动发送
            """
            
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # 发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.use_tls:
                server.starttls()
            
            server.login(self.username, self.password)
            server.sendmail(self.username, self.recipients, msg.as_string())
            server.quit()
            
            self._increment_send()
            print(f"✅ 邮件通知已发送到 {len(self.recipients)} 个收件人")
            return True
            
        except Exception as e:
            self._increment_error()
            print(f"❌ 邮件通知异常：{e}")
            return False


class SMSNotifier(NotificationChannel):
    """短信通知（腾讯云）"""
    
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        app_id: str,
        template_id: str,
        recipients: List[str],
        enabled: bool = True
    ):
        """
        初始化短信通知
        
        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            app_id: 短信应用 ID
            template_id: 短信模板 ID
            recipients: 收件人手机号列表
        """
        super().__init__("短信通知", enabled)
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.app_id = app_id
        self.template_id = template_id
        self.recipients = recipients
        self.endpoint = "sms.tencentcloudapi.com"
        self.version = "2021-01-11"
    
    def _sign(self, payload: str, timestamp: int, secret_key: str) -> str:
        """生成腾讯云签名"""
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        source = f"tc3-request\n{date}\nsms/\nhost\n"
        
        hashed_source = hmac.new(
            secret_key.encode("utf-8"),
            source.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(hashed_source).decode("utf-8")
    
    async def send(self, message: AlertMessage) -> bool:
        """发送短信（需要安装 tencentcloud-sdk-python）"""
        if not self.enabled:
            return False
        
        try:
            # 简化实现，实际使用建议安装官方 SDK
            # pip install tencentcloud-sdk-python
            
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.sms.v20210111 import sms_client, models
            
            cred = credential.Credential(self.secret_id, self.secret_key)
            
            httpProfile = HttpProfile()
            httpProfile.endpoint = self.endpoint
            
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            
            client = sms_client.SmsClient(cred, "", clientProfile)
            
            req = models.SendSmsRequest()
            
            # 构建参数
            time_str = message.timestamp.strftime("%H:%M")
            params = [
                f"时间:{time_str}",
                f"事件:{message.alert_type}",
                f"置信度:{message.confidence:.0%}"
            ]
            
            req.Params = json.dumps({
                "PhoneNumberSet": [f"+86{phone}" for phone in self.recipients],
                "SmsAppId": self.app_id,
                "SignName": "摔倒检测系统",
                "TemplateId": self.template_id,
                "TemplateParamSet": params
            })
            
            resp = client.SendSms(req)
            
            result = json.loads(resp.to_json_string())
            
            if result.get('SendStatusSet', [{}])[0].get('Code') == 'Ok':
                self._increment_send()
                print(f"✅ 短信通知已发送到 {len(self.recipients)} 个手机号")
                return True
            else:
                self._increment_error()
                print(f"❌ 短信通知失败：{result}")
                return False
                
        except ImportError:
            print("⚠️ 未安装腾讯云 SDK，请运行：pip install tencentcloud-sdk-python")
            return False
        except Exception as e:
            self._increment_error()
            print(f"❌ 短信通知异常：{e}")
            return False


class WebhookNotifier(NotificationChannel):
    """通用 Webhook 通知"""
    
    def __init__(self, url: str, method: str = "POST", headers: Dict = None, enabled: bool = True):
        """
        初始化 Webhook 通知
        
        Args:
            url: Webhook URL
            method: HTTP 方法
            headers: 自定义请求头
        """
        super().__init__("Webhook", enabled)
        self.url = url
        self.method = method
        self.headers = headers or {}
    
    async def send(self, message: AlertMessage) -> bool:
        """发送 JSON 格式数据到 Webhook"""
        if not self.enabled:
            return False
        
        try:
            payload = message.to_dict()
            
            response = requests.request(
                self.method,
                self.url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code < 300:
                self._increment_send()
                print(f"✅ Webhook 通知已发送到 {self.url}")
                return True
            else:
                self._increment_error()
                print(f"❌ Webhook 通知失败：{response.status_code}")
                return False
                
        except Exception as e:
            self._increment_error()
            print(f"❌ Webhook 通知异常：{e}")
            return False


class NotificationManager:
    """通知管理器 - 统一管理多个通知渠道"""
    
    def __init__(self):
        """初始化通知管理器"""
        self.channels: List[NotificationChannel] = []
    
    def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.channels.append(channel)
        print(f"✅ 添加通知渠道：{channel.name}")
    
    def remove_channel(self, channel_name: str):
        """移除通知渠道"""
        self.channels = [c for c in self.channels if c.name != channel_name]
        print(f"✅ 移除通知渠道：{channel_name}")
    
    async def notify(self, message: AlertMessage, channels: List[str] = None):
        """
        发送告警通知到指定渠道
        
        Args:
            message: 告警消息
            channels: 指定渠道名称列表（None 表示所有启用的渠道）
        """
        tasks = []
        
        for channel in self.channels:
            if not channel.enabled:
                continue
            
            if channels and channel.name not in channels:
                continue
            
            tasks.append(channel.send(message))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            print(f"📱 通知发送完成：{success_count}/{len(tasks)} 成功")
            return success_count
        
        return 0
    
    async def notify_all(self, message: AlertMessage):
        """发送到所有启用的渠道"""
        return await self.notify(message)
    
    async def notify_critical(self, message: AlertMessage):
        """
        发送紧急告警（仅高优先级渠道）
        
        只发送到：短信、电话等高优先级渠道
        """
        high_priority_channels = ["短信通知"]
        return await self.notify(message, channels=high_priority_channels)
    
    def get_stats(self) -> List[Dict]:
        """获取所有渠道的统计信息"""
        return [channel.get_stats() for channel in self.channels]
    
    def enable_channel(self, channel_name: str):
        """启用渠道"""
        for channel in self.channels:
            if channel.name == channel_name:
                channel.enabled = True
                print(f"✅ 已启用：{channel_name}")
    
    def disable_channel(self, channel_name: str):
        """禁用渠道"""
        for channel in self.channels:
            if channel.name == channel_name:
                channel.enabled = False
                print(f"✅ 已禁用：{channel_name}")


# 全局通知管理器实例
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器单例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
