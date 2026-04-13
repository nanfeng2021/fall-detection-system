#!/usr/bin/env python3
"""
多摄像头监控界面 v2 - 性能优化版

优化点:
1. 使用环形缓冲区替代队列
2. FFmpeg 低延迟参数
3. Streamlit 帧缓存
4. 自适应刷新率
5. 降采样显示
6. 性能监控面板
"""

import streamlit as st
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 导入优化组件 ====================
try:
    from src.camera.multi_camera_manager_v2 import (
        get_camera_manager,
        CameraConfig,
        CameraType
    )
    from src.web.video_components import (
        VideoStreamPlayer,
        render_camera_grid,
        render_performance_metrics,
        optimize_frame_for_display
    )
    CAMERA_ENABLED = True
except Exception as e:
    print(f"⚠️ 组件加载失败：{e}")
    CAMERA_ENABLED = False
    st.error("摄像头模块不可用")

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="多摄像头监控（优化版）",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "1x1"
if 'selected_camera' not in st.session_state:
    st.session_state.selected_camera = None
if 'video_players' not in st.session_state:
    st.session_state.video_players = {}
if 'target_fps' not in st.session_state:
    st.session_state.target_fps = 15  # 默认目标 FPS

# ==================== 权限检查 ====================
def check_login():
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()

check_login()

# ==================== 初始化 ====================
if CAMERA_ENABLED:
    camera_mgr = get_camera_manager()
else:
    st.error("摄像头模块不可用")
    st.stop()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎬 监控设置")
    
    user = st.session_state.current_user
    st.markdown(f"**👤 {user['username']}**")
    
    st.divider()
    
    # 性能设置
    st.subheader("⚡ 性能优化")
    
    target_fps = st.slider(
        "目标 FPS",
        min_value=5,
        max_value=30,
        value=st.session_state.target_fps,
        help="降低 FPS 可减少 CPU 占用，提高流畅度"
    )
    st.session_state.target_fps = target_fps
    
    auto_optimize = st.checkbox(
        "自动优化",
        value=True,
        help="根据系统负载自动调整参数"
    )
    
    st.divider()
    
    # 视图模式
    st.subheader("🖼️ 视图模式")
    view_mode = st.radio(
        "布局",
        ["1x1 (单画面)", "2x2 (四画面)", "3x3 (九画面)"],
        index=0 if st.session_state.view_mode == "1x1" else (1 if st.session_state.view_mode == "2x2" else 2)
    )
    
    if "1x1" in view_mode:
        st.session_state.view_mode = "1x1"
    elif "2x2" in view_mode:
        st.session_state.view_mode = "2x2"
    else:
        st.session_state.view_mode = "3x3"
    
    st.divider()
    
    # 摄像头列表
    st.subheader("📷 摄像头")
    
    active_cams = camera_mgr.get_active_cameras()
    
    for cam_id in active_cams:
        config = camera_mgr.get_camera_config(cam_id)
        status = camera_mgr.get_status(cam_id)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            icon = "🟢" if status and status.is_connected else "🔴"
            st.markdown(f"{icon} **{config.name}**")
        
        with col2:
            if st.button("👁️", key=f"view_{cam_id}"):
                st.session_state.selected_camera = cam_id
                st.session_state.view_mode = "1x1"
                st.rerun()
    
    st.divider()
    
    if st.button("➕ 添加摄像头", use_container_width=True):
        st.session_state.show_add_camera = True
    
    st.divider()
    
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("app/main.py")

# ==================== 主界面 ====================
st.title("📹 多摄像头监控（优化版）")
st.markdown("**低延迟 · 高流畅 · 自适应刷新**")

# 性能监控
render_performance_metrics(camera_mgr)

st.divider()

# ==================== 视频流显示 ====================
view_mode = st.session_state.view_mode

