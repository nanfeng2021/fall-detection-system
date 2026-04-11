#!/usr/bin/env python3
"""
摔倒检测系统 - Streamlit 可视化界面

功能:
- 实时点云 3D 显示
- 检测结果可视化
- 报警历史记录
- 系统状态监控
- 参数配置调整

运行方式:
    streamlit run app.py
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

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.detection.detector import FallDetectionSystem, SystemAlert, FrameResult
from src.preprocessing.clustering import HumanCluster


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统",
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
    
    st.divider()
    
    # 关于
    st.subheader("📖 关于")
    st.markdown("""
    **摔倒检测系统 v1.0**
    
    基于点云的实时摔倒检测
    
    - 技术栈：Python + Streamlit
    - 检测算法：规则引擎
    - 延迟：< 100ms
    
    [GitHub 仓库](https://github.com/nanfeng2021/fall-detection-system)
    """)


# ==================== 主界面 ====================
st.title("🚨 摔倒检测系统")
st.markdown("**实时点云分析 · 智能摔倒检测 · 即时报警通知**")

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
        
        # 创建或更新 3D 图
        chart_placeholder = st.empty()
        
        if st.session_state.running:
            # 模拟实时处理
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            frame_id = len(st.session_state.frame_history)
            
            # 模拟摔倒逻辑
            is_falling = frame_id >= 50 and frame_id < 80
            
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
            
            chart_placeholder.plotly_chart(fig, use_container_width=True)
            
            # 模拟处理延迟
            time.sleep(0.033)  # ~30 FPS
            
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
            
            progress_bar.progress((frame_id % 100) / 100)
            status_text.text(f"处理中... Frame {frame_id}")
            
            # 如果有摔倒，显示报警
            if is_falling and len(st.session_state.alert_history) > 0:
                latest_alert = st.session_state.alert_history[-1]
                if latest_alert['level'] == 'critical':
                    st.error(f"🚨 **{latest_alert['message']}**")
                elif latest_alert['level'] == 'warning':
                    st.warning(f"⚠️ **{latest_alert['message']}**")
        
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
                title="系统未运行 - 点击"启动"开始监测"
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
        
        # 处理时间趋势
        st.subheader("⏱️ 处理时间")
        
        time_values = [f['processing_time_ms'] for f in st.session_state.frame_history]
        
        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(
            y=time_values,
            mode='lines',
            name='处理时间 (ms)',
            line=dict(color='green', width=2)
        ))
        
        fig_time.update_layout(
            title="单帧处理时间",
            xaxis_title="帧 ID",
            yaxis_title="时间 (ms)",
            height=400
        )
        
        st.plotly_chart(fig_time, use_container_width=True)
        
        # 报警统计
        st.subheader("🚨 报警统计")
        
        critical_count = sum(1 for a in st.session_state.alert_history if a['level'] == 'critical')
        warning_count = sum(1 for a in st.session_state.alert_history if a['level'] == 'warning')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("确认摔倒", critical_count)
        
        with col2:
            st.metric("疑似摔倒", warning_count)
        
        # 饼图
        if critical_count > 0 or warning_count > 0:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['确认摔倒', '疑似摔倒'],
                values=[critical_count, warning_count],
                hole=0.3
            )])
            
            fig_pie.update_layout(
                title="报警类型分布",
                height=400
            )
            
            st.plotly_chart(fig_pie, use_container_width=True)
    
    else:
        st.info("暂无统计数据，请先启动系统")


# ==================== Tab 3: 报警历史 ====================
with tab3:
    st.header("报警历史")
    
    if st.session_state.alert_history:
        # 过滤选项
        filter_level = st.selectbox("报警级别", ["全部", "确认摔倒", "疑似摔倒"])
        
        # 过滤数据
        if filter_level == "全部":
            filtered_alerts = st.session_state.alert_history
        elif filter_level == "确认摔倒":
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'critical']
        else:
            filtered_alerts = [a for a in st.session_state.alert_history if a['level'] == 'warning']
        
        # 显示表格
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
    
    # 数据集列表
    st.subheader("📁 数据集")
    
    dataset_dir = Path(__file__).parent / "datasets"
    
    if dataset_dir.exists():
        datasets = list(dataset_dir.glob("*"))
        
        if datasets:
            for dataset in datasets:
                if dataset.is_dir():
                    # 尝试读取元数据
                    metadata_file = dataset / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        st.markdown(f"""
                        **{metadata.get('name', dataset.name)}**
                        
                        - 帧数：{metadata.get('total_frames', '未知')}
                        - 时长：{metadata.get('duration_seconds', 0):.1f}秒
                        - 创建时间：{metadata.get('created_at', '未知')}
                        """)
                        
                        if st.button(f"📂 查看", key=str(dataset)):
                            st.info(f"数据集路径：{dataset}")
                            # TODO: 实现数据集查看功能
                    
                    else:
                        st.markdown(f"**{dataset.name}** (无元数据)")
                    
                    st.divider()
        else:
            st.info("暂无数据集")
    else:
        st.info("数据集目录不存在")
    
    st.divider()
    
    # 配置管理
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
    
    # 当前配置显示
    st.markdown("**当前配置:**")
    st.json(st.session_state.config)


# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.0 | Powered by Streamlit + Open3D</p>
    <p>GitHub: <a href='https://github.com/nanfeng2021/fall-detection-system'>nanfeng2021/fall-detection-system</a></p>
</div>
""", unsafe_allow_html=True)
