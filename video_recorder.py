"""
视频录制模块 - 实现跌倒事件的视频录制与回放
"""

import cv2
import numpy as np
from collections import deque
from datetime import datetime
import os
import threading
import time


class VideoRecorder:
    """视频录制器 - 维护环形缓冲区并在事件触发时保存视频"""
    
    def __init__(self, buffer_seconds=10, output_dir="recordings", fps=30):
        """
        初始化视频录制器
        
        Args:
            buffer_seconds: 环形缓冲区时长（秒）
            output_dir: 视频输出目录
            fps: 视频帧率
        """
        self.buffer_seconds = buffer_seconds
        self.output_dir = output_dir
        self.fps = fps
        self.max_frames = buffer_seconds * fps
        
        # 环形缓冲区 - 存储最近的帧
        self.frame_buffer = deque(maxlen=self.max_frames)
        self.buffer_lock = threading.Lock()
        
        # 录制状态
        self.is_recording = False
        self.recording_frames = []
        self.recording_lock = threading.Lock()
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 统计信息
        self.total_recordings = 0
        self.frames_added = 0
    
    def add_frame(self, frame):
        """
        添加帧到缓冲区
        
        Args:
            frame: OpenCV 帧 (BGR 格式)
        """
        with self.buffer_lock:
            # 存储帧的副本
            self.frame_buffer.append(frame.copy())
            self.frames_added += 1
    
    def start_recording(self, pre_event_seconds=5, post_event_seconds=15):
        """
        开始录制事件视频
        
        Args:
            pre_event_seconds: 包含事件前的秒数
            post_event_seconds: 继续录制事件后的秒数
        """
        with self.recording_lock:
            if self.is_recording:
                return
            
            self.is_recording = True
            self.recording_frames = []
            
            # 从缓冲区获取事件前的帧
            pre_frames_count = min(
                int(pre_event_seconds * self.fps),
                len(self.frame_buffer)
            )
            
            if pre_frames_count > 0:
                # 从缓冲区取出最近的 pre_frames_count 帧
                buffer_list = list(self.frame_buffer)
                self.recording_frames = buffer_list[-pre_frames_count:]
            
            print(f"🎬 开始录制：已包含事件前 {pre_frames_count/self.fps:.1f} 秒")
    
    def continue_recording(self, frame):
        """
        继续录制，添加事件后的帧
        
        Args:
            frame: 当前帧
        """
        with self.recording_lock:
            if self.is_recording:
                self.recording_frames.append(frame.copy())
    
    def stop_and_save(self, event_type="fall", camera_id="cam1"):
        """
        停止录制并保存视频文件
        
        Args:
            event_type: 事件类型 (fall, motion, etc.)
            camera_id: 摄像头 ID
            
        Returns:
            str: 保存的文件路径，如果失败返回 None
        """
        with self.recording_lock:
            if not self.is_recording or len(self.recording_frames) == 0:
                self.is_recording = False
                self.recording_frames = []
                return None
            
            # 生成文件名：YYYYMMDD_HHMMSS_eventtype_camID.mp4
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{event_type}_{camera_id}.mp4"
            filepath = os.path.join(self.output_dir, filename)
            
            # 获取帧尺寸
            height, width = self.recording_frames[0].shape[:2]
            
            # 创建 VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, self.fps, (width, height))
            
            if not out.isOpened():
                print(f"❌ 无法创建视频写入器：{filepath}")
                self.is_recording = False
                self.recording_frames = []
                return None
            
            # 写入所有帧
            for frame in self.recording_frames:
                out.write(frame)
            
            out.release()
            
            # 重置录制状态
            self.is_recording = False
            duration = len(self.recording_frames) / self.fps
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            
            print(f"💾 视频已保存：{filepath}")
            print(f"   时长：{duration:.1f} 秒 | 大小：{file_size_mb:.2f} MB")
            
            self.total_recordings += 1
            recording_info = {
                'filepath': filepath,
                'filename': filename,
                'timestamp': timestamp,
                'event_type': event_type,
                'camera_id': camera_id,
                'duration': duration,
                'frames': len(self.recording_frames)
            }
            
            self.recording_frames = []
            return filepath, recording_info
    
    def get_buffer_stats(self):
        """获取缓冲区统计信息"""
        with self.buffer_lock:
            current_seconds = len(self.frame_buffer) / self.fps
            return {
                'buffer_capacity': self.buffer_seconds,
                'buffer_current': current_seconds,
                'buffer_fill_percent': (current_seconds / self.buffer_seconds) * 100,
                'total_frames_added': self.frames_added,
                'total_recordings': self.total_recordings
            }
    
    def cleanup_old_recordings(self, keep_days=7):
        """
        清理旧的录像文件
        
        Args:
            keep_days: 保留的天数
        """
        import glob
        
        cutoff_time = time.time() - (keep_days * 24 * 60 * 60)
        deleted_count = 0
        
        for filepath in glob.glob(os.path.join(self.output_dir, "*.mp4")):
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except Exception as e:
                    print(f"删除文件失败 {filepath}: {e}")
        
        if deleted_count > 0:
            print(f"🧹 清理了 {deleted_count} 个旧录像文件")
        
        return deleted_count


