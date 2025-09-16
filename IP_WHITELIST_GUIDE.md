# IP 白名单访问控制指引

本文档说明如何使用环境变量配置 IP 白名单来控制对 ML 后端服务的访问。

## 概述

IP 白名单功能通过环境变量提供简单而灵活的访问控制：
- **纯环境变量配置** - 无需修改配置文件，避免仓库冲突
- **本地地址默认放开** - 127.0.0.1, ::1, localhost 无需配置
- **开发友好** - 默认关闭白名单，不影响开发环境
- **生产就绪** - 支持单IP、网段、多IP配置

## 环境变量配置

### 基础配置

#### 1. 启用/禁用白名单
```bash
export IP_WHITELIST_ENABLED=true    # 启用白名单
export IP_WHITELIST_ENABLED=false   # 禁用白名单（默认）
```

#### 2. 配置允许的 IP 地址
```bash
# 单个 IP
export ALLOWED_IPS="120.77.56.227"

# 多个 IP（逗号分隔）
export ALLOWED_IPS="120.77.56.227,192.168.1.100"

# CIDR 网段
export ALLOWED_IPS="192.168.1.0/24"

# 混合配置
export ALLOWED_IPS="120.77.56.227,192.168.1.0/24,10.0.0.0/8"
```

### 可选配置

#### 3. 显示详细 IP 检测日志（调试用）
```bash
export SHOW_IP_DETECTION_DETAILS=true
```

## 使用场景

### 开发环境
**推荐配置：完全开放**
```bash
# 方式1: 不设置任何环境变量（默认行为）
# 所有 IP 都可以访问

# 方式2: 显式禁用
export IP_WHITELIST_ENABLED=false
```

### 测试环境
**推荐配置：限制内网访问**
```bash
export IP_WHITELIST_ENABLED=true
export ALLOWED_IPS="192.168.1.0/24,10.0.0.0/8"
```

### 生产环境
**推荐配置：严格限制**
```bash
export IP_WHITELIST_ENABLED=true
export ALLOWED_IPS="120.77.56.227"  # 你的服务器IP
```

## 安全行为说明

### 默认行为矩阵

| IP_WHITELIST_ENABLED | ALLOWED_IPS 设置 | 行为说明 |
|---------------------|-----------------|--------|
| 未设置或 false       | 任意 | 🟢 允许所有IP访问（开发模式） |
| true | 未设置或空 | 🟡 只允许本地IP访问（127.0.0.1等） |
| true | 已配置 | 🔵 允许配置的IP + 本地IP访问 |

### 特殊IP处理

以下IP地址**始终被允许**，无需配置：
- `127.0.0.1` (IPv4 本地回环)
- `::1` (IPv6 本地回环)  
- `localhost` (主机名)

### 错误处理

- **无效IP格式**: 拒绝访问并记录错误
- **配置解析失败**: 出于安全考虑拒绝访问
- **网络异常**: 允许访问以避免服务中断

## Docker 部署示例

### Docker Compose
```yaml
version: '3.8'
services:
  ml-backend:
    build: .
    ports:
      - "9091:9091"
    environment:
      - IP_WHITELIST_ENABLED=true
      - ALLOWED_IPS=120.77.56.227,192.168.1.0/24
      # 其他环境变量...
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-backend
spec:
  template:
    spec:
      containers:
      - name: ml-backend
        image: your-registry/ml-backend:latest
        env:
        - name: IP_WHITELIST_ENABLED
          value: "true"
        - name: ALLOWED_IPS
          value: "120.77.56.227,192.168.1.0/24"
```

## 访问被拒绝时的响应

当IP不在白名单中时，服务返回：

**HTTP 状态码**: `403 Forbidden`

**响应体**:
```json
{
  "error": "Access denied",
  "message": "Your IP address is not authorized to access this service", 
  "status": "forbidden"
}
```

## 日志记录

### 标准日志
```
WARNING - Access denied for IP: 192.168.2.100
DEBUG - IP whitelist check passed for: 120.77.56.227
INFO - IP whitelist enabled with IPs: ['120.77.56.227']
```

### 详细调试日志
设置 `SHOW_IP_DETECTION_DETAILS=true` 后会显示：
```
=== CLIENT IP DETECTION ===
request.remote_addr: 120.77.56.227
X-Forwarded-For: None
X-Real-IP: None
...
===========================
```

## 故障排查

### 1. 无法访问服务
检查环境变量配置：
```bash
echo "IP_WHITELIST_ENABLED: $IP_WHITELIST_ENABLED"
echo "ALLOWED_IPS: $ALLOWED_IPS"
```

### 2. 本地开发无法访问
确认本地IP是否为标准地址：
```bash
# 检查服务绑定地址
curl http://127.0.0.1:9091/health
# 而不是 localhost 或其他地址
```

### 3. 网段配置无效
验证CIDR格式：
```bash
# 正确: 192.168.1.0/24  
# 错误: 192.168.1.*
```

### 4. 生产环境调试
临时启用详细日志：
```bash
export SHOW_IP_DETECTION_DETAILS=true
# 重启服务后查看日志中的 IP 检测信息
```

## 安全建议

### ✅ 推荐做法
1. **生产环境必须启用白名单**
2. **使用最小权限原则**：只配置必要的IP
3. **定期审查允许的IP列表**
4. **监控访问日志中的拒绝记录**
5. **使用CIDR网段代替单IP（更灵活）**

### ❌ 避免做法
1. 不要在生产环境完全禁用白名单
2. 不要配置过于宽泛的网段 (如 0.0.0.0/0)
3. 不要将内部IP配置暴露在公开仓库中
4. 不要忽视访问日志中的异常IP

## 迁移指南

如果你之前使用其他访问控制方式，迁移步骤：

1. **备份现有配置**
2. **设置环境变量**
3. **测试访问控制**
4. **移除旧的配置方法**
5. **更新部署脚本**

## 技术实现

- IP验证使用Python `ipaddress` 模块，支持IPv4/IPv6
- 中间件在Flask请求处理前执行检查
- 配置加载无依赖，纯环境变量读取
- 失败时快速返回，不影响性能

---

**最后更新**: 2024年

如有问题或建议，请提交 Issue 或 Pull Request。