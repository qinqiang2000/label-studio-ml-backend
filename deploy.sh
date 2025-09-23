#!/bin/bash

# 自动化部署脚本 - Label Studio ML Backend
# 每次代码变更后使用此脚本push并在目标机器上运行最新代码

set -e  # 遇到错误时退出

# 配置变量
REMOTE_HOST="root@129.226.88.226"
REMOTE_PATH="/root/qqin/label-studio-ml-backend"
DOCKER_IMAGE="invoice-extractor:latest"
CONTAINER_NAME="invoice-extractor-container"
HOST_PORT="9091"
CONTAINER_PORT="9090"
BRANCH="company-custom"

echo "🚀 开始自动化部署流程..."

# ========================= SSH 认证与登录说明 =========================
# 本脚本默认直接使用 "ssh $REMOTE_HOST" 进行连接，不显式指定私钥（如 -i）。
# 之所以无需输入密码，是因为本机已配置了可用的 SSH Key，且远端服务器的
#   /root/.ssh/authorized_keys 中已存在对应的公钥，或已通过 ssh-agent/Keychain 缓存。
#
# 在其他机器上维护或运行本脚本时，如果无法无密码登录，请按以下方式处理：
# 1) 推荐方式：将该机器的 SSH 公钥追加到目标机器 root 用户的 authorized_keys 中。
#    - 本机生成/查看公钥：cat ~/.ssh/id_rsa.pub（或 id_ed25519.pub）
#    - 将公钥内容追加到目标机：/root/.ssh/authorized_keys（需具备相应权限）
#
# 2) 使用私钥文件直接登录（历史初次登录方式如下）：
#    原始命令示例：ssh -i ~/tools/pem/ty_sg01.pem root@129.226.88.226
#    - 若临时验证连通性，可直接用上面的命令登录。
#    - 若希望脚本也显式使用该私钥，可临时将 REMOTE_HOST 改为：
#        REMOTE_HOST="-i ~/tools/pem/ty_sg01.pem root@129.226.88.226"
#      然后脚本中的 "ssh $REMOTE_HOST" 会携带 -i 选项（仅临时方案，不建议长期这样写）。
#
# 3) 更优雅的方式：配置 ~/.ssh/config，便于免密与固定私钥登录，例如：
#      Host ls-ml-backend
#        HostName 129.226.88.226
#        User root
#        IdentityFile ~/tools/pem/ty_sg01.pem
#    配置完成后，可将上方 REMOTE_HOST 设置为：REMOTE_HOST="ls-ml-backend"
#    这样脚本依然使用 "ssh $REMOTE_HOST"，但会自动读取该主机配置与私钥。
# ====================================================================

# 1. 检查是否有未提交的更改
echo "📋 检查本地代码状态..."
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 发现未提交的更改，正在提交..."
    git add .
    read -p "请输入提交信息: " commit_message
    if [[ -z "$commit_message" ]]; then
        commit_message="Auto deploy: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    git commit -m "$commit_message

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
else
    echo "✅ 没有未提交的更改"
fi

# 2. 推送到远程仓库
echo "📤 推送代码到远程仓库..."
git push origin $BRANCH

# 3. 在目标机器上停止现有服务
echo "🔴 停止目标机器上的现有容器和进程..."
# 停止Docker容器（如果存在）
echo "  🔍 检查并停止Docker容器..."
ssh $REMOTE_HOST "docker stop $CONTAINER_NAME 2>/dev/null && echo '  ✅ 容器已停止' || echo '  ℹ️ 没有运行中的容器'"

# 由于使用--rm，容器会自动删除，无需手动rm
# 额外清理：杀死可能残留的nohup进程（简化版）
echo "  🔍 清理相关进程..."
echo "  ℹ️ 跳过进程清理（Docker stop已足够）"

# 清理可能的旧日志文件锁
echo "  🔍 清理日志文件锁..."
ssh $REMOTE_HOST "rm -f /var/log/invoice-extractor.log.lock 2>/dev/null && echo '  ✅ 日志锁已清理' || echo '  ℹ️ 没有日志锁文件'"

