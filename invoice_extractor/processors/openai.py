"""
OpenAI Document Processor for OpenAI models
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from .base import DocumentProcessor

logger = logging.getLogger(__name__)

# Check OpenAI availability
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available. Install with: pip install openai")


class OpenAIDocumentProcessor(DocumentProcessor):
    """OpenAI Document Processor"""
    
    def __init__(self, model_name: str = "gpt-4.1", **kwargs):
        """
        Initialize OpenAI processor
        
        Args:
            model_name: OpenAI model name (default: gpt-4.1)
            **kwargs: Additional configuration
        """
        super().__init__()
        self.model_name = model_name
        self.client = None
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE:
            try:
                # OpenAI API key from environment
                api_key = os.environ.get('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable is required")
                
                self.client = OpenAI(api_key=api_key)
                logger.info(f"OpenAI processor initialized with model: {model_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise
        else:
            raise ImportError("OpenAI package is not available")
    
    def get_model_version(self) -> str:
        """Get current model version"""
        return f"openai|{self.model_name}"
    
    def _encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def _is_image_file(self, filepath: str) -> bool:
        """
        Check if file is an image based on extension
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file is an image
        """
        image_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".gif")
        return filepath.lower().endswith(image_extensions)
    
    def _process_image_file(self, filepath: str, prompt: str, runtime_config: Optional[Dict] = None) -> str:
        """
        Process image file using OpenAI vision
        
        Args:
            filepath: Path to image file
            prompt: Processing prompt
            runtime_config: Runtime configuration
            
        Returns:
            Extracted text content
        """
        try:
            # Get configuration
            temperature = runtime_config.get('temperature', 0) if runtime_config else 0
            max_tokens = runtime_config.get('max_output_tokens', 30000) if runtime_config else 30000
            
            # Encode image
            base64_image = self._encode_image(filepath)
            
            # Create OpenAI request for image
            response = self.client.responses.create(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{base64_image}",
                            }
                        ],
                    }
                ],
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            return response.output_text
            
        except Exception as e:
            logger.error(f"Failed to process image file {filepath}: {e}")
            raise
    
    def _process_document_file(self, filepath: str, prompt: str, runtime_config: Optional[Dict] = None) -> str:
        """
        Process document file using OpenAI file upload
        
        Args:
            filepath: Path to document file
            prompt: Processing prompt
            runtime_config: Runtime configuration
            
        Returns:
            Extracted text content
        """
        try:
            # Get configuration
            temperature = runtime_config.get('temperature', 0) if runtime_config else 0
            max_tokens = runtime_config.get('max_output_tokens', 300000) if runtime_config else 300000
            
            # Upload file to OpenAI
            file = self.client.files.create(
                file=open(filepath, "rb"), 
                purpose="user_data"
            )
            file_id = file.id
            
            logger.info(f"Uploaded file to OpenAI with ID: {file_id}")
            
            try:
                # Create OpenAI request for document
                response = self.client.responses.create(
                    model=self.model_name,
                    input=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_file",
                                    "file_id": file_id,
                                }
                            ]
                        }
                    ],
                    instructions=prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
                
                return response.output_text
                
            finally:
                # Clean up uploaded file
                try:
                    self.client.files.delete(file_id)
                    logger.info(f"Deleted uploaded file: {file_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete uploaded file {file_id}: {cleanup_error}")
            
        except Exception as e:
            logger.error(f"Failed to process document file {filepath}: {e}")
            raise
    
    def process_document(self, file_path: str, instruction: str, runtime_config: Optional[Dict] = None) -> str:
        """
        Process document using OpenAI GPT-4.1
        
        Args:
            file_path: Path to document file
            instruction: Processing instruction/prompt
            runtime_config: Runtime configuration with options:
                - temperature: Sampling temperature (0.0-2.0)
                - max_output_tokens: Maximum output tokens
                
        Returns:
            Processed document content as string
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        logger.info(f"Processing document with OpenAI {self.model_name}: {file_path}")
        
        try:
            # Choose processing method based on file type
            if self._is_image_file(file_path):
                logger.info(f"Processing as image file: {file_path}")
                result = self._process_image_file(file_path, instruction, runtime_config)
            else:
                logger.info(f"Processing as document file: {file_path}")
                result = self._process_document_file(file_path, instruction, runtime_config)
            
            logger.info(f"Successfully processed document with OpenAI, result length: {len(result) if result else 0}")
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise RuntimeError(f"OpenAI document processing failed: {str(e)}") from e
    
    def get_supported_formats(self) -> list:
        """Get supported file formats"""
        return [
            '.pdf', '.docx', '.doc', '.txt', '.md',  # Documents
            '.jpg', '.jpeg', '.png', '.bmp', '.gif'  # Images
        ]
    
    def validate_config(self, runtime_config: Optional[Dict] = None) -> bool:
        """
        Validate runtime configuration
        
        Args:
            runtime_config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        if not runtime_config:
            return True
        
        # Validate temperature
        if 'temperature' in runtime_config:
            temp = runtime_config['temperature']
            if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                logger.error(f"Invalid temperature: {temp}. Must be between 0 and 2")
                return False
        
        # Validate max_output_tokens
        if 'max_output_tokens' in runtime_config:
            max_tokens = runtime_config['max_output_tokens']
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                logger.error(f"Invalid max_output_tokens: {max_tokens}. Must be positive integer")
                return False
        
        return True