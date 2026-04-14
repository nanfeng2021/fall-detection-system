# GuardianFall 本地启动指南

## ✅ 环境准备完成

虚拟环境已创建，所有依赖已安装！

## 🚀 启动方式

### 方式一：使用启动脚本（推荐）

```bash
./start_local.sh
```

然后选择：
- `1` - 启动 Web 界面 (需要手动点击启动检测)
- `2` - 启动 Web 界面 (模拟数据版) ⭐ **推荐**
- `3` - 只启动 API 服务 (FastAPI)
- `4` - 同时启动 Web + API
- `5` - 运行命令行 Demo
- `6` - 运行测试

**推荐选择 `2` - 模拟数据版**，会自动生成测试数据，无需硬件设备！

### 方式二：手动启动

**1. 激活虚拟环境**
```bash
source venv/bin/activate
```

**2. 启动 Web 界面**
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
访问：http://localhost:8501

**3. 启动 API 服务（新开终端）**
```bash
source venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
访问：http://localhost:8000/docs

### 方式三：Docker 启动

```bash
docker-compose up -d
```

访问：
- Web 界面：http://localhost:8501
- API 文档：http://localhost:8000/docs

## 📁 项目结构

```
fall-detection-system/
├── app.py                 # Streamlit Web 界面
├── config.yaml           # 配置文件
├── start_local.sh        # 本地启动脚本 ⭐
├── venv/                 # 虚拟环境
├── src/
│   ├── api/             # FastAPI 接口
│   ├── detection/       # 检测模块
│   ├── preprocessing/   # 预处理模块
│   ├── utils/           # 工具模块
│   └── web/             # Web 组件
└── tests/               # 测试代码
```

## 🧪 运行测试

```bash
source venv/bin/activate
pytest tests/ -v
```

## 🔧 常用命令

```bash
# 激活虚拟环境
source venv/bin/activate

# 退出虚拟环境
deactivate

# 安装新依赖
pip install <package-name>

# 保存依赖到 requirements.txt
pip freeze > requirements.txt
```

## 🌐 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Web 界面 | http://localhost:8501 | Streamlit 可视化 |
| API 文档 | http://localhost:8000/docs | FastAPI Swagger |
| API 接口 | http://localhost:8000 | RESTful API |

## ⚠️ 注意事项

1. **Python 版本**：需要 Python 3.9+
2. **硬件要求**：
   - 最低：4GB RAM，2核 CPU
   - 推荐：8GB RAM，4核 CPU
3. **相机支持**（可选）：
   - Azure Kinect DK
   - 或使用模拟数据测试

## 🆘 常见问题

**Q: 端口被占用怎么办？**
```bash
# 查找占用 8501 端口的进程
lsof -i :8501
# 杀掉进程
kill -9 <PID>
```

**Q: 依赖安装失败？**
```bash
# 升级 pip
pip install --upgrade pip
# 重新安装
pip install -r requirements.txt
```

**Q: 如何重置环境？**
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📞 帮助

如有问题，请查看：
- 项目文档：`OPTIMIZATION_SUMMARY.md`
- API 文档：启动后访问 http://localhost:8000/docs
- 日志文件：`logs/` 目录
