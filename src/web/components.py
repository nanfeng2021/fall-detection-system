#!/usr/bin/env python3
"""
Streamlit UI 组件模块
提供可复用的UI组件，优化渲染性能
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import time

import open3d as o3d


@dataclass
class AlertCardProps:
    """报警卡片属性"""
    title: str
    message: str
    level: str  # 'critical', 'warning', 'info'
    timestamp: datetime
    confidence: float


class AlertComponents:
    """报警相关组件"""
    
    @staticmethod
    def render_alert_card(props: AlertCardProps):
        """渲染报警卡片"""
        colors = {
            'critical': ('#ffebee', '#f44336', '🚨'),
            'warning': ('#fff3e0', '#ff9800', '⚠️'),
            'info': ('#e3f2fd', '#2196f3', 'ℹ️')
        }
        
        bg_color, border_color, icon = colors.get(props.level, colors['info'])
        
        st.markdown(f"""
        <div style="
            background-color: {bg_color};
            border-left: 5px solid {border_color};
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        ">
            <h4 style="margin: 0; color: {border_color};">{icon} {props.title}</h4>
            <p style="margin: 5px 0;">{props.message}</p>
            <small style="color: #666;">
                时间: {props.timestamp.strftime('%H:%M:%S')} | 
                置信度: {props.confidence:.0%}
            </small>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_alert_history(alerts: List[Dict], max_items: int = 10):
        """渲染报警历史列表"""
        if not alerts:
            st.info("暂无报警记录")
            return
        
        for alert in list(reversed(alerts))[-max_items:]:
            level_colors = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }
            
            emoji = level_colors.get(alert.get('level', 'info'), '🔵')
            timestamp = alert.get('timestamp', datetime.now())
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])
                
                with col1:
                    st.markdown(f"**{emoji}**")
                
                with col2:
                    st.markdown(f"**{alert.get('message', '')}**")
                    st.caption(f"{timestamp.strftime('%H:%M:%S')}")
                
                with col3:
                    confidence = alert.get('confidence', 0)
                    st.progress(min(confidence, 1.0), text=f"{confidence:.0%}")


class StatsComponents:
    """统计信息组件"""
    
    @staticmethod
    def render_stat_card(label: str, value: str, delta: Optional[str] = None,
                        help_text: Optional[str] = None):
        """渲染统计卡片"""
        st.metric(
            label=label,
            value=value,
            delta=delta,
            help=help_text
        )
    
    @staticmethod
    def render_stats_row(stats: Dict[str, Dict]):
        """渲染统计行"""
        cols = st.columns(len(stats))
        
        for col, (label, data) in zip(cols, stats.items()):
            with col:
                StatsComponents.render_stat_card(
                    label=label,
                    value=data.get('value', 'N/A'),
                    delta=data.get('delta'),
                    help_text=data.get('help')
                )


class VisualizationComponents:
    """可视化组件"""
    
    @staticmethod
    @st.cache_data(ttl=1)
    def point_cloud_to_plotly_cached(points_json: str, colors_json: str) -> go.Figure:
        """缓存的点云转Plotly（优化性能）"""
        import json
        
        points = np.array(json.loads(points_json))
        colors = np.array(json.loads(colors_json)) if colors_json else None
        
        fig = go.Figure(data=[go.Scatter3d(
            x=points[:, 0],
            y=points[:, 1],
            z=points[:, 2],
            mode='markers',
            marker=dict(
                size=2,
                color=colors if colors is not None else points[:, 2],
                colorscale='Viridis',
                opacity=0.8,
                colorbar=dict(title='高度 (m)') if colors is None else None
            ),
            name='点云'
        )])
        
        fig.update_layout(
            scene=dict(
                xaxis=dict(title='X (m)', range=[-3, 3]),
                yaxis=dict(title='Y (m)', range=[-3, 3]),
                zaxis=dict(title='Z (m)', range=[0, 2.5]),
                aspectmode='data'
            ),
            height=500,
            margin=dict(l=0, r=0, t=30, b=0),
        )
        
        return fig
    
    @staticmethod
    def render_point_cloud(pcd: o3d.geometry.PointCloud, 
                          title: str = "点云视图",
                          key: Optional[str] = None):
        """渲染点云（优化版本）"""
        points = np.asarray(pcd.points)
        
        if len(points) == 0:
            st.warning("点云为空")
            return
        
        # 降采样显示（如果点太多）
        max_display_points = 10000
        if len(points) > max_display_points:
            indices = np.random.choice(len(points), max_display_points, replace=False)
            points = points[indices]
        
        # 根据高度着色
        z_values = points[:, 2]
        colors = z_values / max(z_values.max(), 0.1)
        
        fig = go.Figure(data=[go.Scatter3d(
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
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis=dict(title='X (m)', range=[-3, 3]),
                yaxis=dict(title='Y (m)', range=[-3, 3]),
                zaxis=dict(title='Z (m)', range=[0, 2.5]),
                aspectmode='data'
            ),
            height=500,
            margin=dict(l=0, r=0, t=30, b=0),
        )
        
        st.plotly_chart(fig, use_container_width=True, key=key)
    
    @staticmethod
    def render_fps_chart(fps_history: List[float], max_points: int = 100):
        """渲染FPS趋势图"""
        if not fps_history:
            return
        
        # 限制数据点数量
        data = fps_history[-max_points:]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=data,
            mode='lines',
            name='FPS',
            line=dict(color='blue', width=2)
        ))
        
        fig.update_layout(
            title="FPS 趋势",
            xaxis_title="帧",
            yaxis_title="FPS",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    @staticmethod
    def render_processing_time_chart(time_history: List[float], max_points: int = 100):
        """渲染处理时间趋势图"""
        if not time_history:
            return
        
        data = time_history[-max_points:]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=data,
            mode='lines',
            name='处理时间',
            line=dict(color='green', width=2),
            fill='tozeroy'
        ))
        
        fig.update_layout(
            title="处理时间",
            xaxis_title="帧",
            yaxis_title="时间 (ms)",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)


