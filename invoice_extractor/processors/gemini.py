import json
import os
import logging
import pathlib
from typing import Optional, Any, List
from pydantic import BaseModel, Field
from google.genai import types
from google import genai
from processors.base import DocumentProcessor
from utils import extract_json

logger = logging.getLogger(__name__)

class GeminiLMModelParams(BaseModel):
    temperature: Optional[float] = Field(
        0.1,
        description="温度：较高的数值会使输出更加随机，而较低的数值会使其更加集中和确定。如果设置为0，模型将使用对数概率自动增加温度，直到达到某些阈值。"
    )
    seed: Optional[int] = Field(12345, description="随机种子")
    top_p: Optional[float] = Field(
        None,
        description="模型仅考虑概率累积为 top_p 的 token 结果。"
    )
    top_k: Optional[float] = Field(
        None,
        description="模型采样时要考虑的最大 token 数。"
    )
    candidate_count: Optional[int] = Field(None,
                                           description="返回的响应数。如果未设置，则默认为 1。请注意，这不适用于上一代型号（Gemini 1.0 系列）")
    max_output_tokens: Optional[int] = Field(
        None,
        description="允许生成的最大 token 数。"
    )
    stop_sequences: Optional[List[str]] = Field(
        None,
        description="最多可指定 5 个序列，API 遇到这些序列时将停止生成 token。"
    )
    presence_penalty: Optional[float] = Field(
        None,
        description="存在惩罚：正值会基于新 token 是否已经出现在文本中而对其进行惩罚，增加模型使用新词汇的可能性。"
    )
    frequency_penalty: Optional[float] = Field(
        None,
        description="频率惩罚：正值会基于新 token 在文本中已出现的频率对其进行惩罚，降低模型重复相同词汇的可能性。"
    )
    response_mime_type: Optional[str] = Field(
        "application/json",
        description="""响应输出的 MIME 类型。支持的 MIME 类型：
        - text/plain：（默认）文本输出。
        - application/json： JSON 响应。
        - text/x.enum：在输出响应中以字符串形式返回枚举值。"""
    )
    response_schema: Optional[Any] = Field(
        default=None,
        description="""Schema" 对象允许定义输出数据类型。这些类型可以是 objects，也可以是primitives 和 arrays。它表示OpenAPI 3.0 模式对象的一个选定子集。
        如果设置了该对象，则还必须设置兼容的response_mime_type。兼容的 MIME 类型：application/json。
          """,
    )
    response_modalities: Optional[List[str]] = Field(
        default=None,
        description="""响应的请求模态。表示模型可返回的模态集合。空列表等效于仅请求文本。
          """,
    )
    thinking_config: Optional[Any] = Field(
        default=types.ThinkingConfig(thinking_budget=0),
        description="""深度思考配置"""
    )

