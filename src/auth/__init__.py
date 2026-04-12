# Authentication module for GuardianFall
"""
用户认证模块 - 基于 JWT 和 OAuth2
提供用户登录、注册、权限验证等功能
"""

from .auth_service import AuthService, create_access_token, verify_token
from .models import User, TokenData, LoginRequest, RegisterRequest
from .dependencies import get_current_user, require_role

__all__ = [
    'AuthService',
    'create_access_token',
    'verify_token',
    'User',
    'TokenData',
    'LoginRequest',
    'RegisterRequest',
    'get_current_user',
    'require_role',
]
