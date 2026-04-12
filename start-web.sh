#!/bin/bash
# 摔倒检测系统 - Web UI 启动脚本

cd /root/.openclaw/workspace/projects/fall-detection-system

echo "======================================"
echo "🚨 摔倒检测系统 - Web 界面"
echo "======================================"
echo ""
echo "正在启动 Streamlit..."
echo ""
echo "访问地址："
echo "  本地：http://localhost:8501"
echo "  远程：http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "按 Ctrl+C 停止服务"
echo "======================================"
echo ""

source venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
