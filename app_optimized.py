#!/usr/bin/env python3
"""
摔倒检测系统 - Streamlit 可视化界面（带用户认证）

启动命令:
    streamlit run app_optimized.py --server.address 0.0.0.0 --server.port 8501
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
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_error' not in st.session_state:
    st.session_state.auth_error = None
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

# ==================== 导入认证服务 ====================
try:
    from src.auth.auth_service import AuthService, create_access_token
    from src.auth.models import LoginRequest, UserRole
    AUTH_ENABLED = True
except Exception as e:
    print(f"⚠️ 认证模块加载失败：{e}")
    AUTH_ENABLED = False

# ==================== 登出函数 ====================
def logout():
    """用户登出"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

# ==================== 登录函数 ====================
def login(username: str, password: str):
    """用户登录"""
    if not AUTH_ENABLED:
        # 如果认证模块不可用，允许直接登录
        st.session_state.authenticated = True
        st.session_state.current_user = {"username": "admin", "role": "admin"}
        return True
    
    try:
        auth_service = AuthService()
        request = LoginRequest(username=username, password=password)
        user, token = auth_service.login(request)
        
        # 保存用户信息到 session
        st.session_state.authenticated = True
        st.session_state.current_user = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "token": token
        }
        
        return True
        
    except Exception as e:
        st.session_state.auth_error = str(e)
        return False

# ==================== 主程序 ====================

# 检查是否已登录
if not st.session_state.authenticated:
    # ========== 登录页面 ==========
    
    # CSS 样式
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 80px auto;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .login-form {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 30px;
        border-radius: 10px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Logo 和标题
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.title("🛡️ GuardianFall")
        st.subheader("室内人体摔倒实时预警系统")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 登录表单
        st.markdown("<div class='login-form'>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 用户登录")
            
            username = st.text_input(
                "用户名",
                placeholder="请输入用户名",
                help="默认管理员账户：admin"
            )
            
            password = st.text_input(
                "密码",
                type="password",
                placeholder="请输入密码",
                help="默认密码：admin123"
            )
            
            submit_button = st.form_submit_button("登录", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("❌ 请输入用户名和密码")
                else:
                    if login(username, password):
                        st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 提示信息
        st.info("""
        **📝 测试账户**:
        - 用户名：`admin`
        - 密码：`admin123`
        
        ⚠️ 首次使用请修改默认密码！
        """)
        
        # 页脚
        st.markdown("---")
        st.markdown(
            "<div style='text-align: center; color: #666; font-size: 12px;'>",
            unsafe_allow_html=True
        )
        st.markdown("GuardianFall v1.1.0 | 集成用户认证 + 监控告警")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # ========== 主界面（已登录）==========
    
    # 获取当前用户信息
    current_user = st.session_state.current_user
    username = current_user.get('username', 'Unknown')
    user_role = current_user.get('role', 'viewer')
    
    # ==================== 侧边栏 ====================
    with st.sidebar:
        # 用户信息卡片
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 10px; margin-bottom: 20px; color: white;'>
            <p style='margin: 0; font-size: 14px; opacity: 0.9;'>👤 当前用户</p>
            <h3 style='margin: 10px 0;'>{username}</h3>
            <p style='margin: 0; font-size: 12px; opacity: 0.8;'>角色：{user_role.upper()}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 功能菜单
        st.markdown("### 📋 功能菜单")
        menu_options = ["🎯 实时监控"]
        if user_role in ["admin", "operator"]:
            menu_options.extend(["📊 统计图表", "📋 报警历史"])
        if user_role == "admin":
            menu_options.extend(["⚙️ 系统设置", "👥 用户管理"])
        
        selected_menu = st.radio("导航", menu_options, label_visibility="collapsed")
        
        st.divider()
        
        # 登出按钮
        if st.button("🚪 退出登录", use_container_width=True, type="secondary"):
            logout()
        
        # 系统状态
        st.markdown("---")
        st.markdown("### 📊 系统状态")
        st.metric("FPS", "20", "0")
        st.metric("运行时间", "2h 30m", "0")
    
    # ==================== 主内容区域 ====================
    
    if selected_menu == "🎯 实时监控":
        # 页面标题
        st.title("🎯 实时监控")
        st.markdown("---")
        
        # 控制按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if not st.session_state.running:
                if st.button("▶️ 启动监控", use_container_width=True, type="primary"):
                    st.session_state.running = True
                    st.rerun()
            else:
                if st.button("⏹️ 停止监控", use_container_width=True, type="secondary"):
                    st.session_state.running = False
                    st.rerun()
        
        st.markdown("")
        
        # 显示状态
        if st.session_state.running:
            st.success("✅ 监控系统运行中")
        else:
            st.info("ℹ️ 点击【启动监控】按钮开始")
        
        # 模拟点云可视化
        if st.session_state.running:
            # 生成模拟数据
            frame_id = st.session_state.current_frame
            
            # 地面点云
            ground_x = np.random.uniform(0, 4, 500)
            ground_y = np.random.uniform(0, 4, 500)
            mask = ((ground_x < 1.5) | (ground_x > 2.5)) | ((ground_y < 1.5) | (ground_y > 2.5))
            ground_points = np.column_stack([
                ground_x[mask],
                ground_y[mask],
                np.zeros_like(ground_x[mask])
            ])
            
            # 人体点云（简化版）
            person_center = [2.0, 2.0, 0.85]
            person_radius = 0.3
            n_points = 200
            theta = np.random.uniform(0, 2*np.pi, n_points)
            phi = np.random.uniform(0, np.pi, n_points)
            person_x = person_center[0] + person_radius * np.sin(phi) * np.cos(theta)
            person_y = person_center[1] + person_radius * np.sin(phi) * np.sin(theta)
            person_z = person_center[2] + person_radius * np.cos(phi)
            person_points = np.column_stack([person_x, person_y, person_z])
            
            # 合并点云
            all_points = np.vstack([ground_points, person_points])
            
            # 创建 3D 散点图
            fig = go.Figure(data=[go.Scatter3d(
                x=all_points[:, 0],
                y=all_points[:, 1],
                z=all_points[:, 2],
                mode='markers',
                marker=dict(size=2, color=all_points[:, 2], colorscale='Viridis'),
                name='点云'
            )])
            
            fig.update_layout(
                scene=dict(
                    xaxis=dict(title='X (m)', range=[0, 4]),
                    yaxis=dict(title='Y (m)', range=[0, 4]),
                    zaxis=dict(title='Z (m)', range=[0, 3])
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 更新帧数
            st.session_state.current_frame += 1
            
            # 自动刷新
            time.sleep(0.05)
            st.rerun()
    
    elif selected_menu == "📊 统计图表":
        st.title("📊 统计图表")
        st.markdown("---")
        st.info("统计功能开发中...")
    
    elif selected_menu == "📋 报警历史":
        st.title("📋 报警历史")
        st.markdown("---")
        st.info("报警历史查询开发中...")
    
    elif selected_menu == "⚙️ 系统设置":
        st.title("⚙️ 系统设置")
        st.markdown("---")
        st.info("系统设置开发中...（仅管理员可见）")
    
    elif selected_menu == "👥 用户管理":
        st.title("👥 用户管理")
        st.markdown("---")
        st.info("用户管理功能开发中...（仅管理员可见）")
