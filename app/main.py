#!/usr/bin/env python3
"""
Fall Detection System - Main Application Entry Point

启动命令:
    streamlit run app/main.py

环境变量:
    FALL_DETECTION_CONFIG: 配置文件路径
    JWT_SECRET: JWT 密钥
    DATABASE_URL: 数据库连接 URL
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import streamlit as st
from fall_detection import FallDetectionSystem, AuthService
from fall_detection.cameras import CameraManager

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化服务 ====================
@st.cache_resource
def get_auth_service():
    """获取认证服务单例"""
    return AuthService()

@st.cache_resource
def get_camera_manager():
    """获取摄像头管理器单例"""
    return CameraManager()

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ==================== 主函数 ====================
def main():
    """主应用入口"""
    
    # 检查登录状态
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    """显示登录页面"""
    st.title("🛡️ GuardianFall")
    st.subheader("室内人体摔倒实时预警系统 v1.6")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 40px; border-radius: 15px; color: white; text-align: center;'>
            <h2>🔐 用户登录</h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="admin")
            password = st.text_input("密码", type="password", placeholder="admin123")
            
            submit = st.form_submit_button("登录", use_container_width=True)
            
            if submit:
                auth_service = get_auth_service()
                success, result = auth_service.authenticate(username, password)
                
                if success:
                    st.session_state.current_user = result
                    st.session_state.authenticated = True
                    st.success("✅ 登录成功！")
                    st.rerun()
                else:
                    st.error(f"❌ {result}")

def show_main_app():
    """显示主应用"""
    user = st.session_state.current_user
    
    # 侧边栏
    with st.sidebar:
        st.title("🛡️ GuardianFall")
        st.markdown(f"**👤 {user['username']}** ({user['role']})")
        
        st.divider()
        
        menu = st.radio(
            "导航",
            ["🏠 首页", "📹 多摄像头监控", "🎯 检测仪表板", "⚙️ 系统设置"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()
    
    # 主内容区
    if menu == "🏠 首页":
        show_dashboard()
    elif menu == "📹 多摄像头监控":
        st.switch_page("pages/multi_camera_monitor.py")
    elif menu == "🎯 检测仪表板":
        st.switch_page("pages/detection_dashboard.py")
    elif menu == "⚙️ 系统设置":
        st.info("系统设置页面开发中...")

def show_dashboard():
    """显示主仪表板"""
    st.title("🏠 系统概览")
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("摄像头总数", "0", "0")
    with col2:
        st.metric("活跃检测", "0", "0")
    with col3:
        st.metric("今日告警", "0", "0")
    with col4:
        st.metric("系统运行时间", "0h 0m", "0")
    
    st.divider()
    
    # 快速操作
    st.subheader("⚡ 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📹 添加摄像头", use_container_width=True):
            st.switch_page("pages/multi_camera_monitor.py")
    
    with col2:
        if st.button("🔍 查看告警", use_container_width=True):
            st.info("告警历史页面开发中...")
    
    with col3:
        if st.button("👥 用户管理", use_container_width=True, disabled=(st.session_state.current_user.get('role') != 'admin')):
            st.switch_page("pages/user_management.py")
    
    # 系统状态
    st.divider()
    st.subheader("📊 系统状态")
    
    st.success("✅ 系统运行正常")
    st.caption(f"版本：v1.6.0 | 更新时间：2026-04-13")

if __name__ == "__main__":
    main()
