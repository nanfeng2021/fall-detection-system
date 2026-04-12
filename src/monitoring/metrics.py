"""
Prometheus 指标采集器
采集系统性能、检测统计等关键指标
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, start_http_server
import time
import threading
from typing import Dict, Any
from pathlib import Path

from ..utils.config import get_config


config = get_config()


class MetricsCollector:
    """指标采集器"""
    
    def __init__(self):
        # 系统性能指标
        self.fps_gauge = Gauge('fall_detection_fps', 'Current processing FPS')
        self.processing_time = Histogram(
            'fall_detection_processing_time_seconds',
            'Time spent processing frames',
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)
        )
        self.memory_usage = Gauge('fall_detection_memory_bytes', 'Memory usage in bytes')
        self.cpu_usage = Gauge('fall_detection_cpu_percent', 'CPU usage percentage')
        
        # 检测统计指标
        self.frames_processed = Counter('fall_detection_frames_total', 'Total frames processed')
        self.detections_total = Counter('fall_detection_detections_total', 'Total detections', ['type'])
        self.alerts_total = Counter('fall_detection_alerts_total', 'Total alerts triggered', ['level'])
        
        # 状态指标
        self.system_status = Gauge('fall_detection_system_status', 'System status (1=running, 0=stopped)')
        self.camera_status = Gauge('fall_detection_camera_status', 'Camera status (1=connected, 0=disconnected)')
        self.last_detection_time = Gauge('fall_detection_last_detection_timestamp', 'Timestamp of last detection')
        
        # 用户相关指标
        self.active_users = Gauge('fall_detection_active_users', 'Number of active users')
        self.login_attempts = Counter('fall_detection_login_attempts_total', 'Total login attempts', ['result'])
        
        # 启动 Prometheus 指标服务器
        self._start_metrics_server()
        
        # 启动系统状态监控线程
        self._start_monitoring_thread()
    
    def _start_metrics_server(self):
        """启动 Prometheus 指标 HTTP 服务器"""
        port = config.monitoring.metrics_port if hasattr(config, 'monitoring') else 9090
        try:
            start_http_server(port)
            print(f"✅ Prometheus metrics server started on port {port}")
        except Exception as e:
            print(f"⚠️ Failed to start metrics server: {e}")
    
    def _start_monitoring_thread(self):
        """启动后台监控线程"""
        def monitor_loop():
            while True:
                try:
                    # 这里可以添加系统资源监控逻辑
                    # 例如：使用 psutil 获取 CPU/内存使用率
                    time.sleep(5)  # 每 5 秒更新一次
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def update_fps(self, fps: float):
        """更新 FPS 指标"""
        self.fps_gauge.set(fps)
    
    def observe_processing_time(self, duration: float):
        """记录处理时间"""
        self.processing_time.observe(duration)
    
    def update_memory_usage(self, bytes_value: int):
        """更新内存使用量"""
        self.memory_usage.set(bytes_value)
    
    def update_cpu_usage(self, percent: float):
        """更新 CPU 使用率"""
        self.cpu_usage.set(percent)
    
    def increment_frames_processed(self):
        """增加已处理帧数"""
        self.frames_processed.inc()
    
    def increment_detection(self, detection_type: str = "person"):
        """增加检测计数"""
        self.detections_total.labels(type=detection_type).inc()
    
    def increment_alert(self, level: str = "info"):
        """增加告警计数"""
        self.alerts_total.labels(level=level).inc()
    
    def set_system_status(self, running: bool):
        """设置系统状态"""
        self.system_status.set(1 if running else 0)
    
    def set_camera_status(self, connected: bool):
        """设置摄像头状态"""
        self.camera_status.set(1 if connected else 0)
    
    def update_last_detection_time(self, timestamp: float = None):
        """更新最后检测时间"""
        if timestamp is None:
            timestamp = time.time()
        self.last_detection_time.set(timestamp)
    
    def update_active_users(self, count: int):
        """更新活跃用户数"""
        self.active_users.set(count)
    
    def increment_login_attempt(self, success: bool):
        """记录登录尝试"""
        result = "success" if success else "failure"
        self.login_attempts.labels(result=result).inc()
    
    def record_fall_event(self):
        """记录摔倒事件"""
        self.increment_detection("fall")
        self.increment_alert("critical")
        self.update_last_detection_time()


# 全局单例
_metrics_collector = None


def get_metrics() -> MetricsCollector:
    """获取全局指标采集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