class RecordingManager:
    """录像管理器 - 管理多个摄像头的录制"""
    
    def __init__(self, base_dir="recordings"):
        """
        初始化录像管理器
        
        Args:
            base_dir: 基础录像目录
        """
        self.base_dir = base_dir
        self.recorders = {}  # camera_id -> VideoRecorder
        self.recordings_log = []  # 记录所有录像的元数据
        
        os.makedirs(base_dir, exist_ok=True)
    
    def get_or_create_recorder(self, camera_id="cam1", **kwargs):
        """
        获取或创建指定摄像头的录制器
        
        Args:
            camera_id: 摄像头 ID
            **kwargs: VideoRecorder 的参数
            
        Returns:
            VideoRecorder: 录制器实例
        """
        if camera_id not in self.recorders:
            self.recorders[camera_id] = VideoRecorder(
                output_dir=os.path.join(self.base_dir, camera_id),
                **kwargs
            )
        return self.recorders[camera_id]
    
    def on_event_detected(self, camera_id, event_type="fall", 
                         pre_seconds=5, post_seconds=15):
        """
        当事件被检测到时触发录制
        
        Args:
            camera_id: 摄像头 ID
            event_type: 事件类型
            pre_seconds: 事件前保留秒数
            post_seconds: 事件后录制秒数
        """
        recorder = self.get_or_create_recorder(camera_id)
        recorder.start_recording(pre_seconds, post_seconds)
    
    def add_frame(self, camera_id, frame):
        """
        添加帧到指定摄像头的缓冲区
        
        Args:
            camera_id: 摄像头 ID
            frame: 视频帧
        """
        recorder = self.get_or_create_recorder(camera_id)
        recorder.add_frame(frame)
        
        # 如果正在录制，继续添加帧
        if recorder.is_recording:
            recorder.continue_recording(frame)
    
    def finish_recording(self, camera_id, event_type="fall"):
        """
        完成录制并保存
        
        Args:
            camera_id: 摄像头 ID
            event_type: 事件类型
            
        Returns:
            tuple: (filepath, info) 或 None
        """
        if camera_id not in self.recorders:
            return None
        
        result = self.recorders[camera_id].stop_and_save(event_type, camera_id)
        
        if result:
            filepath, info = result
            self.recordings_log.append(info)
        
        return result
    
    def get_recent_recordings(self, limit=10):
        """
        获取最近的录像记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: 录像信息列表
        """
        return sorted(
            self.recordings_log,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    def get_all_recordings(self, camera_id=None, event_type=None):
        """
        获取所有录像记录（可过滤）
        
        Args:
            camera_id: 摄像头 ID 过滤
            event_type: 事件类型过滤
            
        Returns:
            list: 录像信息列表
        """
        recordings = self.recordings_log
        
        if camera_id:
            recordings = [r for r in recordings if r['camera_id'] == camera_id]
        if event_type:
            recordings = [r for r in recordings if r['event_type'] == event_type]
        
        return sorted(recordings, key=lambda x: x['timestamp'], reverse=True)


# 全局录像管理器实例
_recording_manager = None


def get_recording_manager():
    """获取全局录像管理器单例"""
    global _recording_manager
    if _recording_manager is None:
        _recording_manager = RecordingManager()
    return _recording_manager
