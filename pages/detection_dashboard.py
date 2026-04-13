#!/usr/bin/env python3
"""
多摄像头检测仪表板

功能:
- 查看所有摄像头的检测状态
- 实时统计信息
- 告警历史记录
- 检测器配置
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="检测仪表板",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 导入服务 ====================
try:
    from src.detection.multi_camera_detector import (
        get_multi_camera_detector,
        CameraDetectorConfig
    )
    from src.detection.detector import FallDetectionSystem
    from src.camera.multi_camera_manager import get_camera_manager
    DETECTION_ENABLED = True
except Exception as e:
    print(f"⚠️ 检测模块加载失败：{e}")
    DETECTION_ENABLED = False

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'detectors_running' not in st.session_state:
    st.session_state.detectors_running = False

# ==================== 权限检查 ====================
def check_login():
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()

check_login()

# ==================== 初始化 ====================
if DETECTION_ENABLED:
    detector_mgr = get_multi_camera_detector()
    camera_mgr = get_camera_manager()
else:
    st.error("检测模块不可用")
    st.stop()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎯 检测控制")
    
    user = st.session_state.current_user
    st.markdown(f"**👤 {user['username']}**")
    
    st.divider()
    
    # 启动/停止控制
    if st.session_state.detectors_running:
        if st.button("⏹️ 停止所有检测", use_container_width=True, type="secondary"):
            detector_mgr.stop_all()
            st.session_state.detectors_running = False
            st.rerun()
    else:
        if st.button("▶️ 启动所有检测", use_container_width=True, type="primary"):
            detector_mgr.start_all()
            st.session_state.detectors_running = True
            st.rerun()
    
    st.divider()
    
    # 活跃检测器列表
    st.subheader("📊 活跃检测器")
    
    active_detectors = detector_mgr.get_active_detectors()
    
    for cam_id in active_detectors:
        stats = detector_mgr.get_detector_stats(cam_id)
        config = camera_mgr.get_camera_config(cam_id)
        
        st.markdown(f"**📷 {config.name}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("帧数", stats.total_frames_processed if stats else 0)
        with col2:
            st.metric("告警", stats.total_alerts if stats else 0)
        
        # 启用/禁用开关
        enabled = st.checkbox("启用", value=True, key=f"enable_{cam_id}")
        if not enabled:
            detector_mgr.enable_detector(cam_id, False)
    
    st.divider()
    
    # 返回主页
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("app_optimized.py")

# ==================== 主界面 ====================
st.title("🎯 多摄像头检测仪表板")
st.markdown("**实时监控多个摄像头的摔倒检测状态**")

# 总体统计
summary = detector_mgr.get_summary()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("总摄像头", summary['total_cameras'])

with col2:
    st.metric("活跃检测", summary['active_cameras'])

with col3:
    st.metric("处理帧数", f"{summary['total_frames_processed']:,}")

with col4:
    st.metric("检测到摔倒", summary['total_detections'])

with col5:
    st.metric("触发告警", summary['total_alerts'])

st.divider()

# 各摄像头详细状态
st.subheader("📊 各摄像头检测状态")

all_stats = detector_mgr.get_all_stats()

if not all_stats:
    st.info("暂无检测器，请先添加摄像头并配置检测")
else:
    # 创建卡片网格
    cols = st.columns(min(3, len(all_stats)))
    
    for idx, (cam_id, stats) in enumerate(all_stats.items()):
        with cols[idx % len(cols)]:
            config = camera_mgr.get_camera_config(cam_id)
            
            st.markdown(f"**📷 {config.name}**")
            st.caption(f"位置：{config.location or '未设置'}")
            
            # 状态指示器
            is_active = cam_id in detector_mgr.get_active_detectors()
            status = "🟢 检测中" if is_active else "⏸️ 已暂停"
            st.markdown(status)
            
            # 统计信息
            col1, col2 = st.columns(2)
            with col1:
                st.metric("处理帧", f"{stats.total_frames_processed:,}")
            with col2:
                st.metric("告警数", stats.total_alerts)
            
            # 最后检测时间
            if stats.last_detection_time:
                last_time = stats.last_detection_time.strftime("%H:%M:%S")
                st.caption(f"最后检测：{last_time}")
            else:
                st.caption("暂无检测数据")
            
            # 快速操作
            col1, col2 = st.columns(2)
            with col1:
                if is_active:
                    if st.button("⏸️ 暂停", key=f"pause_{cam_id}", use_container_width=True):
                        detector_mgr.enable_detector(cam_id, False)
                        st.rerun()
                else:
                    if st.button("▶️ 恢复", key=f"resume_{cam_id}", use_container_width=True):
                        detector_mgr.enable_detector(cam_id, True)
                        st.rerun()
            
            with col2:
                if st.button("📈 详情", key=f"detail_{cam_id}", use_container_width=True):
                    st.session_state.selected_camera_detail = cam_id

# 告警历史
st.divider()
st.subheader("🚨 最近告警")

# TODO: 从数据库读取告警历史
st.info("告警历史功能开发中...")

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.6 | 多摄像头检测仪表板</p>
    <p>独立检测 · 统一告警 · 实时统计</p>
</div>
""", unsafe_allow_html=True)
