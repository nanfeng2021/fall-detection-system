"""
视频播放组件 - 在 Streamlit 中播放录制的视频
"""

import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import base64


def get_video_files(directory="recordings", camera_id=None, event_type=None):
    """
    获取录像文件列表
    
    Args:
        directory: 录像目录
        camera_id: 摄像头 ID 过滤
        event_type: 事件类型过滤
        
    Returns:
        list: 视频文件信息列表
    """
    recordings_dir = Path(directory)
    
    if not recordings_dir.exists():
        return []
    
    videos = []
    
    # 遍历所有子目录
    for cam_dir in recordings_dir.iterdir():
        if not cam_dir.is_dir():
            continue
        
        # 如果指定了 camera_id，跳过不匹配的
        if camera_id and cam_dir.name != camera_id:
            continue
        
        # 查找 MP4 文件
        for video_file in cam_dir.glob("*.mp4"):
            # 解析文件名：YYYYMMDD_HHMMSS_eventtype_camID.mp4
            filename = video_file.stem
            
            try:
                parts = filename.split('_')
                if len(parts) >= 4:
                    date_str = parts[0]
                    time_str = parts[1]
                    evt_type = parts[2]
                    cam_id = '_'.join(parts[3:])  # 支持 cam_id 中包含下划线
                    
                    # 如果指定了 event_type，过滤
                    if event_type and evt_type != event_type:
                        continue
                    
                    # 解析时间戳
                    timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    
                    # 获取文件大小
                    file_size_mb = video_file.stat().st_size / (1024 * 1024)
                    
                    videos.append({
                        'filepath': str(video_file),
                        'filename': video_file.name,
                        'timestamp': timestamp,
                        'event_type': evt_type,
                        'camera_id': cam_id,
                        'size_mb': file_size_mb,
                        'directory': cam_dir.name
                    })
            except Exception as e:
                # 跳过格式不正确的文件
                continue
    
    # 按时间戳倒序排列（最新的在前）
    videos.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return videos


def encode_video_to_base64(video_path):
    """
    将视频编码为 base64（用于嵌入 HTML5 player）
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        str: base64 编码的视频数据，失败返回 None
    """
    try:
        with open(video_path, 'rb') as f:
            video_data = f.read()
        
        # 限制最大 50MB
        if len(video_data) > 50 * 1024 * 1024:
            st.warning(f"⚠️ 视频文件过大 ({len(video_data) / (1024*1024):.1f}MB)，可能无法播放")
            return None
        
        encoded = base64.b64encode(video_data).decode('utf-8')
        return encoded
    except Exception as e:
        st.error(f"❌ 读取视频失败：{e}")
        return None


def render_video_player(video_info):
    """
    渲染视频播放器
    
    Args:
        video_info: 视频信息字典
    """
    filepath = video_info['filepath']
    
    if not os.path.exists(filepath):
        st.error(f"❌ 视频文件不存在：{filepath}")
        return
    
    # 显示视频信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("事件类型", video_info['event_type'])
    with col2:
        st.metric("摄像头", video_info['camera_id'])
    with col3:
        st.metric("时间", video_info['timestamp'].strftime("%H:%M:%S"))
    with col4:
        st.metric("大小", f"{video_info['size_mb']:.2f} MB")
    
    # 尝试播放视频
    try:
        # 方法 1: 使用 Streamlit 原生 video 组件（推荐）
        with open(filepath, 'rb') as video_file:
            video_bytes = video_file.read()
            st.video(video_bytes)
        
    except Exception as e:
        st.error(f"❌ 播放失败：{e}")
        
        # 降级方案：提供下载链接
        st.warning("⚠️ 无法在线播放，请下载到本地观看")
        
        with open(filepath, 'rb') as f:
            st.download_button(
                label="📥 下载视频",
                data=f.read(),
                file_name=video_info['filename'],
                mime="video/mp4"
            )


def render_recordings_gallery(recordings_dir="recordings", limit=20):
    """
    渲染录像库（缩略图 + 列表）
    
    Args:
        recordings_dir: 录像目录
        limit: 显示数量限制
    """
    st.header("📹 录像库")
    
    # 过滤选项
    col1, col2, col3 = st.columns(3)
    
    with col1:
        camera_filter = st.selectbox(
            "摄像头",
            options=["全部"] + list(set(v['directory'] for v in get_video_files(recordings_dir)))
        )
    
    with col2:
        event_filter = st.selectbox(
            "事件类型",
            options=["全部"] + list(set(v['event_type'] for v in get_video_files(recordings_dir)))
        )
    
    with col3:
        sort_order = st.selectbox("排序", options=["最新优先", "最旧优先"])
    
    # 获取视频列表
    camera_id = None if camera_filter == "全部" else camera_filter
    event_type = None if event_filter == "全部" else event_filter
    
    videos = get_video_files(recordings_dir, camera_id=camera_id, event_type=event_type)
    
    if not videos:
        st.info("📭 暂无录像记录")
        return
    
    # 排序
    if sort_order == "最旧优先":
        videos.reverse()
    
    # 限制数量
    videos = videos[:limit]
    
    st.divider()
    
    # 显示视频列表
    for i, video in enumerate(videos):
        with st.expander(f"🎬 {video['event_type']} @ {video['camera_id']} - {video['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"):
            render_video_player(video)
            
            # 操作按钮
            col1, col2 = st.columns(2)
            
            with col1:
                if os.path.exists(video['filepath']):
                    with open(video['filepath'], 'rb') as f:
                        st.download_button(
                            label="📥 下载视频",
                            data=f.read(),
                            file_name=video['filename'],
                            mime="video/mp4",
                            key=f"download_{i}"
                        )
            
            with col2:
                if st.button("🗑️ 删除", key=f"delete_{i}"):
                    try:
                        os.remove(video['filepath'])
                        st.success("✅ 已删除")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 删除失败：{e}")


def render_live_recording_status(recorder):
    """
    渲染实时录制状态
    
    Args:
        recorder: VideoRecorder 实例
    """
    stats = recorder.get_buffer_stats()
    
    # 进度条显示缓冲区填充状态
    st.progress(stats['buffer_fill_percent'] / 100)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("缓冲区", f"{stats['buffer_current']:.1f}s / {stats['buffer_capacity']}s")
    
    with col2:
        status = "🔴 录制中" if recorder.is_recording else "🟢 待机"
        st.metric("状态", status)
    
    with col3:
        st.metric("总录制数", stats['total_recordings'])
    
    # 如果正在录制，显示警告
    if recorder.is_recording:
        st.warning("🔴 正在录制事件视频...")
