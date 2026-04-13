#!/usr/bin/env python3
"""
从 JSON 迁移用户数据到 SQLite
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.db import init_db, get_db_connection
from src.auth.auth_service_sqlite import AuthService


def migrate_users():
    """迁移用户数据"""
    print("🚀 开始迁移用户数据到 SQLite...")
    
    # 初始化数据库
    db = init_db()
    print(f"✅ 数据库已初始化：{db.db_path}")
    
    # 检查是否已有数据
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        
        if count > 1:  # 已经有数据（除了默认 admin）
            print(f"⚠️  数据库中已有 {count} 个用户，跳过迁移")
            return
    
    # 查找旧的 JSON 文件
    json_path = Path(__file__).parent.parent / "data" / "users.json"
    
    if not json_path.exists():
        print("ℹ️  未找到旧的 users.json 文件，无需迁移")
        return
    
    # 读取旧数据
    with open(json_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    
    users = old_data.get('users', [])
    print(f"📊 发现 {len(users)} 个用户需要迁移")
    
    # 迁移用户
    auth_service = AuthService()
    migrated_count = 0
    
    for user in users:
        try:
            # 跳过已存在的 admin
            if user['username'] == 'admin':
                print(f"  ⏭️  跳过默认管理员账户")
                continue
            
            # 直接插入（不验证密码，使用已有 hash）
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO users 
                    (id, username, email, password_hash, role, is_active, created_at, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.get('id'),
                    user.get('username'),
                    user.get('email'),
                    user.get('password_hash'),
                    user.get('role', 'viewer'),
                    user.get('is_active', True),
                    user.get('created_at'),
                    user.get('last_login')
                ))
            
            migrated_count += 1
            print(f"  ✅ 迁移用户：{user['username']}")
        
        except Exception as e:
            print(f"  ❌ 迁移失败 {user['username']}: {e}")
    
    print(f"\n✅ 迁移完成！共迁移 {migrated_count} 个用户")
    print(f"📁 数据库位置：{db.db_path}")
    print(f"\n💡 提示：建议备份旧的 users.json 文件")


if __name__ == "__main__":
    migrate_users()
