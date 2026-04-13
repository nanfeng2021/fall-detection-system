# Harness 工程规范迁移指南

## 📋 变更概览

本次重构将项目从扁平结构升级为符合 Harness 工程规范的模块化分层架构。

### 主要变化

| 变更前 | 变更后 | 说明 |
|--------|--------|------|
| `src/detection/` | `src/fall_detection/core/` | 核心业务逻辑 |
| `src/auth/` | `src/fall_detection/services/` | 业务服务层 |
| `src/camera/` | `src/fall_detection/cameras/` | 摄像头管理模块 |
| `app_optimized.py` | `app/main.py` | 应用入口标准化 |
| `config.json` | `configs/default.yaml` | 配置文件 YAML 化 |
| - | `pyproject.toml` | 现代 Python 项目配置 |
| - | `.env.example` | 环境变量模板 |

---

## 🏗️ 新架构分层

### 1. Core Layer（核心层）
**位置**: `src/fall_detection/core/`

**职责**:
- 摔倒检测算法实现
- 数据分析引擎
- 检测规则定义
- **无外部依赖**，纯业务逻辑

**关键文件**:
```python
# src/fall_detection/core/detector.py
class FallDetectionSystem:
    def process_frame(self, frame):
        # 核心检测算法
        pass
```

### 2. Services Layer（服务层）
**位置**: `src/fall_detection/services/`

**职责**:
- 业务服务封装
- 跨模块协调
- 事务管理
- 调用 Core + Repositories

**关键服务**:
```python
# src/fall_detection/services/auth_service.py
class AuthService:
    def authenticate(self, username, password):
        # 认证逻辑
        pass

# src/fall_detection/services/detection_service.py
class DetectionService:
    def start_detection(self, camera_id):
        # 检测服务
        pass
```

### 3. API Layer（接口层）
**位置**: `src/fall_detection/api/`

**职责**:
- RESTful API 定义
- 请求/响应模型
- 认证授权
- 输入验证

**路由结构**:
```
src/fall_detection/api/
├── routes/
│   ├── auth.py      # /api/auth/*
│   ├── detection.py # /api/detection/*
│   └── camera.py    # /api/camera/*
└── schemas/         # Pydantic 模型
```

### 4. Models Layer（模型层）
**位置**: `src/fall_detection/models/`

**职责**:
- 数据模型定义
- Pydantic Schemas
- 数据库模型
- 序列化/反序列化

### 5. Repositories Layer（仓库层）
**位置**: `src/fall_detection/repositories/`

**职责**:
- 数据访问抽象
- ORM 封装
- 查询构建
- 缓存策略

---

## 📦 包导入方式

### 旧方式（已废弃）
```python
from src.auth.auth_service import AuthService
from src.camera.multi_camera_manager import get_camera_manager
```

### 新方式（推荐）
```python
from fall_detection.services import AuthService
from fall_detection.cameras import CameraManager
```

### 完整示例
```python
#!/usr/bin/env python3
"""使用新结构的示例代码"""

from fall_detection import FallDetectionSystem, AuthService
from fall_detection.services import DetectionService
from fall_detection.cameras import CameraManager, CameraConfig

# 初始化服务
auth_service = AuthService()
camera_mgr = CameraManager()
detection_service = DetectionService()

# 添加摄像头
config = CameraConfig(
    id="cam1",
    name="客厅摄像头",
    source=0,
    camera_type="usb"
)
camera_mgr.add_camera(config)

# 启动检测
detection_service.start(camera_id="cam1")
```

---

## 🔧 迁移步骤

### 阶段 1: 双轨运行（当前）
- ✅ 新旧结构并存
- ✅ 向后兼容
- ✅ 逐步迁移

### 阶段 2: 完全迁移（TODO）
1. 迁移所有 `src/*/` 到 `src/fall_detection/*/`
2. 更新所有导入语句
3. 删除旧的 `app_optimized.py`
4. 更新启动脚本

### 阶段 3: 清理优化（TODO）
1. 删除废弃的旧文件
2. 完善测试覆盖
3. 更新文档
4. 发布 v2.0

---

## 🚀 使用新结构启动

### 方式 1: Streamlit Web 界面
```bash
# 新入口（推荐）
streamlit run app/main.py

# 旧入口（仍然可用，向后兼容）
streamlit run app_optimized.py
```

