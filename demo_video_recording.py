#!/usr/bin/env python3
"""
视频录制功能演示

展示如何在摔倒检测系统中集成视频录制与回放功能
"""

import cv2
import numpy as np
from datetime import datetime
import time
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from video_recorder import VideoRecorder, RecordingManager, get_recording_manager


def simulate_camera_feed():
    """模拟摄像头输入 - 使用 OpenCV 生成测试视频"""
    
    # 创建录制管理器
    manager = get_recording_manager()
    
    # 创建窗口
    cv2.namedWindow('Fall Detection - Video Recording Demo', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Fall Detection - Video Recording Demo', 1280, 720)
    
    print("🎬 视频录制演示启动")
    print("   按 'q' 键退出")
    print("   按 'f' 键模拟跌倒事件触发录制")
    print(f"   录像保存目录：recordings/")
    
    frame_count = 0
    fps = 30
    
    while True:
        # 生成模拟帧（彩色渐变背景 + 移动的人形矩形）
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        # 渐变背景
        for i in range(720):
            frame[i, :] = [int(i * 0.3), 100, 200]
        
        # 模拟人体（移动的矩形）
        x_pos = int(640 + 300 * np.sin(frame_count * 0.05))
        y_pos = int(360 + 200 * np.cos(frame_count * 0.03))
        
        # 绘制人体
        cv2.rectangle(frame, (x_pos - 50, y_pos - 100), (x_pos + 50, y_pos + 100), (0, 255, 0), -1)
        
        # 显示信息
        cv2.putText(frame, f'Frame: {frame_count}', (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, f'FPS: {fps}', (50, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # 获取缓冲区状态
        recorder = manager.get_or_create_recorder('cam1')
        stats = recorder.get_buffer_stats()
        
        cv2.putText(frame, f'Buffer: {stats["buffer_current"]:.1f}s / {stats["buffer_capacity"]}s', 
                   (50, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f'Recordings: {stats["total_recordings"]}', 
                   (50, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 如果正在录制，显示提示
        if recorder.is_recording:
            cv2.putText(frame, '🔴 RECORDING...', (800, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            # 闪烁的红色边框
            if frame_count % 30 < 15:
                cv2.rectangle(frame, (10, 10), (1270, 710), (0, 0, 255), 5)
        
        # 添加到缓冲区
        manager.add_frame('cam1', frame)
        
        # 显示
        cv2.imshow('Fall Detection - Video Recording Demo', frame)
        
        # 处理按键
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('f'):
            # 模拟跌倒事件
            print("\n⚠️ 检测到跌倒！开始录制...")
            manager.on_event_detected('cam1', event_type='fall', pre_seconds=5, post_seconds=10)
            
            # 模拟持续录制 post_seconds
            start_time = time.time()
            while time.time() - start_time < 10:
                frame_count += 1
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                for i in range(720):
                    frame[i, :] = [int(i * 0.3), 100, 200]
                
                x_pos = int(640 + 300 * np.sin(frame_count * 0.05))
                y_pos = int(360 + 200 * np.cos(frame_count * 0.03))
                cv2.rectangle(frame, (x_pos - 50, y_pos - 100), (x_pos + 50, y_pos + 100), (0, 0, 255), -1)
                
                cv2.putText(frame, f'🔴 FALL EVENT - RECORDING', (400, 400), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                
                manager.add_frame('cam1', frame)
                cv2.imshow('Fall Detection - Video Recording Demo', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # 停止录制
            result = manager.finish_recording('cam1', event_type='fall')
            if result:
                filepath, info = result
                print(f"✅ 视频已保存：{filepath}")
                print(f"   时长：{info['duration']:.1f}秒 | 帧数：{info['frames']}")
        
        frame_count += 1
        time.sleep(1 / fps)
    
    # 清理
    cv2.destroyAllWindows()
    print("\n👋 演示结束")
    
    # 显示录制统计
    recorder = manager.get_or_create_recorder('cam1')
    stats = recorder.get_buffer_stats()
    print(f"\n📊 录制统计:")
    print(f"   总帧数：{stats['total_frames_added']}")
    print(f"   总录制次数：{stats['total_recordings']}")


def test_standalone_recorder():
    """独立测试录制器功能"""
    
    print("🧪 独立录制器测试")
    
    # 创建录制器
    recorder = VideoRecorder(buffer_seconds=10, output_dir="test_recordings", fps=30)
    
    # 生成测试帧
    print("生成测试帧...")
    for i in range(300):  # 10 秒 @ 30fps
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame, (320 + int(100 * np.sin(i * 0.1)), 240), 50, (0, 255, 0), -1)
        cv2.putText(frame, f'Frame {i}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        recorder.add_frame(frame)
    
    print(f"✅ 缓冲区填充完成：{recorder.get_buffer_stats()['buffer_current']:.1f}秒")
    
    # 触发录制
    print("\n🔴 开始录制...")
    recorder.start_recording(pre_event_seconds=5, post_event_seconds=5)
    
    # 继续添加帧（事件后）
    for i in range(150):  # 5 秒
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(frame, (320, 240), 50, (0, 0, 255), -1)
        cv2.putText(frame, f'RECORDING {i}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        recorder.continue_recording(frame)
    
    # 停止并保存
    print("\n💾 保存视频...")
    result = recorder.stop_and_save(event_type="test", camera_id="test_cam")
    
    if result:
        filepath, info = result
        print(f"\n✅ 测试成功!")
        print(f"   文件：{filepath}")
        print(f"   时长：{info['duration']:.1f}秒")
        print(f"   帧数：{info['frames']}")
    else:
        print("❌ 保存失败")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="视频录制功能演示")
    parser.add_argument('--mode', choices=['demo', 'test'], default='demo',
                       help='运行模式：demo=交互式演示，test=独立测试')
    
    args = parser.parse_args()
    
    if args.mode == 'demo':
        simulate_camera_feed()
    else:
        test_standalone_recorder()
