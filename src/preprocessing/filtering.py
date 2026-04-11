#!/usr/bin/env python3
"""
点云滤波去噪模块
提供多种滤波算法：统计滤波、半径滤波、高斯滤波等
"""

import numpy as np
import open3d as o3d
from typing import Tuple, Optional
from loguru import logger


class StatisticalFilter:
    """统计离群点滤波器"""
    
    def __init__(self, nb_neighbors: int = 20, std_ratio: float = 2.0):
        """
        初始化统计滤波器
        
        Args:
            nb_neighbors: 邻域点数
            std_ratio: 标准差倍数，超过此值的点被视为离群点
        """
        self.nb_neighbors = nb_neighbors
        self.std_ratio = std_ratio
        logger.info(f"StatisticalFilter 初始化：nb_neighbors={nb_neighbors}, std_ratio={std_ratio}")
    
    def apply(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """
        应用统计滤波
        
        Args:
            cloud: 输入点云
            
        Returns:
            滤波后的点云
        """
        logger.debug(f"应用统计滤波，输入点数：{len(cloud.points)}")
        
        cl, ind = cloud.remove_statistical_outlier(
            nb_neighbors=self.nb_neighbors,
            std_ratio=self.std_ratio
        )
        
        filtered_cloud = cloud.select_by_index(ind)
        num_removed = len(cloud.points) - len(filtered_cloud.points)
        
        logger.info(f"统计滤波完成，移除 {num_removed} 个离群点，剩余 {len(filtered_cloud.points)} 个点")
        return filtered_cloud
    
    def apply_with_indices(self, cloud: o3d.geometry.PointCloud) -> Tuple[o3d.geometry.PointCloud, np.ndarray]:
        """
        应用统计滤波并返回保留的索引
        
        Args:
            cloud: 输入点云
            
        Returns:
            (滤波后的点云，保留点的索引)
        """
        cl, ind = cloud.remove_statistical_outlier(
            nb_neighbors=self.nb_neighbors,
            std_ratio=self.std_ratio
        )
        
        filtered_cloud = cloud.select_by_index(ind)
        return filtered_cloud, np.array(ind)


class RadiusFilter:
    """半径离群点滤波器"""
    
    def __init__(self, radius: float = 0.1, min_points: int = 5):
        """
        初始化半径滤波器
        
        Args:
            radius: 搜索半径（米）
            min_points: 最小邻域点数
        """
        self.radius = radius
        self.min_points = min_points
        logger.info(f"RadiusFilter 初始化：radius={radius}, min_points={min_points}")
    
    def apply(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """
        应用半径滤波
        
        Args:
            cloud: 输入点云
            
        Returns:
            滤波后的点云
        """
        logger.debug(f"应用半径滤波，输入点数：{len(cloud.points)}")
        
        _, ind = cloud.remove_radius_outlier(
            nb_points=self.min_points,
            radius=self.radius
        )
        
        filtered_cloud = cloud.select_by_index(ind)
        num_removed = len(cloud.points) - len(filtered_cloud.points)
        
        logger.info(f"半径滤波完成，移除 {num_removed} 个离群点，剩余 {len(filtered_cloud.points)} 个点")
        return filtered_cloud


class VoxelGridFilter:
    """体素网格降采样滤波器"""
    
    def __init__(self, leaf_size: float = 0.05):
        """
        初始化体素滤波器
        
        Args:
            leaf_size: 体素边长（米）
        """
        self.leaf_size = leaf_size
        logger.info(f"VoxelGridFilter 初始化：leaf_size={leaf_size}")
    
    def apply(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """
        应用体素降采样
        
        Args:
            cloud: 输入点云
            
        Returns:
            降采样后的点云
        """
        logger.debug(f"应用体素降采样，输入点数：{len(cloud.points)}")
        
        downsampled_cloud = cloud.voxel_down_sample(self.leaf_size)
        reduction_ratio = len(downsampled_cloud.points) / max(len(cloud.points), 1)
        
        logger.info(f"体素降采样完成，点数从 {len(cloud.points)} 减少到 {len(downsampled_cloud.points)} "
                   f"(保留 {reduction_ratio:.2%})")
        return downsampled_cloud


def create_filter(filter_type: str, **kwargs):
    """
    工厂函数：创建滤波器
    
    Args:
        filter_type: 滤波器类型 ('statistical', 'radius', 'voxel')
        **kwargs: 滤波器参数
        
    Returns:
        滤波器实例
        
    Example:
        >>> filter = create_filter('statistical', nb_neighbors=20, std_ratio=2.0)
        >>> filtered_cloud = filter.apply(cloud)
    """
    if filter_type == 'statistical':
        return StatisticalFilter(**kwargs)
    elif filter_type == 'radius':
        return RadiusFilter(**kwargs)
    elif filter_type == 'voxel':
        return VoxelGridFilter(**kwargs)
    else:
        raise ValueError(f"未知的滤波器类型：{filter_type}")


# 测试代码
if __name__ == "__main__":
    # 创建测试点云
    points = np.random.rand(1000, 3)
    # 添加一些离群点
    outliers = np.random.rand(50, 3) * 10 - 5
    all_points = np.vstack([points, outliers])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    print(f"原始点云：{len(pcd.points)} 个点")
    
    # 测试统计滤波
    stat_filter = StatisticalFilter(nb_neighbors=20, std_ratio=2.0)
    filtered = stat_filter.apply(pcd)
    print(f"统计滤波后：{len(filtered.points)} 个点")
    
    # 测试体素降采样
    voxel_filter = VoxelGridFilter(leaf_size=0.1)
    downsampled = voxel_filter.apply(filtered)
    print(f"体素降采样后：{len(downsampled.points)} 个点")
