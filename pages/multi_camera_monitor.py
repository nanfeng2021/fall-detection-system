#!/usr/bin/env python3
"""
多摄像头监控界面

功能:
- 多摄像头同时预览
- 单画面/4 画面/9 画面切换
- 摄像头配置管理
- 实时状态监控
"""

import streamlit as st
import numpy as np
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="多摄像头监控",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 导入服务 ====================
try:
    from src.camera.multi_camera_manager import (
        get_camera_manager,
        CameraConfig,
        CameraType
    )
    CAMERA_ENABLED = True
except Exception as e:
    print(f"⚠️ 摄像头模块加载失败：{e}")
    CAMERA_ENABLED = False

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "1x1"  # 1x1, 2x2, 3x3
if 'selected_camera' not in st.session_state:
    st.session_state.selected_camera = None

# ==================== 权限检查 ====================
def check_login():
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()

check_login()

# ==================== 初始化摄像头管理器 ====================
if CAMERA_ENABLED:
    camera_mgr = get_camera_manager()
else:
    st.error("摄像头模块不可用")
    st.stop()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("📹 摄像头管理")
    
    user = st.session_state.current_user
    st.markdown(f"**👤 {user['username']}**")
    
    st.divider()
    
    # 视图模式选择
    st.subheader("🖼️ 视图模式")
    view_mode = st.radio(
        "布局",
        ["1x1 (单画面)", "2x2 (四画面)", "3x3 (九画面)"],
        index=0 if st.session_state.view_mode == "1x1" else (1 if st.session_state.view_mode == "2x2" else 2),
        label_visibility="collapsed"
    )
    
    # 更新 session state
    if "1x1" in view_mode:
        st.session_state.view_mode = "1x1"
    elif "2x2" in view_mode:
        st.session_state.view_mode = "2x2"
    else:
        st.session_state.view_mode = "3x3"
    
    st.divider()
    
    # 摄像头列表
    st.subheader("📷 摄像头列表")
    
    active_cams = camera_mgr.get_active_cameras()
    
    if not active_cams:
        st.info("暂无活跃摄像头")
    else:
        for cam_id in active_cams:
            config = camera_mgr.get_camera_config(cam_id)
            status = camera_mgr.get_camera_status(cam_id)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                icon = "🟢" if status and status.is_connected else "🔴"
                location = f" - {config.location}" if config.location else ""
                st.markdown(f"{icon} **{config.name}**{location}")
            
            with col2:
                if st.button("👁️", key=f"view_{cam_id}", help="查看此摄像头"):
                    st.session_state.selected_camera = cam_id
                    st.session_state.view_mode = "1x1"
                    st.rerun()
        
        st.divider()
        
        # 添加新摄像头按钮
        if st.button("➕ 添加摄像头", use_container_width=True):
            st.session_state.show_add_camera = True
    
    st.divider()
    
    # 返回主页
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("app_optimized.py")

# ==================== 主界面 ====================
st.title("📹 多摄像头监控")
st.markdown("**实时监控多个区域，统一告警管理**")

# 显示统计信息
active_count = len(camera_mgr.get_active_cameras())
total_count = len(camera_mgr.cameras)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("总摄像头", total_count)
with col2:
    st.metric("活跃", active_count)
with col3:
    st.metric("离线", total_count - active_count)

st.divider()

# ==================== 视图模式 ====================
view_mode = st.session_state.view_mode

if view_mode == "1x1":
    # 单画面模式
    if st.session_state.selected_camera:
        cam_id = st.session_state.selected_camera
        config = camera_mgr.get_camera_config(cam_id)
        
        st.subheader(f"📷 {config.name}")
        
        # 获取帧
        frame = camera_mgr.get_frame(cam_id)
        
        if frame is not None:
            # BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.image(frame_rgb, use_container_width=True)
            
            # 显示信息
            status = camera_mgr.get_camera_status(cam_id)
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("状态", "🟢 在线" if status.is_connected else "🔴 离线")
            with col2:
                st.metric("FPS", f"{status.fps_current:.1f}")
            with col3:
                st.metric("位置", config.location or "未设置")
            with col4:
                last_time = status.last_frame_time.strftime("%H:%M:%S") if status.last_frame_time else "无数据"
                st.metric("最后更新", last_time)
        else:
            st.warning("⚠️ 暂无视频信号")
    
    else:
        # 没有选择摄像头，显示所有摄像头缩略图
        st.info("👈 请从侧边栏选择一个摄像头查看")
        
        all_statuses = camera_mgr.get_all_statuses()
        
        if all_statuses:
            cols = st.columns(min(3, len(all_statuses)))
            
            for idx, (cam_id, status) in enumerate(all_statuses.items()):
                with cols[idx % len(cols)]:
                    config = camera_mgr.get_camera_config(cam_id)
                    
                    st.markdown(f"**{config.name}**")
                    
                    frame = camera_mgr.get_frame(cam_id)
                    if frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        st.image(frame_rgb, use_container_width=True)
                    else:
                        st.caption("无信号")
                    
                    status_text = "🟢 在线" if status.is_connected else "🔴 离线"
                    st.caption(status_text)
                    
                    if st.button("查看", key=f"select_{cam_id}", use_container_width=True):
                        st.session_state.selected_camera = cam_id
                        st.session_state.view_mode = "1x1"
                        st.rerun()

