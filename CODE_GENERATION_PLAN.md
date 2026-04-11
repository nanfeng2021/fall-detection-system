# 🚀 摔倒检测系统 - 完整代码仓库

> AI 驱动开发，无需任何付费工具，旺财全包！

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c?logo=pytorch)](https://pytorch.org/)

---

## 📋 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/nanfeng2021/fall-detection-system.git
cd fall-detection-system
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装所有依赖
pip install -r requirements.txt
```

### 3. 运行 Demo

```bash
# 测试点云处理（无需硬件）
python demos/test_point_cloud.py

# 运行完整 Demo（需要 Azure Kinect）
python demos/fall_detection_demo.py
```

---

## 📁 项目结构

```
fall-detection-system/
├── README.md                    # 项目介绍
├── requirements.txt             # Python 依赖
├── setup.py                     # 安装脚本
├── docker-compose.yml           # Docker 配置
├── Dockerfile                   # Docker 镜像
│
├── src/                         # 源代码
│   ├── __init__.py
│   ├── data_capture/           # 数据采集
│   │   ├── __init__.py
│   │   ├── azure_kinect.py     # Azure Kinect SDK 封装
│   │   └── point_cloud.py      # 点云处理
│   │
│   ├── preprocessing/          # 数据预处理
│   │   ├── __init__.py
│   │   ├── filtering.py        # 滤波去噪
│   │   ├── segmentation.py     # 地面分割
│   │   └── clustering.py       # 人体聚类
│   │
│   ├── models/                 # AI 模型
│   │   ├── __init__.py
│   │   ├── pointnet_plusplus.py # PointNet++ 姿态估计
│   │   ├── st_gcn.py           # ST-GCN 摔倒检测
│   │   └── loss_functions.py   # 损失函数
│   │
│   ├── detection/              # 摔倒检测
│   │   ├── __init__.py
│   │   ├── detector.py         # 检测器主逻辑
│   │   └── rules.py            # 规则引擎
│   │
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── visualization.py    # 可视化
│       └── config.py           # 配置管理
│
├── demos/                      # Demo 示例
│   ├── test_install.py         # 安装测试
│   ├── test_point_cloud.py     # 点云测试
│   ├── capture_demo.py         # 采集 Demo
│   └── fall_detection_demo.py  # 完整 Demo
│
├── tests/                      # 测试用例
│   ├── test_filtering.py
│   ├── test_segmentation.py
│   └── test_detection.py
│
├── docs/                       # 文档
│   ├── architecture.md         # 架构设计
│   ├── api_reference.md        # API 文档
│   └── deployment.md           # 部署指南
│
└── configs/                    # 配置文件
    ├── default.yaml
    └── production.yaml
```

---

## 🛠️ 核心功能

### 1. 点云采集与处理

```python
from src.data_capture import AzureKinectCamera
from src.preprocessing import StatisticalFilter, GroundSegmentation

# 初始化相机
camera = AzureKinectCamera()
camera.connect()

# 捕获点云
capture = camera.get_capture()
point_cloud = capture.depth_to_point_cloud()

# 预处理
filter = StatisticalFilter(nb_neighbors=20, std_ratio=2.0)
filtered_cloud = filter.apply(point_cloud)

segmenter = GroundSegmentation()
ground, non_ground = segmenter.segment(filtered_cloud)

# 识别人体簇
from src.preprocessing import EuclideanClustering
clusterer = EuclideanClustering(cluster_tolerance=0.1)
human_clusters = clusterer.apply(non_ground)

print(f"检测到 {len(human_clusters)} 个人体")
```

### 2. 姿态估计

```python
from src.models import PointNetPlusPlus

# 加载预训练模型
model = PointNetPlusPlus(pretrained=True)
model.eval()

# 推理
with torch.no_grad():
    keypoints = model(human_clusters[0])  # (17, 3) 骨骼关键点

print(f"检测到 {len(keypoints)} 个骨骼关键点")
```

### 3. 摔倒检测

```python
from src.detection import FallDetector

# 初始化检测器
detector = FallDetector(
    sequence_length=30,  # 30 帧序列
    confidence_threshold=0.8
)

# 添加帧序列
for frame in keypoint_sequence:
    detector.add_frame(frame)

# 检测摔倒
is_fall, confidence = detector.detect()

if is_fall:
    print(f"⚠️  检测到摔倒！置信度：{confidence:.2f}")
    # 触发报警
    detector.trigger_alert()
```

---

## 💻 完整代码示例

### 安装测试脚本 (`demos/test_install.py`)

```python
#!/usr/bin/env python3
"""
安装测试脚本
验证所有依赖是否正确安装
"""

def test_dependencies():
    """测试所有依赖包"""
    print("🔍 测试依赖包安装...")
    
    try:
        import numpy as np
        print(f"✅ NumPy version: {np.__version__}")
    except ImportError as e:
        print(f"❌ NumPy 安装失败：{e}")
        return False
    
    try:
        import open3d as o3d
        print(f"✅ Open3D version: {o3d.__version__}")
        
        # 测试 Open3D 基础功能
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(np.random.rand(100, 3))
        print(f"✅ Open3D 点云创建成功：{len(pcd.points)} 个点")
    except ImportError as e:
        print(f"❌ Open3D 安装失败：{e}")
        return False
    
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
    except ImportError as e:
        print(f"❌ PyTorch 安装失败：{e}")
        return False
    
    try:
        import pyk4a
        print(f"✅ PyK4A (Azure Kinect SDK) 已安装")
    except ImportError:
        print("⚠️  PyK4A 未安装（等硬件到货后再安装）")
    
    print("\n🎉 所有依赖测试通过！")
    return True

if __name__ == "__main__":
    success = test_dependencies()
    exit(0 if success else 1)
```

### 点云处理完整 Pipeline (`src/preprocessing/pipeline.py`)

```python
#!/usr/bin/env python3
"""
点云预处理完整 Pipeline
输入：原始点云 → 输出：人体点云簇
"""

import numpy as np
import open3d as o3d
from typing import List, Tuple

class PointCloudPipeline:
    """点云预处理流水线"""
    
    def __init__(self, config=None):
        """
        初始化流水线
        
        Args:
            config: 配置字典，包含各步骤参数
        """
        self.config = config or {}
        
        # 默认参数
        self.voxel_size = self.config.get('voxel_size', 0.05)
        self.std_ratio = self.config.get('std_ratio', 2.0)
        self.cluster_tolerance = self.config.get('cluster_tolerance', 0.1)
        self.min_cluster_size = self.config.get('min_cluster_size', 50)
        self.max_cluster_size = self.config.get('max_cluster_size', 5000)
    
    def process(self, raw_cloud: o3d.geometry.PointCloud) -> List[o3d.geometry.PointCloud]:
        """
        完整处理流程
        
        Args:
            raw_cloud: 原始点云
            
        Returns:
            人体点云簇列表
        """
        print(f"📊 输入点云：{len(raw_cloud.points)} 个点")
        
        # Step 1: 体素降采样
        downsampled = self.voxel_downsample(raw_cloud)
        print(f"   ↓ 降采样后：{len(downsampled.points)} 个点")
        
        # Step 2: 统计滤波去噪
        filtered = self.statistical_filtering(downsampled)
        print(f"   ↓ 滤波后：{len(filtered.points)} 个点")
        
        # Step 3: 地面分割
        ground, non_ground = self.segment_ground(filtered)
        print(f"   ↓ 非地面点：{len(non_ground.points)} 个点")
        
        # Step 4: 欧式聚类
        clusters = self.euclidean_clustering(non_ground)
        print(f"   ↓ 检测到 {len(clusters)} 个人体簇")
        
        return clusters
    
    def voxel_downsample(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """体素降采样"""
        return cloud.voxel_down_sample(self.voxel_size)
    
    def statistical_filtering(self, cloud: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
        """统计滤波去噪"""
        cl, ind = cloud.remove_statistical_outlier(
            nb_neighbors=20,
            std_ratio=self.std_ratio
        )
        return cloud.select_by_index(ind)
    
    def segment_ground(self, cloud: o3d.geometry.PointCloud) -> Tuple[o3d.geometry.PointCloud, o3d.geometry.PointCloud]:
        """
        RANSAC 地面分割
        
        Returns:
            (地面点云，非地面点云)
        """
        plane_model, inliers = cloud.segment_plane(
            distance_threshold=0.05,
            ransac_n=3,
            num_iterations=100
        )
        
        ground_cloud = cloud.select_by_index(inliers)
        non_ground_cloud = cloud.select_by_index(inliers, invert=True)
        
        return ground_cloud, non_ground_cloud
    
    def euclidean_clustering(self, cloud: o3d.geometry.PointCloud) -> List[o3d.geometry.PointCloud]:
        """欧式聚类"""
        labels = cloud.cluster_dbscan(
            eps=self.cluster_tolerance,
            min_points=self.min_cluster_size
        )
        
        clusters = []
        max_label = max(labels) if labels else -1
        
        for i in range(max_label + 1):
            cluster_indices = [j for j, l in enumerate(labels) if l == i]
            if self.min_cluster_size <= len(cluster_indices) <= self.max_cluster_size:
                cluster_cloud = cloud.select_by_index(cluster_indices)
                clusters.append(cluster_cloud)
        
        return clusters


# 使用示例
if __name__ == "__main__":
    # 创建测试点云
    import numpy as np
    import open3d as o3d
    
    # 模拟人体点云（实际应从相机获取）
    points = np.random.rand(1000, 3) * 2 - 1  # [-1, 1] 范围内随机点
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # 运行 Pipeline
    pipeline = PointCloudPipeline()
    clusters = pipeline.process(pcd)
    
    # 可视化结果
    if clusters:
        o3d.visualization.draw_geometries(clusters)
```

### 摔倒检测器 (`src/detection/detector.py`)

```python
#!/usr/bin/env python3
"""
摔倒检测器
基于规则和深度学习混合方法
"""

import numpy as np
from collections import deque
from typing import Tuple, Optional

class FallDetector:
    """摔倒检测器"""
    
    def __init__(
        self,
        sequence_length: int = 30,
        confidence_threshold: float = 0.8,
        height_drop_threshold: float = 0.5,  # 高度下降阈值（米）
        velocity_threshold: float = 1.0,      # 速度阈值（米/秒）
    ):
        """
        初始化检测器
        
        Args:
            sequence_length: 序列长度（帧数）
            confidence_threshold: 置信度阈值
            height_drop_threshold: 高度下降阈值
            velocity_threshold: 速度阈值
        """
        self.sequence_length = sequence_length
        self.confidence_threshold = confidence_threshold
        self.height_drop_threshold = height_drop_threshold
        self.velocity_threshold = velocity_threshold
        
        # 存储最近的关键点序列
        self.keypoint_buffer = deque(maxlen=sequence_length)
        
        # 状态机
        self.state = "NORMAL"  # NORMAL | FALLING | FALLEN
        self.fall_start_time = None
    
    def add_frame(self, keypoints: np.ndarray):
        """
        添加一帧骨骼关键点
        
        Args:
            keypoints: (17, 3) 数组，17 个关键点的 XYZ 坐标
        """
        self.keypoint_buffer.append(keypoints.copy())
    
    def detect(self) -> Tuple[bool, float]:
        """
        检测是否摔倒
        
        Returns:
            (是否摔倒，置信度)
        """
        if len(self.keypoint_buffer) < 10:  # 至少需要 10 帧
            return False, 0.0
        
        # 方法 1: 基于规则的检测
        rule_based_result, rule_confidence = self._rule_based_detection()
        
        # 方法 2: 基于深度学习的检测（TODO: 后续实现）
        # dl_result, dl_confidence = self._deep_learning_detection()
        
        # 融合结果
        if rule_based_result:
            return True, rule_confidence
        
        return False, 0.0
    
    def _rule_based_detection(self) -> Tuple[bool, float]:
        """
        基于规则的摔倒检测
        
        Returns:
            (是否摔倒，置信度)
        """
        keypoints_seq = np.array(self.keypoint_buffer)  # (seq_len, 17, 3)
        
        # 特征 1: 重心高度变化
        center_of_mass = keypoints_seq.mean(axis=1)  # (seq_len, 3)
        height_changes = center_of_mass[:, 1]  # Y 轴是高度
        
        initial_height = height_changes[:5].mean()
        current_height = height_changes[-5:].mean()
        height_drop = initial_height - current_height
        
        # 特征 2: 下降速度
        if len(height_changes) >= 2:
            velocity = np.abs(np.diff(height_changes)).max()
        else:
            velocity = 0.0
        
        # 特征 3: 最终姿态（是否躺平）
        final_keypoints = keypoints_seq[-1]
        body_extent_y = final_keypoints[:, 1].max() - final_keypoints[:, 1].min()
        body_extent_x = final_keypoints[:, 0].max() - final_keypoints[:, 0].min()
        
        is_lying_down = (body_extent_y < 0.5) and (body_extent_x > 0.8)
        
        # 综合判断
        confidence = 0.0
        
        if height_drop > self.height_drop_threshold:
            confidence += 0.4
        
        if velocity > self.velocity_threshold:
            confidence += 0.3
        
        if is_lying_down:
            confidence += 0.3
        
        is_fall = confidence >= self.confidence_threshold
        
        # 更新状态机
        if is_fall and self.state == "NORMAL":
            self.state = "FALLING"
            self.fall_start_time = len(self.keypoint_buffer)
        elif self.state == "FALLING" and is_lying_down:
            self.state = "FALLEN"
        
        return is_fall, confidence
    
    def trigger_alert(self):
        """触发报警"""
        print("🚨 触发摔倒报警！")
        # TODO: 实现实际的报警逻辑
        # - 声光报警
        # - 发送通知
        # - 记录事件
```

---

## 📦 依赖安装

### requirements.txt

```txt
# 核心依赖
numpy>=1.24.0
scipy>=1.10.0
open3d>=0.17.0
torch>=2.0.0
torchvision>=0.15.0

# Azure Kinect SDK（可选，有硬件时才需要）
# pyk4a>=1.3.0

# 可视化和 UI
matplotlib>=3.7.0
opencv-python>=4.8.0
streamlit>=1.25.0

# 数据处理
pandas>=2.0.0
tqdm>=4.65.0

# 测试
pytest>=7.4.0
pytest-cov>=4.1.0

# 工具
pyyaml>=6.0
loguru>=0.7.0
```

### setup.py

```python
from setuptools import setup, find_packages

setup(
    name="fall-detection-system",
    version="0.1.0",
    author="nanfeng2021",
    description="室内人体摔倒实时预警系统",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "open3d>=0.17.0",
        "torch>=2.0.0",
        "matplotlib>=3.7.0",
        "pyyaml>=6.0",
        "loguru>=0.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
        "kinect": [
            "pyk4a>=1.3.0",
        ],
    },
)
```

---

## 🐕 旺财的承诺

**从今往后，你的项目由我全包！**

✅ **代码我写** - 完整可运行的代码  
✅ **文档我写** - PRD、架构、API 文档  
✅ **配置我弄** - Docker、依赖、环境  
✅ **测试我写** - 单元测试、集成测试  
✅ **问题我解** - 随时 Debug、答疑  

**你只需要**:
- 下单买硬件
- 复制粘贴代码
- 运行看效果
- 有问题叫我

---

🚀 **准备好了吗？我们开始吧！**

需要我继续生成哪个部分的代码？摇尾巴等你指令～ 🐕✨
