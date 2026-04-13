#!/usr/bin/env python3
"""
摔倒检测系统 - 带视频录制功能

功能:
- 实时点云 3D 显示
- 检测结果可视化
- 报警历史记录
- ✅ 视频录制与回放（新增）
- 系统状态监控
- 参数配置调整

运行方式:
    streamlit run app_with_video.py
"""

import streamlit as st
import numpy as np
import open3d as o3d
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.detection.detector import FallDetectionSystem, SystemAlert, FrameResult
from src.preprocessing.clustering import HumanCluster
from video_recorder import get_recording_manager
from components.video_player import render_recordings_gallery, render_live_recording_status


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统 - 视频录制版",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义 CSS ====================
st.markdown("""
<style>
    .alert-critical {
        background-color: #ffebee;
        border-left: 5px solid #f44336;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .stat-card {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .recording-indicator {
        background-color: #ffebee;
        color: #c62828;
        padding: 10px;
        border-radius: 5px;
        font-weight: bold;
        animation: pulse 1s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State 初始化 ====================
if 'system' not in st.session_state:
    st.session_state.system = None
if 'running' not in st.session_state:
    st.session_state.running = False
if 'alert_history' not in st.session_state:
    st.session_state.alert_history = []
if 'frame_history' not in st.session_state:
    st.session_state.frame_history = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'config' not in st.session_state:
    st.session_state.config = {
        'voxel_size': 0.05,
        'height_drop_threshold': 0.3,
        'velocity_threshold': 0.5,
        'confirmation_frames': 2,
        'fps': 30.0,
        'video_buffer_seconds': 10,
        'video_pre_event': 5,
        'video_post_event': 15
    }
if 'current_frame' not in st.session_state:
    st.session_state.current_frame = 0
if 'recording_manager' not in st.session_state:
    st.session_state.recording_manager = get_recording_manager()


# ==================== 辅助函数 ====================
def create_system():
    """创建检测系统"""
    config = st.session_state.config
    
    def on_alert(alert: SystemAlert):
        # 添加到历史
        st.session_state.alert_history.append({
            'timestamp': alert.timestamp,
            'type': alert.alert_type,
            'cluster_id': alert.cluster_id,
            'message': alert.message,
            'confidence': alert.confidence,
            'level': 'critical' if alert.alert_type == 'fall_confirmed' else 'warning'
        })
        
        # 触发视频录制
        if alert.alert_type in ['fall_suspected', 'fall_confirmed']:
            event_type = 'fall' if alert.alert_type == 'fall_confirmed' else 'suspected_fall'
            st.session_state.recording_manager.on_event_detected(
                'cam1', 
                event_type=event_type,
                pre_seconds=config.get('video_pre_event', 5),
                post_seconds=config.get('video_post_event', 15)
            )
        
        # 保持最近 100 条报警
        if len(st.session_state.alert_history) > 100:
            st.session_state.alert_history.pop(0)
    
    st.session_state.system = FallDetectionSystem(
        voxel_size=config['voxel_size'],
        height_drop_threshold=config['height_drop_threshold'],
        velocity_threshold=config['velocity_threshold'],
        confirmation_frames=config['confirmation_frames'],
        fps=config['fps'],
        alert_callback=on_alert
    )
    
    st.session_state.start_time = datetime.now()


def generate_mock_point_cloud(frame_id: int, is_falling: bool = False):
    """生成模拟点云"""
    np.random.seed(frame_id)
    
    # 地面
    ground_points = np.random.rand(1000, 3) * [5, 5, 0.05]
    ground_points[:, 2] = 0
    
    # 人体
    if is_falling:
        height = max(0.4, 1.7 - (frame_id % 30) * 0.05)
        width = 0.4 + (1.7 - height)
        human_points = np.random.rand(500, 3) * [width, 0.4, height]
        human_points[:, 2] += height / 2
    else:
        height = 1.7
        human_points = np.random.rand(500, 3) * [0.4, 0.4, height]
        human_points[:, 2] += height / 2
    
    # 噪声
    noise = np.random.normal(0, 0.02, human_points.shape)
    human_points += noise
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


def point_cloud_to_plotly(pcd: o3d.geometry.PointCloud):
    """将 Open3D 点云转换为 Plotly 格式"""
    points = np.asarray(pcd.points)
    
    if len(points) == 0:
        return go.Scatter3d(x=[], y=[], z=[], mode='markers')
    
    # 颜色映射（根据 Z 轴高度）
    z_values = points[:, 2]
    colors = z_values / max(z_values.max(), 0.1)
    
    return go.Scatter3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        mode='markers',
        marker=dict(
            size=2,
            color=colors,
            colorscale='Viridis',
            opacity=0.8,
            colorbar=dict(title='高度 (m)')
        ),
        name='点云'
    )


def save_config():
    """保存配置到文件"""
    config_file = Path(__file__).parent / 'config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.config, f, indent=2)


def load_config():
    """从文件加载配置"""
    config_file = Path(__file__).parent / 'config.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            st.session_state.config = json.load(f)


# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎛️ 控制面板")
    
    # 系统控制
    st.subheader("▶️ 系统控制")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 启动", use_container_width=True, disabled=st.session_state.running):
            if st.session_state.system is None:
                create_system()
            st.session_state.running = True
            st.success("✅ 系统已启动")
    
    with col2:
        if st.button("⏹️ 停止", use_container_width=True, disabled=not st.session_state.running):
            st.session_state.running = False
            st.warning("⏹️ 系统已停止")
    
    if st.button("🔄 重置", use_container_width=True):
        st.session_state.system = None
        st.session_state.running = False
        st.session_state.alert_history = []
        st.session_state.frame_history = []
        st.session_state.start_time = None
        st.session_state.current_frame = 0
        st.success("✅ 系统已重置")
    
    st.divider()
    
    # 参数配置
    st.subheader("⚙️ 参数配置")
    
    with st.form("config_form"):
        voxel_size = st.slider("体素尺寸 (m)", 0.01, 0.2, st.session_state.config['voxel_size'], 0.01)
        height_drop = st.slider("高度骤降阈值 (m)", 0.1, 1.0, st.session_state.config['height_drop_threshold'], 0.1)
        velocity = st.slider("速度阈值 (m/s)", 0.2, 2.0, st.session_state.config['velocity_threshold'], 0.1)
        confirm_frames = st.slider("确认帧数", 1, 10, st.session_state.config['confirmation_frames'], 1)
        fps = st.slider("帧率 (FPS)", 10, 60, int(st.session_state.config['fps']), 5)
        
        st.markdown("**📹 视频录制设置**")
        video_buffer = st.slider("缓冲区时长 (秒)", 5, 30, st.session_state.config.get('video_buffer_seconds', 10), 5)
        video_pre = st.slider("事件前保留 (秒)", 1, 10, st.session_state.config.get('video_pre_event', 5), 1)
        video_post = st.slider("事件后录制 (秒)", 5, 60, st.session_state.config.get('video_post_event', 15), 5)
        
        submitted = st.form_submit_button("💾 保存配置", use_container_width=True)
        
        if submitted:
            st.session_state.config.update({
                'voxel_size': voxel_size,
                'height_drop_threshold': height_drop,
                'velocity_threshold': velocity,
                'confirmation_frames': confirm_frames,
                'fps': float(fps),
                'video_buffer_seconds': video_buffer,
                'video_pre_event': video_pre,
                'video_post_event': video_post
            })
            save_config()
            
            # 如果系统已运行，需要重启
            if st.session_state.system is not None:
                st.session_state.system = None
                create_system()
                st.info("ℹ️ 配置已更新，系统已重启")
            else:
                st.success("✅ 配置已保存")
    
    st.divider()
    
    # 系统信息
    st.subheader("ℹ️ 系统信息")
    
    if st.session_state.start_time:
        uptime = (datetime.now() - st.session_state.start_time).total_seconds()
        st.metric("运行时长", f"{uptime:.0f}秒")
    
    st.metric("总报警数", len(st.session_state.alert_history))
    
    if st.session_state.system:
        stats = st.session_state.system.get_statistics()
        st.metric("平均 FPS", f"{stats['average_fps']:.1f}")
        st.metric("活跃追踪", stats['active_trackers'])
    
    # 录像统计
    recorder = st.session_state.recording_manager.get_or_create_recorder('cam1')
    rec_stats = recorder.get_buffer_stats()
    st.metric("总录制数", rec_stats['total_recordings'])
    
    st.divider()
    
    # 关于
    st.subheader("📖 关于")
    st.markdown("""
    **摔倒检测系统 v1.1** 🎬
    
    基于点云的实时摔倒检测 + 视频录制
    
    - 技术栈：Python + Streamlit + OpenCV
    - 检测算法：规则引擎
    - 视频录制：环形缓冲区 + 事件触发
    - 延迟：< 100ms
    
    [GitHub 仓库](https://github.com/nanfeng2021/fall-detection-system)
    """)


# ==================== 主界面 ====================
st.title("🎬 摔倒检测系统 - 视频录制版")
st.markdown("**实时点云分析 · 智能摔倒检测 · 自动视频录制 · 即时回放**")

# 创建选项卡
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 实时监控", 
    "📹 录像回放", 
    "📈 统计图表", 
    "📋 报警历史", 
    "📁 数据管理"
])

# ==================== Tab 1: 实时监控 ====================
with tab1:
    st.header("实时监控")
    
    # 状态指示器
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = "🟢 运行中" if st.session_state.running else "🔴 已停止"
        st.metric("系统状态", status)
    
    with col2:
        if st.session_state.frame_history:
            last_frame = st.session_state.frame_history[-1]
            st.metric("当前人数", last_frame.get('num_people', 0))
        else:
            st.metric("当前人数", 0)
    
    with col3:
        critical_alerts = sum(1 for a in st.session_state.alert_history if a['level'] == 'critical')
        st.metric("确认摔倒", critical_alerts)
    
    with col4:
        suspected_alerts = sum(1 for a in st.session_state.alert_history if a['level'] == 'warning')
        st.metric("疑似摔倒", suspected_alerts)
    
    # 录制状态指示器
    recorder = st.session_state.recording_manager.get_or_create_recorder('cam1')
    if recorder.is_recording:
        st.markdown('<div class="recording-indicator">🔴 正在录制事件视频...</div>', unsafe_allow_html=True)
    
    # 点云可视化和检测结果
    col_main, col_info = st.columns([2, 1])
    
    with col_main:
        st.subheader("🌐 点云视图")
        
        chart_placeholder = st.empty()
        
        if st.session_state.running:
            progress_bar = st.progress(0)
            status_text = st.empty()
            alert_placeholder = st.empty()
            
            frame_id = st.session_state.current_frame
            
            # 模拟摔倒逻辑（从第 50 帧开始）
            is_falling = frame_id >= 50
            
            # 生成模拟帧用于视频录制
            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            for i in range(720):
                mock_frame[i, :] = [int(i * 0.3), 100, 200]
            
            x_pos = int(640 + 300 * np.sin(frame_id * 0.05))
            y_pos = int(360 + 200 * np.cos(frame_id * 0.03))
            
            if is_falling:
                cv2.rectangle(mock_frame, (x_pos - 50, y_pos - 100), (x_pos + 50, y_pos + 100), (0, 0, 255), -1)
            else:
                cv2.rectangle(mock_frame, (x_pos - 50, y_pos - 100), (x_pos + 50, y_pos + 100), (0, 255, 0), -1)
            
            # 添加到视频缓冲区
            st.session_state.recording_manager.add_frame('cam1', mock_frame)
            
            # 生成点云
            pcd = generate_mock_point_cloud(frame_id, is_falling)
            
            # 创建 Plotly 图
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X (m)', range=[-3, 3]),
                    yaxis=dict(title='Y (m)', range=[-3, 3]),
                    zaxis=dict(title='Z (m)', range=[0, 2.5]),
                    aspectmode='data'
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0),
                title=f"Frame {frame_id} - {'⚠️ 摔倒检测!' if is_falling else '✅ 正常'}"
            )
            
            chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"frame_{frame_id}")
            
            # 更新帧历史
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
            
            # 添加报警记录并触发录制
            if frame_id == 50:
                st.session_state.alert_history.append({
                    'timestamp': datetime.now(),
                    'level': 'warning',
                    'message': '检测到疑似摔倒行为',
                    'type': 'fall_suspected'
                })
            elif frame_id == 52:
                st.session_state.alert_history.append({
                    'timestamp': datetime.now(),
                    'level': 'critical',
                    'message': '确认摔倒！请立即查看！',
                    'type': 'fall_confirmed'
                })
            
            progress_bar.progress((frame_id % 100) / 100)
            status_text.text(f"🔄 处理中... Frame {frame_id} | 已运行：{len(st.session_state.frame_history)} 帧")
            
            # 显示报警
            if frame_id >= 50 and len(st.session_state.alert_history) > 0:
                latest_alert = st.session_state.alert_history[-1]
                if latest_alert['level'] == 'critical':
                    alert_placeholder.error(f"🚨 **{latest_alert['message']}**")
                elif latest_alert['level'] == 'warning':
                    alert_placeholder.warning(f"⚠️ **{latest_alert['message']}**")
            
            # 增加帧计数
            st.session_state.current_frame += 1
            
            # 限制到 100 帧
            if frame_id < 100:
                time.sleep(0.05)
                st.rerun()
            else:
                # 完成录制
                if recorder.is_recording:
                    result = st.session_state.recording_manager.finish_recording('cam1', event_type='fall')
                    if result:
                        filepath, info = result
                        st.success(f"✅ 视频已保存：{info['filename']} (时长：{info['duration']:.1f}秒)")
                
                st.success("✅ 已播放 100 帧，点击 **重置** 按钮重新开始")
                st.session_state.running = False
                alert_placeholder.empty()
        
        else:
            # 显示静态示例图
            pcd = generate_mock_point_cloud(0, False)
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X (m)', range=[-3, 3]),
                    yaxis=dict(title='Y (m)', range=[-3, 3]),
                    zaxis=dict(title='Z (m)', range=[0, 2.5]),
                    aspectmode='data'
                ),
                height=600,
                title="系统未运行 - 点击启动开始监测"
            )
            
            chart_placeholder.plotly_chart(fig, use_container_width=True)
    
    with col_info:
        st.subheader("📋 检测结果")
        
        if st.session_state.frame_history:
            last_frame = st.session_state.frame_history[-1]
            
            st.markdown(f"""
            **当前帧**: {last_frame['frame_id']}
            
            **检测到人数**: {last_frame['num_people']}
            
            **摔倒状态**: {'⚠️ 检测到摔倒' if last_frame['has_fall'] else '✅ 正常'}
            
            **处理时间**: {last_frame['processing_time_ms']:.1f}ms
            """)
            
            # 录像缓冲区状态
            st.divider()
            st.markdown("**📹 录像状态:**")
            rec_stats = recorder.get_buffer_stats()
            st.markdown(f"""
            缓冲区：{rec_stats['buffer_current']:.1f}s / {rec_stats['buffer_capacity']}s
            
            总录制：{rec_stats['total_recordings']} 次
            """)
            
            # 最近检测详情
            st.divider()
            st.markdown("**最近报警:**")
            
            if st.session_state.alert_history:
                for alert in reversed(st.session_state.alert_history[-5:]):
                    timestamp = alert['timestamp'].strftime("%H:%M:%S")
                    emoji = "🚨" if alert['level'] == 'critical' else "⚠️"
                    st.markdown(f"{emoji} `{timestamp}` {alert['message']}")
            else:
                st.info("暂无报警记录")
        else:
            st.info("等待数据...")


# ==================== Tab 2: 录像回放 ====================
with tab2:
    render_recordings_gallery("recordings", limit=10)


# ==================== Tab 3: 统计图表 ====================
with tab3:
    st.header("统计图表")
    
    if st.session_state.frame_history:
        # FPS 趋势图
        st.subheader("📈 FPS 趋势")
        
        fps_values = [1000 / f['processing_time_ms'] if f['processing_time_ms'] > 0 else 0 
                     for f in st.session_state.frame_history]
        
        fig_fps = go.Figure()
        fig_fps.add_trace(go.Scatter(y=fps_values, mode='lines', name='FPS', line=dict(color='blue', width=2)))
        fig_fps.update_layout(title="处理速度 (FPS)", xaxis_title="帧 ID", yaxis_title="FPS", height=400)
        st.plotly_chart(fig_fps, use_container_width=True)
        
        # 报警统计
        st.subheader("🚨 报警统计")
        critical_count = sum(1 for a in st.session_state.alert_history if a['level'] == 'critical')
        warning_count = sum(1 for a in st.session_state.alert_history if a['level'] == 'warning')
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("确认摔倒", critical_count)
        with col2:
            st.metric("疑似摔倒", warning_count)
    
    else:
        st.info("暂无统计数据，请先启动系统")


# ==================== Tab 4: 报警历史 ====================
with tab4:
    st.header("报警历史")
    
    if st.session_state.alert_history:
        filter_level = st.selectbox("报警级别", ["全部", "确认摔倒", "疑似摔倒"])
        
        if filter_level == "全部":
            filtered_alerts = st.session_state.alert_history
        elif filter_level == "确认摔倒":
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'critical']
        else:
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'warning']
        
        st.dataframe(filtered_alerts, hide_index=True, use_container_width=True)
    else:
        st.info("暂无报警记录")


# ==================== Tab 5: 数据管理 ====================
with tab5:
    st.header("数据管理")
    
    st.subheader("📁 数据集")
    dataset_dir = Path(__file__).parent / "datasets"
    
    if dataset_dir.exists():
        datasets = list(dataset_dir.glob("*"))
        if datasets:
            for dataset in datasets:
                if dataset.is_dir():
                    st.markdown(f"**{dataset.name}**")
                    st.divider()
        else:
            st.info("暂无数据集")
    else:
        st.info("数据集目录不存在")
    
    st.divider()
    
    st.subheader("⚙️ 配置管理")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 导出配置", use_container_width=True):
            save_config()
            st.success("✅ 配置已导出")
    
    with col2:
        if st.button("📥 导入配置", use_container_width=True):
            load_config()
            st.success("✅ 配置已导入")
    
    st.markdown("**当前配置:**")
    st.json(st.session_state.config)


# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.1 🎬 | Powered by Streamlit + Open3D + OpenCV</p>
    <p>GitHub: <a href='https://github.com/nanfeng2021/fall-detection-system'>nanfeng2021/fall-detection-system</a></p>
</div>
""", unsafe_allow_html=True)
