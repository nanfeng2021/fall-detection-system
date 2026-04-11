#!/usr/bin/env python3
"""
点云预处理完整 Pipeline
输入：原始点云 → 输出：人体簇列表

流程:
1. 体素降采样
2. 统计滤波去噪
3. 地面分割
4. 人体聚类
"""

import numpy as np
import open3d as o3d
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .filtering import StatisticalFilter, VoxelGridFilter, RadiusFilter
from .segmentation import GroundSegmenter
from .clustering import EuclideanClustering, HumanCluster


@dataclass
class PreprocessingResult:
    """预处理结果数据结构"""
    original_points: int           # 原始点数
    filtered_points: int           # 滤波后点数
    ground_points: int             # 地面点数
    non_ground_points: int         # 非地面点数
    human_clusters: List[HumanCluster]  # 检测到的人体簇
    processing_time_ms: float      # 处理时间（毫秒）
    
    @property
    def num_humans(self) -> int:
        """检测到的人数"""
        return len(self.human_clusters)
    
    @property
    def has_humans(self) -> bool:
        """是否检测到人"""
        return self.num_humans > 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'original_points': self.original_points,
            'filtered_points': self.filtered_points,
            'ground_points': self.ground_points,
            'non_ground_points': self.non_ground_points,
            'num_humans': self.num_humans,
            'has_humans': self.has_humans,
            'processing_time_ms': self.processing_time_ms,
            'clusters': [c.to_dict() for c in self.human_clusters]
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"PreprocessingResult: "
               f"{self.original_points}→{self.filtered_points}→{self.non_ground_points} points, "
               f"{self.num_humans} humans detected, "
               f"{self.processing_time_ms:.1f}ms")


