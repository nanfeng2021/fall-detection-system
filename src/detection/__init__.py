"""
检测模块
包含摔倒检测核心算法和多摄像头支持
"""

from .detector import (
    FallDetectionSystem,
    SystemAlert,
    FrameResult,
    DetectionResult,
    FallState
)

from .multi_camera_detector import (
    CameraDetectorConfig,
    DetectionStats,
    CameraFallDetector,
    MultiCameraFallDetector,
    get_multi_camera_detector,
    reset_multi_camera_detector
)

__all__ = [
    'FallDetectionSystem',
    'SystemAlert',
    'FrameResult',
    'DetectionResult',
    'FallState',
    'CameraDetectorConfig',
    'DetectionStats',
    'CameraFallDetector',
    'MultiCameraFallDetector',
    'get_multi_camera_detector',
    'reset_multi_camera_detector'
]
