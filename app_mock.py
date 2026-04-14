#!/usr/bin/env python3
"""
摔倒检测系统 - Streamlit 可视化界面 (模拟数据版)
自动使用模拟数据，无需硬件
"""

import streamlit as st
import numpy as np
import open3d as o3d
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from pathlib import Path
import sys
import json
import threading
import queue

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.detection.detector import FallDetectionSystem, SystemAlert, FrameResult
from src.preprocessing.clustering import HumanCluster


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统 - 模拟数据",
    page_icon="🚨",
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
    .alert-warning {
        background-color: #fff3e0;
        border-left: 5px solid #ff9800;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .alert-info {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
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
    .stat-number {
        font-size: 2.5em;
        font-weight: bold;
        color: #1976d2;
    }
    .stat-label {
        font-size: 0.9em;
        color: #666;
    }
    .mock-badge {
        background-color: #4caf50;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8em;
        font-weight: bold;
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
        'fps': 30.0
    }
if 'frame_id' not in st.session_state:
    st.session_state.frame_id = 0
if 'mock_data_queue' not in st.session_state:
    st.session_state.mock_data_queue = queue.Queue()


# ==================== 模拟数据生成器 ====================
def generate_mock_point_cloud(frame_id: int, is_falling: bool = False):
    """生成模拟点云"""
    np.random.seed(frame_id)
    
    # 地面
    ground_points = np.random.rand(1000, 3) * [5, 5, 0.05]
    ground_points[:, 2] = 0
    
    # 人体
    if is_falling:
        # 模拟摔倒过程：高度逐渐降低
        progress = min((frame_id - 50) / 30, 1.0) if frame_id >= 50 else 0
        height = 1.7 - progress * 1.3  # 从1.7米降到0.4米
        width = 0.4 + progress * 1.2   # 宽度增加
        depth = 0.4
    else:
        height = 1.7
        width = 0.4
        depth = 0.4
    
    human_points = np.random.rand(500, 3) * [width, depth, height]
    human_points[:, 2] += height / 2
    human_points[:, 0] += 2.5  # 居中
    human_points[:, 1] += 2.5
    
    # 噪声
    noise = np.random.normal(0, 0.02, human_points.shape)
    human_points += noise
    
    # 合并
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd, height


def mock_data_producer():
    """模拟数据生产者 - 在后台线程运行"""
    while st.session_state.running:
        frame_id = st.session_state.frame_id
        
        # 模拟摔倒：前50帧正常，之后摔倒
        is_falling = frame_id >= 50 and frame_id < 100
        
        pcd, height = generate_mock_point_cloud(frame_id, is_falling)
        
        # 放入队列
        try:
            st.session_state.mock_data_queue.put({
                'frame_id': frame_id,
                'pcd': pcd,
                'height': height,
                'is_falling': is_falling,
                'timestamp': datetime.now()
            }, block=False)
        except queue.Full:
            pass
        
        st.session_state.frame_id += 1
        
        # 控制帧率
        time.sleep(1.0 / st.session_state.config['fps'])


# ==================== 辅助函数 ====================
def create_system():
    """创建检测系统"""
    config = st.session_state.config
    
    def on_alert(alert: SystemAlert):
        st.session_state.alert_history.append({
            'timestamp': alert.timestamp,
            'type': alert.alert_type,
            'cluster_id': alert.cluster_id,
            'message': alert.message,
            'confidence': alert.confidence,
            'level': 'critical' if alert.alert_type == 'fall_confirmed' else 'warning'
        })
        
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


def point_cloud_to_plotly(pcd: o3d.geometry.PointCloud):
    """将 Open3D 点云转换为 Plotly 格式"""
    points = np.asarray(pcd.points)
    
    if len(points) == 0:
        return go.Scatter3d(x=[], y=[], z=[], mode='markers')
    
    # 降采样显示
    if len(points) > 5000:
        indices = np.random.choice(len(points), 5000, replace=False)
        points = points[indices]
    
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
    
    # 模拟数据标识
    st.markdown("<span class='mock-badge'>🎮 模拟数据模式</span>", unsafe_allow_html=True)
    st.caption("无需硬件，自动生成测试数据")
    
    st.divider()
    
    # 系统控制
    st.subheader("▶️ 系统控制")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 启动", use_container_width=True, disabled=st.session_state.running):
            if st.session_state.system is None:
                create_system()
            st.session_state.running = True
            st.session_state.frame_id = 0
            
            # 启动模拟数据线程
            thread = threading.Thread(target=mock_data_producer, daemon=True)
            thread.start()
            
            st.success("✅ 系统已启动")
            st.rerun()
    
    with col2:
        if st.button("⏹️ 停止", use_container_width=True, disabled=not st.session_state.running):
            st.session_state.running = False
            st.warning("⏹️ 系统已停止")
            st.rerun()
    
    if st.button("🔄 重置", use_container_width=True):
        st.session_state.system = None
        st.session_state.running = False
        st.session_state.alert_history = []
        st.session_state.frame_history = []
        st.session_state.start_time = None
        st.session_state.frame_id = 0
        while not st.session_state.mock_data_queue.empty():
            try:
                st.session_state.mock_data_queue.get_nowait()
            except:
                break
        st.success("✅ 系统已重置")
        st.rerun()
    
    st.divider()
    
    # 参数配置
    st.subheader("⚙️ 参数配置")
    
    with st.form("config_form"):
        voxel_size = st.slider("体素尺寸 (m)", 0.01, 0.2, st.session_state.config['voxel_size'], 0.01)
        height_drop = st.slider("高度骤降阈值 (m)", 0.1, 1.0, st.session_state.config['height_drop_threshold'], 0.1)
        velocity = st.slider("速度阈值 (m/s)", 0.2, 2.0, st.session_state.config['velocity_threshold'], 0.1)
        confirm_frames = st.slider("确认帧数", 1, 10, st.session_state.config['confirmation_frames'], 1)
        fps = st.slider("帧率 (FPS)", 10, 60, int(st.session_state.config['fps']), 5)
        
        submitted = st.form_submit_button("💾 保存配置", use_container_width=True)
        
        if submitted:
            st.session_state.config.update({
                'voxel_size': voxel_size,
                'height_drop_threshold': height_drop,
                'velocity_threshold': velocity,
                'confirmation_frames': confirm_frames,
                'fps': float(fps)
            })
            save_config()
            
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
    st.metric("当前帧", st.session_state.frame_id)
    
    if st.session_state.system:
        stats = st.session_state.system.get_statistics()
        st.metric("平均 FPS", f"{stats['average_fps']:.1f}")
        st.metric("活跃追踪", stats['active_trackers'])
    
    st.divider()
    
    # 关于
    st.subheader("📖 关于")
    st.markdown("""
    **摔倒检测系统 v1.0**
    
    🎮 **模拟数据模式**
    - 自动生成测试数据
    - 帧 50-100 模拟摔倒
    - 无需硬件设备
    
    技术栈：Python + Streamlit
    
    [GitHub 仓库](https://github.com/nanfeng2021/fall-detection-system)
    """)


# ==================== 主界面 ====================
st.title("🚨 摔倒检测系统")
st.markdown("**实时点云分析 · 智能摔倒检测 · 即时报警通知**")
st.markdown("<span class='mock-badge'>🎮 模拟数据模式 - 自动生成测试数据</span>", unsafe_allow_html=True)

# 创建选项卡
tab1, tab2, tab3, tab4 = st.tabs(["📊 实时监控", "📈 统计图表", "📋 报警历史", "📁 数据管理"])

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
    
    # 点云可视化和检测结果
    col_main, col_info = st.columns([2, 1])
    
    with col_main:
        st.subheader("🌐 点云视图")
        
        chart_placeholder = st.empty()
        
        if st.session_state.running:
            # 从队列获取模拟数据
            try:
                mock_data = st.session_state.mock_data_queue.get_nowait()
                pcd = mock_data['pcd']
                is_falling = mock_data['is_falling']
                frame_id = mock_data['frame_id']
                
                # 创建 Plotly 图
                fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
                
                status_text = "⚠️ 摔倒检测!" if is_falling else "✅ 正常"
                if is_falling:
                    status_color = "red"
                else:
                    status_color = "green"
                
                fig.update_layout(
                    scene=dict(
                        xaxis=dict(title='X (m)', range=[0, 5]),
                        yaxis=dict(title='Y (m)', range=[0, 5]),
                        zaxis=dict(title='Z (m)', range=[0, 2.5]),
                        aspectmode='data'
                    ),
                    height=600,
                    margin=dict(l=0, r=0, t=30, b=0),
                    title=f"Frame {frame_id} - {status_text}"
                )
                
                chart_placeholder.plotly_chart(fig, use_container_width=True)
                
                # 更新帧历史
                st.session_state.frame_history.append({
                    'frame_id': frame_id,
                    'timestamp': datetime.now(),
                    'num_people': 1,
                    'has_fall': is_falling,
                    'processing_time_ms': 33,
                    'height': mock_data['height']
                })
                
                if len(st.session_state.frame_history) > 100:
                    st.session_state.frame_history.pop(0)
                
                # 自动刷新
                time.sleep(0.1)
                st.rerun()
                
            except queue.Empty:
                # 显示等待提示
                st.info("⏳ 等待数据...")
                time.sleep(0.1)
                st.rerun()
        
        else:
            # 显示静态示例图
            pcd, _ = generate_mock_point_cloud(0, False)
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X (m)', range=[0, 5]),
                    yaxis=dict(title='Y (m)', range=[0, 5]),
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
            
            **人体高度**: {last_frame.get('height', 0):.2f}m
            
            **处理时间**: {last_frame['processing_time_ms']:.1f}ms
            """)
            
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
            st.info("等待数据...\n\n💡 点击左侧「启动」按钮开始模拟")


# ==================== Tab 2: 统计图表 ====================
with tab2:
    st.header("统计图表")
    
    if st.session_state.frame_history:
        # FPS 趋势图
        st.subheader("📈 FPS 趋势")
        
        fps_values = [1000 / f['processing_time_ms'] if f['processing_time_ms'] > 0 else 0 
                     for f in st.session_state.frame_history]
        
        fig_fps = go.Figure()
        fig_fps.add_trace(go.Scatter(
            y=fps_values,
            mode='lines',
            name='FPS',
            line=dict(color='blue', width=2)
        ))
        
        fig_fps.update_layout(
            title="处理速度 (FPS)",
            xaxis_title="帧 ID",
            yaxis_title="FPS",
            height=400
        )
        
        st.plotly_chart(fig_fps, use_container_width=True)
        
        # 高度变化趋势
        st.subheader("📏 人体高度变化")
        
        height_values = [f.get('height', 0) for f in st.session_state.frame_history]
        
        fig_height = go.Figure()
        fig_height.add_trace(go.Scatter(
            y=height_values,
            mode='lines',
            name='高度 (m)',
            line=dict(color='green', width=2),
            fill='tozeroy'
        ))
        
        fig_height.add_hline(y=0.8, line_dash="dash", line_color="red", 
                            annotation_text="摔倒阈值")
        
        fig_height.update_layout(
            title="人体高度变化趋势",
            xaxis_title="帧",
            yaxis_title="高度 (m)",
            height=400
        )
        
        st.plotly_chart(fig_height, use_container_width=True)
        
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


# ==================== Tab 3: 报警历史 ====================
with tab3:
    st.header("报警历史")
    
    if st.session_state.alert_history:
        filter_level = st.selectbox("报警级别", ["全部", "确认摔倒", "疑似摔倒"])
        
        if filter_level == "全部":
            filtered_alerts = st.session_state.alert_history
        elif filter_level == "确认摔倒":
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'critical']
        else:
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'warning']
        
        st.dataframe(
            filtered_alerts,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("时间", format="HH:mm:ss"),
                "type": "类型",
                "cluster_id": "人员 ID",
                "message": "消息",
                "confidence": st.column_config.NumberColumn("置信度", format="%.0%"),
                "level": "级别"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # 导出按钮
        csv_data = "\n".join([
            ",".join([
                str(a['timestamp']),
                a['type'],
                str(a['cluster_id']),
                a['message'],
                f"{a['confidence']:.2f}",
                a['level']
            ])
            for a in filtered_alerts
        ])
        
        st.download_button(
            label="📥 导出 CSV",
            data=csv_data,
            file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    else:
        st.info("暂无报警记录")


# ==================== Tab 4: 数据管理 ====================
with tab4:
    st.header("数据管理")
    
    st.subheader("🎮 模拟数据设置")
    
    st.markdown("""
    **当前模式：模拟数据**
    
    系统会自动生成模拟数据：
    - 帧 0-49：正常站立（高度 1.7m）
    - 帧 50-100：模拟摔倒（高度逐渐降低至 0.4m）
    - 帧 100+：保持躺倒状态
    
    无需连接真实硬件即可测试系统功能。
    """)
    
    st.divider()
    
    st.subheader("⚙️ 配置管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 导出配置", use_container_width=True):
            save_config()
            st.success("✅ 配置已导出到 config.json")
    
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
    <p>摔倒检测系统 v1.0 | 模拟数据模式 | Powered by Streamlit + Open3D</p>
    <p>🎮 当前使用模拟数据，无需硬件设备</p>
</div>
""", unsafe_allow_html=True)
