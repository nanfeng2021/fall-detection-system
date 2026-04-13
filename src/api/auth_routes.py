"""
用户认证 API 路由（SQLite 版本）
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List

from ..auth.auth_service_sqlite import AuthService
from ..auth.models import (
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
async def login(request: Request, login_request: LoginRequest):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 access_token 和用户信息
    """
    # 获取 IP 地址和 User-Agent
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    user, token = auth_service.login(login_request, ip_address, user_agent)
    
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
    return auth_service.get_all_users()


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
    auth_service.delete_user(user_id)
    return {"message": "用户已删除"}


@router.put("/users/{user_id}/status", summary="更新用户状态（仅管理员）")
@handle_errors(default_return={"message": "用户状态已更新"})
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """
    更新用户状态（启用/禁用）
    
    - **user_id**: 用户 ID
    - **is_active**: 是否启用
    """
    auth_service.update_user_status(user_id, is_active)
    return {"message": "用户状态已更新"}


@router.get("/login-logs", summary="查看登录日志（仅管理员）")
@handle_errors(default_return=[])
async def get_login_logs(
    user_id: int = None,
    limit: int = 100,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """
    查看登录日志
    
    - **user_id**: 可选，筛选特定用户
    - **limit**: 返回数量限制（默认 100）
    """
    return auth_service.get_login_logs(user_id, limit)
