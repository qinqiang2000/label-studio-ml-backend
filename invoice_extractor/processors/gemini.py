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
    
    def __init__(self, model_name: str = "gemini-2.5-flash-preview-04-17", llm_param_config: dict = None):
        self.client = genai.Client(api_key=os.environ.get("API_KEY"))
        self.model_name = model_name
        # 从环境变量或传入参数中构建 LLM 配置
        self.llm_param_config = self._build_param_config(llm_param_config or {})
    
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
    
    def process_document(self, file_path: str, instruction: str) -> str:
        contents = [
            types.Part.from_bytes(
                data=pathlib.Path(file_path).read_bytes(),
                mime_type="application/pdf" if file_path.lower().endswith('.pdf') else (
                    "image/png" if file_path.lower().endswith('.png') else
                    "image/jpeg" if file_path.lower().endswith(('.jpg', '.jpeg')) else
                    "application/octet-stream"
                ),
            )]
        
        # 构造完整的参数配置
        param_config = GeminiLMModelParams(**self.llm_param_config).model_dump(exclude_none=True)
        param_config["system_instruction"] = [types.Part.from_text(text=instruction)]
        
        generate_content_config = types.GenerateContentConfig(**param_config)
        
        logger.info(f'calling genai: {self.model_name}')
        logger.info(f'Model configuration: {param_config}')
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        )
        
        # extract_json returns a list of JSON strings, so we take the first element
        print(response.text)
        # json_string = extract_json(response.text)[0]
        return response.text
    
    def get_model_version(self) -> str:
        return self.model_name 