"""
多摄像头管理器
支持同时管理多个摄像头源（USB/IP Camera/RTSP）
"""

import cv2
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import queue
import numpy as np


class CameraType(str, Enum):
    """摄像头类型"""
    USB = "usb"  # USB 摄像头
    RTSP = "rtsp"  # RTSP 流
    HTTP = "http"  # HTTP 流
    FILE = "file"  # 视频文件


@dataclass
class CameraConfig:
    """摄像头配置"""
    id: str
    name: str
    source: str  # 设备路径或 URL
    camera_type: CameraType
    enabled: bool = True
    width: int = 1280
    height: int = 720
    fps: int = 30
    location: str = ""  # 安装位置


@dataclass
class CameraStatus:
    """摄像头状态"""
    id: str
    is_connected: bool
    is_recording: bool
    last_frame_time: Optional[datetime]
    fps_current: float
    error_message: Optional[str] = None


class CameraStream:
    """单个摄像头流"""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame: Optional[np.ndarray] = None
        self.last_frame_time: Optional[datetime] = None
        self.fps_current = 0.0
        self.error_message: Optional[str] = None
        
        # 帧率计算
        self.frame_count = 0
        self.last_fps_calc_time = time.time()
    
    def connect(self) -> bool:
        """连接摄像头"""
        try:
            # 根据类型设置后端
            if self.config.camera_type == CameraType.RTSP:
                self.cap = cv2.VideoCapture(
                    self.config.source,
                    cv2.CAP_FFMPEG
                )
            else:
                self.cap = cv2.VideoCapture(self.config.source)
            
            if not self.cap.isOpened():
                self.error_message = f"无法打开摄像头：{self.config.source}"
                return False
            
            # 设置参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            self.is_running = True
            self.thread = threading.Thread(target=self._read_frames, daemon=True)
            self.thread.start()
            
            self.error_message = None
            return True
            
        except Exception as e:
            self.error_message = str(e)
            return False
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def _read_frames(self):
        """持续读取帧（后台线程）"""
        while self.is_running:
            if self.cap is None:
                time.sleep(0.1)
                continue
            
            ret, frame = self.cap.read()
            
            if not ret:
                self.error_message = "读取帧失败"
                time.sleep(0.1)
                continue
            
            # 更新最后一帧
            self.last_frame = frame
            self.last_frame_time = datetime.now()
            
            # 计算 FPS
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_calc_time >= 1.0:
                self.fps_current = self.frame_count / (current_time - self.last_fps_calc_time)
                self.frame_count = 0
                self.last_fps_calc_time = current_time
            
            # 放入队列（如果队列满则丢弃旧帧）
            try:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame, block=False)
            except:
                pass
            
            time.sleep(0.001)  # 避免过度占用 CPU
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """获取最新帧"""
        if self.last_frame is not None:
            return self.last_frame.copy()
        return None
    
    def get_status(self) -> CameraStatus:
        """获取摄像头状态"""
        return CameraStatus(
            id=self.config.id,
            is_connected=self.cap is not None and self.cap.isOpened(),
            is_recording=self.is_running,
            last_frame_time=self.last_frame_time,
            fps_current=self.fps_current,
            error_message=self.error_message
        )


class MultiCameraManager:
    """多摄像头管理器"""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.callbacks: Dict[str, List[Callable]] = {}  # 帧回调
        self.is_running = False
    
    def add_camera(self, config: CameraConfig) -> bool:
        """添加摄像头"""
        if config.id in self.cameras:
            return False
        
        stream = CameraStream(config)
        self.cameras[config.id] = stream
        return True
    
    def remove_camera(self, camera_id: str):
        """移除摄像头"""
        if camera_id in self.cameras:
            self.cameras[camera_id].disconnect()
            del self.cameras[camera_id]
    
    def start_all(self):
        """启动所有摄像头"""
        self.is_running = True
        
        for camera in self.cameras.values():
            if camera.config.enabled:
                camera.connect()
    
    def stop_all(self):
        """停止所有摄像头"""
        self.is_running = False
        
        for camera in self.cameras.values():
            camera.disconnect()
    
    def get_camera_status(self, camera_id: str) -> Optional[CameraStatus]:
        """获取摄像头状态"""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_status()
        return None
    
    def get_all_statuses(self) -> Dict[str, CameraStatus]:
        """获取所有摄像头状态"""
        return {
            cam_id: cam.get_status()
            for cam_id, cam in self.cameras.items()
        }
    
    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """获取指定摄像头的最新帧"""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_latest_frame()
        return None
    
    def get_all_frames(self) -> Dict[str, Optional[np.ndarray]]:
        """获取所有摄像头的最新帧"""
        return {
            cam_id: cam.get_latest_frame()
            for cam_id, cam in self.cameras.items()
        }
    
    def register_callback(self, camera_id: str, callback: Callable[[np.ndarray], None]):
        """注册帧回调函数"""
        if camera_id not in self.callbacks:
            self.callbacks[camera_id] = []
        self.callbacks[camera_id].append(callback)
    
    def enable_camera(self, camera_id: str, enabled: bool):
        """启用/禁用摄像头"""
        if camera_id in self.cameras:
            self.cameras[camera_id].config.enabled = enabled
            
            if enabled and self.is_running:
                self.cameras[camera_id].connect()
            elif not enabled:
                self.cameras[camera_id].disconnect()
    
    def get_active_cameras(self) -> List[str]:
        """获取活跃摄像头 ID 列表"""
        return [
            cam_id for cam_id, cam in self.cameras.items()
            if cam.config.enabled and cam.get_status().is_connected
        ]
    
    def get_camera_config(self, camera_id: str) -> Optional[CameraConfig]:
        """获取摄像头配置"""
        if camera_id in self.cameras:
            return self.cameras[camera_id].config
        return None
    
    def update_camera_config(self, camera_id: str, **kwargs):
        """更新摄像头配置"""
        if camera_id in self.cameras:
            config = self.cameras[camera_id].config
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)


# 全局实例
_camera_manager: Optional[MultiCameraManager] = None


def get_camera_manager() -> MultiCameraManager:
    """获取摄像头管理器单例"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = MultiCameraManager()
    return _camera_manager


def reset_camera_manager():
    """重置摄像头管理器（用于测试）"""
    global _camera_manager
    if _camera_manager:
        _camera_manager.stop_all()
    _camera_manager = None
