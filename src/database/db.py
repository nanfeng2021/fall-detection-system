"""
数据库连接和管理
使用 SQLite 作为默认数据库
"""

import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import os


class Database:
    """数据库管理类"""
    
    _instance: Optional['Database'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'Database':
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化数据库连接"""
        if not self._initialized:
            # 数据库文件路径
            db_path = Path(__file__).parent.parent.parent / "data" / "fall_detection.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.db_path = str(db_path)
            self._create_tables()
            self._initialized = True
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典格式
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _create_tables(self):
        """创建数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 登录日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 用户会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    device_info TEXT,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 密码重置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 双因素认证表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_2fa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    secret TEXT NOT NULL,
                    enabled BOOLEAN NOT NULL DEFAULT 0,
                    backup_codes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 登录失败尝试表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 用户锁定表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_locks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    locked_until TIMESTAMP NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_logs_user_id ON login_logs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_logs_logged_at ON login_logs(logged_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_resets_token ON password_resets(token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_2fa_user_id ON user_2fa(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_username ON login_attempts(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_locks_username ON user_locks(username)")
            
            # 插入默认管理员账户
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count == 0:
                import bcrypt
                from datetime import datetime
                
                default_password = "admin123"
                salt = bcrypt.gensalt(rounds=12)
                password_hash = bcrypt.hashpw(default_password.encode('utf-8'), salt).decode('utf-8')
                
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, role, is_active)
                    VALUES (?, ?, ?, ?, ?)
                """, ("admin", "admin@example.com", password_hash, "admin", 1))
                
                print("✅ 默认管理员账户已创建 (admin/admin123)")


# 全局数据库实例
db = Database()


def init_db():
    """初始化数据库（显式调用）"""
    return db


@contextmanager
def get_db_connection():
    """获取数据库连接的便捷函数"""
    with db.get_connection() as conn:
        yield conn
