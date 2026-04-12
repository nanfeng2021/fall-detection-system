"""
告警管理器
管理告警级别、触发条件、告警历史等
"""

from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from pathlib import Path

from ..utils.config import get_config
from ..utils.error_handler import handle_errors


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


class Alert:
    """告警对象"""
    
    def __init__(
        self,
        level: AlertLevel,
        message: str,
        source: str = "system",
        data: Optional[Dict[str, Any]] = None
    ):
        self.id = datetime.now().timestamp()
        self.level = level
        self.message = message
        self.source = source
        self.data = data or {}
        self.timestamp = datetime.now()
        self.acknowledged = False
        self.acknowledged_by = None
        self.acknowledged_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }
    
    def acknowledge(self, user: str):
        """确认告警"""
        self.acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = datetime.now()


class Alerter:
    """告警管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.alerts_file = Path(__file__).parent.parent.parent / "data" / "alerts.json"
        self.alert_history: List[Alert] = []
        self.active_alerts: Dict[float, Alert] = {}
        
        # 告警回调函数列表
        self.callbacks = []
        
        # 加载历史告警
        self._load_alerts()
    
    def _load_alerts(self):
        """加载历史告警"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for alert_data in data.get("alerts", [])[-100:]:  # 只保留最近 100 条
                        alert = Alert(
                            level=AlertLevel(alert_data["level"]),
                            message=alert_data["message"],
                            source=alert_data.get("source", "system"),
                            data=alert_data.get("data", {})
                        )
                        alert.timestamp = datetime.fromisoformat(alert_data["timestamp"])
                        if alert_data.get("acknowledged"):
                            alert.acknowledge(alert_data.get("acknowledged_by", "unknown"))
                        self.alert_history.append(alert)
            except Exception as e:
                print(f"Failed to load alerts: {e}")
    
    def _save_alerts(self):
        """保存告警记录"""
        try:
            self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "alerts": [alert.to_dict() for alert in self.alert_history[-1000:]],
                "active": [alert.to_dict() for alert in self.active_alerts.values()]
            }
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save alerts: {e}")
    
    def add_callback(self, callback):
        """添加告警回调函数"""
        self.callbacks.append(callback)
    
    @handle_errors(default_return=None)
    def trigger(
        self,
        level: AlertLevel,
        message: str,
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
        notify: bool = True
    ):
        """
        触发告警
        
        Args:
            level: 告警级别
            message: 告警消息
            source: 告警来源
            data: 附加数据
            notify: 是否发送通知
        """
        alert = Alert(level=level, message=message, source=source, data=data)
        
        # 添加到活动告警
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)
        
        # 保存到文件
        self._save_alerts()
        
        # 调用回调函数
        if notify:
            for callback in self.callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Alert callback error: {e}")
        
        # 打印告警信息
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}
        print(f"{emoji.get(level.value, '📢')} [{level.value.upper()}] {message}")
        
        return alert
    
    def acknowledge(self, alert_id: float, user: str) -> bool:
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledge(user)
            del self.active_alerts[alert_id]
            self._save_alerts()
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取所有活动告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(
        self,
        limit: int = 50,
        level: Optional[AlertLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Alert]:
        """获取告警历史"""
        filtered = self.alert_history
        
        if level:
            filtered = [a for a in filtered if a.level == level]
        
        if start_time:
            filtered = [a for a in filtered if a.timestamp >= start_time]
        
        if end_time:
            filtered = [a for a in filtered if a.timestamp <= end_time]
        
        return filtered[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        now = datetime.now()
        last_24h = now.timestamp() - 86400
        
        stats = {
            "total": len(self.alert_history),
            "active": len(self.active_alerts),
            "last_24h": 0,
            "by_level": {level.value: 0 for level in AlertLevel}
        }
        
        for alert in self.alert_history:
            stats["by_level"][alert.level.value] += 1
            if alert.timestamp.timestamp() > last_24h:
                stats["last_24h"] += 1
        
        return stats


# 全局单例
_alerter = None


def get_alerter() -> Alerter:
    """获取全局告警管理器实例"""
    global _alerter
    if _alerter is None:
        _alerter = Alerter()
    return _alerter