if view_mode == "1x1":
    # 单画面模式
    if st.session_state.selected_camera:
        cam_id = st.session_state.selected_camera
        config = camera_mgr.get_camera_config(cam_id)
        
        st.subheader(f"📷 {config.name}")
        
        # 获取或创建播放器
        if cam_id not in st.session_state.video_players:
            st.session_state.video_players[cam_id] = VideoStreamPlayer(
                cam_id,
                max_width=960  # 单画面更大
            )
        
        player = st.session_state.video_players[cam_id]
        player.target_fps = st.session_state.target_fps
        
        # 获取帧
        frame = camera_mgr.get_frame(cam_id)
        
        # 渲染
        success = player.render(frame, f"{config.name} - 无信号")
        
        # 显示状态
        status = camera_mgr.get_status(cam_id)
        if status:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("状态", "🟢 在线" if status.is_connected else "🔴 离线")
            with col2:
                st.metric("FPS", f"{status.fps_current:.1f}")
            with col3:
                st.metric("延迟", f"{status.latency_ms:.0f}ms")
            with col4:
                st.metric("丢帧", status.dropped_frames)
        
        # 播放器统计
        if st.expander("📊 播放器统计"):
            stats = player.get_stats()
            st.json(stats)
    
    else:
        st.info("👈 请从侧边栏选择一个摄像头")
        
        all_statuses = camera_mgr.get_all_statuses()
        
        if all_statuses:
            cols = st.columns(min(3, len(all_statuses)))
            
            for idx, (cam_id, status) in enumerate(all_statuses.items()):
                with cols[idx % len(cols)]:
                    config = camera_mgr.get_camera_config(cam_id)
                    st.markdown(f"**{config.name}**")
                    
                    frame = camera_mgr.get_frame(cam_id)
                    if frame is not None:
                        optimized = optimize_frame_for_display(frame, 320)
                        rgb_frame = cv2.cvtColor(optimized, cv2.COLOR_BGR2RGB)
                        st.image(rgb_frame, channels="RGB", use_container_width=True)
                    else:
                        st.caption("无信号")
                    
                    status_text = "🟢" if status.is_connected else "🔴"
                    st.caption(f"{status_text} FPS: {status.fps_current:.1f}")
                    
                    if st.button("查看", key=f"select_{cam_id}", use_container_width=True):
                        st.session_state.selected_camera = cam_id
                        st.rerun()

elif view_mode == "2x2":
    # 四画面模式
    st.subheader("🖼️ 四画面预览")
    
    active_cams = camera_mgr.get_active_cameras()[:4]
    
    if len(active_cams) < 4:
        st.info(f"当前只有 {len(active_cams)} 个活跃摄像头")
    
    # 获取所有帧
    frames_dict = {}
    for cam_id in active_cams:
        frame = camera_mgr.get_frame(cam_id)
        frames_dict[cam_id] = frame
    
    # 使用优化的网格渲染
    render_camera_grid(frames_dict, cols=2, max_width=320)

elif view_mode == "3x3":
    # 九画面模式
    st.subheader("🖼️ 九画面预览")
    
    active_cams = camera_mgr.get_active_cameras()[:9]
    
    if len(active_cams) < 9:
        st.info(f"当前只有 {len(active_cams)} 个活跃摄像头")
    
    # 获取所有帧
    frames_dict = {}
    for cam_id in active_cams:
        frame = camera_mgr.get_frame(cam_id)
        frames_dict[cam_id] = frame
    
    # 使用优化的网格渲染
    render_camera_grid(frames_dict, cols=3, max_width=240)

# ==================== 添加摄像头对话框 ====================
if st.session_state.get('show_add_camera', False):
    st.divider()
    st.subheader("➕ 添加新摄像头")
    
    with st.form("add_camera_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            cam_id = st.text_input("摄像头 ID", placeholder="cam1")
            cam_name = st.text_input("名称", placeholder="客厅摄像头")
            cam_type = st.selectbox(
                "类型",
                options=["usb", "rtsp", "http", "file"]
            )
        
        with col2:
            cam_source = st.text_input("源地址", placeholder="0 或 rtsp://...")
            cam_location = st.text_input("安装位置")
        
        # 高级设置
        with st.expander("⚙️ 高级设置"):
            buffer_size = st.slider("缓冲区大小", 1, 10, 3)
            low_latency = st.checkbox("低延迟模式", value=True)
        
        submitted = st.form_submit_button("✅ 添加摄像头", use_container_width=True)
        
        if submitted:
            if cam_id and cam_name and cam_source:
                try:
                    config = CameraConfig(
                        id=cam_id,
                        name=cam_name,
                        source=cam_source,
                        camera_type=CameraType(cam_type),
                        buffer_size=buffer_size,
                        low_latency=low_latency,
                        location=cam_location
                    )
                    
                    if camera_mgr.add_camera(config):
                        camera_mgr.start_all()
                        st.success(f"✅ '{cam_name}' 添加成功！")
                        st.session_state.show_add_camera = False
                        st.rerun()
                    else:
                        st.error(f"❌ ID '{cam_id}' 已存在")
                
                except Exception as e:
                    st.error(f"❌ 添加失败：{e}")

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.7 | 多摄像头监控（性能优化版）</p>
    <p>🚀 低延迟架构 · 自适应刷新 · 智能降采样</p>
</div>
""", unsafe_allow_html=True)