### 方式 2: FastAPI 后端
```bash
# 安装为可编辑包
pip install -e .

# 启动 FastAPI
uvicorn fall_detection.api.main:app --reload

# 或使用命令行工具
fall-detection-api --host 0.0.0.0 --port 8000
```

### 方式 3: Docker 容器
```bash
# 使用新 Dockerfile
docker build -f docker/Dockerfile -t fall-detection:latest .
docker run -p 8501:8501 -p 8000:8000 fall-detection:latest
```

---

## ⚙️ 配置迁移

### 环境变量（.env）
```bash
# 复制模板
cp .env.example .env

# 必填配置
JWT_SECRET="your-secret-key"
DATABASE_URL="sqlite:///data/database.db"

# 可选配置
APP_ENV=production
DEBUG=false
```

### YAML 配置（configs/default.yaml）
```yaml
# 替代原来的 config.json
app:
  name: "Fall Detection System"
  version: "1.6.0"
  
server:
  host: "0.0.0.0"
  port: 8501

camera:
  max_cameras: 16
  default_fps: 30
```

---

## 🧪 测试规范

### 运行测试
```bash
# 所有测试
pytest

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=fall_detection --cov-report=html
```

### 测试目录结构
```
tests/
├── unit/              # 单元测试
│   ├── test_core/
│   ├── test_services/
│   └── test_api/
├── integration/       # 集成测试
│   └── test_detection_flow.py
└── fixtures/          # 测试数据
    └── sample_data.json
```

---

## 📝 代码规范

### 导入顺序
```python
# 1. 标准库
import os
import sys
from typing import List, Optional

# 2. 第三方库
import streamlit as st
import numpy as np
import cv2

# 3. 项目内部
from fall_detection.core import FallDetectionSystem
from fall_detection.services import AuthService
```

### 类命名
```python
# ✅ 推荐
class FallDetectionSystem:  # 业务核心类
class AuthService:          # 服务类
class CameraManager:        # 管理类
class DetectionError(Exception):  # 异常类

# ❌ 避免
class fall_detection_system:  # 不要用小写
class AUTH_SERVICE:           # 不要用全大写（常量才用）
```

### 函数命名
```python
# ✅ 推荐
def process_frame(frame):
def authenticate_user(username, password):
def is_falling(person_bbox):
def get_camera_status(camera_id):

# ❌ 避免
def ProcessFrame(frame):  # 不要用 CamelCase
def proc_frame(f):        # 不要过度缩写
```

---

## 🔍 常见问题

### Q1: 为什么要重构？
**A**: 
- 符合 Harness 工程规范
- 更好的模块化和可维护性
- 便于团队协作
- 支持 CI/CD 自动化

### Q2: 旧代码还能用吗？
**A**: 是的，当前采用双轨制，旧代码仍然可以运行，但建议逐步迁移到新结构。

### Q3: 如何迁移现有代码？
**A**: 
1. 将业务逻辑移到 `src/fall_detection/core/`
2. 将服务封装到 `src/fall_detection/services/`
3. 更新导入语句
4. 运行测试确保功能正常

### Q4: 影响现有功能吗？
**A**: 不影响。新结构与旧结构并行，所有现有功能保持不变。

### Q5: 需要重新安装依赖吗？
**A**: 不需要。`requirements.txt` 仍然可用，新的 `pyproject.toml` 是可选的增强。

---

## 📚 相关文档

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 详细项目结构规范
- [README_HARNESS.md](README_HARNESS.md) - Harness 版本使用说明
- [.env.example](.env.example) - 环境变量模板
- [configs/default.yaml](configs/default.yaml) - 默认配置文件

---

## 🎯 下一步计划

### 近期（v1.7）
- [ ] 迁移剩余模块到新结构
- [ ] 完善 API 文档（OpenAPI/Swagger）
- [ ] 添加更多单元测试
- [ ] 配置 GitHub Actions CI/CD

### 中期（v1.8）
- [ ] 删除旧结构（完全切换）
- [ ] 发布到 PyPI
- [ ] 添加 Helm Chart（K8s 部署）
- [ ] 性能优化与基准测试

### 长期（v2.0）
- [ ] 微服务架构拆分
- [ ] 云端部署方案
- [ ] 移动端 App
- [ ] AI 模型持续训练

---

**迁移支持**: 如有问题请提交 Issue 或联系开发团队  
**更新日期**: 2026-04-13  
**版本**: v1.6.0 (Harness Ready)
