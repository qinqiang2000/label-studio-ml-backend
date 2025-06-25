# Runtime Config 迁移指引

## 🎯 概述

本文档为原有对接方提供详细的迁移指引，说明如何适配新增的 `runtime_config` 参数功能。新功能完全向后兼容，现有集成无需修改即可继续工作。

## 🔧 核心变更

### 新增参数支持

Invoice Extractor 现在支持通过 `runtime_config` 参数动态配置AI模型行为：

- **temperature**: 控制输出随机性 (0.0-2.0)
- **response_schema**: 定义结构化输出的JSON schema
- **response_mime_type**: 设置响应格式 ("application/json" 或 "text/plain")
- **max_output_tokens**: 最大输出token数
- 以及其他Gemini模型参数

## 📋 迁移步骤

### 步骤 1: 评估现有集成 ✅

**好消息**: 现有的API调用无需任何修改即可继续工作！

```python
# 现有调用方式 - 完全兼容，无需修改
response = requests.post('/predict', json={
    'tasks': [your_task_data],
    'prompt': 'Extract invoice information'  # 可选
})
```

### 步骤 2: 确定优化需求 🎯

根据业务需求，确定是否需要使用 `runtime_config`：

| 场景 | 是否需要runtime_config | 原因 |
|------|---------------------|------|
| 现有功能正常工作 | ❌ 不需要 | 继续使用默认配置 |
| 需要更精确的结构化输出 | ✅ 需要 | 使用response_schema |
| 需要更稳定/更创意的输出 | ✅ 需要 | 调整temperature |
| 需要控制输出长度 | ✅ 需要 | 设置max_output_tokens |
| 需要可重复的结果 | ✅ 需要 | 设置seed参数 |

### 步骤 3: 渐进式迁移 🔄

#### 3.1 保持现有调用不变

```python
# 继续使用现有方式
def extract_invoice_legacy(task_data):
    response = requests.post('/predict', json={
        'tasks': [task_data],
        'prompt': 'Extract invoice information'
    })
    return response.json()
```

#### 3.2 为新需求添加runtime_config

```python
# 为需要特殊配置的场景添加新方法
def extract_invoice_structured(task_data, precision_mode=False):
    request_data = {
        'tasks': [task_data],
        'prompt': 'Extract invoice information'
    }
    
    # 根据需求添加runtime_config
    if precision_mode:
        request_data['runtime_config'] = {
            "temperature": 0.1,  # 更稳定的输出
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "total_amount": {"type": "number"},
                    "date": {"type": "string"},
                    "vendor": {"type": "string"}
                },
                "required": ["invoice_number", "total_amount", "date"]
            }
        }
    
    response = requests.post('/predict', json=request_data)
    return response.json()
```

## 🛠️ 实际应用示例

### 示例 1: 基础迁移（推荐）

```python
class InvoiceExtractorClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def extract_invoice(self, task_data, config=None):
        """
        提取发票信息
        
        Args:
            task_data: 任务数据
            config: 可选的运行时配置
        """
        request_data = {
            'tasks': [task_data],
            'prompt': 'Extract detailed invoice information'
        }
        
        # 如果提供了配置，则添加到请求中
        if config:
            request_data['runtime_config'] = config
            
        response = requests.post(f'{self.base_url}/predict', json=request_data)
        return response.json()

# 使用示例
client = InvoiceExtractorClient("http://localhost:9090")

# 1. 使用默认配置（无变化）
result = client.extract_invoice(task_data)

# 2. 使用自定义配置（新功能）
precise_config = {
    "temperature": 0.1,
    "response_mime_type": "application/json"
}
result = client.extract_invoice(task_data, precise_config)
```

### 示例 2: 场景驱动的配置

```python
class InvoiceProcessor:
    def __init__(self):
        self.base_configs = {
            'precise': {
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "seed": 12345
            },
            'creative': {
                "temperature": 0.7,
                "response_mime_type": "text/plain",
                "top_p": 0.9
            },
            'structured': {
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "header": {"type": "object"},
                        "line_items": {"type": "array"},
                        "totals": {"type": "object"}
                    }
                }
            }
        }
    
    def process_invoice(self, task_data, mode='default'):
        request_data = {
            'tasks': [task_data],
            'prompt': 'Extract invoice information'
        }
        
        # 根据模式添加配置
        if mode in self.base_configs:
            request_data['runtime_config'] = self.base_configs[mode]
        
        response = requests.post('/predict', json=request_data)
        return response.json()

# 使用示例
processor = InvoiceProcessor()

# 不同场景使用不同配置
result1 = processor.process_invoice(task_data, 'default')    # 使用默认
result2 = processor.process_invoice(task_data, 'precise')    # 精确模式
result3 = processor.process_invoice(task_data, 'structured') # 结构化模式
```

