# Excel 分析端点 `/analyze` 使用指南 (Gemini-Powered)

## 概述

新增的 `/analyze` 端点现已集成 **Google Gemini 文档理解**能力，支持对 Excel 文件进行深度 AI 分析并返回专业的 Markdown 格式分析报告。

## 新功能亮点

✨ **Gemini AI 驱动**: 使用 Google Gemini 2.5 Flash 模型进行智能文档分析  
📊 **多表格处理**: 自动将 Excel 工作表转换为 CSV 并上传到 Gemini  
🎯 **专业分析**: 基于发票识别系统的专业分析框架  
🔧 **灵活配置**: 支持环境变量配置 API 密钥和模型选择  

## 环境配置

### 必需环境变量

```bash
# Gemini API 密钥 (必需)
export API_KEY='your-gemini-api-key'

# 分析模型 (可选，默认: gemini-2.5-flash)
export ANALYSIS_MODEL='gemini-2.5-flash'
```

### 获取 API 密钥

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新的 API 密钥
3. 设置环境变量

### 依赖安装

```bash
pip install google-genai pandas openpyxl
```

## API 规范

### 端点
```
POST /analyze
```

### 请求体
```json
{
  "excel_content": "string",        // Excel文件的base64编码内容
  "excel_filename": "string",       // Excel文件名（用于识别和日志）
  "project": "string",              // 项目UID (格式: project_id.timestamp)
  "label_config": "string",         // 项目的标注配置
  "params": {
    "context": "object",            // 可选，上下文信息
    "analysis_type": "string",      // 可选，分析类型，默认为"evaluation"
    "extra_params": "object"        // 可选，额外参数
  }
}
```

### 响应体
```json
{
  "status": "success|error",
  "analysis_result": "string",      // Gemini生成的Markdown格式分析结果
  "metadata": {
    "model_version": "string"       // 分析模型版本
  },
  "error": "string"                 // 错误信息（仅在status为error时返回）
}
```

## 使用方法

### 1. 启动服务

```bash
# 在项目根目录运行
label-studio-ml start ./invoice_extractor
```

服务将在 `http://localhost:9090` 启动

### 2. 设置环境变量

```bash
# 设置 Gemini API 密钥
export API_KEY='your-actual-gemini-api-key'

# 可选：设置模型
export ANALYSIS_MODEL='gemini-2.5-flash'
```

### 3. 测试方法

#### 方法一：使用 Python 测试脚本

```bash
# 设置环境变量
export API_KEY='your-gemini-api-key'

# 创建测试文件
python create_test_excel.py

# 测试默认文件
python test_analyze.py test_analysis.xlsx

# 测试指定文件
python test_analyze.py /path/to/your/file.xlsx
```

#### 方法二：使用 cURL 脚本

```bash
# 设置环境变量
export API_KEY='your-gemini-api-key'

# 测试默认文件
./test_curl.sh test_analysis.xlsx

# 测试指定文件
./test_curl.sh /path/to/your/file.xlsx
```

#### 方法三：直接使用 cURL

```bash
# 1. 设置环境变量
export API_KEY='your-gemini-api-key'

# 2. 编码Excel文件为base64
EXCEL_BASE64=$(base64 -i your_file.xlsx)

# 3. 发送请求
curl -X POST http://localhost:9090/analyze \
  -H "Content-Type: application/json" \
  --max-time 120 \
  -d '{
    "excel_content": "'$EXCEL_BASE64'",
    "excel_filename": "your_file.xlsx",
    "project": "test.123",
    "label_config": "<View><Text name=\"doc\" value=\"$doc\"/></View>",
    "params": {
      "analysis_type": "evaluation"
    }
  }'
```

## Gemini 分析流程

1. **文件处理**: Excel 文件解码并读取所有工作表
2. **格式转换**: 每个工作表转换为独立的 CSV 文件
3. **文件上传**: CSV 文件上传到 Gemini File API
4. **AI 分析**: Gemini 使用专业分析模板进行深度分析
5. **结果生成**: 返回结构化的 Markdown 分析报告
6. **资源清理**: 自动清理临时文件和上传文件

## 分析能力

### 🎯 核心健康指标分析
- 可识别率、文件准确率、票据准确率
- 字段准确率、单个字段识别率
- other文件占比分析

### 📊 问题诊断
- 仅显示未达标指标（达标指标不显示）
- 深度剖析每个问题的根本原因
- 提供具体的错误模式分析

### 💡 优化方案
- 可直接落地的技术优化方案
- 包含详细参数和预期效果
- 优先级分级（高/中/低）

## 示例输出

Gemini 会根据专业分析模板生成如下结构的报告：

```markdown
--------------------------------------------------
一、核心问题诊断（仅未达标指标）
[1] 可识别率：75% vs 80% (差距: -5%)
  • 文件格式识别失误导致处理异常
  • 图像质量低下影响OCR准确性

二、深度问题剖析
[图像质量] OCR识别准确性偏低
  - 问题机制：低分辨率图像导致字符边缘模糊
  - 错误模式：
    • 数字0/O混淆 (占比23%)
    • 字母l/I/1混淆 (占比18%)

三、可执行优化方案
[技术优化] 图像预处理增强 (优先级：高)
1. 实施图像锐化算法（unsharp mask, sigma=1.0）
   - 预期效果：OCR准确率提升8-12%
2. 添加噪声过滤处理（median filter, kernel=3）
   - 预期效果：字符识别清晰度提升15%
```

## 错误处理

### 常见错误及解决方案

| 错误类型 | 解决方案 |
|---------|----------|
| `API_KEY not set` | 设置环境变量：`export API_KEY='your-key'` |
| `Model not found` | 检查 `ANALYSIS_MODEL` 环境变量设置 |
| `Quota exceeded` | 检查 Gemini API 配额限制 |
| `Timeout` | Excel 文件过大，考虑拆分或等待更长时间 |

### 调试技巧

1. **检查环境变量**
   ```bash
   echo $API_KEY
   echo $ANALYSIS_MODEL
   ```

2. **查看服务日志**
   - 服务启动时会显示详细的处理日志
   - 包含文件上传、Gemini调用等步骤

3. **文件大小限制**
   - Gemini File API 支持最大 50MB 文件
   - 建议 Excel 文件不超过 20MB

## 性能说明

- **处理时间**: 30-60 秒（取决于文件大小和表格数量）
- **并发支持**: 支持多个请求并行处理
- **文件限制**: 最大 50MB Excel 文件
- **表格限制**: 无限制（受 Gemini 上下文窗口限制）

## 注意事项

1. **API 配额**: Gemini API 有使用配额限制，请合理使用
2. **文件隐私**: 上传的 CSV 文件会临时存储在 Gemini 中48小时后自动删除
3. **网络要求**: 需要能够访问 Google AI 服务
4. **错误处理**: 任何错误都会直接抛出，便于调试

## 下一步计划

- 支持更多文件格式（PDF、图片等）
- 自定义分析模板和评估标准
- 批量文件分析功能
- 分析结果可视化 