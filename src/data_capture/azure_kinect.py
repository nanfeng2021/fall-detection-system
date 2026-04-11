#!/usr/bin/env python3
"""
Azure Kinect DK 数据采集模块
封装微软 Azure Kinect 相机 SDK，提供简单易用的接口

功能:
- 实时点云采集
- 深度图捕获
- 彩色图捕获（可选）
- 点云保存
- 多帧录制
"""

import numpy as np
import open3d as o3d
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from pathlib import Path
import time
from loguru import logger

# 尝试导入 pyk4a，如果未安装则提供友好的错误提示
try:
    from pyk4a import PyK4A, Config, ColorResolution, DepthMode, WiredSyncMode
    from pyk4a.results import Result
    PYK4A_AVAILABLE = True
except ImportError:
    PYK4A_AVAILABLE = False
    logger.warning("pyk4a 未安装，请先运行：pip install pyk4a")


@dataclass
class CaptureResult:
    """单次捕获结果"""
    timestamp: float                  # 时间戳
    depth_image: Optional[np.ndarray]  # 深度图 (H, W)
    point_cloud: Optional[o3d.geometry.PointCloud]  # 点云
    color_image: Optional[np.ndarray]  # 彩色图 (H, W, 3)
    num_points: int                   # 点数
    
    @property
    def has_point_cloud(self) -> bool:
        """是否有点云数据"""
        return self.point_cloud is not None and len(self.point_cloud.points) > 0


