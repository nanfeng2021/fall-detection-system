# 🛡️ Fall Detection System v1.6

**室内人体摔倒实时预警系统 - Harness Engineering 规范版**

[![Version](https://img.shields.io/badge/version-1.6.0-blue.svg)](https://github.com/nanfeng2021/fall-detection-system)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)]()

---

## 📋 目录

- [快速开始](#-快速开始)
- [项目结构](#-项目结构)
- [功能特性](#-功能特性)
- [安装部署](#-安装部署)
- [配置说明](#-配置说明)
- [API 文档](#-api-文档)
- [开发指南](#-开发指南)
- [常见问题](#-常见问题)

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/nanfeng2021/fall-detection-system.git
cd fall-detection-system
```

### 2. 安装依赖
```bash
pip install -e .
# 或
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置 JWT_SECRET 等关键参数
```

### 4. 启动应用
```bash
# 方式 1: Streamlit Web 界面
streamlit run app/main.py

# 方式 2: FastAPI 后端服务
uvicorn app.api:app --host 0.0.0.0 --port 8000

# 方式 3: Docker 容器
docker-compose up -d
```

### 5. 访问系统
- **Web 界面**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs
- **默认账户**: admin / admin123

---

## 📁 项目结构

```
fall-detection-system/
├── src/fall_detection/       # 核心代码包
│   ├── core/                 # 核心业务逻辑
│   ├── services/             # 业务服务层
│   ├── api/                  # API 接口层
│   ├── models/               # 数据模型
│   ├── repositories/         # 数据访问层
│   ├── cameras/              # 摄像头管理
│   ├── preprocessing/        # 数据预处理
│   ├── monitoring/           # 监控告警
│   └── utils/                # 工具函数
├── app/                      # 应用入口
│   ├── main.py              # Streamlit 主应用
│   └── api.py               # FastAPI 应用
├── pages/                    # Streamlit 多页面
├── tests/                    # 测试代码
├── configs/                  # 配置文件
├── data/                     # 数据目录
├── scripts/                  # 运维脚本
├── docs/                     # 文档目录
└── docker/                   # Docker 配置
```

详细说明请参考 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## ✨ 功能特性

### 🔐 安全认证
- ✅ JWT Token 认证
- ✅ 双因素认证 (2FA/TOTP)
- ✅ 登录失败锁定机制
- ✅ 密码强度验证
- ✅ 会话管理（踢人下线）
- ✅ 忘记密码自助流程

### 📹 多摄像头监控
- ✅ 支持 USB/RTSP/HTTP 摄像头
- ✅ 16+ 路并发处理
- ✅ 1x1/2x2/3x3 多画面预览
- ✅ 独立检测实例
- ✅ 统一告警管理

### 🎯 摔倒检测
- ✅ 基于点云分析的 3D 检测算法
- ✅ 多特征融合（高度 + 速度 + 姿态）
- ✅ 可配置检测频率（5-20 FPS）
- ✅ 告警防抖动（30 秒冷却期）
- ✅ 实时统计与监控

### 📊 管理后台
- ✅ 用户管理（CRUD + 批量操作）
- ✅ 系统仪表板（资源监控）
- ✅ 安全中心（2FA 设置/修改密码）
- ✅ 登录历史查看
- ✅ 活跃会话管理

### 🚨 多渠道告警
- ✅ 微信推送（企业微信/公众号）
- ✅ 短信通知（腾讯云/阿里云）
- ✅ 邮件通知（SMTP）
- ✅ 飞书机器人
- ✅ 语音电话（待实现）

### 💾 数据存储
- ✅ SQLite 数据库（默认）
- ✅ PostgreSQL/MySQL 支持
- ✅ 录像文件自动管理
- ✅ 告警历史记录
- ✅ 数据导出功能

---

## 🛠️ 安装部署

### 本地开发环境

#### 前置要求
- Python 3.8+
- pip
- Git

#### 安装步骤
```bash
# 1. 克隆项目
git clone https://github.com/nanfeng2021/fall-detection-system.git
cd fall-detection-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 配置环境
cp .env.example .env
# 编辑 .env 文件

# 5. 运行测试
pytest

# 6. 启动应用
streamlit run app/main.py
```

### 生产环境部署

#### Docker 部署（推荐）
```bash
# 1. 构建镜像
docker build -t fall-detection:latest .

# 2. 启动容器
docker-compose up -d

# 3. 查看日志
docker-compose logs -f app

# 4. 停止服务
docker-compose down
```

#### Systemd 部署
```bash
# 1. 复制服务文件
sudo cp fall-detection.service /etc/systemd/system/

# 2. 启用服务
sudo systemctl enable fall-detection
sudo systemctl start fall-detection

# 3. 查看状态
sudo systemctl status fall-detection
```

#### Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

---

## ⚙️ 配置说明

### 环境变量（.env）

```bash
# 必填配置
JWT_SECRET="your-secret-key-change-in-production"
DATABASE_URL="sqlite:///data/database.db"

# 可选配置
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

### 配置文件（configs/default.yaml）

```yaml
app:
  name: "Fall Detection System"
  environment: production
  debug: false

server:
  host: "0.0.0.0"
  port: 8501
  workers: 4

camera:
  max_cameras: 16
  default_fps: 30

detection:
  confidence_threshold: 0.7
  alert_cooldown_seconds: 30
```

完整配置参考 [.env.example](.env.example) 和 [configs/default.yaml](configs/default.yaml)

---

## 📡 API 文档

启动 FastAPI 服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要接口

#### 认证相关
```bash
# 用户登录
POST /api/auth/login
{
  "username": "admin",
  "password": "admin123"
}

# 刷新 Token
POST /api/auth/refresh

# 退出登录
POST /api/auth/logout
```

#### 检测相关
```bash
# 获取检测状态
GET /api/detection/status

# 手动触发检测
POST /api/detection/trigger

# 获取告警历史
GET /api/detection/alerts
```

#### 摄像头相关
```bash
# 获取摄像头列表
GET /api/cameras

# 添加摄像头
POST /api/cameras

# 控制摄像头
PUT /api/cameras/{camera_id}/control
```

---

## 👩‍💻 开发指南

### 代码规范
- 遵循 PEP 8 风格指南
- 使用 Black 格式化代码
- 使用 Ruff 进行代码检查
- 类型注解覆盖率达到 90%+

```bash
# 代码格式化
black src/ app/ tests/

# 代码检查
ruff check src/ app/ tests/

# 类型检查
mypy src/ app/
```

### 测试规范
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_core/

# 生成覆盖率报告
pytest --cov=fall_detection --cov-report=html

# 查看覆盖率
open htmlcov/index.html
```

### 提交规范
```bash
# Commit Message 格式
feat: 添加多摄像头支持
fix: 修复登录失败问题
docs: 更新 API 文档
test: 添加单元测试
refactor: 重构认证模块
```

---

## ❓ 常见问题

### Q1: 无法启动服务？
**A**: 检查依赖是否完整安装，查看日志：
```bash
tail -f /tmp/fall-detection.log
```

### Q2: 摄像头无法连接？
**A**: 确认摄像头地址正确，检查网络连通性：
```bash
ping camera-ip-address
```

### Q3: 检测准确率不高？
**A**: 调整检测阈值参数：
```yaml
detection:
  voxel_size: 0.05  # 减小提高精度
  height_drop_threshold: 0.3
  confidence_threshold: 0.7  # 提高减少误报
```

### Q4: 如何备份数据？
**A**: 运行备份脚本：
```bash
./scripts/backup.sh
```

### Q5: 忘记密码怎么办？
**A**: 访问"忘记密码"页面或使用脚本重置：
```bash
./scripts/reset_password.py admin newpassword123
```

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📞 联系方式

- **作者**: Nanfeng
- **邮箱**: nanfeng@example.com
- **项目地址**: https://github.com/nanfeng2021/fall-detection-system
- **问题反馈**: https://github.com/nanfeng2021/fall-detection-system/issues

---

## 🗺️ 路线图

### v1.6 (Current)
- ✅ 多摄像头监控
- ✅ 独立摔倒检测
- ✅ 统一告警管理
- ✅ Harness 工程规范

### v1.7 (Next)
- [ ] 跨摄像头人员追踪
- [ ] 风险热力图
- [ ] AI 预测模型

### v2.0 (Future)
- [ ] 云端部署
- [ ] 移动端 App
- [ ] 语音电话通知

---

**Made with ❤️ by the Fall Detection Team**  
**版本**: v1.6.0 | **更新日期**: 2026-04-13
