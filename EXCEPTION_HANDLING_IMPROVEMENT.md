# 异常处理改进说明

## 概述

为了解决 LLM 调用中经常出现的超时、地区不支持等异常问题，我们扩展了 `ModelResponse` 类并改进了 `predict` 方法，使其能够向调用方返回详细的异常信息。

## 主要改进

### 1. 扩展 ModelResponse 类

在 `label_studio_ml/response.py` 中添加了错误处理功能：

- **新增字段**: `errors: Optional[List[Dict[str, Any]]] = None`
- **新增方法**: 
  - `add_error(task_index, task_id, error_message, error_type)` - 添加错误信息
  - `has_errors()` - 检查是否有错误

### 2. 改进 predict 方法

在 `invoice_extractor/model.py` 中的 `predict` 方法现在会：

- 捕获各种类型的异常
- 自动识别错误类型（超时、地区限制、认证等）
- 将错误信息添加到响应中
- 继续处理其他任务，不会因单个任务失败而中断整个批处理

## 错误类型分类

系统会自动识别以下错误类型：

| 错误类型 | 触发关键词 | 说明 |
|---------|-----------|------|
| `timeout_error` | timeout, 超时, timed out | 请求超时 |
| `region_not_supported` | region, 地区, location, country | 地区不支持 |
| `authentication_error` | api, key, 密钥, auth | 认证失败 |
| `network_error` | network, 网络, connection | 网络连接问题 |
| `empty_prediction` | - | 模型返回空预测 |
| `processing_error` | - | 其他处理错误（默认类型） |
| `critical_error` | - | 严重错误（连异常处理都失败） |

## 响应格式

### 成功的响应（无异常）
```json
{
  "results": {
    "model_version": "gemini-2.5-flash-preview-04-17",
    "predictions": [
      {
        "result": [...],
        "score": 0.9,
        "model_version": "..."
      }
    ],
    "errors": null
  }
}
```

### 包含异常的响应
```json
{
  "results": {
    "model_version": "gemini-2.5-flash-preview-04-17",
    "predictions": [
      {
        "result": [...],
        "score": 0.9,
        "model_version": "..."
      }
    ],
    "errors": [
      {
        "task_index": 1,
        "task_id": "task-456",
        "error_type": "timeout_error",
        "error_message": "Request timed out after 30 seconds"
      },
      {
        "task_index": 2,
        "task_id": "task-789",
        "error_type": "region_not_supported",
        "error_message": "API access not available in your region"
      }
    ]
  }
}
```

## 使用方式

### 客户端处理异常信息

```python
import requests

response = requests.post('/predict', json={
    'tasks': [...],
    'label_config': '...',
    # other parameters
})

result = response.json()
predictions = result['results'].get('predictions', [])
errors = result['results'].get('errors', [])

# 处理成功的预测
for prediction in predictions:
    print(f"预测结果: {prediction}")

# 处理错误
if errors:
    print(f"发现 {len(errors)} 个错误:")
    for error in errors:
        task_idx = error['task_index']
        task_id = error['task_id']
        error_type = error['error_type']
        error_msg = error['error_message']
        
        print(f"任务 {task_idx+1} (ID: {task_id}) 失败:")
        print(f"  错误类型: {error_type}")
        print(f"  错误信息: {error_msg}")
        
        # 根据错误类型采取不同的处理策略
        if error_type == 'timeout_error':
            print("  建议: 稍后重试或增加超时时间")
        elif error_type == 'region_not_supported':
            print("  建议: 检查API地区设置或使用代理")
        elif error_type == 'authentication_error':
            print("  建议: 检查API密钥配置")
```

### 错误统计和监控

```python
def analyze_errors(errors):
    """分析错误类型分布"""
    error_counts = {}
    for error in errors:
        error_type = error['error_type']
        error_counts[error_type] = error_counts.get(error_type, 0) + 1
    
    print("错误类型统计:")
    for error_type, count in error_counts.items():
        print(f"  {error_type}: {count}")
    
    return error_counts

# 使用示例
if errors:
    analyze_errors(errors)
```

## 向后兼容性

这次改进完全向后兼容：

- 现有的客户端代码无需修改即可继续工作
- `errors` 字段是可选的，当没有错误时为 `null`
- `predictions` 字段的格式和行为保持不变

## 日志输出

控制台会输出详细的处理统计信息：

```
Batch processing completed:
Total tasks: 5
Successful: 3
Failed: 2
Error details:
  - Task 2 (id: task-456): [timeout_error] Request timed out after 30 seconds
  - Task 4 (id: task-789): [region_not_supported] API access not available in your region
```

## 注意事项

1. **错误不会中断批处理**: 即使某些任务失败，系统仍会继续处理其他任务
2. **详细错误信息**: 每个错误都包含任务索引、任务ID、错误类型和详细消息
3. **自动错误分类**: 系统会根据错误消息自动识别错误类型，便于客户端采取针对性的处理策略
4. **性能影响最小**: 错误处理逻辑对正常流程的性能影响可忽略不计

这样的改进让调用方能够更好地了解和处理各种异常情况，提高了系统的可靠性和用户体验。 