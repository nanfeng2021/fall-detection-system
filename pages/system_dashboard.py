#!/usr/bin/env python3
"""
系统概览仪表板 - 管理员视图

功能:
- 系统状态监控
- 用户统计
- 告警统计
- 资源使用情况
- 快速操作
"""

import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="系统仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 导入服务 ====================
try:
    from src.auth.auth_service_sqlite import AuthService
    from src.database.db import init_db
    from src.auth.models import UserRole
    AUTH_ENABLED = True
except Exception as e:
    print(f"⚠️ 认证模块加载失败：{e}")
    AUTH_ENABLED = False

# ==================== Session State ====================
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# ==================== 权限检查 ====================
def check_admin_access():
    if not st.session_state.authenticated:
        st.warning("⚠️ 请先登录")
        st.link_button("前往登录", "/")
        st.stop()
    
    user = st.session_state.current_user
    if not user or user.get('role') != 'admin':
        st.error("🚫 仅限管理员访问")
        st.link_button("返回首页", "/")
        st.stop()

check_admin_access()

# ==================== 辅助函数 ====================
def get_auth_service():
    return AuthService()

def get_system_stats():
    """获取系统统计信息"""
    import psutil
    import os
    
    stats = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'memory_used_gb': psutil.virtual_memory().used / (1024**3),
        'memory_total_gb': psutil.virtual_memory().total / (1024**3),
        'disk_percent': psutil.disk_usage('/').percent,
        'disk_used_gb': psutil.disk_usage('/').used / (1024**3),
        'disk_total_gb': psutil.disk_usage('/').total / (1024**3),
        'uptime': datetime.now() - timedelta(seconds=psutil.boot_time())
    }
    
    return stats

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("🎛️ 管理面板")
    
    user = st.session_state.current_user
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <p style="margin: 0; font-weight: bold;">👤 {user['username']}</p>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 0.9em;">{'👑 管理员' if user['role'] == 'admin' else user['role']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    menu = ["系统概览", "用户管理", "日志查看", "系统设置"]
    selection = st.radio("导航", menu, label_visibility="collapsed")
    
    st.divider()
    
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

# ==================== 主界面 ====================
st.title("📊 系统仪表板")
st.markdown("**实时监控系统状态和关键指标**")

# 刷新时间
last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"最后更新：{last_refresh}")

auth_service = get_auth_service()

# ==================== 第一行：核心指标 ====================
st.subheader("🎯 核心指标")

col1, col2, col3, col4 = st.columns(4)

# 用户统计
users = auth_service.get_all_users()
active_users = sum(1 for u in users if u.is_active)

with col1:
    st.metric(
        label="总用户数",
        value=len(users),
        delta=f"{active_users} 活跃"
    )

# 登录统计（今天）
today = datetime.now().date()
logs = auth_service.get_login_logs(limit=1000)
today_logins = sum(1 for log in logs if datetime.fromisoformat(log['logged_at']).date() == today)
today_failed = sum(1 for log in logs if datetime.fromisoformat(log['logged_at']).date() == today and not log['success'])

with col2:
    st.metric(
        label="今日登录",
        value=today_logins,
        delta=f"-{today_failed} 失败" if today_failed > 0 else "全部成功",
        delta_color="normal" if today_failed == 0 else "inverse"
    )

# 系统运行时间
try:
    system_stats = get_system_stats()
    uptime_days = system_stats['uptime'].days
    uptime_hours = system_stats['uptime'].seconds // 3600
    
    with col3:
        st.metric(
            label="系统运行时间",
            value=f"{uptime_days}天 {uptime_hours}小时",
            delta="稳定运行"
        )
except:
    with col3:
        st.metric("系统运行时间", "未知")

# 磁盘使用
try:
    disk_used = system_stats['disk_percent']
    
    with col4:
        st.metric(
            label="磁盘使用率",
            value=f"{disk_used:.1f}%",
            delta="正常" if disk_used < 80 else "⚠️ 注意",
            delta_color="normal" if disk_used < 80 else "inverse"
        )
except:
    with col4:
        st.metric("磁盘使用率", "未知")

