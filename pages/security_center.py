#!/usr/bin/env python3
"""
安全中心 - 用户自助安全管理

功能:
- 双因素认证设置向导
- 修改密码
- 查看登录历史
- 管理活跃会话
- 备用码查看
"""

import streamlit as st
import qrcode
import base64
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="安全中心",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 导入服务 ====================
try:
    from src.auth.auth_service_sqlite import AuthService
    from src.security.two_factor_auth import get_two_factor_auth
    from src.security.login_lock import get_lock_manager
    from src.database.db import get_db_connection
    from src.auth.models import ChangePasswordRequest, UserRole
    AUTH_ENABLED = True
except Exception as e:
    print(f"⚠️ 模块加载失败：{e}")
    AUTH_ENABLED = False

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ==================== 权限检查 ====================
def check_login():
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()

check_login()

# ==================== 辅助函数 ====================
def get_auth_service():
    return AuthService()

def get_two_factor():
    return get_two_factor_auth()

def get_lock_mgr():
    return get_lock_manager()

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🔐 安全中心")
    
    user = st.session_state.current_user
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <p style="margin: 0; font-weight: bold;">👤 {user['username']}</p>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">{'👑 管理员' if user['role'] == 'admin' else user['role']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    menu = ["📱 双因素认证", "🔑 修改密码", "📊 登录历史", "💻 活跃会话"]
    selected = st.radio("菜单", menu, label_visibility="collapsed")
    
    st.divider()
    
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

# ==================== 主界面 ====================
st.title("🔐 安全中心")
st.markdown("**管理您的账户安全设置**")

auth_service = get_auth_service()
two_factor = get_two_factor()
user_id = st.session_state.current_user['id']

