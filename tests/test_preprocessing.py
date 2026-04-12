#!/usr/bin/env python3
"""
预处理模块测试
"""

import pytest
import numpy as np
import open3d as o3d

from src.preprocessing.filtering import VoxelGridFilter, StatisticalFilter
from src.preprocessing.segmentation import GroundSegmenter
from src.preprocessing.clustering import EuclideanClustering, HumanCluster
from src.preprocessing.pipeline import PointCloudPipeline


class TestVoxelGridFilter:
    """体素滤波测试"""
    
    def test_initialization(self):
        """测试初始化"""
        filter_obj = VoxelGridFilter(leaf_size=0.05)
        assert filter_obj.leaf_size == 0.05
    
    def test_apply(self, sample_point_cloud):
        """测试滤波应用"""
        filter_obj = VoxelGridFilter(leaf_size=0.1)
        result = filter_obj.apply(sample_point_cloud)
        
        assert isinstance(result, o3d.geometry.PointCloud)
        assert len(result.points) <= len(sample_point_cloud.points)


class TestStatisticalFilter:
    """统计滤波测试"""
    
    def test_initialization(self):
        """测试初始化"""
        filter_obj = StatisticalFilter(nb_neighbors=20, std_ratio=2.0)
        assert filter_obj.nb_neighbors == 20
        assert filter_obj.std_ratio == 2.0
    
    def test_apply(self, sample_point_cloud):
        """测试滤波应用"""
        filter_obj = StatisticalFilter(nb_neighbors=10, std_ratio=1.0)
        result = filter_obj.apply(sample_point_cloud)
        
        assert isinstance(result, o3d.geometry.PointCloud)


class TestGroundSegmenter:
    """地面分割测试"""
    
    def test_initialization(self):
        """测试初始化"""
        segmenter = GroundSegmenter(distance_threshold=0.05)
        assert segmenter.distance_threshold == 0.05
    
    def test_segment(self, sample_point_cloud):
        """测试地面分割"""
        segmenter = GroundSegmenter(distance_threshold=0.1)
        ground, non_ground = segmenter.segment(sample_point_cloud)
        
        assert isinstance(ground, o3d.geometry.PointCloud)
        assert isinstance(non_ground, o3d.geometry.PointCloud)
        assert len(ground.points) + len(non_ground.points) <= len(sample_point_cloud.points)


class TestEuclideanClustering:
    """欧式聚类测试"""
    
    def test_initialization(self):
        """测试初始化"""
        clusterer = EuclideanClustering(
            cluster_tolerance=0.1,
            min_cluster_size=50,
            max_cluster_size=5000
        )
        assert clusterer.cluster_tolerance == 0.1
    
    def test_cluster(self, sample_point_cloud):
        """测试聚类"""
        # 先去除地面
        segmenter = GroundSegmenter(distance_threshold=0.1)
        _, non_ground = segmenter.segment(sample_point_cloud)
        
        clusterer = EuclideanClustering(
            cluster_tolerance=0.2,
            min_cluster_size=50,
            max_cluster_size=5000
        )
        clusters = clusterer.cluster(non_ground)
        
        assert isinstance(clusters, list)
        assert len(clusters) >= 1
        
        for cluster in clusters:
            assert isinstance(cluster, HumanCluster)
            assert cluster.num_points >= 50
    
    def test_empty_cloud(self):
        """测试空点云"""
        empty_cloud = o3d.geometry.PointCloud()
        clusterer = EuclideanClustering()
        clusters = clusterer.cluster(empty_cloud)
        
        assert clusters == []


class TestHumanCluster:
    """人体簇测试"""
    
    def test_properties(self, mock_human_cluster):
        """测试属性"""
        cluster = mock_human_cluster
        
        assert cluster.height > 0
        assert cluster.width > 0
        assert cluster.depth > 0
        assert cluster.volume > 0
        assert cluster.num_points == 500
    
    def test_is_human_like(self, mock_human_cluster):
        """测试人体判断"""
        cluster = mock_human_cluster
        
        # 应该被识别为人体
        assert cluster.is_human_like() == True
        
        # 测试不符合人体条件
        cluster.height = 0.3  # 太矮
        assert cluster.is_human_like() == False
    
    def test_to_dict(self, mock_human_cluster):
        """测试字典转换"""
        cluster = mock_human_cluster
        data = cluster.to_dict()
        
        assert 'id' in data
        assert 'height' in data
        assert 'centroid' in data
        assert isinstance(data['centroid'], list)


class TestPointCloudPipeline:
    """点云处理流水线测试"""
    
    def test_initialization(self):
        """测试初始化"""
        pipeline = PointCloudPipeline(config={
            'voxel_size': 0.05,
            'std_ratio': 2.0
        })
        
        assert pipeline.voxel_size == 0.05
        assert pipeline.std_ratio == 2.0
    
    def test_process(self, sample_point_cloud):
        """测试完整处理流程"""
        pipeline = PointCloudPipeline(config={
            'voxel_size': 0.1,
            'std_ratio': 2.0,
            'distance_threshold': 0.1,
            'cluster_tolerance': 0.2
        })
        
        result = pipeline.process(sample_point_cloud)
        
        assert result.original_points == len(sample_point_cloud.points)
        assert result.filtered_points <= result.original_points
        assert result.num_humans >= 0
        assert result.processing_time_ms > 0
    
    def test_process_batch(self, sample_point_cloud):
        """测试批量处理"""
        pipeline = PointCloudPipeline()
        
        clouds = [sample_point_cloud for _ in range(3)]
        results = pipeline.process_batch(clouds)
        
        assert len(results) == 3
        for result in results:
            assert result.num_humans >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
