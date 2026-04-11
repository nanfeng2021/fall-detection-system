#!/usr/bin/env python3
"""
人体聚类模块
从点云中识别和分割出独立的人体簇
提供多种聚类算法：欧式聚类、DBSCAN、欧几里得聚类等
"""

import numpy as np
import open3d as o3d
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class HumanCluster:
    """人体簇数据结构"""
    id: int                      # 簇 ID
    point_cloud: o3d.geometry.PointCloud  # 点云数据
    centroid: np.ndarray         # 质心坐标 (x, y, z)
    bounding_box: o3d.geometry.AxisAlignedBoundingBox  # 包围盒
    num_points: int              # 点数
    confidence: float            # 置信度（0-1）
    
    def __post_init__(self):
        """后处理：计算质心和包围盒"""
        if self.centroid is None:
            points = np.asarray(self.point_cloud.points)
            self.centroid = points.mean(axis=0)
        
        if self.bounding_box is None:
            self.bounding_box = self.point_cloud.get_axis_aligned_bounding_box()
    
    @property
    def height(self) -> float:
        """人体高度（米）"""
        return self.bounding_box.get_extent()[2]
    
    @property
    def width(self) -> float:
        """人体宽度（米）"""
        return self.bounding_box.get_extent()[0]
    
    @property
    def depth(self) -> float:
        """人体深度（米）"""
        return self.bounding_box.get_extent()[1]
    
    @property
    def volume(self) -> float:
        """包围盒体积（立方米）"""
        extent = self.bounding_box.get_extent()
        return extent[0] * extent[1] * extent[2]
    
    def is_human_like(self, 
                      min_height: float = 0.5,
                      max_height: float = 2.5,
                      min_points: int = 50) -> bool:
        """
        判断是否像人体
        
        Args:
            min_height: 最小高度（米）
            max_height: 最大高度（米）
            min_points: 最小点数
            
        Returns:
            是否像人体
        """
        # 高度检查
        if not (min_height <= self.height <= max_height):
            return False
        
        # 点数检查
        if self.num_points < min_points:
            return False
        
        # 宽高比检查（人体通常是瘦高的）
        aspect_ratio = self.height / max(self.width, 0.1)
        if aspect_ratio < 1.5:  # 太矮胖了
            return False
        
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'centroid': self.centroid.tolist(),
            'num_points': self.num_points,
            'height': self.height,
            'width': self.width,
            'depth': self.depth,
            'confidence': self.confidence,
            'is_human': self.is_human_like()
        }


class EuclideanClustering:
    """欧式聚类算法"""
    
    def __init__(
        self,
        cluster_tolerance: float = 0.1,
        min_cluster_size: int = 50,
        max_cluster_size: int = 5000,
    ):
        """
        初始化欧式聚类器
        
        Args:
            cluster_tolerance: 聚类半径阈值（米），同一簇内点的最大距离
            min_cluster_size: 最小簇点数
            max_cluster_size: 最大簇点数
        """
        self.cluster_tolerance = cluster_tolerance
        self.min_cluster_size = min_cluster_size
        self.max_cluster_size = max_cluster_size
        
        logger.info(f"EuclideanClustering 初始化："
                   f"tolerance={cluster_tolerance}, "
                   f"min_size={min_cluster_size}, max_size={max_cluster_size}")
    
    def cluster(self, cloud: o3d.geometry.PointCloud) -> List[HumanCluster]:
        """
        执行欧式聚类
        
        Args:
            cloud: 输入点云（应该是非地面点）
            
        Returns:
            人体簇列表
        """
        logger.debug(f"执行欧式聚类，输入点数：{len(cloud.points)}")
        
        # Open3D 的 DBSCAN 实现（基于欧式距离）
        labels = np.array(cloud.cluster_dbscan(
            eps=self.cluster_tolerance,
            min_points=self.min_cluster_size,
            print_progress=False
        ))
        
        if len(labels) == 0:
            logger.warning("聚类结果为空")
            return []
        
        # 按标签分组
        unique_labels = np.unique(labels)
        clusters = []
        
        for label in unique_labels:
            if label == -1:  # -1 表示噪声点
                continue
            
            # 提取当前簇的点
            cluster_indices = np.where(labels == label)[0]
            
            # 检查点数是否在合理范围内
            if not (self.min_cluster_size <= len(cluster_indices) <= self.max_cluster_size):
                continue
            
            # 创建簇点云
            cluster_cloud = cloud.select_by_index(cluster_indices.tolist())
            
            # 创建人体簇对象
            human_cluster = HumanCluster(
                id=int(label),
                point_cloud=cluster_cloud,
                centroid=None,  # 会在 __post_init__ 中计算
                bounding_box=None,  # 会在 __post_init__ 中计算
                num_points=len(cluster_indices),
                confidence=1.0  # 初始置信度
            )
            
            # 更新置信度
            human_cluster.confidence = self._calculate_confidence(human_cluster)
            
            clusters.append(human_cluster)
        
        logger.info(f"欧式聚类完成：检测到 {len(clusters)} 个人体簇")
        return clusters
    
    def _calculate_confidence(self, cluster: HumanCluster) -> float:
        """
        计算簇的置信度（是否真的是人体）
        
        Args:
            cluster: 人体簇
            
        Returns:
            置信度（0-1）
        """
        confidence = 1.0
        
        # 高度评分（理想身高 1.6-1.8 米）
        if 1.5 <= cluster.height <= 1.9:
            confidence *= 1.0
        elif 1.2 <= cluster.height <= 2.2:
            confidence *= 0.8
        else:
            confidence *= 0.5
        
        # 点数评分
        if 500 <= cluster.num_points <= 2000:
            confidence *= 1.0
        elif 200 <= cluster.num_points <= 3000:
            confidence *= 0.8
        else:
            confidence *= 0.6
        
        # 宽高比评分
        aspect_ratio = cluster.height / max(cluster.width, 0.1)
        if 2.0 <= aspect_ratio <= 4.0:
            confidence *= 1.0
        elif 1.5 <= aspect_ratio <= 5.0:
            confidence *= 0.8
        else:
            confidence *= 0.6
        
        return min(confidence, 1.0)


