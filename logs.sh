#!/bin/bash

# 远程容器日志查看工具

REMOTE_HOST="-i ~/tools/pem/ty_sg01.pem root@129.226.88.226"
CONTAINER_NAME="invoice-extractor-container"

show_help() {
    echo "🔍 Docker容器日志查看工具 (文件模式)"
    echo ""
    echo "用法: ./logs.sh [选项]"
    echo ""
    echo "📂 读取远程日志文件: /var/log/invoice-extractor.log"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -f, --follow   实时跟踪日志"
    echo "  -t, --tail N   显示最后N行日志 (默认: 50)"
    echo "  -s, --since T  显示从时间T开始的日志 (文件模式下暂不支持)"
    echo "  -e, --error    只显示错误日志"
    echo "  -g, --grep S   搜索包含字符串S的日志"
    echo "  --save         保存日志到本地文件"
    echo ""
    echo "示例:"
    echo "  ./logs.sh                    # 显示最后50行日志"
    echo "  ./logs.sh -f                 # 实时跟踪日志"
    echo "  ./logs.sh -t 100             # 显示最后100行"
    echo "  ./logs.sh -e                 # 只显示错误"
    echo "  ./logs.sh -g 'versions'      # 搜索包含'versions'的日志"
    echo "  ./logs.sh --save             # 保存日志到文件"
    echo ""
    echo "注意: 文件模式下日志无Docker时间戳前缀，显示原始应用输出"
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

# 检查日志文件是否存在
LOG_FILE="/var/log/invoice-extractor.log"
if ! ssh $REMOTE_HOST "test -f $LOG_FILE"; then
    echo "❌ 日志文件 '$LOG_FILE' 不存在"
    echo "📋 检查容器是否运行:"
    ssh $REMOTE_HOST "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep $CONTAINER_NAME || echo '容器未运行'"
    exit 1
fi

# 构建文件读取命令
if [ "$FOLLOW" = true ]; then
    CMD="tail -f $LOG_FILE"
elif [ -n "$SINCE" ]; then
    # since参数对文件操作较复杂，使用find + tail组合
    echo "⚠️ --since 参数在文件模式下暂不支持，显示最后 $TAIL_LINES 行"
    CMD="tail -$TAIL_LINES $LOG_FILE"
else
    CMD="tail -$TAIL_LINES $LOG_FILE"
fi

# 添加过滤
if [ "$ERROR_ONLY" = true ]; then
    CMD="$CMD 2>&1 | grep -i -E 'error|exception|traceback|failed'"
elif [ -n "$GREP_PATTERN" ]; then
    CMD="$CMD 2>&1 | grep -i '$GREP_PATTERN'"
fi

echo "🔍 查看容器日志: $CONTAINER_NAME (文件模式)"
echo "📂 日志文件: $LOG_FILE"
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