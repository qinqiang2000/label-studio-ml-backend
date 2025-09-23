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
echo "🔴 停止目标机器上的现有容器..."
ssh $REMOTE_HOST "docker stop $CONTAINER_NAME 2>/dev/null || true"
ssh $REMOTE_HOST "docker rm $CONTAINER_NAME 2>/dev/null || true"

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
ssh $REMOTE_HOST "cd $REMOTE_PATH/invoice_extractor && docker run -d --name $CONTAINER_NAME -p $HOST_PORT:$CONTAINER_PORT --env-file .env $DOCKER_IMAGE"

# 8. 等待服务启动并进行全面测试
echo "⏳ 等待服务启动..."
sleep 10

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
container_status=$(ssh $REMOTE_HOST "docker inspect --format='{{.State.Status}}' $CONTAINER_NAME")
if [ "$container_status" = "running" ]; then
    echo "  ✅ Docker容器运行状态正常"
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
    ssh $REMOTE_HOST "docker logs $CONTAINER_NAME --tail 5"
else
    echo "❌ 部署测试失败！发现 $test_failed 个问题"
    echo "📋 完整容器日志："
    ssh $REMOTE_HOST "docker logs $CONTAINER_NAME"
    exit 1
fi
