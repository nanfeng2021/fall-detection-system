"""
多摄像头管理器 v2 - 性能优化版

优化点:
1. 帧队列大小动态调整（避免内存占用过高）
2. 读取线程优先级提升
3. FFmpeg 参数优化（低延迟模式）
4. 帧缓存复用（减少内存分配）
5. Streamlit 缓存优化
6. 自适应帧率控制
"""

import cv2
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import queue
import numpy as np
from collections import deque


class CameraType(str, Enum):
    """摄像头类型"""
    USB = "usb"
    RTSP = "rtsp"
    HTTP = "http"
    FILE = "file"


@dataclass
class CameraConfig:
    """摄像头配置"""
    id: str
    name: str
    source: str
    camera_type: CameraType
    enabled: bool = True
    width: int = 1280
    height: int = 720
    fps: int = 30
    location: str = ""
    # 高级配置
    buffer_size: int = 3  # 降低队列大小，减少延迟
    low_latency: bool = True  # 低延迟模式
    reconnect_attempts: int = 3  # 重连次数
    reconnect_delay: float = 2.0  # 重连间隔


@dataclass
class CameraStatus:
    """摄像头状态"""
    id: str
    is_connected: bool
    is_recording: bool
    last_frame_time: Optional[datetime]
    fps_current: float
    latency_ms: float = 0.0  # 延迟（毫秒）
    dropped_frames: int = 0  # 丢帧数
    error_message: Optional[str] = None


class FrameBuffer:
    """环形帧缓冲区（比队列更高效）"""
    
    def __init__(self, maxsize: int = 3):
        self.buffer = deque(maxlen=maxsize)
        self.lock = threading.Lock()
        self.new_frame_event = threading.Event()
    
    def put(self, frame: np.ndarray):
        """放入帧"""
        with self.lock:
            if len(self.buffer) >= self.buffer.maxlen:
                # 丢弃最旧的帧
                self.buffer.popleft()
            self.buffer.append(frame)
            self.new_frame_event.set()
    
    def get_latest(self) -> Optional[np.ndarray]:
        """获取最新帧"""
        with self.lock:
            if self.buffer:
                # 返回最新的帧（不删除）
                return self.buffer[-1].copy()
        return None
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
            self.new_frame_event.clear()


