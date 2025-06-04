import json
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

logger = logging.getLogger(__name__)

LABEL_STUDIO_ACCESS_TOKEN = os.environ.get("LABEL_STUDIO_ACCESS_TOKEN")
LABEL_STUDIO_HOST = os.environ.get("LABEL_STUDIO_HOST")

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

def extract_json(text) -> List[dict]:
    """Extracts JSON content from a string where JSON is embedded between \`\`\`json and \`\`\` tags.

    Parameters:
        text (str): The text containing the JSON content.

    Returns:
        list: A list of extracted JSON strings.
    """
    # Define the regular expression pattern to match JSON blocks
    pattern = r"\`\`\`json(.*?)\`\`\`"

    # Find all non-overlapping matches of the pattern in the string
    matches = re.findall(pattern, text, re.DOTALL)

    # Return the list of matched JSON strings, stripping any leading or trailing whitespace
    try:
        return [match.strip() for match in matches]
    except Exception:
        raise ValueError(f"Failed to parse: {text}")
    

class NewModel(LabelStudioMLBase):
    MODEL_DIR = os.environ.get('MODEL_DIR', '.')
    """Custom ML Backend model
    """

    def setup(self):
        """Configure any parameters of your model here
        """
        self.set("model_version", "0.1")

    def extract_src_from_embed(self, embed_html):
        """Extract src attribute value from HTML embed tag"""
        # 使用正则表达式提取src属性的值，支持单引号和双引号
        pattern = r"src=['\"]([^'\"]*)['\"]"
        match = re.search(pattern, embed_html)
        if match:
            return match.group(1)
        return None

    def generate(self, file_path):
        contents = [
            types.Part.from_bytes(
                data=pathlib.Path(file_path).read_bytes(),
                mime_type="application/pdf" if file_path.lower().endswith('.pdf') else (
                    "image/png" if file_path.lower().endswith('.png') else
                    "image/jpeg" if file_path.lower().endswith(('.jpg', '.jpeg')) else
                    "application/octet-stream"
                ),
            )]

        instruction = multi_page_prompt if file_path.lower().endswith('.pdf') and is_multi_page_pdf(file_path) else prompt
        
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
        
        text = extract_json(response.text)[0]   
        logger.info(f'response: {text}')
    
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
        
        text = self.generate(filepath)
        
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
        print(f'''\
        Run prediction on {tasks}
        Received context: {context}
        Project ID: {self.project_id}
        Label config: {self.label_config}
        Parsed JSON Label config: {self.parsed_label_config}
        Extra params: {self.extra_params} \n\n''')
        
        predictions = []
        for task in tasks:            
            prediction = self.predict_single(task)
            if prediction:
                predictions.append(prediction)
        
        # example for simple classification
        return ModelResponse(predictions=predictions)
    
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