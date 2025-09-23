#!/bin/bash

# 远程容器日志查看工具

REMOTE_HOST="root@129.226.88.226"
CONTAINER_NAME="invoice-extractor-container"

show_help() {
    echo "🔍 Docker容器日志查看工具"
    echo ""
    echo "用法: ./logs.sh [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -f, --follow   实时跟踪日志"
    echo "  -t, --tail N   显示最后N行日志 (默认: 50)"
    echo "  -s, --since T  显示从时间T开始的日志 (如: 10m, 1h, 2d)"
    echo "  -e, --error    只显示错误日志"
    echo "  -g, --grep S   搜索包含字符串S的日志"
    echo "  --save         保存日志到本地文件"
    echo ""
    echo "示例:"
    echo "  ./logs.sh                    # 显示最后50行日志"
    echo "  ./logs.sh -f                 # 实时跟踪日志"
    echo "  ./logs.sh -t 100             # 显示最后100行"
    echo "  ./logs.sh -s 30m             # 显示最近30分钟的日志"
    echo "  ./logs.sh -e                 # 只显示错误"
    echo "  ./logs.sh -g 'versions'      # 搜索包含'versions'的日志"
    echo "  ./logs.sh --save             # 保存日志到文件"
}

# 默认参数
TAIL_LINES=50
FOLLOW=false
SINCE=""
ERROR_ONLY=false
GREP_PATTERN=""
SAVE_TO_FILE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -s|--since)
            SINCE="$2"
            shift 2
            ;;
        -e|--error)
            ERROR_ONLY=true
            shift
            ;;
        -g|--grep)
            GREP_PATTERN="$2"
            shift 2
            ;;
        --save)
            SAVE_TO_FILE=true
            shift
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 -h 查看帮助"
            exit 1
            ;;
    esac
done

# 检查容器是否存在
if ! ssh $REMOTE_HOST "docker ps -a --format '{{.Names}}' | grep -q '^${CONTAINER_NAME}$'"; then
    echo "❌ 容器 '$CONTAINER_NAME' 不存在"
    echo "📋 可用容器:"
    ssh $REMOTE_HOST "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
    exit 1
fi

# 构建docker logs命令
CMD="docker logs"

if [ "$FOLLOW" = true ]; then
    CMD="$CMD -f"
fi

if [ -n "$SINCE" ]; then
    CMD="$CMD --since $SINCE"
fi

if [ "$TAIL_LINES" != "50" ] || [ "$FOLLOW" = false ]; then
    CMD="$CMD --tail $TAIL_LINES"
fi

CMD="$CMD -t $CONTAINER_NAME"

# 添加过滤
if [ "$ERROR_ONLY" = true ]; then
    CMD="$CMD 2>&1 | grep -i -E 'error|exception|traceback|failed'"
elif [ -n "$GREP_PATTERN" ]; then
    CMD="$CMD 2>&1 | grep -i '$GREP_PATTERN'"
fi

echo "🔍 查看容器日志: $CONTAINER_NAME"
echo "📡 执行命令: ssh $REMOTE_HOST \"$CMD\""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$SAVE_TO_FILE" = true ]; then
    LOGFILE="container_logs_$(date +%Y%m%d_%H%M%S).log"
    echo "💾 保存日志到文件: $LOGFILE"
    ssh $REMOTE_HOST "$CMD" > "$LOGFILE" 2>&1
    echo "✅ 日志已保存到: $LOGFILE"
else
    # 执行命令
    ssh $REMOTE_HOST "$CMD"
fi