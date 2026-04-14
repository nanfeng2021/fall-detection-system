#!/bin/bash
# GuardianFall 本地启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  GuardianFall 本地启动脚本${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate

# 检查依赖
if ! python -c "import streamlit" 2>/dev/null; then
    echo -e "${YELLOW}安装依赖...${NC}"
    pip install -r requirements.txt
fi

# 创建必要目录
mkdir -p logs data datasets

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}启动选项:${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "1) 启动 Web 界面 (Streamlit) - 需要手动启动检测"
echo "2) 启动 Web 界面 (模拟数据版) - 自动生成数据 ⭐推荐"
echo "3) 启动 API 服务 (FastAPI)"
echo "4) 同时启动 Web + API"
echo "5) 运行模拟数据 Demo (命令行)"
echo "6) 运行测试"
echo "7) 退出"
echo ""

read -p "请选择 [1-7]: " choice

case $choice in
    1)
        echo -e "${YELLOW}启动 Web 界面...${NC}"
        echo -e "${GREEN}访问地址: http://localhost:8501${NC}"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8501
        ;;
    2)
        echo -e "${YELLOW}启动 Web 界面 (模拟数据版)...${NC}"
        echo -e "${GREEN}访问地址: http://localhost:8501${NC}"
        echo -e "${BLUE}🎮 此模式自动生成模拟数据，无需硬件${NC}"
        streamlit run app_mock.py --server.address 0.0.0.0 --server.port 8501
        ;;
    3)
        echo -e "${YELLOW}启动 API 服务...${NC}"
        echo -e "${GREEN}API 文档: http://localhost:8000/docs${NC}"
        uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    4)
        echo -e "${YELLOW}启动 Web + API...${NC}"
        
        # 启动API（后台）
        uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &
        API_PID=$!
        echo -e "${GREEN}API 服务已启动 (PID: $API_PID)${NC}"
        echo -e "${GREEN}API 文档: http://localhost:8000/docs${NC}"
        
        # 等待API启动
        sleep 3
        
        # 启动Web
        echo -e "${GREEN}Web 界面: http://localhost:8501${NC}"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8501
        
        # 关闭API
        kill $API_PID 2>/dev/null || true
        ;;
    5)
        echo -e "${YELLOW}运行模拟数据 Demo...${NC}"
        python demos/fall_detection_demo.py --mock
        ;;
    6)
        echo -e "${YELLOW}运行测试...${NC}"
        pytest tests/ -v
        ;;
    7)
        echo "退出"
        exit 0
        ;;
    *)
        echo "无效选项，使用默认模式：启动 Web 界面"
        echo -e "${YELLOW}启动 Web 界面...${NC}"
        echo -e "${GREEN}访问地址: http://localhost:8501${NC}"
        streamlit run app.py --server.address 0.0.0.0 --server.port 8501
        ;;
esac
