"""
Fall Detection System - Harness Engineering Package

室内人体摔倒实时预警系统
支持多摄像头监控、智能检测、多渠道告警
"""

__version__ = "1.6.0"
__author__ = "Nanfeng"
__email__ = "nanfeng@example.com"

from .core.detector import FallDetectionSystem
from .services.auth_service import AuthService
from .services.detection_service import DetectionService
from .cameras.manager import CameraManager

__all__ = [
    "FallDetectionSystem",
    "AuthService",
    "DetectionService",
    "CameraManager",
]
