import os
import logging
import re
import pathlib
from typing import List, Dict, Optional
from uuid import uuid4
from label_studio_ml.model import LabelStudioMLBase
from label_studio_ml.response import ModelResponse
from label_studio_sdk.label_interface.objects import PredictionValue
from google.genai import types
from google import genai
from prompt import prompt, multi_page_prompt
import PyPDF2
import dotenv
from utils import extract_json, get_mock_invoice_data, should_use_mock_data
import json

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


client = genai.Client(api_key=os.environ.get("API_KEY"))
# model = "gemini-2.5-flash-preview-05-20"
model = "gemini-2.5-flash-preview-04-17"

def is_multi_page_pdf(file_path):
    """
    判断一个文件是否为多页PDF。
    :param file_path: PDF文件路径
    :return: 如果是PDF且页数大于1，返回True，否则返回False
    """
    if not file_path.lower().endswith('.pdf'):
        return False
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return len(reader.pages) > 1
    except Exception as e:
        raise Exception(f"Error reading PDF: {file_path}, {e}")


class NewModel(LabelStudioMLBase):
    MODEL_DIR = os.environ.get('MODEL_DIR', '.')
    """Custom ML Backend model
    """

    def setup(self):
        """Configure any parameters of your model here
        """
        self.set("model_version", "gemini-2.5-flash-preview-04-17")
        self.prompt=None

    def extract_src_from_embed(self, embed_html):
        """Extract src attribute value from HTML embed tag"""
        # 使用正则表达式提取src属性的值，支持单引号和双引号
        pattern = r"src=['\"]([^'\"]*)['\"]"
        match = re.search(pattern, embed_html)
        if match:
            return match.group(1)
        return None

    def img_understanding(self, file_path):
        # 检查是否使用仿真数据
        if should_use_mock_data():
            logger.info('Using mock data for img_understanding')
            return get_mock_invoice_data()

        contents = [
            types.Part.from_bytes(
                data=pathlib.Path(file_path).read_bytes(),
                mime_type="application/pdf" if file_path.lower().endswith('.pdf') else (
                    "image/png" if file_path.lower().endswith('.png') else
                    "image/jpeg" if file_path.lower().endswith(('.jpg', '.jpeg')) else
                    "application/octet-stream"
                ),
            )]

        # instruction = multi_page_prompt if file_path.lower().endswith('.pdf') and is_multi_page_pdf(file_path) else prompt
        instruction = self.prompt if self.prompt else prompt
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=instruction),
            ],
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        
        logger.info(f'calling genai: {model}')
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        # extract_json returns a list of JSON strings, so we take the first element
        json_string = extract_json(response.text)[0]
        text = self._post_process_ret(json_string, file_path)

        logger.info(f'response: {text}')
    
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
            logger.info(f'Successfully parsed JSON response: {text}')
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

    def predict_single(self, task):
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
        
        text = self.img_understanding(filepath)
        
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
            :return model_response
                ModelResponse(predictions=predictions) with
                predictions: [Predictions array in JSON format](https://labelstud.io/guide/export.html#Label-Studio-JSON-format-of-annotated-tasks)
        """
        # print(f'''\
        # Run prediction on {tasks}
        # Received context: {context}
        # Project ID: {self.project_id}
        # Label config: {self.label_config}
        # Parsed JSON Label config: {self.parsed_label_config}
        # Extra params: {self.extra_params} \n\n''')
        self.prompt = kwargs.get('prompt') if kwargs else None
        print(f"Received prompt: {self.prompt}")
        
        predictions = []
        
        # 创建ModelResponse对象，用于统一管理预测结果和错误信息
        model_response = ModelResponse(predictions=[], model_version=str(self.model_version))
        print(f"MODEL: Created ModelResponse with version: {self.model_version}")
        
        for i, task in enumerate(tasks):
            try:
                print(f"Processing task {i+1}/{len(tasks)}, task_id: {task.get('id', 'unknown')}")
                prediction = self.predict_single(task)
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