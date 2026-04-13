"""
Streamlit 视频流优化组件

功能:
1. 帧缓存（避免重复处理）
2. 降采样显示（减少传输）
3. 自动刷新控制
4. 性能监控
"""

import streamlit as st
import numpy as np
from typing import Optional, Dict
import cv2
import time


# ==================== Streamlit 缓存优化 ====================

@st.cache_data(maxsize=128, ttl=0.5)
def cached_resize_frame(frame_bytes: bytes, target_width: int = 640) -> bytes:
    """
    缓存的图片缩放（使用字节缓存，避免重复处理）
    
    Args:
        frame_bytes: JPEG 编码的帧数据
        target_width: 目标宽度
    
    Returns:
        缩放后的 JPEG 数据
    """
    # 解码
    frame = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    
    if frame is None:
        return frame_bytes
    
    # 计算缩放比例
    height, width = frame.shape[:2]
    scale = target_width / width
    new_height = int(height * scale)
    
    # 缩放
    resized = cv2.resize(frame, (target_width, new_height), interpolation=cv2.INTER_AREA)
    
    # 重新编码为 JPEG
    _, encoded = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
    
    return encoded.tobytes()


def optimize_frame_for_display(frame: np.ndarray, max_width: int = 640) -> np.ndarray:
    """
    优化帧用于显示
    
    Args:
        frame: 原始帧（BGR）
        max_width: 最大宽度
    
    Returns:
        优化后的帧
    """
    if frame is None:
        return None
    
    height, width = frame.shape[:2]
    
    # 如果已经足够小，直接返回
    if width <= max_width:
        return frame
    
    # 计算缩放比例
    scale = max_width / width
    new_height = int(height * scale)
    
    # 快速缩放
    optimized = cv2.resize(frame, (max_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    return optimized


# ==================== 高性能视频显示组件 ====================

class VideoStreamPlayer:
    """
    高性能视频流播放器
    
    特性:
    - 帧缓存
    - 自适应刷新率
    - 性能统计
    """
    
    def __init__(self, camera_id: str, max_width: int = 640):
        self.camera_id = camera_id
        self.max_width = max_width
        self.last_frame_hash = None
        self.frame_count = 0
        self.skip_count = 0
        self.target_fps = 15  # 目标显示 FPS
        self.last_display_time = 0
        
    def render(self, frame: Optional[np.ndarray], placeholder_text: str = "无信号") -> bool:
        """
        渲染帧到 Streamlit
        
        Args:
            frame: BGR 帧
            placeholder_text: 无信号时的提示文字
        
        Returns:
            是否成功显示
        """
        current_time = time.time()
        
        # 帧率控制（避免过度刷新）
        frame_interval = 1.0 / self.target_fps
        if current_time - self.last_display_time < frame_interval:
            self.skip_count += 1
            return False
        
        if frame is None:
            # 显示占位符
            st.info(f"📷 {placeholder_text}")
            return False
        
        try:
            # 优化帧
            optimized = optimize_frame_for_display(frame, self.max_width)
            
            # BGR to RGB
            rgb_frame = cv2.cvtColor(optimized, cv2.COLOR_BGR2RGB)
            
            # 显示
            st.image(rgb_frame, channels="RGB", use_container_width=True)
            
            # 更新统计
            self.frame_count += 1
            self.last_display_time = current_time
            
            # 计算帧哈希（检测变化）
            frame_hash = hash(rgb_frame.tobytes())
            if frame_hash == self.last_frame_hash:
                # 帧内容未变化
                pass
            self.last_frame_hash = frame_hash
            
            return True
            
        except Exception as e:
            st.error(f"❌ 显示失败：{e}")
            return False
    
    def get_stats(self) -> Dict:
        """获取播放统计"""
        elapsed = time.time() - self.last_display_time if self.last_display_time > 0 else 0
        actual_fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        return {
            'camera_id': self.camera_id,
            'displayed_frames': self.frame_count,
            'skipped_frames': self.skip_count,
            'actual_fps': round(actual_fps, 1),
            'target_fps': self.target_fps,
            'efficiency': round(self.frame_count / (self.frame_count + self.skip_count) * 100, 1) if (self.frame_count + self.skip_count) > 0 else 0
        }


# ==================== 多画面网格布局组件 ====================

def render_camera_grid(frames_dict: Dict[str, np.ndarray], cols: int = 2, max_width: int = 320):
    """
    渲染多摄像头网格布局
    
    Args:
        frames_dict: {camera_id: frame} 字典
        cols: 列数
        max_width: 每个画面的最大宽度
    """
    camera_ids = list(frames_dict.keys())
    rows = (len(camera_ids) + cols - 1) // cols
    
    for row in range(rows):
        st_cols = st.columns(cols)
        
        for col_idx in range(cols):
            cam_idx = row * cols + col_idx
            
            if cam_idx >= len(camera_ids):
                break
            
            with st_cols[col_idx]:
                cam_id = camera_ids[cam_idx]
                frame = frames_dict.get(cam_id)
                
                if frame is not None:
                    # 优化并显示
                    optimized = optimize_frame_for_display(frame, max_width)
                    rgb_frame = cv2.cvtColor(optimized, cv2.COLOR_BGR2RGB)
                    st.image(rgb_frame, channels="RGB", caption=f"📷 {cam_id}", use_container_width=True)
                else:
                    st.caption(f"📷 {cam_id} - 无信号")


# ==================== 性能监控组件 ====================

def render_performance_metrics(manager) -> None:
    """
    渲染性能指标
    
    Args:
        manager: 摄像头管理器实例
    """
    if not hasattr(manager, 'get_performance_report'):
        return
    
    report = manager.get_performance_report()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "活跃摄像头",
            f"{report['active_cameras']}/{report['total_cameras']}",
            delta=None
        )
    
    with col2:
        st.metric(
            "总 FPS",
            f"{report['total_fps']:.1f}",
            delta="正常" if report['total_fps'] > 20 else "偏低"
        )
    
    with col3:
        st.metric(
            "平均延迟",
            f"{report['avg_latency_ms']:.1f}ms",
            delta="优秀" if report['avg_latency_ms'] < 50 else "偏高",
            delta_color="inverse"
        )
    
    with col4:
        smooth_score = report['smooth_score']
        st.metric(
            "流畅度评分",
            f"{smooth_score}/100",
            delta="优秀" if smooth_score >= 80 else ("良好" if smooth_score >= 60 else "需优化"),
            delta_color="normal" if smooth_score >= 80 else "inverse"
        )
    
    # 丢帧统计
    if report['dropped_frames'] > 0:
        st.warning(f"⚠️ 累计丢帧：{report['dropped_frames']}")


# ==================== 自动刷新容器 ====================

@st.experimental_fragment
def auto_refresh_video(player: VideoStreamPlayer, get_frame_func, refresh_rate: float = 15.0):
    """
    自动刷新的视频组件（使用 Streamlit Fragment）
    
    Args:
        player: VideoStreamPlayer 实例
        get_frame_func: 获取帧的函数
        refresh_rate: 刷新率（FPS）
    """
    import time
    
    # 获取帧
    frame = get_frame_func()
    
    # 渲染
    player.render(frame)
    
    # 自动刷新
    time.sleep(1.0 / refresh_rate)
    st.rerun()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例代码
    st.title("🎬 视频流优化演示")
    
    # 创建播放器
    player = VideoStreamPlayer("cam1")
    
    # 模拟帧
    dummy_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    
    # 渲染
    success = player.render(dummy_frame, "测试画面")
    
    # 显示统计
    stats = player.get_stats()
    st.json(stats)
