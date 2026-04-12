"""
通知器模块
支持邮件、企业微信等多种通知方式
"""

import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..utils.config import get_config
from ..utils.error_handler import handle_errors
from .alerter import Alert, AlertLevel


class EmailNotifier:
    """邮件通知器"""
    
    def __init__(self):
        self.config = get_config()
        self.smtp_server = self.config.notifications.email.smtp_server
        self.smtp_port = self.config.notifications.email.smtp_port
        self.username = self.config.notifications.email.username
        self.password = self.config.notifications.email.password
        self.from_addr = self.config.notifications.email.from_addr
        self.to_addrs = self.config.notifications.email.to_addrs
    
    @handle_errors(default_return=None)
    def send(self, subject: str, content: str, html: bool = False):
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
            html: 是否为 HTML 格式
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        
        # 添加内容
        if html:
            msg.attach(MIMEText(content, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        # 发送邮件
        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        server.login(self.username, self.password)
        server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
        server.quit()
        
        print(f"✅ Email sent: {subject}")
    
    def send_alert(self, alert: Alert):
        """发送告警邮件"""
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        
        subject = f"[GuardianFall] {emoji.get(alert.level.value, '📢')} {alert.level.value.upper()}: {alert.message}"
        
        content = f"""
<h2>🛡️ GuardianFall 告警通知</h2>

<table style="border-collapse: collapse; width: 100%;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警级别</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.level.value.upper()}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警消息</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.message}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>告警来源</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.source}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>发生时间</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
    </tr>
</table>

<h3>详细信息</h3>
<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">
{json.dumps(alert.data, indent=2, ensure_ascii=False)}
</pre>

<hr>
<p style="color: #666; font-size: 12px;">此邮件由 GuardianFall 系统自动发送，请勿回复。</p>
        """
        
        self.send(subject, content, html=True)


class WeChatNotifier:
    """企业微信通知器"""
    
    def __init__(self):
        self.config = get_config()
        self.webhook_url = self.config.notifications.wechat.webhook_url
        self.agent_id = self.config.notifications.wechat.agent_id if hasattr(self.config.notifications.wechat, 'agent_id') else None
        self.corp_id = self.config.notifications.wechat.corp_id if hasattr(self.config.notifications.wechat, 'corp_id') else None
        self.corp_secret = self.config.notifications.wechat.corp_secret if hasattr(self.config.notifications.wechat, 'corp_secret') else None
        self.access_token = None
        self.token_expires_at = None
    
    def _get_access_token(self) -> Optional[str]:
        """获取企业微信访问 Token"""
        if not self.corp_id or not self.corp_secret:
            return None
        
        # 如果 Token 未过期，直接返回
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get("errcode") == 0:
                self.access_token = data["access_token"]
                self.token_expires_at = datetime.now().timestamp() + data["expires_in"] - 300
                return self.access_token
        except Exception as e:
            print(f"Failed to get WeChat token: {e}")
        
        return None
    
    @handle_errors(default_return=None)
    def send_text(self, content: str, mentioned_list: List[str] = None):
        """
        发送文本消息
        
        Args:
            content: 消息内容
            mentioned_list: 需要@的用户列表
        """
        # 尝试使用 Webhook 方式
        if self.webhook_url:
            return self._send_via_webhook(content, mentioned_list)
        
        # 否则使用 API 方式
        access_token = self._get_access_token()
        if not access_token:
            print("⚠️ WeChat notifier not configured properly")
            return
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        
        data = {
            "touser": "@all",
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or ["@all"]
            },
            "safe": 0
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get("errcode") == 0:
            print(f"✅ WeChat message sent")
        else:
            print(f"⚠️ WeChat send failed: {result}")
    
    def _send_via_webhook(self, content: str, mentioned_list: List[str] = None):
        """通过 Webhook 发送消息（机器人方式）"""
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content,
                    "mentioned_list": mentioned_list or ["@all"]
                }
            }
            
            response = requests.post(self.webhook_url, json=data, timeout=10)
            result = response.json()
            
            if result.get("errcode") == 0:
                print(f"✅ WeChat webhook message sent")
            else:
                print(f"⚠️ WeChat webhook failed: {result}")
        except Exception as e:
            print(f"WeChat webhook error: {e}")
    
    def send_alert(self, alert: Alert):
        """发送告警消息到企业微信"""
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        
        color_map = {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "emphasis"
        }
        
        content = f"""{emoji.get(alert.level.value, '📢')} *GuardianFall 告警通知*

>告警级别：{alert.level.value.upper()}
>告警消息：{alert.message}
>告警来源：{alert.source}
>发生时间：{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

详细信息：
\`\`\`
{json.dumps(alert.data, indent=2, ensure_ascii=False)}
\`\`\`
        """
        
        # 严重告警@所有人
        mentioned = ["@all"] if alert.level == AlertLevel.CRITICAL else []
        
        self.send_text(content, mentioned)


# 全局通知器实例
_email_notifier = None
_wechat_notifier = None


def get_email_notifier() -> Optional[EmailNotifier]:
    """获取邮件通知器实例"""
    global _email_notifier
    if _email_notifier is None:
        try:
            _email_notifier = EmailNotifier()
        except Exception as e:
            print(f"⚠️ Email notifier init failed: {e}")
            return None
    return _email_notifier


def get_wechat_notifier() -> Optional[WeChatNotifier]:
    """获取企业微信通知器实例"""
    global _wechat_notifier
    if _wechat_notifier is None:
        try:
            _wechat_notifier = WeChatNotifier()
        except Exception as e:
            print(f"⚠️ WeChat notifier init failed: {e}")
            return None
    return _wechat_notifier
