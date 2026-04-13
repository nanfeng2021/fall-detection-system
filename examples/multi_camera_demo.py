#!/usr/bin/env python3
"""
多摄像头监控演示脚本

展示如何配置和使用多摄像头系统
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.camera.multi_camera_manager import (
    get_camera_manager,
    CameraConfig,
    CameraType
)


def demo_basic_usage():
    """基础使用示例"""
    print("📹 多摄像头监控演示")
    print("=" * 50)
    
    # 获取摄像头管理器
    camera_mgr = get_camera_manager()
    
    # 示例 1: 添加 USB 摄像头
    print("\n1️⃣ 添加 USB 摄像头...")
    usb_cam = CameraConfig(
        id="usb_cam1",
        name="客厅 USB 摄像头",
        source=0,  # 第一个 USB 摄像头
        camera_type=CameraType.USB,
        width=1280,
        height=720,
        fps=30,
        location="客厅"
    )
    camera_mgr.add_camera(usb_cam)
    print(f"   ✅ 已添加：{usb_cam.name}")
    
    # 示例 2: 添加 RTSP 流（网络摄像头）
    print("\n2️⃣ 添加 RTSP 摄像头...")
    rtsp_cam = CameraConfig(
        id="rtsp_cam1",
        name="走廊 IP 摄像头",
        source="rtsp://192.168.1.100:554/stream1",  # 示例地址
        camera_type=CameraType.RTSP,
        width=1920,
        height=1080,
        fps=25,
        location="走廊"
    )
    camera_mgr.add_camera(rtsp_cam)
    print(f"   ✅ 已添加：{rtsp_cam.name}")
    
    # 示例 3: 添加 HTTP 流
    print("\n3️⃣ 添加 HTTP 流...")
    http_cam = CameraConfig(
        id="http_cam1",
        name="门口摄像头",
        source="http://192.168.1.101:8080/video",
        camera_type=CameraType.HTTP,
        width=1280,
        height=720,
        fps=30,
        location="门口"
    )
    camera_mgr.add_camera(http_cam)
    print(f"   ✅ 已添加：{http_cam.name}")
    
    # 启动所有摄像头
    print("\n🚀 启动所有摄像头...")
    camera_mgr.start_all()
    
    # 查看状态
    print("\n📊 摄像头状态:")
    all_statuses = camera_mgr.get_all_statuses()
    
    for cam_id, status in all_statuses.items():
        config = camera_mgr.get_camera_config(cam_id)
        connected = "🟢 在线" if status.is_connected else "🔴 离线"
        fps = f"{status.fps_current:.1f}" if status.is_connected else "N/A"
        
        print(f"   {config.name}: {connected}, FPS: {fps}")
        if status.error_message:
            print(f"      ⚠️ 错误：{status.error_message}")
    
    # 获取帧（示例）
    print("\n📸 获取视频帧...")
    for cam_id in camera_mgr.get_active_cameras():
        frame = camera_mgr.get_frame(cam_id)
        
        if frame is not None:
            print(f"   ✅ {cam_id}: 获取到帧，尺寸 {frame.shape}")
        else:
            print(f"   ❌ {cam_id}: 无法获取帧")
    
    # 运行 10 秒后停止
    print("\n⏱️  监控 10 秒...")
    import time
    time.sleep(10)
    
    # 停止所有摄像头
    print("\n🛑 停止所有摄像头...")
    camera_mgr.stop_all()
    
    print("\n✅ 演示完成！")


def demo_custom_callback():
    """自定义回调函数示例"""
    print("\n📹 回调函数演示")
    print("=" * 50)
    
    camera_mgr = get_camera_manager()
    
    # 定义回调函数
    def on_new_frame(frame):
        """新帧到达时的回调"""
        print(f"   📸 收到新帧：{frame.shape}")
        # 在这里可以调用摔倒检测算法
    
    # 添加摄像头
    config = CameraConfig(
        id="demo_cam",
        name="演示摄像头",
        source=0,
        camera_type=CameraType.USB
    )
    camera_mgr.add_camera(config)
    
    # 注册回调
    camera_mgr.register_callback("demo_cam", on_new_frame)
    
    print("✅ 回调已注册，新帧将自动触发处理函数")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="多摄像头监控演示")
    parser.add_argument(
        "--mode",
        choices=["basic", "callback"],
        default="basic",
        help="演示模式"
    )
    
    args = parser.parse_args()
    
    if args.mode == "basic":
        demo_basic_usage()
    elif args.mode == "callback":
        demo_custom_callback()
