# 🔐 安全增强功能指南

## 📋 概述

摔倒检测系统 v1.5 新增了企业级安全功能，保护系统免受暴力破解和未授权访问。

---

## ✅ 新增安全功能

### 1. **登录失败锁定机制** 🔒

防止暴力破解攻击的核心功能。

#### 工作原理

- 记录每次登录失败尝试（用户名 + IP）
- 15 分钟内失败 5 次 → 自动锁定 30 分钟
- 锁定期间无法登录（即使密码正确）
- 管理员可手动解锁

#### 配置参数

```python
# 默认配置
MAX_FAILED_ATTEMPTS = 5      # 最大失败次数
LOCKOUT_WINDOW_MINUTES = 15  # 时间窗口（分钟）
LOCKOUT_DURATION_MINUTES = 30  # 锁定持续时间
```

#### 使用示例

```python
from src.security.login_lock import get_lock_manager

lock_manager = get_lock_manager()

# 检查用户是否被锁定
is_locked, locked_until = lock_manager.is_locked("admin")
if is_locked:
    print(f"账户已锁定，直到 {locked_until}")

# 手动锁定用户
lock_manager.lock_user("baduser", duration_minutes=60)

# 手动解锁用户
lock_manager.unlock_user("admin")

# 获取统计信息
stats = lock_manager.get_lock_stats()
print(f"当前锁定用户数：{stats['locked_users']}")
print(f"今日失败尝试：{stats['today_failed_attempts']}")
```

---

### 2. **双因素认证（2FA）** 📱

基于 TOTP 的双因素认证，提供额外安全层。

#### 支持的验证器

- Google Authenticator
- Microsoft Authenticator
- Authy
- 任何支持 TOTP 的应用

#### 启用 2FA 流程

1. **生成密钥和二维码**
   ```python
   from src.security.two_factor_auth import get_two_factor_auth
   
   two_factor = get_two_factor_auth()
   
   # 为用户设置 2FA
   secret, uri, backup_codes = two_factor.setup_2fa(user_id=1, username="admin")
   
   # 生成二维码图片（Base64）
   qr_image = two_factor.generate_qr_code(uri)
   
   # 显示备用码（一次性！）
   print("备用码（请安全保存）:")
   for code in backup_codes:
       print(f"  - {code}")
   ```

2. **用户扫描二维码**
   - 打开验证器 App
   - 扫描屏幕上的二维码
   - 或手动输入密钥

3. **验证并启用**
   ```python
   # 用户输入 6 位验证码
   verify_code = "123456"
   
   if two_factor.enable_2fa(user_id=1, verify_code=verify_code):
       print("✅ 2FA 已启用")
   else:
       print("❌ 验证码错误")
   ```

4. **登录时使用 2FA**
   ```python
   from src.auth.auth_service_sqlite import AuthService
   
   auth = AuthService()
   
   try:
       user, token = auth.login(
           LoginRequest(username="admin", password="password123"),
           two_factor_code="123456"  # 6 位验证码
       )
   except AppException as e:
       if e.metadata.get("requires_2fa"):
           print("需要提供 2FA 验证码")
   ```

#### 备用码使用

如果手机丢失，可以使用备用码登录：

```python
# 使用备用码代替 TOTP
backup_code = "12345678"

if two_factor.verify_backup_code(user_id=1, backup_code=backup_code):
    print("✅ 备用码验证成功")
    # 注意：每个备用码只能使用一次
```

#### 重新生成备用码

```python
new_codes = two_factor.regenerate_backup_codes(user_id=1)
print("新的备用码:")
for code in new_codes:
    print(f"  - {code}")
```

---

### 3. **IP 白名单** 🌐

限制只有特定 IP 可以访问系统。

#### 配置方式

在配置文件中添加：

```json
{
  "security": {
    "ip_whitelist_enabled": true,
    "ip_whitelist": [
      "192.168.1.0/24",
      "10.0.0.1",
      "203.0.113.0/24"
    ],
    "ip_blacklist": [
      "198.51.100.1"
    ]
  }
}
```

#### 使用示例

```python
from ipaddress import ip_address, ip_network

def check_ip_access(client_ip: str) -> bool:
    """检查 IP 是否允许访问"""
    
    whitelist = ["192.168.1.0/24", "10.0.0.1"]
    blacklist = ["198.51.100.1"]
    
    client = ip_address(client_ip)
    
    # 检查黑名单
    for blocked in blacklist:
        if client == ip_address(blocked):
            return False
    
    # 检查白名单
    for allowed in whitelist:
        if '/' in allowed:
            if client in ip_network(allowed):
                return True
        else:
            if client == ip_address(allowed):
                return True
    
    return False  # 不在白名单内
```

---

### 4. **会话管理** 👥

查看和管理活跃会话。

#### 查看活跃会话

```python
from src.database.db import get_db_connection
from datetime import datetime

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.token, s.device_info, s.ip_address, 
               s.created_at, s.expires_at, u.username
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.is_active = 1 AND s.expires_at > ?
        ORDER BY s.created_at DESC
    """, (datetime.now().isoformat(),))
    
    sessions = cursor.fetchall()
    
    for session in sessions:
        print(f"用户：{session['username']}")
        print(f"设备：{session['device_info']}")
        print(f"IP: {session['ip_address']}")
        print(f"过期：{session['expires_at']}")
        print("---")
```

#### 强制下线（踢人）

