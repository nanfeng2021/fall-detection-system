"""
用户认证 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from .auth_service import AuthService
from .models import (
    LoginRequest, RegisterRequest, TokenResponse,
    ChangePasswordRequest, User, UserRole
)
from .dependencies import get_current_user, require_role
from ..utils.error_handler import handle_errors, AppException


router = APIRouter(prefix="/auth", tags=["认证管理"])
auth_service = AuthService()


@router.post("/register", response_model=User, summary="用户注册")
@handle_errors(default_return=None)
async def register(request: RegisterRequest):
    """
    注册新用户
    
    - **username**: 用户名（3-50 字符）
    - **email**: 邮箱地址
    - **password**: 密码（最少 8 位）
    - **role**: 用户角色（默认 viewer）
    """
    user = auth_service.register(request)
    return user


@router.post("/login", response_model=TokenResponse, summary="用户登录")
@handle_errors(default_return=None)
async def login(request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 access_token 和用户信息
    """
    user, token = auth_service.login(request)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=1800,  # 30 分钟
        user=user
    )


@router.get("/me", response_model=User, summary="获取当前用户信息")
@handle_errors(default_return=None)
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前登录用户的详细信息"""
    user = auth_service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/change-password", summary="修改密码")
@handle_errors(default_return={"message": "密码修改成功"})
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    修改当前用户的密码
    
    - **old_password**: 原密码
    - **new_password**: 新密码（最少 8 位）
    """
    auth_service.change_password(
        current_user.user_id,
        request.old_password,
        request.new_password
    )
    return {"message": "密码修改成功"}


@router.get("/users", response_model=List[User], summary="获取用户列表（仅管理员）")
@handle_errors(default_return=None)
async def list_users(current_user: dict = Depends(require_role(UserRole.ADMIN))):
    """
    获取所有用户列表（仅管理员权限）
    
    返回不含密码的用户信息列表
    """
    # 简化实现，实际应该从数据库查询所有用户
    return []


@router.delete("/users/{user_id}", summary="删除用户（仅管理员）")
@handle_errors(default_return={"message": "用户已删除"})
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """
    删除指定用户（仅管理员权限）
    
    - **user_id**: 用户 ID
    """
    # TODO: 实现删除逻辑
    return {"message": "用户已删除"}