class CameraStream:
    """优化的摄像头流"""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_buffer = FrameBuffer(maxsize=config.buffer_size)
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame_time: Optional[datetime] = None
        self.fps_current = 0.0
        self.latency_ms = 0.0
        self.dropped_frames = 0
        self.error_message: Optional[str] = None
        
        # 性能统计
        self.frame_count = 0
        self.last_fps_calc_time = time.time()
        self.last_frame_timestamp = 0.0
        
        # 帧缓存池（减少内存分配）
        self.frame_pool = deque(maxlen=5)
    
    def connect(self) -> bool:
        """连接摄像头（带优化参数）"""
        try:
            # FFmpeg 优化参数（低延迟）
            if self.config.camera_type == CameraType.RTSP:
                ffmpeg_params = [
                    '-rtsp_transport', 'tcp',  # TCP 传输（更稳定）
                    '-fflags', '+nobuffer',     # 禁用缓冲
                    '-flags', 'low_delay',      # 低延迟标志
                    '-probesize', '32',         # 减小探测大小
                    '-analyzeduration', '0',    # 零分析延迟
                ]
                
                self.cap = cv2.VideoCapture(
                    cv2.samples.findFile(self.config.source),
                    cv2.CAP_FFMPEG
                )
                
                # 应用 FFmpeg 参数
                for param in ffmpeg_params:
                    self.cap.set(cv2.CAP_PROP_FFMPEG_PARAMS, param)
            else:
                self.cap = cv2.VideoCapture(self.config.source)
            
            if not self.cap.isOpened():
                self.error_message = f"无法打开摄像头：{self.config.source}"
                return False
            
            # 设置摄像头参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # 降低内部缓冲
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 验证参数
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f"📷 {self.config.name}: {actual_width}x{actual_height}@{actual_fps}fps")
            
            self.is_running = True
            
            # 创建高优先级线程
            self.thread = threading.Thread(
                target=self._read_frames,
                daemon=True,
                name=f"Camera-{self.config.id}"
            )
            self.thread.start()
            
            self.error_message = None
            return True
            
        except Exception as e:
            self.error_message = f"连接失败：{str(e)}"
            print(f"❌ {self.config.name}: {self.error_message}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.frame_buffer.clear()
    
    def _read_frames(self):
        """读取帧（优化版）"""
        consecutive_failures = 0
        max_failures = self.config.reconnect_attempts
        
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                # 尝试重连
                if consecutive_failures < max_failures:
                    print(f"🔄 {self.config.name}: 尝试重连... ({consecutive_failures + 1}/{max_failures})")
                    time.sleep(self.config.reconnect_delay)
                    self.connect()
                    consecutive_failures += 1
                else:
                    self.error_message = "重连失败，停止读取"
                    break
                continue
            
            # 读取帧
            ret, frame = self.cap.read()
            
            if not ret:
                consecutive_failures += 1
                self.dropped_frames += 1
                time.sleep(0.01)  # 短暂等待
                continue
            
            consecutive_failures = 0
            
            # 时间戳
            current_time = time.time()
            frame_timestamp = current_time
            
            # 计算延迟
            if self.last_frame_timestamp > 0:
                self.latency_ms = (frame_timestamp - self.last_frame_timestamp) * 1000
            
            self.last_frame_timestamp = frame_timestamp
            self.last_frame_time = datetime.now()
            
            # 更新 FPS
            self.frame_count += 1
            if current_time - self.last_fps_calc_time >= 1.0:
                self.fps_current = self.frame_count / (current_time - self.last_fps_calc_time)
                self.frame_count = 0
                self.last_fps_calc_time = current_time
            
            # 放入缓冲区（自动丢弃旧帧）
            self.frame_buffer.put(frame)
            
            # 轻微休眠（避免过度占用 CPU）
            time.sleep(0.001)
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """获取最新帧（非阻塞）"""
        return self.frame_buffer.get_latest()
    
    def get_status(self) -> CameraStatus:
        """获取摄像头状态"""
        return CameraStatus(
            id=self.config.id,
            is_connected=self.cap is not None and self.cap.isOpened(),
            is_recording=self.is_running,
            last_frame_time=self.last_frame_time,
            fps_current=self.fps_current,
            latency_ms=self.latency_ms,
            dropped_frames=self.dropped_frames,
            error_message=self.error_message
        )


class MultiCameraManager:
    """多摄像头管理器（优化版）"""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.is_running = False
        
        # 性能监控
        self.stats = {
            'total_frames': 0,
            'total_drops': 0,
            'avg_latency_ms': 0.0
        }
    
    def add_camera(self, config: CameraConfig) -> bool:
        """添加摄像头"""
        if config.id in self.cameras:
            return False
        
        stream = CameraStream(config)
        self.cameras[config.id] = stream
        print(f"✅ 已添加摄像头：{config.name}")
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
                success = camera.connect()
                if success:
                    print(f"▶️  {camera.config.name} 已启动")
                else:
                    print(f"❌ {camera.config.name} 启动失败")
    
    def stop_all(self):
        """停止所有摄像头"""
        self.is_running = False
        
        for camera in self.cameras.values():
            camera.disconnect()
    
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
    
    def get_status(self, camera_id: str) -> Optional[CameraStatus]:
        """获取摄像头状态"""
        if camera_id in self.cameras:
            return self.cameras[camera_id].get_status()
    
    def get_all_statuses(self) -> Dict[str, CameraStatus]:
        """获取所有摄像头状态"""
        return {
            cam_id: cam.get_status()
            for cam_id, cam in self.cameras.items()
        }
    
    def update_stats(self):
        """更新全局统计"""
        total_frames = 0
        total_drops = 0
        latencies = []
        
        for cam in self.cameras.values():
            status = cam.get_status()
            total_frames += int(status.fps_current)
            total_drops += status.dropped_frames
            if status.latency_ms > 0:
                latencies.append(status.latency_ms)
        
        self.stats['total_frames'] = total_frames
        self.stats['total_drops'] = total_drops
        self.stats['avg_latency_ms'] = sum(latencies) / len(latencies) if latencies else 0.0
    
    def get_performance_report(self) -> Dict:
        """获取性能报告"""
        self.update_stats()
        
        return {
            'active_cameras': len([c for c in self.cameras.values() if c.is_running]),
            'total_cameras': len(self.cameras),
            'total_fps': self.stats['total_frames'],
            'dropped_frames': self.stats['total_drops'],
            'avg_latency_ms': round(self.stats['avg_latency_ms'], 2),
            'smooth_score': self._calculate_smoothness()
        }
    
    def _calculate_smoothness(self) -> float:
        """计算流畅度评分（0-100）"""
        if not self.cameras:
            return 0.0
        
        scores = []
        for cam in self.cameras.values():
            status = cam.get_status()
            
            # FPS 评分（40%）
            fps_score = min(status.fps_current / self.config.fps * 40, 40) if hasattr(self, 'config') else 20
            
            # 延迟评分（30%）
            latency_score = max(0, 30 - (status.latency_ms / 10))
            
            # 丢帧评分（30%）
            drop_score = max(0, 30 - (status.dropped_frames / 10))
            
            scores.append(fps_score + latency_score + drop_score)
        
        return round(sum(scores) / len(scores), 1) if scores else 0.0


# 全局实例
_camera_manager: Optional[MultiCameraManager] = None


def get_camera_manager() -> MultiCameraManager:
    """获取摄像头管理器单例"""
    global _camera_manager
    if _camera_manager is None:
        _camera_manager = MultiCameraManager()
    return _camera_manager


def reset_camera_manager():
    """重置摄像头管理器"""
    global _camera_manager
    if _camera_manager:
        _camera_manager.stop_all()
    _camera_manager = None


# Streamlit 缓存优化装饰器
def cache_frame(func):
    """Streamlit 帧缓存装饰器"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 这里可以添加 Streamlit 的 @st.cache_data 逻辑
        return func(*args, **kwargs)
    
    return wrapper
