# 自定义端点扩展指南

## 当前可用端点

### 标准端点 (由label-studio-ml提供)
- `GET /health` - 基础健康检查
- `POST /setup` - 模型设置
- `POST /predict` - 模型预测
- `POST /train` - 模型训练
- `GET /metrics` - 系统指标

### 自定义端点 (由custom_api.py提供)
- `GET /versions` - 获取所有可用模型版本
- `GET /model/info` - 获取当前模型详细信息
- `GET /health/detailed` - 详细的健康检查

## 如何添加新的自定义端点

### 方法1：在custom_api.py中直接添加

1. 编辑 `custom_api.py` 文件
2. 在 `add_custom_endpoints()` 函数中添加新的路由

```python
def add_custom_endpoints(app, model_class):
    # ... 现有端点 ...

    @app.route('/your/new/endpoint', methods=['GET', 'POST'])
    def your_new_endpoint():
        """
        你的新端点描述
        """
        try:
            # 端点逻辑
            return jsonify({'message': 'success'})
        except Exception as e:
            logger.error(f"Your endpoint error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500
```

### 方法2：扩展模型类

如果端点需要复杂的模型逻辑，可以在 `model.py` 的 `NewModel` 类中添加方法：

```python
class NewModel(LabelStudioMLBase):
    # ... 现有方法 ...

    def your_custom_method(self):
        """你的自定义方法"""
        return {'data': 'your_data'}
```

然后在 `custom_api.py` 中调用：

```python
@app.route('/your/model/endpoint', methods=['GET'])
def your_model_endpoint():
    try:
        model_instance = model_class()
        result = model_instance.your_custom_method()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## 部署新端点

添加新端点后，使用自动化部署脚本：

```bash
./deploy.sh
```

这将：
1. 提交代码变更
2. 推送到远程仓库
3. 在目标机器上重新构建和部署
4. 自动测试新端点

## 测试端点

```bash
# 测试versions端点
curl http://129.226.88.226:9091/versions

# 测试模型信息端点
curl http://129.226.88.226:9091/model/info

# 测试详细健康检查
curl http://129.226.88.226:9091/health/detailed
```

## 最佳实践

1. **错误处理**: 所有端点都应该有try-catch错误处理
2. **日志记录**: 使用logger记录重要信息和错误
3. **文档**: 为每个端点添加docstring说明
4. **一致性**: 返回格式保持一致（JSON）
5. **权限**: 如需要，可以添加认证装饰器

## 常见端点模式

### 数据查询端点
```python
@app.route('/data/<data_id>', methods=['GET'])
def get_data(data_id):
    """获取特定数据"""
    try:
        model_instance = model_class()
        data = model_instance.get_data_by_id(data_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 配置更新端点
```python
@app.route('/config/update', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        config_data = request.json
        model_instance = model_class()
        result = model_instance.update_config(config_data)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### 状态查询端点
```python
@app.route('/status/<component>', methods=['GET'])
def get_component_status(component):
    """获取组件状态"""
    try:
        model_instance = model_class()
        status = model_instance.get_component_status(component)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```