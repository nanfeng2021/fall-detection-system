# 用户认证与监控告警系统实现文档

**版本**: v1.1.0  
**日期**: 2026-04-13  
**作者**: GuardianFall Team

---

## 📋 目录

1. [功能概述](#功能概述)
2. [用户认证系统](#用户认证系统)
3. [监控告警系统](#监控告警系统)
4. [通知服务](#通知服务)
5. [快速开始](#快速开始)
6. [API 使用示例](#api 使用示例)
7. [配置说明](#配置说明)

---

## 🎯 功能概述

本次更新新增了以下核心功能：

### 1. 用户认证系统 🔐
- ✅ JWT Token 认证
- ✅ 用户注册/登录
- ✅ 角色权限管理（Admin/Operator/Viewer）
- ✅ 密码加密存储（bcrypt）
- ✅ Token 自动过期

### 2. 监控告警系统 📊
- ✅ Prometheus 指标采集
- ✅ 系统性能监控（FPS、CPU、内存）
- ✅ 检测统计追踪
- ✅ 多级告警管理（Info/Warning/Error/Critical）
- ✅ 告警历史记录

### 3. 通知服务 📧
- ✅ 邮件通知（SMTP）
- ✅ 企业微信通知（Webhook/API）
- ✅ 告警自动推送
- ✅ 支持@提及

---

## 🔐 用户认证系统

### 架构设计

```
src/auth/
├── __init__.py           # 模块导出
├── models.py             # 数据模型（User, Token, etc.）
├── auth_service.py       # 认证服务（注册/登录/Token 管理）
└── dependencies.py       # FastAPI 依赖（权限验证）
```

### 核心功能

#### 1. 用户模型

```python
class User(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole  # admin, operator, viewer
    is_active: bool
    created_at: datetime
    last_login: datetime
```

#### 2. 角色权限

| 角色 | 权限 |
|------|------|
| **admin** | 所有权限（用户管理、系统配置） |
| **operator** | 操作权限（启动/停止检测、查看告警） |
| **viewer** | 只读权限（查看状态、统计数据） |

#### 3. JWT Token

- **算法**: HS256
- **有效期**: 30 分钟（可配置）
- **刷新**: 需要重新登录

### API 接口

#### 用户注册
```bash
POST /api/v1/auth/register
{
  "username": "newuser",
  "email": "user@example.com",
  "password": "securepassword123"
}
```

#### 用户登录
```bash
POST /api/v1/auth/login
{
  "username": "admin",
  "password": "admin123"
}

# 响应
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

#### 获取当前用户信息
```bash
GET /api/v1/auth/me
Authorization: Bearer <token>
```

---

## 📊 监控告警系统

### 架构设计

```
src/monitoring/
├── __init__.py           # 模块导出
├── metrics.py            # Prometheus 指标采集
├── alerter.py            # 告警管理器
└── notifiers.py          # 通知器（邮件/微信）
```

### Prometheus 指标

#### 系统性能指标
- `fall_detection_fps` - 当前处理 FPS
- `fall_detection_processing_time_seconds` - 处理时间直方图
- `fall_detection_memory_bytes` - 内存使用量
- `fall_detection_cpu_percent` - CPU 使用率

#### 检测统计指标
- `fall_detection_frames_total` - 已处理帧数
- `fall_detection_detections_total` - 检测总数
- `fall_detection_alerts_total` - 告警总数

#### 状态指标
- `fall_detection_system_status` - 系统状态（1=运行，0=停止）
- `fall_detection_camera_status` - 摄像头连接状态

### 告警级别

| 级别 | 说明 | 通知方式 |
|------|------|----------|
| **INFO** | 信息提示 | 仅记录 |
| **WARNING** | 警告 | 记录 + 日志 |
| **ERROR** | 错误 | 记录 + 邮件 |
| **CRITICAL** | 严重 | 记录 + 邮件 + 微信 |

### API 接口

#### 获取告警列表
```bash
GET /api/v1/alerts?limit=50&level=critical
Authorization: Bearer <token>
```

#### 确认告警
```bash
POST /api/v1/alerts/{alert_id}/acknowledge
Authorization: Bearer <token>
```

#### 获取告警统计
```bash
GET /api/v1/alerts/statistics
Authorization: Bearer <token>
```

---

## 📧 通知服务

### 邮件通知配置

```yaml
notifications:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 465
    username: "your-email@gmail.com"
    password: "your-app-password"
    from_addr: "your-email@gmail.com"
    to_addrs: ["admin@example.com"]
```

### 企业微信配置

#### 方式 1: Webhook 机器人（推荐）

1. 在企业微信群中添加机器人
2. 获取 Webhook URL
3. 配置文件：

```yaml
notifications:
  wechat:
    enabled: true
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
```

#### 方式 2: 企业微信 API

```yaml
notifications:
  wechat:
    enabled: true
    corp_id: "your-corp-id"
    corp_secret: "your-corp-secret"
    agent_id: 1000001
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /root/.openclaw/workspace/projects/fall-detection-system
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config.yaml`：

```yaml
# 修改 JWT 密钥（重要！）
auth:
  jwt_secret: "your-random-secret-key-here"
  jwt_expire_minutes: 30

# 配置通知（可选）
notifications:
  email:
    enabled: true
    smtp_server: "smtp.example.com"
    username: "your-email@example.com"
    password: "your-password"
  
  wechat:
    enabled: true
    webhook_url: "your-webhook-url"
```

### 3. 启动服务

```bash
# 启动 API 服务（包含认证和监控）
python -m src.api.main

# 或使用 uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs

---

## 💡 API 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 登录
login_response = requests.post(f"{BASE_URL}/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
token = login_response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 2. 获取系统状态
status = requests.get(f"{BASE_URL}/status", headers=headers)
print(status.json())

# 3. 获取活动告警
alerts = requests.get(f"{BASE_URL}/alerts/active", headers=headers)
print(alerts.json())

# 4. 确认告警
alert_id = 1234567890.0
ack = requests.post(f"{BASE_URL}/alerts/{alert_id}/acknowledge", headers=headers)
print(ack.json())
```

### cURL 示例

```bash
# 登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取用户信息
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 启动检测
curl -X POST "http://localhost:8000/api/v1/detection/start" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"camera_id":0}'
```

---

## ⚙️ 配置说明

### config.yaml 新增配置项

```yaml
# ==================== 认证配置 ====================
auth:
  jwt_secret: "change-this-in-production"  # ⚠️ 必须修改
  jwt_expire_minutes: 30
  
  session:
    max_sessions_per_user: 5
    session_timeout_minutes: 60

# ==================== 监控配置 ====================
monitoring:
  metrics_port: 9090
  
  health_check:
    enabled: true
    interval_seconds: 30
  
  performance:
    enabled: true
    log_slow_frames: true
    slow_threshold_ms: 100

# ==================== 通知配置 ====================
notifications:
  email:
    enabled: false
    smtp_server: "smtp.example.com"
    smtp_port: 465
    username: "your-email@example.com"
    password: "your-password"
    from_addr: "your-email@example.com"
    to_addrs: ["admin@example.com"]
  
  wechat:
    enabled: false
    webhook_url: ""
    corp_id: ""
    corp_secret: ""
    agent_id: 1000001
```

---

## 🔒 安全建议

### 生产环境部署

1. **修改 JWT 密钥**
   ```bash
   # 生成随机密钥
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **启用 HTTPS**
   - 使用 Nginx 反向代理
   - 配置 SSL 证书

3. **限制访问 IP**
   ```yaml
   api:
     allowed_ips: ["127.0.0.1", "192.168.1.0/24"]
   ```

4. **定期备份用户数据**
   ```bash
   cp data/users.json backup/users_$(date +%Y%m%d).json
   ```

---

## 📈 监控面板

### Prometheus + Grafana

1. **安装 Prometheus**
   ```bash
   docker run -d --name prometheus \
     -p 9090:9090 \
     -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
     prom/prometheus
   ```

2. **配置 prometheus.yml**
   ```yaml
   scrape_configs:
     - job_name: 'fall-detection'
       static_configs:
         - targets: ['localhost:9090']
   ```

3. **安装 Grafana**
   ```bash
   docker run -d --name grafana \
     -p 3000:3000 \
     grafana/grafana
   ```

4. **导入 Dashboard**
   - 访问 http://localhost:3000
   - 添加 Prometheus 数据源
   - 导入自定义 Dashboard

---

## 🎉 总结

本次更新为 GuardianFall 系统添加了完整的企业级功能：

✅ **用户认证** - 安全的 JWT 认证和权限管理  
✅ **监控告警** - 实时的性能监控和多级告警  
✅ **通知推送** - 邮件和企业微信自动通知  
✅ **API 文档** - 完整的 Swagger 文档

所有代码已提交到代码仓，可以直接使用！🚀
