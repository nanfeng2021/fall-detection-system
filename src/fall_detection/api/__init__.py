"""
API 接口层
提供 RESTful API 路由、请求验证、响应格式化
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

__all__ = [
    "APIRouter",
    "Depends",
    "HTTPException",
    "status",
]