class DBSCANClustering:
    """DBSCAN 聚类算法（更通用）"""
    
    def __init__(
        self,
        eps: float = 0.15,
        min_samples: int = 30,
        metric: str = 'euclidean',
    ):
        """
        初始化 DBSCAN 聚类器
        
        Args:
            eps: 邻域半径（米）
            min_samples: 核心点最小样本数
            metric: 距离度量 ('euclidean', 'manhattan')
        """
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
        
        logger.info(f"DBSCANClustering 初始化：eps={eps}, min_samples={min_samples}")
    
    def cluster(self, cloud: o3d.geometry.PointCloud) -> List[HumanCluster]:
        """
        执行 DBSCAN 聚类
        
        Args:
            cloud: 输入点云
            
        Returns:
            人体簇列表
        """
        logger.debug(f"执行 DBSCAN 聚类，输入点数：{len(cloud.points)}")
        
        # 转换为 numpy 数组
        points = np.asarray(cloud.points)
        
        if len(points) < self.min_samples:
            logger.warning(f"点数太少 ({len(points)})，无法进行 DBSCAN 聚类")
            return []
        
        # 使用 sklearn 的 DBSCAN（如果安装的话）
        try:
            from sklearn.cluster import DBSCAN as SKLearnDBSCAN
            
            db = SKLearnDBSCAN(
                eps=self.eps,
                min_samples=self.min_samples,
                metric=self.metric
            )
            labels = db.fit_predict(points)
            
        except ImportError:
            # 降级到 Open3D 的实现
            logger.info("sklearn 未安装，降级到 Open3D DBSCAN")
            labels = np.array(cloud.cluster_dbscan(
                eps=self.eps,
                min_points=self.min_samples,
                print_progress=False
            ))
        
        # 处理结果
        clusters = self._process_labels(cloud, labels)
        logger.info(f"DBSCAN 聚类完成：检测到 {len(clusters)} 个人体簇")
        
        return clusters
    
    def _process_labels(self, cloud: o3d.geometry.PointCloud, labels: np.ndarray) -> List[HumanCluster]:
        """处理聚类标签，生成人体簇"""
        unique_labels = np.unique(labels)
        clusters = []
        
        for label in unique_labels:
            if label == -1:  # 噪声点
                continue
            
            cluster_indices = np.where(labels == label)[0]
            
            if len(cluster_indices) < 30:  # 太小的簇忽略
                continue
            
            cluster_cloud = cloud.select_by_index(cluster_indices.tolist())
            
            human_cluster = HumanCluster(
                id=int(label),
                point_cloud=cluster_cloud,
                centroid=None,
                bounding_box=None,
                num_points=len(cluster_indices),
                confidence=0.8  # DBSCAN 的默认置信度
            )
            
            clusters.append(human_cluster)
        
        return clusters


