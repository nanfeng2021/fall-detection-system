#!/usr/bin/env python3
"""
检测服务
封装检测逻辑，为API提供统一接口
"""

import time
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from .models import (
    SystemStatus, FrameResult, AlertInfo, DetectionConfig,
    StatisticsResponse, AlertLevel
)


@dataclass
class ServiceState:
    """服务状态"""
    is_running: bool = False
    current_frame: int = 0
    current_fps: float = 0.0
    start_time: Optional[datetime] = None
    total_frames: int = 0
    total_alerts: int = 0
    fps_history: List[float] = field(default_factory=list)
    alerts: List[AlertInfo] = field(default_factory=list)
    frame_buffer: List[FrameResult] = field(default_factory=list)
    active_trackers: int = 0


class DetectionService:
    """检测服务"""
    
    _instance: Optional['DetectionService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._state = ServiceState()
            self._config = DetectionConfig()
            self._lock = asyncio.Lock()
            self._detection_task: Optional[asyncio.Task] = None
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._state.is_running
    
    @property
    def current_frame(self) -> int:
        """当前帧"""
        return self._state.current_frame
    
    @property
    def current_fps(self) -> float:
        """当前FPS"""
        return self._state.current_fps
    
    @property
    def total_frames(self) -> int:
        """总帧数"""
        return self._state.total_frames
    
    @property
    def total_alerts(self) -> int:
        """总报警数"""
        return self._state.total_alerts
    
    @property
    def active_trackers(self) -> int:
        """活跃追踪器数量"""
        return self._state.active_trackers
    
    @property
    def uptime_seconds(self) -> float:
        """运行时间"""
        if self._state.start_time is None:
            return 0.0
        return (datetime.now() - self._state.start_time).total_seconds()
    
    async def initialize(self):
        """初始化服务"""
        # 加载配置
        self._config = DetectionConfig()
        print("✅ 检测服务初始化完成")
    
    async def shutdown(self):
        """关闭服务"""
        if self.is_running:
            await self.stop()
        print("🛑 检测服务已关闭")
    
    async def start(self, config: Optional[DetectionConfig] = None) -> bool:
        """启动检测"""
        async with self._lock:
            if self.is_running:
                return True
            
            if config:
                self._config = config
            
            self._state.is_running = True
            self._state.start_time = datetime.now()
            self._state.current_frame = 0
            
            # 启动检测任务
            self._detection_task = asyncio.create_task(self._detection_loop())
            
            print(f"▶️ 检测已启动，配置: {self._config}")
            return True
    
    async def stop(self) -> bool:
        """停止检测"""
        async with self._lock:
            if not self.is_running:
                return False
            
            self._state.is_running = False
            
            # 取消检测任务
            if self._detection_task:
                self._detection_task.cancel()
                try:
                    await self._detection_task
                except asyncio.CancelledError:
                    pass
                self._detection_task = None
            
            print("⏹️ 检测已停止")
            return True
    
    async def _detection_loop(self):
        """检测主循环"""
        try:
            while self.is_running:
                # 模拟帧处理
                await self._process_frame()
                
                # 控制帧率
                await asyncio.sleep(1.0 / self._config.fps)
        
        except asyncio.CancelledError:
            print("检测循环被取消")
        except Exception as e:
            print(f"检测循环错误: {e}")
            self._state.is_running = False
    
    async def _process_frame(self):
        """处理单帧"""
        start_time = time.time()
        
        self._state.current_frame += 1
        self._state.total_frames += 1
        
        # 模拟处理结果
        frame_result = FrameResult(
            frame_id=self._state.current_frame,
            timestamp=datetime.now(),
            num_people=1,  # 模拟检测到1人
            has_fall=False,
            processing_time_ms=33.0,
            detections=[]
        )
        
        # 保存到缓冲区
        self._state.frame_buffer.append(frame_result)
        if len(self._state.frame_buffer) > 100:
            self._state.frame_buffer.pop(0)
        
        # 计算FPS
        processing_time = (time.time() - start_time) * 1000
        fps = 1000.0 / max(processing_time, 1)
        self._state.current_fps = fps
        self._state.fps_history.append(fps)
        if len(self._state.fps_history) > 30:
            self._state.fps_history.pop(0)
    
    async def get_status(self) -> SystemStatus:
        """获取系统状态"""
        return SystemStatus(
            is_running=self.is_running,
            current_frame=self.current_frame,
            fps=self.current_fps,
            uptime_seconds=self.uptime_seconds,
            active_trackers=self.active_trackers,
            total_alerts=self.total_alerts
        )
    
    async def get_latest_frame(self) -> Optional[FrameResult]:
        """获取最新帧"""
        if not self._state.frame_buffer:
            return None
        return self._state.frame_buffer[-1]
    
    async def get_frame(self, frame_id: int) -> Optional[FrameResult]:
        """获取指定帧"""
        for frame in self._state.frame_buffer:
            if frame.frame_id == frame_id:
                return frame
        return None
    
    async def get_alerts(self, limit: int = 100, 
                        level: Optional[str] = None) -> List[AlertInfo]:
        """获取报警列表"""
        alerts = self._state.alerts
        
        if level:
            alerts = [a for a in alerts if a.level.value == level]
        
        return alerts[-limit:]
    
    async def get_alert_stats(self) -> Dict[str, int]:
        """获取报警统计"""
        stats = {"critical": 0, "warning": 0, "info": 0}
        
        for alert in self._state.alerts:
            if alert.level.value in stats:
                stats[alert.level.value] += 1
        
        return stats
    
    async def clear_alerts(self):
        """清空报警"""
        self._state.alerts.clear()
        self._state.total_alerts = 0
    
    async def get_config(self) -> DetectionConfig:
        """获取配置"""
        return self._config
    
    async def update_config(self, config: DetectionConfig) -> bool:
        """更新配置"""
        self._config = config
        return True
    
    async def reset_config(self):
        """重置配置"""
        self._config = DetectionConfig()
    
    async def get_statistics(self) -> StatisticsResponse:
        """获取统计信息"""
        avg_fps = sum(self._state.fps_history) / max(len(self._state.fps_history), 1)
        
        return StatisticsResponse(
            total_frames=self.total_frames,
            total_alerts=self.total_alerts,
            average_fps=avg_fps,
            average_processing_time_ms=1000.0 / max(avg_fps, 1),
            uptime_seconds=self.uptime_seconds,
            start_time=self._state.start_time
        )
    
    async def get_fps_history(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """获取FPS历史"""
        return [
            {"timestamp": datetime.now().isoformat(), "fps": fps}
            for fps in self._state.fps_history
        ]
    
    def _add_alert(self, level: AlertLevel, message: str, confidence: float = 0.5):
        """添加报警（内部方法）"""
        alert = AlertInfo(
            id=f"alert_{self._state.total_alerts}",
            timestamp=datetime.now(),
            level=level,
            type="fall_detection",
            message=message,
            confidence=confidence
        )
        
        self._state.alerts.append(alert)
        self._state.total_alerts += 1


# 全局服务实例
detection_service = DetectionService()
