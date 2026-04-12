#!/usr/bin/env python3
"""
FastAPI 主应用
提供RESTful API接口
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
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


# 创建检测服务实例
detection_service = DetectionService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 API服务启动...")
    await detection_service.initialize()
    
    yield
    
    # 关闭时
    print("🛑 API服务关闭...")
    await detection_service.shutdown()


# 创建FastAPI应用
app = FastAPI(
    title="GuardianFall API",
    description="摔倒检测系统RESTful API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 系统接口 ====================

@app.get("/", response_model=Dict[str, str])
async def root():
    """根路径"""
    return {
        "name": "GuardianFall API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        uptime_seconds=detection_service.uptime_seconds,
        version="1.0.0"
    )


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """获取系统状态"""
    return await detection_service.get_status()


# ==================== 检测接口 ====================

@app.post("/detection/start")
async def start_detection(request: Optional[StartDetectionRequest] = None):
    """启动检测"""
    try:
        config = request.config if request else None
        success = await detection_service.start(config)
        
        if success:
            return {"success": True, "message": "检测已启动"}
        else:
            raise HTTPException(status_code=400, detail="检测启动失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detection/stop", response_model=StopDetectionResponse)
async def stop_detection():
    """停止检测"""
    try:
        success = await detection_service.stop()
        
        return StopDetectionResponse(
            success=success,
            message="检测已停止" if success else "检测未运行",
            total_frames=detection_service.total_frames,
            total_alerts=detection_service.total_alerts
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/detection/status")
async def get_detection_status():
    """获取检测状态"""
    return {
        "is_running": detection_service.is_running,
        "current_frame": detection_service.current_frame,
        "fps": detection_service.current_fps,
        "active_trackers": detection_service.active_trackers
    }


# ==================== 数据接口 ====================

@app.get("/frames/latest", response_model=Optional[FrameResult])
async def get_latest_frame():
    """获取最新帧"""
    frame = await detection_service.get_latest_frame()
    
    if frame is None:
        raise HTTPException(status_code=404, detail="暂无帧数据")
    
    return frame


@app.get("/frames/{frame_id}", response_model=FrameResult)
async def get_frame(frame_id: int):
    """获取指定帧"""
    frame = await detection_service.get_frame(frame_id)
    
    if frame is None:
        raise HTTPException(status_code=404, detail=f"帧 {frame_id} 不存在")
    
    return frame


@app.get("/alerts", response_model=List[AlertInfo])
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, regex="^(critical|warning|info)$")
):
    """获取报警列表"""
    alerts = await detection_service.get_alerts(limit=limit, level=level)
    return alerts


@app.get("/alerts/stats")
async def get_alert_stats():
    """获取报警统计"""
    return await detection_service.get_alert_stats()


@app.delete("/alerts/clear")
async def clear_alerts():
    """清空报警记录"""
    await detection_service.clear_alerts()
    return {"success": True, "message": "报警记录已清空"}


# ==================== 配置接口 ====================

@app.get("/config", response_model=DetectionConfig)
async def get_config():
    """获取当前配置"""
    return await detection_service.get_config()


@app.put("/config")
async def update_config(config: DetectionConfig):
    """更新配置"""
    try:
        success = await detection_service.update_config(config)
        
        if success:
            return {"success": True, "message": "配置已更新"}
        else:
            raise HTTPException(status_code=400, detail="配置更新失败")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/reset")
async def reset_config():
    """重置配置为默认值"""
    await detection_service.reset_config()
    return {"success": True, "message": "配置已重置"}


# ==================== 统计接口 ====================

@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """获取系统统计"""
    return await detection_service.get_statistics()


@app.get("/statistics/fps/history")
async def get_fps_history(
    minutes: int = Query(5, ge=1, le=60)
):
    """获取FPS历史"""
    return await detection_service.get_fps_history(minutes=minutes)


# ==================== WebSocket 接口（实时数据）====================

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时数据流"""
    await websocket.accept()
    
    try:
        while True:
            # 发送当前状态
            status = await detection_service.get_status()
            await websocket.send_json(status.dict())
            
            # 每秒更新一次
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        print("WebSocket断开连接")
    except Exception as e:
        print(f"WebSocket错误: {e}")


# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# 启动命令（用于直接运行）
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
