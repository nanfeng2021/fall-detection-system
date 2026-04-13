"""
摄像头模块
支持多摄像头管理和视频流处理
"""

from .multi_camera_manager import (
    CameraType,
    CameraConfig,
    CameraStatus,
    CameraStream,
    MultiCameraManager,
    get_camera_manager,
    reset_camera_manager
)

__all__ = [
    'CameraType',
    'CameraConfig',
    'CameraStatus',
    'CameraStream',
    'MultiCameraManager',
    'get_camera_manager',
    'reset_camera_manager'
]