class GeminiProcessor(DocumentProcessor):
    """Gemini-based document processor"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-preview-04-17"):
        self.client = genai.Client(api_key=os.environ.get("API_KEY"))
        self.model_name = model_name
        # 从环境变量构建 LLM 配置，使用默认值
        self.llm_param_config = self._build_param_config({})
    
    def _build_param_config(self, custom_config: dict) -> dict:
        """从环境变量和自定义配置构建 LLM 参数配置"""
        # 从环境变量读取参数
        env_config = {}
        
        # Temperature (0.0-2.0)
        if os.environ.get('GEMINI_TEMPERATURE'):
            env_config['temperature'] = float(os.environ.get('GEMINI_TEMPERATURE'))
        
        # Max output tokens
        if os.environ.get('GEMINI_MAX_OUTPUT_TOKENS'):
            env_config['max_output_tokens'] = int(os.environ.get('GEMINI_MAX_OUTPUT_TOKENS'))
        
        # Top P
        if os.environ.get('GEMINI_TOP_P'):
            env_config['top_p'] = float(os.environ.get('GEMINI_TOP_P'))
        
        # Top K
        if os.environ.get('GEMINI_TOP_K'):
            env_config['top_k'] = int(os.environ.get('GEMINI_TOP_K'))
        
        # Seed
        if os.environ.get('GEMINI_SEED'):
            env_config['seed'] = int(os.environ.get('GEMINI_SEED'))
        
        # Candidate count
        if os.environ.get('GEMINI_CANDIDATE_COUNT'):
            env_config['candidate_count'] = int(os.environ.get('GEMINI_CANDIDATE_COUNT'))
        
        # Stop sequences
        if os.environ.get('GEMINI_STOP_SEQUENCES'):
            env_config['stop_sequences'] = os.environ.get('GEMINI_STOP_SEQUENCES').split(',')
        
        # Presence penalty
        if os.environ.get('GEMINI_PRESENCE_PENALTY'):
            env_config['presence_penalty'] = float(os.environ.get('GEMINI_PRESENCE_PENALTY'))
        
        # Frequency penalty
        if os.environ.get('GEMINI_FREQUENCY_PENALTY'):
            env_config['frequency_penalty'] = float(os.environ.get('GEMINI_FREQUENCY_PENALTY'))
        
        # Response MIME type
        if os.environ.get('GEMINI_RESPONSE_MIME_TYPE'):
            env_config['response_mime_type'] = os.environ.get('GEMINI_RESPONSE_MIME_TYPE')
        
        # Thinking budget
        if os.environ.get('GEMINI_THINKING_BUDGET'):
            thinking_budget = int(os.environ.get('GEMINI_THINKING_BUDGET'))
            env_config['thinking_config'] = types.ThinkingConfig(thinking_budget=thinking_budget)
        
        # 合并环境变量配置和自定义配置，自定义配置优先
        final_config = {**env_config, **custom_config}
        
        logger.debug(f"Built Gemini param config: {final_config}")
        return final_config
    
    def _normalize_schema(self, schema):
        """
        标准化 JSON Schema 格式
        将大写的类型名称转换为小写，修复结构问题
        """
        if not isinstance(schema, dict):
            return schema
        
        # 递归处理嵌套的 schema
        normalized = {}
        
        for key, value in schema.items():
            if key == 'type' and isinstance(value, str):
                # 将类型名称转换为小写
                normalized[key] = value.lower()
            elif key == 'properties' and isinstance(value, dict):
                # 递归处理 properties，并移除错误的 required 字段
                normalized_props = {}
                for prop_key, prop_value in value.items():
                    if prop_key != 'required':  # 移除 properties 中的 required
                        normalized_props[prop_key] = self._normalize_schema(prop_value)
                normalized[key] = normalized_props
            elif key in ['items', 'anyOf', 'oneOf', 'allOf'] and isinstance(value, (dict, list)):
                # 递归处理数组和条件 schema
                if isinstance(value, dict):
                    normalized[key] = self._normalize_schema(value)
                elif isinstance(value, list):
                    normalized[key] = [self._normalize_schema(item) for item in value]
            else:
                # 其他字段保持不变
                normalized[key] = value
        
        return normalized
    
    def process_document(self, file_path: str, instruction: str, runtime_config: Optional[dict] = None) -> str:
        """
        处理文档
        
        Args:
            file_path: 文档文件路径
            instruction: 处理指令
            runtime_config: 运行时配置，可覆盖默认配置。支持的参数：
                - temperature: 温度参数
                - response_mime_type: 响应MIME类型
                - response_schema: 响应schema
                - 以及其他GeminiLMModelParams支持的参数
        
        Returns:
            处理结果的JSON字符串
        """
        contents = [
            types.Part.from_bytes(
                data=pathlib.Path(file_path).read_bytes(),
                mime_type="application/pdf" if file_path.lower().endswith('.pdf') else (
                    "image/png" if file_path.lower().endswith('.png') else
                    "image/jpeg" if file_path.lower().endswith(('.jpg', '.jpeg')) else
                    "application/octet-stream"
                ),
            )]
        
        # 合并运行时配置：runtime_config > 默认配置
        merged_config = {**self.llm_param_config}
        if runtime_config:
            merged_config.update(runtime_config)
            logger.debug(f"Applied runtime config: {runtime_config}")
        
        # 标准化 response_schema 格式（修复大写类型名称问题）
        if 'response_schema' in merged_config and merged_config['response_schema']:
            merged_config['response_schema'] = self._normalize_schema(merged_config['response_schema'])
            logger.info(f"Normalized response_schema format")
        
        # 构造完整的参数配置
        param_config = GeminiLMModelParams(**merged_config).model_dump(exclude_none=True)
        param_config["system_instruction"] = [types.Part.from_text(text=instruction)]
        
        generate_content_config = types.GenerateContentConfig(**param_config)
        
        logger.info(f'calling genai: {self.model_name}')
        logger.info(f'Model configuration: {param_config}')
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        )
        print(response.text)
        
        # extract_json returns a list of JSON strings, so we take the first element
        json_string = response.text
        
        # if the response_mime_type is text/plain, we need to extract the JSON string
        current_mime_type = merged_config.get('response_mime_type', 'application/json')
        if current_mime_type == 'text/plain':
            json_string = extract_json(response.text)
            if isinstance(json_string, list) and len(json_string) > 0:
                json_string = json_string[0]
                
        return json_string
    
    def get_model_version(self) -> str:
        return self.model_name 

"""
使用示例：

# 1. 使用默认配置（向后兼容）
processor = GeminiProcessor()
result = processor.process_document("invoice.pdf", "Extract invoice data")

# 2. 使用运行时配置
processor = GeminiProcessor()

# 传递特定的配置参数
runtime_config = {
    "temperature": 0.2,
    "response_mime_type": "application/json",
    "response_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total_amount": {"type": "number"},
            "date": {"type": "string"}
        },
        "required": ["invoice_number", "total_amount", "date"]
    }
}

result = processor.process_document("invoice.pdf", "Extract invoice data", runtime_config)

# 3. 只覆盖部分参数
minimal_config = {
    "temperature": 0.5,
    "response_mime_type": "text/plain"
}

result = processor.process_document("invoice.pdf", "Extract invoice data", minimal_config)
""" 