#!/bin/bash
# 摔倒检测系统 - 一键启动脚本

echo "🚀 摔倒检测系统 - 启动向导"
echo "======================================"

# 检查 Python 版本
echo ""
echo "1️⃣  检查 Python 环境..."
python_version=$(python3 --version 2>&1)
if [ $? -eq 0 ]; then
    echo "✅ $python_version"
else
    echo "❌ Python3 未安装，请先安装 Python 3.10+"
    exit 1
fi

# 检查虚拟环境
echo ""
echo "2️⃣  检查虚拟环境..."
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
echo ""
echo "3️⃣  激活虚拟环境..."
source venv/bin/activate
echo "✅ 虚拟环境已激活"

# 安装依赖
echo ""
echo "4️⃣  安装依赖..."
if [ -f "requirements.txt" ]; then
    echo "📥 正在安装依赖包..."
    pip install -r requirements.txt -q
    echo "✅ 依赖安装完成"
else
    echo "❌ requirements.txt 不存在"
    exit 1
fi

# 选择运行模式
echo ""
echo "5️⃣  选择运行模式:"
echo ""
echo "  1) 🎨 Web 界面 (Streamlit)"
echo "  2) 🧪 命令行 Demo (模拟数据)"
echo "  3) 📷 实时检测 (需要 Azure Kinect)"
echo "  4) 📼 数据录制"
echo "  5) ❌ 退出"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🎨 启动 Web 界面..."
        echo "浏览器将自动打开 http://localhost:8501"
        echo ""
        echo "按 Ctrl+C 停止"
        echo ""
        streamlit run app.py
        ;;
    2)
        echo ""
        echo "🧪 启动命令行 Demo (模拟数据)..."
        echo ""
        python demos/fall_detection_demo.py --mock
        ;;
    3)
        echo ""
        echo "📷 启动实时检测..."
        echo "⚠️  需要连接 Azure Kinect 相机"
        echo ""
        python demos/fall_detection_demo.py --camera
        ;;
    4)
        echo ""
        read -p "输入录制时长 (秒，默认 30): " duration
        duration=${duration:-30}
        
        read -p "输入输出目录 (默认 ./dataset): " output
        output=${output:-./dataset}
        
        echo ""
        echo "📼 开始录制..."
        echo "时长：${duration}秒"
        echo "输出：${output}"
        echo ""
        python demos/fall_detection_demo.py --record --output "$output" --duration "$duration"
        ;;
    5)
        echo ""
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ 无效选项"
        exit 1
        ;;
esac
