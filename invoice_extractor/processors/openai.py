"""
OpenAI Document Processor for OpenAI models with Structured Outputs support
"""

import os
import base64
import logging
from typing import Optional, Dict, Any, Union
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
    """OpenAI Document Processor with Structured Outputs support"""
    
    def __init__(self, model_name: str = "gpt-4o", **kwargs):
        """
        Initialize OpenAI processor
        
        Args:
            model_name: OpenAI model name (default: gpt-4o)
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

    def _supports_temperature(self) -> bool:
        """
        Check if current model supports temperature parameter

        GPT-5 series models do not support temperature parameter.

        Returns:
            True if model supports temperature, False otherwise
        """
        # GPT-5 and later models don't support temperature
        if 'gpt-5' in self.model_name.lower():
            return False
        return True
    
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
    
    def _convert_gemini_schema_to_openai(self, schema: Dict) -> Dict:
        """
        Convert Gemini-style schema to OpenAI Structured Outputs compatible format
        
        OpenAI Structured Outputs requirements:
        1. All properties must be in 'required' array
        2. Must set 'additionalProperties: false' on all objects
        3. Optional fields should use Union types with null
        4. Nested objects must follow same rules
        
        Args:
            schema: Gemini-style JSON schema
            
        Returns:
            OpenAI Structured Outputs compatible schema
        """
        def convert_schema_recursive(schema_obj):
            if not isinstance(schema_obj, dict):
                return schema_obj
            
            converted = {}
            
            for key, value in schema_obj.items():
                if key == "type":
                    converted[key] = value
                elif key == "properties":
                    # Convert properties recursively
                    converted_props = {}
                    for prop_key, prop_value in value.items():
                        converted_props[prop_key] = convert_schema_recursive(prop_value)
                    converted[key] = converted_props
                elif key == "items":
                    # Convert array items recursively
                    converted[key] = convert_schema_recursive(value)
                elif key == "required":
                    # Will be handled later - collect all property keys
                    continue
                else:
                    converted[key] = value
            
            # For objects, ensure all properties are required and additionalProperties is false
            if converted.get("type") == "object" and "properties" in converted:
                # Make all properties required for OpenAI strict mode
                converted["required"] = list(converted["properties"].keys())
                converted["additionalProperties"] = False
                
                # Handle originally optional fields by converting them to Union[Type, null]
                original_required = schema_obj.get("required", [])
                all_props = list(converted["properties"].keys())
                optional_props = [prop for prop in all_props if prop not in original_required]
                
                # Convert optional properties to nullable types
                for prop in optional_props:
                    prop_schema = converted["properties"][prop]
                    if isinstance(prop_schema, dict) and "type" in prop_schema:
                        # Convert to Union type with null
                        prop_type = prop_schema["type"]
                        converted["properties"][prop] = {
                            "anyOf": [
                                prop_schema,
                                {"type": "null"}
                            ]
                        }
                        logger.debug(f"Converted optional property '{prop}' to nullable type")
            
            return converted
        
        converted_schema = convert_schema_recursive(schema)
        logger.info("Converted Gemini schema to OpenAI Structured Outputs format")
        return converted_schema

    def _create_response_format(self, response_schema: Optional[Dict]) -> Optional[Dict]:
        """
        Create response_format for structured outputs
        
        Args:
            response_schema: JSON schema for response format (Gemini format)
            
        Returns:
            Formatted response_format dict for OpenAI API
        """
        if not response_schema:
            return None
        
        # Convert Gemini schema to OpenAI Structured Outputs format
        openai_schema = self._convert_gemini_schema_to_openai(response_schema)
        
        # Standard OpenAI structured outputs format
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_response",
                "strict": True,
                "schema": openai_schema
            }
        }
    
    def _prepare_message_content(self, filepath: str, prompt: str) -> tuple:
        """
        Prepare message content for OpenAI API

        Args:
            filepath: Path to file
            prompt: Processing prompt

        Returns:
            Tuple of (content_list, use_instructions_api)
            - content_list: List of content items for the message
            - use_instructions_api: Whether to use instructions-based API
        """
        if self._is_image_file(filepath):
            # Handle image files with base64 encoding
            base64_image = self._encode_image(filepath)
            content = [
                {"type": "input_text", "text": prompt},
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                }
            ]
            return content, False
        else:
            # For non-image files (PDF, DOCX, etc.), use file upload with user_data purpose
            try:
                with open(filepath, "rb") as file:
                    uploaded_file = self.client.files.create(
                        file=file,
                        purpose="user_data"  # user_data supports PDF and other document formats
                    )
                    content = [{
                        "type": "input_file",
                        "file_id": uploaded_file.id
                    }]
                    # Store file_id for cleanup
                    self._uploaded_file_id = uploaded_file.id
                    # For file uploads, use instructions-based API
                    return content, True
            except Exception as e:
                logger.error(f"Failed to upload file {filepath}: {e}")
                raise
    
    def process_document(self, file_path: str, instruction: str, runtime_config: Optional[Dict] = None) -> str:
        """
        Process document using OpenAI Responses API with Structured Outputs support
        
        Args:
            file_path: Path to document file
            instruction: Processing instruction/prompt
            runtime_config: Runtime configuration with options:
                - temperature: Sampling temperature (0.0-2.0)
                - max_output_tokens: Maximum output tokens
                - response_schema: JSON schema for structured outputs
                - response_mime_type: Response MIME type (for compatibility)
                
        Returns:
            Processed document content as string (JSON if schema provided)
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        logger.info(f"Processing document with OpenAI {self.model_name}: {file_path}")
        
        try:
            # Get runtime configuration
            temperature = runtime_config.get('temperature', 0.1) if runtime_config else 0.1
            max_tokens = runtime_config.get('max_output_tokens', 4096) if runtime_config else 4096
            response_schema = runtime_config.get('response_schema') if runtime_config else None

            # Prepare message content
            content, use_instructions_api = self._prepare_message_content(file_path, instruction)

            # Prepare API parameters based on file type
            if use_instructions_api:
                # For PDF and other documents, use instructions-based API
                api_params = {
                    "model": self.model_name,
                    "input": [{
                        "role": "user",
                        "content": content
                    }],
                    "instructions": instruction,
                    "max_output_tokens": max_tokens
                }
            else:
                # For images, use content-based API
                api_params = {
                    "model": self.model_name,
                    "input": [{
                        "role": "user",
                        "content": content
                    }],
                    "max_output_tokens": max_tokens
                }

            # Only add temperature if model supports it
            if self._supports_temperature():
                api_params["temperature"] = temperature
            else:
                logger.info(f"Skipping temperature parameter for model {self.model_name} (not supported)")

            # Add response format for structured outputs
            response_format = self._create_response_format(response_schema)
            if response_format:
                api_params["response_format"] = response_format
                logger.info("Using structured outputs with response schema")

            logger.info(f"Calling OpenAI API with parameters: {api_params.keys()}, use_instructions_api={use_instructions_api}")

            # Choose API based on whether we need structured outputs
            if response_format:
                # Use chat.completions.create for structured outputs support
                messages = []
                for input_item in api_params["input"]:
                    if input_item["role"] == "user":
                        messages.append({
                            "role": "user",
                            "content": input_item["content"]
                        })

                chat_params = {
                    "model": api_params["model"],
                    "messages": messages,
                    "max_tokens": api_params["max_output_tokens"],
                    "response_format": response_format
                }

                # Only add temperature if model supports it
                if self._supports_temperature():
                    chat_params["temperature"] = temperature

                response = self.client.chat.completions.create(**chat_params)

                # Convert chat completion response to responses-like format
                class MockResponse:
                    def __init__(self, chat_response):
                        self.output_text = chat_response.choices[0].message.content
                        self.output = [
                            type('obj', (object,), {
                                'content': [
                                    type('obj', (object,), {
                                        'text': chat_response.choices[0].message.content
                                    })()
                                ]
                            })()
                        ]

                response = MockResponse(response)
            else:
                # Use responses.create for regular processing
                response = self.client.responses.create(**api_params)
            
            # Extract response content
            result = None
            if hasattr(response, 'output_text') and response.output_text:
                result = response.output_text
            elif hasattr(response, 'output') and response.output:
                # Extract text from output messages
                for output_item in response.output:
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                result = content_item.text
                                break
                    if result:
                        break
            
            if not result:
                raise RuntimeError("No response content received from OpenAI")

            logger.info(f"OpenAI response: {result}")
            logger.info(f"Successfully processed document with OpenAI, result length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise RuntimeError(f"OpenAI document processing failed: {str(e)}") from e
        finally:
            # Clean up uploaded files
            if hasattr(self, '_uploaded_file_id'):
                try:
                    self.client.files.delete(self._uploaded_file_id)
                    logger.info(f"Deleted uploaded file: {self._uploaded_file_id}")
                    delattr(self, '_uploaded_file_id')
                except Exception as cleanup_error:
                    logger.warning(f"Failed to delete uploaded file: {cleanup_error}")
    
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
        
        # Validate response_schema
        if 'response_schema' in runtime_config:
            schema = runtime_config['response_schema']
            if schema is not None and not isinstance(schema, dict):
                logger.error(f"Invalid response_schema: {type(schema)}. Must be a dict or None")
                return False
            
            # Basic schema validation
            if schema and 'type' not in schema:
                logger.error("response_schema must contain 'type' field")
                return False
        
        return True
    
    def supports_structured_outputs(self) -> bool:
        """Check if this processor supports structured outputs"""
        return True