```python
def revoke_session(session_id: int):
    """撤销指定会话"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions SET is_active = 0
            WHERE id = ?
        """, (session_id,))
        conn.commit()

def revoke_all_user_sessions(user_id: int):
    """撤销用户所有会话（修改密码后使用）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions SET is_active = 0
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
```

---

## 🔧 集成到登录流程

### 完整的登录流程

```python
from src.auth.auth_service_sqlite import AuthService
from src.security.login_lock import get_lock_manager
from src.models import LoginRequest

auth = AuthService()
lock_manager = get_lock_manager()

def login_with_security(username: str, password: str, 
                       ip_address: str, user_agent: str,
                       two_factor_code: str = None):
    """安全的登录流程"""
    
    # 1. 检查是否被锁定
    is_locked, locked_until = lock_manager.is_locked(username)
    if is_locked:
        return {
            "success": False,
            "error": f"账户已被锁定，请在 {locked_until.strftime('%H:%M')} 后重试"
        }
    
    try:
        # 2. 尝试登录
        request = LoginRequest(username=username, password=password)
        user, token = auth.login(
            request,
            ip_address=ip_address,
            user_agent=user_agent,
            two_factor_code=two_factor_code
        )
        
        return {
            "success": True,
            "user": user,
            "token": token
        }
        
    except AppException as e:
        if e.metadata.get("requires_2fa"):
            return {
                "success": False,
                "requires_2fa": True,
                "error": "需要双因素认证代码"
            }
        
        return {
            "success": False,
            "error": str(e)
        }
```

---

## 📊 安全监控

### 查看攻击统计

```python
from src.security.login_lock import get_lock_manager

lock_manager = get_lock_manager()
stats = lock_manager.get_lock_stats()

print("=== 安全统计 ===")
print(f"当前锁定用户数：{stats['locked_users']}")
print(f"今日失败尝试：{stats['today_failed_attempts']}")

print("\nTop 攻击 IP:")
for item in stats['top_attack_ips']:
    print(f"  {item['ip']}: {item['count']} 次尝试")
```

### 定期清理旧数据

```python
# 每周清理一次
lock_manager.cleanup_old_attempts(days=7)
```

---

## 🛡️ 最佳实践

### 1. 强制启用 2FA

对管理员账户强制启用 2FA：

```python
def require_2fa_for_admins(user_id: int):
    """强制管理员启用 2FA"""
    user = auth.get_user_by_id(user_id)
    
    if user.role == UserRole.ADMIN:
        if not two_factor.is_2fa_enabled(user_id):
            raise AppException("管理员必须启用双因素认证", status_code=403)
```

### 2. 密码策略

```python
def validate_password_strength(password: str) -> tuple[bool, str]:
    """验证密码强度"""
    
    if len(password) < 8:
        return False, "密码至少 8 个字符"
    
    if not any(c.isupper() for c in password):
        return False, "密码必须包含大写字母"
    
    if not any(c.islower() for c in password):
        return False, "密码必须包含小写字母"
    
    if not any(c.isdigit() for c in password):
        return False, "密码必须包含数字"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "密码必须包含特殊字符"
    
    return True, "密码强度合格"
```

### 3. 会话超时

```python
# 设置较短的 Token 过期时间（30 分钟）
JWT_EXPIRE_MINUTES = 30

# 对于敏感操作，要求重新验证
def require_fresh_login():
    """要求最近登录（10 分钟内）"""
    last_login = st.session_state.get('last_login')
    
    if not last_login or (datetime.now() - last_login).seconds > 600:
        st.warning("为了安全，请重新登录")
        st.stop()
```

### 4. 审计日志

记录所有敏感操作：

```python
def log_sensitive_action(user_id: int, action: str, details: str):
    """记录敏感操作"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, details, datetime.now().isoformat()))
```

---

## 📈 安全仪表板

创建安全管理页面：

```python
import streamlit as st
from src.security.login_lock import get_lock_manager
from src.security.two_factor_auth import get_two_factor_auth

st.title("🔐 安全管理")

lock_manager = get_lock_manager()
stats = lock_manager.get_lock_stats()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("当前锁定用户", stats['locked_users'])

with col2:
    st.metric("今日失败尝试", stats['today_failed_attempts'])

with col3:
    st.metric("活跃会话", get_active_session_count())

st.subheader("🚨 Top 攻击 IP")
for item in stats['top_attack_ips']:
    st.error(f"{item['ip']}: {item['count']} 次失败尝试")
```

---

## 🆘 故障排查

### Q1: 用户被意外锁定怎么办？

**解决**:
```python
lock_manager.unlock_user("username")
```

### Q2: 用户丢失了 2FA 手机怎么办？

**解决**:
1. 使用备用码登录
2. 或管理员禁用 2FA：
   ```python
   two_factor.disable_2fa(user_id=1)
   ```
3. 重新设置 2FA

### Q3: 如何查看所有用户的 2FA 状态？

```python
users = auth.get_all_users()
for user in users:
    enabled = two_factor.is_2fa_enabled(user.id)
    status = "✅" if enabled else "❌"
    print(f"{status} {user.username}")
```

---

## 📞 技术支持

如有安全问题，请立即联系：

- GitHub Issues: https://github.com/nanfeng2021/fall-detection-system/issues
- 紧急联系：security@example.com

---

**版本**: v1.5  
**更新日期**: 2026-04-13  
**作者**: 旺财 🐕