### 示例 3: 动态配置构建

```python
class SmartInvoiceExtractor:
    def build_config(self, requirements):
        """根据业务需求动态构建配置"""
        config = {}
        
        if requirements.get('high_precision'):
            config['temperature'] = 0.1
            config['seed'] = 12345
        elif requirements.get('creative_interpretation'):
            config['temperature'] = 0.7
            config['top_p'] = 0.9
        
        if requirements.get('structured_output'):
            config['response_mime_type'] = 'application/json'
            config['response_schema'] = requirements['schema']
        
        if requirements.get('max_length'):
            config['max_output_tokens'] = requirements['max_length']
        
        return config if config else None
    
    def extract(self, task_data, requirements=None):
        request_data = {
            'tasks': [task_data],
            'prompt': 'Extract invoice information'
        }
        
        if requirements:
            config = self.build_config(requirements)
            if config:
                request_data['runtime_config'] = config
        
        response = requests.post('/predict', json=request_data)
        return response.json()

# 使用示例
extractor = SmartInvoiceExtractor()

# 高精度提取
result = extractor.extract(task_data, {
    'high_precision': True,
    'structured_output': True,
    'schema': {...}
})
```

## 🔍 测试和验证

### 测试检查清单

- [ ] 现有调用保持正常工作
- [ ] 新的runtime_config参数生效
- [ ] 错误处理正常（无效配置被忽略）
- [ ] 日志记录配置应用情况
- [ ] 性能没有明显下降

### 测试用例模板

```python
import pytest
import requests

class TestMigration:
    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 使用原有调用方式
        response = requests.post('/predict', json={
            'tasks': [sample_task]
        })
        assert response.status_code == 200
    
    def test_new_runtime_config(self):
        """测试新的runtime_config功能"""
        config = {"temperature": 0.5}
        response = requests.post('/predict', json={
            'tasks': [sample_task],
            'runtime_config': config
        })
        assert response.status_code == 200
    
    def test_invalid_config_handling(self):
        """测试无效配置处理"""
        invalid_config = "not_a_dict"
        response = requests.post('/predict', json={
            'tasks': [sample_task],
            'runtime_config': invalid_config
        })
        # 应该继续工作，忽略无效配置
        assert response.status_code == 200
```

## 📊 配置最佳实践

### 常用配置组合

#### 高精度提取（推荐用于生产环境）
```python
precision_config = {
    "temperature": 0.1,
    "response_mime_type": "application/json",
    "seed": 12345,
    "max_output_tokens": 2000
}
```

#### 结构化数据提取
```python
structured_config = {
    "temperature": 0.2,
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "invoice_data": {
                "type": "object",
                "properties": {
                    "header": {"type": "object"},
                    "line_items": {"type": "array"},
                    "totals": {"type": "object"}
                }
            }
        }
    }
}
```

#### 探索性提取（用于数据分析）
```python
exploratory_config = {
    "temperature": 0.6,
    "response_mime_type": "text/plain",
    "top_p": 0.9,
    "max_output_tokens": 1500
}
```

## ⚠️ 注意事项

### 1. 配置优先级

系统按以下优先级应用配置：
1. **Runtime Config** (最高) - API中传入的配置
2. **Environment Variables** (中等) - 环境变量
3. **Default Values** (最低) - 代码默认值

### 2. 错误处理

- 无效的配置参数会被记录警告但不会中断处理
- 不支持runtime_config的processor会忽略该参数
- 系统会记录详细日志便于调试

### 3. 性能考虑

- Runtime_config不会显著影响性能
- 建议为常用场景预定义配置而非每次动态构建
- 使用合适的max_output_tokens避免过长响应

## 🆘 故障排除

### 常见问题

**Q: 添加了runtime_config但似乎没有生效？**
A: 检查日志中是否有"Applied runtime_config"消息，确认配置格式正确（必须是dict）

**Q: 某些参数被忽略了？**
A: 检查是否有"Unknown runtime_config parameters"警告，确认参数名拼写正确

**Q: 现有功能突然不工作了？**
A: Runtime_config完全向后兼容，检查其他可能的问题（网络、认证等）

### 调试建议

1. 启用详细日志记录
2. 检查API请求格式
3. 验证配置参数有效性
4. 使用简单配置测试

## 📞 支持

如有任何迁移问题，请：
1. 查看系统日志
2. 参考测试用例
3. 联系技术支持团队

---

**记住：迁移是可选的！现有系统无需任何修改即可继续正常工作。** 