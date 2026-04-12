#!/usr/bin/env python3
"""
FastAPI 主应用 - 集成认证和监控
提供 RESTful API 接口
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from .models import (
    SystemStatus, FrameResult, AlertInfo, DetectionConfig,
    StartDetectionRequest, StopDetectionResponse,
    HealthCheckResponse, StatisticsResponse
)
from .detection_service import DetectionService
from .auth_routes import router as auth_router
from ..auth.dependencies import get_current_user
from ..monitoring.metrics import get_metrics
from ..monitoring.alerter import get_alerter, AlertLevel
from ..monitoring.notifiers import get_email_notifier, get_wechat_notifier
from ..utils.config import get_config


# 创建检测服务实例
detection_service = DetectionService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 API 服务启动...")
    await detection_service.initialize()
    
    # 初始化监控告警系统
    metrics = get_metrics()
    alerter = get_alerter()
    
    # 注册告警回调（发送邮件和微信通知）
    email_notifier = get_email_notifier()
    wechat_notifier = get_wechat_notifier()
    
    def alert_callback(alert):
        """告警触发时的回调"""
        if alert.level == AlertLevel.CRITICAL:
            # 严重告警同时发送邮件和微信
            if email_notifier:
                email_notifier.send_alert(alert)
            if wechat_notifier:
                wechat_notifier.send_alert(alert)
        elif alert.level == AlertLevel.ERROR:
            # 错误只发送邮件
            if email_notifier:
                email_notifier.send_alert(alert)
    
    alerter.add_callback(alert_callback)
    
    yield
    
    # 关闭时
    print("🛑 API 服务关闭...")
    await detection_service.shutdown()


# 创建 FastAPI 应用
config = get_config()
app = FastAPI(
    title="GuardianFall API",
    description="摔倒检测系统 RESTful API - 集成用户认证和监控告警",
    version="1.1.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 路由注册 ====================

# 认证相关路由
app.include_router(auth_router)


# ==================== 基础接口 ====================

@app.get("/", tags=["根路径"])
async def root():
    """API 根路径"""
    return {
        "name": "GuardianFall API",
        "version": "1.1.0",
        "status": "running",
        "features": ["认证管理", "摔倒检测", "监控告警", "数据统计"]
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    is_running = detection_service.is_running()
    
    metrics = get_metrics()
    metrics.set_system_status(is_running)
    
    return HealthCheckResponse(
        status="healthy" if is_running else "unhealthy",
        timestamp=datetime.now(),
        version="1.1.0"
    )


@app.get("/status", response_model=SystemStatus, tags=["系统状态"])
async def get_status(current_user: dict = Depends(get_current_user)):
    """获取系统运行状态（需要认证）"""
    return detection_service.get_status()


# ==================== 检测控制接口 ====================

@app.post("/detection/start", tags=["检测控制"])
async def start_detection(
    request: StartDetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """启动检测（需要认证）"""
    try:
        await detection_service.start(request.camera_id)
        return {"message": "检测已启动", "camera_id": request.camera_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detection/stop", response_model=StopDetectionResponse, tags=["检测控制"])
async def stop_detection(current_user: dict = Depends(get_current_user)):
    """停止检测（需要认证）"""
    success = await detection_service.stop()
    return StopDetectionResponse(success=success)


@app.get("/detection/status", tags=["检测控制"])
async def detection_status(current_user: dict = Depends(get_current_user)):
    """获取检测状态（需要认证）"""
    return detection_service.get_status()


# ==================== 监控告警接口 ====================

@app.get("/alerts", tags=["监控告警"])
async def get_alerts(
    limit: int = Query(50, ge=1, le=500),
    level: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取告警列表（需要认证）"""
    alerter = get_alerter()
    
    from .alerter import AlertLevel
    alert_level = AlertLevel(level) if level else None
    alerts = alerter.get_alert_history(limit=limit, level=alert_level)
    
    return {"alerts": [a.to_dict() for a in alerts]}


@app.get("/alerts/active", tags=["监控告警"])
async def get_active_alerts(current_user: dict = Depends(get_current_user)):
    """获取活动告警（需要认证）"""
    alerter = get_alerter()
    alerts = alerter.get_active_alerts()
    return {"alerts": [a.to_dict() for a in alerts]}


@app.post("/alerts/{alert_id}/acknowledge", tags=["监控告警"])
async def acknowledge_alert(
    alert_id: float,
    current_user: dict = Depends(get_current_user)
):
    """确认告警（需要认证）"""
    alerter = get_alerter()
    success = alerter.acknowledge(alert_id, current_user.username)
    
    if success:
        return {"message": "告警已确认"}
    else:
        raise HTTPException(status_code=404, detail="告警不存在")


@app.get("/alerts/statistics", tags=["监控告警"])
async def get_alert_statistics(current_user: dict = Depends(get_current_user)):
    """获取告警统计（需要认证）"""
    alerter = get_alerter()
    return alerter.get_statistics()


# ==================== 监控指标接口 ====================

@app.get("/metrics", tags=["监控指标"])
async def get_metrics_info(current_user: dict = Depends(get_current_user)):
    """获取监控指标（需要认证）"""
    # Prometheus 指标通过 /metrics 端点暴露
    # 这里返回指标概览
    return {
        "prometheus_endpoint": "/metrics",
        "description": "Prometheus metrics available on port 9090"
    }


# ==================== 用户管理接口 ====================

@app.get("/users/me", tags=["用户管理"])
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    from ..auth.auth_service import AuthService
    auth_service = AuthService()
    
    user = auth_service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user


# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    # 记录异常到监控系统
    alerter = get_alerter()
    alerter.trigger(
        level=AlertLevel.ERROR,
        message=f"API 异常：{str(exc)}",
        source="api",
        data={"path": str(request.url.path)}
    )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
