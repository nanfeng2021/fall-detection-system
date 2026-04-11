#!/usr/bin/env python3
"""
地面分割模块
使用 RANSAC 算法从点云中分割地面
"""

import numpy as np
import open3d as o3d
from typing import Tuple, Optional
from loguru import logger


class GroundSegmenter:
    """基于 RANSAC 的地面分割器"""
    
    def __init__(
        self,
        distance_threshold: float = 0.05,
        ransac_n: int = 3,
        num_iterations: int = 100,
        z_axis: int = 1,  # Y 轴是垂直方向（Azure Kinect 坐标系）
    ):
        """
        初始化地面分割器
        
        Args:
            distance_threshold: 点到平面的距离阈值（米）
            ransac_n: RANSAC 采样点数
            num_iterations: RANSAC 迭代次数
            z_axis: 垂直轴索引（Azure Kinect: Y 轴=1, 其他可能是 Z 轴=2）
        """
        self.distance_threshold = distance_threshold
        self.ransac_n = ransac_n
        self.num_iterations = num_iterations
        self.z_axis = z_axis
        
        logger.info(f"GroundSegmenter 初始化："
                   f"distance_threshold={distance_threshold}, "
                   f"iterations={num_iterations}")
    
    def segment(self, cloud: o3d.geometry.PointCloud) -> Tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud]:
        """
        分割地面和非地面点云
        
        Args:
            cloud: 输入点云
            
        Returns:
            (地面点云，非地面点云)
        """
        logger.debug(f"应用 RANSAC 地面分割，输入点数：{len(cloud.points)}")
        
        # RANSAC 平面拟合
        plane_model, inliers = cloud.segment_plane(
            distance_threshold=self.distance_threshold,
            ransac_n=self.ransac_n,
            num_iterations=self.num_iterations
        )
        
        # 提取地面和非地面点云
        ground_cloud = cloud.select_by_index(inliers)
        non_ground_cloud = cloud.select_by_index(inliers, invert=True)
        
        # 验证平面模型是否合理（地面应该是相对水平的）
        a, b, c, d = plane_model
        normal_vector = np.array([a, b, c])
        
        # 检查法向量是否接近垂直方向
        vertical_axis = np.zeros(3)
        vertical_axis[self.z_axis] = 1.0
        
        cos_angle = np.abs(np.dot(normal_vector, vertical_axis))
        
        if cos_angle < 0.8:  # 角度大于约 37 度
            logger.warning(f"检测到的平面可能不是地面（法向量角度异常：{np.arccos(cos_angle):.2f} 弧度）")
        
        logger.info(f"地面分割完成：地面 {len(ground_cloud.points)} 个点，"
                   f"非地面 {len(non_ground_cloud.points)} 个点，"
                   f"占比 {len(ground_cloud.points)/max(len(cloud.points), 1):.2%}")
        
        return ground_cloud, non_ground_cloud
    
    def get_plane_equation(self, cloud: o3d.geometry.PointCloud) -> np.ndarray:
        """
        获取地面平面方程
        
        Args:
            cloud: 输入点云
            
        Returns:
            平面参数 [a, b, c, d]，满足 ax + by + cz + d = 0
        """
        _, inliers = cloud.segment_plane(
            distance_threshold=self.distance_threshold,
            ransac_n=self.ransac_n,
            num_iterations=self.num_iterations
        )
        
        # 重新拟合以获得更精确的平面
        ground_points = np.asarray(cloud.points)[inliers]
        
        if len(ground_points) < 3:
            raise ValueError("地面点太少，无法拟合平面")
        
        # 使用最小二乘法拟合平面
        A = ground_points[:, :2]
        B = ground_points[:, 2]
        
        # 添加常数项
        A_with_intercept = np.hstack([A, np.ones((A.shape[0], 1))])
        
        # 求解
        coefficients, _, _, _ = np.linalg.lstsq(A_with_intercept, B, rcond=None)
        
        # 转换为平面方程形式
        a, b, c = -coefficients[0], -coefficients[1], 1.0
        d = -coefficients[2]
        
        # 归一化
        norm = np.sqrt(a**2 + b**2 + c**2)
        plane_model = np.array([a/norm, b/norm, c/norm, d/norm])
        
        return plane_model
    
    def remove_ground(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """
        移除地面点，只保留非地面点
        
        Args:
            cloud: 输入点云
            
        Returns:
            非地面点云
        """
        _, non_ground = self.segment(cloud)
        return non_ground


class ProgressiveMorphologicalFilter:
    """
    渐进形态学滤波器
   适用于地形起伏较大的场景
    """
    
    def __init__(
        self,
        max_window_size: float = 2.0,
        slope: float = 1.0,
        initial_distance: float = 0.5,
    ):
        """
        初始化渐进形态学滤波器
        
        Args:
            max_window_size: 最大窗口尺寸（米）
            slope: 坡度参数
            initial_distance: 初始距离阈值
        """
        self.max_window_size = max_window_size
        self.slope = slope
        self.initial_distance = initial_distance
        
        logger.info(f"ProgressiveMorphologicalFilter 初始化")
    
    def apply(self, cloud: o3d.geometry.PointCloud) -> Tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud]:
        """
        应用渐进形态学滤波
        
        注意：这是一个简化实现，生产环境建议使用 PCL 的完整实现
        
        Args:
            cloud: 输入点云
            
        Returns:
            (地面点云，非地面点云)
        """
        logger.warning("ProgressiveMorphologicalFilter 是简化实现，建议使用 RANSAC 方法")
        
        # 简化实现：退化为 RANSAC
        segmenter = GroundSegmenter(
            distance_threshold=self.initial_distance,
            num_iterations=200
        )
        
        return segmenter.segment(cloud)


def create_segmenter(method: str = 'ransac', **kwargs):
    """
    工厂函数：创建地面分割器
    
    Args:
        method: 分割方法 ('ransac', 'pmf')
        **kwargs: 分割器参数
        
    Returns:
        分割器实例
    """
    if method == 'ransac':
        return GroundSegmenter(**kwargs)
    elif method == 'pmf':
        return ProgressiveMorphologicalFilter(**kwargs)
    else:
        raise ValueError(f"未知的分割方法：{method}")


# 测试代码
if __name__ == "__main__":
    # 创建模拟地面点云
    x = np.linspace(-5, 5, 100)
    y = np.linspace(-5, 5, 100)
    X, Y = np.meshgrid(x, y)
    Z = np.zeros_like(X)  # 水平地面
    
    # 添加一些噪声
    Z += np.random.normal(0, 0.02, Z.shape)
    
    # 添加一些"物体"（非地面点）
    object_points = np.random.rand(500, 3)
    object_points[:, 2] += 0.5  # 抬高 0.5 米
    
    # 合并点云
    ground_points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    all_points = np.vstack([ground_points, object_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    print(f"原始点云：{len(pcd.points)} 个点")
    
    # 测试地面分割
    segmenter = GroundSegmenter(distance_threshold=0.05)
    ground, non_ground = segmenter.segment(pcd)
    
    print(f"地面点云：{len(ground.points)} 个点")
    print(f"非地面点云：{len(non_ground.points)} 个点")
    
    # 可视化
    ground.paint_uniform_color([0, 1, 0])  # 绿色
    non_ground.paint_uniform_color([1, 0, 0])  # 红色
    
    o3d.visualization.draw_geometries([ground, non_ground])
