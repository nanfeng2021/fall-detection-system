#!/usr/bin/env python3
"""
摔倒检测器主模块
整合预处理、人体聚类和摔倒检测规则

使用方式:
1. 创建 FallDetectionSystem 实例
2. 调用 process_frame() 处理每帧
3. 监听报警回调
"""

import numpy as np
import open3d as o3d
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
import time
from loguru import logger

from ..preprocessing.pipeline import PointCloudPipeline, PreprocessingResult
from ..preprocessing.clustering import HumanCluster
from .rules import RuleBasedFallDetector, DetectionResult, FallState


@dataclass
class SystemAlert:
    """系统报警"""
    timestamp: datetime
    alert_type: str              # 'fall_confirmed', 'fall_suspected', 'system_error'
    cluster_id: int
    message: str
    confidence: float
    location: Optional[str] = None  # 位置信息
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'alert_type': self.alert_type,
            'cluster_id': self.cluster_id,
            'message': self.message,
            'confidence': self.confidence,
            'location': self.location,
            'metadata': self.metadata or {}
        }


@dataclass
class FrameResult:
    """单帧处理结果"""
    frame_id: int
    timestamp: datetime
    preprocessing: PreprocessingResult
    detections: List[DetectionResult]
    alerts: List[SystemAlert]
    processing_time_ms: float
    
    @property
    def has_fall(self) -> bool:
        """是否检测到摔倒"""
        return any(d.alert_triggered for d in self.detections)
    
    @property
    def num_people(self) -> int:
        """检测到的人数"""
        return len(self.detections)
    
    @property
    def num_falls(self) -> int:
        """摔倒人数"""
        return sum(1 for d in self.detections if d.alert_triggered)


class FallDetectionSystem:
    """摔倒检测系统主类"""
    
    def __init__(
        self,
        voxel_size: float = 0.05,
        std_ratio: float = 2.0,
        distance_threshold: float = 0.05,
        cluster_tolerance: float = 0.25,  # 增大到 0.25 以检测人体
        height_drop_threshold: float = 0.3,
        velocity_threshold: float = 0.5,
        confirmation_frames: int = 2,
        fps: float = 30.0,
        alert_callback: Optional[Callable[[SystemAlert], None]] = None,
    ):
        """
        初始化摔倒检测系统
        
        Args:
            voxel_size: 体素降采样尺寸 (米)
            std_ratio: 统计滤波标准差倍数
            distance_threshold: 地面分割距离阈值 (米)
            cluster_tolerance: 聚类半径阈值 (米)
            height_drop_threshold: 高度骤降阈值 (米)
            velocity_threshold: 速度阈值 (米/秒)
            confirmation_frames: 确认摔倒所需连续帧数
            fps: 帧率
            alert_callback: 报警回调函数
        """
        # 创建预处理 Pipeline
        self.pipeline = PointCloudPipeline(
            config={
                'voxel_size': voxel_size,
                'std_ratio': std_ratio,
                'distance_threshold': distance_threshold,
                'cluster_tolerance': cluster_tolerance,
            }
        )
        
        # 创建摔倒检测器
        self.fall_detector = RuleBasedFallDetector(
            height_drop_threshold=height_drop_threshold,
            velocity_threshold=velocity_threshold,
            confirmation_frames=confirmation_frames,
            fps=fps
        )
        
        # 报警回调
        self.alert_callback = alert_callback
        
        # 统计信息
        self.frame_count = 0
        self.total_alerts = 0
        self.start_time: Optional[datetime] = None
        
        # 性能监控
        self.fps_history = []
        
        logger.info("FallDetectionSystem 初始化完成")
        logger.info(f"  预处理配置：voxel={voxel_size}, std_ratio={std_ratio}")
        logger.info(f"  检测配置：height_drop={height_drop_threshold}m, "
                   f"velocity={velocity_threshold}m/s")
    
    def process_frame(self, raw_cloud: o3d.geometry.PointCloud, 
                     frame_id: Optional[int] = None) -> FrameResult:
        """
        处理单帧点云
        
        Args:
            raw_cloud: 原始点云
            frame_id: 帧 ID (可选，默认自动生成)
            
        Returns:
            处理结果
        """
        start_time = time.time()
        
        # 初始化计时
        if self.start_time is None:
            self.start_time = datetime.now()
        
        # 生成帧 ID
        if frame_id is None:
            frame_id = self.frame_count
        
        timestamp = datetime.now()
        
        # Step 1: 预处理
        preproc_result = self.pipeline.process(raw_cloud)
        
        # Step 2: 摔倒检测
        detection_results = self.fall_detector.detect(
            clusters=preproc_result.human_clusters,
            frame_id=frame_id,
            timestamp=timestamp.timestamp()
        )
        
        # Step 3: 生成报警
        alerts = []
        for det_result in detection_results:
            if det_result.alert_triggered:
                alert = SystemAlert(
                    timestamp=timestamp,
                    alert_type='fall_confirmed' if det_result.state == FallState.CONFIRMED else 'fall_suspected',
                    cluster_id=det_result.cluster_id,
                    message=det_result.message,
                    confidence=det_result.confidence,
                    metadata=det_result.to_dict()
                )
                alerts.append(alert)
                
                # 触发回调
                if self.alert_callback:
                    try:
                        self.alert_callback(alert)
                    except Exception as e:
                        logger.error(f"报警回调执行失败：{e}")
        
        # 计算处理时间
        processing_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 更新 FPS 统计
        if processing_time > 0:
            fps = 1000.0 / processing_time
            self.fps_history.append(fps)
            if len(self.fps_history) > 30:
                self.fps_history.pop(0)
        
        # 创建结果
        result = FrameResult(
            frame_id=frame_id,
            timestamp=timestamp,
            preprocessing=preproc_result,
            detections=detection_results,
            alerts=alerts,
            processing_time_ms=processing_time
        )
        
        # 更新统计
        self.frame_count += 1
        self.total_alerts += len(alerts)
        
        # 日志记录
        avg_fps = np.mean(self.fps_history) if self.fps_history else 0
        
        if result.has_fall:
            logger.warning(f"Frame {frame_id}: ⚠️ 检测到 {result.num_falls} 次摔倒！"
                          f" ({processing_time:.1f}ms, {avg_fps:.1f} FPS)")
        else:
            logger.debug(f"Frame {frame_id}: {result.num_people} 人，正常 "
                        f"({processing_time:.1f}ms, {avg_fps:.1f} FPS)")
        
        return result
    
    def process_continuous(self, cloud_generator, max_frames: Optional[int] = None):
        """
        连续处理点云流
        
        Args:
            cloud_generator: 点云生成器 (yield o3d.geometry.PointCloud)
            max_frames: 最大处理帧数 (None 则无限)
            
        Yields:
            FrameResult
        """
        logger.info("开始连续处理...")
        
        frame_count = 0
        try:
            for raw_cloud in cloud_generator:
                result = self.process_frame(raw_cloud)
                yield result
                
                frame_count += 1
                
                if max_frames and frame_count >= max_frames:
                    break
                
        except KeyboardInterrupt:
            logger.info("用户中断处理")
        except Exception as e:
            logger.error(f"处理异常：{e}")
            raise
        
        logger.info(f"连续处理完成，共 {frame_count} 帧")
    
    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'uptime_seconds': uptime,
            'total_frames': self.frame_count,
            'total_alerts': self.total_alerts,
            'average_fps': np.mean(self.fps_history) if self.fps_history else 0,
            'active_trackers': len(self.fall_detector.trackers),
            'detector_stats': self.fall_detector.get_statistics()
        }
    
    def reset(self):
        """重置系统"""
        self.pipeline = PointCloudPipeline()  # 重新创建 Pipeline
        self.fall_detector.reset()
        self.frame_count = 0
        self.total_alerts = 0
        self.start_time = None
        self.fps_history.clear()
        logger.info("系统已重置")


