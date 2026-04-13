#!/usr/bin/env python3
"""
摔倒检测系统 - 带视频录制 + 移动推送 + 数据分析

功能:
- 实时点云 3D 显示
- 检测结果可视化
- ✅ 视频录制与回放
- ✅ 移动端推送通知
- ✅ 数据分析面板（趋势/热力图/统计）
- 报警历史记录
- 系统状态监控

运行方式:
    streamlit run app_with_analytics.py
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
import json
import asyncio
import cv2

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.detection.detector import FallDetectionSystem, SystemAlert, FrameResult
from video_recorder import get_recording_manager
from components.video_player import render_recordings_gallery
from notifiers import get_notification_manager, AlertMessage, WeComBotNotifier, FeishuBotNotifier, EmailNotifier, WebhookNotifier
from analytics import create_analytics_engine, create_dashboard_builder, FallEvent


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统 - 数据分析版",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
        'video_post_event': 15,
        'notifications_enabled': True,
        'analytics_enabled': True
    }
if 'current_frame' not in st.session_state:
    st.session_state.current_frame = 0
if 'recording_manager' not in st.session_state:
    st.session_state.recording_manager = get_recording_manager()
if 'notification_manager' not in st.session_state:
    st.session_state.notification_manager = get_notification_manager()
if 'notifications_sent' not in st.session_state:
    st.session_state.notifications_sent = []
if 'analytics_engine' not in st.session_state:
    st.session_state.analytics_engine = create_analytics_engine()
if 'dashboard_builder' not in st.session_state:
    st.session_state.dashboard_builder = None


# ==================== 辅助函数 ====================
def setup_dashboard():
    """设置仪表板构建器"""
    if st.session_state.analytics_engine:
        st.session_state.dashboard_builder = create_dashboard_builder(
            st.session_state.analytics_engine
        )
    return st.session_state.dashboard_builder


def load_notification_config():
    """加载通知配置"""
    config_file = Path(__file__).parent / 'config.notifications.json'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def setup_notifications():
    """根据配置设置通知渠道"""
    config = load_notification_config()
    manager = st.session_state.notification_manager
    manager.channels = []
    
    if config.get('wecom_bot', {}).get('enabled'):
        webhook_url = config['wecom_bot'].get('webhook_url')
        if webhook_url:
            manager.add_channel(WeComBotNotifier(webhook_url))
    
    if config.get('feishu_bot', {}).get('enabled'):
        webhook_url = config['feishu_bot'].get('webhook_url')
        secret = config['feishu_bot'].get('secret', '')
        if webhook_url:
            manager.add_channel(FeishuBotNotifier(webhook_url, secret))
    
    if config.get('email', {}).get('enabled'):
        email_config = config['email']
        if all(k in email_config for k in ['smtp_server', 'username', 'password', 'recipients']):
            manager.add_channel(EmailNotifier(
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config.get('smtp_port', 587),
                username=email_config['username'],
                password=email_config['password'],
                recipients=email_config['recipients'],
                use_tls=email_config.get('use_tls', True)
            ))
    
    if config.get('webhook', {}).get('enabled'):
        webhook_config = config['webhook']
        if 'url' in webhook_config:
            manager.add_channel(WebhookNotifier(
                url=webhook_config['url'],
                method=webhook_config.get('method', 'POST'),
                headers=webhook_config.get('headers', {})
            ))
    
    return sum(1 for c in manager.channels if c.enabled)


def create_system():
    """创建检测系统"""
    config = st.session_state.config
    
    def on_alert(alert: SystemAlert):
        # 添加到历史
        alert_dict = {
            'timestamp': alert.timestamp,
            'type': alert.alert_type,
            'cluster_id': alert.cluster_id,
            'message': alert.message,
            'confidence': alert.confidence,
            'level': 'critical' if alert.alert_type == 'fall_confirmed' else 'warning',
            'location': alert.location
        }
        st.session_state.alert_history.append(alert_dict)
        
        # 记录到分析引擎
        if config.get('analytics_enabled', True) and st.session_state.analytics_engine:
            fall_event = FallEvent(
                timestamp=alert.timestamp,
                event_type=alert.alert_type,
                location=alert.location or '未知',
                confidence=alert.confidence,
                cluster_id=alert.cluster_id
            )
            st.session_state.analytics_engine.add_event(fall_event)
        
        # 触发视频录制
        if alert.alert_type in ['fall_suspected', 'fall_confirmed']:
            event_type = 'fall' if alert.alert_type == 'fall_confirmed' else 'suspected_fall'
            st.session_state.recording_manager.on_event_detected(
                'cam1', 
                event_type=event_type,
                pre_seconds=config.get('video_pre_event', 5),
                post_seconds=config.get('video_post_event', 15)
            )
        
        # 发送通知
        if config.get('notifications_enabled', True) and st.session_state.notification_manager.channels:
            alert_message = AlertMessage(
                title="确认摔倒！请立即查看！" if alert.alert_type == 'fall_confirmed' else "疑似摔倒行为",
                content=alert.message,
                alert_type=alert.alert_type,
                timestamp=alert.timestamp,
                location=alert.location,
                confidence=alert.confidence
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if alert.alert_type == 'fall_confirmed':
                success_count = loop.run_until_complete(
                    st.session_state.notification_manager.notify_all(alert_message)
                )
            else:
                success_count = loop.run_until_complete(
                    st.session_state.notification_manager.notify(
                        alert_message,
                        channels=["企业微信机器人", "飞书机器人", "Webhook"]
                    )
                )
            
            loop.close()
            
            st.session_state.notifications_sent.append({
                'timestamp': datetime.now(),
                'alert_type': alert.alert_type,
                'channels_success': success_count
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


def generate_mock_point_cloud(frame_id: int, is_falling: bool = False):
    """生成模拟点云"""
    np.random.seed(frame_id)
    ground_points = np.random.rand(1000, 3) * [5, 5, 0.05]
    ground_points[:, 2] = 0
    
    if is_falling:
        height = max(0.4, 1.7 - (frame_id % 30) * 0.05)
        width = 0.4 + (1.7 - height)
        human_points = np.random.rand(500, 3) * [width, 0.4, height]
        human_points[:, 2] += height / 2
    else:
        height = 1.7
        human_points = np.random.rand(500, 3) * [0.4, 0.4, height]
        human_points[:, 2] += height / 2
    
    noise = np.random.normal(0, 0.02, human_points.shape)
    human_points += noise
    all_points = np.vstack([ground_points, human_points])
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    return pcd


def point_cloud_to_plotly(pcd: o3d.geometry.PointCloud):
    """将 Open3D 点云转换为 Plotly 格式"""
    points = np.asarray(pcd.points)
    if len(points) == 0:
        return go.Scatter3d(x=[], y=[], z=[], mode='markers')
    
    z_values = points[:, 2]
    colors = z_values / max(z_values.max(), 0.1)
    
    return go.Scatter3d(
        x=points[:, 0], y=points[:, 1], z=points[:, 2],
        mode='markers',
        marker=dict(size=2, color=colors, colorscale='Viridis', opacity=0.8)
    )


def save_config():
    """保存配置"""
    config_file = Path(__file__).parent / 'config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(st.session_state.config, f, indent=2)


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
        st.session_state.notifications_sent = []
        st.success("✅ 系统已重置")
    
    st.divider()
    
    # 通知管理
    st.subheader("📱 通知管理")
    notif_enabled = st.checkbox("启用通知", value=st.session_state.config.get('notifications_enabled', True))
    st.session_state.config['notifications_enabled'] = notif_enabled
    
    enabled_channels = setup_notifications()
    st.markdown(f"**活跃渠道**: {enabled_channels}")
    
    if st.session_state.notifications_sent:
        st.divider()
        total_sent = sum(n['channels_success'] for n in st.session_state.notifications_sent)
        st.metric("已发送通知", total_sent)
    
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
    
    if st.session_state.system:
        stats = st.session_state.system.get_statistics()
        st.metric("平均 FPS", f"{stats['average_fps']:.1f}")
    
    recorder = st.session_state.recording_manager.get_or_create_recorder('cam1')
    rec_stats = recorder.get_buffer_stats()
    st.metric("总录制数", rec_stats['total_recordings'])
    
    # 分析统计
    if st.session_state.analytics_engine:
        ana_stats = st.session_state.analytics_engine.get_statistics()
        st.metric("事件记录", ana_stats['total_events'])
    
    st.divider()
    
    st.subheader("📖 关于")
    st.markdown("""
    **摔倒检测系统 v1.3** 📊
    
    点云检测 + 视频录制 + 移动推送 + 数据分析
    
    [GitHub 仓库](https://github.com/nanfeng2021/fall-detection-system)
    """)


# ==================== 主界面 ====================
st.title("📊 摔倒检测系统 - 数据分析版")
st.markdown("**实时检测 · 自动录像 · 即时推送 · 智能分析**")

# 创建选项卡
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 实时监控", 
    "📈 数据分析",
    "📹 录像回放", 
    "📱 通知记录",
    "📅 趋势图表", 
    "📋 报警历史"
])

# ==================== Tab 1: 实时监控 ====================
with tab1:
    st.header("实时监控")
    
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
        total_notifs = sum(n['channels_success'] for n in st.session_state.notifications_sent)
        st.metric("已发通知", total_notifs)
    
    recorder = st.session_state.recording_manager.get_or_create_recorder('cam1')
    if recorder.is_recording:
        st.markdown('<div style="background-color:#ffebee;color:#c62828;padding:10px;border-radius:5px;font-weight:bold;">🔴 正在录制事件视频...</div>', unsafe_allow_html=True)
    
    col_main, col_info = st.columns([2, 1])
    
    with col_main:
        st.subheader("🌐 点云视图")
        chart_placeholder = st.empty()
        
        if st.session_state.running:
            progress_bar = st.progress(0)
            status_text = st.empty()
            alert_placeholder = st.empty()
            
            frame_id = st.session_state.current_frame
            is_falling = frame_id >= 50
            
            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            for i in range(720):
                mock_frame[i, :] = [int(i * 0.3), 100, 200]
            
            x_pos = int(640 + 300 * np.sin(frame_id * 0.05))
            y_pos = int(360 + 200 * np.cos(frame_id * 0.03))
            color = (0, 0, 255) if is_falling else (0, 255, 0)
            cv2.rectangle(mock_frame, (x_pos - 50, y_pos - 100), (x_pos + 50, y_pos + 100), color, -1)
            
            st.session_state.recording_manager.add_frame('cam1', mock_frame)
            
            pcd = generate_mock_point_cloud(frame_id, is_falling)
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            fig.update_layout(
                scene=dict(xaxis=dict(range=[-3, 3]), yaxis=dict(range=[-3, 3]), zaxis=dict(range=[0, 2.5])),
                height=600, margin=dict(l=0, r=0, t=30, b=0),
                title=f"Frame {frame_id} - {'⚠️ 摔倒检测!' if is_falling else '✅ 正常'}"
            )
            
            chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"frame_{frame_id}")
            
            st.session_state.frame_history.append({
                'frame_id': frame_id, 'timestamp': datetime.now(),
                'num_people': 1, 'has_fall': is_falling, 'processing_time_ms': 33
            })
            
            if len(st.session_state.frame_history) > 100:
                st.session_state.frame_history.pop(0)
            
            if frame_id == 50:
                st.session_state.alert_history.append({
                    'timestamp': datetime.now(), 'level': 'warning',
                    'message': '检测到疑似摔倒行为', 'type': 'fall_suspected', 'location': '客厅'
                })
            elif frame_id == 52:
                st.session_state.alert_history.append({
                    'timestamp': datetime.now(), 'level': 'critical',
                    'message': '确认摔倒！请立即查看！', 'type': 'fall_confirmed', 'location': '客厅'
                })
                
                if st.session_state.config.get('notifications_enabled', True):
                    st.session_state.notifications_sent.append({
                        'timestamp': datetime.now(), 'alert_type': 'fall_confirmed',
                        'channels_success': enabled_channels
                    })
            
            progress_bar.progress((frame_id % 100) / 100)
            status_text.text(f"🔄 处理中... Frame {frame_id}")
            
            if frame_id >= 50 and st.session_state.alert_history:
                latest_alert = st.session_state.alert_history[-1]
                if latest_alert['level'] == 'critical':
                    alert_placeholder.error(f"🚨 **{latest_alert['message']}**")
                elif latest_alert['level'] == 'warning':
                    alert_placeholder.warning(f"⚠️ **{latest_alert['message']}**")
            
            st.session_state.current_frame += 1
            
            if frame_id < 100:
                time.sleep(0.05)
                st.rerun()
            else:
                if recorder.is_recording:
                    result = st.session_state.recording_manager.finish_recording('cam1', event_type='fall')
                    if result:
                        filepath, info = result
                        st.success(f"✅ 视频已保存：{info['filename']}")
                
                st.success("✅ 已播放 100 帧，点击 **重置** 重新开始")
                st.session_state.running = False
        
        else:
            pcd = generate_mock_point_cloud(0, False)
            fig = go.Figure(data=[point_cloud_to_plotly(pcd)])
            fig.update_layout(height=600, title="系统未运行 - 点击启动开始监测")
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
        else:
            st.info("等待数据...")


# ==================== Tab 2: 数据分析 ====================
with tab2:
    st.header("📈 数据分析面板")
    
    setup_dashboard()
    
    if st.session_state.dashboard_builder:
        builder = st.session_state.dashboard_builder
        engine = st.session_state.analytics_engine
        
        # 摘要卡片
        st.subheader("📊 总体统计")
        cards = builder.create_summary_cards()
        
        cols = st.columns(len(cards))
        for i, card in enumerate(cards):
            with cols[i]:
                st.markdown(f"""
                <div style="background-color:{card['color']};color:white;padding:20px;border-radius:10px;text-align:center;">
                    <div style="font-size:2em;">{card['icon']}</div>
                    <div style="font-size:2em;font-weight:bold;">{card['value']}</div>
                    <div style="font-size:0.9em;opacity:0.9;">{card['title']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # 位置分布和置信度分布
        st.subheader("📍 位置与置信度分析")
        col1, col2 = st.columns(2)
        
        with col1:
            heatmap_fig = builder.create_heatmap()
            st.plotly_chart(heatmap_fig, use_container_width=True)
        
        with col2:
            confidence_fig = builder.create_confidence_distribution()
            st.plotly_chart(confidence_fig, use_container_width=True)
        
        st.divider()
        
        # 时间分布
        st.subheader("⏰ 时间分布分析")
        col1, col2 = st.columns(2)
        
        with col1:
            hour_fig = builder.create_time_distribution()
            st.plotly_chart(hour_fig, use_container_width=True)
        
        with col2:
            weekday_fig = builder.create_weekday_distribution()
            st.plotly_chart(weekday_fig, use_container_width=True)
        
        st.divider()
        
        # 导出报表
        st.subheader("📥 导出报表")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 导出 JSON 报表", use_container_width=True):
                filepath = builder.export_report('json')
                st.success(f"✅ 报表已导出：{filepath}")
        
        with col2:
            if st.button("📊 导出 CSV 报表", use_container_width=True):
                filepath = builder.export_report('csv')
                st.success(f"✅ 报表已导出：{filepath}")
        
        # 原始数据
        st.divider()
        st.subheader("📋 事件明细")
        
        if engine.events:
            events_data = [e.to_dict() for e in engine.events]
            st.dataframe(events_data, use_container_width=True)
        else:
            st.info("暂无事件记录，启动系统并触发告警后将显示在这里")
    
    else:
        st.info("请启动系统以初始化数据分析模块")


# ==================== Tab 3: 录像回放 ====================
with tab3:
    render_recordings_gallery("recordings", limit=10)


# ==================== Tab 4: 通知记录 ====================
with tab4:
    st.header("📱 通知发送记录")
    
    if st.session_state.notifications_sent:
        st.dataframe(st.session_state.notifications_sent, hide_index=True, use_container_width=True)
        
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总通知次数", len(st.session_state.notifications_sent))
        with col2:
            confirmed = sum(1 for n in st.session_state.notifications_sent if n['alert_type'] == 'fall_confirmed')
            st.metric("紧急通知", confirmed)
        with col3:
            suspected = sum(1 for n in st.session_state.notifications_sent if n['alert_type'] == 'fall_suspected')
            st.metric("疑似通知", suspected)
    else:
        st.info("暂无通知记录")


# ==================== Tab 5: 趋势图表 ====================
with tab5:
    st.header("📅 趋势图表")
    
    setup_dashboard()
    
    if st.session_state.dashboard_builder:
        builder = st.session_state.dashboard_builder
        
        # 趋势图
        st.subheader("📈 事件趋势")
        
        period = st.selectbox("时间粒度", options=['hour', 'day', 'week', 'month'], index=1)
        days = st.slider("显示天数", 7, 90, 30)
        
        trend_fig = builder.create_trend_chart(period=period, days=days)
        st.plotly_chart(trend_fig, use_container_width=True)
        
        # 统计信息
        st.divider()
        st.subheader("📊 统计信息")
        
        stats = st.session_state.analytics_engine.get_statistics()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **总事件数**: {stats['total_events']}
            
            **确认摔倒**: {stats['confirmed_falls']}
            
            **疑似摔倒**: {stats['suspected_falls']}
            
            **平均置信度**: {stats['average_confidence']*100:.1f}%
            """)
        
        with col2:
            if stats['first_event']:
                st.markdown(f"""
                **首次事件**: {stats['first_event'].strftime('%Y-%m-%d %H:%M')}
                
                **最近事件**: {stats['last_event'].strftime('%Y-%m-%d %H:%M')}
                
                **监控位置数**: {stats['unique_locations']}
                
                **位置列表**: {', '.join(stats['locations'])}
                """)
            else:
                st.info("暂无事件数据")
    else:
        st.info("请启动系统以初始化数据分析模块")


# ==================== Tab 6: 报警历史 ====================
with tab6:
    st.header("📋 报警历史")
    
    if st.session_state.alert_history:
        filter_level = st.selectbox("级别", ["全部", "确认摔倒", "疑似摔倒"])
        
        if filter_level == "全部":
            filtered = st.session_state.alert_history
        elif filter_level == "确认摔倒":
            filtered = [a for a in st.session_state.alert_history if a['level'] == 'critical']
        else:
            filtered = [a for a in st.session_state.alert_history if a['level'] == 'warning']
        
        st.dataframe(filtered, hide_index=True, use_container_width=True)
    else:
        st.info("暂无报警记录")


# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.3 📊 | Powered by Streamlit + Open3D + OpenCV + Plotly</p>
    <p>GitHub: <a href='https://github.com/nanfeng2021/fall-detection-system'>nanfeng2021/fall-detection-system</a></p>
</div>
""", unsafe_allow_html=True)
