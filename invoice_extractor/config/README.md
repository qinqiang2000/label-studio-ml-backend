# 模型配置管理系统

## 概述

这个配置管理系统统一管理所有AI模型处理器的配置，避免了配置散乱和硬编码的问题。

## 文件结构

```
config/
├── models.yaml      # 主配置文件
├── manager.py       # 配置管理器
└── README.md        # 本文档
```

## 配置文件说明

### 主配置文件 (`models.yaml`)

包含以下主要部分：

1. **全局默认设置** - 默认处理器和备用处理器
2. **处理器配置** - 每个AI服务商的详细配置
3. **模型选择策略** - 自动选择模型的策略

### 配置结构

```yaml
# 全局设置
defaults:
  processor: "gemini"           # 默认处理器

# 处理器配置
processors:
  gemini:                       # 处理器类型
    type: "gemini"
    name: "Google Gemini"
    enabled: true               # 是否启用
    default_model: "gemini-2.5-flash-preview-04-17"
    
    env_vars:                   # 环境变量映射
      api_key: "API_KEY"
      model_override: "GEMINI_MODEL"
    
    models:                     # 支持的模型列表
      gemini-2.5-flash-preview-04-17:
        name: "gemini-2.5-flash-preview-04-17"
        description: "Gemini 2.5 Flash Preview (tested, recommended)"
```

## 使用方法

### 1. 添加新模型

要添加一个新的Gemini模型，只需在 `models.yaml` 中添加：

```yaml
processors:
  gemini:
    models:
      新模型名称:
        name: "新模型名称"
        description: "模型描述"
```

### 2. 添加新处理器

要添加一个全新的AI服务商：

```yaml
processors:
  新处理器:
    type: "新处理器"
    name: "新AI服务商"
    description: "服务商描述"
    enabled: true
    default_model: "默认模型名"
    
    env_vars:
      api_key: "新处理器_API_KEY"
      model_override: "新处理器_MODEL"
    
    models:
      # ... 模型配置
```

### 3. 禁用处理器

```yaml
processors:
  openai:
    enabled: false  # 禁用OpenAI处理器
```

### 4. 更改默认模型

```yaml
processors:
  gemini:
    default_model: "gemini-2.5-flash"  # 更改默认模型
```

## 环境变量支持

系统支持通过环境变量覆盖配置：

```bash
# 全局处理器选择
export DOCUMENT_PROCESSOR=gemini

# Gemini特定配置
export API_KEY=your_gemini_api_key
export GEMINI_MODEL=gemini-2.5-flash  # 覆盖默认模型

# OpenAI特定配置
export OPENAI_API_KEY=your_openai_api_key
export OPENAI_MODEL=gpt-4o
```

## 配置管理器API

### 基本用法

```python
from config.manager import config_manager

# 获取所有可用版本
versions = config_manager.get_all_versions()

# 获取处理器配置
gemini_config = config_manager.get_processor_config('gemini')

# 获取默认模型
default_model = config_manager.get_default_model('gemini')

# 验证模型版本
processor_type, model_name = config_manager.validate_model_version('gemini|gemini-2.5-flash')

# 获取模型配置详情
model_config = config_manager.get_model_config('gemini', 'gemini-2.5-flash-preview-04-17')
```

### 高级功能

```python
# 获取推荐模型（返回默认模型）
recommended = config_manager.get_recommended_models('gemini')

# 获取环境变量映射
env_vars = config_manager.get_env_vars_for_processor('gemini')

# 重新加载配置
config_manager.reload_config()
```

## 向后兼容性

- 当配置管理器不可用时，系统会自动回退到原有的硬编码配置
- 现有的环境变量设置继续有效
- 原有的API调用方式保持不变

## 优势

1. **集中配置** - 所有模型配置集中在一个文件中
2. **简化维护** - 去除复杂的元数据，只保留必要信息
3. **灵活扩展** - 易于添加新模型和处理器
4. **环境变量支持** - 支持运行时覆盖配置
5. **向后兼容** - 不破坏现有功能
6. **详细注释** - YAML格式支持详细的配置说明

## 配置验证

配置管理器会自动验证：

- 处理器类型是否存在
- 模型名称是否有效
- 配置文件格式是否正确

错误时会直接失败并报告错误（不再有自动回退逻辑）。

## 特殊说明

- **Excel 分析功能**独立于此配置系统，使用专门的 `analyze_excel` 方法
- 该方法直接使用环境变量 `API_KEY` 和 `ANALYSIS_MODEL` 进行配置
- 不传入模型名称时，使用各处理器的默认模型 