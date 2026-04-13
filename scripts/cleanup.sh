#!/bin/bash
# 摔倒检测系统 - 定期清理脚本
# 用法：./scripts/cleanup.sh [days_to_keep]

set -e

DAYS_TO_KEEP=${1:-7}
PROJECT_DIR="/root/.openclaw/workspace/projects/fall-detection-system"

echo "======================================"
echo "  摔倒检测系统 - 磁盘清理脚本"
echo "======================================"
echo ""
echo "保留策略：${DAYS_TO_KEEP} 天"
echo "执行时间：$(date)"
echo ""

cd "$PROJECT_DIR"

# 1. 清理旧录像
echo "📹 清理 ${DAYS_TO_KEEP} 天前的录像文件..."
if [ -d "recordings" ]; then
    find recordings -name "*.mp4" -type f -mtime +${DAYS_TO_KEEP} -delete -print
    echo "   ✅ 录像清理完成"
else
    echo "   ℹ️  录像目录不存在"
fi
echo ""

# 2. 清理旧报表
echo "📊 清理 30 天前的分析报表..."
if [ -d "analytics_data" ]; then
    find analytics_data -name "report_*" -type f -mtime +30 -delete -print
    echo "   ✅ 报表清理完成"
else
    echo "   ℹ️  分析数据目录不存在"
fi
echo ""

# 3. 清理 Python 缓存
echo "🗑️ 清理 Python 缓存文件..."
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ 缓存清理完成"
echo ""

# 4. 清理临时文件
echo "🧹 清理临时文件..."
find . -path ./venv -prune -o \( -name "*.tmp" -o -name "*.pyc" -o -name "*.log" \) -type f -delete 2>/dev/null || true
echo "   ✅ 临时文件清理完成"
echo ""

# 5. 显示磁盘使用情况
echo "📊 当前磁盘使用情况:"
df -h "$PROJECT_DIR" | tail -1
echo ""

echo "======================================"
echo "  清理完成！✅"
echo "======================================"
