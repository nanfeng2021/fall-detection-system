# 🌐 摔倒检测系统 - 部署与访问指南

## ✅ 当前状态

**服务已启动！** 🎉

- **状态**: ✅ 运行中
- **端口**: 8501
- **访问地址**: http://0.0.0.0:8501
- **模式**: 对外开放（所有 IP 可访问）

---

## 🔗 访问方式

### 方式 1: 本地访问
```
http://localhost:8501
```

### 方式 2: 服务器 IP 访问
```
http://<服务器IP>:8501
```

**查看服务器 IP**:
```bash
curl ifconfig.me
# 或
hostname -I
```

### 方式 3: 域名访问（需要配置 DNS）

#### 步骤 1: 域名解析设置

登录你的域名提供商（如阿里云、腾讯云、Cloudflare），添加 DNS 记录：

**A 记录**:
```
主机记录：@ 或 www
记录类型：A
记录值：<你的服务器公网 IP>
TTL: 600
```

**示例配置**（以阿里云为例）:
```
主机记录：ainanfeng.cn
记录类型：A
记录值：123.45.67.89  (替换为你的实际 IP)
```

#### 步骤 2: 等待 DNS 生效
- 通常 5-10 分钟生效
- 最长可能需要 24 小时
- 使用以下命令检查：

```bash
ping ainfanfeng.cn
# 或
dig ainfanfeng.cn
```

#### 步骤 3: 访问域名
```
http://ainanfeng.cn:8501
```

---

## 🔒 安全建议

### ⚠️ 当前配置风险

**当前服务对所有 IP 开放**，存在以下风险：
- 任何人都可以访问你的 Web 界面
- 可能泄露检测数据
- 可能被恶意利用

### 推荐安全措施

#### 方案 1: 防火墙限制（推荐）

安装并配置 UFW 防火墙：

```bash
# 安装 UFW
apt-get install ufw -y

# 允许 SSH（防止被锁在外面）
ufw allow 22/tcp

# 只允许特定 IP 访问 8501（替换为你的可信 IP）
ufw allow from 192.168.1.0/24 to any port 8501
# 或只允许单个 IP
ufw allow from 123.45.67.89 to any port 8501

# 启用防火墙
ufw enable

# 查看状态
ufw status
```

#### 方案 2: Nginx 反向代理 + HTTPS（最佳实践）

1. **安装 Nginx**:
```bash
apt-get install nginx -y
```

2. **配置 Nginx** (`/etc/nginx/sites-available/fall-detection`):
```nginx
server {
    listen 80;
    server_name ainfanfeng.cn;
    
    # 重定向到 HTTPS（可选，需要有 SSL 证书）
    # return 301 https://$server_name$request_uri;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（Streamlit 需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

3. **启用配置**:
```bash
ln -s /etc/nginx/sites-available/fall-detection /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

4. **配置 SSL 证书**（推荐 Let's Encrypt）:
```bash
apt-get install certbot python3-certbot-nginx -y
certbot --nginx -d ainfanfeng.cn
```

#### 方案 3: Streamlit 内置密码保护

创建 `.streamlit/secrets.toml`:
```toml
[general]
password = "your_password_here"

[browser]
gatherUsageStats = false
```

生成密码哈希：
```python
import streamlit as st
hashed = st.hash_password("your_password_here")
print(hashed)
```

---

## 🔧 服务管理

### 手动管理

**启动服务**:
```bash
cd /root/.openclaw/workspace/projects/fall-detection-system
source venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

**停止服务**:
```bash
pkill -f "streamlit run app.py"
```

**查看日志**:
```bash
ps aux | grep streamlit
tail -f /tmp/fall_detection.log
```

### Systemd 管理（推荐）

**安装服务**:
```bash
cp fall-detection.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable fall-detection
systemctl start fall-detection
```

**服务控制**:
```bash
# 查看状态
systemctl status fall-detection

# 启动
systemctl start fall-detection

# 停止
systemctl stop fall-detection

# 重启
systemctl restart fall-detection

# 开机自启
systemctl enable fall-detection

# 禁用开机自启
systemctl disable fall-detection
```

**查看日志**:
```bash
journalctl -u fall-detection -f
```

---

## 📊 性能监控

### 查看资源占用
```bash
# CPU 和内存
top -p $(pgrep -f "streamlit run")

# 或使用 htop
htop -p $(pgrep -f "streamlit run")
```

### 查看网络连接
```bash
# 查看连接到 8501 的客户端
netstat -anp | grep 8501

# 或使用 ss
ss -tnp | grep 8501
```

### 查看进程信息
```bash
ps aux | grep streamlit
```

---

## 🐛 故障排查

### 问题 1: 无法访问

**检查服务状态**:
```bash
systemctl status fall-detection
# 或
ps aux | grep streamlit
```

**检查端口监听**:
```bash
ss -tlnp | grep 8501
```

**检查防火墙**:
```bash
ufw status
# 或
iptables -L -n | grep 8501
```

**检查日志**:
```bash
journalctl -u fall-detection -f
# 或
tail -f /tmp/fall_detection.log
```

### 问题 2: 域名无法访问

**检查 DNS 解析**:
```bash
ping ainfanfeng.cn
dig ainfanfeng.cn
nslookup ainfanfeng.cn
```

**检查域名是否正确配置**:
- 登录域名提供商控制台
- 确认 A 记录指向正确的 IP
- 等待 DNS 生效（最多 24 小时）

**检查端口是否开放**:
```bash
telnet ainfanfeng.cn 8501
# 或
nc -zv ainfanfeng.cn 8501
```

### 问题 3: 服务频繁崩溃

**查看崩溃日志**:
```bash
journalctl -u fall-detection -f
```

**常见原因**:
- 内存不足 → 增加服务器内存
- 依赖缺失 → `pip install -r requirements.txt`
- 端口冲突 → 更换端口

**增加内存**（如果 swap 不足）:
```bash
# 创建 2GB swap
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

---

## 📝 配置修改

### 修改端口

编辑 systemd 服务文件：
```bash
nano /etc/systemd/system/fall-detection.service
```

修改端口号：
```ini
ExecStart=/root/.openclaw/workspace/projects/fall-detection-system/venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8502 --server.headless true
```

重新加载：
```bash
systemctl daemon-reload
systemctl restart fall-detection
```

### 限制访问 IP

编辑 Streamlit 配置文件 `~/.streamlit/config.toml`:
```toml
[server]
headless = true
port = 8501
address = "127.0.0.1"  # 只允许本地访问
enableCORS = false
enableXsrfProtection = true
```

然后通过 Nginx 反向代理对外提供服务。

---

## 🎯 快速检查清单

- [ ] 服务已启动：`systemctl status fall-detection`
- [ ] 端口已监听：`ss -tlnp | grep 8501`
- [ ] 防火墙已配置：`ufw status`
- [ ] DNS 已解析：`ping ainfanfeng.cn`
- [ ] 可以本地访问：`curl http://localhost:8501`
- [ ] 可以远程访问：浏览器访问 `http://<IP>:8501`
- [ ] 域名可访问：浏览器访问 `http://ainfanfeng.cn:8501`
- [ ] 已配置开机自启：`systemctl is-enabled fall-detection`

---

## 📞 技术支持

遇到问题？

1. 查看本指南
2. 检查系统日志
3. 联系开发者

**GitHub**: https://github.com/nanfeng2021/fall-detection-system

---

*最后更新：2026-04-12*
*服务状态：✅ 运行中 - 端口 8501 - 对外开放*