# ==================== Tab 1: 双因素认证 ====================
if selected == "📱 双因素认证":
    st.header("📱 双因素认证 (2FA)")
    
    # 检查当前状态
    is_enabled = two_factor.is_2fa_enabled(user_id)
    
    if is_enabled:
        # ✅ 已启用状态
        st.success("✅ 双因素认证已启用")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **如何禁用 2FA:**
            
            1. 打开验证器 App
            2. 输入当前 6 位验证码
            3. 点击【禁用】按钮
            """)
            
            disable_code = st.text_input(
                "输入验证码以禁用",
                placeholder="6 位数字",
                key="disable_2fa"
            )
            
            if st.button("🔴 禁用 2FA", type="secondary", disabled=not disable_code):
                if two_factor.verify_code(user_id, disable_code):
                    two_factor.disable_2fa(user_id)
                    st.success("✅ 2FA 已禁用")
                    st.rerun()
                else:
                    st.error("❌ 验证码错误")
        
        with col2:
            st.info("""
            **备用码:**
            
            备用码用于手机丢失时恢复访问。
            每个备用码只能使用一次。
            """)
            
            if st.button("🔄 重新生成备用码"):
                new_codes = two_factor.regenerate_backup_codes(user_id)
                st.warning("⚠️ 请立即保存以下备用码（只显示一次）:")
                
                codes_text = "\n".join(new_codes)
                st.code(codes_text, language="text")
                
                st.download_button(
                    label="📥 下载备用码",
                    data=codes_text,
                    file_name=f"backup_codes_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
    
    else:
        # ❌ 未启用状态 - 设置向导
        st.info("📱 启用双因素认证可以显著提高账户安全性")
        
        # 步骤指示器
        step = st.session_state.get('2fa_step', 1)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("步骤 1", "生成密钥" if step >= 1 else "等待")
        with col2:
            st.metric("步骤 2", "扫描二维码" if step >= 2 else "等待")
        with col3:
            st.metric("步骤 3", "验证启用" if step >= 3 else "等待")
        
        st.divider()
        
        # 步骤 1: 生成密钥
        if step == 1:
            st.subheader("步骤 1: 生成密钥")
            
            if st.button("🔑 生成密钥", type="primary"):
                secret, uri, backup_codes = two_factor.setup_2fa(
                    user_id=user_id,
                    username=st.session_state.current_user['username']
                )
                
                st.session_state['2fa_secret'] = secret
                st.session_state['2fa_uri'] = uri
                st.session_state['2fa_backup_codes'] = backup_codes
                st.session_state['2fa_step'] = 2
                
                st.rerun()
        
        # 步骤 2: 扫描二维码
        elif step == 2:
            st.subheader("步骤 2: 扫描二维码")
            
            uri = st.session_state.get('2fa_uri')
            secret = st.session_state.get('2fa_secret')
            backup_codes = st.session_state.get('2fa_backup_codes')
            
            if not uri:
                st.error("请先完成步骤 1")
                st.stop()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**1. 下载验证器 App**")
                st.markdown("""
                - **Google Authenticator** ([iOS](https://apps.apple.com/app/google-authenticator/id388497605) | [Android](https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2))
                - **Microsoft Authenticator** ([iOS](https://apps.apple.com/app/microsoft-authenticator/id983156458) | [Android](https://play.google.com/store/apps/details?id=com.azure.authenticator))
                - **Authy** ([官网](https://authy.com/))
                """)
                
                st.markdown("**2. 扫描二维码**")
                qr_image = two_factor.generate_qr_code(uri)
                st.image(qr_image, caption="扫描此二维码", width=300)
                
                st.markdown("**或手动输入密钥:**")
                st.code(secret, language="text")
            
            with col2:
                st.markdown("**3. 保存备用码**")
                st.warning("⚠️ 这些备用码只显示一次，请立即保存！")
                
                codes_text = "\n".join(backup_codes)
                st.code(codes_text, language="text")
                
                st.download_button(
                    label="📥 下载备用码",
                    data=codes_text,
                    file_name=f"backup_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key="download_backup"
                )
                
                st.markdown("---")
                
                if st.checkbox("✅ 我已保存备用码并扫描了二维码"):
                    st.session_state['2fa_step'] = 3
                    st.rerun()
        
        # 步骤 3: 验证启用
        elif step == 3:
            st.subheader("步骤 3: 验证并启用")
            
            st.info("📱 打开验证器 App，输入显示的 6 位验证码")
            
            verify_code = st.text_input(
                "验证码",
                placeholder="6 位数字",
                max_chars=6,
                key="verify_2fa"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ 验证并启用", type="primary"):
                    if two_factor.enable_2fa(user_id, verify_code):
                        st.success("🎉 双因素认证已启用！")
                        st.balloons()
                        
                        # 清理 session
                        for key in ['2fa_secret', '2fa_uri', '2fa_backup_codes', '2fa_step']:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.rerun()
                    else:
                        st.error("❌ 验证码错误，请重试")
            
            with col2:
                if st.button("⬅️ 上一步"):
                    st.session_state['2fa_step'] = 2
                    st.rerun()

# ==================== Tab 2: 修改密码 ====================
elif selected == "🔑 修改密码":
    st.header("🔑 修改密码")
    
    with st.form("change_password_form"):
        old_password = st.text_input("当前密码", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            new_password = st.text_input("新密码", type="password", help="至少 8 个字符，包含大小写字母和数字")
        with col2:
            confirm_password = st.text_input("确认新密码", type="password")
        
        submitted = st.form_submit_button("💾 修改密码", type="primary")
        
        if submitted:
            errors = []
            
            # 验证
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
                try:
                    auth_service.change_password(
                        user_id=user_id,
                        old_password=old_password,
                        new_password=new_password
                    )
                    
                    st.success("✅ 密码修改成功！")
                    
                    # 询问是否撤销所有会话
                    if st.checkbox("撤销其他设备的登录状态（推荐）"):
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE user_sessions SET is_active = 0
                                WHERE user_id = ?
                            """, (user_id,))
                        st.success("✅ 其他设备已登出")
                    
                except Exception as e:
                    st.error(f"❌ 修改失败：{e}")

# ==================== Tab 3: 登录历史 ====================
elif selected == "📊 登录历史":
    st.header("📊 登录历史")
    
    # 获取日志
    logs = auth_service.get_login_logs(user_id=user_id, limit=100)
    
    if not logs:
        st.info("暂无登录记录")
    else:
        # 统计
        total = len(logs)
        success = sum(1 for log in logs if log['success'])
        failed = total - success
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总登录次数", total)
        with col2:
            st.metric("成功", success)
        with col3:
            st.metric("失败", failed)
        
        st.divider()
        
        # 表格
        log_data = []
        for log in logs:
            status = "✅" if log['success'] else "❌"
            time_str = datetime.fromisoformat(log['logged_at']).strftime("%Y-%m-%d %H:%M")
            
            log_data.append({
                '时间': time_str,
                '状态': f"{status} {'成功' if log['success'] else '失败'}",
                'IP 地址': log['ip_address'] or '未知',
                '设备': (log['user_agent'] or '未知')[:50],
                '失败原因': log['failure_reason'] or '-'
            })
        
        st.dataframe(log_data, use_container_width=True, hide_index=True)

# ==================== Tab 4: 活跃会话 ====================
elif selected == "💻 活跃会话":
    st.header("💻 活跃会话管理")
    
    # 获取活跃会话
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, device_info, ip_address, created_at, expires_at
            FROM user_sessions
            WHERE user_id = ? AND is_active = 1 AND expires_at > ?
            ORDER BY created_at DESC
        """, (user_id, datetime.now().isoformat()))
        
        sessions = cursor.fetchall()
    
    if not sessions:
        st.info("暂无活跃会话")
    else:
        st.info(f"当前有 **{len(sessions)}** 个活跃会话")
        
        for session in sessions:
            is_current = session['ip_address'] == st.session_state.get('client_ip', '')
            
            with st.expander(f"{'📍 当前设备' if is_current else '💻'} {session['device_info'] or '未知设备'} - {session['ip_address']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    - **创建时间**: {datetime.fromisoformat(session['created_at']).strftime('%Y-%m-%d %H:%M')}
                    - **过期时间**: {datetime.fromisoformat(session['expires_at']).strftime('%Y-%m-%d %H:%M')}
                    - **IP 地址**: {session['ip_address']}
                    """)
                
                with col2:
                    if not is_current:
                        if st.button("🚫 下线", key=f"revoke_{session['id']}"):
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE user_sessions SET is_active = 0
                                WHERE id = ?
                            """, (session['id'],))
                            conn.commit()
                            st.success("✅ 已下线")
                            st.rerun()
                    else:
                        st.caption("当前会话")
        
        # 批量操作
        st.divider()
        
        if st.button("🚫 下线所有其他设备", type="secondary"):
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions SET is_active = 0
                    WHERE user_id = ? AND id != (
                        SELECT id FROM user_sessions
                        WHERE user_id = ? AND is_active = 1
                        ORDER BY created_at DESC LIMIT 1
                    )
                """, (user_id, user_id))
            st.success("✅ 已下线所有其他设备")
            st.rerun()

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.5 | 安全中心</p>
    <p>最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
""".format(datetime=datetime), unsafe_allow_html=True)
