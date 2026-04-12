#!/usr/bin/env python3
"""
Pytest 配置文件
提供测试固件和共享配置
"""

import pytest
import numpy as np
import open3d as o3d
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_point_cloud():
    """创建示例点云"""
    np.random.seed(42)
    
    # 地面点
    ground_points = np.random.rand(1000, 3) * [5, 5, 0.05]
    ground_points[:, 2] = 0
    
    # 人体点
    human_points = np.random.rand(500, 3) * [0.4, 0.4, 1.7]
    human_points[:, 2] += 0.85
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


@pytest.fixture
def mock_human_cluster():
    """创建模拟人体簇"""
    from src.preprocessing.clustering import HumanCluster
    
    points = np.random.rand(500, 3) * [0.4, 0.4, 1.7] + [0, 0, 0.85]
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    cluster = HumanCluster(
        id=0,
        point_cloud=pcd,
        centroid=np.array([0, 0, 0.85]),
        bounding_box=pcd.get_axis_aligned_bounding_box(),
        num_points=500,
        confidence=0.9
    )
    
    return cluster


@pytest.fixture
def temp_directory(tmp_path):
    """临时目录"""
    return tmp_path


@pytest.fixture
def mock_config():
    """模拟配置"""
    from src.utils.config import Config, SystemConfig, DetectionRulesConfig
    
    config = Config()
    config.system.debug = True
    config.system.log_level = "DEBUG"
    config.detection.rules.height_drop_threshold = 0.3
    config.detection.rules.velocity_threshold = 0.5
    config.detection.rules.confirmation_frames = 2
    
    return config


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    data_dir = Path(__file__).parent / "test_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir
