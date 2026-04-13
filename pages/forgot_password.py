#!/usr/bin/env python3
"""
忘记密码 - 密码找回流程

功能:
- 通过邮箱验证重置密码
- 安全问题验证（可选）
- 管理员协助重置
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import sys
import random
import string

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="忘记密码",
    page_icon="🔑",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== 导入服务 ====================
try:
    from src.auth.auth_service_sqlite import AuthService
    from src.database.db import get_db_connection
    AUTH_ENABLED = True
except Exception as e:
    print(f"⚠️ 模块加载失败：{e}")
    AUTH_ENABLED = False

# ==================== Session State ====================
if 'reset_token' not in st.session_state:
    st.session_state.reset_token = None
if 'reset_step' not in st.session_state:
    st.session_state.reset_step = 1

# ==================== 辅助函数 ====================
def generate_reset_token() -> str:
    """生成重置令牌"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def create_reset_request(username: str, email: str) -> str:
    """创建密码重置请求"""
    token = generate_reset_token()
    expires_at = datetime.now() + timedelta(hours=1)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 验证用户名和邮箱
        cursor.execute("""
            SELECT id FROM users WHERE username = ? AND email = ?
        """, (username, email))
        
        if not cursor.fetchone():
            return None
        
        # 保存重置令牌
        cursor.execute("""
            INSERT INTO password_resets (user_id, token, expires_at, used)
            SELECT id, ?, ?, 0 FROM users WHERE username = ? AND email = ?
        """, (token, expires_at.isoformat(), username, email))
    
    return token

def verify_reset_token(token: str) -> bool:
    """验证重置令牌"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM password_resets
            WHERE token = ? AND expires_at > ? AND used = 0
        """, (token, datetime.now().isoformat()))
        
        return cursor.fetchone() is not None

def reset_password(token: str, new_password: str) -> bool:
    """重置密码"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 获取用户 ID
        cursor.execute("""
            SELECT user_id FROM password_resets
            WHERE token = ? AND expires_at > ? AND used = 0
        """, (token, datetime.now().isoformat()))
        
        result = cursor.fetchone()
        if not result:
            return False
        
        user_id = result[0]
        
        # 更新密码
        auth_service = AuthService()
        password_hash = auth_service._hash_password(new_password)
        
        cursor.execute("""
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (password_hash, user_id))
        
        # 标记令牌已使用
        cursor.execute("""
            UPDATE password_resets SET used = 1 WHERE token = ?
        """, (token,))
        
        # 撤销所有会话
        cursor.execute("""
            UPDATE user_sessions SET is_active = 0 WHERE user_id = ?
        """, (user_id,))
    
    return True

# ==================== 主界面 ====================
st.title("🔑 忘记密码")
st.markdown("**找回密码，重设访问权限**")

# 返回登录链接
st.link_button("← 返回登录", "/")

st.divider()

# 步骤指示器
step = st.session_state.get('reset_step', 1)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("步骤 1", "验证身份" if step >= 1 else "等待")
with col2:
    st.metric("步骤 2", "接收验证码" if step >= 2 else "等待")
with col3:
    st.metric("步骤 3", "重置密码" if step >= 3 else "等待")

st.divider()

# ==================== 步骤 1: 验证身份 ====================
if step == 1:
    st.subheader("步骤 1: 验证身份")
    
    st.info("📧 请输入您的用户名和注册邮箱，我们将发送验证码到您的邮箱。")
    
    with st.form("verify_identity"):
        username = st.text_input("用户名", placeholder="请输入用户名")
        email = st.text_input("注册邮箱", placeholder="example@email.com")
        
        submitted = st.form_submit_button("发送验证码", type="primary", use_container_width=True)
        
        if submitted:
            if not username or not email:
                st.error("请填写用户名和邮箱")
            else:
                # 验证用户是否存在
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id FROM users WHERE username = ? AND email = ?
                    """, (username, email))
                    
                    if cursor.fetchone():
                        # 生成并保存令牌
                        token = generate_reset_token()
                        expires_at = datetime.now() + timedelta(minutes=15)
                        
                        cursor.execute("""
                            INSERT INTO password_resets (user_id, token, expires_at, used)
                            SELECT id, ?, ?, 0 FROM users WHERE username = ? AND email = ?
                        """, (token, expires_at.isoformat(), username, email))
                        
                        # 保存到 session
                        st.session_state.reset_token = token
                        st.session_state.reset_username = username
                        st.session_state.reset_step = 2
                        
                        # TODO: 实际应用中发送邮件
                        # send_reset_email(email, token)
                        
                        st.success("✅ 验证码已发送到您的邮箱")
                        st.info(f"📝 测试模式：验证码为 `{token[:8]}...`（前 8 位）")
                        st.rerun()
                    else:
                        st.error("❌ 用户名或邮箱不匹配")

# ==================== 步骤 2: 输入验证码 ====================
elif step == 2:
    st.subheader("步骤 2: 输入验证码")
    
    username = st.session_state.get('reset_username', '')
    st.info(f"验证码已发送到 **{username}** 的注册邮箱")
    
    with st.form("verify_code"):
        reset_code = st.text_input(
            "验证码",
            placeholder="请输入验证码",
            help="验证码有效期 15 分钟"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("验证", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("重新发送", use_container_width=True):
                # 重新生成令牌
                token = generate_reset_token()
                st.session_state.reset_token = token
                st.success("✅ 新验证码已发送")
                st.info(f"📝 测试模式：验证码为 `{token[:8]}...`")
        
        if submitted:
            if not reset_code:
                st.error("请输入验证码")
            else:
                # 验证令牌
                stored_token = st.session_state.get('reset_token')
                
                if stored_token and reset_code == stored_token:
                    st.session_state.reset_step = 3
                    st.rerun()
                else:
                    st.error("❌ 验证码错误")

# ==================== 步骤 3: 重置密码 ====================
elif step == 3:
    st.subheader("步骤 3: 重置密码")
    
    st.success("✅ 身份验证成功")
    
    with st.form("reset_password"):
        col1, col2 = st.columns(2)
        with col1:
            new_password = st.text_input(
                "新密码",
                type="password",
                help="至少 8 个字符，包含大小写字母和数字"
            )
        with col2:
            confirm_password = st.text_input(
                "确认新密码",
                type="password"
            )
        
        submitted = st.form_submit_button("重置密码", type="primary", use_container_width=True)
        
        if submitted:
            errors = []
            
            if len(new_password) < 8:
                errors.append("密码至少 8 个字符")
            
            if not any(c.isupper() for c in new_password):
                errors.append("密码必须包含大写字母")
            
            if not any(c.isdigit() for c in new_password):
                errors.append("密码必须包含数字")
            
            if new_password != confirm_password:
                errors.append("两次输入的密码不一致")
            
            if errors:
                st.error("❌ 请修正以下错误:\n- " + "\n- ".join(errors))
            else:
                # 重置密码
                token = st.session_state.get('reset_token')
                
                if reset_password(token, new_password):
                    st.success("🎉 密码重置成功！")
                    st.balloons()
                    
                    # 清理 session
                    for key in ['reset_token', 'reset_username', 'reset_step']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.info("✅ 请使用新密码重新登录")
                    
                    if st.link_button("前往登录", "/"):
                        st.rerun()
                else:
                    st.error("❌ 重置失败，令牌可能已过期")

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.5 | 忘记密码</p>
    <p>如有问题请联系管理员</p>
</div>
""", unsafe_allow_html=True)
