#!/usr/bin/env python3
"""
快速测试摔倒检测 - 简化版
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import open3d as o3d
from src.detection.detector import FallDetectionSystem, SystemAlert
from datetime import datetime

def create_simple_mock_cloud(frame_id: int, is_falling: bool = False):
    """创建简单的模拟点云 - 人体点云更密集"""
    np.random.seed(frame_id + 42)
    
    # 地面 (500 点) - 只在周围，中间留空给人体
    ground_x = np.random.uniform(0, 4, 500)
    ground_y = np.random.uniform(0, 4, 500)
    # 移除中心区域的地面点
    mask = ((ground_x < 1.5) | (ground_x > 2.5)) | ((ground_y < 1.5) | (ground_y > 2.5))
    ground_x = ground_x[mask]
    ground_y = ground_y[mask]
    ground_z = np.zeros_like(ground_x)
    ground_points = np.column_stack([ground_x, ground_y, ground_z])
    
    # 人体 (800 点) - 密集的圆柱体，放在中心
    human_center_x = 2.0
    human_center_y = 2.0
    
    if is_falling:
        # 摔倒状态
        progress = min(1.0, (frame_id - 50) / 10)
        height = max(0.3, 1.7 - progress * 1.4)  # 从 1.7m 降到 0.3m
        radius = 0.3 + progress * 0.5  # 从 0.3m 扩展到 0.8m
        
        theta = np.random.uniform(0, 2 * np.pi, 800)
        r = np.sqrt(np.random.uniform(0, 1, 800)) * radius
        h = np.random.uniform(0, 1, 800) * height
        
        human_points = np.column_stack([
            r * np.cos(theta) + human_center_x,
            r * np.sin(theta) + human_center_y,
            h
        ])
    else:
        # 站立状态
        height = 1.7
        radius = 0.3
        
        theta = np.random.uniform(0, 2 * np.pi, 800)
        r = np.sqrt(np.random.uniform(0, 1, 800)) * radius
        h = np.random.uniform(0, 1, 800) * height
        
        human_points = np.column_stack([
            r * np.cos(theta) + human_center_x,
            r * np.sin(theta) + human_center_y,
            h
        ])
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


def on_alert(alert: SystemAlert):
    """报警回调"""
    timestamp = alert.timestamp.strftime("%H:%M:%S")
    emoji = "🚨" if alert.alert_type == 'fall_confirmed' else "⚠️"
    print(f"{emoji} [{timestamp}] {alert.alert_type}: {alert.message}")
    print(f"   置信度：{alert.confidence:.2f}, 簇 ID: {alert.cluster_id}")


# 创建系统实例
print("="*60)
print("🧪 摔倒检测系统测试")
print("="*60)

system = FallDetectionSystem(
    voxel_size=0.05,
    std_ratio=2.0,
    cluster_tolerance=0.25,
    height_drop_threshold=0.3,
    velocity_threshold=0.5,
    confirmation_frames=2,
    alert_callback=on_alert
)

# 处理 70 帧（前 50 帧正常，后 20 帧摔倒）
print("\n开始处理 70 帧...")
print("-" * 60)

for frame_id in range(70):
    is_falling = frame_id >= 50
    cloud = create_simple_mock_cloud(frame_id, is_falling)
    
    result = system.process_frame(cloud, frame_id)
    
    # 每 5 帧打印一次状态
    if frame_id % 5 == 0 or result.has_fall:
        status = "🚨 摔倒!" if result.has_fall else "✅ 正常"
        print(f"Frame {frame_id:3d}: {result.num_people} 人, 高度：{result.detections[0].height:.2f}m" if result.num_people > 0 else f"Frame {frame_id:3d}: 0 人", end=" ")
        print(f"- {status}")

print("-" * 60)
print("测试完成！")
