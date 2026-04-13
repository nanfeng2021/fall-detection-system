#!/usr/bin/env python3
"""
测试 SQLite 认证功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.db import init_db
from src.auth.auth_service_sqlite import AuthService
from src.auth.models import LoginRequest, RegisterRequest, UserRole


def test_auth():
    """测试认证功能"""
    print("🧪 开始测试 SQLite 认证功能...\n")
    
    # 初始化数据库
    db = init_db()
    print(f"✅ 数据库位置：{db.db_path}\n")
    
    auth_service = AuthService()
    
    # 测试 1: 验证默认管理员账户
    print("1️⃣ 测试默认管理员登录...")
    try:
        login_request = LoginRequest(username="admin", password="admin123")
        user, token = auth_service.login(login_request)
        print(f"   ✅ 登录成功！")
        print(f"      用户：{user.username}")
        print(f"      角色：{user.role.value}")
        print(f"      Token: {token[:50]}...")
    except Exception as e:
        print(f"   ❌ 登录失败：{e}")
    
    print()
    
    # 测试 2: 注册新用户
    print("2️⃣ 测试注册用户...")
    try:
        register_request = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password="test123456",
            role=UserRole.VIEWER
        )
        new_user = auth_service.register(register_request)
        print(f"   ✅ 注册成功！")
        print(f"      用户 ID: {new_user.id}")
        print(f"      用户名：{new_user.username}")
        print(f"      邮箱：{new_user.email}")
        print(f"      角色：{new_user.role.value}")
    except Exception as e:
        print(f"   ❌ 注册失败：{e}")
    
    print()
    
    # 测试 3: 用新用户登录
    print("3️⃣ 测试新用户登录...")
    try:
        login_request = LoginRequest(username="testuser", password="test123456")
        user, token = auth_service.login(login_request)
        print(f"   ✅ 登录成功！")
        print(f"      用户：{user.username}")
        print(f"      角色：{user.role.value}")
    except Exception as e:
        print(f"   ❌ 登录失败：{e}")
    
    print()
    
    # 测试 4: 获取所有用户
    print("4️⃣ 获取用户列表...")
    try:
        users = auth_service.get_all_users()
        print(f"   ✅ 共 {len(users)} 个用户:")
        for u in users:
            print(f"      - {u.username} ({u.role.value}) - {u.email}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")
    
    print()
    
    # 测试 5: 查看登录日志
    print("5️⃣ 查看登录日志...")
    try:
        logs = auth_service.get_login_logs(limit=5)
        print(f"   ✅ 最近 {len(logs)} 条登录记录:")
        for log in logs:
            status = "✅" if log['success'] else "❌"
            print(f"      {status} {log['username']} @ {log['logged_at']}")
    except Exception as e:
        print(f"   ❌ 失败：{e}")
    
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    test_auth()