class AzureKinectCamera:
    """Azure Kinect DK 相机封装"""
    
    def __init__(
        self,
        device_id: int = 0,
        depth_mode: str = 'nfov_unbinned',
        color_resolution: str = 'off',
        fps: int = 30,
        synchronized_images_only: bool = True,
    ):
        """
        初始化 Azure Kinect 相机
        
        Args:
            device_id: 设备 ID（多相机时使用）
            depth_mode: 深度模式
                - 'nfov_unbinned': 窄视场，高分辨率（推荐）
                - 'wfov_unbinned': 宽视场，高分辨率
                - 'nfov_binned': 窄视场，低分辨率
                - 'passive_ir': 被动红外
            color_resolution: 彩色分辨率
                - 'off': 关闭彩色相机
                - '720p': 1280x720
                - '1080p': 1920x1080
                - '1440p': 2560x1440
                - '1536p': 2048x1536
                - '2160p': 3840x2160
                - '3072p': 4096x3072
            fps: 帧率 (5, 15, 或 30)
            synchronized_images_only: 只获取同步的深度和彩色图
        """
        if not PYK4A_AVAILABLE:
            raise ImportError(
                "pyk4a 未安装！\n"
                "请运行以下命令安装：\n"
                "  pip install pyk4a\n"
                "\n"
                "或者等硬件到货后再安装。"
            )
        
        self.device_id = device_id
        self.depth_mode_str = depth_mode
        self.color_resolution_str = color_resolution
        self.fps = fps
        
        # 映射字符串到 pyk4a 枚举
        depth_mode_map = {
            'nfov_unbinned': DepthMode.NFOV_UNBINNED,
            'wfov_unbinned': DepthMode.WFOV_UNBINNED,
            'nfov_binned': DepthMode.NFOV_BINNED,
            'passive_ir': DepthMode.PASSIVE_IR,
        }
        
        color_resolution_map = {
            'off': ColorResolution.OFF,
            '720p': ColorResolution.RES720P,
            '1080p': ColorResolution.RES1080P,
            '1440p': ColorResolution.RES1440P,
            '1536p': ColorResolution.RES1536P,
            '2160p': ColorResolution.RES2160P,
            '3072p': ColorResolution.RES3072P,
        }
        
        self.depth_mode = depth_mode_map.get(depth_mode, DepthMode.NFOV_UNBINNED)
        self.color_resolution = color_resolution_map.get(color_resolution, ColorResolution.OFF)
        
        # 创建配置
        self.config = Config(
            color_resolution=self.color_resolution,
            depth_mode=self.depth_mode,
            synchronized_images_only=synchronized_images_only,
            camera_fps=self._get_fps_enum(fps),
            wired_sync_mode=WiredSyncMode.STANDALONE,
        )
        
        # 相机实例
        self.k4a: Optional[PyK4A] = None
        self.is_connected = False
        
        # 统计信息
        self.frame_count = 0
        self.start_time: Optional[float] = None
        
        logger.info(f"AzureKinectCamera 初始化："
                   f"device_id={device_id}, depth_mode={depth_mode}, "
                   f"color_resolution={color_resolution}, fps={fps}")
    
    def _get_fps_enum(self, fps: int):
        """获取 FPS 枚举值"""
        try:
            from pyk4a import FPS
            if fps == 5:
                return FPS.FPS_5
            elif fps == 15:
                return FPS.FPS_15
            elif fps == 30:
                return FPS.FPS_30
            else:
                logger.warning(f"不支持的 FPS: {fps}，使用默认值 30")
                return FPS.FPS_30
        except Exception:
            # 如果导入失败，使用默认值
            return FPS.FPS_30
    
    def connect(self) -> bool:
        """
        连接相机
        
        Returns:
            是否连接成功
        """
        logger.info(f"正在连接 Azure Kinect 设备 {self.device_id}...")
        
        try:
            self.k4a = PyK4A(config=self.config, device_id=self.device_id)
            result = self.k4a.connect()
            
            if result == Result.Success:
                self.is_connected = True
                self.start_time = time.time()
                logger.info("✅ Azure Kinect 连接成功！")
                
                # 打印相机信息
                self._print_device_info()
                return True
            else:
                logger.error(f"❌ 连接失败：{result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 连接异常：{e}")
            logger.error("请检查：\n"
                        "1. 相机是否正确连接\n"
                        "2. USB 线是否是 USB 3.0\n"
                        "3. 驱动程序是否已安装\n"
                        "4. 是否有其他程序占用相机")
            return False
    
    def disconnect(self):
        """断开相机连接"""
        if self.k4a and self.is_connected:
            self.k4a.disconnect()
            self.is_connected = False
            logger.info("Azure Kinect 已断开连接")
    
    def _print_device_info(self):
        """打印设备信息"""
        if not self.k4a:
            return
        
        try:
            # 获取校准信息
            calibration = self.k4a.calibration
            
            logger.info(f"设备信息:")
            logger.info(f"  深度分辨率：{calibration.depth_camera_calibration.resolution_x} x "
                       f"{calibration.depth_camera_calibration.resolution_y}")
            
            if self.color_resolution != ColorResolution.OFF:
                logger.info(f"  彩色分辨率：{calibration.color_camera_calibration.resolution_x} x "
                           f"{calibration.color_camera_calibration.resolution_y}")
            
            logger.info(f"  FPS: {self.fps}")
            logger.info(f"  深度模式：{self.depth_mode_str}")
            
        except Exception as e:
            logger.debug(f"无法获取详细设备信息：{e}")
    
    def get_capture(self, timeout_ms: int = 1000) -> CaptureResult:
        """
        捕获单帧
        
        Args:
            timeout_ms: 超时时间（毫秒）
            
        Returns:
            捕获结果
        """
        if not self.is_connected or not self.k4a:
            logger.error("相机未连接，请先调用 connect()")
            return CaptureResult(
                timestamp=time.time(),
                depth_image=None,
                point_cloud=None,
                color_image=None,
                num_points=0
            )
        
        try:
            # 获取捕获数据
            capture = self.k4a.get_capture(timeout_ms=timeout_ms)
            
            timestamp = time.time()
            depth_image = None
            color_image = None
            point_cloud = None
            num_points = 0
            
            # 提取深度图
            if capture.depth is not None:
                depth_image = capture.depth
                logger.debug(f"深度图：{depth_image.shape}")
            
            # 提取彩色图
            if capture.color is not None:
                color_image = capture.color
                logger.debug(f"彩色图：{color_image.shape}")
            
            # 生成点云（从深度图）
            if depth_image is not None:
                point_cloud = self._depth_to_point_cloud(depth_image, timestamp)
                num_points = len(point_cloud.points) if point_cloud else 0
            
            # 更新统计
            self.frame_count += 1
            
            result = CaptureResult(
                timestamp=timestamp,
                depth_image=depth_image,
                point_cloud=point_cloud,
                color_image=color_image,
                num_points=num_points
            )
            
            logger.debug(f"Frame {self.frame_count}: {num_points} 个点")
            return result
            
        except Exception as e:
            logger.error(f"捕获失败：{e}")
            return CaptureResult(
                timestamp=time.time(),
                depth_image=None,
                point_cloud=None,
                color_image=None,
                num_points=0
            )
    
    def _depth_to_point_cloud(self, depth_image: np.ndarray, timestamp: float) -> o3d.geometry.PointCloud:
        """
        将深度图转换为点云
        
        Args:
            depth_image: 深度图 (H, W)
            timestamp: 时间戳
            
        Returns:
            点云对象
        """
        try:
            # 使用 Open3D 的 RGBD 图像转换
            height, width = depth_image.shape
            
            # 创建深度图像（归一化到米）
            depth_o3d = o3d.geometry.Image(depth_image.astype(np.float32) / 1000.0)
            
            # 创建伪彩色图像（全黑，因为我们只需要深度）
            color_o3d = o3d.geometry.Image(np.zeros((height, width, 3), dtype=np.uint8))
            
            # 创建 RGBD 图像
            rgbd_image = o3d.geometry.RGBDImage.create_from_depth_and_color(
                depth_o3d, color_o3d,
                convert_rgb_to_intensity=False
            )
            
            # 使用针孔相机模型生成点云
            # Azure Kinect 的内参（近似值）
            fx = 524.5  # 焦距 X
            fy = 524.5  # 焦距 Y
            cx = width / 2  # 主点 X
            cy = height / 2  # 主点 Y
            
            pinhole_camera_intrinsic = o3d.camera.PinholeCameraIntrinsic(
                width, height, fx, fy, cx, cy
            )
            
            pcd = o3d.geometry.PointCloud.create_from_rgbd_image(
                rgbd_image,
                pinhole_camera_intrinsic
            )
            
            # 移除无效点（深度为 0 的点）
            valid_indices = []
            points = np.asarray(pcd.points)
            for i, point in enumerate(points):
                if not np.any(np.isnan(point)) and not np.any(np.isinf(point)):
                    if np.linalg.norm(point) > 0.1:  # 距离相机至少 10cm
                        valid_indices.append(i)
            
            if valid_indices:
                pcd = pcd.select_by_index(valid_indices)
            
            return pcd
            
        except Exception as e:
            logger.error(f"深度图转点云失败：{e}")
            return o3d.geometry.PointCloud()
    
    def capture_continuous(self, duration_seconds: float = 10.0) -> List[CaptureResult]:
        """
        连续捕获多帧
        
        Args:
            duration_seconds: 捕获时长（秒）
            
        Returns:
            捕获结果列表
        """
        logger.info(f"开始连续捕获，时长：{duration_seconds}秒")
        
        results = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                result = self.get_capture()
                if result.has_point_cloud:
                    results.append(result)
                
                # 控制帧率
                time.sleep(1.0 / self.fps)
            
            logger.info(f"连续捕获完成，共 {len(results)} 帧有效数据")
            return results
            
        except KeyboardInterrupt:
            logger.info("用户中断捕获")
            return results
    
    def save_point_cloud(self, pcd: o3d.geometry.PointCloud, filepath: str):
        """
        保存点云到文件
        
        Args:
            pcd: 点云对象
            filepath: 文件路径（.ply 或 .pcd）
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if filepath.suffix.lower() == '.ply':
            o3d.io.write_point_cloud(str(filepath), pcd)
        elif filepath.suffix.lower() == '.pcd':
            o3d.io.write_point_cloud(str(filepath), pcd)
        else:
            # 默认保存为 PLY
            filepath = filepath.with_suffix('.ply')
            o3d.io.write_point_cloud(str(filepath), pcd)
        
        logger.info(f"点云已保存：{filepath} ({len(pcd.points)} 个点)")
    
    def record(self, output_dir: str, duration_seconds: float = 60.0, prefix: str = 'frame'):
        """
        录制点云序列并保存
        
        Args:
            output_dir: 输出目录
            duration_seconds: 录制时长（秒）
            prefix: 文件名前缀
        """
        logger.info(f"开始录制，输出目录：{output_dir}, 时长：{duration_seconds}秒")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = self.capture_continuous(duration_seconds)
        
        # 保存每一帧
        saved_files = []
        for i, result in enumerate(results):
            if result.has_point_cloud:
                filename = f"{prefix}_{i:04d}.ply"
                filepath = output_path / filename
                self.save_point_cloud(result.point_cloud, str(filepath))
                saved_files.append(str(filepath))
        
        # 保存元数据
        metadata = {
            'total_frames': len(results),
            'saved_frames': len(saved_files),
            'duration_seconds': duration_seconds,
            'fps': self.fps,
            'depth_mode': self.depth_mode_str,
            'files': saved_files
        }
        
        import json
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"录制完成：{len(saved_files)} 帧，元数据：{metadata_file}")
        return metadata
    
    def get_fps(self) -> float:
        """获取当前 FPS"""
        if not self.start_time:
            return 0.0
        
        elapsed = time.time() - self.start_time
        if elapsed <= 0:
            return 0.0
        
        return self.frame_count / elapsed
    
    def __enter__(self):
        """上下文管理器：进入"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器：退出"""
        self.disconnect()