def create_detection_system(config: Optional[Dict] = None, **kwargs):
    """
    工厂函数：创建摔倒检测系统
    
    Args:
        config: 配置字典
        **kwargs: 系统参数
        
    Returns:
        FallDetectionSystem 实例
    """
    if config:
        kwargs.update(config)
    
    return FallDetectionSystem(**kwargs)


# 测试代码
if __name__ == "__main__":
    print("🧪 测试摔倒检测系统...")
    
    # 创建模拟点云生成器
    def mock_cloud_generator(num_frames: int = 100):
        """生成模拟点云"""
        for i in range(num_frames):
            # 创建地面
            ground_points = np.random.rand(1000, 3) * [5, 5, 0.05]
            ground_points[:, 2] = 0
            
            # 创建人体（高度逐渐降低模拟摔倒）
            if i < 50:
                # 正常站立
                height = 1.7
            else:
                # 摔倒过程
                height = max(0.4, 1.7 - (i - 50) * 0.1)
            
            human_points = np.random.rand(500, 3) * [0.4, 0.4, height]
            human_points[:, 2] += (1.7 - height) / 2  # 调整质心
            
            # 合并
            all_points = np.vstack([ground_points, human_points])
            
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(all_points)
            
            yield pcd
    
    # 创建报警回调
    def on_alert(alert: SystemAlert):
        print(f"\n🚨 报警！")
        print(f"  类型：{alert.alert_type}")
        print(f"  消息：{alert.message}")
        print(f"  置信度：{alert.confidence:.2f}")
        print(f"  时间：{alert.timestamp}")
    
    # 创建系统
    system = FallDetectionSystem(
        voxel_size=0.05,
        height_drop_threshold=0.3,
        velocity_threshold=0.5,
        confirmation_frames=2,
        alert_callback=on_alert
    )
    
    # 处理模拟数据
    print("\n开始处理模拟数据...")
    print("="*60)
    
    for i, result in enumerate(system.process_continuous(mock_cloud_generator(80))):
        if i % 10 == 0:
            print(f"\n帧 {i}:")
            print(f"  处理时间：{result.processing_time_ms:.1f}ms")
            print(f"  检测到 {result.num_people} 人")
            print(f"  摔倒 {result.num_falls} 人")
            
            if result.has_fall:
                for alert in result.alerts:
                    print(f"  🚨 {alert.message}")
    
    # 打印统计
    print("\n" + "="*60)
    print("📊 系统统计:")
    stats = system.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成！")
