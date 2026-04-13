# Fall Detection System - Harness Engineering Structure

## 📁 项目结构规范

本项目遵循 Harness 工程最佳实践，采用模块化、分层架构设计。

```
fall-detection-system/
├── 📄 README.md                 # 项目说明文档
├── 📄 LICENSE                   # 开源许可证
├── 📄 requirements.txt          # Python 依赖清单
├── 📄 setup.py                  # 包安装配置（可选）
├── 📄 pyproject.toml           # 现代 Python 项目配置
├── 📄 .gitignore               # Git 忽略规则
├── 📄 .env.example             # 环境变量模板
│
├── 📁 src/                     # 源代码目录
│   └── fall_detection/         # 主包名
│       ├── __init__.py         # 包初始化
│       │
│       ├── 📁 core/            # 核心业务逻辑
│       │   ├── __init__.py
│       │   ├── detector.py     # 摔倒检测算法
│       │   ├── analyzer.py     # 数据分析引擎
│       │   └── rules.py        # 检测规则定义
│       │
│       ├── 📁 api/             # API 接口层
│       │   ├── __init__.py
│       │   ├── routes/         # 路由定义
│       │   │   ├── auth.py
│       │   │   ├── detection.py
│       │   │   └── camera.py
│       │   ├── schemas/        # Pydantic 模型
│       │   │   ├── auth.py
│       │   │   └── detection.py
│       │   └── deps.py         # 依赖注入
│       │
│       ├── 📁 services/        # 业务服务层
│       │   ├── __init__.py
│       │   ├── auth_service.py     # 认证服务
│       │   ├── detection_service.py # 检测服务
│       │   ├── notification_service.py # 通知服务
│       │   └── camera_service.py    # 摄像头服务
│       │
│       ├── 📁 models/          # 数据模型层
│       │   ├── __init__.py
│       │   ├── user.py         # 用户模型
│       │   ├── alert.py        # 告警模型
│       │   └── config.py       # 配置模型
│       │
│       ├── 📁 repositories/    # 数据访问层
│       │   ├── __init__.py
│       │   ├── user_repo.py    # 用户数据访问
│       │   └── alert_repo.py   # 告警数据访问
│       │
│       ├── 📁 cameras/         # 摄像头管理
│       │   ├── __init__.py
│       │   ├── manager.py      # 多摄像头管理器
│       │   ├── stream.py       # 视频流处理
│       │   └── config.py       # 摄像头配置
│       │
│       ├── 📁 preprocessing/   # 数据预处理
│       │   ├── __init__.py
│       │   ├── filtering.py    # 滤波算法
│       │   ├── segmentation.py # 分割算法
│       │   └── pipeline.py     # 处理流水线
│       │
│       ├── 📁 monitoring/      # 监控告警
│       │   ├── __init__.py
│       │   ├── notifier.py     # 通知器
│       │   ├── metrics.py      # 指标收集
│       │   └── alerter.py      # 告警分发
│       │
│       ├── 📁 utils/           # 工具函数
│       │   ├── __init__.py
│       │   ├── logger.py       # 日志配置
│       │   ├── config.py       # 配置加载
│       │   └── helpers.py      # 辅助函数
│       │
│       └── 📁 exceptions/      # 异常定义
│           ├── __init__.py
│           └── handlers.py     # 异常处理器
│
├── 📁 app/                     # 应用入口
│   ├── __init__.py
│   ├── main.py                # FastAPI 主应用
│   └── streamlit_app.py       # Streamlit Web 界面
│
├── 📁 pages/                   # Streamlit 多页面
│   ├── dashboard.py           # 主仪表板
│   ├── multi_camera.py        # 多摄像头监控
│   ├── detection_board.py     # 检测仪表板
│   ├── user_management.py     # 用户管理
│   ├── security_center.py     # 安全中心
│   └── settings.py            # 系统设置
│
├── 📁 tests/                   # 测试代码
│   ├── __init__.py
│   ├── conftest.py            # pytest 配置
│   ├── test_core/             # 核心测试
│   ├── test_api/              # API 测试
│   ├── test_services/         # 服务测试
│   └── test_integration/      # 集成测试
│
├── 📁 scripts/                 # 运维脚本
│   ├── deploy.sh              # 部署脚本
│   ├── backup.sh              # 备份脚本
│   ├── cleanup.sh             # 清理脚本
│   └── migrate.py             # 数据库迁移
│
├── 📁 configs/                 # 配置文件
│   ├── default.yaml           # 默认配置
│   ├── production.yaml        # 生产环境配置
│   ├── development.yaml       # 开发环境配置
│   └── cameras.yaml           # 摄像头配置
│
├── 📁 data/                    # 数据目录
│   ├── database.db            # SQLite 数据库
│   ├── recordings/            # 录像文件
│   ├── exports/               # 导出文件
│   └── cache/                 # 缓存文件
│
├── 📁 docs/                    # 文档目录
│   ├── api.md                 # API 文档
│   ├── deployment.md          # 部署指南
│   ├── architecture.md        # 架构设计
│   └── development.md         # 开发指南
│
├── 📁 docker/                  # Docker 相关
│   ├── Dockerfile             # 主镜像
│   ├── Dockerfile.dev         # 开发镜像
│   └── docker-compose.yml     # 编排配置
│
└── 📁 .github/                 # GitHub 配置
    └── workflows/             # CI/CD 流程
        ├── ci.yml             # 持续集成
        └── cd.yml             # 持续部署
```