class ControlComponents:
    """控制组件"""
    
    @staticmethod
    def render_control_panel(on_start: Callable, on_stop: Callable, on_reset: Callable,
                            running: bool = False):
        """渲染控制面板"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.button(
                "▶️ 启动",
                use_container_width=True,
                disabled=running,
                on_click=on_start
            )
        
        with col2:
            st.button(
                "⏹️ 停止",
                use_container_width=True,
                disabled=not running,
                on_click=on_stop
            )
        
        with col3:
            st.button(
                "🔄 重置",
                use_container_width=True,
                on_click=on_reset
            )
    
    @staticmethod
    def render_config_form(config: Dict, on_save: Callable):
        """渲染配置表单"""
        with st.form("config_form"):
            st.subheader("⚙️ 参数配置")
            
            new_config = {}
            
            new_config['voxel_size'] = st.slider(
                "体素尺寸 (m)",
                0.01, 0.2,
                config.get('voxel_size', 0.05),
                0.01
            )
            
            new_config['height_drop_threshold'] = st.slider(
                "高度骤降阈值 (m)",
                0.1, 1.0,
                config.get('height_drop_threshold', 0.3),
                0.1
            )
            
            new_config['velocity_threshold'] = st.slider(
                "速度阈值 (m/s)",
                0.2, 2.0,
                config.get('velocity_threshold', 0.5),
                0.1
            )
            
            new_config['confirmation_frames'] = st.slider(
                "确认帧数",
                1, 10,
                config.get('confirmation_frames', 2),
                1
            )
            
            submitted = st.form_submit_button("💾 保存配置", use_container_width=True)
            
            if submitted:
                on_save(new_config)
                st.success("✅ 配置已保存")


class StatusComponents:
    """状态组件"""
    
    @staticmethod
    def render_status_indicator(status: str, label: str = "状态"):
        """渲染状态指示器"""
        colors = {
            'running': '#4caf50',
            'stopped': '#f44336',
            'error': '#ff9800',
            'warning': '#ff9800',
            'idle': '#9e9e9e'
        }
        
        color = colors.get(status.lower(), colors['idle'])
        
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background-color: {color}20;
            border-radius: 5px;
        ">
            <div style="
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background-color: {color};
            "></div>
            <span><strong>{label}:</strong> {status}</span>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_progress_bar(progress: float, label: str = "进度"):
        """渲染进度条"""
        st.progress(min(progress, 1.0), text=f"{label}: {progress:.0%}")


# 便捷函数
def render_page_header(title: str, subtitle: Optional[str] = None):
    """渲染页面头部"""
    st.title(f"🚨 {title}")
    if subtitle:
        st.markdown(f"**{subtitle}**")
    st.divider()


def render_footer():
    """渲染页脚"""
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>GuardianFall 摔倒检测系统 | Powered by Streamlit + Open3D</p>
    </div>
    """, unsafe_allow_html=True)


# 测试代码
if __name__ == "__main__":
    print("🧪 测试UI组件模块...")
    
    # 测试数据类
    alert_props = AlertCardProps(
        title="测试报警",
        message="这是一个测试报警消息",
        level="warning",
        timestamp=datetime.now(),
        confidence=0.85
    )
    
    print(f"报警卡片属性: {alert_props}")
    
    # 测试统计组件
    stats = {
        "FPS": {"value": "30.5", "delta": "+2.3"},
        "延迟": {"value": "33ms", "delta": "-5ms"},
        "人数": {"value": "2", "help": "当前检测到的人数"}
    }
    
    print(f"统计数据: {stats}")
    
    print("\n✅ 组件模块测试完成!")
