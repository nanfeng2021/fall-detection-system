"""
登录失败锁定机制
防止暴力破解攻击
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from ..database.db import get_db_connection


class LoginLockManager:
    """登录锁定管理器"""
    
    def __init__(self):
        self._create_table()
    
    def _create_table(self):
        """创建失败尝试表"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_username ON login_attempts(username)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_ip ON login_attempts(ip_address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_locks_username ON user_locks(username)")
    
    def record_attempt(self, username: str, ip_address: Optional[str] = None):
        """记录登录失败尝试"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO login_attempts (username, ip_address)
                VALUES (?, ?)
            """, (username, ip_address))
    
    def get_failed_attempts(self, username: str, minutes: int = 15) -> int:
        """获取指定时间内的失败次数"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM login_attempts
                WHERE username = ? AND attempted_at > ?
            """, (username, cutoff_time.isoformat()))
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def is_locked(self, username: str) -> tuple[bool, Optional[datetime]]:
        """
        检查用户是否被锁定
        
        Returns:
            tuple: (是否锁定，锁定直到何时)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT locked_until FROM user_locks
                WHERE username = ? AND locked_until > ?
            """, (username, datetime.now().isoformat()))
            
            result = cursor.fetchone()
            
            if result:
                return True, datetime.fromisoformat(result[0])
            return False, None
    
    def lock_user(self, username: str, duration_minutes: int = 30, reason: str = "多次登录失败"):
        """锁定用户账户"""
        locked_until = datetime.now() + timedelta(minutes=duration_minutes)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_locks (username, locked_until, reason)
                VALUES (?, ?, ?)
            """, (username, locked_until.isoformat(), reason))
    
    def unlock_user(self, username: str):
        """解锁用户账户"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_locks WHERE username = ?", (username,))
    
    def check_and_lock(self, username: str, max_attempts: int = 5, window_minutes: int = 15):
        """
        检查是否应该锁定用户
        
        Args:
            username: 用户名
            max_attempts: 最大尝试次数
            window_minutes: 时间窗口（分钟）
        """
        failed_count = self.get_failed_attempts(username, window_minutes)
        
        if failed_count >= max_attempts:
            # 锁定 30 分钟
            self.lock_user(username, duration_minutes=30, reason=f"连续{failed_count}次登录失败")
            return True
        
        return False
    
    def cleanup_old_attempts(self, days: int = 7):
        """清理旧的尝试记录"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 删除旧尝试记录
            cursor.execute("""
                DELETE FROM login_attempts
                WHERE attempted_at < ?
            """, (cutoff_time.isoformat(),))
            
            # 删除已过期的锁定
            cursor.execute("""
                DELETE FROM user_locks
                WHERE locked_until < ?
            """, (datetime.now().isoformat(),))
    
    def get_lock_stats(self) -> Dict:
        """获取锁定统计信息"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 当前锁定的用户数
            cursor.execute("""
                SELECT COUNT(*) FROM user_locks
                WHERE locked_until > ?
            """, (datetime.now().isoformat(),))
            locked_count = cursor.fetchone()[0]
            
            # 今天的失败尝试数
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COUNT(*) FROM login_attempts
                WHERE attempted_at > ?
            """, (today_start.isoformat(),))
            today_attempts = cursor.fetchone()[0]
            
            # 最常见的攻击 IP
            cursor.execute("""
                SELECT ip_address, COUNT(*) as count
                FROM login_attempts
                WHERE attempted_at > ? AND ip_address IS NOT NULL
                GROUP BY ip_address
                ORDER BY count DESC
                LIMIT 5
            """, (today_start.isoformat(),))
            top_ips = cursor.fetchall()
            
            return {
                'locked_users': locked_count,
                'today_failed_attempts': today_attempts,
                'top_attack_ips': [{'ip': row[0], 'count': row[1]} for row in top_ips]
            }


# 全局实例
lock_manager = LoginLockManager()


def get_lock_manager() -> LoginLockManager:
    """获取锁定管理器实例"""
    return lock_manager
