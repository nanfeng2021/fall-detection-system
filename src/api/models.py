#!/usr/bin/env python3
"""
API 数据模型
使用Pydantic定义请求和响应模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertLevel(str, Enum):
    """报警级别"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class DetectionState(str, Enum):
    """检测状态"""
    NORMAL = "normal"
    SUSPECTED = "suspected"
    CONFIRMED = "confirmed"
    RECOVERING = "recovering"


class SystemStatus(BaseModel):
    """系统状态"""
    is_running: bool = Field(..., description="是否正在运行")
    current_frame: int = Field(..., description="当前帧ID")
    fps: float = Field(..., description="当前FPS")
    uptime_seconds: float = Field(..., description="运行时间（秒）")
    active_trackers: int = Field(..., description="活跃追踪器数量")
    total_alerts: int = Field(..., description="总报警数")
    memory_usage_mb: Optional[float] = Field(None, description="内存使用（MB）")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU使用率")


class FrameResult(BaseModel):
    """帧处理结果"""
    frame_id: int = Field(..., description="帧ID")
    timestamp: datetime = Field(..., description="时间戳")
    num_people: int = Field(..., description="检测到的人数")
    has_fall: bool = Field(..., description="是否检测到摔倒")
    processing_time_ms: float = Field(..., description="处理时间（毫秒）")
    detections: List[Dict[str, Any]] = Field(default=[], description="检测结果列表")


class AlertInfo(BaseModel):
    """报警信息"""
    id: str = Field(..., description="报警ID")
    timestamp: datetime = Field(..., description="报警时间")
    level: AlertLevel = Field(..., description="报警级别")
    type: str = Field(..., description="报警类型")
    message: str = Field(..., description="报警消息")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    cluster_id: Optional[int] = Field(None, description="人员ID")
    location: Optional[str] = Field(None, description="位置信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加数据")


class DetectionConfig(BaseModel):
    """检测配置"""
    voxel_size: float = Field(0.05, ge=0.01, le=0.5, description="体素尺寸")
    height_drop_threshold: float = Field(0.3, ge=0.1, le=1.0, description="高度骤降阈值")
    velocity_threshold: float = Field(0.5, ge=0.1, le=2.0, description="速度阈值")
    confirmation_frames: int = Field(2, ge=1, le=10, description="确认帧数")
    fps: float = Field(30.0, ge=5, le=60, description="帧率")
    
    class Config:
        json_schema_extra = {
            "example": {
                "voxel_size": 0.05,
                "height_drop_threshold": 0.3,
                "velocity_threshold": 0.5,
                "confirmation_frames": 2,
                "fps": 30.0
            }
        }


class StartDetectionRequest(BaseModel):
    """启动检测请求"""
    config: Optional[DetectionConfig] = Field(None, description="检测配置")
    source: Optional[str] = Field("camera", description="数据源")


class StopDetectionResponse(BaseModel):
    """停止检测响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    total_frames: int = Field(..., description="总处理帧数")
    total_alerts: int = Field(..., description="总报警数")


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态")
    timestamp: datetime = Field(..., description="时间戳")
    uptime_seconds: float = Field(..., description="运行时间")
    version: str = Field(..., description="版本")


class StatisticsResponse(BaseModel):
    """统计响应"""
    total_frames: int = Field(..., description="总帧数")
    total_alerts: int = Field(..., description="总报警数")
    average_fps: float = Field(..., description="平均FPS")
    average_processing_time_ms: float = Field(..., description="平均处理时间")
    detection_accuracy: Optional[float] = Field(None, description="检测准确率")
    false_positive_rate: Optional[float] = Field(None, description="误报率")
    uptime_seconds: float = Field(..., description="运行时间")
    start_time: Optional[datetime] = Field(None, description="启动时间")


class ClusterInfo(BaseModel):
    """簇信息"""
    id: int = Field(..., description="簇ID")
    centroid: List[float] = Field(..., description="质心坐标")
    height: float = Field(..., description="高度")
    width: float = Field(..., description="宽度")
    depth: float = Field(..., description="深度")
    num_points: int = Field(..., description="点数")
    confidence: float = Field(..., description="置信度")
    is_human: bool = Field(..., description="是否是人体")


class DetectionResultDetail(BaseModel):
    """检测结果详情"""
    frame_id: int = Field(..., description="帧ID")
    timestamp: datetime = Field(..., description="时间戳")
    cluster_id: int = Field(..., description="簇ID")
    state: DetectionState = Field(..., description="状态")
    confidence: float = Field(..., description="置信度")
    height: float = Field(..., description="高度")
    height_change: float = Field(..., description="高度变化")
    velocity: float = Field(..., description="速度")
    is_lying: bool = Field(..., description="是否躺倒")
    alert_triggered: bool = Field(..., description="是否触发报警")
    message: str = Field(..., description="消息")


class ConfigUpdateResponse(BaseModel):
    """配置更新响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    config: Optional[DetectionConfig] = Field(None, description="当前配置")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    timestamp: datetime = Field(..., description="时间戳")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now)


class FrameUpdateMessage(WebSocketMessage):
    """帧更新消息"""
    type: str = "frame_update"
    frame: FrameResult


class AlertMessage(WebSocketMessage):
    """报警消息"""
    type: str = "alert"
    alert: AlertInfo


class StatusUpdateMessage(WebSocketMessage):
    """状态更新消息"""
    type: str = "status_update"
    status: SystemStatus
