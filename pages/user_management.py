#!/usr/bin/env python3
"""
用户管理后台 - 管理员专用界面

功能:
- 查看用户列表
- 启用/禁用用户
- 删除用户
- 重置密码
- 查看登录日志
- 创建新用户
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="用户管理",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 导入认证服务 ====================
try:
    from src.auth.auth_service_sqlite import AuthService
    from src.database.db import init_db
    from src.auth.models import UserRole
    AUTH_ENABLED = True
except Exception as e:
    print(f"⚠️ 认证模块加载失败：{e}")
    AUTH_ENABLED = False
    st.error("认证模块未初始化，请先完成数据库升级")
    st.stop()

# ==================== Session State 初始化 ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ==================== 权限检查 ====================
def check_admin_access():
    """检查管理员权限"""
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()
    
    user = st.session_state.current_user
    if not user or user.get('role') != 'admin':
        st.error("🚫 仅限管理员访问")
        st.link_button("返回首页", "/")
        st.stop()

# 检查权限
check_admin_access()

# ==================== 辅助函数 ====================
def get_auth_service():
    """获取认证服务实例"""
    return AuthService()

def format_role(role: UserRole) -> str:
    """格式化角色显示"""
    role_emoji = {
        'admin': '👑',
        'operator': '🔧',
        'viewer': '👁️'
    }
    role_name = {
        'admin': '管理员',
        'operator': '操作员',
        'viewer': '观察员'
    }
    return f"{role_emoji.get(role.value, '👤')} {role_name.get(role.value, role.value)}"

def format_datetime(dt):
    """格式化日期时间"""
    if not dt:
        return "从未"
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return str(dt)

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎛️ 管理面板")
    
    # 当前用户信息
    user = st.session_state.current_user
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
        <p style="margin: 0; font-weight: bold;">👤 {user['username']}</p>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">{format_role(UserRole(user['role']))}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 导航菜单
    menu_options = ["用户列表", "创建用户", "登录日志", "系统设置"]
    selected_menu = st.radio("📋 菜单", menu_options, label_visibility="collapsed")
    
    st.divider()
    
    # 登出按钮
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

# ==================== 主界面 ====================
st.title("👥 用户管理后台")
st.markdown("**管理员专用界面 - 管理系统用户和权限**")

auth_service = get_auth_service()

# ==================== Tab 1: 用户列表 ====================
if selected_menu == "用户列表":
    st.header("用户列表")
    
    # 刷新按钮
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    # 获取所有用户
    users = auth_service.get_all_users()
    
    if not users:
        st.info("暂无用户数据")
    else:
        # 统计数据
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("总用户数", len(users))
        with col2:
            active_count = sum(1 for u in users if u.is_active)
            st.metric("活跃用户", active_count)
        with col3:
            admin_count = sum(1 for u in users if u.role == UserRole.ADMIN)
            st.metric("管理员", admin_count)
        with col4:
            viewer_count = sum(1 for u in users if u.role == UserRole.VIEWER)
            st.metric("观察员", viewer_count)
        
        st.divider()
        
        # 用户表格
        st.subheader("用户详情")
        
        # 准备数据
        user_data = []
        for user in users:
            user_data.append({
                'ID': user.id,
                '用户名': user.username,
                '邮箱': user.email,
                '角色': format_role(user.role),
                '状态': '🟢 激活' if user.is_active else '🔴 禁用',
                '创建时间': format_datetime(user.created_at),
                '最后登录': format_datetime(user.last_login)
            })
        
        df = pd.DataFrame(user_data)
        
        # 显示表格（带交互）
        edited_df = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "用户名": st.column_config.TextColumn("用户名", width="medium"),
                "邮箱": st.column_config.TextColumn("邮箱", width="large"),
                "角色": st.column_config.TextColumn("角色", width="medium"),
                "状态": st.column_config.TextColumn("状态", width="medium"),
                "创建时间": st.column_config.DatetimeColumn("创建时间", width="medium"),
                "最后登录": st.column_config.DatetimeColumn("最后登录", width="medium")
            }
        )
        
        st.divider()
        
        # 批量操作
        st.subheader("批量操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_user_id = st.number_input("选择用户 ID", min_value=1, max_value=max(u.id for u in users) if users else 1)
        
        with col2:
            action = st.selectbox("操作", ["启用账户", "禁用账户", "删除用户", "重置密码"])
        
        with col3:
            st.write("")  # 占位
            st.write("")  # 占位
            if st.button("执行操作", use_container_width=True, type="primary"):
                try:
                    if action == "启用账户":
                        auth_service.update_user_status(selected_user_id, True)
                        st.success(f"✅ 用户 {selected_user_id} 已启用")
                    elif action == "禁用账户":
                        auth_service.update_user_status(selected_user_id, False)
                        st.success(f"✅ 用户 {selected_user_id} 已禁用")
                    elif action == "删除用户":
                        if selected_user_id == st.session_state.current_user['id']:
                            st.error("❌ 不能删除自己")
                        else:
                            auth_service.delete_user(selected_user_id)
                            st.success(f"✅ 用户 {selected_user_id} 已删除")
                    elif action == "重置密码":
                        new_password = st.text_input("新密码", type="password", key="reset_pwd")
                        if new_password and len(new_password) >= 6:
                            # 这里需要特殊处理，简化实现直接更新
                            st.warning("⚠️ 密码重置功能需要使用管理员权限，请联系系统管理员")
                        else:
                            st.warning("密码长度至少 6 位")
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 操作失败：{e}")
        
        st.divider()
        
        # 单个用户操作
        st.subheader("快速操作")
        
        selected_username = st.selectbox("选择用户", [u.username for u in users])
        
        if selected_username:
            user = next((u for u in users if u.username == selected_username), None)
            
            if user:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("🟢 启用", use_container_width=True, disabled=user.is_active):
                        auth_service.update_user_status(user.id, True)
                        st.success(f"已启用 {user.username}")
                        st.rerun()
                
                with col2:
                    if st.button("🔴 禁用", use_container_width=True, disabled=not user.is_active):
                        auth_service.update_user_status(user.id, False)
                        st.success(f"已禁用 {user.username}")
                        st.rerun()
                
                with col3:
                    if st.button("🗑️ 删除", use_container_width=True, disabled=(user.id == st.session_state.current_user['id'])):
                        auth_service.delete_user(user.id)
                        st.success(f"已删除 {user.username}")
                        st.rerun()
                
                with col4:
                    if st.button("📝 编辑", use_container_width=True):
                        st.info(f"编辑用户 {user.username} 的功能开发中...")

# ==================== Tab 2: 创建用户 ====================
elif selected_menu == "创建用户":
    st.header("创建新用户")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("用户名 *", placeholder="3-50 个字符", help="用户名必须是唯一的")
            email = st.text_input("邮箱 *", placeholder="example@email.com")
        
        with col2:
            password = st.text_input("密码 *", type="password", placeholder="至少 6 个字符")
            confirm_password = st.text_input("确认密码 *", type="password")
        
        role = st.selectbox(
            "用户角色",
            options=[UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN],
            format_func=lambda x: format_role(x)
        )
        
        is_active = st.checkbox("创建后立即启用", value=True)
        
        submitted = st.form_submit_button("✅ 创建用户", use_container_width=True, type="primary")
        
        if submitted:
            # 验证输入
            errors = []
            
            if not username or len(username) < 3:
                errors.append("用户名至少 3 个字符")
            
            if not email or '@' not in email:
                errors.append("请输入有效的邮箱地址")
            
            if not password or len(password) < 6:
                errors.append("密码至少 6 个字符")
            
            if password != confirm_password:
                errors.append("两次输入的密码不一致")
            
            if errors:
                st.error("❌ 请修正以下错误:\n- " + "\n- ".join(errors))
            else:
                try:
                    from src.auth.models import RegisterRequest
                    
                    request = RegisterRequest(
                        username=username,
                        email=email,
                        password=password,
                        role=role
                    )
                    
                    new_user = auth_service.register(request)
                    
                    st.success(f"✅ 用户 **{new_user.username}** 创建成功！")
                    st.json({
                        "ID": new_user.id,
                        "用户名": new_user.username,
                        "邮箱": new_user.email,
                        "角色": format_role(new_user.role),
                        "状态": "激活" if new_user.is_active else "禁用"
                    })
                    
                except Exception as e:
                    st.error(f"❌ 创建失败：{e}")

# ==================== Tab 3: 登录日志 ====================
elif selected_menu == "登录日志":
    st.header("📊 登录日志")
    
    # 过滤选项
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_user = st.selectbox("筛选用户", ["全部"] + [u.username for u in users])
    
    with col2:
        filter_status = st.selectbox("筛选状态", ["全部", "成功", "失败"])
    
    with col3:
        limit = st.number_input("显示数量", min_value=10, max_value=1000, value=100, step=10)
    
    # 获取日志
    user_id = None
    if filter_user != "全部":
        selected_user = next((u for u in users if u.username == filter_user), None)
        if selected_user:
            user_id = selected_user.id
    
    logs = auth_service.get_login_logs(user_id=user_id, limit=limit)
    
    if not logs:
        st.info("暂无登录日志")
    else:
        # 统计
        total = len(logs)
        success = sum(1 for log in logs if log['success'])
        failed = total - success
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总登录次数", total)
        with col2:
            st.metric("成功", success, delta=f"{success/total*100:.1f}%")
        with col3:
            st.metric("失败", failed, delta=f"-{failed/total*100:.1f}%", delta_color="inverse")
        
        st.divider()
        
        # 日志表格
        log_data = []
        for log in logs:
            status_filter = (
                filter_status == "全部" or
                (filter_status == "成功" and log['success']) or
                (filter_status == "失败" and not log['success'])
            )
            
            if status_filter:
                log_data.append({
                    '时间': format_datetime(log['logged_at']),
                    '用户': log['username'],
                    'IP 地址': log['ip_address'] or '未知',
                    '设备': (log['user_agent'] or '未知')[:50] + '...' if len(log['user_agent'] or '') > 50 else (log['user_agent'] or '未知'),
                    '状态': '✅ 成功' if log['success'] else f"❌ 失败：{log['failure_reason'] or '未知'}"
                })
        
        if log_data:
            df_logs = pd.DataFrame(log_data)
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("没有符合条件的日志记录")

# ==================== Tab 4: 系统设置 ====================
elif selected_menu == "系统设置":
    st.header("⚙️ 系统设置")
    
    st.info("🚧 系统设置功能开发中...")
    
    st.markdown("""
    ### 计划功能:
    
    - 🔐 安全设置
      - JWT Token 过期时间
      - 密码策略（最小长度、复杂度）
      - 登录失败锁定策略
    
    - 📧 通知设置
      - 邮件服务器配置
      - 告警通知接收人
    
    - 💾 数据设置
      - 日志保留天数
      - 自动备份策略
    
    - 🎨 界面设置
      - 主题颜色
      - Logo 自定义
    """)

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.4 | 用户管理后台</p>
    <p>Powered by Streamlit + SQLite</p>
</div>
""", unsafe_allow_html=True)
