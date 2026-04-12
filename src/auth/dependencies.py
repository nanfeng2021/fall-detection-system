"""
认证依赖项
用于 FastAPI 路由的权限验证
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from .auth_service import verify_token
from .models import TokenData, UserRole
from ..utils.error_handler import AppException


# HTTP Bearer Token 安全方案
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """获取当前登录用户"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    return token_data


def require_role(*allowed_roles: UserRole):
    """
    装饰器：要求用户具有特定角色
    
    用法:
        @app.get("/admin")
        @require_role(UserRole.ADMIN)
        async def admin_endpoint(current_user: TokenData = Depends(get_current_user)):
            ...
    """
    async def role_checker(current_user: TokenData = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色权限：{', '.join([r.value for r in allowed_roles])}",
            )
        return current_user
    
    return role_checker
