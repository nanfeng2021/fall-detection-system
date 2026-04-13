"""
多摄像头摔倒检测器
为每个摄像头提供独立的检测实例，统一告警管理
"""

import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import queue
import numpy as np

from .detector import FallDetectionSystem, SystemAlert, FrameResult
from ..camera.multi_camera_manager import MultiCameraManager, get_camera_manager


@dataclass
class CameraDetectorConfig:
    """摄像头检测器配置"""
    camera_id: str
    enabled: bool = True
    detection_interval_ms: int = 100  # 检测间隔（毫秒）
    alert_callback: Optional[Callable] = None


@dataclass
class DetectionStats:
    """检测统计信息"""
    camera_id: str
    total_frames_processed: int = 0
    total_detections: int = 0
    total_alerts: int = 0
    last_detection_time: Optional[datetime] = None
    fps_processing: float = 0.0
    alerts_last_hour: int = 0


class CameraFallDetector:
    """单个摄像头的摔倒检测器"""
    
    def __init__(self, config: CameraDetectorConfig, detection_system: FallDetectionSystem):
        self.config = config
        self.detection_system = detection_system
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_queue = queue.Queue(maxsize=5)
        
        self.stats = DetectionStats(camera_id=config.camera_id)
        self.last_alert_time: Optional[datetime] = None
        
        # 防抖动（避免重复告警）
        self.alert_cooldown_seconds = 30
        self.current_state = "normal"  # normal, falling, fallen
    
    def start(self):
        """启动检测线程"""
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止检测"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
    
    def add_frame(self, frame: np.ndarray):
        """添加帧到检测队列"""
        try:
            if not self.frame_queue.full():
                self.frame_queue.put(frame, block=False)
        except:
            pass
    
    def _detection_loop(self):
        """检测循环（后台线程）"""
        last_process_time = time.time()
        interval_seconds = self.config.detection_interval_ms / 1000.0
        
        while self.is_running:
            current_time = time.time()
            
            # 控制处理频率
            if current_time - last_process_time < interval_seconds:
                time.sleep(0.01)
                continue
            
            # 获取帧
            try:
                frame = self.frame_queue.get(block=False)
            except queue.Empty:
                continue
            
            # 处理帧
            try:
                result = self.detection_system.process_frame(frame)
                
                # 更新统计
                self.stats.total_frames_processed += 1
                self.stats.last_detection_time = datetime.now()
                
                # 处理告警
                if result.has_fall:
                    self.stats.total_detections += 1
                    
                    # 检查是否在冷却期
                    if self._should_trigger_alert():
                        self._handle_alert(result)
                
                last_process_time = current_time
                
            except Exception as e:
                print(f"❌ {self.config.camera_id} 检测失败：{e}")
    
    def _should_trigger_alert(self) -> bool:
        """判断是否应该触发告警（防抖动）"""
        if self.last_alert_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_alert_time).total_seconds()
        return elapsed >= self.alert_cooldown_seconds
    
    def _handle_alert(self, result: FrameResult):
        """处理告警"""
        self.last_alert_time = datetime.now()
        self.stats.total_alerts += 1
        self.stats.alerts_last_hour += 1
        
        # 调用回调
        if self.config.alert_callback:
            for alert in result.alerts:
                alert.metadata['camera_id'] = self.config.camera_id
                self.config.alert_callback(alert)
    
    def get_stats(self) -> DetectionStats:
        """获取统计信息"""
        # 计算处理 FPS
        if self.stats.last_detection_time:
            # 简化计算，实际应该更精确
            self.stats.fps_processing = 1000.0 / self.config.detection_interval_ms
        
        return self.stats


class MultiCameraFallDetector:
    """多摄像头摔倒检测管理器"""
    
    def __init__(self, camera_manager: Optional[MultiCameraManager] = None):
        self.camera_manager = camera_manager or get_camera_manager()
        self.detectors: Dict[str, CameraFallDetector] = {}
        self.global_alert_callbacks: List[Callable] = []
        self.is_running = False
    
    def add_detector(self, config: CameraDetectorConfig, detection_system: FallDetectionSystem):
        """添加摄像头检测器"""
        detector = CameraFallDetector(config, detection_system)
        self.detectors[config.camera_id] = detector
        
        # 注册帧源
        def on_new_frame(frame):
            if detector.is_running:
                detector.add_frame(frame)
        
        self.camera_manager.register_callback(config.camera_id, on_new_frame)
    
    def start_all(self):
        """启动所有检测器"""
        self.is_running = True
        
        for detector in self.detectors.values():
            if detector.config.enabled:
                detector.start()
                print(f"✅ 已启动 {detector.config.camera_id} 的检测")
    
    def stop_all(self):
        """停止所有检测器"""
        self.is_running = False
        
        for detector in self.detectors.values():
            detector.stop()
    
    def register_global_alert_callback(self, callback: Callable[[SystemAlert], None]):
        """注册全局告警回调"""
        self.global_alert_callbacks.append(callback)
        
        # 同时为每个检测器设置回调
        for detector in self.detectors.values():
            original_callback = detector.config.alert_callback
            
            def combined_callback(alert: SystemAlert):
                if original_callback:
                    original_callback(alert)
                callback(alert)
            
            detector.config.alert_callback = combined_callback
    
    def get_detector_stats(self, camera_id: str) -> Optional[DetectionStats]:
        """获取指定摄像头的检测统计"""
        if camera_id in self.detectors:
            return self.detectors[camera_id].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, DetectionStats]:
        """获取所有摄像头的统计"""
        return {
            cam_id: detector.get_stats()
            for cam_id, detector in self.detectors.items()
        }
    
    def enable_detector(self, camera_id: str, enabled: bool):
        """启用/禁用指定摄像头的检测"""
        if camera_id in self.detectors:
            detector = self.detectors[camera_id]
            detector.config.enabled = enabled
            
            if enabled and self.is_running:
                detector.start()
            elif not enabled:
                detector.stop()
    
    def get_active_detectors(self) -> List[str]:
        """获取活跃的检测器 ID 列表"""
        return [
            cam_id for cam_id, detector in self.detectors.items()
            if detector.config.enabled and detector.is_running
        ]
    
    def get_summary(self) -> Dict:
        """获取检测摘要"""
        all_stats = self.get_all_stats()
        
        total_frames = sum(s.total_frames_processed for s in all_stats.values())
        total_detections = sum(s.total_detections for s in all_stats.values())
        total_alerts = sum(s.total_alerts for s in all_stats.values())
        
        return {
            'total_cameras': len(self.detectors),
            'active_cameras': len(self.get_active_detectors()),
            'total_frames_processed': total_frames,
            'total_detections': total_detections,
            'total_alerts': total_alerts,
            'cameras_with_alerts': sum(1 for s in all_stats.values() if s.total_alerts > 0)
        }


# 全局实例
_multi_camera_detector: Optional[MultiCameraFallDetector] = None


def get_multi_camera_detector() -> MultiCameraFallDetector:
    """获取多摄像头检测器单例"""
    global _multi_camera_detector
    if _multi_camera_detector is None:
        _multi_camera_detector = MultiCameraFallDetector()
    return _multi_camera_detector


def reset_multi_camera_detector():
    """重置多摄像头检测器（用于测试）"""
    global _multi_camera_detector
    if _multi_camera_detector:
        _multi_camera_detector.stop_all()
    _multi_camera_detector = None
