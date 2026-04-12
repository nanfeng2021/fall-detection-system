"""
用户认证数据模型
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"  # 管理员
    OPERATOR = "operator"  # 操作员
    VIEWER = "viewer"  # 只读用户


class User(BaseModel):
    """用户模型"""
    id: int
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TokenData(BaseModel):
    """JWT Token 数据"""
    user_id: int
    username: str
    role: UserRole
    exp: datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 过期时间（秒）
    user: User


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
