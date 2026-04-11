#!/bin/bash
# 摔倒检测系统 - 监控脚本
# 使用方式：./monitor.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# 检查服务状态
check_service_status() {
    log_info "检查服务状态..."
    
    # Docker 容器状态
    if docker-compose ps | grep -q "Up"; then
        log_success "Docker 容器运行正常"
    else
        log_error "Docker 容器未运行"
        return 1
    fi
    
    # HTTP 健康检查
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 | grep -q "200"; then
        log_success "HTTP 服务响应正常"
    else
        log_error "HTTP 服务无响应"
        return 1
    fi
    
    return 0
}

# 检查资源使用
check_resources() {
    log_info "检查资源使用..."
    
    # CPU 使用率
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$CPU_USAGE < 80" | bc -l) )); then
        log_success "CPU 使用率：${CPU_USAGE}%"
    else
        log_error "CPU 使用率过高：${CPU_USAGE}%"
    fi
    
    # 内存使用率
    MEM_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
    if (( $(echo "$MEM_USAGE < 80" | bc -l) )); then
        log_success "内存使用率：${MEM_USAGE}%"
    else
        log_error "内存使用率过高：${MEM_USAGE}%"
    fi
    
    # 磁盘使用率
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    if [ "$DISK_USAGE" -lt 80 ]; then
        log_success "磁盘使用率：${DISK_USAGE}%"
    else
        log_error "磁盘使用率过高：${DISK_USAGE}%"
    fi
}

# 查看实时日志
view_logs() {
    docker-compose logs -f "${1:-fall-detection}"
}

# 显示统计信息
show_stats() {
    echo ""
    echo "======================================"
    echo "📊 系统统计信息"
    echo "======================================"
    
    # 运行时间
    UPTIME=$(docker inspect --format='{{.State.StartedAt}}' fall-detection-system 2>/dev/null || echo "未知")
    echo "启动时间：$UPTIME"
    
    # 重启次数
    RESTARTS=$(docker inspect --format='{{.RestartCount}}' fall-detection-system 2>/dev/null || echo "0")
    echo "重启次数：$RESTARTS"
    
    # 网络统计
    echo ""
    echo "网络统计:"
    docker exec fall-detection-system netstat -tlnp 2>/dev/null | grep 8501 || echo "无法获取"
    
    # 进程信息
    echo ""
    echo "进程信息:"
    docker exec fall-detection-system ps aux | grep streamlit | grep -v grep || echo "无法获取"
    
    echo ""
    echo "======================================"
}

# 自动重启服务
auto_restart() {
    log_info "尝试自动重启服务..."
    docker-compose restart
    sleep 10
    
    if check_service_status; then
        log_success "服务已成功重启"
        return 0
    else
        log_error "服务重启失败"
        return 1
    fi
}

# 主监控循环
monitor_loop() {
    log_info "启动监控循环（Ctrl+C 停止）..."
    
    while true; do
        echo ""
        echo "======================================"
        log_info "监控检查 - $(date '+%Y-%m-%d %H:%M:%S')"
        
        if ! check_service_status; then
            log_warning "服务异常，尝试自动重启..."
            auto_restart
        fi
        
        check_resources
        show_stats
        
        sleep 60
    done
}

# 主程序
case "${1:-status}" in
    status)
        check_service_status
        check_resources
        ;;
    logs)
        view_logs "$2"
        ;;
    stats)
        show_stats
        ;;
    monitor)
        monitor_loop
        ;;
    restart)
        auto_restart
        ;;
    help|--help|-h)
        echo "用法：$0 [command]"
        echo ""
        echo "命令:"
        echo "  status   检查服务状态（默认）"
        echo "  logs     查看日志"
        echo "  stats    显示统计信息"
        echo "  monitor  持续监控"
        echo "  restart  重启服务"
        echo ""
        ;;
    *)
        echo "未知命令：$1"
        echo "使用 '$0 help' 查看帮助"
        exit 1
        ;;
esac
