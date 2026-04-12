#!/usr/bin/env python3
"""
摔倒检测系统 - Streamlit 可视化界面（高性能版）

优化:
- 使用 @st.experimental_fragment 实现局部刷新
- 复用 Plotly 图表容器，避免重复创建
- 移除 time.sleep，使用 fragment 自动节流
- 减少不必要的 session_state 更新
"""

import streamlit as st
import numpy as np
import open3d as o3d
import plotly.graph_objects as go
from datetime import datetime
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Session State 初始化 ====================
if 'running' not in st.session_state:
    st.session_state.running = False
if 'current_frame' not in st.session_state:
    st.session_state.current_frame = 0
if 'frame_history' not in st.session_state:
    st.session_state.frame_history = []
if 'alert_history' not in st.session_state:
    st.session_state.alert_history = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()

# ==================== 模拟点云生成 ====================
def generate_mock_point_cloud(frame_id: int, is_falling: bool = False):
    """生成模拟点云 - 优化版"""
    np.random.seed(frame_id + 42)
    
    # 地面（只在周围，中间留空）
    ground_x = np.random.uniform(0, 4, 500)
    ground_y = np.random.uniform(0, 4, 500)
    mask = ((ground_x < 1.5) | (ground_x > 2.5)) | ((ground_y < 1.5) | (ground_y > 2.5))
    ground_points = np.column_stack([
        ground_x[mask],
        ground_y[mask],
        np.zeros_like(ground_x[mask])
    ])
    
    # 人体（密集圆柱体）
    if is_falling:
        progress = min(1.0, (frame_id - 50) / 10)
        height = max(0.3, 1.7 - progress * 1.4)
        radius = 0.3 + progress * 0.5
    else:
        height = 1.7
        radius = 0.3
    
    theta = np.random.uniform(0, 2 * np.pi, 800)
    r = np.sqrt(np.random.uniform(0, 1, 800)) * radius
    h = np.random.uniform(0, 1, 800) * height
    
    human_points = np.column_stack([
        r * np.cos(theta) + 2.0,
        r * np.sin(theta) + 2.0,
        h
    ])
    
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


def point_cloud_to_plotly(pcd: o3d.geometry.PointCloud):
    """将 Open3D 点云转换为 Plotly 格式"""
    points = np.asarray(pcd.points)
    z_values = points[:, 2]
    
    return go.Scatter3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        mode='markers',
        marker=dict(
            size=2,
            color=z_values,
            colorscale='Viridis',
            opacity=0.8,
            colorbar=dict(title='高度 (m)')
        )
    )


# ==================== 自定义 CSS ====================
st.markdown("""
<style>
    .stAlert {padding: 10px 20px;}
    [data-testid="stMetricValue"] {font-size: 2em;}
    /* 减少动画过渡时间 */
    .stPlotlyChart {transition: none !important;}
</style>
""", unsafe_allow_html=True)


# ==================== Fragment 装饰器（局部刷新） ====================
@st.fragment(run_every=0.05)  # 50ms = 20 FPS
def live_monitoring_fragment():
    """实时监控画面的局部刷新 fragment"""
    if not st.session_state.running:
        return
    
    frame_id = st.session_state.current_frame
    is_falling = frame_id >= 50
    
    # 生成点云
    pcd = generate_mock_point_cloud(frame_id, is_falling)
    
    # 创建图表
    fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='X (m)', range=[-1, 5]),
            yaxis=dict(title='Y (m)', range=[-1, 5]),
            zaxis=dict(title='Z (m)', range=[0, 2.5]),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.5)
        ),
        height=600,
        margin=dict(l=0, r=0, t=30, b=0),
        title=f"Frame {frame_id} - {'⚠️ 摔倒!' if is_falling else '✅ 正常'}"
    )
    
    # 使用固定的 key，避免重复创建
    st.plotly_chart(fig, use_container_width=True, key="live_chart")
    
    # 更新状态
    st.text(f"🔄 处理中... Frame {frame_id} | 已运行：{len(st.session_state.frame_history)} 帧")
    
    # 添加报警
    if frame_id == 50:
        st.session_state.alert_history.append({
            'timestamp': datetime.now(),
            'level': 'warning',
            'message': '检测到疑似摔倒行为'
        })
    elif frame_id == 52:
        st.session_state.alert_history.append({
            'timestamp': datetime.now(),
            'level': 'critical',
            'message': '确认摔倒！请立即查看！'
        })
    
    # 显示报警
    if frame_id >= 52:
        st.error("🚨 **确认摔倒！请立即查看！**")
    elif frame_id >= 50:
        st.warning("⚠️ **检测到疑似摔倒行为**")
    
    # 记录历史
    st.session_state.frame_history.append({
        'frame_id': frame_id,
        'timestamp': datetime.now(),
        'num_people': 1,
        'has_fall': is_falling,
        'processing_time_ms': 33
    })
    
    # 保持最近 100 帧
    if len(st.session_state.frame_history) > 100:
        st.session_state.frame_history.pop(0)
    
    # 下一帧
    st.session_state.current_frame += 1
    
    # 自动停止
    if frame_id >= 100:
        st.success("✅ 已播放 100 帧，点击 **重置** 重新开始")
        st.session_state.running = False


