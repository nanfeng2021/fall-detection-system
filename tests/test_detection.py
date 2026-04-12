#!/usr/bin/env python3
"""
检测模块测试
"""

import pytest
import numpy as np
import open3d as o3d

from src.detection.rules import (
    RuleBasedFallDetector, PersonTracker, FallState, DetectionResult
)
from src.preprocessing.clustering import HumanCluster


class TestPersonTracker:
    """人体追踪器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        tracker = PersonTracker(cluster_id=0)
        
        assert tracker.cluster_id == 0
        assert tracker.fall_state == FallState.NORMAL
        assert tracker.history == []
    
    def test_add_observation(self, mock_human_cluster):
        """测试添加观测"""
        tracker = PersonTracker(cluster_id=0)
        tracker.add_observation(mock_human_cluster, frame_id=1, timestamp=1000.0)
        
        assert len(tracker.history) == 1
        assert tracker.history[0]['frame_id'] == 1
    
    def test_height_change(self, mock_human_cluster):
        """测试高度变化计算"""
        tracker = PersonTracker(cluster_id=0)
        
        # 添加两个观测
        tracker.add_observation(mock_human_cluster, frame_id=1, timestamp=1.0)
        
        # 修改高度模拟摔倒
        mock_human_cluster.bounding_box.max_bound[2] = 0.5
        tracker.add_observation(mock_human_cluster, frame_id=2, timestamp=2.0)
        
        height_change = tracker.get_height_change()
        assert height_change < 0  # 高度下降
    
    def test_velocity_calculation(self, mock_human_cluster):
        """测试速度计算"""
        tracker = PersonTracker(cluster_id=0)
        
        tracker.add_observation(mock_human_cluster, frame_id=1, timestamp=0.0)
        
        # 降低高度
        mock_human_cluster.bounding_box.max_bound[2] = 0.5
        tracker.add_observation(mock_human_cluster, frame_id=2, timestamp=1.0)
        
        velocity = tracker.get_velocity(fps=1.0)
        assert velocity < 0  # 向下运动
    
    def test_is_lying_down(self, mock_human_cluster):
        """测试躺倒判断"""
        tracker = PersonTracker(cluster_id=0)
        
        # 正常站立
        tracker.add_observation(mock_human_cluster, frame_id=1, timestamp=1.0)
        assert tracker.is_lying_down() == False
    
    def test_state_transitions(self, mock_human_cluster):
        """测试状态转换"""
        tracker = PersonTracker(cluster_id=0, confirmation_frames=2)
        
        # 初始状态
        assert tracker.fall_state == FallState.NORMAL
        
        # 第一次检测到摔倒
        tracker.update_state(is_fall=True, confidence=0.6, frame_id=1)
        assert tracker.fall_state == FallState.SUSPECTED
        
        # 连续检测到，确认摔倒
        tracker.update_state(is_fall=True, confidence=0.6, frame_id=2)
        assert tracker.fall_state == FallState.CONFIRMED
        
        # 恢复正常
        tracker.update_state(is_fall=False, confidence=0.0, frame_id=10)
        assert tracker.fall_state == FallState.RECOVERING


class TestRuleBasedFallDetector:
    """规则检测器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        detector = RuleBasedFallDetector(
            height_drop_threshold=0.3,
            velocity_threshold=0.5,
            confirmation_frames=2
        )
        
        assert detector.height_drop_threshold == 0.3
        assert detector.velocity_threshold == 0.5
        assert detector.confirmation_frames == 2
    
    def test_detect_normal(self, mock_human_cluster):
        """测试正常状态检测"""
        detector = RuleBasedFallDetector()
        
        results = detector.detect([mock_human_cluster], frame_id=1)
        
        assert len(results) == 1
        assert results[0].state == FallState.NORMAL
        assert results[0].alert_triggered == False
    
    def test_detect_fall(self):
        """测试摔倒检测"""
        detector = RuleBasedFallDetector(
            height_drop_threshold=0.3,
            velocity_threshold=0.5,
            confirmation_frames=2
        )
        
        # 创建模拟摔倒的人体簇
        heights = [1.7, 1.5, 1.0, 0.5, 0.4]
        
        for i, height in enumerate(heights):
            points = np.random.rand(500, 3) * [0.4, 0.4, height] + [0, 0, height/2]
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            
            cluster = HumanCluster(
                id=0,
                point_cloud=pcd,
                centroid=np.array([0, 0, height/2]),
                bounding_box=pcd.get_axis_aligned_bounding_box(),
                num_points=500,
                confidence=0.9
            )
            
            results = detector.detect([cluster], frame_id=i)
            
            if i >= 3:  # 摔倒后几帧
                assert results[0].height < 0.6
    
    def test_empty_clusters(self):
        """测试空簇列表"""
        detector = RuleBasedFallDetector()
        
        results = detector.detect([], frame_id=1)
        
        assert results == []
    
    def test_statistics(self, mock_human_cluster):
        """测试统计信息"""
        detector = RuleBasedFallDetector()
        
        # 模拟一些检测
        for i in range(5):
            detector.detect([mock_human_cluster], frame_id=i)
        
        stats = detector.get_statistics()
        
        assert 'total_detections' in stats
        assert stats['total_detections'] == 5
        assert 'active_trackers' in stats
    
    def test_tracker_cleanup(self):
        """测试追踪器清理"""
        detector = RuleBasedFallDetector()
        
        # 创建两个簇
        points1 = np.random.rand(500, 3) * [0.4, 0.4, 1.7] + [0, 0, 0.85]
        pcd1 = o3d.geometry.PointCloud()
        pcd1.points = o3d.utility.Vector3dVector(points1)
        cluster1 = HumanCluster(id=0, point_cloud=pcd1, centroid=np.array([0, 0, 0.85]),
                               bounding_box=pcd1.get_axis_aligned_bounding_box(),
                               num_points=500, confidence=0.9)
        
        points2 = np.random.rand(500, 3) * [0.4, 0.4, 1.7] + [2, 0, 0.85]
        pcd2 = o3d.geometry.PointCloud()
        pcd2.points = o3d.utility.Vector3dVector(points2)
        cluster2 = HumanCluster(id=1, point_cloud=pcd2, centroid=np.array([2, 0, 0.85]),
                               bounding_box=pcd2.get_axis_aligned_bounding_box(),
                               num_points=500, confidence=0.9)
        
        # 第一次检测两个
        detector.detect([cluster1, cluster2], frame_id=1)
        assert len(detector.trackers) == 2
        
        # 第二次只检测一个
        detector.detect([cluster1], frame_id=2)
        assert len(detector.trackers) == 1


class TestDetectionResult:
    """检测结果测试"""
    
    def test_to_dict(self):
        """测试字典转换"""
        result = DetectionResult(
            timestamp=1000.0,
            frame_id=1,
            cluster_id=0,
            state=FallState.NORMAL,
            confidence=0.9,
            height=1.7,
            height_change=0.0,
            velocity=0.0,
            aspect_ratio=4.0,
            is_lying=False,
            alert_triggered=False,
            alert_level="info",
            message="正常"
        )
        
        data = result.to_dict()
        
        assert data['frame_id'] == 1
        assert data['state'] == 'normal'
        assert data['confidence'] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
