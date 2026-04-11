#!/bin/bash
# 摔倒检测系统 - 一键部署脚本
# 使用方式：./deploy.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否以 root 运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 sudo 运行此脚本"
        exit 1
    fi
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_warning "Docker 未安装，正在安装..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        log_success "Docker 安装完成"
    else
        log_success "Docker 已安装：$(docker --version)"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose 未安装，正在安装..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose 安装完成"
    else
        log_success "Docker Compose 已安装：$(docker-compose --version)"
    fi
}

# 停止现有服务
stop_services() {
    log_info "停止现有服务..."
    docker-compose down || true
    pkill -f "streamlit run" || true
    log_success "服务已停止"
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    docker-compose build --no-cache
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose up -d
    sleep 5
    log_success "服务已启动"
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    docker-compose ps
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    for i in {1..30}; do
        if curl -s http://localhost:8501 > /dev/null 2>&1; then
            log_success "服务已就绪！"
            return 0
        fi
        sleep 2
    done
    
    log_error "服务启动超时，请检查日志"
    docker-compose logs fall-detection
    return 1
}

# 显示访问信息
show_access_info() {
    echo ""
    echo "======================================"
    echo "🎉 部署完成！"
    echo "======================================"
    echo ""
    echo "📍 访问地址:"
    echo "   本地：http://localhost:8501"
    
    # 获取服务器 IP
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    if [ -n "$SERVER_IP" ]; then
        echo "   远程：http://$SERVER_IP:8501"
    fi
    
    echo ""
    echo "📊 管理命令:"
    echo "   查看状态：docker-compose ps"
    echo "   查看日志：docker-compose logs -f"
    echo "   重启服务：docker-compose restart"
    echo "   停止服务：docker-compose down"
    echo "   更新部署：./deploy.sh update"
    echo ""
    echo "======================================"
}

# 主部署流程
main_deploy() {
    echo "======================================"
    echo "🚀 摔倒检测系统 - 一键部署"
    echo "======================================"
    echo ""
    
    check_root
    check_docker
    stop_services
    build_images
    start_services
    check_status
    show_access_info
}

# 更新部署
update_deploy() {
    log_info "执行更新部署..."
    stop_services
    docker-compose pull
    build_images
    start_services
    check_status
    log_success "更新完成！"
}

# 仅启动服务
start_only() {
    log_info "启动服务..."
    docker-compose up -d
    check_status
    show_access_info
}

# 仅停止服务
stop_only() {
    log_info "停止服务..."
    stop_services
    log_success "服务已停止"
}

# 查看日志
view_logs() {
    docker-compose logs -f "${1:-}"
}

# 清理资源
cleanup() {
    log_warning "此操作将删除所有容器、镜像和数据卷！"
    read -p "确认继续？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker-compose down -v --rmi all
        log_success "清理完成"
    else
        log_info "已取消"
    fi
}

# 显示帮助
show_help() {
    echo "用法：$0 [command]"
    echo ""
    echo "命令:"
    echo "  deploy    完整部署（默认）"
    echo "  update    更新部署"
    echo "  start     仅启动服务"
    echo "  stop      仅停止服务"
    echo "  logs      查看日志"
    echo "  status    查看状态"
    echo "  cleanup   清理资源"
    echo "  help      显示帮助"
    echo ""
    echo "示例:"
    echo "  $0              # 完整部署"
    echo "  $0 update       # 更新部署"
    echo "  $0 logs         # 查看日志"
    echo "  $0 cleanup      # 清理资源"
}

# 主程序
case "${1:-deploy}" in
    deploy)
        main_deploy
        ;;
    update)
        update_deploy
        ;;
    start)
        start_only
        ;;
    stop)
        stop_only
        ;;
    logs)
        view_logs "$2"
        ;;
    status)
        docker-compose ps
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "未知命令：$1"
        show_help
        exit 1
        ;;
esac
