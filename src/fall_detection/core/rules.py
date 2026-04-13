#!/usr/bin/env python3
"""
摔倒检测规则引擎
基于规则的摔倒检测方法

检测逻辑:
1. 高度骤降检测 - 人体高度突然降低
2. 速度检测 - 下落速度超过阈值
3. 姿态检测 - 躺倒姿态识别
4. 静止检测 - 摔倒后保持静止
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from ..preprocessing.clustering import HumanCluster


class FallState(Enum):
    """摔倒状态枚举"""
    NORMAL = "normal"              # 正常状态
    SUSPECTED = "suspected"        # 疑似摔倒
    CONFIRMED = "confirmed"        # 确认摔倒
    RECOVERING = "recovering"      # 恢复中
    FALSE_ALARM = "false_alarm"    # 误报


@dataclass
class DetectionResult:
    """单次检测结果"""
    timestamp: float                    # 时间戳
    frame_id: int                       # 帧 ID
    cluster_id: int                     # 人体簇 ID
    state: FallState                    # 摔倒状态
    confidence: float                   # 置信度 (0-1)
    
    # 检测指标
    height: float                       # 当前高度 (米)
    height_change: float                # 高度变化 (米)
    velocity: float                     # 垂直速度 (米/秒)
    aspect_ratio: float                 # 宽高比
    is_lying: bool                      # 是否躺倒
    
    # 报警信息
    alert_triggered: bool               # 是否触发报警
    alert_level: str                    # 报警级别 ("info", "warning", "critical")
    message: str                        # 报警消息
    
    # 原始数据引用
    cluster: Optional[HumanCluster] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'frame_id': self.frame_id,
            'cluster_id': self.cluster_id,
            'state': self.state.value,
            'confidence': self.confidence,
            'height': self.height,
            'height_change': self.height_change,
            'velocity': self.velocity,
            'aspect_ratio': self.aspect_ratio,
            'is_lying': self.is_lying,
            'alert_triggered': self.alert_triggered,
            'alert_level': self.alert_level,
            'message': self.message
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"DetectionResult: frame={self.frame_id}, "
               f"cluster={self.cluster_id}, state={self.state.value}, "
               f"confidence={self.confidence:.2f}, "
               f"alert={self.alert_triggered} ({self.alert_level})")


@dataclass
class PersonTracker:
    """人体追踪器 - 跟踪单个人的历史状态"""
    cluster_id: int
    history: List[Dict] = field(default_factory=list)  # 历史记录
    fall_state: FallState = FallState.NORMAL           # 当前摔倒状态
    fall_start_frame: Optional[int] = None             # 摔倒开始帧
    consecutive_fall_frames: int = 0                   # 连续摔倒帧数
    
    # 阈值配置（可自定义）
    height_drop_threshold: float = 0.5       # 高度骤降阈值 (米)
    velocity_threshold: float = 1.0          # 速度阈值 (米/秒)
    lying_aspect_ratio_threshold: float = 1.5  # 躺倒宽高比阈值
    confirmation_frames: int = 3             # 确认摔倒所需连续帧数
    
    def add_observation(self, cluster: HumanCluster, frame_id: int, timestamp: float):
        """添加观测数据"""
        obs = {
            'frame_id': frame_id,
            'timestamp': timestamp,
            'height': cluster.height,
            'centroid': cluster.centroid.copy(),
            'aspect_ratio': cluster.height / max(cluster.width, 0.1),
            'num_points': cluster.num_points,
            'confidence': cluster.confidence,
            'is_human_like': cluster.is_human_like()
        }
        
        self.history.append(obs)
        
        # 保持最近 30 帧的历史
        if len(self.history) > 30:
            self.history.pop(0)
    
    def get_previous_height(self) -> Optional[float]:
        """获取前一帧的高度"""
        if len(self.history) >= 2:
            return self.history[-2]['height']
        return None
    
    def get_height_change(self) -> float:
        """计算高度变化"""
        if len(self.history) >= 2:
            current_height = self.history[-1]['height']
            previous_height = self.history[-2]['height']
            return current_height - previous_height
        return 0.0
    
    def get_velocity(self, fps: float = 30.0) -> float:
        """计算垂直速度 (米/秒)"""
        if len(self.history) >= 2:
            height_change = self.get_height_change()
            time_delta = 1.0 / fps
            return height_change / time_delta
        return 0.0
    
    def is_lying_down(self) -> bool:
        """判断是否躺倒"""
        if not self.history:
            return False
        
        aspect_ratio = self.history[-1]['aspect_ratio']
        return aspect_ratio < self.lying_aspect_ratio_threshold
    
    def detect_fall(self) -> Tuple[bool, float, str]:
        """
        检测是否发生摔倒
        
        Returns:
            (是否摔倒，置信度，原因描述)
        """
        if len(self.history) < 2:
            return False, 0.0, "历史数据不足"
        
        current = self.history[-1]
        previous = self.history[-2]
        
        reasons = []
        confidence = 0.0
        
        # 规则 1: 高度骤降
        height_change = self.get_height_change()
        if height_change < -self.height_drop_threshold:
            reasons.append(f"高度骤降 {abs(height_change):.2f}米")
            confidence += 0.4
        
        # 规则 2: 快速下落
        velocity = self.get_velocity()
        if velocity < -self.velocity_threshold:
            reasons.append(f"快速下落 {abs(velocity):.2f}米/秒")
            confidence += 0.3
        
        # 规则 3: 躺倒姿态
        if self.is_lying_down():
            reasons.append(f"躺倒姿态 (宽高比={current['aspect_ratio']:.2f})")
            confidence += 0.3
        
        # 规则 4: 高度显著降低
        if current['height'] < 0.8:  # 低于 0.8 米
            reasons.append(f"高度过低 ({current['height']:.2f}米)")
            confidence += 0.2
        
        # 判断是否摔倒
        is_fall = confidence >= 0.5 or (len(reasons) >= 2)
        
        reason_str = "; ".join(reasons) if reasons else "无明显特征"
        
        return is_fall, min(confidence, 1.0), reason_str
    
    def update_state(self, is_fall: bool, confidence: float, frame_id: int):
        """更新摔倒状态"""
        if is_fall:
            if self.fall_state == FallState.NORMAL:
                self.fall_state = FallState.SUSPECTED
                self.fall_start_frame = frame_id
                self.consecutive_fall_frames = 1
            
            elif self.fall_state == FallState.SUSPECTED:
                self.consecutive_fall_frames += 1
                
                # 连续多帧检测到摔倒，确认为真
                if self.consecutive_fall_frames >= self.confirmation_frames:
                    self.fall_state = FallState.CONFIRMED
            
            elif self.fall_state == FallState.CONFIRMED:
                # 保持确认状态
                pass
        
        else:
            if self.fall_state == FallState.CONFIRMED:
                self.fall_state = FallState.RECOVERING
            
            elif self.fall_state == FallState.RECOVERING:
                # 恢复中，如果连续几帧正常则回到正常状态
                self.fall_state = FallState.NORMAL
                self.fall_start_frame = None
                self.consecutive_fall_frames = 0
            
            elif self.fall_state == FallState.SUSPECTED:
                # 疑似但后续正常，可能是误报
                self.fall_state = FallState.FALSE_ALARM
                self.fall_start_frame = None
                self.consecutive_fall_frames = 0


class RuleBasedFallDetector:
    """基于规则的摔倒检测器"""
    
    def __init__(
        self,
        height_drop_threshold: float = 0.5,
        velocity_threshold: float = 1.0,
        lying_aspect_ratio_threshold: float = 1.5,
        confirmation_frames: int = 3,
        fps: float = 30.0,
    ):
        """
        初始化摔倒检测器
        
        Args:
            height_drop_threshold: 高度骤降阈值 (米)
            velocity_threshold: 速度阈值 (米/秒)
            lying_aspect_ratio_threshold: 躺倒宽高比阈值
            confirmation_frames: 确认摔倒所需连续帧数
            fps: 帧率
        """
        self.height_drop_threshold = height_drop_threshold
        self.velocity_threshold = velocity_threshold
        self.lying_aspect_ratio_threshold = lying_aspect_ratio_threshold
        self.confirmation_frames = confirmation_frames
        self.fps = fps
        
        # 人体追踪器字典：cluster_id -> PersonTracker
        self.trackers: Dict[int, PersonTracker] = {}
        
        # 统计信息
        self.total_detections = 0
        self.total_alerts = 0
        self.false_alarms = 0
        
        logger.info(f"RuleBasedFallDetector 初始化："
                   f"height_drop={height_drop_threshold}m, "
                   f"velocity={velocity_threshold}m/s, "
                   f"confirmation_frames={confirmation_frames}")
    
    def detect(self, clusters: List[HumanCluster], frame_id: int, 
               timestamp: Optional[float] = None) -> List[DetectionResult]:
        """
        检测摔倒事件
        
        Args:
            clusters: 人体簇列表
            frame_id: 帧 ID
            timestamp: 时间戳 (可选，默认使用当前时间)
            
        Returns:
            检测结果列表
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        
        results = []
        
        # 为每个簇创建或更新追踪器
        for cluster in clusters:
            cluster_id = cluster.id
            
            # 创建新追踪器或获取现有
            if cluster_id not in self.trackers:
                tracker = PersonTracker(
                    cluster_id=cluster_id,
                    height_drop_threshold=self.height_drop_threshold,
                    velocity_threshold=self.velocity_threshold,
                    lying_aspect_ratio_threshold=self.lying_aspect_ratio_threshold,
                    confirmation_frames=self.confirmation_frames
                )
                self.trackers[cluster_id] = tracker
            else:
                tracker = self.trackers[cluster_id]
            
            # 添加观测
            tracker.add_observation(cluster, frame_id, timestamp)
            
            # 检测摔倒
            is_fall, confidence, reason = tracker.detect_fall()
            
            # 更新状态
            tracker.update_state(is_fall, confidence, frame_id)
            
            # 创建检测结果
            result = self._create_result(
                tracker=tracker,
                cluster=cluster,
                frame_id=frame_id,
                timestamp=timestamp,
                is_fall=is_fall,
                confidence=confidence,
                reason=reason
            )
            
            results.append(result)
            
            # 更新统计
            self.total_detections += 1
            if result.alert_triggered:
                self.total_alerts += 1
            if tracker.fall_state == FallState.FALSE_ALARM:
                self.false_alarms += 1
        
        # 清理长时间未出现的追踪器
        self._cleanup_trackers(clusters)
        
        logger.debug(f"Frame {frame_id}: 检测 {len(clusters)} 人，"
                    f"{sum(1 for r in results if r.alert_triggered)} 次报警")
        
        return results
    
    def _create_result(self, tracker: PersonTracker, cluster: HumanCluster,
                      frame_id: int, timestamp: float,
                      is_fall: bool, confidence: float,
                      reason: str) -> DetectionResult:
        """创建检测结果"""
        height_change = tracker.get_height_change()
        velocity = tracker.get_velocity(self.fps)
        is_lying = tracker.is_lying_down()
        
        # 确定报警级别
        if tracker.fall_state == FallState.CONFIRMED:
            alert_level = "critical"
            alert_triggered = True
            message = f"⚠️ 确认摔倒！{reason}"
        
        elif tracker.fall_state == FallState.SUSPECTED:
            alert_level = "warning"
            alert_triggered = True
            message = f"⚠️ 疑似摔倒！{reason}"
        
        elif tracker.fall_state == FallState.RECOVERING:
            alert_level = "info"
            alert_triggered = False
            message = "ℹ️ 人员正在恢复"
        
        elif tracker.fall_state == FallState.FALSE_ALARM:
            alert_level = "info"
            alert_triggered = False
            message = "✅ 误报解除"
        
        else:  # NORMAL
            alert_level = "info"
            alert_triggered = False
            message = "✅ 状态正常"
        
        return DetectionResult(
            timestamp=timestamp,
            frame_id=frame_id,
            cluster_id=tracker.cluster_id,
            state=tracker.fall_state,
            confidence=confidence,
            height=cluster.height,
            height_change=height_change,
            velocity=velocity,
            aspect_ratio=cluster.height / max(cluster.width, 0.1),
            is_lying=is_lying,
            alert_triggered=alert_triggered,
            alert_level=alert_level,
            message=message,
            cluster=cluster
        )
    
    def _cleanup_trackers(self, current_clusters: List[HumanCluster]):
        """清理长时间未出现的追踪器"""
        current_ids = {c.id for c in current_clusters}
        stale_ids = set(self.trackers.keys()) - current_ids
        
        # 简单实现：立即清理
        # 更好的实现可以保留一段时间用于重识别
        for stale_id in stale_ids:
            logger.debug(f"清理追踪器 {stale_id}")
            del self.trackers[stale_id]
    
    def get_tracker(self, cluster_id: int) -> Optional[PersonTracker]:
        """获取指定人体的追踪器"""
        return self.trackers.get(cluster_id)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_detections': self.total_detections,
            'total_alerts': self.total_alerts,
            'false_alarms': self.false_alarms,
            'active_trackers': len(self.trackers),
            'alert_rate': self.total_alerts / max(self.total_detections, 1)
        }
    
    def reset(self):
        """重置检测器"""
        self.trackers.clear()
        self.total_detections = 0
        self.total_alerts = 0
        self.false_alarms = 0
        logger.info("摔倒检测器已重置")