st.divider()

# ==================== 第二行：系统资源 ====================
st.subheader("💻 系统资源")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**CPU 使用率**")
    try:
        cpu = system_stats['cpu_percent']
        st.progress(cpu / 100)
        st.caption(f"当前：{cpu:.1f}%")
        
        if cpu > 80:
            st.warning("⚠️ CPU 使用率较高")
        elif cpu > 90:
            st.error("🚨 CPU 使用率过高！")
    except:
        st.info("无法获取 CPU 信息")

with col2:
    st.markdown("**内存使用率**")
    try:
        memory = system_stats['memory_percent']
        st.progress(memory / 100)
        st.caption(f"已用：{system_stats['memory_used_gb']:.2f}GB / {system_stats['memory_total_gb']:.2f}GB ({memory:.1f}%)")
        
        if memory > 80:
            st.warning("⚠️ 内存使用率较高")
        elif memory > 90:
            st.error("🚨 内存使用率过高！")
    except:
        st.info("无法获取内存信息")

st.divider()

# ==================== 第三行：用户分析 ====================
st.subheader("👥 用户分析")

col1, col2, col3 = st.columns(3)

# 角色分布
role_counts = {}
for user in users:
    role = user.role.value
    role_counts[role] = role_counts.get(role, 0) + 1

with col1:
    st.markdown("**角色分布**")
    role_data = []
    for role, count in role_counts.items():
        emoji = {'admin': '👑', 'operator': '🔧', 'viewer': '👁️'}.get(role, '👤')
        role_name = {'admin': '管理员', 'operator': '操作员', 'viewer': '观察员'}.get(role, role)
        role_data.append(f"{emoji} {role_name}: {count}")
    
    st.markdown("\n".join(role_data))

# 最近创建的用户
with col2:
    st.markdown("**最近创建的用户**")
    if users:
        sorted_users = sorted(users, key=lambda u: u.created_at, reverse=True)[:5]
        for u in sorted_users:
            created = u.created_at.strftime("%m-%d") if u.created_at else "未知"
            st.caption(f"👤 {u.username} ({created})")
    else:
        st.info("暂无用户")

# 最近登录
with col3:
    st.markdown("**最近登录的用户**")
    if users:
        sorted_by_login = sorted(
            [u for u in users if u.last_login],
            key=lambda u: u.last_login,
            reverse=True
        )[:5]
        
        for u in sorted_by_login:
            last_login = u.last_login.strftime("%m-%d %H:%M") if u.last_login else "未知"
            st.caption(f"👤 {u.username} ({last_login})")
    else:
        st.info("暂无登录记录")

st.divider()

# ==================== 第四行：登录活动 ====================
st.subheader("🔐 最近登录活动")

logs = auth_service.get_login_logs(limit=10)

if logs:
    log_data = []
    for log in logs:
        status = "✅" if log['success'] else "❌"
        time_str = datetime.fromisoformat(log['logged_at']).strftime("%m-%d %H:%M")
        ip = log['ip_address'] or '未知'
        
        log_data.append({
            '时间': time_str,
            '用户': log['username'],
            'IP': ip,
            '状态': f"{status} {'成功' if log['success'] else '失败'}"
        })
    
    st.dataframe(log_data, use_container_width=True, hide_index=True)
else:
    st.info("暂无登录日志")

st.divider()

# ==================== 第五行：快速操作 ====================
st.subheader("⚡ 快速操作")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("👥 用户管理", use_container_width=True):
        st.switch_page("pages/user_management.py")

with col2:
    if st.button("📊 查看日志", use_container_width=True):
        st.switch_page("pages/system_dashboard.py")  # 可以新建一个日志页面

with col3:
    if st.button("🔄 刷新数据", use_container_width=True):
        st.rerun()

with col4:
    if st.button("⚙️ 系统设置", use_container_width=True):
        st.info("系统设置功能开发中...")

# ==================== 页脚 ====================
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>摔倒检测系统 v1.4 | 系统仪表板</p>
    <p>最后更新：{last_refresh}</p>
</div>
""".format(last_refresh=last_refresh), unsafe_allow_html=True)
