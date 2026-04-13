"""
双因素认证（2FA）模块
基于 TOTP（Time-based One-Time Password）
"""

import pyotp
import base64
import qrcode
import io
from typing import Optional, Tuple
from pathlib import Path
from ..database.db import get_db_connection


class TwoFactorAuth:
    """双因素认证管理器"""
    
    def __init__(self):
        self._create_table()
    
    def _create_table(self):
        """创建 2FA 配置表"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
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
    
    def generate_secret(self) -> str:
        """生成新的 TOTP 密钥"""
        return pyotp.random_base32()
    
    def setup_2fa(self, user_id: int, username: str) -> Tuple[str, str]:
        """
        设置 2FA
        
        Returns:
            tuple: (secret, provisioning_uri, qr_code_image)
        """
        secret = self.generate_secret()
        
        # 创建 TOTP URI
        totp = pyotp.TOTP(secret)
        issuer = "FallDetectionSystem"
        uri = totp.provisioning_uri(name=username, issuer_name=issuer)
        
        # 保存到数据库（未启用状态）
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 生成备用码（10 个）
            import random
            import string
            backup_codes = [
                ''.join(random.choices(string.digits, k=8))
                for _ in range(10)
            ]
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_2fa (user_id, secret, enabled, backup_codes)
                VALUES (?, ?, 0, ?)
            """, (user_id, secret, ','.join(backup_codes)))
        
        return secret, uri, backup_codes
    
    def enable_2fa(self, user_id: int, verify_code: str) -> bool:
        """
        启用 2FA（验证后）
        
        Args:
            user_id: 用户 ID
            verify_code: 用户输入的验证码
            
        Returns:
            bool: 是否成功启用
        """
        secret = self.get_user_secret(user_id)
        
        if not secret:
            return False
        
        # 验证码是否正确
        totp = pyotp.TOTP(secret)
        if totp.verify(verify_code, valid_window=1):  # 允许前后 1 个时间窗口
            # 启用 2FA
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_2fa SET enabled = 1 WHERE user_id = ?
                """, (user_id,))
            return True
        
        return False
    
    def disable_2fa(self, user_id: int):
        """禁用 2FA"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_2fa SET enabled = 0 WHERE user_id = ?
            """, (user_id,))
    
    def get_user_secret(self, user_id: int) -> Optional[str]:
        """获取用户的 2FA 密钥"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT secret FROM user_2fa WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def is_2fa_enabled(self, user_id: int) -> bool:
        """检查用户是否启用了 2FA"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT enabled FROM user_2fa WHERE user_id = ?
            """, (user_id,))
            result = cursor.fetchone()
            return bool(result and result[0])
    
    def verify_code(self, user_id: int, code: str) -> bool:
        """
        验证 2FA 代码
        
        Args:
            user_id: 用户 ID
            code: 6 位数字代码
            
        Returns:
            bool: 是否有效
        """
        secret = self.get_user_secret(user_id)
        
        if not secret:
            return False
        
        totp = pyotp.TOTP(secret)
        
        # 验证代码（允许前后 1 个时间窗口的偏差）
        return totp.verify(code, valid_window=1)
    
    def verify_backup_code(self, user_id: int, backup_code: str) -> bool:
        """
        验证备用码
        
        Args:
            user_id: 用户 ID
            backup_code: 备用码
            
        Returns:
            bool: 是否有效
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT backup_codes FROM user_2fa WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                return False
            
            codes = result[0].split(',')
            
            if backup_code in codes:
                # 删除已使用的备用码
                codes.remove(backup_code)
                cursor.execute("""
                    UPDATE user_2fa SET backup_codes = ? WHERE user_id = ?
                """, (','.join(codes), user_id))
                return True
            
            return False
    
    def get_backup_codes(self, user_id: int) -> list:
        """获取用户的备用码列表"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT backup_codes FROM user_2fa WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                return result[0].split(',')
            return []
    
    def regenerate_backup_codes(self, user_id: int) -> list:
        """重新生成备用码"""
        import random
        import string
        
        new_codes = [
            ''.join(random.choices(string.digits, k=8))
            for _ in range(10)
        ]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_2fa SET backup_codes = ? WHERE user_id = ?
            """, (','.join(new_codes), user_id))
        
        return new_codes
    
    def generate_qr_code(self, uri: str) -> str:
        """
        生成二维码图片（Base64）
        
        Args:
            uri: TOTP provisioning URI
            
        Returns:
            str: Base64 编码的 PNG 图片
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为 Base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"


# 全局实例
two_factor_auth = TwoFactorAuth()


def get_two_factor_auth() -> TwoFactorAuth:
    """获取 2FA 实例"""
    return two_factor_auth
