import os
import sys
import logging
import re
import base64
import tempfile
import pandas as pd
import csv
from pathlib import Path
from typing import List, Dict, Optional
from uuid import uuid4

# Add current directory to Python path to support direct imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.label_interface.objects import PredictionValue
from prompt import prompt, analysis_prompt
import dotenv
from utils import should_use_mock_data
import json
from processors.factory import DocumentProcessorFactory
from processors.mock import MockProcessor

# Gemini imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenAI not available. Install with: pip install google-genai")

# Load .env if present
dotenv.load_dotenv()

logger = logging.getLogger(__name__)

LABEL_STUDIO_ACCESS_TOKEN = os.environ.get("LABEL_STUDIO_ACCESS_TOKEN")
LABEL_STUDIO_HOST = os.environ.get("LABEL_STUDIO_URL")

if os.environ.get('USING_PROXY', '').upper() == 'TRUE':
    print("使用Proxy！")
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
    os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:7891'


class NewModel(LabelStudioMLBase):
    MODEL_DIR = os.environ.get('MODEL_DIR', '.')
    """Custom ML Backend model with pluggable document processors"""

    def setup(self):
        """Configure any parameters of your model here"""
        # Determine processor type from environment or default to gemini
        processor_type = os.environ.get('DOCUMENT_PROCESSOR', 'mock' if should_use_mock_data() else 'gemini')
        
        # Create processor with optional configuration
        processor_config = {}
        if processor_type == 'gemini':
            model_name = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
            processor_config['model_name'] = model_name
        
        self.processor = DocumentProcessorFactory.create_processor(processor_type, **processor_config)
        self.set("model_version", self.processor.get_model_version())
        self.prompt = None

    def analyze_excel(self, excel_content: str, filename: str, context: Optional[Dict] = None, 
                     analysis_type: str = 'evaluation', prompt=None, **kwargs) -> str:
        """
        Analyze Excel file content using Gemini document understanding and return analysis in markdown format
        
        Args:
            excel_content: Base64 encoded Excel file content
            filename: Excel filename for reference
            context: Optional context information
            analysis_type: Type of analysis to perform (default: 'evaluation')
            **kwargs: Additional parameters including:
                - prompt: Custom prompt for analysis
        
        Returns:
            Markdown formatted analysis result from Gemini
        """
        logger.info("=== 接收到的prompt===")
        logger.info(prompt)
        logger.info("=== 请求数据打印完成 ===")

        custom_prompt = prompt
        if custom_prompt:
            logger.info(f"Using custom prompt from kwargs: {custom_prompt[:100]}...")
            base_prompt = custom_prompt
        else:
            logger.info("Using default analysis_prompt")
            base_prompt = analysis_prompt
        
        logger.info(f"Starting Excel analysis with Gemini for file: {filename}")
        
        # Check Gemini availability
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenAI package not available. Install with: pip install google-genai")
        
        # Get environment variables
        api_key = os.environ.get('API_KEY')
        model_name = os.environ.get('ANALYSIS_MODEL', 'gemini-2.5-flash')
        
        if not api_key:
            raise ValueError("API_KEY environment variable is required")
        
        logger.info(f"Using Gemini model: {model_name}")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Decode base64 content
        excel_bytes = base64.b64decode(excel_content)
        logger.info(f"Successfully decoded base64 content, size: {len(excel_bytes)} bytes")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            excel_filepath = temp_path / f"{filename}"
            
            # Save Excel file
            excel_filepath.write_bytes(excel_bytes)
            logger.info(f"Created temporary Excel file: {excel_filepath}")
            
            # Read Excel and convert sheets to CSV
            excel_data = self._read_excel_file(str(excel_filepath))
            csv_files = self._save_sheets_as_csv(excel_data, temp_path, filename)
            logger.info(f"Created {len(csv_files)} CSV files from Excel sheets")
            
            # 打印CSV文件信息
            for i, csv_file in enumerate(csv_files):
                logger.info(f"CSV文件 {i+1}: {csv_file.name} (大小: {csv_file.stat().st_size} bytes)")
            
            # Upload CSV files to Gemini File API
            uploaded_files = []
            for csv_file in csv_files:
                try:
                    uploaded_file = client.files.upload(
                        file=csv_file,
                        config=dict(mime_type='text/csv')
                    )
                    uploaded_files.append(uploaded_file)
                    logger.info(f"Uploaded CSV file to Gemini: {csv_file.name}")
                except Exception as e:
                    logger.error(f"Failed to upload {csv_file.name}: {str(e)}")
                    raise
            
            # Prepare content for Gemini analysis
            contents = uploaded_files.copy()
            
            # Add context information to prompt if provided
            context_info = ""
            if context:
                context_info = f"\n\n**附加上下文信息:**\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            
            # Prepare analysis prompt
            full_prompt = f"""
                    {base_prompt}

                    **待分析文件信息:**
                    - 已处理工作表数量: {len(excel_data)} (仅前2个工作表)
                    - 工作表名称: {list(excel_data.keys())}
                    - CSV文件数量: {len(csv_files)}
                    {context_info}
                    """
            
            contents.append(full_prompt)
            
            # Call Gemini for analysis
            try:
                logger.info("Calling Gemini for document analysis...")
                logger.info(f"Sending prompt to Gemini (first 200 chars): {full_prompt[:200]}...")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                
                analysis_result = response.text
                logger.info("Analysis completed successfully")
                
                # 打印Gemini返回的完整内容
                logger.info("=== GEMINI返回的完整分析结果 ===")
                logger.info(f"返回内容长度: {len(analysis_result)} 字符")
                logger.info("=== 返回内容开始 ===")
                logger.info(analysis_result)
                logger.info("=== 返回内容结束 ===")
                
                return analysis_result
                
            except Exception as e:
                logger.error(f"Gemini analysis failed: {str(e)}")
                raise
            
            finally:
                # Cleanup uploaded files from Gemini
                for uploaded_file in uploaded_files:
                    try:
                        client.files.delete(name=uploaded_file.name)
                        logger.info(f"Cleaned up uploaded file: {uploaded_file.name}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup file {uploaded_file.name}: {cleanup_error}")

    def _read_excel_file(self, filepath: str) -> Dict[str, pd.DataFrame]:
        """
        Read Excel file and return dictionary of sheet data (only first 2 sheets)
        """
        try:
            # Read all sheets first to get sheet names
            all_sheets = pd.read_excel(filepath, sheet_name=None, engine='openpyxl')
            sheet_names = list(all_sheets.keys())
            
            # Only keep first 2 sheets
            excel_data = {}
            sheets_to_process = sheet_names[:2]  # 只取前两个sheet
            
            logger.info(f"Total sheets found: {len(sheet_names)}, processing first {len(sheets_to_process)} sheets")
            logger.info(f"Sheet names: {sheet_names}")
            logger.info(f"Processing sheets: {sheets_to_process}")
            
            for i, sheet_name in enumerate(sheets_to_process):
                df = all_sheets[sheet_name]
                excel_data[sheet_name] = df
                logger.info(f"Sheet '{sheet_name}': {df.shape[0]} rows × {df.shape[1]} columns")
                
                # 打印第一个sheet的内容详情
                if i == 0:  # 第一个sheet
                    logger.info(f"=== 第一个Sheet内容详情 '{sheet_name}' ===")
                    logger.info(f"列名: {list(df.columns)}")
                    
                    # 打印前5行数据（如果有的话）
                    if not df.empty:
                        logger.info(f"前5行数据:")
                        for idx, row in df.head(5).iterrows():
                            logger.info(f"行 {idx}: {dict(row)}")
                    else:
                        logger.info("Sheet为空")
                    
                    # 打印数据类型信息
                    logger.info(f"数据类型:")
                    for col, dtype in df.dtypes.items():
                        logger.info(f"  {col}: {dtype}")
                    
                    # 打印基本统计信息（仅数值列）
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        logger.info(f"数值列统计信息:")
                        for col in numeric_cols:
                            logger.info(f"  {col}: 最小值={df[col].min()}, 最大值={df[col].max()}, 平均值={df[col].mean():.2f}")
                    
                    logger.info(f"=== 第一个Sheet内容详情结束 ===")
            
            return excel_data
            
        except Exception as e:
            logger.error(f"Failed to read Excel file: {str(e)}")
            raise

    def _save_sheets_as_csv(self, excel_data: Dict[str, pd.DataFrame], 
                           temp_path: Path, original_filename: str) -> List[Path]:
        """
        Save each Excel sheet as a separate CSV file (only first 2 sheets)
        
        Args:
            excel_data: Dictionary of sheet name to DataFrame (already limited to first 2 sheets)
            temp_path: Temporary directory path
            original_filename: Original Excel filename for naming
            
        Returns:
            List of CSV file paths
        """
        csv_files = []
        base_name = Path(original_filename).stem
        
        # Process only first 2 sheets (should already be limited by _read_excel_file)
        sheet_items = list(excel_data.items())[:2]
        
        logger.info(f"Converting {len(sheet_items)} sheets to CSV files")
        
        for i, (sheet_name, df) in enumerate(sheet_items):
            # Clean sheet name for filename
            clean_sheet_name = re.sub(r'[^\w\-_.]', '_', sheet_name)
            csv_filename = f"{base_name}_sheet{i+1}_{clean_sheet_name}.csv"
            csv_filepath = temp_path / csv_filename
            
            # Save DataFrame to CSV
            try:
                df.to_csv(csv_filepath, index=False, encoding='utf-8')
                csv_files.append(csv_filepath)
                logger.info(f"Saved sheet {i+1} '{sheet_name}' to {csv_filename} ({df.shape[0]} rows × {df.shape[1]} columns)")
            except Exception as e:
                logger.error(f"Failed to save sheet '{sheet_name}' as CSV: {str(e)}")
                raise
        
        return csv_files

    def _generate_evaluation_analysis(self, excel_data: Dict[str, pd.DataFrame], 
                                    filename: str, context: Optional[Dict] = None) -> str:
        """
        Generate evaluation-type analysis for Excel data (Legacy method - now unused)
        """
        # This method is kept for backward compatibility but not used in new flow
        logger.warning("Legacy _generate_evaluation_analysis called - should use Gemini analysis")
        return "# Legacy analysis method - please use Gemini-powered analysis"

    def _generate_default_analysis(self, excel_data: Dict[str, pd.DataFrame], 
                                  filename: str, context: Optional[Dict] = None) -> str:
        """
        Generate default analysis for Excel data (Legacy method - now unused)
        """
        # This method is kept for backward compatibility but not used in new flow
        logger.warning("Legacy _generate_default_analysis called - should use Gemini analysis")
        return "# Legacy analysis method - please use Gemini-powered analysis"

    def extract_src_from_embed(self, embed_html):
        """Extract src attribute value from HTML embed tag"""
        # 使用正则表达式提取src属性的值，支持单引号和双引号
        pattern = r"src=['\"]([^'\"]*)['\"]"
        match = re.search(pattern, embed_html)
        if match:
            return match.group(1)
        return None

    def doc_understanding(self, file_path, runtime_config: Optional[dict] = None):
        # 检查是否使用仿真数据 - 这个检查现在在processor内部处理
        if should_use_mock_data() and not isinstance(self.processor, MockProcessor):
            # 如果环境要求使用mock但当前不是mock processor，临时切换
            logger.info('Environment requires mock data, switching to mock processor')
            mock_processor = DocumentProcessorFactory.create_processor('mock')
            json_string = mock_processor.process_document(file_path, "")
        else:
            # 使用配置的processor
            instruction = self.prompt if self.prompt else prompt
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
        print(f'get_first_tag_occurence: {from_name}, {to_name}, {value}')
        
        # 提取src属性的值
        embed_html = task['data'][value]
        url = self.extract_src_from_embed(embed_html)
        print(f'extracted src: {url} from: {embed_html} ')
        
        if not url:
            print('Could not extract src from embed tag')
            return PredictionValue(result=[])
        
        # you need to set env vars LABEL_STUDIO_URL and LABEL_STUDIO_API_KEY
        filepath = self.get_local_path(url, task_id=task['id'])
        print(f'Local path: {filepath}')
        
        text = self.doc_understanding(filepath, runtime_config)
        
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
            :return model_response
                ModelResponse(predictions=predictions) with
                predictions: [Predictions array in JSON format](https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks)
        """
        # 从kwargs中提取参数
        self.prompt = kwargs.get('prompt') if kwargs else None
        runtime_config = kwargs.get('runtime_config') if kwargs else None
        
        print(f"Received prompt: {self.prompt}")
        print(f"Received runtime_config: {runtime_config}")
        
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
        print(f"MODEL: Created ModelResponse with version: {self.model_version}")
        
        for i, task in enumerate(tasks):
            try:
                print(f"Processing task {i+1}/{len(tasks)}, task_id: {task.get('id', 'unknown')}")
                prediction = self.predict_single(task, runtime_config)
                if prediction:
                    predictions.append(prediction)
                    print(f"Successfully processed task {i+1}/{len(tasks)}")
                else:
                    print(f"Warning: Task {i+1}/{len(tasks)} returned empty prediction")
                    # 空预测也算作一种错误
                    model_response.add_error(
                        task_index=i,
                        task_id=task.get('id', 'unknown'),
                        error_message="Model returned empty prediction",
                        error_type="empty_prediction"
                    )
            except Exception as e:
                try:
                    task_id = task.get('id', 'unknown') if isinstance(task, dict) else 'unknown'
                    error_str = str(e) if e else 'Unknown error'
                    error_msg = f"Failed to process task {i+1}/{len(tasks)} (id: {task_id}): {error_str}"
                    print(error_msg)
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
                    model_response.add_error(
                        task_index=i,
                        task_id=task_id,
                        error_message=error_str,
                        error_type=error_type
                    )
                    print(f"MODEL: Added error to response - type: {error_type}, task_id: {task_id}")
                    
                except Exception as log_error:
                    # 如果连异常处理都失败了，至少要记录基本信息
                    print(f"Critical error: Failed to log error for task {i+1}/{len(tasks)}: {log_error}")
                    try:
                        model_response.add_error(
                            task_index=i,
                            task_id='error_in_error_handling',
                            error_message=f'Logging failed: {log_error}',
                            error_type="critical_error"
                        )
                    except:
                        # 最后的保险措施
                        print(f"Fatal error: Cannot even add error info for task {i+1}")
                # 继续处理下一个task，不中断整个批处理
                continue
        
        # 设置预测结果
        model_response.predictions = predictions
        print(f"MODEL: Set predictions to response, count: {len(predictions)}")
        
        # 记录处理结果统计
        total_tasks = len(tasks)
        successful_tasks = len(predictions)
        error_count = len(model_response.errors) if model_response.has_errors() else 0
        
        print(f"\nBatch processing completed:")
        print(f"Total tasks: {total_tasks}")
        print(f"Successful: {successful_tasks}")
        print(f"Failed: {error_count}")

        
        if model_response.has_errors():
            print(f"Error details:")
            for error in model_response.errors:
                print(f"  - Task {error['task_index']+1} (id: {error['task_id']}): [{error['error_type']}] {error['error_message']}")
        
        # 返回包含预测结果和错误信息的响应
        print(f"MODEL: Returning response - predictions: {len(model_response.predictions)}, errors: {len(model_response.errors) if model_response.has_errors() else 0}")
        return model_response
    
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
        print(f'Old data: {old_data}')
        print(f'Old model version: {old_model_version}')

        # store new data to the cache
        self.set('my_data', 'my_new_data_value')
        self.set('model_version', 'my_new_model_version')
        print(f'New data: {self.get("my_data")}')
        print(f'New model version: {self.get("model_version")}')

        print('fit() completed successfully.')

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