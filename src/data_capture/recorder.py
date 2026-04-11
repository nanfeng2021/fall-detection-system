#!/usr/bin/env python3
"""
数据录制与回放模块
用于录制点云序列、保存数据集、以及回放已录制的数据

功能:
- 录制点云序列到文件
- 加载已录制的数据集
- 逐帧回放
- 数据集格式转换
- 数据标注支持
"""

import numpy as np
import open3d as o3d
import json
from pathlib import Path
from typing import List, Dict, Optional, Iterator, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from loguru import logger


@dataclass
class DatasetInfo:
    """数据集信息"""
    name: str                    # 数据集名称
    description: str             # 描述
    created_at: str              # 创建时间
    total_frames: int            # 总帧数
    duration_seconds: float      # 时长（秒）
    fps: float                   # 帧率
    depth_mode: str              # 深度模式
    color_resolution: str        # 彩色分辨率
    files: List[str]             # 文件列表
    metadata: Dict               # 其他元数据
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DatasetInfo':
        """从字典创建"""
        return cls(**data)


class PointCloudRecorder:
    """点云录制器"""
    
    def __init__(self, output_dir: str):
        """
        初始化录制器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.frames_dir = self.output_dir / "frames"
        self.metadata_file = self.output_dir / "metadata.json"
        
        logger.info(f"PointCloudRecorder 初始化，输出目录：{output_dir}")
    
    def start_recording(self, name: str = "recording", description: str = ""):
        """
        开始录制（创建目录结构）
        
        Args:
            name: 数据集名称
            description: 描述
        """
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建初始元数据
        self.temp_metadata = {
            'name': name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'frames': [],
            'start_time': datetime.now()
        }
        
        logger.info(f"开始录制：{name} → {self.output_dir}")
    
    def record_frame(self, point_cloud: o3d.geometry.PointCloud, 
                     frame_id: Optional[int] = None,
                     extra_data: Optional[Dict] = None) -> str:
        """
        录制单帧
        
        Args:
            point_cloud: 点云对象
            frame_id: 帧 ID（可选，默认自动生成）
            extra_data: 额外数据（如标签、注释等）
            
        Returns:
            保存的文件路径
        """
        if not hasattr(self, 'temp_metadata'):
            raise RuntimeError("请先调用 start_recording()")
        
        # 生成帧 ID
        if frame_id is None:
            frame_id = len(self.temp_metadata['frames'])
        
        # 保存点云
        filename = f"frame_{frame_id:06d}.ply"
        filepath = self.frames_dir / filename
        
        o3d.io.write_point_cloud(str(filepath), point_cloud)
        
        # 记录帧信息
        frame_info = {
            'frame_id': frame_id,
            'filename': filename,
            'num_points': len(point_cloud.points),
            'timestamp': datetime.now().isoformat(),
            'filepath': str(filepath),
            'extra_data': extra_data or {}
        }
        
        self.temp_metadata['frames'].append(frame_info)
        
        logger.debug(f"录制帧 {frame_id}: {len(point_cloud.points)} 个点")
        return str(filepath)
    
    def stop_recording(self, fps: float = 30.0) -> DatasetInfo:
        """
        停止录制并保存元数据
        
        Args:
            fps: 帧率
            
        Returns:
            数据集信息
        """
        if not hasattr(self, 'temp_metadata'):
            raise RuntimeError("未开始录制")
        
        # 计算时长
        end_time = datetime.now()
        start_time = self.temp_metadata['start_time']
        duration = (end_time - start_time).total_seconds()
        
        num_frames = len(self.temp_metadata['frames'])
        
        # 创建最终元数据
        dataset_info = DatasetInfo(
            name=self.temp_metadata['name'],
            description=self.temp_metadata.get('description', ''),
            created_at=self.temp_metadata['created_at'],
            total_frames=num_frames,
            duration_seconds=duration,
            fps=fps,
            depth_mode='nfov_unbinned',  # 默认值
            color_resolution='off',       # 默认值
            files=[f['filename'] for f in self.temp_metadata['frames']],
            metadata={
                'frames': self.temp_metadata['frames']
            }
        )
        
        # 保存元数据
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(dataset_info.to_dict(), f, indent=2, ensure_ascii=False)
        
        # 清理临时数据
        delattr(self, 'temp_metadata')
        
        logger.info(f"录制完成：{num_frames} 帧，时长 {duration:.1f}秒")
        logger.info(f"元数据已保存：{self.metadata_file}")
        
        return dataset_info
    
    def record_from_camera(self, camera, duration_seconds: float = 60.0, 
                          name: str = "recording", description: str = "") -> DatasetInfo:
        """
        直接从相机录制
        
        Args:
            camera: AzureKinectCamera 实例
            duration_seconds: 录制时长（秒）
            name: 数据集名称
            description: 描述
            
        Returns:
            数据集信息
        """
        from .azure_kinect import AzureKinectCamera
        
        self.start_recording(name, description)
        
        import time
        start_time = time.time()
        frame_count = 0
        
        try:
            while time.time() - start_time < duration_seconds:
                # 捕获帧
                result = camera.get_capture()
                
                if result.has_point_cloud:
                    self.record_frame(result.point_cloud, frame_id=frame_count)
                    frame_count += 1
                
                # 控制帧率
                time.sleep(1.0 / camera.fps)
            
            # 停止录制
            dataset_info = self.stop_recording(fps=camera.fps)
            
            logger.info(f"从相机录制完成：{frame_count} 帧")
            return dataset_info
            
        except KeyboardInterrupt:
            logger.info("用户中断录制")
            dataset_info = self.stop_recording(fps=camera.fps)
            return dataset_info


class PointCloudDataset:
    """点云数据集（用于加载和回放）"""
    
    def __init__(self, dataset_path: str):
        """
        初始化数据集
        
        Args:
            dataset_path: 数据集路径（包含 metadata.json 的目录）
        """
        self.dataset_path = Path(dataset_path)
        self.metadata_file = self.dataset_path / "metadata.json"
        self.frames_dir = self.dataset_path / "frames"
        
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"元数据文件不存在：{self.metadata_file}")
        
        # 加载元数据
        with open(self.metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.info = DatasetInfo.from_dict(data)
        self.frames_cache: Dict[int, o3d.geometry.PointCloud] = {}
        
        logger.info(f"加载数据集：{self.info.name}")
        logger.info(f"  位置：{self.dataset_path}")
        logger.info(f"  帧数：{self.info.total_frames}")
        logger.info(f"  时长：{self.info.duration_seconds:.1f}秒")
    
    def load_frame(self, frame_id: int) -> Optional[o3d.geometry.PointCloud]:
        """
        加载单帧点云
        
        Args:
            frame_id: 帧 ID
            
        Returns:
            点云对象，如果不存在则返回 None
        """
        # 检查缓存
        if frame_id in self.frames_cache:
            return self.frames_cache[frame_id]
        
        # 从文件加载
        frame_info = self.info.metadata['frames'][frame_id]
        filepath = self.frames_dir / frame_info['filename']
        
        if not filepath.exists():
            logger.warning(f"帧文件不存在：{filepath}")
            return None
        
        pcd = o3d.io.read_point_cloud(str(filepath))
        
        # 缓存
        self.frames_cache[frame_id] = pcd
        
        logger.debug(f"加载帧 {frame_id}: {len(pcd.points)} 个点")
        return pcd
    
    def iter_frames(self, batch_size: int = 1) -> Iterator[Tuple[int, o3d.geometry.PointCloud]]:
        """
        迭代所有帧
        
        Args:
            batch_size: 批次大小（暂未实现批处理）
            
        Yields:
            (frame_id, point_cloud)
        """
        for frame_id in range(self.info.total_frames):
            pcd = self.load_frame(frame_id)
            if pcd is not None:
                yield frame_id, pcd
    
    def get_frame_info(self, frame_id: int) -> Dict:
        """
        获取帧信息
        
        Args:
            frame_id: 帧 ID
            
        Returns:
            帧信息字典
        """
        if 0 <= frame_id < self.info.total_frames:
            return self.info.metadata['frames'][frame_id]
        else:
            raise IndexError(f"帧 ID 超出范围：{frame_id}")
    
    def add_annotation(self, frame_id: int, annotation: Dict):
        """
        添加标注
        
        Args:
            frame_id: 帧 ID
            annotation: 标注数据
        """
        if 0 <= frame_id < self.info.total_frames:
            frame_info = self.info.metadata['frames'][frame_id]
            frame_info['annotation'] = annotation
            
            logger.info(f"为帧 {frame_id} 添加标注")
        else:
            raise IndexError(f"帧 ID 超出范围：{frame_id}")
    
    def save_annotations(self, output_file: Optional[str] = None):
        """
        保存标注到文件
        
        Args:
            output_file: 输出文件路径（默认保存到数据集目录）
        """
        if output_file is None:
            output_file = self.dataset_path / "annotations.json"
        
        annotations = {}
        for frame_info in self.info.metadata['frames']:
            if 'annotation' in frame_info:
                annotations[frame_info['frame_id']] = frame_info['annotation']
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
        
        logger.info(f"标注已保存：{output_file}")
    
    def play(self, fps: Optional[float] = None, loop: bool = False):
        """
        播放数据集（可视化）
        
        Args:
            fps: 播放帧率（None 则使用原始帧率）
            loop: 是否循环播放
        """
        if fps is None:
            fps = self.info.fps
        
        logger.info(f"开始播放：{self.info.name} @ {fps} FPS")
        
        import time
        
        playing = True
        while playing:
            for frame_id, pcd in self.iter_frames():
                # 显示
                o3d.visualization.draw_geometries([pcd], 
                                                 window_name=f"Frame {frame_id}/{self.info.total_frames}",
                                                 width=1280, height=720)
                
                # 控制帧率
                time.sleep(1.0 / fps)
            
            if not loop:
                break
        
        logger.info("播放结束")
    
    def export_to_format(self, output_dir: str, format: str = 'pcl'):
        """
        导出为其他格式
        
        Args:
            output_dir: 输出目录
            format: 目标格式 ('pcl', 'rosbag', 'custom')
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"导出数据为 {format} 格式：{output_dir}")
        
        if format == 'pcl':
            # PCL 格式已经是 .ply，无需转换
            logger.info("PCL 格式与当前格式兼容，直接复制文件")
            # TODO: 实现文件复制
        
        elif format == 'rosbag':
            logger.warning("ROS bag 格式导出尚未实现")
            # TODO: 实现 rosbag 导出
        
        elif format == 'custom':
            # 自定义格式：保存为 numpy 数组
            for frame_id, pcd in self.iter_frames():
                points = np.asarray(pcd.points)
                np.save(output_path / f"frame_{frame_id:06d}.npy", points)
            
            logger.info(f"已导出 {self.info.total_frames} 帧为 numpy 格式")
        
        else:
            raise ValueError(f"不支持的格式：{format}")


