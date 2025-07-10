import json
import os
import logging
import base64
import pathlib
from typing import Optional, Any, List
from pydantic import BaseModel, Field
import requests
from processors.base import DocumentProcessor
from processors.piaozone_token import get_piaozone_token
from utils import extract_json

logger = logging.getLogger(__name__)

class PiaoZoneModelParams(BaseModel):
    temperature: Optional[float] = Field(
        0.1,
        description="温度：较高的数值会使输出更加随机，而较低的数值会使其更加集中和确定。"
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
    max_output_tokens: Optional[int] = Field(
        None,
        description="允许生成的最大 token 数。"
    )
    response_mime_type: Optional[str] = Field(
        "application/json",
        description="响应输出的 MIME 类型。"
    )
    response_schema: Optional[Any] = Field(
        default=None,
        description="Schema 对象允许定义输出数据类型。"
    )
    thinking_budget: Optional[int] = Field(
        0,
        description="深度思考配置预算"
    )

class PiaoZoneProcessor(DocumentProcessor):
    """PiaoZone-based document processor"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-preview-04-17"):
        # 从环境变量获取API配置
        self.api_url = os.environ.get("PIAOZONE_API_URL", "https://api-sit.piaozone.com/ai/knowledge/v1/chat/completions")
        self.model_name = model_name
        
        # 从环境变量构建 LLM 配置，使用默认值
        self.llm_param_config = self._build_param_config({})
        
        logger.info(f"Initialized PiaoZone processor with model: {model_name}")
    
    def _build_param_config(self, custom_config: dict) -> dict:
        """从环境变量和自定义配置构建 LLM 参数配置"""
        # 从环境变量读取参数
        env_config = {}
        
        # Temperature (0.0-2.0)
        if os.environ.get('PIAOZONE_TEMPERATURE'):
            env_config['temperature'] = float(os.environ.get('PIAOZONE_TEMPERATURE'))
        
        # Max output tokens
        if os.environ.get('PIAOZONE_MAX_OUTPUT_TOKENS'):
            env_config['max_output_tokens'] = int(os.environ.get('PIAOZONE_MAX_OUTPUT_TOKENS'))
        
        # Top P
        if os.environ.get('PIAOZONE_TOP_P'):
            env_config['top_p'] = float(os.environ.get('PIAOZONE_TOP_P'))
        
        # Top K
        if os.environ.get('PIAOZONE_TOP_K'):
            env_config['top_k'] = int(os.environ.get('PIAOZONE_TOP_K'))
        
        # Seed
        if os.environ.get('PIAOZONE_SEED'):
            env_config['seed'] = int(os.environ.get('PIAOZONE_SEED'))
        
        # Response MIME type
        if os.environ.get('PIAOZONE_RESPONSE_MIME_TYPE'):
            env_config['response_mime_type'] = os.environ.get('PIAOZONE_RESPONSE_MIME_TYPE')
        
        # Thinking budget
        if os.environ.get('PIAOZONE_THINKING_BUDGET'):
            env_config['thinking_budget'] = int(os.environ.get('PIAOZONE_THINKING_BUDGET'))
        
        # 合并环境变量配置和自定义配置，自定义配置优先
        final_config = {**env_config, **custom_config}
        
        logger.debug(f"Built PiaoZone param config: {final_config}")
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
                # 将类型名称转换为大写 (PiaoZone API 需要大写)
                normalized[key] = value.upper()
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
    
    def _get_mime_type(self, file_path: str) -> str:
        """根据文件扩展名确定MIME类型"""
        if file_path.lower().endswith('.pdf'):
            return "application/pdf"
        elif file_path.lower().endswith('.png'):
            return "image/png"
        elif file_path.lower().endswith(('.jpg', '.jpeg')):
            return "image/jpeg"
        else:
            return "application/octet-stream"
    
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
                - 以及其他PiaoZoneModelParams支持的参数
        
        Returns:
            处理结果的JSON字符串
        """
        # 读取文件并转换为base64
        file_data = pathlib.Path(file_path).read_bytes()
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        file_name = os.path.basename(file_path)
        mime_type = self._get_mime_type(file_path)
        
        # 合并运行时配置：runtime_config > 默认配置
        merged_config = {**self.llm_param_config}
        if runtime_config:
            merged_config.update(runtime_config)
            logger.debug(f"Applied runtime config: {runtime_config}")
        
        # 标准化 response_schema 格式（转换为大写类型名称）
        if 'response_schema' in merged_config and merged_config['response_schema']:
            merged_config['response_schema'] = self._normalize_schema(merged_config['response_schema'])
            logger.info(f"Normalized response_schema format for PiaoZone API")
        
        # 构造完整的参数配置
        param_config = PiaoZoneModelParams(**merged_config).model_dump(exclude_none=True)
        
        # 尝试简化的请求格式（使用文本内容）
        # 如果是文本文件，尝试读取文本内容而不是base64编码
        if mime_type == "application/octet-stream" and file_name.endswith('.txt'):
            try:
                text_content = pathlib.Path(file_path).read_text(encoding='utf-8')
                logger.info(f"Using text content instead of file: {text_content[:100]}...")
                
                request_data = {
                    "llm_type": "gemini", 
                    "data": {
                        "model": self.model_name,
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": f"Document content:\n{text_content}\n\nInstruction: {instruction}"
                                    }
                                ]
                            }
                        ],
                        "generation_config": param_config
                    }
                }
            except Exception as e:
                logger.warning(f"Failed to read text content: {e}, falling back to file format")
                # 如果读取文本失败，使用原来的文件格式
                request_data = {
                    "llm_type": "gemini",
                    "data": {
                        "model": self.model_name,
                        "contents": [
                            {
                                "type": "file",
                                "file": {
                                    "mime_type": mime_type,
                                    "data": file_base64,
                                    "name": file_name
                                }
                            }
                        ],
                        "generation_config": {
                            **param_config,
                            "system_instruction": instruction
                        }
                    }
                }
        else:
            # 对于PDF和图片，使用文件格式
            request_data = {
                "llm_type": "gemini",
                "data": {
                    "model": self.model_name,
                    "contents": [
                        {
                            "type": "file",
                            "file": {
                                "mime_type": mime_type,
                                "data": file_base64,
                                "name": file_name
                            }
                        }
                    ],
                    "generation_config": {
                        **param_config,
                        "system_instruction": instruction
                    }
                }
            }
        
        # 获取动态token
        try:
            access_token = get_piaozone_token()
        except Exception as e:
            logger.error(f"Failed to get PiaoZone access token: {e}")
            raise RuntimeError(f"Failed to get PiaoZone access token: {e}")
        
        # 添加access_token到URL参数
        api_url_with_token = f"{self.api_url}?access_token={access_token}"
        
        logger.info(f'Calling PiaoZone API: {self.model_name}')
        logger.info(f'API URL: {api_url_with_token}')
        
        # 创建一个用于日志的请求数据副本，缩短base64内容
        log_request_data = json.loads(json.dumps(request_data))
        if 'data' in log_request_data and 'contents' in log_request_data['data']:
            for content in log_request_data['data']['contents']:
                if 'file' in content and 'data' in content['file']:
                    original_length = len(content['file']['data'])
                    content['file']['data'] = f"<base64_data_length_{original_length}>"
        
        logger.info(f'Request data structure: {json.dumps(log_request_data, ensure_ascii=False, indent=2)}')
        
        # 发送HTTP请求
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "client-platform": "common"
            }
            
            logger.info(f'Request headers: {headers}')
            logger.info(f'Request method: POST')
            
            response = requests.post(
                api_url_with_token,
                json=request_data,
                headers=headers,
                timeout=120  # 2分钟超时
            )
            
            logger.info(f'Response status code: {response.status_code}')
            logger.info(f'Response headers: {dict(response.headers)}')
            
            # 记录响应内容（如果是错误响应）
            if response.status_code >= 400:
                logger.error(f'Error response body: {response.text}')
            
            response.raise_for_status()  # 检查HTTP状态码
            
            # 解析响应
            response_data = response.json()
            logger.debug(f"PiaoZone API response: {response_data}")
            
            # 提取响应内容 - 优先从parsed获取，否则从text获取
            content = None
            
            # 优先尝试获取parsed字段
            if 'data' in response_data and 'parsed' in response_data['data']:
                parsed_data = response_data['data']['parsed']
                if parsed_data is not None:
                    content = json.dumps(parsed_data, ensure_ascii=False)
                    logger.info(f"Got parsed data from PiaoZone API response")
            
            # 如果没有parsed，则尝试获取text内容
            if content is None:
                if ('data' in response_data and 'candidates' in response_data['data'] 
                    and len(response_data['data']['candidates']) > 0):
                    candidate = response_data['data']['candidates'][0]
                    if ('content' in candidate and 'parts' in candidate['content'] 
                        and len(candidate['content']['parts']) > 0):
                        text_content = candidate['content']['parts'][0].get('text', '')
                        if text_content:
                            content = text_content
                            logger.info(f"Got text content from PiaoZone API response")
                
                # 兼容旧格式
                elif 'choices' in response_data and len(response_data['choices']) > 0:
                    content = response_data['choices'][0].get('message', {}).get('content', '')
                elif 'data' in response_data and 'content' in response_data['data']:
                    content = response_data['data']['content']
            
            # 如果还是没有内容，返回整个响应
            if content is None:
                content = json.dumps(response_data, ensure_ascii=False)
                logger.warning(f"Could not extract content from response, returning full response")
            
            logger.info(f"PiaoZone API response content: {content[:200]}...")
            
            # 如果content是字符串且response_mime_type是text/plain，需要提取JSON
            current_mime_type = merged_config.get('response_mime_type', 'application/json')
            if isinstance(content, str) and current_mime_type == 'text/plain':
                json_string = extract_json(content)
                if isinstance(json_string, list) and len(json_string) > 0:
                    json_string = json_string[0]
                else:
                    json_string = content
            else:
                json_string = content
            
            return json_string
            
        except requests.exceptions.RequestException as e:
            logger.error(f"PiaoZone API request failed: {e}")
            raise RuntimeError(f"PiaoZone API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PiaoZone API response: {e}")
            raise RuntimeError(f"Failed to parse PiaoZone API response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in PiaoZone processor: {e}")
            raise RuntimeError(f"Unexpected error in PiaoZone processor: {e}")
    
    def get_model_version(self) -> str:
        return f"piaozone|{self.model_name}"

"""
使用示例：

# 1. 使用默认配置
processor = PiaoZoneProcessor()
result = processor.process_document("invoice.pdf", "Extract invoice data")

# 2. 使用运行时配置
processor = PiaoZoneProcessor()

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

# 3. 使用环境变量配置
# 设置环境变量：
# 方式1：使用静态token（向后兼容）
# export PIAOZONE_ACCESS_TOKEN="your_static_token"
# 
# 方式2：使用动态token获取（推荐）
# export PIAOZONE_CLIENT_ID="Q3V07mngUYcDOGeELsIS"
# export PIAOZONE_CLIENT_SECRET="163e7765d14c4601a26931493ca57634"
# export PIAOZONE_TOKEN_URL="https://api-sit.piaozone.com/base/oauth/token"
# 
# 其他可选配置：
# export PIAOZONE_API_URL="https://api-sit.piaozone.com/ai/knowledge/v1/chat/completions"
# export PIAOZONE_TEMPERATURE="0.1"
# export PIAOZONE_TOKEN_DURATION_HOURS="24"

processor = PiaoZoneProcessor()
result = processor.process_document("invoice.pdf", "Extract invoice data")
"""