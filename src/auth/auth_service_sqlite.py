"""
用户认证服务（SQLite 版本）
提供 JWT Token 生成、验证、用户管理等功能
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import os

from ..database.db import get_db_connection
from .models import User, UserRole, TokenData, LoginRequest, RegisterRequest
from ..utils.config import get_config
from ..utils.error_handler import handle_errors, AppException


# 配置
config = get_config()
JWT_SECRET = os.getenv("JWT_SECRET", config.auth.jwt_secret)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(config.auth.jwt_expire_minutes)))


class AuthService:
    """用户认证服务类（SQLite 版本）"""
    
    def __init__(self):
        pass
    
    def _hash_password(self, password: str) -> str:
        """对密码进行哈希加密"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @handle_errors(default_return=None)
    def register(self, request: RegisterRequest) -> User:
        """用户注册"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (request.username,))
            if cursor.fetchone():
                raise AppException("用户名已存在", status_code=400)
            
            # 检查邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE email = ?", (request.email,))
            if cursor.fetchone():
                raise AppException("邮箱已被注册", status_code=400)
            
            # 创建新用户
            password_hash = self._hash_password(request.password)
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (request.username, request.email, password_hash, request.role.value, True))
            
            user_id = cursor.lastrowid
            
            # 返回用户信息
            return User(
                id=user_id,
                username=request.username,
                email=request.email,
                role=request.role,
                is_active=True,
                created_at=datetime.now(),
                last_login=None
            )
    
    @handle_errors(default_return=None)
    def login(self, request: LoginRequest, ip_address: str = None, user_agent: str = None) -> Tuple[User, str]:
        """用户登录"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("""
                SELECT id, username, email, password_hash, role, is_active, created_at, last_login
                FROM users
                WHERE username = ?
            """, (request.username,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                # 记录失败日志
                self._log_login_attempt(None, request.username, ip_address, user_agent, False, "用户不存在")
                raise AppException("用户名或密码错误", status_code=401)
            
            # 验证密码
            if not self._verify_password(request.password, user_data["password_hash"]):
                # 记录失败日志
                self._log_login_attempt(user_data["id"], user_data["username"], ip_address, user_agent, False, "密码错误")
                raise AppException("用户名或密码错误", status_code=401)
            
            # 检查用户是否激活
            if not user_data["is_active"]:
                self._log_login_attempt(user_data["id"], user_data["username"], ip_address, user_agent, False, "账户已禁用")
                raise AppException("账户已被禁用", status_code=403)
            
            # 更新最后登录时间
            now = datetime.now()
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE id = ?
            """, (now, user_data["id"]))
            
            # 生成 Token
            token = create_access_token(
                user_id=user_data["id"],
                username=user_data["username"],
                role=UserRole(user_data["role"])
            )
            
            # 记录会话
            self._create_session(user_data["id"], token, ip_address, user_agent)
            
            # 记录成功日志
            self._log_login_attempt(user_data["id"], user_data["username"], ip_address, user_agent, True)
            
            # 返回用户信息和 Token
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=UserRole(user_data["role"]),
                is_active=bool(user_data["is_active"]),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data["created_at"] else now,
                last_login=datetime.fromisoformat(user_data["last_login"]) if user_data["last_login"] else now
            )
            
            return user, token
    
    def _log_login_attempt(self, user_id: Optional[int], username: str, 
                          ip_address: Optional[str], user_agent: Optional[str],
                          success: bool, failure_reason: Optional[str] = None):
        """记录登录日志"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO login_logs (user_id, username, ip_address, user_agent, success, failure_reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, ip_address, user_agent, success, failure_reason))
        except Exception as e:
            print(f"⚠️ 记录登录日志失败：{e}")
    
    def _create_session(self, user_id: int, token: str, 
                       ip_address: Optional[str], user_agent: Optional[str]):
        """创建用户会话"""
        try:
            expires_at = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, token, device_info, ip_address, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, token, user_agent, ip_address, expires_at))
        except Exception as e:
            print(f"⚠️ 创建会话失败：{e}")
    
    @handle_errors(default_return=None)
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            return User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=UserRole(user_data["role"]),
                is_active=bool(user_data["is_active"]),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data["created_at"] else datetime.now(),
                last_login=datetime.fromisoformat(user_data["last_login"]) if user_data["last_login"] else None
            )
    
    @handle_errors(default_return=None)
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users
                WHERE username = ?
            """, (username,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            return User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                role=UserRole(user_data["role"]),
                is_active=bool(user_data["is_active"]),
                created_at=datetime.fromisoformat(user_data["created_at"]) if user_data["created_at"] else datetime.now(),
                last_login=datetime.fromisoformat(user_data["last_login"]) if user_data["last_login"] else None
            )
    
    @handle_errors(default_return=None)
    def change_password(self, user_id: int, old_password: str, new_password: str):
        """修改密码"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                raise AppException("用户不存在", status_code=404)
            
            # 验证旧密码
            if not self._verify_password(old_password, user_data["password_hash"]):
                raise AppException("原密码错误", status_code=400)
            
            # 更新密码
            new_hash = self._hash_password(new_password)
            cursor.execute("""
                UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_hash, user_id))
    
    @handle_errors(default_return=None)
    def get_all_users(self) -> list:
        """获取所有用户列表"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, role, is_active, created_at, last_login
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append(User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    role=UserRole(row["role"]),
                    is_active=bool(row["is_active"]),
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                    last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None
                ))
            
            return users
    
    @handle_errors(default_return=None)
    def delete_user(self, user_id: int):
        """删除用户"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 不能删除自己
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            if cursor.rowcount == 0:
                raise AppException("用户不存在", status_code=404)
    
    @handle_errors(default_return=None)
    def update_user_status(self, user_id: int, is_active: bool):
        """更新用户状态"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (is_active, user_id))
    
    @handle_errors(default_return=None)
    def get_login_logs(self, user_id: Optional[int] = None, limit: int = 100) -> list:
        """获取登录日志"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    SELECT id, user_id, username, ip_address, success, failure_reason, logged_at
                    FROM login_logs
                    WHERE user_id = ?
                    ORDER BY logged_at DESC
                    LIMIT ?
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT id, user_id, username, ip_address, success, failure_reason, logged_at
                    FROM login_logs
                    ORDER BY logged_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]


def create_access_token(user_id: int, username: str, role: UserRole) -> str:
    """生成访问 Token"""
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    
    to_encode = {
        "user_id": user_id,
        "username": username,
        "role": role.value,
        "exp": expire
    }
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """验证 Token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(
            user_id=payload["user_id"],
            username=payload["username"],
            role=UserRole(payload["role"]),
            exp=datetime.fromtimestamp(payload["exp"])
        )
    except jwt.ExpiredSignatureError:
        raise AppException("Token 已过期", status_code=401)
    except jwt.InvalidTokenError:
        raise AppException("无效的 Token", status_code=401)
