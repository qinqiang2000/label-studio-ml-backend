import os
import sys
import logging
import re

from typing import List, Dict, Optional
from uuid import uuid4

# Add current directory to Python path to support direct imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.label_interface.objects import PredictionValue
from prompt import prompt
import dotenv
from utils import should_use_mock_data, format_prompt_template
import json
from processors.factory import DocumentProcessorFactory
from processors.mock import MockProcessor
from analyzers import ExcelAnalyzer

logger = logging.getLogger(__name__)




# Load .env if present
dotenv.load_dotenv()

LABEL_STUDIO_ACCESS_TOKEN = os.environ.get("LABEL_STUDIO_ACCESS_TOKEN")
LABEL_STUDIO_HOST = os.environ.get("LABEL_STUDIO_URL")

if os.environ.get('USING_PROXY', '').upper() == 'TRUE':
    logger.info("使用Proxy！")
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:7891'


class NewModel(LabelStudioMLBase):
    MODEL_DIR = os.environ.get('MODEL_DIR', '.')
    """Custom ML Backend model with pluggable document processors"""

    def _safe_add_error(self, model_response, task_index: int, task_id: str, error_message: str, error_type: str = "processing_error"):
        """
        Safely add error to model response with version compatibility
        """
        if hasattr(model_response, 'add_error'):
            try:
                model_response.add_error(
                    task_index=task_index,
                    task_id=task_id,
                    error_message=error_message,
                    error_type=error_type
                )
            except Exception as e:
                logger.warning(f"Failed to add error to model response: {e}")
        else:
            # Fallback for older versions - just log the error
            logger.error(f"Task {task_index+1} (id: {task_id}) error [{error_type}]: {error_message}")

    def _safe_has_errors(self, model_response) -> bool:
        """
        Safely check if model response has errors with version compatibility
        """
        if hasattr(model_response, 'has_errors'):
            try:
                return model_response.has_errors()
            except Exception:
                pass

        # Fallback: check errors attribute directly
        if hasattr(model_response, 'errors'):
            return model_response.errors is not None and len(model_response.errors) > 0

        return False

    def _safe_get_error_count(self, model_response) -> int:
        """
        Safely get error count with version compatibility
        """
        if self._safe_has_errors(model_response):
            errors = getattr(model_response, 'errors', [])
            return len(errors) if errors else 0
        return 0

    def setup(self):
        """Configure any parameters of your model here"""
        
        # 尝试使用配置管理器获取默认配置
        try:
            from config.manager import config_manager
            
            # 确定处理器类型
            if should_use_mock_data():
                processor_type = 'mock'
            else:
                # 优先使用环境变量，否则使用配置文件中的默认值
                processor_type = os.environ.get('DOCUMENT_PROCESSOR')
                if not processor_type:
                    processor_type = config_manager._config.get('defaults', {}).get('processor', 'gemini')
            
            logger.info(f"Using processor type: {processor_type}")
            
            # 获取处理器配置
            processor_config = {}
            if processor_type in ['gemini', 'openai']:
                # 从配置管理器获取默认模型
                default_model = config_manager.get_default_model(processor_type)
                if default_model:
                    processor_config['model_name'] = default_model
                    logger.info(f"Using model from config: {default_model}")
            
        except ImportError:
            logger.warning("Config manager not available, using fallback setup")
            # 备用配置方法
            processor_type = os.environ.get('DOCUMENT_PROCESSOR', 'mock' if should_use_mock_data() else 'gemini')
            processor_config = {}
            if processor_type == 'gemini':
                model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
                processor_config['model_name'] = model_name
                
        except Exception as e:
            logger.error(f"Failed to use config manager in setup: {e}")
            # 备用配置方法
            processor_type = os.environ.get('DOCUMENT_PROCESSOR', 'mock' if should_use_mock_data() else 'gemini')
            processor_config = {}
            if processor_type == 'gemini':
                model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
                processor_config['model_name'] = model_name
        
        # 创建处理器实例
        self.processor = DocumentProcessorFactory.create_processor(processor_type, **processor_config)
        self.set("model_version", self.processor.get_model_version())
        self.prompt = None
        
        # 创建Excel分析器实例
        self.excel_analyzer = ExcelAnalyzer()

    def analyze_excel(self, excel_content: str, filename: str, context: Optional[Dict] = None, 
                     analysis_type: str = 'evaluation', prompt=None, **kwargs) -> str:
        """
        Analyze Excel file content using Gemini document understanding and return analysis in markdown format
        
        Args:
            excel_content: Base64 encoded Excel file content
            filename: Excel filename for reference
            context: Optional context information
            analysis_type: Type of analysis to perform (default: 'evaluation')
            prompt: Custom prompt for analysis
            **kwargs: Additional parameters
        
        Returns:
            Markdown formatted analysis result from Gemini
        """
        logger.info(f"Delegating Excel analysis to ExcelAnalyzer for file: {filename}")
        
        # Delegate to the Excel analyzer
        return self.excel_analyzer.analyze(
            excel_content=excel_content,
            filename=filename,
            context=context,
            analysis_type=analysis_type,
            prompt=prompt,
            **kwargs
        )



    def extract_src_from_embed(self, embed_html):
        """Extract src attribute value from HTML embed tag"""
        # 使用正则表达式提取src属性的值，支持单引号和双引号
        pattern = r"src=['\"]([^'\"]*)['\"]"
        match = re.search(pattern, embed_html)
        if match:
            return match.group(1)
        return None

    def doc_understanding(self, file_path, runtime_config: Optional[dict] = None, formatted_prompt: Optional[str] = None):
        # 检查是否使用仿真数据 - 这个检查现在在processor内部处理
        if should_use_mock_data() and not isinstance(self.processor, MockProcessor):
            # 如果环境要求使用mock但当前不是mock processor，临时切换
            logger.info('Environment requires mock data, switching to mock processor')
            mock_processor = DocumentProcessorFactory.create_processor('mock')
            json_string = mock_processor.process_document(file_path, "")
        else:
            # 使用配置的processor
            # 优先使用格式化后的prompt，然后是self.prompt，最后是默认prompt
            instruction = formatted_prompt if formatted_prompt else (self.prompt if self.prompt else prompt)
            # 传递runtime_config给processor
            if hasattr(self.processor, 'process_document'):
                # 检查processor是否支持runtime_config参数
                import inspect
                sig = inspect.signature(self.processor.process_document)
                if 'runtime_config' in sig.parameters:
                    json_string = self.processor.process_document(file_path, instruction, runtime_config)
                else:
                    json_string = self.processor.process_document(file_path, instruction)
                    if runtime_config:
                        logger.warning(f'Processor {type(self.processor).__name__} does not support runtime_config, ignoring: {runtime_config}')
            else:
                json_string = self.processor.process_document(file_path, instruction)

        text = self._post_process_ret(json_string, file_path)
        return text 
                 
    def _post_process_ret(self, json_string: str, file_path: str) -> str:
        """
        Post-processes the extracted JSON text:
        1. Parses the JSON string into a Python object.
        2. Forces the 'page' field to [1] for image files.
        3. Converts the Python object back to a JSON string.
        """
        try:
            text = json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error(f'Failed to decode JSON from response: {json_string}, Error: {e}')
            raise ValueError(f"Invalid JSON received from model: {json_string}") from e

        # Force page field to [1] for image files
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            logger.info('Processing an image file, forcing "page" field to [1] for all objects.')
            # Ensure text is a list before iterating
            if isinstance(text, list):
                for item in text:
                    if isinstance(item, dict):
                        item['page'] = [1]
            else:
                # This case should ideally not happen if the model consistently returns a list of objects
                logger.warning(f"Expected parsed text to be a list but got {type(text)}. Cannot force 'page' field.")

        # Convert the Python object back to a JSON string before returning
        try:
            text = json.dumps(text, ensure_ascii=False)
            logger.info("Converted text back to JSON string.")
        except TypeError as e:
            logger.error(f"Failed to convert text object to JSON string: {text}, Error: {e}")
            raise ValueError("Failed to serialize response to JSON") from e

        return text

    def predict_single(self, task, runtime_config: Optional[dict] = None):
        # extract task metadata: labels, from_name, to_name and other
        from_name, to_name, value = self.label_interface.get_first_tag_occurence(
            'TextArea',
            'HyperText'
        )
        logger.info(f'get_first_tag_occurence: {from_name}, {to_name}, {value}')

        # 提取src属性的值
        embed_html = task['data'][value]
        url = self.extract_src_from_embed(embed_html)
        logger.info(f'extracted src: {url} from: {embed_html} ')

        if not url:
            logger.error('Could not extract src from embed tag')
            return PredictionValue(result=[])

        # you need to set env vars LABEL_STUDIO_URL and LABEL_STUDIO_API_KEY
        filepath = self.get_local_path(url, task_id=task['id'])
        logger.info(f'Local path: {filepath}')

        # 格式化prompt模板，使用task['data']中的值替换占位符
        formatted_prompt = None
        if self.prompt:
            task_data = task.get('data', {})
            formatted_prompt = format_prompt_template(self.prompt, task_data)
            logger.debug(f'Formatted prompt: {formatted_prompt}')
            if formatted_prompt != self.prompt:
                logger.debug(f'Original prompt: {self.prompt}')

        text = self.doc_understanding(filepath, runtime_config, formatted_prompt)

        result = {
            "id": str(uuid4())[:8],
            "from_name": from_name,
            "to_name": to_name,
            "type": "textarea",
            'origin': 'manual',
            "value":  {
                "text": [
                    text
                ]
            }}

        return PredictionValue(result=[result], score=0.9, model_version=str(self.model_version))
    
    def predict(self, tasks: List[Dict], context: Optional[Dict] = None, **kwargs) -> ModelResponse:
        """ Write your inference logic here
            :param tasks: [Label Studio tasks in JSON format](https://labelstud.io/guide/task_format.html)
            :param context: [Label Studio context in JSON format](https://labelstud.io/guide/ml_create#Implement-prediction-logic)
            :param kwargs: Additional parameters including:
                - prompt: Custom prompt for processing
                - runtime_config: Runtime configuration for AI model (temperature, response_schema, response_mime_type, etc.)
                - model_version: Model version to use for prediction (format: "processor_type|model_name" or just model_name)
            :return model_response
                ModelResponse(predictions=predictions) with
                predictions: [Predictions array in JSON format](https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks)
        """
        # 从kwargs中提取参数
        self.prompt = kwargs.get('prompt') if kwargs else None
        runtime_config = kwargs.get('runtime_config') if kwargs else None
        model_version = kwargs.get('model_version') if kwargs else None

        logger.info(f"Received prompt: {self.prompt}")
        logger.info(f"Received runtime_config: {runtime_config}")
        logger.info(f"Received model_version: {model_version}")
        
        # 如果指定了model_version，切换处理器
        original_processor = None
        original_model_version = self.model_version
        
        if model_version and model_version.strip() != "":
            try:
                original_processor = self.processor
                processor_type, model_name = self._parse_model_version(model_version)
                
                if processor_type and model_name:
                    # 创建新的处理器实例
                    processor_config = {}
                    # 为所有处理器类型设置 model_name 参数
                    processor_config['model_name'] = model_name
                    
                    self.processor = DocumentProcessorFactory.create_processor(processor_type, **processor_config)
                    self.set("model_version", self.processor.get_model_version())
                    logger.info(f"Switched to processor: {processor_type} with model: {model_name}")
                    logger.info(f"MODEL: Switched to {processor_type}|{model_name}")
                else:
                    logger.warning(f"Failed to parse model_version '{model_version}', using default processor")
                    
            except Exception as e:
                logger.error(f"Failed to switch processor for model_version '{model_version}': {e}, using default")
                logger.error(f"MODEL: Error switching processor: {e}")
                # 如果切换失败，恢复原始处理器
                if original_processor:
                    self.processor = original_processor
        
        # 验证runtime_config格式
        if runtime_config is not None:
            if not isinstance(runtime_config, dict):
                logger.warning(f"runtime_config should be a dict, got {type(runtime_config)}, ignoring")
                runtime_config = None
            else:
                # 记录收到的配置参数
                supported_params = ['temperature', 'response_schema', 'response_mime_type', 'max_output_tokens', 
                                  'top_p', 'top_k', 'seed', 'candidate_count', 'stop_sequences', 
                                  'presence_penalty', 'frequency_penalty', 'response_modalities', 'thinking_config']
                received_params = list(runtime_config.keys())
                logger.info(f"Received runtime_config parameters: {received_params}")
                
                # 警告未知参数
                unknown_params = [p for p in received_params if p not in supported_params]
                if unknown_params:
                    logger.warning(f"Unknown runtime_config parameters (will be ignored): {unknown_params}")
        
        predictions = []
        
        # 创建ModelResponse对象，用于统一管理预测结果和错误信息
        model_response = ModelResponse(predictions=[], model_version=str(self.model_version))
        logger.info(f"MODEL: Created ModelResponse with version: {self.model_version}")
        
        for i, task in enumerate(tasks):
            try:
                logger.info(f"Processing task {i+1}/{len(tasks)}, task_id: {task.get('id', 'unknown')}")
                prediction = self.predict_single(task, runtime_config)
                if prediction:
                    predictions.append(prediction)
                    logger.info(f"Successfully processed task {i+1}/{len(tasks)}")
                else:
                    logger.warning(f"Task {i+1}/{len(tasks)} returned empty prediction")
                    # 空预测也算作一种错误
                    self._safe_add_error(
                        model_response, i, task.get('id', 'unknown'),
                        "Model returned empty prediction", "empty_prediction"
                    )
            except Exception as e:
                try:
                    task_id = task.get('id', 'unknown') if isinstance(task, dict) else 'unknown'
                    error_str = str(e) if e else 'Unknown error'
                    error_msg = f"Failed to process task {i+1}/{len(tasks)} (id: {task_id}): {error_str}"
                    logger.error(error_msg)
                    logger.error(error_msg, exc_info=True)
                    
                    # 判断错误类型
                    error_type = "processing_error"
                    if any(keyword in error_str.lower() for keyword in ['timeout', '超时', 'timed out']):
                        error_type = "timeout_error"
                    elif any(keyword in error_str.lower() for keyword in ['region', '地区', 'location', 'country']):
                        error_type = "region_not_supported"
                    elif any(keyword in error_str.lower() for keyword in ['api', 'key', '密钥', 'auth']):
                        error_type = "authentication_error"
                    elif any(keyword in error_str.lower() for keyword in ['network', '网络', 'connection']):
                        error_type = "network_error"
                    elif any(keyword in error_str.lower() for keyword in ['runtime_config', 'config', 'parameter']):
                        error_type = "config_error"
                    
                    # 将错误信息添加到响应中
                    self._safe_add_error(model_response, i, task_id, error_str, error_type)
                    logger.info(f"MODEL: Added error to response - type: {error_type}, task_id: {task_id}")
                    
                except Exception as log_error:
                    # 如果连异常处理都失败了，至少要记录基本信息
                    logger.critical(f"Critical error: Failed to log error for task {i+1}/{len(tasks)}: {log_error}")
                    try:
                        self._safe_add_error(
                            model_response, i, 'error_in_error_handling',
                            f'Logging failed: {log_error}', "critical_error"
                        )
                    except:
                        # 最后的保险措施
                        logger.critical(f"Fatal error: Cannot even add error info for task {i+1}")
                # 继续处理下一个task，不中断整个批处理
                continue
        
        # 设置预测结果
        model_response.predictions = predictions
        logger.info(f"MODEL: Set predictions to response, count: {len(predictions)}")
        
        # 记录处理结果统计
        total_tasks = len(tasks)
        successful_tasks = len(predictions)
        error_count = self._safe_get_error_count(model_response)
        
        logger.info(f"Batch processing completed:")
        logger.info(f"Total tasks: {total_tasks}")
        logger.info(f"Successful: {successful_tasks}")
        logger.info(f"Failed: {error_count}")


        if self._safe_has_errors(model_response):
            logger.info(f"Error details:")
            errors = getattr(model_response, 'errors', [])
            for error in errors:
                logger.info(f"  - Task {error['task_index']+1} (id: {error['task_id']}): [{error['error_type']}] {error['error_message']}")
        
        # 恢复原始处理器（如果进行了切换）
        if original_processor:
            try:
                self.processor = original_processor
                self.set("model_version", original_model_version)
                logger.info("Restored original processor after prediction")
                logger.info("MODEL: Restored original processor")
            except Exception as e:
                logger.error(f"Failed to restore original processor: {e}")
        
        # 返回包含预测结果和错误信息的响应
        error_count_for_log = self._safe_get_error_count(model_response)
        logger.info(f"MODEL: Returning response - predictions: {len(model_response.predictions)}, errors: {error_count_for_log}")
        return model_response
    
    def _parse_model_version(self, model_version: str) -> tuple:
        """
        解析model_version字符串，返回(processor_type, model_name)
        
        Args:
            model_version: 模型版本字符串，格式可以是：
                - "processor_type|model_name" (如: "gemini|gemini-2.5-flash")
                - "model_name" (如: "gemini-2.5-flash"，默认为gemini处理器)
        
        Returns:
            tuple: (processor_type, model_name) 或 (None, None) 如果解析失败
        """
        try:
            # 首先尝试使用配置管理器验证
            try:
                from config.manager import config_manager
                result = config_manager.validate_model_version(model_version)
                if result != (None, None):
                    return result
                # 如果配置管理器返回 None，继续使用备用方法
                
            except ImportError:
                logger.warning("Config manager not available, using fallback parsing")
                
            except Exception as e:
                logger.error(f"Failed to validate model version with config manager: {e}")
            
            # 备用解析方法
            model_version = model_version.strip()
            if '|' in model_version:
                parts = model_version.split('|', 1)
                processor_type = parts[0].strip()
                model_name = parts[1].strip()
                
                # 验证处理器类型是否可用
                available_processors = DocumentProcessorFactory.get_available_processors()
                if processor_type not in available_processors:
                    logger.error(f"Unknown processor type: {processor_type}. Available: {available_processors}")
                    return None, None
                
                return processor_type, model_name
            else:
                # 如果没有分隔符，默认假设是gemini模型名称
                model_name = model_version
                if model_name:
                    return 'gemini', model_name
                else:
                    return None, None
                    
        except Exception as e:
            logger.error(f"Failed to parse model_version '{model_version}': {e}")
            return None, None
    
    def get_versions(self):
        """
        获取可用的处理器和模型版本
        
        Returns:
            dict: 包含可用版本信息的字典
        """
        try:
            # 尝试使用配置管理器获取版本信息
            try:
                from config.manager import config_manager
                available_versions = config_manager.get_all_versions()
                logger.info(f"Retrieved {len(available_versions)} versions from config manager")
                
            except ImportError:
                logger.warning("Config manager not available, using fallback method")
                available_versions = self._get_fallback_versions()
                
            except Exception as e:
                logger.error(f"Failed to get versions from config manager: {e}")
                available_versions = self._get_fallback_versions()
            
            # 获取当前使用的版本信息
            current_processor_type = None
            current_model_name = None
            
            # 尝试从当前处理器获取信息
            if hasattr(self.processor, '__class__'):
                processor_class_name = self.processor.__class__.__name__.lower()
                if 'gemini' in processor_class_name:
                    current_processor_type = 'gemini'
                elif 'openai' in processor_class_name:
                    current_processor_type = 'openai'
                elif 'mock' in processor_class_name:
                    current_processor_type = 'mock'
            
            if hasattr(self.processor, 'get_model_version'):
                current_model_name = self.processor.get_model_version()
            
            result = {
                "versions": available_versions,
                "current_version": {
                    "processor_type": current_processor_type,
                    "model_name": current_model_name,
                    "version_string": f"{current_processor_type}|{current_model_name}" if current_processor_type and current_model_name else str(self.model_version)
                },
                "total_count": len(available_versions)
            }
            
            logger.info(f"Retrieved {len(available_versions)} available model versions")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get versions: {e}")
            return {
                "versions": [],
                "current_version": {"model_name": str(self.model_version)},
                "total_count": 0,
                "error": str(e)
            }
    
    def _get_fallback_versions(self):
        """
        当配置管理器不可用时的备用版本获取方法
        
        Returns:
            List of version dictionaries
        """
        available_versions = []
        
        # Gemini处理器的可用模型
        gemini_models = [
            {
                "model_name": "gemini-2.5-flash-preview-04-17", 
                "description": "Gemini 2.5 Flash Preview (tested)"
            },
            {
                "model_name": "gemini-2.5-flash-lite-preview-06-17",
                "description": "Gemini 2.5 flash (fastest and cheapest)"
            }
        ]
        
        for model_info in gemini_models:
            available_versions.append({
                "processor_type": "gemini",
                "model_name": model_info["model_name"],
                "version_string": f"gemini|{model_info['model_name']}",
                "description": model_info["description"],
                "is_default": model_info["model_name"] == "gemini-2.5-flash-preview-04-17"
            })
        
        # OpenAI处理器的可用模型（如果可用）
        from processors.factory import OPENAI_AVAILABLE
        if OPENAI_AVAILABLE:
            openai_models = [
                {
                    "model_name": "gpt-4o",
                    "description": "OpenAI GPT-4o (Vision + Text)"
                },
                {
                    "model_name": "gpt-4.1",
                    "description": "OpenAI GPT-4.1 (Stable)"
                }
            ]
            
            for model_info in openai_models:
                available_versions.append({
                    "processor_type": "openai",
                    "model_name": model_info["model_name"],
                    "version_string": f"openai|{model_info['model_name']}",
                    "description": model_info["description"],
                    "is_default": model_info["model_name"] == "gpt-4.1"
                })
        
        # Mock处理器（用于测试）
        available_versions.append({
            "processor_type": "mock",
            "model_name": "mock-v1.0",
            "version_string": "mock|mock-v1.0",
            "description": "Mock processor for testing",
            "is_default": False
        })
        
        return available_versions
    
    def fit(self, event, data, **kwargs):
        """
        This method is called each time an annotation is created or updated
        You can run your logic here to update the model and persist it to the cache
        It is not recommended to perform long-running operations here, as it will block the main thread
        Instead, consider running a separate process or a thread (like RQ worker) to perform the training
        :param event: event type can be ('ANNOTATION_CREATED', 'ANNOTATION_UPDATED', 'START_TRAINING')
        :param data: the payload received from the event (check [Webhook event reference](https://labelstud.io/guide/webhook_reference.html))
        """

        # use cache to retrieve the data from the previous fit() runs
        old_data = self.get('my_data')
        old_model_version = self.get('model_version')
        logger.debug(f'Old data: {old_data}')
        logger.debug(f'Old model version: {old_model_version}')

        # store new data to the cache
        self.set('my_data', 'my_new_data_value')
        self.set('model_version', 'my_new_model_version')
        logger.debug(f'New data: {self.get("my_data")}')
        logger.debug(f'New model version: {self.get("model_version")}')

        logger.info('fit() completed successfully.')

    def load_image(self, img_path_url, task_id):
        # cache_dir = os.path.join(self.MODEL_DIR, '.file-cache')
        # os.makedirs(cache_dir, exist_ok=True)
        # logger.info(f'Using cache dir: {cache_dir}')
        filepath = self.get_local_path(
            img_path_url,
            # cache_dir=cache_dir,
            ls_access_token=LABEL_STUDIO_ACCESS_TOKEN,
            ls_host=LABEL_STUDIO_HOST,
            task_id=task_id
        )
        
        return filepath