# 🚀 摔倒检测系统 - 完整部署指南

## 📋 目录

1. [快速开始](#快速开始)
2. [Docker 部署（推荐）](#docker-部署推荐)
3. [手动部署](#手动部署)
4. [生产环境配置](#生产环境配置)
5. [监控与维护](#监控与维护)
6. [故障排查](#故障排查)

---

## 🎯 快速开始

### 一键部署（最简单）

```bash
cd /root/.openclaw/workspace/projects/fall-detection-system

# 赋予执行权限
chmod +x deploy.sh

# 执行部署
sudo ./deploy.sh
```

**部署完成后访问**:
- 本地：http://localhost:8501
- 远程：http://<服务器IP>:8501

---

## 🐳 Docker 部署（推荐）

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 内存
- 10GB+ 磁盘空间

### 方式 1: 使用部署脚本（推荐）

```bash
# 完整部署
sudo ./deploy.sh

# 更新部署
sudo ./deploy.sh update

# 查看状态
sudo ./deploy.sh status

# 查看日志
sudo ./deploy.sh logs

# 停止服务
sudo ./deploy.sh stop

# 清理资源
sudo ./deploy.sh cleanup
```

### 方式 2: 使用 Docker Compose

```bash
# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f fall-detection

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 清理所有资源
docker-compose down -v --rmi all
```

### 方式 3: 使用 Docker 命令

```bash
# 构建镜像
docker build -t fall-detection-system .

# 启动容器
docker run -d \
  --name fall-detection-system \
  -p 8501:8501 \
  -v $(pwd)/datasets:/app/datasets \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/configs:/app/configs \
  --restart unless-stopped \
  fall-detection-system

# 查看日志
docker logs -f fall-detection-system

# 停止容器
docker stop fall-detection-system

# 删除容器
docker rm fall-detection-system
```

---

## 💻 手动部署（无 Docker）

### 步骤 1: 安装依赖

```bash
# 安装 Python 3.10+
apt-get update
apt-get install -y python3 python3-pip python3-venv

# 安装系统依赖
apt-get install -y libgl1-mesa-glx libglib2.0-0 ffmpeg libsm6 libxext6

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt
```

### 步骤 2: 配置 systemd 服务

```bash
# 复制服务文件
sudo cp fall-detection.service /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable fall-detection

# 启动服务
sudo systemctl start fall-detection

# 查看状态
sudo systemctl status fall-detection
```

### 步骤 3: 手动运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 Streamlit
streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true
```

---

## 🏭 生产环境配置

### Nginx 反向代理

#### 步骤 1: 安装 Nginx

```bash
apt-get install -y nginx
```

#### 步骤 2: 配置 Nginx

```bash
# 复制配置文件
sudo cp nginx.conf /etc/nginx/nginx.conf

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 步骤 3: 配置 SSL 证书（Let's Encrypt）

```bash
# 安装 Certbot
apt-get install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d ainfanfeng.cn -d www.ainfanfeng.cn

# 自动续期
sudo crontab -e
# 添加：0 3 * * * certbot renew --quiet
```

### 防火墙配置

```bash
# 安装 UFW
apt-get install -y ufw

# 允许 SSH
ufw allow 22/tcp

# 允许 HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# 允许 Streamlit 端口（可选，如果只用 Nginx 则不需要）
ufw allow 8501/tcp

# 启用防火墙
ufw enable

# 查看状态
ufw status
```

### 优化系统配置

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化网络配置
cat >> /etc/sysctl.conf << EOF
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
EOF

sysctl -p
```

---

## 📊 监控与维护

### 使用监控脚本

```bash
# 赋予执行权限
chmod +x monitor.sh

# 查看状态
./monitor.sh status

# 查看日志
./monitor.sh logs

# 显示统计
./monitor.sh stats

# 持续监控
./monitor.sh monitor

# 重启服务
./monitor.sh restart
```

### 手动监控命令

```bash
# 查看 Docker 容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f fall-detection

# 查看资源使用
docker stats fall-detection-system

# 查看进程
ps aux | grep streamlit

# 查看端口监听
ss -tlnp | grep 8501

# 查看网络连接
netstat -anp | grep 8501
```

### 性能监控

```bash
# CPU 和内存
top -p $(pgrep -f streamlit)

# 或使用 htop
htop -p $(pgrep -f streamlit)

# 磁盘 I/O
iotop -o

# 网络流量
iftop -P -n -p
```

### 日志管理

```bash
# 查看应用日志
journalctl -u fall-detection -f

# 查看 Docker 日志
docker-compose logs -f fall-detection

# 查看 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 轮转日志（防止过大）
logrotate -f /etc/logrotate.conf
```

---

## 🐛 故障排查

### 问题 1: 服务无法启动

**检查 Docker 状态**:
```bash
systemctl status docker
docker info
```

**查看详细错误**:
```bash
docker-compose logs fall-detection
```

**常见原因**:
- 端口被占用：`ss -tlnp | grep 8501`
- 内存不足：`free -h`
- 依赖缺失：`docker-compose build --no-cache`

### 问题 2: 无法访问 Web 界面

**检查服务状态**:
```bash
curl -I http://localhost:8501
```

**检查防火墙**:
```bash
ufw status
iptables -L -n | grep 8501
```

**检查端口监听**:
```bash
ss -tlnp | grep 8501
```

### 问题 3: 性能低下

**检查资源使用**:
```bash
docker stats
free -h
df -h
```

**优化建议**:
- 增大体素尺寸（降低点云精度）
- 降低帧率设置
- 增加服务器资源
- 使用 SSD 存储

### 问题 4: 频繁崩溃

**查看崩溃日志**:
```bash
docker inspect fall-detection-system | grep -A 20 State
journalctl -u fall-detection -xe
```

**增加 Swap**（如果内存不足）:
```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 问题 5: Docker 相关问题

**重置 Docker**:
```bash
# 停止所有容器
docker-compose down

# 删除所有镜像
docker rmi -f $(docker images -q)

# 清理系统
docker system prune -a --volumes

# 重新启动
docker-compose up -d --build
```

---

## 📝 备份与恢复

### 备份数据

```bash
# 创建备份目录
mkdir -p /backup/fall-detection

# 备份数据集
tar -czf /backup/fall-detection/datasets_$(date +%Y%m%d).tar.gz datasets/

# 备份配置
tar -czf /backup/fall-detection/configs_$(date +%Y%m%d).tar.gz configs/

# 备份日志（可选）
tar -czf /backup/fall-detection/logs_$(date +%Y%m%d).tar.gz logs/
```

### 恢复数据

```bash
# 停止服务
docker-compose down

# 恢复数据集
tar -xzf /backup/fall-detection/datasets_YYYYMMDD.tar.gz -C /

# 恢复配置
tar -xzf /backup/fall-detection/configs_YYYYMMDD.tar.gz -C /

# 启动服务
docker-compose up -d
```

---

## 🔄 更新升级

### 自动更新

```bash
# 拉取最新代码
git pull origin main

# 重新构建并部署
sudo ./deploy.sh update
```

### 手动更新

```bash
# 停止服务
docker-compose down

# 拉取最新代码
git pull

# 重新构建
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看日志确认
docker-compose logs -f
```

---

## 📞 获取帮助

### 查看文档

```bash
# 用户指南
cat docs/USER_GUIDE.md

# Web UI 指南
cat docs/WEB_UI_GUIDE.md

# 部署指南
cat docs/DEPLOYMENT.md
```

### 社区支持

- **GitHub Issues**: https://github.com/nanfeng2021/fall-detection-system/issues
- **讨论区**: https://github.com/nanfeng2021/fall-detection-system/discussions

---

## 🎯 最佳实践

### 安全建议

1. **使用防火墙**: 只开放必要端口
2. **配置 HTTPS**: 使用 Let's Encrypt 免费证书
3. **定期更新**: 保持系统和依赖最新
4. **限制访问**: 使用 IP 白名单或 VPN
5. **监控日志**: 定期检查异常访问

### 性能优化

1. **使用 SSD**: 提高数据读写速度
2. **增加内存**: 建议 4GB+
3. **CPU 核心**: 建议 2 核+
4. **网络带宽**: 确保足够带宽
5. **定期清理**: 删除旧日志和数据集

### 运维建议

1. **设置监控**: 使用监控脚本或 Prometheus
2. **配置告警**: 邮件或短信通知
3. **定期备份**: 每天备份重要数据
4. **文档记录**: 记录所有配置变更
5. **测试演练**: 定期测试灾难恢复

---

*最后更新：2026-04-12*  
*版本：v1.0*  
*维护者：旺财团队*