class MultiViewClustering:
    """多视角聚类（融合多个相机的数据）"""
    
    def __init__(self, base_clusterer: EuclideanClustering):
        """
        初始化多视角聚类器
        
        Args:
            base_clusterer: 基础聚类器
        """
        self.base_clusterer = base_clusterer
        logger.info("MultiViewClustering 初始化")
    
    def cluster_from_multiple_views(
        self,
        clouds: List[o3d.geometry.PointCloud],
        transforms: List[np.ndarray]
    ) -> List[HumanCluster]:
        """
        从多个视角的点云中聚类并融合
        
        Args:
            clouds: 多个视角的点云列表
            transforms: 每个视角到世界坐标系的变换矩阵
            
        Returns:
            融合后的人体簇列表
        """
        logger.info(f"执行多视角聚类，视角数量：{len(clouds)}")
        
        # 将所有点云转换到世界坐标系并合并
        merged_points = []
        
        for i, (cloud, transform) in enumerate(zip(clouds, transforms)):
            # 变换点云
            transformed_cloud = cloud.transform(transform)
            points = np.asarray(transformed_cloud.points)
            merged_points.append(points)
            
            logger.debug(f"视角 {i}: {len(points)} 个点")
        
        # 合并所有点
        all_points = np.vstack(merged_points)
        merged_cloud = o3d.geometry.PointCloud()
        merged_cloud.points = o3d.utility.Vector3dVector(all_points)
        
        logger.info(f"合并后总点数：{len(all_points)}")
        
        # 执行聚类
        clusters = self.base_clusterer.cluster(merged_cloud)
        
        return clusters


def create_clusterer(method: str = 'euclidean', **kwargs):
    """
    工厂函数：创建聚类器
    
    Args:
        method: 聚类方法 ('euclidean', 'dbscan', 'multiview')
        **kwargs: 聚类器参数
        
    Returns:
        聚类器实例
    """
    if method == 'euclidean':
        return EuclideanClustering(**kwargs)
    elif method == 'dbscan':
        return DBSCANClustering(**kwargs)
    elif method == 'multiview':
        base_clusterer = EuclideanClustering(
            cluster_tolerance=kwargs.pop('cluster_tolerance', 0.1),
            min_cluster_size=kwargs.pop('min_cluster_size', 50),
            max_cluster_size=kwargs.pop('max_cluster_size', 5000),
        )
        return MultiViewClustering(base_clusterer)
    else:
        raise ValueError(f"未知的聚类方法：{method}")


def visualize_clusters(clusters: List[HumanCluster], show_bbox: bool = True):
    """
    可视化聚类结果
    
    Args:
        clusters: 人体簇列表
        show_bbox: 是否显示包围盒
    """
    import open3d as o3d
    
    geometries = []
    
    # 为每个簇分配不同颜色
    colors = [
        [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0],
        [1, 0, 1], [0, 1, 1], [1, 0.5, 0], [0.5, 1, 0],
    ]
    
    for i, cluster in enumerate(clusters):
        color = colors[i % len(colors)]
        cluster.point_cloud.paint_uniform_color(color)
        geometries.append(cluster.point_cloud)
        
        # 添加包围盒
        if show_bbox:
            bbox = cluster.bounding_box
            bbox_lines = bbox.get_box_lines()
            geometries.extend(bbox_lines)
        
        # 打印信息
        print(f"簇 {cluster.id}: "
              f"{cluster.num_points} 个点，"
              f"高度={cluster.height:.2f}m，"
              f"置信度={cluster.confidence:.2f}, "
              f"质心={cluster.centroid}")
    
    # 显示
    o3d.visualization.draw_geometries(geometries)


# 测试代码
if __name__ == "__main__":
    print("🧪 测试人体聚类模块...")
    
    # 创建模拟点云（几个人体形状的簇）
    np.random.seed(42)
    
    # 模拟 3 个"人体"簇
    all_points = []
    
    # 第一个人：位置 (0, 0, 0)，高度 1.7m
    person1 = np.random.rand(500, 3) * [0.3, 0.3, 1.7] + [0, 0, 0.85]
    all_points.append(person1)
    
    # 第二个人：位置 (2, 0, 0)，高度 1.6m
    person2 = np.random.rand(400, 3) * [0.3, 0.3, 1.6] + [2, 0, 0.8]
    all_points.append(person2)
    
    # 第三个人：位置 (-2, 0, 0)，高度 1.8m
    person3 = np.random.rand(600, 3) * [0.3, 0.3, 1.8] + [-2, 0, 0.9]
    all_points.append(person3)
    
    # 合并所有点
    all_points = np.vstack(all_points)
    
    # 创建点云
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    print(f"创建测试点云：{len(pcd.points)} 个点")
    
    # 执行聚类
    clusterer = EuclideanClustering(
        cluster_tolerance=0.2,
        min_cluster_size=50,
        max_cluster_size=5000
    )
    
    clusters = clusterer.cluster(pcd)
    
    print(f"\n检测到 {len(clusters)} 个人体簇:")
    for cluster in clusters:
        is_human = cluster.is_human_like()
        print(f"  簇 {cluster.id}: "
              f"{cluster.num_points} 点，"
              f"高度={cluster.height:.2f}m，"
              f"置信度={cluster.confidence:.2f}, "
              f"是人体：{is_human}")
    
    # 可视化
    print("\n🎨 可视化聚类结果...")
    visualize_clusters(clusters, show_bbox=True)
    
    print("\n✅ 测试完成！")