elif view_mode == "2x2":
    # 四画面模式
    st.subheader("🖼️ 四画面预览")
    
    active_cams = camera_mgr.get_active_cameras()[:4]
    
    if len(active_cams) < 4:
        st.info(f"当前只有 {len(active_cams)} 个活跃摄像头，需要 4 个才能填满画面")
    
    # 创建 2x2 网格
    rows = st.columns(2)
    
    for i in range(4):
        row_idx = i // 2
        col_idx = i % 2
        
        with rows[row_idx]:
            if i < len(active_cams):
                cam_id = active_cams[i]
                config = camera_mgr.get_camera_config(cam_id)
                
                frame = camera_mgr.get_frame(cam_id)
                
                if frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    st.image(frame_rgb, use_container_width=True, caption=f"{config.name}")
                else:
                    st.caption(f"📷 {config.name} - 无信号")
            else:
                st.caption(f"空位 {i+1}")

elif view_mode == "3x3":
    # 九画面模式
    st.subheader("🖼️ 九画面预览")
    
    active_cams = camera_mgr.get_active_cameras()[:9]
    
    if len(active_cams) < 9:
        st.info(f"当前只有 {len(active_cams)} 个活跃摄像头")
    
    # 创建 3x3 网格
    for row in range(3):
        cols = st.columns(3)
        for col in range(3):
            idx = row * 3 + col
            
            with cols[col]:
                if idx < len(active_cams):
                    cam_id = active_cams[idx]
                    config = camera_mgr.get_camera_config(cam_id)
                    
                    frame = camera_mgr.get_frame(cam_id)
                    
                    if frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        # 缩小显示
                        small_frame = cv2.resize(frame_rgb, (320, 180))
                        st.image(small_frame, use_container_width=True)
                        st.caption(f"{config.name}")
                    else:
                        st.caption(f"📷 {config.name}")
                else:
                    st.caption(f"空位 {idx+1}")

# ==================== 添加摄像头对话框 ====================
if st.session_state.get('show_add_camera', False):
    st.divider()
    st.subheader("➕ 添加新摄像头")
    
    with st.form("add_camera_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            cam_id = st.text_input("摄像头 ID", placeholder="例如：cam1")
            cam_name = st.text_input("名称", placeholder="例如：客厅摄像头")
            cam_type = st.selectbox(
                "类型",
                options=["usb", "rtsp", "http", "file"],
                format_func=lambda x: {"usb": "USB 摄像头", "rtsp": "RTSP 流", "http": "HTTP 流", "file": "视频文件"}[x]
            )
        
        with col2:
            cam_source = st.text_input(
                "源地址",
                placeholder="USB: 0 或 /dev/video0\nRTSP: rtsp://...\nHTTP: http://...\nFile: /path/to/video.mp4",
                help="USB 摄像头输入设备号（如 0），网络摄像头输入 URL"
            )
            cam_location = st.text_input("安装位置", placeholder="例如：客厅东侧")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            width = st.number_input("宽度", value=1280)
        with col2:
            height = st.number_input("高度", value=720)
        with col3:
            fps = st.number_input("帧率", value=30)
        
        enabled = st.checkbox("立即启用", value=True)
        
        submitted = st.form_submit_button("✅ 添加摄像头", use_container_width=True)
        
        if submitted:
            if not cam_id or not cam_name or not cam_source:
                st.error("请填写必填字段")
            else:
                try:
                    config = CameraConfig(
                        id=cam_id,
                        name=cam_name,
                        source=cam_source,
                        camera_type=CameraType(cam_type),
                        enabled=enabled,
                        width=width,
                        height=height,
                        fps=fps,
                        location=cam_location
                    )
                    
                    if camera_mgr.add_camera(config):
                        st.success(f"✅ 摄像头 '{cam_name}' 添加成功！")
                        
                        # 如果启用，立即连接
                        if enabled:
                            camera_mgr.start_all()
                        
                        st.session_state.show_add_camera = False
                        st.rerun()
                    else:
                        st.error(f"❌ 摄像头 ID '{cam_id}' 已存在")
                
                except Exception as e:
                    st.error(f"❌ 添加失败：{e}")

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.6 | 多摄像头监控</p>
    <p>支持 USB / RTSP / HTTP / 文件流</p>
</div>
""", unsafe_allow_html=True)
