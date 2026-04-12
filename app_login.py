#!/usr/bin/env python3
"""
摔倒检测系统 - 登录页面
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="摔倒检测系统 - 登录",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== CSS 样式 ====================
st.markdown("""
<style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background-color: #ffffff;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .header {
        text-align: center;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State 初始化 ====================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'auth_error' not in st.session_state:
    st.session_state.auth_error = None

# ==================== 导入认证服务 ====================
try:
    from src.auth.auth_service import AuthService, create_access_token
    from src.auth.models import LoginRequest, UserRole
    AUTH_ENABLED = True
except Exception as e:
    st.warning(f"⚠️ 认证模块加载失败：{e}")
    AUTH_ENABLED = False

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
        
        # 记录登录日志
        st.success(f"✅ 欢迎回来，{user.username}！")
        return True
        
    except Exception as e:
        st.session_state.auth_error = str(e)
        return False

# ==================== 登出函数 ====================
def logout():
    """用户登出"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

# ==================== 主界面 ====================
if st.session_state.authenticated:
    # 已登录，重定向到主应用
    st.switch_page("app_main.py")
else:
    # 显示登录表单
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo 和标题
        st.markdown("<div class='header'>", unsafe_allow_html=True)
        st.title("🛡️ GuardianFall")
        st.subheader("室内人体摔倒实时预警系统")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 登录表单
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
            
            submit_button = st.form_submit_button("登录")
            
            if submit_button:
                if not username or not password:
                    st.error("❌ 请输入用户名和密码")
                else:
                    login(username, password)
        
        # 显示错误信息
        if st.session_state.auth_error:
            st.error(f"❌ {st.session_state.auth_error}")
        
        # 提示信息
        st.info("""
        **测试账户**:
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
        st.markdown("GuardianFall v1.1.0 | Powered by AI")
        st.markdown("</div>", unsafe_allow_html=True)