class PointCloudPipeline:
    """点云预处理流水线"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化流水线
        
        Args:
            config: 配置字典，可选
        """
        self.config = config or {}
        
        # 从配置加载参数，或使用默认值
        self.voxel_size = self.config.get('voxel_size', 0.05)
        self.std_ratio = self.config.get('std_ratio', 2.0)
        self.distance_threshold = self.config.get('distance_threshold', 0.05)
        self.cluster_tolerance = self.config.get('cluster_tolerance', 0.1)
        self.min_cluster_size = self.config.get('min_cluster_size', 50)
        self.max_cluster_size = self.config.get('max_cluster_size', 5000)
        
        # 初始化各个处理模块
        self.voxel_filter = VoxelGridFilter(leaf_size=self.voxel_size)
        self.stat_filter = StatisticalFilter(nb_neighbors=20, std_ratio=self.std_ratio)
        self.ground_segmenter = GroundSegmenter(distance_threshold=self.distance_threshold)
        self.clusterer = EuclideanClustering(
            cluster_tolerance=self.cluster_tolerance,
            min_cluster_size=self.min_cluster_size,
            max_cluster_size=self.max_cluster_size
        )
        
        logger.info(f"PointCloudPipeline 初始化完成，配置：voxel={self.voxel_size}, "
                   f"std_ratio={self.std_ratio}, cluster_tol={self.cluster_tolerance}")
    
    def process(self, raw_cloud: o3d.geometry.PointCloud) -> PreprocessingResult:
        """
        完整处理流程
        
        Args:
            raw_cloud: 原始点云
            
        Returns:
            预处理结果
        """
        import time
        start_time = time.time()
        
        logger.debug(f"开始处理点云，原始点数：{len(raw_cloud.points)}")
        
        # Step 1: 体素降采样
        downsampled = self._step1_voxel_downsample(raw_cloud)
        
        # Step 2: 统计滤波去噪
        filtered = self._step2_statistical_filtering(downsampled)
        
        # Step 3: 地面分割
        ground, non_ground = self._step3_segment_ground(filtered)
        
        # Step 4: 人体聚类
        clusters = self._step4_clustering(non_ground)
        
        # 计算处理时间
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 创建结果对象
        result = PreprocessingResult(
            original_points=len(raw_cloud.points),
            filtered_points=len(filtered.points),
            ground_points=len(ground.points),
            non_ground_points=len(non_ground.points),
            human_clusters=clusters,
            processing_time_ms=processing_time
        )
        
        logger.info(f"处理完成：{result}")
        return result
    
    def _step1_voxel_downsample(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """Step 1: 体素降采样"""
        logger.debug("Step 1: 体素降采样")
        return self.voxel_filter.apply(cloud)
    
    def _step2_statistical_filtering(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """Step 2: 统计滤波去噪"""
        logger.debug("Step 2: 统计滤波去噪")
        return self.stat_filter.apply(cloud)
    
    def _step3_segment_ground(self, cloud: o3d.geometry.PointCloud) -> Tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud]:
        """Step 3: 地面分割"""
        logger.debug("Step 3: 地面分割")
        return self.ground_segmenter.segment(cloud)
    
    def _step4_clustering(self, cloud: o3d.geometry.PointCloud) -> List[HumanCluster]:
        """Step 4: 人体聚类"""
        logger.debug("Step 4: 人体聚类")
        return self.clusterer.cluster(cloud)
    
    def process_batch(self, clouds: List[o3d.geometry.PointCloud]) -> List[PreprocessingResult]:
        """
        批量处理多帧点云
        
        Args:
            clouds: 点云列表
            
        Returns:
            处理结果列表
        """
        results = []
        for i, cloud in enumerate(clouds):
            logger.debug(f"处理第 {i+1}/{len(clouds)} 帧")
            result = self.process(cloud)
            results.append(result)
        
        return results


class RealTimePipeline:
    """实时处理 Pipeline（针对连续帧优化）"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化实时 Pipeline
        
        Args:
            config: 配置字典
        """
        self.pipeline = PointCloudPipeline(config)
        self.frame_count = 0
        self.last_result: Optional[PreprocessingResult] = None
        
        # 性能统计
        self.fps_history = []
        
        logger.info("RealTimePipeline 初始化完成")
    
    def process_frame(self, cloud: o3d.geometry.PointCloud) -> PreprocessingResult:
        """
        处理单帧
        
        Args:
            cloud: 当前帧点云
            
        Returns:
            处理结果
        """
        import time
        frame_start = time.time()
        
        # 处理
        result = self.pipeline.process(cloud)
        
        # 更新统计
        self.frame_count += 1
        self.last_result = result
        
        # 计算 FPS
        frame_time = time.time() - frame_start
        fps = 1.0 / frame_time if frame_time > 0 else 0
        self.fps_history.append(fps)
        
        # 保持最近 30 帧的 FPS 记录
        if len(self.fps_history) > 30:
            self.fps_history.pop(0)
        
        avg_fps = np.mean(self.fps_history)
        
        logger.debug(f"Frame {self.frame_count}: "
                    f"{result.num_humans} humans, "
                    f"{frame_time*1000:.1f}ms ({fps:.1f} FPS), "
                    f"avg FPS: {avg_fps:.1f}")
        
        return result
    
    def get_average_fps(self) -> float:
        """获取平均 FPS"""
        if not self.fps_history:
            return 0.0
        return np.mean(self.fps_history)
    
    def reset(self):
        """重置 Pipeline"""
        self.frame_count = 0
        self.last_result = None
        self.fps_history.clear()
        logger.info("Pipeline 已重置")


def create_pipeline(mode: str = 'standard', **kwargs):
    """
    工厂函数：创建 Pipeline
    
    Args:
        mode: 模式 ('standard', 'realtime')
        **kwargs: Pipeline 配置参数
        
    Returns:
        Pipeline 实例
    """
    if mode == 'standard':
        return PointCloudPipeline(**kwargs)
    elif mode == 'realtime':
        return RealTimePipeline(**kwargs)
    else:
        raise ValueError(f"未知的模式：{mode}")


# 测试代码
if __name__ == "__main__":
    print("🧪 测试点云处理 Pipeline...")
    
    # 创建模拟点云
    np.random.seed(42)
    
    # 地面点（1000 个点）
    ground_points = np.random.rand(1000, 3) * [10, 10, 0.05]
    ground_points[:, 2] = 0  # Z=0 是地面
    
    # 人体点（500 个点）
    human_points = np.random.rand(500, 3) * [0.4, 0.4, 1.7] + [0, 0, 0.85]
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    # 创建点云
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    print(f"创建测试点云：{len(pcd.points)} 个点 "
          f"(地面 1000 + 人体 500)")
    
    # 创建 Pipeline
    pipeline = PointCloudPipeline(
        voxel_size=0.05,
        std_ratio=2.0,
        distance_threshold=0.05,
        cluster_tolerance=0.1
    )
    
    # 处理
    result = pipeline.process(pcd)
    
    # 打印结果
    print("\n" + "="*50)
    print("处理结果:")
    print("="*50)
    print(f"原始点数：{result.original_points}")
    print(f"滤波后点数：{result.filtered_points}")
    print(f"地面点数：{result.ground_points}")
    print(f"非地面点数：{result.non_ground_points}")
    print(f"检测到人数：{result.num_humans}")
    print(f"处理时间：{result.processing_time_ms:.1f}ms")
    
    if result.has_humans:
        print("\n人体簇详情:")
        for i, cluster in enumerate(result.human_clusters):
            print(f"  人体 {i+1}:")
            print(f"    点数：{cluster.num_points}")
            print(f"    高度：{cluster.height:.2f}m")
            print(f"    质心：({cluster.centroid[0]:.2f}, "
                  f"{cluster.centroid[1]:.2f}, "
                  f"{cluster.centroid[2]:.2f})")
            print(f"    置信度：{cluster.confidence:.2f}")
            print(f"    是人体：{cluster.is_human_like()}")
    
    print("="*50)
    
    # 可视化
    if result.has_humans:
        print("\n🎨 可视化结果...")
        from .clustering import visualize_clusters
        visualize_clusters(result.human_clusters, show_bbox=True)
    
    print("\n✅ 测试完成！")