# ==================== 主界面 ====================
st.title("🚨 摔倒检测实时监控系统")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("🎛️ 控制面板")
    
    # 控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ 启动", use_container_width=True, disabled=st.session_state.running):
            st.session_state.running = True
            st.session_state.current_frame = 0
            st.session_state.frame_history = []
            st.session_state.alert_history = []
            st.rerun()
    
    with col2:
        if st.button("⏹️ 停止", use_container_width=True, disabled=not st.session_state.running):
            st.session_state.running = False
            st.rerun()
    
    if st.button("🔄 重置", use_container_width=True):
        st.session_state.running = False
        st.session_state.current_frame = 0
        st.session_state.frame_history = []
        st.session_state.alert_history = []
        st.rerun()
    
    st.divider()
    
    # 状态信息
    st.subheader("📊 实时状态")
    
    if st.session_state.frame_history:
        last_frame = st.session_state.frame_history[-1]
        st.metric("当前帧", last_frame['frame_id'])
        st.metric("检测到人数", last_frame['num_people'])
        
        fps = 1000 / last_frame['processing_time_ms'] if last_frame['processing_time_ms'] > 0 else 0
        st.metric("FPS", f"{fps:.1f}")
    
    total_alerts = len(st.session_state.alert_history)
    st.metric("报警次数", total_alerts)


# 主界面
tab1, tab2 = st.tabs(["🌐 实时监控", "📈 统计图表"])

with tab1:
    col_main, col_info = st.columns([2, 1])
    
    with col_main:
        st.subheader("🔍 点云视图")
        
        if st.session_state.running:
            # 使用 fragment 实现局部刷新
            live_monitoring_fragment()
        else:
            # 静态显示
            pcd = generate_mock_point_cloud(0, False)
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X (m)', range=[-1, 5]),
                    yaxis=dict(title='Y (m)', range=[-1, 5]),
                    zaxis=dict(title='Z (m)', range=[0, 2.5]),
                    aspectmode='manual',
                    aspectratio=dict(x=1, y=1, z=0.5)
                ),
                height=600,
                title="系统未运行 - 点击 **启动** 开始监测"
            )
            st.plotly_chart(fig, use_container_width=True, key="static_chart")
            st.text("⏸️ 等待启动...")
    
    with col_info:
        st.subheader("📋 检测结果")
        
        if st.session_state.frame_history:
            last = st.session_state.frame_history[-1]
            st.markdown(f"""
            **当前帧**: {last['frame_id']}  
            **人数**: {last['num_people']}  
            **状态**: {'🚨 摔倒' if last['has_fall'] else '✅ 正常'}  
            **耗时**: {last['processing_time_ms']:.1f}ms
            """)
            
            st.divider()
            st.markdown("**报警记录:**")
            for alert in reversed(st.session_state.alert_history[-5:]):
                ts = alert['timestamp'].strftime("%H:%M:%S")
                emoji = "🚨" if alert['level'] == 'critical' else "⚠️"
                st.markdown(f"{emoji} `{ts}` {alert['message']}")
        else:
            st.info("暂无数据")

with tab2:
    st.subheader("📈 FPS 趋势")
    
    if st.session_state.frame_history:
        fps_list = [1000/f['processing_time_ms'] for f in st.session_state.frame_history]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=fps_list, mode='lines', name='FPS'))
        fig.update_layout(title="处理速度", xaxis_title="帧 ID", yaxis_title="FPS", height=400)
        st.plotly_chart(fig, use_container_width=True, key="fps_chart")
    else:
        st.info("启动系统后查看统计数据")
