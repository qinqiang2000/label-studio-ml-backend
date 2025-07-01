# Model Version API 单元测试文档

## 概述

这些测试用于验证模型版本管理和配置系统的正确性，包括：

- **ConfigManager** - 配置管理器的功能测试
- **NewModel.get_versions()** - 模型版本获取接口测试  
- **集成测试** - 端到端功能验证

## 测试文件

### 主要测试文件

- `test_model_versions.py` - 主要的单元测试文件
- `run_model_version_tests.py` - 测试运行脚本
- `README_MODEL_VERSION_TESTS.md` - 本文档

### 测试覆盖范围

#### 1. ConfigManager 测试 (`TestConfigManager`)

✅ **配置文件加载测试**
- `test_config_loading_success` - 成功加载YAML配置
- `test_config_loading_file_not_found` - 配置文件不存在时的回退机制
- `test_config_loading_yaml_error` - YAML格式错误时的处理

✅ **配置查询测试**
- `test_get_processor_config` - 获取处理器配置
- `test_get_available_processors` - 获取可用处理器列表
- `test_get_default_model` - 获取默认模型（包括环境变量覆盖）
- `test_get_model_config` - 获取具体模型配置

✅ **版本管理测试**
- `test_validate_model_version` - 模型版本字符串验证
- `test_get_all_versions` - 获取所有可用版本

#### 2. NewModel.get_versions() 测试 (`TestNewModelGetVersions`)

✅ **配置管理器集成测试**
- `test_get_versions_with_config_manager` - 使用配置管理器获取版本
- `test_get_versions_config_manager_exception` - 配置管理器异常处理

✅ **回退机制测试**
- `test_get_versions_fallback_method` - 配置管理器不可用时的回退

✅ **功能测试**
- `test_get_versions_current_processor_detection` - 当前处理器检测
- `test_get_versions_error_handling` - 错误处理机制

#### 3. 集成测试 (`TestModelVersionIntegration`)

✅ **端到端测试**
- `test_end_to_end_version_retrieval` - 完整的版本获取流程
- `test_processor_factory_integration` - 与处理器工厂的集成
- `test_configuration_consistency` - 配置一致性验证

## 运行测试

### 基本用法

```bash
# 运行所有测试
cd invoice_extractor/tests
python run_model_version_tests.py

# 或者直接运行测试文件
python test_model_versions.py
```

### 分类运行

```bash
# 只运行配置管理器测试
python run_model_version_tests.py config

# 只运行模型版本获取测试
python run_model_version_tests.py model

# 只运行集成测试
python run_model_version_tests.py integration
```

### 运行特定测试

```bash
# 运行特定的测试方法
python run_model_version_tests.py specific test_get_all_versions

# 运行包含特定关键词的测试
python run_model_version_tests.py specific config_loading
```

### 查看帮助

```bash
python run_model_version_tests.py help
```

## 测试输出示例

### 成功输出

```
🧪 Model Version API Unit Tests
============================================================
🔧 Running ConfigManager Tests
==================================================
test_config_loading_success ... ok
test_get_all_versions ... ok
test_get_available_processors ... ok
...

📋 Running NewModel.get_versions() Tests  
==================================================
test_get_versions_with_config_manager ... ok
test_get_versions_fallback_method ... ok
...

🔗 Running Integration Tests
==================================================
test_end_to_end_version_retrieval ... ok
test_configuration_consistency ... ok
...

============================================================
📊 Test Summary:
   ConfigManager Tests: ✅ PASS
   NewModel Tests:      ✅ PASS
   Integration Tests:   ✅ PASS
------------------------------------------------------------
🎉 All tests passed! Model version API is working correctly.
```

### 失败输出

```
❌ Some tests failed. Check the output above for details.
```

## 测试数据

测试使用模拟的配置数据：

```yaml
processors:
  gemini:
    default_model: "gemini-2.5-flash-preview-04-17"
    models:
      gemini-2.5-flash-preview-04-17:
        name: "gemini-2.5-flash-preview-04-17"
        description: "Gemini 2.5 Flash Preview (tested, recommended)"
      gemini-2.5-flash-lite-preview-06-17:
        name: "gemini-2.5-flash-lite-preview-06-17"
        description: "Gemini 2.5 flash (fastest and cheapest)"
        
  openai:
    default_model: "gpt-4.1"
    models:
      gpt-4.1-mini:
        name: "gpt-4.1-mini"
        description: "OpenAI GPT-4.1-mini (fastest and cheapest)"
      gpt-4.1:
        name: "gpt-4.1"
        description: "OpenAI GPT-4.1 (Stable)"
```

## 验证的功能

### ✅ 配置管理器功能

1. **配置加载**
   - YAML文件解析
   - 文件不存在时的回退
   - 格式错误时的处理

2. **配置查询**
   - 处理器配置获取
   - 模型配置获取
   - 默认值处理

3. **环境变量支持**
   - 模型覆盖机制
   - 环境变量优先级

### ✅ 版本接口功能

1. **版本获取**
   - 完整的版本列表
   - 版本字符串格式
   - 默认模型标记

2. **当前状态**
   - 当前处理器检测
   - 当前模型版本

3. **错误处理**
   - 异常捕获
   - 回退机制
   - 错误信息返回

### ✅ 系统集成

1. **组件协作**
   - 配置管理器与模型类的集成
   - 处理器工厂的一致性

2. **数据一致性**
   - 版本信息的准确性
   - 配置与实际的匹配

## 扩展测试

如果需要添加新的测试：

1. **在 `TestConfigManager` 中添加配置管理器相关测试**
2. **在 `TestNewModelGetVersions` 中添加模型版本接口测试**
3. **在 `TestModelVersionIntegration` 中添加集成测试**

### 测试模板

```python
def test_new_functionality(self):
    """Test description"""
    # Arrange
    # 设置测试数据
    
    # Act  
    # 执行被测试的功能
    
    # Assert
    # 验证结果
    self.assertEqual(expected, actual)
```

## 故障排除

### 常见问题

1. **ImportError**: 确保在正确的目录运行测试
2. **配置错误**: 检查测试数据格式
3. **环境变量**: 测试会自动设置必要的环境变量

### 调试技巧

```python
# 在测试中添加调试输出
import logging
logging.basicConfig(level=logging.DEBUG)

# 或使用print语句
print(f"Debug: {variable_to_check}")
```

## CI/CD 集成

这些测试可以轻松集成到 CI/CD 流水线中：

```bash
# 在CI脚本中运行
cd invoice_extractor/tests
python run_model_version_tests.py
if [ $? -eq 0 ]; then
    echo "Model version tests passed"
else
    echo "Model version tests failed"
    exit 1
fi
``` 