def create_fall_detector(method: str = 'rule_based', **kwargs):
    """
    工厂函数：创建摔倒检测器
    
    Args:
        method: 检测方法 ('rule_based', 'ai_based', 'hybrid')
        **kwargs: 检测器参数
        
    Returns:
        检测器实例
    """
    if method == 'rule_based':
        return RuleBasedFallDetector(**kwargs)
    elif method == 'ai_based':
        # TODO: 实现 AI -based 检测器
        raise NotImplementedError("AI-based 检测器尚未实现")
    elif method == 'hybrid':
        # TODO: 实现混合检测器
        raise NotImplementedError("混合检测器尚未实现")
    else:
        raise ValueError(f"未知的检测方法：{method}")


# 测试代码
if __name__ == "__main__":
    print("🧪 测试摔倒检测规则引擎...")
    
    from ..preprocessing.clustering import HumanCluster
    import open3d as o3d
    
    # 创建检测器
    detector = RuleBasedFallDetector(
        height_drop_threshold=0.3,
        velocity_threshold=0.5,
        confirmation_frames=2,
        fps=30
    )
    
    # 模拟正常站立的人
    print("\n1️⃣ 模拟正常站立...")
    normal_cluster = HumanCluster(
        id=0,
        point_cloud=o3d.geometry.PointCloud(),
        centroid=np.array([0, 0, 0.9]),
        bounding_box=None,
        num_points=500,
        confidence=1.0
    )
    # 手动设置包围盒范围来模拟高度
    normal_cluster.bounding_box = o3d.geometry.AxisAlignedBoundingBox(
        min_bound=(-0.2, -0.2, 0.0),
        max_bound=(0.2, 0.2, 1.7)
    )
    
    for i in range(5):
        results = detector.detect([normal_cluster], frame_id=i)
        result = results[0]
        print(f"  帧 {i}: 高度={result.height:.2f}m, "
              f"状态={result.state.value}, "
              f"报警={result.alert_triggered}")
    
    # 模拟摔倒过程
    print("\n2️⃣ 模拟摔倒过程...")
    
    # 创建不同高度的簇来模拟摔倒
    heights = [1.7, 1.6, 1.5, 1.0, 0.5, 0.4, 0.4, 0.4]  # 逐渐降低
    
    for i, height in enumerate(heights):
        fall_cluster = HumanCluster(
            id=0,
            point_cloud=o3d.geometry.PointCloud(),
            centroid=np.array([0, 0, height/2]),
            bounding_box=None,
            num_points=500,
            confidence=1.0
        )
        # 模拟躺倒：高度降低，宽度增加
        fall_cluster.bounding_box = o3d.geometry.AxisAlignedBoundingBox(
            min_bound=(-0.8, -0.2, 0.0),
            max_bound=(0.8, 0.2, height)
        )
        
        results = detector.detect([fall_cluster], frame_id=i+10)
        result = results[0]
        
        print(f"  帧 {i+10}: 高度={result.height:.2f}m, "
              f"变化={result.height_change:+.2f}m, "
              f"速度={result.velocity:+.2f}m/s, "
              f"状态={result.state.value}, "
              f"报警={result.alert_triggered} ({result.alert_level})")
        
        if result.alert_triggered:
            print(f"    📢 {result.message}")
    
    # 打印统计
    print("\n📊 统计信息:")
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 测试完成！")