# 4. 安全更新代码（增量更新，不删除）
echo "🔄 安全更新代码..."
ssh $REMOTE_HOST "cd $REMOTE_PATH && git fetch origin $BRANCH"

# 检查是否有本地修改
if ssh $REMOTE_HOST "cd $REMOTE_PATH && git status --porcelain" | grep -q .; then
    echo "⚠️ 发现本地修改，创建备份分支..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    ssh $REMOTE_HOST "cd $REMOTE_PATH && git add . && git commit -m 'Auto backup before deploy $timestamp' || true"
    ssh $REMOTE_HOST "cd $REMOTE_PATH && git checkout -b backup_$timestamp || true"
fi

# 切换到目标分支并更新
echo "📥 更新到最新代码..."
ssh $REMOTE_HOST "cd $REMOTE_PATH && git checkout $BRANCH && git reset --hard origin/$BRANCH"

# 5. 验证关键文件存在
echo "🔍 验证关键文件..."
if ! ssh $REMOTE_HOST "test -f $REMOTE_PATH/invoice_extractor/.env"; then
    echo "⚠️ .env文件缺失，从模板创建..."
    exit 1
fi

# 6. 构建新的Docker镜像
echo "🔨 构建新的Docker镜像..."
ssh $REMOTE_HOST "cd $REMOTE_PATH/invoice_extractor && docker build -t $DOCKER_IMAGE ."

# 7. 运行新容器
echo "🚀 启动新的Docker容器..."
ssh $REMOTE_HOST "cd $REMOTE_PATH/invoice_extractor && nohup docker run --rm --name $CONTAINER_NAME -p $HOST_PORT:$CONTAINER_PORT --env-file .env $DOCKER_IMAGE > /var/log/invoice-extractor.log 2>&1 &"

# 验证容器启动
echo "🔍 验证容器启动..."
sleep 3
startup_success=false
for i in {1..5}; do
    if ssh $REMOTE_HOST "docker ps --format '{{.Names}}' | grep -q '^${CONTAINER_NAME}$'"; then
        echo "  ✅ 容器启动成功 (尝试 $i/5)"
        startup_success=true
        break
    else
        echo "  ⏳ 等待容器启动... (尝试 $i/5)"
        sleep 2
    fi
done

if [ "$startup_success" = false ]; then
    echo "  ❌ 容器启动失败，检查日志："
    ssh $REMOTE_HOST "tail -10 /var/log/invoice-extractor.log 2>/dev/null || echo '日志文件不存在'"
    exit 1
fi

# 8. 等待服务完全就绪
echo "⏳ 等待服务完全就绪..."
sleep 7

echo "🔍 开始自动化测试..."

# 测试函数
test_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local expected_status=${3:-200}
    local description=$4

    echo "  📡 测试 $method $endpoint - $description"

    if [ "$method" = "GET" ]; then
        response=$(ssh $REMOTE_HOST "curl -s -w '%{http_code}' http://localhost:$HOST_PORT$endpoint")
    else
        response=$(ssh $REMOTE_HOST "curl -s -w '%{http_code}' -X $method -H 'Content-Type: application/json' -d '{}' http://localhost:$HOST_PORT$endpoint")
    fi

    http_code="${response: -3}"
    content="${response%???}"

    if [ "$http_code" = "$expected_status" ]; then
        echo "  ✅ $endpoint 测试通过 (HTTP $http_code)"
        return 0
    else
        echo "  ❌ $endpoint 测试失败 (HTTP $http_code, 期望 $expected_status)"
        echo "     响应内容: $content"
        return 1
    fi
}

# 基础连通性测试
echo "🌐 1. 基础连通性测试"
test_failed=0

test_endpoint "/health" "GET" "200" "基础健康检查" || test_failed=1
test_endpoint "/versions" "GET" "200" "版本信息端点" || test_failed=1

