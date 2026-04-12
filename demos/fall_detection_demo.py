#!/usr/bin/env python3
"""
摔倒检测系统完整 Demo
演示从数据采集到摔倒检测的完整流程

运行方式:
1. 有硬件：连接 Azure Kinect，实时检测
2. 无硬件：使用模拟数据测试

用法:
    # 使用模拟数据
    python demos/fall_detection_demo.py --mock
    
    # 使用真实相机
    python demos/fall_detection_demo.py --camera
    
    # 录制数据集
    python demos/fall_detection_demo.py --record --output /path/to/dataset
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
import numpy as np
import open3d as o3d

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.detection.detector import FallDetectionSystem, SystemAlert
from src.preprocessing.clustering import visualize_clusters


def create_mock_cloud(frame_id: int, is_falling: bool = False) -> o3d.geometry.PointCloud:
    """
    创建模拟点云
    
    Args:
        frame_id: 帧 ID
        is_falling: 是否模拟摔倒
        
    Returns:
        点云对象
    """
    np.random.seed(frame_id + 42)  # 固定种子保证可重复性
    
    # 地面 (800 点) - 缩小范围让人体更突出
    ground_points = np.random.rand(800, 3) * [4, 4, 0.02]
    ground_points[:, 2] = 0
    
    # 人体中心位置 (放在场景中央)
    human_center_x = 2.0
    human_center_y = 2.0
    
    # 人体 (600 点) - 更密集的圆柱体
    if is_falling:
        # 摔倒：高度降低，宽度增加，躺在地上
        progress = min(1.0, (frame_id - 50) / 10)  # 摔倒进度 0-1
        height = 1.7 - progress * 1.3  # 从 1.7m 降到 0.4m
        radius = 0.2 + progress * 0.4  # 从 0.2m 扩展到 0.6m
        
        # 生成圆柱体点云
        theta = np.random.uniform(0, 2 * np.pi, 600)
        r = np.sqrt(np.random.uniform(0, 1, 600)) * radius
        h = np.random.uniform(0, 1, 600) * height
        
        human_points = np.column_stack([
            r * np.cos(theta) + human_center_x,
            r * np.sin(theta) + human_center_y,
            h
        ])
        
        # 摔倒时逐渐放倒
        if progress > 0.5:
            tilt_angle = (progress - 0.5) * np.pi / 2  # 最多倾斜 90 度
            z_new = human_points[:, 2] * np.cos(tilt_angle)
            y_new = human_points[:, 1] + human_points[:, 2] * np.sin(tilt_angle)
            human_points[:, 2] = z_new
            human_points[:, 1] = y_new
    else:
        # 正常站立：细长的圆柱体
        height = 1.7
        radius = 0.25
        
        theta = np.random.uniform(0, 2 * np.pi, 600)
        r = np.sqrt(np.random.uniform(0, 1, 600)) * radius
        h = np.random.uniform(0, 1, 600) * height
        
        human_points = np.column_stack([
            r * np.cos(theta) + human_center_x,
            r * np.sin(theta) + human_center_y,
            h
        ])
    
    # 添加少量噪声
    noise = np.random.normal(0, 0.015, human_points.shape)
    human_points += noise
    
    # 确保人体在地面以上
    human_points[:, 2] = np.maximum(human_points[:, 2], 0.01)
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


def mock_cloud_generator(num_frames: int = 100, fall_start_frame: int = 50):
    """
    模拟点云生成器
    
    Args:
        num_frames: 总帧数
        fall_start_frame: 开始摔倒的帧
    """
    for i in range(num_frames):
        is_falling = i >= fall_start_frame
        yield create_mock_cloud(i, is_falling)


def run_mock_demo():
    """运行模拟数据 Demo"""
    print("="*60)
    print("🎬 摔倒检测系统 Demo - 模拟数据模式")
    print("="*60)
    
    # 创建报警回调
    def on_alert(alert: SystemAlert):
        timestamp = alert.timestamp.strftime("%H:%M:%S")
        print(f"\n{'🚨'*10}")
        print(f"⏰ 时间：{timestamp}")
        print(f"⚠️  类型：{alert.alert_type}")
        print(f"👤 人员：ID={alert.cluster_id}")
        print(f"📢 消息：{alert.message}")
        print(f"🎯 置信度：{alert.confidence:.0%}")
        print(f"{'🚨'*10}\n")
    
    # 创建检测系统
    system = FallDetectionSystem(
        voxel_size=0.05,
        std_ratio=2.0,
        distance_threshold=0.05,
        cluster_tolerance=0.1,
        height_drop_threshold=0.3,
        velocity_threshold=0.5,
        confirmation_frames=2,
        fps=30.0,
        alert_callback=on_alert
    )
    
    print("\n📊 系统配置:")
    print(f"  体素尺寸：0.05m")
    print(f"  高度骤降阈值：0.3m")
    print(f"  速度阈值：0.5m/s")
    print(f"  确认帧数：2")
    
    print("\n▶️  开始处理模拟数据...")
    print("(前 50 帧正常站立，后 50 帧模拟摔倒)\n")
    
    # 处理
    frame_count = 0
    alert_count = 0
    
    start_time = time.time()
    
    for result in system.process_continuous(mock_cloud_generator(100, fall_start_frame=50)):
        frame_count += 1
        
        # 每 10 帧打印一次状态
        if frame_count % 10 == 0:
            elapsed = time.time() - start_time
            fps = frame_count / elapsed if elapsed > 0 else 0
            
            print(f"📍 帧 {frame_count}/100: "
                  f"{result.num_people} 人 detected, "
                  f"{result.num_falls} falls, "
                  f"{result.processing_time_ms:.1f}ms, "
                  f"{fps:.1f} FPS")
        
        alert_count += len(result.alerts)
    
    # 最终统计
    total_time = time.time() - start_time
    stats = system.get_statistics()
    
    print("\n" + "="*60)
    print("📊 处理完成！统计信息:")
    print("="*60)
    print(f"  总帧数：{frame_count}")
    print(f"  总报警：{alert_count}")
    print(f"  总耗时：{total_time:.2f}秒")
    print(f"  平均 FPS: {stats['average_fps']:.1f}")
    print(f"  平均处理时间：{total_time/frame_count*1000:.1f}ms/帧")
    print("="*60)
    
    # 可视化最后一帧
    print("\n🎨 打开可视化窗口...")
    print("(关闭以退出程序)")
    
    # 创建一帧用于可视化
    final_cloud = create_mock_cloud(99, is_falling=True)
    o3d.visualization.draw_geometries(
        [final_cloud],
        window_name="Fall Detection Demo - Final Frame",
        width=1280,
        height=720
    )


def run_camera_demo():
    """运行真实相机 Demo"""
    print("="*60)
    print("🎬 摔倒检测系统 Demo - 真实相机模式")
    print("="*60)
    
    try:
        from src.data_capture.azure_kinect import AzureKinectCamera
    except ImportError:
        print("\n❌ pyk4a 未安装!")
        print("\n请先安装:")
        print("  pip install pyk4a")
        print("\n或者使用模拟模式:")
        print("  python demos/fall_detection_demo.py --mock")
        return
    
    # 创建报警回调
    def on_alert(alert: SystemAlert):
        timestamp = alert.timestamp.strftime("%H:%M:%S")
        print(f"\n{'🚨'*5}")
        print(f"⏰ {timestamp} - {alert.message}")
        print(f"{'🚨'*5}\n")
    
    # 创建相机
    camera = AzureKinectCamera(
        depth_mode='nfov_unbinned',
        color_resolution='off',
        fps=30
    )
    
    # 创建检测系统
    system = FallDetectionSystem(
        alert_callback=on_alert
    )
    
    # 连接相机
    print("\n📷 正在连接 Azure Kinect...")
    if not camera.connect():
        print("\n❌ 连接失败!")
        print("\n请检查:")
        print("  1. 相机是否正确连接")
        print("  2. USB 线是否是 USB 3.0")
        print("  3. 驱动程序是否已安装")
        print("  4. 是否有其他程序占用相机")
        print("\n或者使用模拟模式:")
        print("  python demos/fall_detection_demo.py --mock")
        return
    
    print("✅ 相机连接成功!")
    print("\n▶️  开始实时检测...")
    print("(按 Ctrl+C 停止)\n")
    
    # 定义生成器
    def camera_generator():
        while True:
            result = camera.get_capture()
            if result.has_point_cloud:
                yield result.point_cloud
            time.sleep(1.0 / 30)  # 控制帧率
    
    # 处理
    frame_count = 0
    try:
        for result in system.process_continuous(camera_generator()):
            frame_count += 1
            
            # 每 30 帧 (约 1 秒) 打印状态
            if frame_count % 30 == 0:
                stats = system.get_statistics()
                print(f"📍 {frame_count} 帧："
                      f"{result.num_people} 人，"
                      f"{stats['total_alerts']} 次报警，"
                      f"{stats['average_fps']:.1f} FPS")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  用户停止检测")
    
    finally:
        camera.disconnect()
        
        # 打印统计
        stats = system.get_statistics()
        print("\n" + "="*60)
        print("📊 本次运行统计:")
        print("="*60)
        print(f"  总帧数：{frame_count}")
        print(f"  总报警：{stats['total_alerts']}")
        print(f"  运行时长：{stats['uptime_seconds']:.1f}秒")
        print(f"  平均 FPS: {stats['average_fps']:.1f}")
        print("="*60)


def run_record_demo(output_dir: str, duration: int = 30):
    """运行录制 Demo"""
    print("="*60)
    print(f"🎬 摔倒检测系统 - 数据录制模式")
    print("="*60)
    
    try:
        from src.data_capture.recorder import PointCloudRecorder
        from src.data_capture.azure_kinect import AzureKinectCamera
    except ImportError:
        print("\n❌ pyk4a 未安装!")
        print("请先运行：pip install pyk4a")
        return
    
    # 创建相机和录制器
    camera = AzureKinectCamera()
    recorder = PointCloudRecorder(output_dir)
    
    # 连接相机
    print(f"\n📷 正在连接相机...")
    if not camera.connect():
        print("❌ 连接失败")
        return
    
    print("✅ 相机连接成功")
    
    # 开始录制
    print(f"\n▶️  开始录制，时长 {duration} 秒...")
    print(f"输出目录：{output_dir}")
    print("(按 Ctrl+C 提前停止)\n")
    
    try:
        dataset_info = recorder.record_from_camera(
            camera,
            duration_seconds=duration,
            name=f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="摔倒检测数据集"
        )
        
        print("\n✅ 录制完成!")
        print(f"\n📊 数据集信息:")
        print(f"  名称：{dataset_info.name}")
        print(f"  帧数：{dataset_info.total_frames}")
        print(f"  时长：{dataset_info.duration_seconds:.1f}秒")
        print(f"  位置：{output_dir}")
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断录制")
        dataset_info = recorder.stop_recording(fps=30.0)
    
    finally:
        camera.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="摔倒检测系统 Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用模拟数据
  python demos/fall_detection_demo.py --mock
  
  # 使用真实相机
  python demos/fall_detection_demo.py --camera
  
  # 录制数据集
  python demos/fall_detection_demo.py --record --output ./dataset --duration 60
        """
    )
    
    parser.add_argument('--mock', action='store_true',
                       help='使用模拟数据 (无需硬件)')
    parser.add_argument('--camera', action='store_true',
                       help='使用真实相机 (需要 Azure Kinect)')
    parser.add_argument('--record', action='store_true',
                       help='录制数据集模式')
    parser.add_argument('--output', type=str, default='./dataset',
                       help='录制输出目录 (仅 record 模式)')
    parser.add_argument('--duration', type=int, default=30,
                       help='录制时长 (秒，仅 record 模式)')
    
    args = parser.parse_args()
    
    # 默认使用模拟模式
    if not any([args.mock, args.camera, args.record]):
        args.mock = True
    
    # 运行对应模式
    if args.mock:
        run_mock_demo()
    elif args.camera:
        run_camera_demo()
    elif args.record:
        run_record_demo(args.output, args.duration)


if __name__ == "__main__":
    main()
