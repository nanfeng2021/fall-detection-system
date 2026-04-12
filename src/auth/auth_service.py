"""
用户认证服务
提供 JWT Token 生成、验证、用户管理等功能
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import json
import os

from .models import User, UserRole, TokenData, LoginRequest, RegisterRequest
from ..utils.config import get_config
from ..utils.error_handler import handle_errors, AppException


# 配置
config = get_config()
JWT_SECRET = os.getenv("JWT_SECRET", config.auth.jwt_secret)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", str(config.auth.jwt_expire_minutes)))

# 用户数据库文件（简化实现，生产环境应使用真正的数据库）
USERS_DB_PATH = Path(__file__).parent.parent.parent / "data" / "users.json"


class AuthService:
    """用户认证服务类"""
    
    def __init__(self):
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保用户数据库文件存在"""
        USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not USERS_DB_PATH.exists():
            # 创建默认管理员账户
            default_users = {
                "users": [
                    {
                        "id": 1,
                        "username": "admin",
                        "email": "admin@example.com",
                        "password_hash": self._hash_password("admin123"),
                        "role": "admin",
                        "is_active": True,
                        "created_at": datetime.now().isoformat(),
                        "last_login": None
                    }
                ]
            }
            with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(default_users, f, indent=2, ensure_ascii=False)
    
    def _load_users(self) -> Dict[str, Any]:
        """加载用户数据"""
        try:
            with open(USERS_DB_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"users": []}
    
    def _save_users(self, data: Dict[str, Any]):
        """保存用户数据"""
        with open(USERS_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
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
        data = self._load_users()
        
        # 检查用户名是否已存在
        for user in data["users"]:
            if user["username"] == request.username:
                raise AppException("用户名已存在", status_code=400)
        
        # 创建新用户
        new_user = {
            "id": max([u["id"] for u in data["users"]], default=0) + 1,
            "username": request.username,
            "email": request.email,
            "password_hash": self._hash_password(request.password),
            "role": request.role.value,
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        data["users"].append(new_user)
        self._save_users(data)
        
        # 返回不含密码的用户信息
        return User(
            id=new_user["id"],
            username=new_user["username"],
            email=new_user["email"],
            role=UserRole(new_user["role"]),
            is_active=new_user["is_active"],
            created_at=datetime.fromisoformat(new_user["created_at"]),
            last_login=None
        )
    
    @handle_errors(default_return=None)
    def login(self, request: LoginRequest) -> tuple[User, str]:
        """用户登录"""
        data = self._load_users()
        
        # 查找用户
        user_data = None
        for user in data["users"]:
            if user["username"] == request.username:
                user_data = user
                break
        
        if not user_data:
            raise AppException("用户名或密码错误", status_code=401)
        
        # 验证密码
        if not self._verify_password(request.password, user_data["password_hash"]):
            raise AppException("用户名或密码错误", status_code=401)
        
        # 检查用户是否激活
        if not user_data["is_active"]:
            raise AppException("账户已被禁用", status_code=403)
        
        # 更新最后登录时间
        for user in data["users"]:
            if user["username"] == request.username:
                user["last_login"] = datetime.now().isoformat()
                break
        self._save_users(data)
        
        # 生成 Token
        token = create_access_token(
            user_id=user_data["id"],
            username=user_data["username"],
            role=UserRole(user_data["role"])
        )
        
        # 返回用户信息和 Token
        user = User(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            role=UserRole(user_data["role"]),
            is_active=user_data["is_active"],
            created_at=datetime.fromisoformat(user_data["created_at"]),
            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data["last_login"] else None
        )
        
        return user, token
    
    @handle_errors(default_return=None)
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        data = self._load_users()
        
        for user in data["users"]:
            if user["id"] == user_id:
                return User(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    role=UserRole(user["role"]),
                    is_active=user["is_active"],
                    created_at=datetime.fromisoformat(user["created_at"]),
                    last_login=datetime.fromisoformat(user["last_login"]) if user["last_login"] else None
                )
        
        return None
    
    @handle_errors(default_return=None)
    def change_password(self, user_id: int, old_password: str, new_password: str):
        """修改密码"""
        data = self._load_users()
        
        # 查找用户
        user_data = None
        for user in data["users"]:
            if user["id"] == user_id:
                user_data = user
                break
        
        if not user_data:
            raise AppException("用户不存在", status_code=404)
        
        # 验证旧密码
        if not self._verify_password(old_password, user_data["password_hash"]):
            raise AppException("原密码错误", status_code=400)
        
        # 更新密码
        user_data["password_hash"] = self._hash_password(new_password)
        self._save_users(data)


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