# 标准端点测试
echo "🔧 2. 标准端点测试"
test_endpoint "/setup" "POST" "500" "模型设置端点（预期需要参数）" || test_failed=1
test_endpoint "/metrics" "GET" "200" "系统指标端点" || test_failed=1

# 自定义端点测试
echo "🚀 3. 自定义端点测试"
test_endpoint "/model/info" "GET" "200" "模型信息端点" || test_failed=1
test_endpoint "/health/detailed" "GET" "200" "详细健康检查端点" || test_failed=1

# 验证 /versions 端点返回数据
echo "📊 4. 数据完整性测试"
echo "  🔍 验证 /versions 端点数据..."
versions_response=$(ssh $REMOTE_HOST "curl -s http://localhost:$HOST_PORT/versions")
if echo "$versions_response" | grep -q "versions" && echo "$versions_response" | grep -q "current_version"; then
    echo "  ✅ /versions 端点返回正确的数据结构"
    # 显示当前版本信息
    current_version=$(echo "$versions_response" | grep -o '"current_version":{[^}]*}' | head -1)
    echo "  📋 当前版本: $current_version"
else
    echo "  ❌ /versions 端点数据结构异常"
    echo "     响应: $versions_response"
    test_failed=1
fi

# 容器健康检查
echo "🐳 5. 容器状态检查"
container_status=$(ssh $REMOTE_HOST "docker inspect --format='{{.State.Status}}' $CONTAINER_NAME 2>/dev/null || echo 'not_found'")
if [ "$container_status" = "running" ]; then
    echo "  ✅ Docker容器运行状态正常"
elif [ "$container_status" = "not_found" ]; then
    echo "  ⚠️ 容器使用--rm模式，检查进程是否运行..."
    # 检查Docker进程和端口监听
    if ssh $REMOTE_HOST "pgrep -f 'docker.*$CONTAINER_NAME' >/dev/null 2>&1"; then
        echo "  ✅ 容器进程运行正常"
    elif ssh $REMOTE_HOST "netstat -tlnp | grep :$HOST_PORT" >/dev/null 2>&1; then
        echo "  ✅ 服务端口正在监听（容器可能已启动）"
    else
        echo "  ❌ 容器进程和端口都未找到"
        test_failed=1
    fi
else
    echo "  ❌ Docker容器状态异常: $container_status"
    test_failed=1
fi

# 端口监听检查
echo "🔌 6. 端口监听检查"
if ssh $REMOTE_HOST "netstat -tlnp | grep :$HOST_PORT" >/dev/null 2>&1; then
    echo "  ✅ 端口 $HOST_PORT 正在被监听"
else
    echo "  ❌ 端口 $HOST_PORT 未被监听"
    test_failed=1
fi

# 性能基准测试
echo "⚡ 7. 基础性能测试"
echo "  ⏱️  测试响应时间..."
response_time=$(ssh $REMOTE_HOST "time curl -s http://localhost:$HOST_PORT/health >/dev/null" 2>&1 | grep real | awk '{print $2}')
echo "  📊 /health 端点响应时间: $response_time"

# 最终结果
echo ""
echo "📋 测试摘要:"
if [ $test_failed -eq 0 ]; then
    echo "✅ 🎉 所有测试通过！部署成功！"
    echo "🔗 服务地址: http://$REMOTE_HOST:$HOST_PORT"
    echo "📝 可用端点:"
    echo "   标准: /health, /setup, /predict, /train, /metrics"
    echo "   自定义: /versions, /model/info, /health/detailed"

    # 显示容器日志的最后几行
    echo ""
    echo "📋 最新容器日志："
    ssh $REMOTE_HOST "tail -5 /var/log/invoice-extractor.log 2>/dev/null || echo '日志文件暂不可用'"
else
    echo "❌ 部署测试失败！发现 $test_failed 个问题"
    echo "📋 完整容器日志："
    ssh $REMOTE_HOST "cat /var/log/invoice-extractor.log 2>/dev/null || echo '日志文件不存在'"
    exit 1
fi