def create_recorder(output_dir: str) -> PointCloudRecorder:
    """
    工厂函数：创建录制器
    
    Args:
        output_dir: 输出目录
        
    Returns:
        PointCloudRecorder 实例
    """
    return PointCloudRecorder(output_dir)


def load_dataset(dataset_path: str) -> PointCloudDataset:
    """
    工厂函数：加载数据集
    
    Args:
        dataset_path: 数据集路径
        
    Returns:
        PointCloudDataset 实例
    """
    return PointCloudDataset(dataset_path)


# 测试代码
if __name__ == "__main__":
    print("🧪 测试数据录制与回放模块...")
    
    # 创建模拟数据集
    print("\n1️⃣ 创建模拟数据集...")
    
    recorder = PointCloudRecorder("/tmp/test_dataset")
    recorder.start_recording(name="test_recording", description="测试数据集")
    
    # 录制一些模拟帧
    for i in range(10):
        # 创建随机点云
        points = np.random.rand(500, 3) * 2 - 1
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        # 录制
        recorder.record_frame(pcd, frame_id=i, extra_data={'label': 'test'})
    
    # 停止录制
    dataset_info = recorder.stop_recording(fps=30.0)
    
    print(f"\n✅ 数据集创建完成:")
    print(f"  名称：{dataset_info.name}")
    print(f"  帧数：{dataset_info.total_frames}")
    print(f"  位置：{dataset_info.files[0]}")
    
    # 加载数据集
    print("\n2️⃣ 加载数据集...")
    dataset = PointCloudDataset("/tmp/test_dataset")
    
    print(f"  名称：{dataset.info.name}")
    print(f"  总帧数：{dataset.info.total_frames}")
    
    # 加载单帧
    print("\n3️⃣ 加载单帧...")
    pcd = dataset.load_frame(0)
    print(f"  帧 0: {len(pcd.points)} 个点")
    
    # 迭代所有帧
    print("\n4️⃣ 迭代所有帧...")
    for frame_id, pcd in dataset.iter_frames():
        print(f"  帧 {frame_id}: {len(pcd.points)} 个点")
    
    print("\n✅ 测试完成！")
    print("\n💡 提示:")
    print("  - 数据集位置：/tmp/test_dataset")
    print("  - 可以手动查看 metadata.json")
    print("  - 使用 dataset.play() 播放数据集")
