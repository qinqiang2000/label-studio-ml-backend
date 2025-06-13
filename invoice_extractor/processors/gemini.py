import os
import logging
import pathlib
from google.genai import types
from google import genai
from invoice_extractor.processors.base import DocumentProcessor
from invoice_extractor.utils import extract_json

logger = logging.getLogger(__name__)

class GeminiProcessor(DocumentProcessor):
    """Gemini-based document processor"""
    
    def __init__(self, model_name: str = "gemini-2.5-flash-preview-04-17"):
        self.client = genai.Client(api_key=os.environ.get("API_KEY"))
        self.model_name = model_name
    
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
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction=[
                types.Part.from_text(text=instruction),
            ],
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        
        logger.info(f'calling genai: {self.model_name}')
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=generate_content_config,
        )
        
        # extract_json returns a list of JSON strings, so we take the first element
        json_string = extract_json(response.text)[0]
        return json_string
    
    def get_model_version(self) -> str:
        return self.model_name 