def create_camera(**kwargs) -> AzureKinectCamera:
    """
    工厂函数：创建相机实例
    
    Args:
        **kwargs: 相机参数
        
    Returns:
        AzureKinectCamera 实例
    """
    return AzureKinectCamera(**kwargs)


# 测试代码（模拟模式，无需硬件）
if __name__ == "__main__":
    print("🧪 测试 Azure Kinect 数据采集模块...")
    
    if not PYK4A_AVAILABLE:
        print("\n⚠️  pyk4a 未安装，跳过实际测试")
        print("\n安装方法:")
        print("  pip install pyk4a")
        print("\n或者等硬件到货后再测试")
    else:
        print("\n📷 连接真实设备测试...")
        
        # 创建相机实例
        camera = AzureKinectCamera(
            depth_mode='nfov_unbinned',
            color_resolution='off',
            fps=30
        )
        
        # 连接
        if not camera.connect():
            print("\n❌ 连接失败，请检查设备")
            print("\n常见问题:")
            print("1. 相机是否正确连接")
            print("2. USB 线是否是 USB 3.0")
            print("3. 驱动程序是否已安装")
            print("4. 是否有其他程序占用相机")
        else:
            print("\n✅ 连接成功！开始捕获...")
            
            # 捕获单帧
            result = camera.get_capture()
            
            if result.has_point_cloud:
                print(f"\n📊 捕获成功:")
                print(f"  点数：{result.num_points}")
                print(f"  时间戳：{result.timestamp}")
                
                # 保存点云
                camera.save_point_cloud(result.point_cloud, "test_capture.ply")
                print("\n✅ 点云已保存：test_capture.ply")
                
                # 可视化
                print("\n🎨 打开可视化窗口...")
                o3d.visualization.draw_geometries([result.point_cloud])
            else:
                print("\n❌ 捕获失败，没有点云数据")
            
            # 断开连接
            camera.disconnect()
            print("\n✅ 测试完成！")
    
    print("\n💡 提示:")
    print("  - 确保 Azure Kinect 已正确连接")
    print("  - 使用 USB 3.0 线缆")
    print("  - 运行 'pip install pyk4a' 安装驱动")
    print("  - 查看文档：https://github.com/etiennedub/pyk4a")