## 🏗️ 分层架构说明

### 1. **Core Layer** (`src/fall_detection/core/`)
- 核心业务逻辑
- 摔倒检测算法实现
- 数据处理规则
- **无外部依赖**，纯业务逻辑

### 2. **Services Layer** (`src/fall_detection/services/`)
- 业务服务封装
- 跨模块协调
- 事务管理
- 调用 Core + Repositories

### 3. **API Layer** (`src/fall_detection/api/`)
- RESTful API 定义
- 请求/响应模型
- 认证授权
- 输入验证

### 4. **Repositories Layer** (`src/fall_detection/repositories/`)
- 数据访问抽象
- ORM 封装
- 查询构建
- 缓存策略

### 5. **Models Layer** (`src/fall_detection/models/`)
- 数据模型定义
- Pydantic Schemas
- 数据库模型
- 序列化/反序列化

## 📝 命名规范

### 文件命名
- ✅ `snake_case.py` - Python 文件
- ✅ `kebab-case.md` - 文档文件
- ✅ `.extension` - 配置文件

### 类命名
- ✅ `CamelCase` - 类名
- ✅ `Exception` - 异常类后缀
- ✅ `Service` - 服务类后缀
- ✅ `Repository` - 仓库类后缀

### 函数命名
- ✅ `snake_case()` - 函数名
- ✅ `is_`, `has_`, `can_` - 布尔返回
- ✅ `get_`, `set_`, `create_`, `delete_` - CRUD 操作

### 变量命名
- ✅ `snake_case` - 普通变量
- ✅ `UPPER_CASE` - 常量
- ✅ `_private` - 私有变量
- ✅ `__dunder__` - 魔术方法

## 🔧 配置管理

### 环境变量优先级
1. 操作系统环境变量
2. `.env` 文件
3. `configs/*.yaml` 配置文件
4. 代码中的默认值

### 配置文件结构
```yaml
# configs/default.yaml
app:
  name: "Fall Detection System"
  version: "1.6.0"
  debug: false

database:
  url: "sqlite:///data/database.db"
  pool_size: 10

auth:
  jwt_secret: "${JWT_SECRET}"  # 从环境变量读取
  jwt_expire_minutes: 30

camera:
  default_fps: 30
  max_cameras: 16

notification:
  enabled: true
  channels:
    - wechat
    - sms
    - email
```

## 🧪 测试规范

### 测试目录结构
```
tests/
├── unit/              # 单元测试
├── integration/       # 集成测试
├── e2e/              # 端到端测试
└── fixtures/         # 测试数据
```

### 测试文件命名
- `test_*.py` - 测试文件
- `conftest.py` - pytest 配置
- `test_<module>_<function>.py` - 具体测试

### 测试覆盖率要求
- Core: ≥95%
- Services: ≥90%
- API: ≥85%
- 总体：≥90%

## 🚀 部署规范

### 环境隔离
- `development` - 开发环境
- `staging` - 预发布环境
- `production` - 生产环境

### 容器化部署
```bash
# 构建镜像
docker build -t fall-detection:latest .

# 运行容器
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 健康检查
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## 📊 日志规范

### 日志级别
- `DEBUG` - 调试信息
- `INFO` - 一般信息
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `CRITICAL` - 严重错误

### 日志格式
```json
{
  "timestamp": "2026-04-13T23:48:00Z",
  "level": "INFO",
  "module": "detection_service",
  "message": "Fall detected",
  "context": {
    "camera_id": "cam1",
    "confidence": 0.95,
    "user_id": "admin"
  }
}
```

## 🔒 安全规范

### 认证授权
- JWT Token 认证
- RBAC 权限控制
- API Rate Limiting
- CORS 配置

### 数据安全
- 密码 bcrypt 加密
- 敏感信息环境变量
- SQL 注入防护
- XSS 防护

### 审计日志
- 登录日志
- 操作日志
- 异常日志
- 访问日志

## 📈 监控指标

### 应用指标
- QPS (Queries Per Second)
- 响应时间 (P50/P95/P99)
- 错误率
- 活跃连接数

### 业务指标
- 检测准确率
- 告警响应时间
- 摄像头在线率
- 用户活跃度

### 系统指标
- CPU 使用率
- 内存使用率
- 磁盘使用率
- 网络流量

---

**版本**: v1.6  
**更新日期**: 2026-04-13  
**维护者**: 旺财 🐕
